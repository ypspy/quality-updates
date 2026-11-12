# -*- coding: utf-8 -*-
"""금융감독원 질의회신 요약 두 게시판을 항목 폴더로 보관한다.

KASB 질의회신 아카이브와 같은 저장 방식이다. 그 모듈을 import하지 않는다.
다운로드 주소와 쿼리 이름은 운영자가 저장한 상세 HTML의 fileDown.do 링크를 따른다.
"""
from __future__ import annotations

import io
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
import yaml
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
ORIGIN = "https://www.fss.or.kr"

BOARD_MENU = {
    "B0000132": "200442",
    "B0000133": "200443",
}

_REPLY_RE = re.compile(
    r"회신일\s*[`'‘’']?\s*(\d{2,4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})"
)
_SIZE_RE = re.compile(r"\(파일크기:.*?\)")
_INVALID_NAME = re.compile(r'[<>:"/\\|?*]')


@dataclass(frozen=True)
class AttachmentRef:
    name: str
    atch_file_id: str
    file_sn: str
    menu_no: str


@dataclass(frozen=True)
class ListRow:
    board: str
    menu_no: str
    ntt_id: str
    number: str
    title: str
    department: str
    standards: tuple[str, ...]
    published_date: str | None
    attachments: tuple[AttachmentRef, ...]


@dataclass(frozen=True)
class DetailPage:
    subject: str
    department: str
    registered_date: str | None
    notice: str
    attachments: tuple[AttachmentRef, ...]


def selected_boards(choice: str) -> list[str]:
    if choice == "all":
        return ["B0000132", "B0000133"]
    if choice not in BOARD_MENU:
        raise ValueError(choice)
    return [choice]


def page_url(board: str, ntt_id: str, menu_no: str) -> str:
    return f"{ORIGIN}/fss/bbs/{board}/view.do?nttId={ntt_id}&menuNo={menu_no}"


