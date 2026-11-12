# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

from . import fss_hwp_text

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


_TEMP_PATH = re.compile(r"/tmp/(?:tmp|fss-hwp-|kasb-hwp-)[A-Za-z0-9_.-]*")
_SUCCESS_STATUS = {"ok", "hwp_parsed", "hwpx_parsed"}
_BODY_STATUS = _SUCCESS_STATUS | {"partial"}
_REV_RE = re.compile(r"[A-Za-z0-9._-]+")


def _short_error(exc: BaseException | str, tmp_path: Path | None = None) -> str:
    """트레이스백과 임시 경로를 빼고, 실행마다 같은 한 줄만 남긴다."""
    if isinstance(exc, subprocess.TimeoutExpired):
        return "TimeoutExpired: timed out"
    text = exc if isinstance(exc, str) else str(exc or "")
    if tmp_path is not None:
        text = text.replace(str(tmp_path), "")
        try:
            text = text.replace(str(tmp_path.resolve()), "")
        except OSError:
            pass
    text = _TEMP_PATH.sub("", text)
    lines = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not line or line.startswith("Traceback") or line.startswith("File ") or line.startswith("^"):
            continue
        lines.append(line)
    chosen = ""
    for line in reversed(lines):
        if re.search(r"(Error|Exception)\b", line):
            chosen = line
            break
    if not chosen and lines:
        chosen = lines[-1]
    chosen = " ".join(_TEMP_PATH.sub("", chosen).split())
    if not chosen:
        if isinstance(exc, str):
            return "failed"
        return exc.__class__.__name__
    if isinstance(exc, str):
        return chosen
    if "Error" not in chosen and "Exception" not in chosen:
        return f"{exc.__class__.__name__}: {chosen}"
    return chosen


def _extract_hwpx(data: bytes) -> tuple[str, str]:
    try:
        text = fss_hwp_text.hwpx_to_text(data)
    except fss_hwp_text.HwpConvertError as exc:
        return (_short_error(exc), "failed")
    if not str(text).strip():
        return ("empty", "failed")
    return (str(text).strip(), "hwpx_parsed")


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


def _prvtext(ole) -> str | None:
    try:
        if not ole.exists("PrvText"):
            return None
        raw = ole.openstream("PrvText").read()
        text = raw.decode("utf-16-le")
    except Exception:
        return None
    while text and (text[-1] == "\x00" or text[-1].isspace()):
        text = text[:-1]
    return text or None


def _hwp_fallback(ole, exc: BaseException | str, tmp_path: Path | None) -> tuple[str, str]:
    message = _short_error(exc, tmp_path)
    preview = _prvtext(ole)
    if preview:
        return (f"{preview}\n\n오류: {message}", "partial")
    if message == "empty":
        return ("PrvText missing", "failed")
    return (message, "failed")


def _extract_hwp(data: bytes, *, timeout: float = 90, hwp_to_html=None) -> tuple[str, str]:
    if not data:
        return ("empty file", "failed")
    import olefile

    try:
        ole = olefile.OleFileIO(io.BytesIO(data))
    except Exception:
        return ("not an OLE file", "failed")
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="kasb-hwp-", suffix=".hwp", delete=False) as handle:
            handle.write(data)
            tmp_path = Path(handle.name)
        convert = hwp_to_html or fss_hwp_text.hwp_file_to_html
        try:
            html = convert(tmp_path, timeout)
            text = fss_hwp_text.html_to_markdown(html)
        except Exception as exc:
            return _hwp_fallback(ole, exc, tmp_path)
        if not str(text).strip():
            return _hwp_fallback(ole, "empty", tmp_path)
        return (str(text).strip(), "hwp_parsed")
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        ole.close()


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
        return (_short_error(exc), "failed")
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
    if all(status in _SUCCESS_STATUS for status in statuses):
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
        if status in _BODY_STATUS and text.strip():
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


