# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import re
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import requests
import yaml
from bs4 import BeautifulSoup

LIST_URL = "https://www.kasb.or.kr/front/board/allReplySummaryList.do"
DOWNLOAD_URL = "https://www.kasb.or.kr/commonFile/fileDownload.do"

_DETAIL_RE = re.compile(r"fn_Detail\s*\(\s*'(\d+)'\s*,\s*'(\d+)'\s*\)")
_FILE_RE = re.compile(r"fileDownload\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")
_PAGE_RE = re.compile(r"G_MovePage\((\d+)\)")


@dataclass(frozen=True)
class AttachmentRef:
    name: str
    file_no: str
    file_seq: str


@dataclass(frozen=True)
class ListRow:
    seq: str
    ctg_cd: str
    number: str
    category: str
    title: str
    reply_date: str | None
    published_date: str | None
    attachments: tuple[AttachmentRef, ...]


def parse_date(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _attachments_in(node) -> list[AttachmentRef]:
    found = []
    for link in node.find_all("a"):
        match = _FILE_RE.search(link.get("onclick") or "")
        if not match:
            continue
        name = link.get_text(strip=True) or f"file-{match.group(2)}"
        found.append(AttachmentRef(name=name, file_no=match.group(1), file_seq=match.group(2)))
    return found


def parse_list_page(html: str) -> list[ListRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        cells = tr.find_all("td")
        if len(cells) < 6:
            continue
        title_link = None
        detail = None
        for link in cells[2].find_all("a"):
            detail = _DETAIL_RE.search(link.get("onclick") or "")
            if detail:
                title_link = link
                break
        if not detail or title_link is None:
            continue
        rows.append(
            ListRow(
                seq=detail.group(1),
                ctg_cd=detail.group(2),
                number=cells[0].get_text(strip=True),
                category=cells[1].get_text(strip=True),
                title=title_link.get_text(strip=True),
                reply_date=parse_date(cells[4].get_text(strip=True)),
                published_date=parse_date(cells[5].get_text(strip=True)),
                attachments=tuple(_attachments_in(cells[3])),
            )
        )
    return rows


def last_page_number(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("li.pag_last a")
    if node is None:
        return 1
    match = _PAGE_RE.search(node.get("href") or "")
    return int(match.group(1)) if match else 1


def dedupe_rows(rows: list[ListRow]) -> list[ListRow]:
    seen: set[str] = set()
    kept = []
    for row in rows:
        if row.seq in seen:
            continue
        seen.add(row.seq)
        kept.append(row)
    return kept


@dataclass(frozen=True)
class DetailPage:
    category: str | None
    standards: tuple[str, ...]
    registered_date: str | None
    notice: str
    attachments: tuple[AttachmentRef, ...]


def _labeled_text(wrap, label: str) -> str:
    for th in wrap.find_all("th"):
        if th.get_text(strip=True) == label:
            td = th.find_next("td")
            return td.get_text(" ", strip=True) if td else ""
    return ""


def parse_detail_page(html: str) -> DetailPage:
    soup = BeautifulSoup(html, "html.parser")
    wrap = soup.select_one(".board_view_wrap") or soup
    category = _labeled_text(wrap, "분류") or None
    standards: list[str] = []
    for th in wrap.find_all("th"):
        if th.get_text(strip=True) != "관련기준서":
            continue
        td = th.find_next("td")
        if td is not None:
            inner_rows = td.find_all("tr")
            if not inner_rows:
                text = td.get_text(" ", strip=True)
                if text:
                    standards.append(text)
            else:
                for row in inner_rows:
                    label_th = row.find("th")
                    label = label_th.get_text(strip=True) if label_th else ""
                    td_texts = [
                        cell.get_text(" ", strip=True)
                        for cell in row.find_all("td")
                        if cell.get_text(" ", strip=True)
                    ]
                    joined = " ".join(td_texts)
                    if not joined:
                        continue
                    if label == "기준서 명" and standards:
                        standards[-1] = f"{standards[-1]} {joined}"
                    else:
                        standards.append(joined)
        break
    notice_node = wrap.select_one(".board_view_cont")
    notice = notice_node.get_text(" ", strip=True) if notice_node else ""
    return DetailPage(
        category=category,
        standards=tuple(standards),
        registered_date=parse_date(_labeled_text(wrap, "등록일")),
        notice=notice,
        attachments=tuple(_attachments_in(wrap)),
    )


def _nonempty(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    return (cleaned, "ok" if cleaned else "empty")


def _extract_pdf(data: bytes) -> tuple[str, str]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return _nonempty("\n\n".join(parts))


def _extract_hwpx(data: bytes) -> tuple[str, str]:
    texts = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = sorted(
            name
            for name in zf.namelist()
            if name.startswith("Contents/section") and name.endswith(".xml")
        )
        for name in names:
            raw = zf.read(name)
            root = ElementTree.fromstring(raw)
            for el in root.iter():
                if el.tag.split("}")[-1] == "t" and el.text:
                    texts.append(el.text)
    return _nonempty("\n".join(texts))


def _cell(value) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return text.replace("|", "\\|")


def _extract_xlsx(data: bytes) -> tuple[str, str]:
    from openpyxl import load_workbook

    book = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    chunks = []
    for sheet in book.worksheets:
        rows = []
        for row in sheet.iter_rows(values_only=True):
            if all(cell is None or str(cell).strip() == "" for cell in row):
                continue
            rows.append([_cell(cell) for cell in row])
        if not rows:
            continue
        width = max(len(row) for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]
        header = "| " + " | ".join(rows[0]) + " |"
        rule = "| " + " | ".join("---" for _ in rows[0]) + " |"
        body = ["| " + " | ".join(row) + " |" for row in rows[1:]]
        chunks.append("### " + sheet.title + "\n\n" + "\n".join([header, rule, *body]))
    return _nonempty("\n\n".join(chunks))


def _extract_hwp(data: bytes) -> tuple[str, str]:
    import olefile

    try:
        ole = olefile.OleFileIO(io.BytesIO(data))
    except Exception as exc:
        return (str(exc), "failed")
    if not ole.exists("PrvText"):
        return ("PrvText missing", "failed")
    raw = ole.openstream("PrvText").read()
    try:
        text = raw.decode("utf-16-le")
    except UnicodeDecodeError as exc:
        return (str(exc), "failed")
    while text and (text[-1] == "\x00" or text[-1].isspace()):
        text = text[:-1]
    if not text:
        return ("empty preview", "failed")
    return (text, "partial")


def extract_bytes(filename: str, data: bytes) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            return _extract_pdf(data)
        if suffix == ".hwpx":
            return _extract_hwpx(data)
        if suffix == ".xlsx":
            return _extract_xlsx(data)
        if suffix == ".hwp":
            return _extract_hwp(data)
    except Exception as exc:
        return (str(exc), "failed")
    return ("unsupported", "failed")


def aggregate_status(statuses: list[str]) -> str:
    if not statuses:
        return "empty"
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "partial" for status in statuses):
        return "partial"
    if all(status == "empty" for status in statuses):
        return "empty"
    if any(status == "empty" for status in statuses):
        return "partial"
    if all(status == "ok" for status in statuses):
        return "ok"
    return "failed"


def attachment_filename(name: str, file_seq: str, used: set[str]) -> str:
    cleaned = Path(name.replace("\\", "/")).name.strip() or f"attachment-{file_seq}"
    cleaned = cleaned.replace("\x00", "")
    if cleaned not in used:
        used.add(cleaned)
        return cleaned
    stem = Path(cleaned).stem
    suffix = Path(cleaned).suffix
    candidate = f"{stem}-{file_seq}{suffix}"
    number = 2
    while candidate in used:
        candidate = f"{stem}-{file_seq}-{number}{suffix}"
        number += 1
    used.add(candidate)
    return candidate


def compose_item(row: ListRow, detail: DetailPage, sections: list[tuple[str, str, str]], fetched_at: str) -> str:
    category = detail.category or row.category
    reply_date = row.reply_date or detail.registered_date
    source = detail.attachments or row.attachments
    names = []
    used: set[str] = set()
    for ref in source:
        names.append(attachment_filename(ref.name, ref.file_seq, used))
    by_saved = {filename: (text, status) for filename, text, status in sections}
    attachments = []
    body_sections = []
    for ref, filename in zip(source, names):
        text, status = by_saved.get(filename, ("missing extract", "failed"))
        attachments.append(
            {
                "name": filename,
                "file_no": ref.file_no,
                "file_seq": ref.file_seq,
                "extract_status": status,
            }
        )
        body_sections.append((filename, text, status))
    meta = {
        "seq": row.seq,
        "ctg_cd": row.ctg_cd,
        "number": row.number,
        "category": category,
        "title": row.title,
        "standards": list(detail.standards),
        "reply_date": reply_date,
        "published_date": row.published_date,
        "attachments": attachments,
        "fetched_at": fetched_at,
        "extract_status": aggregate_status([item["extract_status"] for item in attachments]),
    }
    dumped = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    lines = ["---", dumped, "---", "", "## 상세 안내", "", detail.notice.strip() or "(없음)", ""]
    for filename, text, status in body_sections:
        lines.extend([f"## 첨부: {filename}", ""])
        if status in {"ok", "partial"} and text.strip():
            lines.extend([text.rstrip(), ""])
        else:
            lines.extend([f"{status}: {text.strip() or status}", ""])
    return "\n".join(lines).rstrip() + "\n"


def read_meta(directory: Path) -> dict | None:
    item = directory / "item.md"
    if not item.is_file():
        return None
    text = item.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return meta if isinstance(meta, dict) else None


def should_attempt(directory: Path, retry_failed: bool) -> bool:
    meta = read_meta(directory)
    if meta is None:
        return True
    status = meta.get("extract_status")
    files_ok = all((directory / item["name"]).is_file() for item in meta.get("attachments") or [])
    if status == "ok" and files_ok:
        return False
    if status == "ok" and not files_ok:
        return True
    if not files_ok:
        return True
    return retry_failed and status in {"failed", "partial", "empty"}


def append_manifest(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def crawl_archive(
    archive: Path,
    *,
    fetch_list,
    fetch_detail,
    fetch_file,
    delay: float = 0.2,
    limit: int | None = None,
    retry_failed: bool = False,
    sleep=time.sleep,
    now=None,
) -> dict[str, int]:
    archive.mkdir(parents=True, exist_ok=True)
    counts = {"saved": 0, "skipped": 0, "failed": 0}
    seen: set[str] = set()
    attempts = 0
    first_http = True

    def call(func, *args):
        nonlocal first_http
        if not first_http and delay:
            sleep(delay)
        first_http = False
        return func(*args)

    page = 1
    last_page = 1
    while page <= last_page:
        html = call(fetch_list, page)
        if page == 1:
            last_page = last_page_number(html)
        for row in parse_list_page(html):
            if row.seq in seen:
                continue
            seen.add(row.seq)
            directory = archive / row.seq
            if not should_attempt(directory, retry_failed):
                counts["skipped"] += 1
                continue
            if limit is not None and attempts >= limit:
                return counts
            attempts += 1
            try:
                detail = parse_detail_page(call(fetch_detail, row.seq, row.ctg_cd))
                refs = detail.attachments or row.attachments
                directory.mkdir(parents=True, exist_ok=True)
                used: set[str] = set()
                pending: list[tuple[str, bytes | None]] = []
                for ref in refs:
                    filename = attachment_filename(ref.name, ref.file_seq, used)
                    path = directory / filename
                    if path.is_file():
                        pending.append((filename, None))
                    else:
                        pending.append((filename, call(fetch_file, ref.file_no, ref.file_seq)))
                sections = []
                for filename, payload in pending:
                    path = directory / filename
                    data = path.read_bytes() if payload is None else payload
                    if payload is not None:
                        path.write_bytes(payload)
                    text, status = extract_bytes(filename, data)
                    sections.append((filename, text, status))
                moment = now() if now else datetime.now(timezone.utc)
                if moment.tzinfo is None:
                    moment = moment.replace(tzinfo=timezone.utc)
                item = compose_item(row, detail, sections, moment.isoformat())
                (directory / "item.md").write_text(item, encoding="utf-8")
                meta = read_meta(directory) or {}
                append_manifest(
                    archive / "manifest.jsonl",
                    {
                        "seq": row.seq,
                        "ctg_cd": row.ctg_cd,
                        "number": row.number,
                        "category": meta.get("category", row.category),
                        "title": row.title,
                        "reply_date": meta.get("reply_date", row.reply_date),
                        "published_date": row.published_date,
                        "extract_status": meta.get("extract_status", "failed"),
                        "path": f"{row.seq}/item.md",
                        "error": None,
                    },
                )
                counts["saved"] += 1
            except Exception as exc:
                append_manifest(
                    archive / "manifest.jsonl",
                    {
                        "seq": row.seq,
                        "ctg_cd": row.ctg_cd,
                        "number": row.number,
                        "category": row.category,
                        "title": row.title,
                        "reply_date": row.reply_date,
                        "published_date": row.published_date,
                        "extract_status": "failed",
                        "path": None,
                        "error": str(exc),
                    },
                )
                counts["failed"] += 1
        page += 1
    return counts


def default_archive() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "kasb-replies"


def default_raw_dest() -> Path:
    return Path(r"C:\dev\obsidian-vault\raw\kasb-replies")


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    session.get(LIST_URL, timeout=30)
    return session


def _view_url(ctg_cd: str) -> str:
    return f"https://www.kasb.or.kr/front/board/View{ctg_cd}.do"


def http_fetch_list(session, page: int) -> str:
    response = session.post(
        LIST_URL,
        data={
            "siteCd": "002000000000000",
            "searchfield": "ALL",
            "searchword": "",
            "page": page,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def http_fetch_detail(session, seq: str, ctg_cd: str) -> str:
    response = session.post(_view_url(ctg_cd), data={"seq": seq, "ctgCd": ctg_cd}, timeout=30)
    response.raise_for_status()
    return response.text


def http_fetch_file(session, file_no: str, file_seq: str) -> bytes:
    response = session.post(
        DOWNLOAD_URL,
        data={"fileNo": file_no, "fileSeq": file_seq},
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def copy_archive_markdown(archive: Path, dest: Path) -> tuple[int, int]:
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0
    if not archive.is_dir():
        return copied, skipped
    for item in sorted(archive.glob("*/item.md")):
        target = dest / f"{item.parent.name}.md"
        if target.exists():
            skipped += 1
            continue
        target.write_bytes(item.read_bytes())
        copied += 1
    return copied, skipped