def parse_date(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def resolve_reply_date(title: str, detail_text: str, published_date: str | None) -> str | None:
    for text in (title, detail_text):
        match = _REPLY_RE.search(text or "")
        if not match:
            continue
        year = int(match.group(1))
        if year < 100:
            year += 2000
        month = int(match.group(2))
        day = int(match.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"
    return published_date


def _query(href: str) -> dict[str, str]:
    parsed = parse_qs(urlparse(href).query)
    return {key: values[0] for key, values in parsed.items() if values}


def _link_name(link) -> str:
    span = link.select_one("span.name")
    if span is not None and span.get_text(strip=True):
        return " ".join(span.get_text(" ", strip=True).split())
    text = _SIZE_RE.sub("", link.get_text(" ", strip=True))
    return " ".join(text.split())


def _attachments_in(node) -> list[AttachmentRef]:
    found = []
    seen: set[tuple[str, str]] = set()
    if node is None:
        return found
    for link in node.find_all("a"):
        href = link.get("href") or ""
        if "fileDown.do" not in href:
            continue
        name = _link_name(link)
        if not name or name in {"다운로드", "문서뷰어"}:
            continue
        query = _query(href)
        atch = query.get("atchFileId", "")
        file_sn = query.get("fileSn", "")
        if not atch:
            continue
        key = (atch, file_sn)
        if key in seen:
            continue
        seen.add(key)
        found.append(
            AttachmentRef(
                name=name,
                atch_file_id=atch,
                file_sn=file_sn,
                menu_no=query.get("menuNo", ""),
            )
        )
    return found


def _standard_names(cell) -> list[str]:
    for br in cell.find_all("br"):
        br.replace_with("\n")
    names = []
    for line in cell.get_text("\n").splitlines():
        text = " ".join(line.split())
        if text:
            names.append(text)
    return names


def _board_from_href(href: str) -> str:
    parts = [part for part in urlparse(href).path.split("/") if part]
    if "bbs" not in parts:
        return ""
    index = parts.index("bbs") + 1
    if index >= len(parts):
        return ""
    return parts[index]


def parse_list_page(html: str) -> list[ListRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[ListRow] = []
    for table in soup.select("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "제목" not in headers or "번호" not in headers:
            continue
        index = {name: pos for pos, name in enumerate(headers)}
        for tr in table.select("tbody tr"):
            cells = tr.find_all("td")
            if len(cells) <= index["제목"]:
                continue
            link = cells[index["제목"]].select_one("a[href*='view.do']")
            if link is None:
                continue
            href = link.get("href") or ""
            board = _board_from_href(href)
            ntt_id = _query(href).get("nttId", "")
            if not board or not ntt_id:
                continue
            menu_no = _query(href).get("menuNo") or BOARD_MENU.get(board, "")
            standards: tuple[str, ...] = ()
            if "관련기준서" in index and index["관련기준서"] < len(cells):
                standards = tuple(_standard_names(cells[index["관련기준서"]]))
            department = ""
            if "담당부서" in index and index["담당부서"] < len(cells):
                department = cells[index["담당부서"]].get_text(strip=True)
            published = None
            if "등록일" in index and index["등록일"] < len(cells):
                published = parse_date(cells[index["등록일"]].get_text(strip=True))
            attachments: tuple[AttachmentRef, ...] = ()
            if "첨부파일" in index and index["첨부파일"] < len(cells):
                attachments = tuple(_attachments_in(cells[index["첨부파일"]]))
            rows.append(
                ListRow(
                    board=board,
                    menu_no=menu_no,
                    ntt_id=ntt_id,
                    number=cells[index["번호"]].get_text(strip=True),
                    title=link.get_text(strip=True),
                    department=department,
                    standards=standards,
                    published_date=published,
                    attachments=attachments,
                )
            )
    return rows


def _labeled(view, label: str) -> str:
    for dt in view.find_all("dt"):
        if dt.get_text(strip=True) == label:
            dd = dt.find_next("dd")
            return dd.get_text(" ", strip=True) if dd else ""
    return ""


def parse_detail_page(html: str) -> DetailPage:
    soup = BeautifulSoup(html, "html.parser")
    view = soup.select_one(".krds-bd-view") or soup
    subject_node = view.select_one("h3.subject")
    subject = subject_node.get_text(" ", strip=True) if subject_node else ""
    notice_node = view.select_one(".dbdata") or view.select_one(".n-dbdata")
    notice = ""
    if notice_node is not None:
        for script in notice_node.find_all("script"):
            script.decompose()
        notice = notice_node.get_text(" ", strip=True)
    return DetailPage(
        subject=subject,
        department=_labeled(view, "담당부서"),
        registered_date=parse_date(_labeled(view, "등록일")),
        notice=notice,
        attachments=tuple(_attachments_in(view)),
    )


def stored_attachments(refs: tuple[AttachmentRef, ...] | list[AttachmentRef]) -> tuple[AttachmentRef, ...]:
    pdfs = [ref for ref in refs if Path(ref.name).suffix.lower() == ".pdf"]
    if pdfs:
        return tuple(pdfs)
    hangul = [ref for ref in refs if Path(ref.name).suffix.lower() in {".hwp", ".hwpx"}]
    if hangul:
        return tuple(hangul)
    return tuple(refs)


def _nonempty(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    return (cleaned, "ok" if cleaned else "empty")


def _extract_pdf(data: bytes) -> tuple[str, str]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return _nonempty("\n\n".join(parts))


def extract_saved(filename: str, data: bytes) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            return _extract_pdf(data)
        except Exception as exc:
            return (str(exc), "failed")
    if suffix in {".hwp", ".hwpx"}:
        return ("", "pending_whale")
    return ("unsupported", "failed")


def aggregate_status(statuses: list[str]) -> str:
    if not statuses:
        return "empty"
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "pending_whale" for status in statuses):
        return "pending_whale"
    if any(status == "ok" for status in statuses):
        return "ok"
    return "empty"


def attachment_filename(name: str, file_sn: str, used: set[str]) -> str:
    cleaned = Path(name.replace("\\", "/")).name.strip()
    cleaned = _INVALID_NAME.sub("_", cleaned).replace("\x00", "")
    if not cleaned or cleaned in {".", ".."}:
        cleaned = f"attachment-{file_sn}"
    if cleaned not in used:
        used.add(cleaned)
        return cleaned
    stem = Path(cleaned).stem
    suffix = Path(cleaned).suffix
    candidate = f"{stem}-{file_sn}{suffix}"
    number = 2
    while candidate in used:
        candidate = f"{stem}-{file_sn}-{number}{suffix}"
        number += 1
    used.add(candidate)
    return candidate


def compose_item(
    row: ListRow,
    detail: DetailPage,
    sections: list[tuple[AttachmentRef, str, str, str]],
    fetched_at: str,
) -> str:
    reply_date = resolve_reply_date(
        row.title,
        f"{detail.subject}\n{detail.notice}",
        row.published_date or detail.registered_date,
    )
    attachments = []
    for ref, filename, _text, status in sections:
        attachments.append(
            {
                "name": filename,
                "atch_file_id": ref.atch_file_id,
                "file_sn": ref.file_sn,
                "extract_status": status,
            }
        )
    meta = {
        "board": row.board,
        "menu_no": row.menu_no,
        "ntt_id": row.ntt_id,
        "number": row.number,
        "title": row.title,
        "department": row.department or detail.department or "",
        "standards": list(row.standards),
        "reply_date": reply_date,
        "published_date": row.published_date,
        "page_url": page_url(row.board, row.ntt_id, row.menu_no),
        "attachments": attachments,
        "fetched_at": fetched_at,
        "extract_status": aggregate_status([item["extract_status"] for item in attachments]),
    }
    dumped = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    lines = ["---", dumped, "---", "", "## 상세 안내", "", detail.notice.strip() or "(없음)", ""]
    for _ref, filename, text, status in sections:
        lines.extend([f"## 첨부: {filename}", ""])
        if status == "pending_whale":
            lines.extend(["pending_whale", "Whale 변환 대기", ""])
        elif status == "ok" and text.strip():
            lines.extend([text.rstrip(), ""])
        elif status == "failed":
            lines.extend([f"failed: {text.strip() or 'failed'}", ""])
        else:
            lines.extend(["empty", ""])
    return "\n".join(lines).rstrip() + "\n"


def read_meta(directory: Path) -> dict | None:
    item = directory / "item.md"
    if not item.is_file():
        return None
    text = item.read_text(encoding="utf-8")
    if not text.startswith("---"):
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
    if status in {"ok", "pending_whale"} and files_ok:
        return False
    if not files_ok:
        return True
    return retry_failed and status in {"failed", "empty"}


def append_manifest(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _manifest_record(row: ListRow, **overrides) -> dict:
    record = {
        "board": row.board,
        "ntt_id": row.ntt_id,
        "menu_no": row.menu_no,
        "number": row.number,
        "title": row.title,
        "reply_date": resolve_reply_date(row.title, "", row.published_date),
        "published_date": row.published_date,
        "extract_status": "failed",
        "path": None,
        "error": None,
    }
    record.update(overrides)
    return record


def crawl_archive(
    archive: Path,
    *,
    boards: list[str],
    fetch_list,
    fetch_detail,
    fetch_file,
    delay: float = 0.3,
    limit: int | None = None,
    retry_failed: bool = False,
    sleep=time.sleep,
    now=None,
) -> dict[str, int]:
    archive.mkdir(parents=True, exist_ok=True)
    counts = {"saved": 0, "skipped": 0, "failed": 0}
    seen: set[tuple[str, str]] = set()
    attempts = 0
    first_http = True

    def call(func, *args):
        nonlocal first_http
        if not first_http and delay:
            sleep(delay)
        first_http = False
        return func(*args)

    def moment() -> str:
        current = now() if now else datetime.now().astimezone()
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current.isoformat()

    for board in boards:
        if board not in BOARD_MENU:
            continue
        menu_no = BOARD_MENU[board]
        page = 1
        while True:
            if limit is not None and attempts >= limit:
                return counts
            html = call(fetch_list, board, menu_no, page)
            rows = [row for row in parse_list_page(html) if row.board == board]
            if not rows:
                break
            for row in rows:
                key = (row.board, row.ntt_id)
                if key in seen:
                    continue
                seen.add(key)
                directory = archive / row.board / row.ntt_id
                if not should_attempt(directory, retry_failed):
                    counts["skipped"] += 1
                    continue
                if limit is not None and attempts >= limit:
                    return counts
                attempts += 1
                try:
                    detail = parse_detail_page(call(fetch_detail, row.board, row.ntt_id, row.menu_no))
                    refs = stored_attachments(detail.attachments or row.attachments)
                    directory.mkdir(parents=True, exist_ok=True)
                    used: set[str] = set()
                    downloaded: list[tuple[str, AttachmentRef, bytes | None]] = []
                    for ref in refs:
                        filename = attachment_filename(ref.name, ref.file_sn, used)
                        path = directory / filename
                        if path.is_file():
                            downloaded.append((filename, ref, None))
                        else:
                            payload = call(
                                fetch_file,
                                ref.menu_no or row.menu_no,
                                ref.atch_file_id,
                                ref.file_sn,
                            )
                            downloaded.append((filename, ref, payload))
                    sections = []
                    for filename, ref, payload in downloaded:
                        path = directory / filename
                        if payload is not None:
                            path.write_bytes(payload)
                        data = path.read_bytes() if path.is_file() else b""
                        text, status = extract_saved(filename, data)
                        sections.append((ref, filename, text, status))
                    item = compose_item(row, detail, sections, moment())
                    (directory / "item.md").write_text(item, encoding="utf-8")
                    meta = read_meta(directory) or {}
                    append_manifest(
                        archive / "manifest.jsonl",
                        _manifest_record(
                            row,
                            reply_date=meta.get("reply_date"),
                            published_date=row.published_date,
                            extract_status=meta.get("extract_status", "failed"),
                            path=f"{row.board}/{row.ntt_id}/item.md",
                            error=None,
                        ),
                    )
                    counts["saved"] += 1
                except Exception as exc:
                    append_manifest(
                        archive / "manifest.jsonl",
                        _manifest_record(row, error=str(exc)),
                    )
                    counts["failed"] += 1
                if limit is not None and attempts >= limit:
                    return counts
            page += 1
    return counts


def default_archive() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "fss-replies"


def default_raw_dest() -> Path:
    return Path(r"C:\dev\obsidian-vault\raw\fss-replies")


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def _response_text(response) -> str:
    encoding = getattr(response, "encoding", None) or "utf-8"
    if str(encoding).lower() == "iso-8859-1":
        response.encoding = getattr(response, "apparent_encoding", None) or "utf-8"
    return response.text


def http_fetch_list(session, board: str, menu_no: str, page: int) -> str:
    response = session.get(
        f"{ORIGIN}/fss/bbs/{board}/list.do",
        params={"menuNo": menu_no, "pageIndex": page},
        timeout=30,
    )
    response.raise_for_status()
    return _response_text(response)


def http_fetch_detail(session, board: str, ntt_id: str, menu_no: str) -> str:
    response = session.get(
        f"{ORIGIN}/fss/bbs/{board}/view.do",
        params={"nttId": ntt_id, "menuNo": menu_no},
        timeout=30,
    )
    response.raise_for_status()
    return _response_text(response)


def http_fetch_file(session, menu_no: str, atch_file_id: str, file_sn: str) -> bytes:
    response = session.get(
        f"{ORIGIN}/fss/cmmn/file/fileDown.do",
        params={
            "menuNo": menu_no,
            "atchFileId": atch_file_id,
            "fileSn": file_sn,
            "bbsId": "",
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def copy_archive_markdown(archive: Path, dest: Path) -> tuple[int, int]:
    copied = 0
    skipped = 0
    if not archive.is_dir():
        return copied, skipped
    dest.mkdir(parents=True, exist_ok=True)
    for item in sorted(archive.glob("*/*/item.md")):
        board = item.parent.parent.name
        ntt_id = item.parent.name
        target_dir = dest / board
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{ntt_id}.md"
        if target.exists():
            skipped += 1
            continue
        target.write_bytes(item.read_bytes())
        copied += 1
    return copied, skipped