def _attachment_payload(text: str, status: str) -> str:
    if status in _BODY_STATUS and text.strip():
        return text.rstrip()
    return f"{status}: {text.strip() or status}"


def _replace_attachment_section(body: str, filename: str, payload: str) -> str:
    marker = f"## 첨부: {filename}"
    start = body.find(marker)
    block = f"{marker}\n\n{payload.strip()}\n"
    if start < 0:
        suffix = body if body.endswith("\n") or not body else body + "\n"
        return suffix + "\n" + block
    next_heading = body.find("\n## 첨부:", start + len(marker))
    end = next_heading if next_heading >= 0 else len(body)
    return body[:start] + block + body[end:]


def _status_token(line: str) -> str:
    value = line.split(":", 1)[1].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _front_with_statuses(front: str, attachment_statuses: list[str], item_status: str) -> str:
    lines = front.splitlines()
    attachment_index = 0
    in_attachments = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("attachments:"):
            in_attachments = True
            continue
        if in_attachments and line and not line[0].isspace() and not stripped.startswith("-"):
            in_attachments = False
        if (
            in_attachments
            and stripped.startswith("extract_status:")
            and attachment_index < len(attachment_statuses)
        ):
            new_status = attachment_statuses[attachment_index]
            attachment_index += 1
            if _status_token(line) == new_status:
                continue
            indent = line[: len(line) - len(line.lstrip(" \t"))]
            lines[index] = f"{indent}extract_status: {new_status}"
        elif (not in_attachments) and line.startswith("extract_status:"):
            if _status_token(line) != item_status:
                lines[index] = f"extract_status: {item_status}"
    return "\n".join(lines)


def _write_item(text: str, body: str, attachment_statuses: list[str], item_status: str) -> str:
    close = text.find("\n---", 3)
    if close < 0:
        raise ValueError("item.md missing front matter end")
    front = _front_with_statuses(text[4:close], attachment_statuses, item_status)
    if not body.startswith("\n"):
        body = "\n" + body
    if not body.endswith("\n"):
        body += "\n"
    return f"---\n{front}\n---{body}"


