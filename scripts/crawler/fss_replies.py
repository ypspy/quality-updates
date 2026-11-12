# -*- coding: utf-8 -*-
"""금융감독원 질의회신 요약 두 게시판을 항목 폴더로 보관한다.

KASB 질의회신 아카이브와 같은 저장 방식이다. 그 모듈을 import하지 않는다.
다운로드 주소와 쿼리 이름은 운영자가 저장한 상세 HTML의 fileDown.do 링크를 따른다.
목록 관련기준서가 비어 있으면 상세 페이지 값을 쓰고, 둘 다 없으면 제목·첨부명·상세 안내에서 추론한다.
맨몸 폴백만 있는 항목은 추출된 첨부 본문의 구체 인용으로 바꿀 수 있다.
수집 직후의 HWP/HWPX는 pending_whale이고, 본문은 extract_local이 오프라인으로 뽑는다.
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
import yaml
from bs4 import BeautifulSoup

from . import fss_hwp_text

html_to_markdown = fss_hwp_text.html_to_markdown
hwpx_to_text = fss_hwp_text.hwpx_to_text
hwp5html_command = fss_hwp_text.hwp5html_command
hwp_file_to_html = fss_hwp_text.hwp_file_to_html
HwpConvertError = fss_hwp_text.HwpConvertError

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
    standards: tuple[str, ...] = ()


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


def _labeled_standards(view) -> tuple[str, ...]:
    for dt in view.find_all("dt"):
        if dt.get_text(strip=True) == "관련기준서":
            dd = dt.find_next("dd")
            if dd is None:
                return ()
            return tuple(_standard_names(dd))
    return ()


_BARE_FRAMEWORKS = {"K-IFRS", "한국채택국제회계기준"}
_BOILERPLATE = re.compile(
    r"일반\s*기업\s*회계기준\s*질의회신요약을\s*게시하오니"
    r"|일반\s*기업\s*회계기준\s*도입에\s*따른\s*기존\s*질의회신\s*정비작업"
)
_PREFIX = re.compile(r"^\s*[（(]\s*(?:일반\s*기업\s*회계기준|일반기준)\s*[）)]")
_PAREN = r"(?:\s*[（(][^）)]+[）)])?"
_CITATION = re.compile(
    r"일반\s*기업\s*회계기준\s*제\s*\d+\s*장"
    + _PAREN
    + r"|기업회계기준서\s*제\s*\d+\s*호"
    + _PAREN
    + r"|기업회계기준\s*등에\s*관한\s*해석\s*\d+\s*[-‐－–—]\s*\d+"
    + r"|(?:(?<![A-Za-z0-9])K\s*[-‐－]\s*IFRS|한국채택국제회계기준)\s*제\s*\d+\s*호"
    + r"|중소기업\s*회계처리\s*특례"
    + r"|중소기업\s*회계기준(?!서)"
    + r"|(?:일반\s*기업\s*회계기준\s+|기업회계기준서\s+"
    + r"|(?:(?<![A-Za-z0-9])K\s*[-‐－]\s*IFRS|한국채택국제회계기준)\s+)?"
    + r"실무\s*지침(?:\s*제\s*\d+\s*호)?"
    + _PAREN
    + r"|(?<![A-Za-z0-9])K\s*[-‐－]\s*IFRS(?!\s*(?:도입|질의회신))"
    + r"|한국채택국제회계기준"
)


def _norm_space(text: str) -> str:
    return " ".join(text.split())


def _prepare_citation_text(text: str) -> str:
    cleaned = (text or "").replace("\u00a0", " ").replace("\u3000", " ")
    return _BOILERPLATE.sub(" ", cleaned)


def _paren_title(raw: str) -> str | None:
    match = re.search(r"[（(]\s*([^）)]+?)\s*[）)]", raw)
    if not match:
        return None
    title = _norm_space(match.group(1))
    return title or None


def _canonicalize_citation(raw: str) -> str:
    text = _norm_space(raw)
    chapter = re.fullmatch(
        r"일반\s*기업\s*회계기준\s*제\s*(\d+)\s*장(?:\s*[（(]\s*[^）)]+?\s*[）)])?",
        text,
    )
    if chapter:
        base = f"일반기업회계기준 제{chapter.group(1)}장"
        title = _paren_title(text)
        return f"{base} ({title})" if title else base
    statement = re.fullmatch(
        r"기업회계기준서\s*제\s*(\d+)\s*호(?:\s*[（(]\s*[^）)]+?\s*[）)])?",
        text,
    )
    if statement:
        base = f"기업회계기준서 제{statement.group(1)}호"
        title = _paren_title(text)
        return f"{base}({title})" if title else base
    interpretation = re.fullmatch(
        r"기업회계기준\s*등에\s*관한\s*해석\s*(\d+)\s*[-‐－–—]\s*(\d+)",
        text,
    )
    if interpretation:
        return f"기업회계기준 등에 관한 해석 {interpretation.group(1)}-{interpretation.group(2)}"
    numbered = re.fullmatch(
        r"(K\s*[-‐－]\s*IFRS|한국채택국제회계기준)\s*제\s*(\d+)\s*호",
        text,
    )
    if numbered:
        name = "K-IFRS" if "IFRS" in numbered.group(1).upper() else "한국채택국제회계기준"
        return f"{name} 제{numbered.group(2)}호"
    if re.fullmatch(r"중소기업\s*회계처리\s*특례", text):
        return "중소기업회계처리 특례"
    if re.fullmatch(r"중소기업\s*회계기준", text):
        return text
    guide = re.fullmatch(
        r"(?:(일반\s*기업\s*회계기준|기업회계기준서|K\s*[-‐－]\s*IFRS|한국채택국제회계기준)\s+)?"
        r"실무\s*지침(?:\s*제\s*(\d+)\s*호)?(?:\s*[（(]\s*[^）)]+?\s*[）)])?",
        text,
    )
    if guide:
        prefix = ""
        raw_prefix = guide.group(1) or ""
        if raw_prefix:
            if "IFRS" in raw_prefix.upper():
                prefix = "K-IFRS "
            elif "한국채택" in raw_prefix:
                prefix = "한국채택국제회계기준 "
            elif "기준서" in raw_prefix:
                prefix = "기업회계기준서 "
            else:
                prefix = "일반기업회계기준 "
        base = f"{prefix}실무지침"
        if guide.group(2):
            base += f" 제{guide.group(2)}호"
        title = _paren_title(text)
        return f"{base}({title})" if title else base
    if re.fullmatch(r"K\s*[-‐－]\s*IFRS", text):
        return "K-IFRS"
    if text.replace(" ", "") == "한국채택국제회계기준":
        return "한국채택국제회계기준"
    return text


def _citations_in(text: str, *, attachment: bool) -> list[str]:
    cleaned = _prepare_citation_text(text)
    found: list[str] = []
    if attachment and _PREFIX.match(cleaned):
        found.append("일반기업회계기준")
    for match in _CITATION.finditer(cleaned):
        value = _canonicalize_citation(match.group(0))
        if value and value not in found:
            found.append(value)
    return found


def infer_standards(
    board: str,
    title: str,
    attachment_names,
    notice: str,
    body_text: str = "",
) -> list[str]:
    """제목, 첨부 파일명, 상세 안내, 선택적 첨부 본문에서 기준명을 고른다.

    네트워크와 첨부 바이트는 쓰지 않는다. 문단 번호는 항목으로 넣지 않는다.
    장·호처럼 구체적인 인용이 없고 게시판이 B0000133이면 일반기업회계기준을 넣는다.
    ``K-IFRS 도입``, ``유사한 K-IFRS 질의회신``만으로는 bare K-IFRS를 넣지 않는다.
    """
    found: list[str] = []
    sources = [(title or "", False)]
    for name in attachment_names or []:
        sources.append((name or "", True))
    sources.append((notice or "", False))
    if body_text:
        sources.append((body_text, False))
    for text, is_attachment in sources:
        for value in _citations_in(text, attachment=is_attachment):
            if value not in found:
                found.append(value)
    specific = [item for item in found if item not in _BARE_FRAMEWORKS]
    if board == "B0000133" and not specific and "일반기업회계기준" not in found:
        found.append("일반기업회계기준")
    return _drop_bare_framework_when_numbered(found)


def _drop_bare_framework_when_numbered(found: list[str]) -> list[str]:
    """번호 있는 K-IFRS·한국채택국제회계기준이 있으면 맨몸 이름은 뺀다."""
    has_numbered = any(re.match(r"^(?:K-IFRS|한국채택국제회계기준) 제\d+호$", item) for item in found)
    if not has_numbered:
        return found
    return [item for item in found if item not in _BARE_FRAMEWORKS]


def _present_standards(values) -> list[str]:
    return [str(item).strip() for item in (values or []) if str(item).strip()]


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
        standards=_labeled_standards(view),
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


_PARSED_ATTACHMENT = {"ok", "hwp_parsed", "hwpx_parsed"}


def aggregate_status(statuses: list[str]) -> str:
    if not statuses:
        return "empty"
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "pending_whale" for status in statuses):
        return "pending_whale"
    if any(status in _PARSED_ATTACHMENT for status in statuses):
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
    standards = _present_standards(row.standards)
    if not standards:
        standards = _present_standards(detail.standards)
    if not standards:
        standards = infer_standards(
            row.board,
            row.title,
            [filename for _ref, filename, _text, _status in sections],
            detail.notice,
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
        "standards": standards,
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
        elif status in _PARSED_ATTACHMENT and text.strip():
            lines.extend([text.rstrip(), ""])
        elif status == "failed":
            lines.extend([f"failed: {text.strip() or 'failed'}", ""])
        else:
            lines.extend(["empty", ""])
    return "\n".join(lines).rstrip() + "\n"


def read_meta_file(path: Path) -> dict | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
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


def read_meta(directory: Path) -> dict | None:
    return read_meta_file(directory / "item.md")


def _split_item(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ValueError("item.md missing front matter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("item.md missing front matter")
    meta = yaml.safe_load(parts[1]) or {}
    if not isinstance(meta, dict):
        raise ValueError("item.md front matter is not a mapping")
    return meta, parts[2]


def _notice_text(body: str) -> str:
    if "## 상세 안내" not in body:
        return ""
    rest = body.split("## 상세 안내", 1)[1].lstrip("\n")
    if "## 첨부:" in rest:
        rest = rest.split("## 첨부:", 1)[0]
    notice = rest.strip()
    if notice == "(없음)":
        return ""
    return notice


def _attachment_names(meta: dict, body: str) -> list[str]:
    names = []
    for item in meta.get("attachments") or []:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    if names:
        return names
    return [line[len("## 첨부: ") :].strip() for line in body.splitlines() if line.startswith("## 첨부: ")]


def _standards_yaml(standards: list[str]) -> str:
    dumped = yaml.safe_dump(
        {"standards": list(standards)},
        allow_unicode=True,
        sort_keys=False,
        width=10**6,
    )
    return dumped.strip() + "\n"


def _replace_standards_in_front(front: str, dumped: str) -> str:
    lines = front.splitlines(keepends=True)
    start = None
    for index, line in enumerate(lines):
        if line.startswith("standards:"):
            start = index
            break
    block = dumped if dumped.endswith("\n") else dumped + "\n"
    if start is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        lines.append(block)
        return "".join(lines)
    end = start + 1
    if not re.match(r"^standards:\s*\[", lines[start]):
        while end < len(lines) and re.match(r"^[ \t]*-[ \t]?", lines[end]):
            end += 1
    return "".join(lines[:start]) + block + "".join(lines[end:])


def _rewrite_standards(text: str, standards: list[str]) -> str:
    if not text.startswith("---"):
        raise ValueError("item.md missing front matter")
    close = text.find("\n---", 3)
    if close < 0:
        raise ValueError("item.md missing front matter end")
    front = text[4 : close + 1]
    rewritten = _replace_standards_in_front(front, _standards_yaml(standards))
    if not rewritten.endswith("\n"):
        rewritten += "\n"
    return "---\n" + rewritten + text[close + 1 :]


def _json_value(value):
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()
    return value


def _manifest_line(old_line: str | None, standards: list[str], meta: dict) -> str:
    payload = json.dumps(standards, ensure_ascii=False)
    if old_line:
        text = old_line.rstrip("\n")
        record = json.loads(text)
        if "standards" in record:
            record["standards"] = standards
            return json.dumps(record, ensure_ascii=False) + "\n"
        if not text.endswith("}"):
            raise ValueError("manifest line is not an object")
        return text[:-1] + ', "standards": ' + payload + "}\n"
    record = {
        "board": meta.get("board"),
        "ntt_id": _json_value(meta.get("ntt_id")),
        "menu_no": _json_value(meta.get("menu_no")),
        "number": _json_value(meta.get("number")),
        "title": meta.get("title"),
        "reply_date": _json_value(meta.get("reply_date")),
        "published_date": _json_value(meta.get("published_date")),
        "extract_status": meta.get("extract_status"),
        "path": f"{meta.get('board')}/{meta.get('ntt_id')}/item.md",
        "error": None,
        "standards": standards,
    }
    return json.dumps(record, ensure_ascii=False) + "\n"


_BARE_LABELS = _BARE_FRAMEWORKS | {"일반기업회계기준"}


def _is_bare_fallback(standards: list[str]) -> bool:
    return bool(standards) and all(item in _BARE_LABELS for item in standards)


def _normalize_standard_labels(standards: list[str]) -> list[str]:
    """이미 있는 라벨의 표기만 맞추고 순서를 유지한 채 중복을 뺀다."""
    chosen: list[str] = []
    for item in standards:
        value = _canonicalize_citation(str(item))
        if value and value not in chosen:
            chosen.append(value)
    return chosen


def _choose_body_standards(existing: list[str], inferred: list[str]) -> list[str]:
    """맨몸 폴백만 본문 추론으로 바꾼다. 구체 인용은 그대로 둔다."""
    specific = [item for item in inferred if item not in _BARE_LABELS]
    if specific:
        return inferred
    if inferred and _is_bare_fallback(inferred) and set(inferred) < set(existing):
        return inferred
    return existing


def _extracted_attachment_text(body: str) -> str:
    parts = []
    for chunk in re.split(r"\n(?=## 첨부: )", body):
        stripped = chunk.lstrip("\n")
        if not stripped.startswith("## 첨부:"):
            continue
        payload = "\n".join(stripped.splitlines()[1:]).strip()
        if not payload or payload == "empty" or payload.startswith("pending_whale") or payload.startswith("failed:"):
            continue
        parts.append(payload)
    return "\n\n".join(parts)


def refresh_standards(archive: Path, *, from_body: bool = False) -> dict:
    """item.md의 standards와 manifest.jsonl만 오프라인으로 다시 쓴다.

    첨부 파일, 본문, extract_status, fetched_at은 바꾸지 않는다.
    이미 채워진 구체 standards는 추론으로 덮어쓰지 않는다.
    라벨 표기만 _canonicalize_citation으로 맞춘다.
    from_body 일 때만, 맨몸 폴백은 추출된 첨부 본문의 구체 인용으로 바꾼다.
    """
    if not archive.is_dir():
        return {"updated": 0, "unchanged": 0, "items": 0}
    items = sorted(path for path in archive.glob("*/*/item.md") if path.is_file())
    parsed = []
    for path in items:
        text = path.read_text(encoding="utf-8")
        meta, body = _split_item(text)
        notice = _notice_text(body)
        names = _attachment_names(meta, body)
        existing = _present_standards(meta.get("standards"))
        body_text = _extracted_attachment_text(body) if from_body else ""
        if not existing:
            chosen = infer_standards(
                str(meta.get("board") or ""),
                str(meta.get("title") or ""),
                names,
                notice,
                body_text,
            )
        elif from_body and _is_bare_fallback(existing):
            inferred = infer_standards(
                str(meta.get("board") or ""),
                str(meta.get("title") or ""),
                names,
                notice,
                body_text,
            )
            chosen = _choose_body_standards(existing, inferred)
        else:
            chosen = existing
        chosen = _normalize_standard_labels(chosen)
        parsed.append((path, text, meta, chosen))

    manifest_path = archive / "manifest.jsonl"
    old_lines: dict[tuple[str, str], str] = {}
    order: list[tuple[str, str]] = []
    if manifest_path.is_file():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            key = (str(record.get("board")), str(record.get("ntt_id")))
            if key in old_lines:
                continue
            old_lines[key] = line
            order.append(key)

    by_key = {}
    for path, text, meta, chosen in parsed:
        key = (str(meta.get("board")), str(meta.get("ntt_id")))
        by_key[key] = (path, text, meta, chosen)

    updated = 0
    unchanged = 0
    for path, text, _meta, chosen in parsed:
        original = _present_standards(_split_item(text)[0].get("standards"))
        if original == chosen:
            unchanged += 1
            continue
        path.write_text(_rewrite_standards(text, chosen), encoding="utf-8")
        updated += 1

    seen: set[tuple[str, str]] = set()
    lines = []
    for key in order:
        if key not in by_key or key in seen:
            continue
        seen.add(key)
        _path, _text, meta, chosen = by_key[key]
        lines.append(_manifest_line(old_lines.get(key), chosen, meta))
    for key in sorted(by_key):
        if key in seen:
            continue
        seen.add(key)
        _path, _text, meta, chosen = by_key[key]
        lines.append(_manifest_line(old_lines.get(key), chosen, meta))
    manifest_path.write_text("".join(lines), encoding="utf-8")
    return {"updated": updated, "unchanged": unchanged, "items": len(parsed)}


def should_attempt(directory: Path, retry_failed: bool) -> bool:
    meta = read_meta(directory)
    if meta is None:
        return True
    status = meta.get("extract_status")
    files_ok = all((directory / item["name"]).is_file() for item in meta.get("attachments") or [])
    if status in {"ok", "pending_whale", "hwp_parsed", "hwpx_parsed"} and files_ok:
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


_HWP_STATUS = {".hwp": "hwp_parsed", ".hwpx": "hwpx_parsed"}


def _replace_attachment_section(body: str, filename: str, payload: str) -> str:
    marker = f"## 첨부: {filename}"
    start = body.find(marker)
    if start < 0:
        return body
    next_heading = body.find("\n## 첨부:", start + len(marker))
    end = next_heading if next_heading >= 0 else len(body)
    block = f"{marker}\n\n{payload.strip()}\n"
    return body[:start] + block + body[end:]


_TEMP_PATH = re.compile(r"/tmp/(?:tmp|fss-hwp-)[A-Za-z0-9_.-]*")


def _short_error_message(exc: BaseException | str) -> str:
    """트레이스백과 임시 경로를 빼고, 실행마다 같은 한 줄만 남긴다."""
    if isinstance(exc, str):
        return " ".join(exc.split()) or "failed"
    if isinstance(exc, subprocess.TimeoutExpired):
        return "TimeoutExpired: timed out"
    text = _TEMP_PATH.sub("", str(exc) or "")
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
        return exc.__class__.__name__
    if "Error" not in chosen and "Exception" not in chosen:
        return f"{exc.__class__.__name__}: {chosen}"
    return chosen


def _pending_error(exc: BaseException | str) -> str:
    return f"pending_whale\nWhale 변환 대기\n오류: {_short_error_message(exc)}"


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
            indent = line[: len(line) - len(line.lstrip(" \t"))]
            lines[index] = f"{indent}extract_status: {attachment_statuses[attachment_index]}"
            attachment_index += 1
        elif (not in_attachments) and line.startswith("extract_status:"):
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


def _sync_manifest_extract_status(archive: Path, statuses: dict[tuple[str, str], str]) -> None:
    path = archive / "manifest.jsonl"
    existing = []
    if path.is_file():
        existing = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    seen: set[tuple[str, str]] = set()
    output = []
    for line in existing:
        record = json.loads(line)
        key = (str(record.get("board")), str(record.get("ntt_id")))
        if key in seen:
            continue
        seen.add(key)
        if key in statuses:
            record["extract_status"] = statuses[key]
        output.append(json.dumps(record, ensure_ascii=False))
    for key in sorted(statuses):
        if key in seen:
            continue
        board, ntt_id = key
        output.append(
            json.dumps(
                {
                    "board": board,
                    "ntt_id": ntt_id,
                    "extract_status": statuses[key],
                    "path": f"{board}/{ntt_id}/item.md",
                    "error": None,
                },
                ensure_ascii=False,
            )
        )
    if output or path.is_file():
        path.write_text(("\n".join(output) + "\n") if output else "", encoding="utf-8")


def extract_local(archive: Path, *, timeout: float = 90, hwp_to_html=None) -> dict:
    """pending_whale HWP/HWPX만 로컬 파일에서 추출한다. 네트워크를 쓰지 않는다.

    성공한 .hwp 는 hwp_parsed, .hwpx 는 hwpx_parsed 다. 항목은 첨부가 모두
    파싱되면 ok 다. 실패·시간 초과·파일 없음은 pending_whale 을 유지한다.
    원본 첨부는 지우거나 옮기지 않는다. 이미 파싱한 본문은 다시 쓰지 않는다.
    """
    counts = {"parsed": 0, "failed": 0, "missing": 0, "skipped": 0}
    if not archive.is_dir():
        return counts
    convert = hwp_to_html or hwp_file_to_html
    items = sorted(path for path in archive.glob("*/*/item.md") if path.is_file())
    statuses: dict[tuple[str, str], str] = {}
    for path in items:
        text = path.read_text(encoding="utf-8")
        try:
            meta, body = _split_item(text)
        except ValueError:
            continue
        attachments = [item for item in (meta.get("attachments") or []) if isinstance(item, dict)]
        new_statuses: list[str] = []
        changed = False
        for attachment in attachments:
            status = str(attachment.get("extract_status") or "")
            name = str(attachment.get("name") or "")
            suffix = Path(name).suffix.lower()
            if status in _PARSED_ATTACHMENT:
                counts["skipped"] += 1
                new_statuses.append(status)
                continue
            if status != "pending_whale" or suffix not in _HWP_STATUS:
                new_statuses.append(status or "failed")
                continue
            file_path = path.parent / name
            if not file_path.is_file():
                counts["missing"] += 1
                new_statuses.append("pending_whale")
                continue
            try:
                if suffix == ".hwpx":
                    extracted = hwpx_to_text(file_path.read_bytes())
                else:
                    extracted = html_to_markdown(convert(file_path, timeout))
            except (subprocess.TimeoutExpired, HwpConvertError, OSError) as exc:
                counts["failed"] += 1
                body = _replace_attachment_section(body, name, _pending_error(exc))
                new_statuses.append("pending_whale")
                changed = True
                continue
            if not str(extracted).strip():
                counts["failed"] += 1
                body = _replace_attachment_section(body, name, _pending_error("empty"))
                new_statuses.append("pending_whale")
                changed = True
                continue
            body = _replace_attachment_section(body, name, str(extracted).strip())
            new_statuses.append(_HWP_STATUS[suffix])
            counts["parsed"] += 1
            changed = True
        item_status = aggregate_status(new_statuses) if new_statuses else str(meta.get("extract_status") or "empty")
        previous = [str(item.get("extract_status") or "") for item in attachments]
        if changed or previous != new_statuses or str(meta.get("extract_status") or "") != item_status:
            path.write_text(_write_item(text, body, new_statuses, item_status), encoding="utf-8")
        key = (str(meta.get("board") or path.parent.parent.name), str(meta.get("ntt_id") or path.parent.name))
        statuses[key] = item_status
    if items:
        _sync_manifest_extract_status(archive, statuses)
        refresh_standards(archive, from_body=True)
    return counts


def _pending_target_needs_source(source: Path, target: Path) -> bool:
    target_meta = read_meta_file(target)
    source_meta = read_meta_file(source)
    if not isinstance(target_meta, dict) or not isinstance(source_meta, dict):
        return False
    if target_meta.get("extract_status") != "pending_whale":
        return False
    return source_meta.get("extract_status") != "pending_whale"


_REV_RE = re.compile(r"[A-Za-z0-9._-]+")


def _count_write(target: Path, payload: bytes) -> str:
    if target.is_file() and target.read_bytes() == payload:
        return "skipped"
    target.parent.mkdir(parents=True, exist_ok=True)
    existed = target.is_file()
    target.write_bytes(payload)
    return "updated" if existed else "copied"


def copy_archive_markdown(
    archive: Path,
    dest: Path,
    *,
    update_pending: bool = False,
    sibling_rev: str | None = None,
) -> tuple[int, int, int]:
    """item.md만 dest로 복사한다. 첨부는 복사하지 않는다.

    기본은 대상이 있으면 건너뛴다. update_pending 일 때는 대상 extract_status 가
    pending_whale 이고 소스가 더 이상 pending_whale 이 아닐 때만 덮어쓴다.
    대상만 있는 파일은 지우지 않는다.

    sibling_rev 가 있으면 ``{board}/{nttId}.{rev}.md`` 와 ``manifest-{rev}.jsonl`` 만
    쓴다. 원래 ``{nttId}.md`` 와 기존 manifest 는 쓰지 않는다.
    """
    if sibling_rev is not None and update_pending:
        raise ValueError("sibling-rev cannot be combined with update-pending")
    copied = 0
    updated = 0
    skipped = 0
    if not archive.is_dir():
        return copied, updated, skipped
    if sibling_rev is not None:
        if not _REV_RE.fullmatch(sibling_rev):
            raise ValueError("invalid sibling rev")
        counts = {"copied": 0, "updated": 0, "skipped": 0}
        dest.mkdir(parents=True, exist_ok=True)
        for item in sorted(path for path in archive.glob("*/*/item.md") if path.is_file()):
            target = dest / item.parent.parent.name / f"{item.parent.name}.{sibling_rev}.md"
            counts[_count_write(target, item.read_bytes())] += 1
        manifest = archive / "manifest.jsonl"
        if manifest.is_file():
            counts[_count_write(dest / f"manifest-{sibling_rev}.jsonl", manifest.read_bytes())] += 1
        return counts["copied"], counts["updated"], counts["skipped"]
    dest.mkdir(parents=True, exist_ok=True)
    for item in sorted(archive.glob("*/*/item.md")):
        board = item.parent.parent.name
        ntt_id = item.parent.name
        target_dir = dest / board
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{ntt_id}.md"
        if not target.exists():
            target.write_bytes(item.read_bytes())
            copied += 1
            continue
        if update_pending and _pending_target_needs_source(item, target):
            target.write_bytes(item.read_bytes())
            updated += 1
            continue
        skipped += 1
    return copied, updated, skipped