def _split_item(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ValueError("item.md missing front matter")
    close = text.find("\n---", 3)
    if close < 0:
        raise ValueError("item.md missing front matter end")
    meta = yaml.safe_load(text[4:close])
    if not isinstance(meta, dict):
        raise ValueError("item.md front matter is not a mapping")
    return meta, text[close + 4 :]


def _local_target(name: str, status: str, reextract_hwpx: bool) -> bool:
    suffix = Path(name).suffix.lower()
    if suffix == ".hwp" and status in {"partial", "failed"}:
        return True
    return bool(reextract_hwpx and suffix == ".hwpx" and status == "ok")


def _sync_manifest_statuses(archive: Path, updates: dict[str, str]) -> None:
    if not updates:
        return
    path = archive / "manifest.jsonl"
    original = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = original.splitlines()
    last: dict[str, int] = {}
    parsed: dict[int, dict] = {}
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        seq = str(record.get("seq") or "")
        if not seq:
            continue
        last[seq] = index
        parsed[index] = record
    changed = False
    for seq, status in updates.items():
        index = last.get(seq)
        if index is None:
            lines.append(
                json.dumps(
                    {
                        "seq": seq,
                        "extract_status": status,
                        "path": f"{seq}/item.md",
                        "error": None,
                    },
                    ensure_ascii=False,
                )
            )
            changed = True
            continue
        record = parsed[index]
        if record.get("extract_status") == status:
            continue
        record["extract_status"] = status
        lines[index] = json.dumps(record, ensure_ascii=False)
        changed = True
    if not changed:
        return
    text = "\n".join(lines)
    if original.endswith("\n") or original == "":
        text += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def extract_local(
    archive: Path,
    *,
    reextract_hwpx: bool = False,
    timeout: float = 90,
    hwp_to_html=None,
) -> dict[str, int]:
    """커밋된 첨부만 다시 읽는다. 네트워크를 쓰지 않는다.

    대상은 ``partial`` 또는 ``failed`` 인 ``.hwp`` 다. ``reextract_hwpx`` 이면
    상태가 ``ok`` 인 ``.hwpx`` 도 다시 읽는다. 이미 성공한 첨부와 PDF, XLSX 는
    그대로 둔다. 같은 아카이브를 다시 실행하면 바이트가 같다.
    """
    counts = {"parsed": 0, "failed": 0, "partial": 0, "skipped": 0}
    if not archive.is_dir():
        return counts
    updates: dict[str, str] = {}
    for path in sorted(item for item in archive.glob("*/item.md") if item.is_file()):
        text = path.read_text(encoding="utf-8")
        try:
            meta, body = _split_item(text)
        except (ValueError, yaml.YAMLError):
            continue
        attachments = [item for item in (meta.get("attachments") or []) if isinstance(item, dict)]
        new_statuses: list[str] = []
        changed = False
        for attachment in attachments:
            status = str(attachment.get("extract_status") or "")
            name = str(attachment.get("name") or "")
            if not _local_target(name, status, reextract_hwpx):
                counts["skipped"] += 1
                new_statuses.append(status)
                continue
            file_path = path.parent / name
            if not file_path.is_file():
                extracted, new_status = ("missing file", "failed")
            elif Path(name).suffix.lower() == ".hwpx":
                extracted, new_status = _extract_hwpx(file_path.read_bytes())
            else:
                extracted, new_status = _extract_hwp(
                    file_path.read_bytes(),
                    timeout=timeout,
                    hwp_to_html=hwp_to_html,
                )
            body = _replace_attachment_section(body, name, _attachment_payload(extracted, new_status))
            new_statuses.append(new_status)
            changed = True
            if new_status in _SUCCESS_STATUS:
                counts["parsed"] += 1
            elif new_status == "partial":
                counts["partial"] += 1
            else:
                counts["failed"] += 1
        if not new_statuses:
            continue
        item_status = aggregate_status(new_statuses)
        if changed or [str(item.get("extract_status") or "") for item in attachments] != new_statuses:
            rewritten = _write_item(text, body, new_statuses, item_status)
            if rewritten != text:
                path.write_text(rewritten, encoding="utf-8")
        previous = str(meta.get("extract_status") or "")
        if previous != item_status:
            updates[str(meta.get("seq") or path.parent.name)] = item_status
    _sync_manifest_statuses(archive, updates)
    return counts


def _count_write(target: Path, payload: bytes) -> str:
    if target.is_file() and target.read_bytes() == payload:
        return "skipped"
    target.parent.mkdir(parents=True, exist_ok=True)
    existed = target.is_file()
    target.write_bytes(payload)
    return "updated" if existed else "copied"


def _validated_rev(sibling_rev: str) -> str:
    if not _REV_RE.fullmatch(sibling_rev):
        raise ValueError("invalid sibling rev")
    return sibling_rev


def copy_archive_markdown(
    archive: Path,
    dest: Path,
    *,
    sibling_rev: str | None = None,
) -> tuple[int, int] | tuple[int, int, int]:
    if sibling_rev is None:
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
    rev = _validated_rev(sibling_rev)
    counts = {"copied": 0, "updated": 0, "skipped": 0}
    if not archive.is_dir():
        return counts["copied"], counts["updated"], counts["skipped"]
    dest.mkdir(parents=True, exist_ok=True)
    for item in sorted(path for path in archive.glob("*/item.md") if path.is_file()):
        target = dest / f"{item.parent.name}.{rev}.md"
        counts[_count_write(target, item.read_bytes())] += 1
    manifest = archive / "manifest.jsonl"
    if manifest.is_file():
        counts[_count_write(dest / f"manifest-{rev}.jsonl", manifest.read_bytes())] += 1
    return counts["copied"], counts["updated"], counts["skipped"]
