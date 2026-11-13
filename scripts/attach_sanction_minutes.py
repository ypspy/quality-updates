from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import time
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

LINK_RE = re.compile(r"^- \((\d{2})-(\d{2})-(\d{2})\) \[(.+?)\]\((https?://[^\)]+)\)")
_YEAR_QUOTES = "'\u2018\u2019"
KEY_RE = re.compile(
    rf"제\s*(\d+)\s*차\s*(?:임시|서면)?\s*(증권선물위원회|금융위원회)"
    rf"[^()\n]{{0,30}}?"
    rf"\(\s*[{_YEAR_QUOTES}]\s*(\d{{2}})"
)
_COMMITTEE_RE = "금융감독위원회|금융위원회|증권선물의원회|증권선물위원회|증선위"
_DECISION_WITH_CHA = re.compile(
    rf"(?:(?P<year>\d{{4}})\s*년\s*도?\s*)?"
    rf"제\s*(?P<number>\d+)\s*차\s*"
    rf"(?:임시|서면)?\s*"
    rf"(?P<committee>{_COMMITTEE_RE})"
)
_DECISION_GLUED = re.compile(
    rf"(?:(?P<year>\d{{4}})\s*년\s*도?\s*)?"
    rf"제\s*(?P<number>\d+)\s*"
    rf"(?P<committee>{_COMMITTEE_RE})"
)
_TITLE_YEAR = re.compile(r"(\d{4})\s*년\s*도?")
_CLOSED_TITLE = re.compile(r"비공개\s*기간|비공개\s*사유")
# 네 자리는 년 또는 - . _ 구분자일 때만 연도다. 2000억처럼 수량에 붙은 숫자는 연도가 아니다.
_FOUR_YEAR = re.compile(
    r"(?<!\d)((?:19|20)\d{2})\s*년"
    r"|(?<!\d)((?:19|20)\d{2})(?=[-._])"
    r"|(?<=[-._])((?:19|20)\d{2})(?!\d)"
)
# 두 자리는 시작·하이픈·밑줄·점 뒤의 09년·02년만 연도다. '최근 10년'은 빼다.
_TWO_YEAR = re.compile(r"(?:^|[-._])(\d{2})년")
POST_TITLE_WORDS = ("의사록", "안건", "의결서")
# www 없는 호스트가 TLS에 더 안정적이다. 정규 경로와 백필이 같은 출처를 쓴다.
FSC_ORIGIN = "https://fsc.go.kr"
BOARD_URLS = {
    "금융위": FSC_ORIGIN + "/no020101",
    "증선위": FSC_ORIGIN + "/no020102",
}
BOARDS = (BOARD_URLS["금융위"], BOARD_URLS["증선위"])
# 금융위 2001-01-26, 증선위만 돌릴 때 2001-02-08.
FSC_SINCE = {"금융위": date(2001, 1, 26), "증선위": date(2001, 2, 8)}
# TLS EOF·연결 시간 초과·5xx는 최대 5회, 지수 백오프 1초부터 상한 30초.
# 403은 1초 간격으로 1회만 더 시도하고 실패 목록에 남긴다.
HTTP_RETRY_ATTEMPTS = 5
HTTP_BACKOFF_BASE = 1.0
HTTP_BACKOFF_CAP = 30.0
HTTP_FORBIDDEN_RETRIES = 1
HTTP_FORBIDDEN_DELAY = 1.0
_PENDING_SUFFIXES = (".hwp", ".hwpx", ".xls", ".xlsx")
QUARTER_NAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})\.md$")
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
_request_delay = 1.0
_requests_made = 0
MEETING_DATE_RE = re.compile(
    rf"\(\s*[{_YEAR_QUOTES}]?\s*(\d{{2}})\.(\d{{1,2}})\.(\d{{1,2}})\."
)
UNPUBLISHED_BULLET = "- 분기중 미보도 항목"


def _resolution_item_boundary(raw: str) -> bool:
    stripped = raw.strip()
    return (
        raw.startswith("####")
        or stripped.startswith("### ")
        or stripped.startswith("## ")
        or stripped == UNPUBLISHED_BULLET
    )


AUDIT_TERMS = ("감리", "회계법인", "감사인")
INVESTIGATION_PHRASES = ("조사감리", "조사결과")
# 시장질서교란 의결서·안건은 불공정거래와 같이 보존하지 않는다.
EXCLUDED_TERMS = ("불공정거래", "시세조종", "미공개정보", "개정", "규정", "시장질서교란")
_MASK_CHARS = set("○◯〇△▲▽▼◇◆■□●★＊*")
_DOTS = "·ㆍ･‧"


@dataclass(frozen=True)
class DecisionPost:
    year: int
    committee: str
    kind: str
    number: int
    pdf_url: str
    zip_urls: list[str]
    title: str = ""
    page_url: str = ""


@dataclass(frozen=True)
class AgendaFile:
    filename: str
    kind: str
    number: int | None
    masked: bool


def meeting_key(text: str) -> tuple[int, str, str, int] | None:
    """제N차 and 증권선물위원회 or 금융위원회, then a parenthetical '26, ‘26, or ’26."""
    matched = KEY_RE.search(text) or KEY_RE.search(re.sub(r"\s+", "", text))
    if not matched:
        return None
    number, committee, year_digits = matched.groups()
    year = 2000 + int(year_digits)
    span = matched.group(0)
    if "임시" in span:
        kind = "임시"
    elif "서면" in span:
        kind = "서면"
    else:
        kind = "정기"
    name = "증선위" if committee == "증권선물위원회" else "금융위"
    return year, name, kind, int(number)


def _coerce_date(value: date | datetime | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip().replace(".", "-")
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def decision_key(
    title: str,
    posted: date | datetime | str | None = None,
) -> tuple[int, str, str, int] | None:
    """회의 키 (연도, 금융위|증선위, 정기|임시|서면, 회차).

    제목의 YYYY년·YYYY년도를 제N차와의 위치와 관계없이 우선하고, 없으면 목록 게시일 연도를 쓴다.
    서면이 있으면 서면, 그다음 임시(임시회의·임시증권선물위원회 포함)면 임시, 아니면 정기다.
    비공개 기간·비공개 사유 안건은 띄어쓰기와 관계없이 회의가 아니므로 None이다.
    """
    if _CLOSED_TITLE.search(title):
        return None
    matched = _DECISION_WITH_CHA.search(title) or _DECISION_GLUED.search(title)
    if matched is None:
        return None
    titled_year = _TITLE_YEAR.search(title)
    if titled_year:
        year = int(titled_year.group(1))
    else:
        posted_date = _coerce_date(posted)
        if posted_date is None:
            return None
        year = posted_date.year
    if "서면" in title:
        kind = "서면"
    elif "임시" in title:
        kind = "임시"
    else:
        kind = "정기"
    committee = matched.group("committee")
    name = "금융위" if committee.startswith("금융") else "증선위"
    return year, name, kind, int(matched.group("number"))


def _year_token(matched: re.Match) -> int:
    for group in matched.groups():
        if group:
            return int(group)
    raise ValueError("year pattern had no digits")


def filename_year_conflict(name: str, meeting_year: int) -> bool:
    """파일명의 연도 표기가 회의 연도와 다르면 True.

    ``2009-``·``2009년``·``-09년``·``02년``은 연도다.
    ``2000억``과 ``최근 10년``처럼 수량에 붙은 숫자는 연도가 아니다.
    """
    for matched in _FOUR_YEAR.finditer(name):
        if _year_token(matched) != meeting_year:
            return True
    for matched in _TWO_YEAR.finditer(name):
        if 2000 + _year_token(matched) != meeting_year:
            return True
    return False


def _filename_rank(name: str) -> tuple[int, int, str]:
    penalty = 1 if ("사본" in name or "[1]" in name) else 0
    return penalty, len(name), name


def select_named_files(
    meeting_year: int,
    files: list[tuple[str, bytes]],
) -> tuple[list[tuple[str, bytes]], list[str]]:
    """연도가 다른 파일은 버리고, 같은 내용 해시는 짧은 이름 하나만 남긴다."""
    notes: list[str] = []
    candidates: list[tuple[str, bytes]] = []
    for name, payload in files:
        if filename_year_conflict(name, meeting_year):
            notes.append(f"year-mismatch {name}")
            continue
        candidates.append((name, payload))
    best: dict[str, tuple[str, bytes]] = {}
    order: list[str] = []
    for name, payload in candidates:
        digest = hashlib.sha256(payload).hexdigest()
        current = best.get(digest)
        if current is None:
            best[digest] = (name, payload)
            order.append(digest)
            continue
        if _filename_rank(name) < _filename_rank(current[0]):
            notes.append(f"duplicate {current[0]}")
            best[digest] = (name, payload)
        else:
            notes.append(f"duplicate {name}")
    return [best[digest] for digest in order], notes


def dedupe_payloads(
    rows: list[tuple[str, str, bytes]],
) -> tuple[list[tuple[str, str, bytes]], list[str]]:
    """(kind, filename, payload) 중 같은 해시는 사본·[1]보다 짧은 이름만 남긴다."""
    notes: list[str] = []
    best: dict[str, tuple[str, str, bytes]] = {}
    order: list[str] = []
    for kind, filename, payload in rows:
        digest = hashlib.sha256(payload).hexdigest()
        current = best.get(digest)
        row = (kind, filename, payload)
        if current is None:
            best[digest] = row
            order.append(digest)
            continue
        if _filename_rank(filename) < _filename_rank(current[1]):
            notes.append(f"duplicate {current[1]}")
            best[digest] = row
        else:
            notes.append(f"duplicate {filename}")
    return [best[digest] for digest in order], notes


def is_pending_minutes(name: str) -> bool:
    """PDF가 아닌 의사록. 변환하지 않고 대기 목록에만 남긴다."""
    lowered = name.lower()
    return "의사록" in name and lowered.endswith(_PENDING_SUFFIXES)


def normalize_fsc_url(url: str) -> str:
    """www.fsc.go.kr 요청을 https://fsc.go.kr 로 바꾼다."""
    return re.sub(r"^(https?://)www\.fsc\.go\.kr(?=/|:|$)", r"\1fsc.go.kr", url, count=1)


def absolute_fsc_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return normalize_fsc_url(href)
    if not href.startswith("/"):
        href = "/" + href
    return FSC_ORIGIN + href


def post_id_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]


def board_label(board_url: str) -> str:
    if "/no020101" in board_url:
        return "금융위"
    if "/no020102" in board_url:
        return "증선위"
    return ""


def _backoff_seconds(attempt: int) -> float:
    return min(HTTP_BACKOFF_CAP, HTTP_BACKOFF_BASE * (2 ** (attempt - 1)))


class FetchFailed(Exception):
    """재시도를 마친 뒤의 다운로드·목록 실패."""

    def __init__(self, url: str, http_status: int | None, error: str, attempts: int):
        super().__init__(error)
        self.url = url
        self.http_status = http_status
        self.error = error
        self.attempts = attempts


def _transport_retryable(exc: BaseException) -> bool:
    import requests

    if isinstance(
        exc,
        (
            requests.exceptions.Timeout,
            requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
        ),
    ):
        return True
    text = str(exc)
    return "UNEXPECTED_EOF" in text or "timed out" in text.lower()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _atomic_write_text(path: Path, text: str) -> None:
    """같은 디렉터리의 임시 파일에 쓴 뒤 최종 경로로 교체한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    body = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    _atomic_write_text(path, body)


def clear_failure(path: Path, url: str) -> None:
    """받아 낸 URL의 실패 행을 지운다."""
    if not path.is_file():
        return
    rows = _read_jsonl(path)
    kept = [row for row in rows if row.get("url") != url]
    if len(kept) != len(rows):
        _write_jsonl(path, kept)


def record_failure(path: Path, row: dict) -> None:
    """같은 url은 마지막 결과로 덮어쓴다."""
    rows = [item for item in _read_jsonl(path) if item.get("url") != row.get("url")]
    rows.append(row)
    _write_jsonl(path, rows)


def record_pending(path: Path, row: dict) -> None:
    record_failure(path, row)


def forbidden_urls(path: Path) -> set[str]:
    return {row["url"] for row in _read_jsonl(path) if row.get("http_status") == 403 and row.get("url")}


def _empty_backfill_state() -> dict:
    return {"pages": {}, "posts": []}


def load_backfill_state(path: Path) -> dict:
    if not path.is_file():
        return _empty_backfill_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError, OSError):
        return _empty_backfill_state()
    if not isinstance(data, dict):
        return _empty_backfill_state()
    pages = data.get("pages")
    posts = data.get("posts")
    return {
        "pages": pages if isinstance(pages, dict) else {},
        "posts": posts if isinstance(posts, list) else [],
    }


def save_backfill_state(path: Path, state: dict) -> None:
    _atomic_write_text(
        path,
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _done_ids(state: dict) -> set[str]:
    return {str(item.get("post_id")) for item in state.get("posts", [])}


def _mark_done(state: dict, post_id: str, page: int, board: str, page_url: str) -> None:
    posts = [item for item in state["posts"] if str(item.get("post_id")) != str(post_id)]
    posts.append(
        {"board": board, "page": page, "page_url": page_url, "post_id": str(post_id)}
    )
    posts.sort(key=lambda item: (item["board"], item["page"], item["post_id"]))
    state["posts"] = posts


_REPO_ROOT = Path(__file__).resolve().parent.parent
_README_SOURCE = _REPO_ROOT / "docs" / "project" / "sanctions-downloads-readme.md"


def ensure_sanctions_readme(downloads: Path) -> None:
    """회차 폴더를 만들 때 README가 없으면 문서 원본을 복사한다."""
    target = downloads / "sanctions" / "README.md"
    if target.is_file() or not _README_SOURCE.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_README_SOURCE, target)


def _prune_empty(folder: Path) -> None:
    if not folder.exists():
        return
    for child in sorted(folder.rglob("*"), reverse=True):
        if child.is_dir():
            try:
                child.rmdir()
            except OSError:
                return
    try:
        folder.rmdir()
    except OSError:
        return


def _eligible_block(block: str) -> bool:
    marker = '!!! note "위원 논의"'
    start = block.find(marker)
    if start < 0:
        return True
    body = block[start + len(marker) :]
    next_note = body.find("!!! note")
    if next_note >= 0:
        body = body[:next_note]
    return "미공개" in body


def is_additional_minutes(title: str) -> bool:
    return "의사록(추가" in title or "(추가_" in title or "(추가)" in title


def _minutes_filename(pdf_url: str, key: tuple[int, str, str, int], title: str = "") -> str:
    del pdf_url, key
    return "minutes-추가.pdf" if is_additional_minutes(title) else "minutes.pdf"


def _minutes_marker(key: tuple[int, str, str, int], filename: str) -> str:
    return f"downloads/sanctions/{sanction_folder(key)}/{filename}"


def _meeting_posts(key, posts: list[DecisionPost]) -> list[DecisionPost]:
    return [post for post in posts if (post.year, post.committee, post.kind, post.number) == key]


def _unique_texts(values: list[str]) -> list[str]:
    found: list[str] = []
    for value in values:
        if value and value not in found:
            found.append(value)
    return found


def meeting_source_urls(posts: list[DecisionPost]) -> tuple[str, list[str], list[str]]:
    """Primary page, additional pages, and ZIP URLs with the primary post's ZIP first."""
    primaries = [post for post in posts if not is_additional_minutes(post.title)]
    additions = [post for post in posts if is_additional_minutes(post.title)]
    pages = _unique_texts([post.page_url for post in primaries])
    extra_pages = _unique_texts([post.page_url for post in additions])
    zips = _unique_texts([url for post in primaries for url in post.zip_urls])
    for url in _unique_texts([url for post in additions for url in post.zip_urls]):
        if url not in zips:
            zips.append(url)
    return ", ".join(pages), extra_pages, zips


def minutes_urls_for_key(key, posts: list[DecisionPost]) -> list[str] | None:
    """PDF urls for one meeting. None means two primary minutes, so no marker."""
    group = [post for post in _meeting_posts(key, posts) if post.pdf_url]
    if not group:
        return []
    primaries = [post for post in group if not is_additional_minutes(post.title)]
    extras = [post for post in group if is_additional_minutes(post.title)]
    if len(primaries) > 1:
        return None
    urls: list[str] = []
    for post in primaries + extras:
        if post.pdf_url not in urls:
            urls.append(post.pdf_url)
    return urls


def _title_for_url(key, posts: list[DecisionPost], url: str) -> str:
    matches = [post.title for post in _meeting_posts(key, posts) if post.pdf_url == url and post.title]
    additional = [title for title in matches if is_additional_minutes(title)]
    if additional:
        return additional[0]
    return matches[0] if matches else ""


def select_minutes_pdf(key, posts: list[DecisionPost]) -> str | None:
    found = [
        post.pdf_url
        for post in posts
        if (post.year, post.committee, post.kind, post.number) == key and post.pdf_url
    ]
    if len(found) != 1:
        return None
    return found[0]


def attach_minutes(text: str, posts: list[DecisionPost]) -> tuple[str, list[str]]:
    lines = text.splitlines()
    report: list[str] = []
    in_resolution = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#### "):
            in_resolution = stripped == "#### 제재 의결"
        elif stripped.startswith("### ") or stripped.startswith("## "):
            in_resolution = False
        if in_resolution and (matched := LINK_RE.match(lines[i])):
            block_end = i + 1
            while block_end < len(lines) and not LINK_RE.match(lines[block_end]):
                raw = lines[block_end]
                if _resolution_item_boundary(raw):
                    break
                block_end += 1
            block = "\n".join(lines[i:block_end])
            key = meeting_key(matched.group(4) + "\n" + block)
            if key and not _eligible_block(block):
                report.append(f"skipped discussion {key[0]} {key[1]} {key[2]} {key[3]}")
                i = block_end
                continue
            found = minutes_urls_for_key(key, posts) if key else []
            if key and found is None:
                report.append(f"ambiguous {key[0]} {key[1]} {key[2]} {key[3]}")
            elif key and len(found) == 0:
                report.append(f"unpublished {key[0]} {key[1]} {key[2]} {key[3]}")
            elif key and found:
                names = []
                for url in found:
                    name = _minutes_filename(url, key, _title_for_url(key, posts, url))
                    marker = _minutes_marker(key, name)
                    if marker not in block:
                        names.append(marker)
                if names:
                    lines.insert(i + 1, "")
                    for offset, marker in enumerate(names):
                        lines.insert(i + 2 + offset, f"    <!-- source: pdf|{marker} -->")
                    report.append(f"attached {key[0]} {key[1]} {key[2]} {key[3]}")
                    i = block_end + 1 + len(names)
                    continue
            i = block_end
            continue
        i += 1
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), report


def parse_board_rows(html: str) -> list[tuple[str, str, date | None]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    rows: list[tuple[str, str, date | None]] = []
    for item in soup.select("li > div.inner"):
        subject = item.select_one(".subject a")
        if subject is None or not subject.get("href"):
            continue
        url = absolute_fsc_url(subject["href"]).split("?", 1)[0]
        day = item.select_one(".day")
        posted = _coerce_date(day.get_text(" ", strip=True)) if day else None
        rows.append((subject.get_text(" ", strip=True), url, posted))
    return rows


def parse_decision_list(html: str) -> list[tuple[str, str]]:
    return [(title, url) for title, url, _posted in parse_board_rows(html)]


def detail_attachments(detail_html: str) -> list[tuple[str, str]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(detail_html, "html.parser")
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = anchor.get("href") or ""
        name = anchor.get_text(" ", strip=True)
        if "getFile" not in href:
            continue
        url = absolute_fsc_url(href)
        if url in seen:
            continue
        seen.add(url)
        found.append((name, url))
    return found


def minutes_pdf_urls(detail_html: str) -> list[str]:
    return [
        url
        for name, url in detail_attachments(detail_html)
        if "의사록" in name and name.lower().endswith(".pdf")
    ]


def agenda_zip_urls(detail_html: str) -> list[str]:
    return [url for name, url in detail_attachments(detail_html) if name.lower().endswith(".zip")]


def zip_entry_names(data: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return [_zip_name(info) for info in archive.infolist() if not info.is_dir()]


def _zip_name(info: zipfile.ZipInfo) -> str:
    name = info.filename.replace("\\", "/").rsplit("/", 1)[-1]
    if info.flag_bits & 0x800:
        return name
    try:
        return name.encode("cp437").decode("cp949")
    except UnicodeError:
        return name


def parse_agenda_number(text: str) -> int | None:
    numbered = re.search(r"제\s*(\d{4})\s*-\s*(\d+)\s*호", text)
    if numbered:
        return int(numbered.group(2))
    decided = re.search(r"의결\s*(\d+)", text)
    if decided:
        return int(decided.group(1))
    return None


def _flat_name(text: str) -> str:
    flattened = text
    for dot in _DOTS:
        flattened = flattened.replace(dot, "")
    return re.sub(r"\s+", "", flattened)


def is_audit_related(name: str) -> bool:
    flattened = _flat_name(name)
    if any(term in flattened for term in EXCLUDED_TERMS):
        return False
    if any(phrase in flattened for phrase in INVESTIGATION_PHRASES):
        return True
    return any(term in flattened for term in AUDIT_TERMS)


def _agenda_temp_name(url: str) -> str:
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"_agenda-{digest}.zip"


def meeting_date(text: str) -> str:
    matched = MEETING_DATE_RE.search(text)
    if matched is None:
        return "없음"
    year = 2000 + int(matched.group(1))
    month = int(matched.group(2))
    day = int(matched.group(3))
    return f"{year:04d}-{month:02d}-{day:02d}"


_PUBLICATION_RE = re.compile(
    r"\(\s*\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*공개\s*\)"
)
_SPOKEN_DATE_RE = re.compile(
    r"(?<!\d)(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"
)
_DOTTED_DATE_RE = re.compile(
    r"(?<!\d)(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?"
)
_TITLE_DOTTED_RE = re.compile(
    r"(?<!\d)(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?\s*$"
)
_STANDALONE_DOTTED_RE = re.compile(
    r"(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?(?:\s*\([^)]*\))?"
)
_SESSION_DATE_RE = re.compile(
    r"일\s*시[^\n]{0,40}?(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"
)
_FRONT_LINES = 60


def _iso_date(year: str, month: str, day: str) -> str | None:
    try:
        parsed = date(int(year), int(month), int(day))
    except ValueError:
        return None
    return parsed.isoformat()


def _clean_minutes_line(line: str) -> str:
    return line.replace("\ufeff", "").strip()


def _calendar_date(text: str) -> str:
    """Full calendar date, ignoring a publication note such as (2026.9.18. 공개)."""
    cleaned = _PUBLICATION_RE.sub(" ", text.replace("\ufeff", ""))
    parenthetical = meeting_date(cleaned)
    if parenthetical != "없음":
        return parenthetical
    spoken = _SPOKEN_DATE_RE.search(cleaned)
    if spoken:
        parsed = _iso_date(*spoken.groups())
        if parsed:
            return parsed
    dotted = _DOTTED_DATE_RE.search(cleaned)
    if dotted:
        parsed = _iso_date(*dotted.groups())
        if parsed:
            return parsed
    return "없음"


def meeting_date_from_minutes_text(text: str) -> str:
    """Date under the minutes title, or the 일시 line. Other dates are not the meeting day."""
    lines = [_clean_minutes_line(line) for line in text.splitlines()[:_FRONT_LINES]]
    for index, line in enumerate(lines):
        if "의사록" not in line:
            continue
        stripped = _PUBLICATION_RE.sub(" ", line).strip()
        trailed = _TITLE_DOTTED_RE.search(stripped)
        if trailed:
            parsed = _iso_date(*trailed.groups())
            if parsed:
                return parsed
        for follow in lines[index + 1 : index + 8]:
            if not follow or _PUBLICATION_RE.search(follow):
                continue
            matched = _STANDALONE_DOTTED_RE.fullmatch(follow)
            if matched:
                parsed = _iso_date(*matched.groups()[:3])
                if parsed:
                    return parsed
            break
        break
    session = _SESSION_DATE_RE.search("\n".join(lines))
    if session:
        parsed = _iso_date(*session.groups())
        if parsed:
            return parsed
    return "없음"


def read_minutes_pdf_text(path: Path) -> str:
    """First page only. Later pages carry agenda dates, not the meeting day."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        if not reader.pages:
            return ""
        return reader.pages[0].extract_text() or ""
    except Exception:
        return ""


def resolve_meeting_day(
    block: str,
    posts: list[DecisionPost],
    minutes_pdf: Path | None = None,
) -> str:
    found = meeting_date(block)
    if found != "없음":
        return found
    for additional in (False, True):
        for post in posts:
            if is_additional_minutes(post.title) != additional:
                continue
            found = _calendar_date(post.title)
            if found != "없음":
                return found
    if minutes_pdf is not None and minutes_pdf.is_file():
        return meeting_date_from_minutes_text(read_minutes_pdf_text(minutes_pdf))
    return "없음"


def is_masked_label(text: str) -> bool:
    if any(char in text for char in _MASK_CHARS):
        return True
    if re.search(r"(?:㈜|\(주\))\s*[Oo]{2,}|[Oo]{2,}\s*(?:㈜|\(주\))", text):
        return True
    return re.search(r"(?<![A-Za-z])[A-Za-z]사(?![가-힣])", text) is not None


def classify_zip_entry(name: str) -> str | None:
    lowered = name.lower()
    if lowered.endswith((".hwp", ".hwpx")):
        return "hwp" if is_audit_related(name) else None
    if not lowered.endswith(".pdf") or not is_audit_related(name):
        return None
    if "의결서" in name:
        return "decision"
    if "공개용" in name:
        return "agenda"
    return None


def audit_zip_entries(names: list[str]) -> tuple[list[AgendaFile], list[str]]:
    kept: list[AgendaFile] = []
    whale: list[str] = []
    for name in names:
        kind = classify_zip_entry(name)
        if kind == "hwp":
            whale.append(name)
        elif kind in {"agenda", "decision"}:
            kept.append(
                AgendaFile(name, kind, parse_agenda_number(name), is_masked_label(name))
            )
    return kept, whale


def _without_discussion(block: str) -> str:
    marker = '!!! note "위원 논의"'
    start = block.find(marker)
    if start < 0:
        return block
    return block[:start]


def press_agenda_numbers(block: str) -> set[int]:
    text = re.sub(r"<!--.*?-->", "", _without_discussion(block), flags=re.DOTALL)
    found: set[int] = set()
    for matched in re.finditer(r"제\s*(\d{4})\s*-\s*(\d+)\s*호", text):
        found.add(int(matched.group(2)))
    for matched in re.finditer(r"제\s*(\d+)\s*호", text):
        found.add(int(matched.group(1)))
    for matched in re.finditer(r"의결\s*(\d+)", text):
        found.add(int(matched.group(1)))
    return found


def _is_org(cell: str) -> bool:
    if cell in {"회사", "대상", "대상자"}:
        return False
    if any(token in cell for token in ("대표", "임원", "이사")):
        return False
    return any(token in cell for token in ("㈜", "(주)", "주식회사", "회계법인", "감사반"))


def real_company_names(block: str) -> list[str]:
    names: list[str] = []
    header: list[str] | None = None
    for line in _without_discussion(block).splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            header = None
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or set(cells[0]) <= set("-: "):
            continue
        if header is None:
            header = cells
            continue
        for column, cell in zip(header, cells):
            if column not in {"회사명", "회사", "대상", "대상자"} or not _is_org(cell):
                continue
            if is_masked_label(cell) or cell in names:
                continue
            names.append(cell)
    return names


def _name_hits(names: list[str], filename: str) -> list[str]:
    compact_file = _flat_name(filename).replace("(주)", "㈜")
    hits = [name for name in names if _flat_name(name).replace("(주)", "㈜") in compact_file]
    hits.sort(key=len, reverse=True)
    kept: list[str] = []
    for name in hits:
        if any(_flat_name(name) in _flat_name(other) for other in kept):
            continue
        kept.append(name)
    return kept


def link_agendas(
    block: str,
    key: tuple[int, str, str, int],
    agendas: list[AgendaFile],
) -> tuple[list[tuple[AgendaFile, str]], list[AgendaFile]]:
    del key
    names = real_company_names(block)
    numbers = press_agenda_numbers(block)
    linked: list[tuple[AgendaFile, str]] = []
    unmatched: list[AgendaFile] = []
    for agenda in agendas:
        masked = agenda.masked or is_masked_label(agenda.filename)
        hits = [] if masked else _name_hits(names, agenda.filename)
        if agenda.number is not None and agenda.number in numbers:
            linked.append((agenda, "의안번호"))
        elif len(hits) == 1:
            linked.append((agenda, "실명"))
        else:
            unmatched.append(agenda)
    return linked, unmatched


def _press_url(block: str) -> str:
    for line in block.splitlines():
        matched = LINK_RE.match(line.strip())
        if matched:
            return matched.group(5)
    return ""


def _agenda_record_rows(
    block: str,
    agendas: list[AgendaFile],
) -> list[tuple[AgendaFile, str, str]]:
    """(agenda, press URL or unmatched, 의안번호/실명 or blank)."""
    linked, _unmatched = link_agendas(block, (0, "", "", 0), agendas)
    url = _press_url(block)
    basis_by_name = {item.filename: basis for item, basis in linked}
    rows: list[tuple[AgendaFile, str, str]] = []
    for agenda in agendas:
        basis = basis_by_name.get(agenda.filename, "")
        if basis and url:
            rows.append((agenda, url, basis))
        else:
            rows.append((agenda, "unmatched", ""))
    return rows


def sanction_folder(key: tuple[int, str, str, int]) -> str:
    year, committee, kind, number = key
    if kind in {"임시", "서면"}:
        return f"{year}-{committee}-{kind}-{number}차"
    return f"{year}-{committee}-{number}차"


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", name.replace("\\", "/").rsplit("/", 1)[-1])
    return cleaned.strip() or "attachment.pdf"


def _bundle_file(folder: Path, kind: str, filename: str) -> Path:
    safe = _safe_filename(filename)
    if kind == "minutes":
        if safe not in {"minutes.pdf", "minutes-추가.pdf"}:
            safe = "minutes-추가.pdf" if "추가" in safe else "minutes.pdf"
        return folder / safe
    return folder / kind / safe


def _minutes_names(text: str) -> list[str]:
    matched = re.search(r"^(- 의사록:\s*)(.*)$", text, re.MULTILINE)
    if matched is None:
        return []
    names: list[str] = []
    for part in matched.group(2).split(","):
        name = part.strip()
        if name.endswith(".pdf") and name not in names:
            names.append(name)
    return names


def _merge_minutes_line(text: str, minutes: list[str]) -> str:
    matched = re.search(r"^(- 의사록:\s*)(.*)$", text, re.MULTILINE)
    if matched is None or not minutes:
        return text
    names = [part.strip() for part in matched.group(2).split(",") if part.strip() and part.strip() != "없음"]
    for name in minutes:
        if name not in names:
            names.append(name)
    if not names:
        return text
    merged = matched.group(1) + ", ".join(names)
    return text[: matched.start()] + merged + text[matched.end() :]


def place_sanction_bundle(
    root: Path,
    key: tuple[int, str, str, int],
    record: str,
    files: list[tuple[str, str, bytes]],
    written: list[Path] | None = None,
    restores: list[tuple[Path, bytes]] | None = None,
) -> list[Path]:
    folder = root / sanction_folder(key)
    folder.mkdir(parents=True, exist_ok=True)
    record_path = folder / "record.md"
    if not record_path.exists():
        record_path.write_text(record, encoding="utf-8", newline="\n")
        if written is not None:
            written.append(record_path)
    else:
        original = record_path.read_bytes()
        try:
            previous = original.decode("utf-8")
        except UnicodeError:
            previous = ""
        updated = _merge_minutes_line(record, _minutes_names(previous))
        revised = updated.encode("utf-8")
        if revised != original:
            if restores is not None:
                restores.append((record_path, original))
            record_path.write_bytes(revised)
    for kind, filename, payload in files:
        dest = _bundle_file(folder, kind, filename)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            continue
        dest.write_bytes(payload)
        if written is not None:
            written.append(dest)
    return [folder]


def _item_key(title: str, block: str) -> tuple[int, str, str, int] | None:
    return meeting_key(title + "\n" + block) or decision_key(title + "\n" + block)


def _iter_resolution_blocks(lines: list[str]):
    in_resolution = False
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("#### "):
            in_resolution = stripped == "#### 제재 의결"
        elif stripped.startswith("### ") or stripped.startswith("## "):
            in_resolution = False
        matched = LINK_RE.match(lines[index]) if in_resolution else None
        if not matched:
            index += 1
            continue
        block_end = index + 1
        while block_end < len(lines) and not LINK_RE.match(lines[block_end]):
            raw = lines[block_end]
            if _resolution_item_boundary(raw):
                break
            block_end += 1
        yield index, block_end, matched.group(4), "\n".join(lines[index:block_end])
        index = block_end


def attach_agenda_markers(
    text: str,
    key: tuple[int, str, str, int],
    rows: list[tuple[AgendaFile, str, str]],
) -> tuple[str, list[str]]:
    lines = text.splitlines()
    report: list[str] = []
    for agenda, label, marker_path in rows:
        number = agenda.number if agenda.number is not None else "-"
        if label == "unmatched":
            report.append(f"unmatched {key[0]} {key[1]} {key[2]} {key[3]} {number} {agenda.filename}")
        else:
            report.append(f"linked {key[0]} {key[1]} {key[2]} {key[3]} {number} {label}")
    insertions: list[tuple[int, list[str]]] = []
    for index, block_end, title, block in _iter_resolution_blocks(lines):
        if _item_key(title, block) != key:
            continue
        marker_rows = [row for row in rows if row[1] != "unmatched"]
        missing = [path for _, _, path in marker_rows if path not in block]
        if missing:
            insertions.append((index, missing))
        break
    shift = 0
    for index, paths in insertions:
        at = index + shift
        cursor = at + 1
        while cursor < len(lines) and lines[cursor].strip() == "":
            cursor += 1
        if cursor < len(lines) and lines[cursor].strip().startswith("<!-- source:"):
            while cursor < len(lines) and lines[cursor].strip().startswith("<!-- source:"):
                cursor += 1
            for offset, path in enumerate(paths):
                lines.insert(cursor + offset, f"    <!-- source: pdf|{path} -->")
            shift += len(paths)
        else:
            lines.insert(at + 1, "")
            for offset, path in enumerate(paths):
                lines.insert(at + 2 + offset, f"    <!-- source: pdf|{path} -->")
            shift += 1 + len(paths)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), report


def _press_label(block: str) -> str:
    first = block.splitlines()[0] if block else ""
    matched = LINK_RE.match(first.strip())
    if matched is None:
        return "미보도"
    return f"{matched.group(4)} ({matched.group(5)})"


def _record_text(
    key: tuple[int, str, str, int],
    page_url: str,
    zip_url: str,
    meeting_day: str,
    minutes: list[str],
    rows: list[tuple[AgendaFile, str, str]],
    press: str = "미보도",
    extra_pages: list[str] | None = None,
) -> str:
    lines = [
        f"# {sanction_folder(key)}",
        "",
        f"- 회의일: {meeting_day}",
        f"- 게시 URL: {page_url or '없음'}",
    ]
    if extra_pages:
        lines.append(f"- 추가 게시 URL: {', '.join(extra_pages)}")
    lines.extend(
        [
            f"- ZIP URL: {zip_url or '없음'}",
            f"- 보도: {press or '미보도'}",
            f"- 의사록: {', '.join(minutes) if minutes else '없음'}",
            "",
            "| 번호 | 구분 | 제목 | 마스킹 | 연결 | 연결근거 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for agenda, link, basis in rows:
        masked = "예" if agenda.masked else "아니오"
        number = agenda.number if agenda.number is not None else ""
        lines.append(
            f"| {number} | {agenda.kind} | {agenda.filename} | {masked} | {link} | {basis} |"
        )
    if not rows:
        lines.append("|  |  |  |  |  |  |")
    lines.append("")
    return "\n".join(lines)


def _extract_kept(
    data: bytes,
    meeting_year: int | None = None,
) -> tuple[list[tuple[str, str, bytes]], list[str], list[str]]:
    whale: list[str] = []
    notes: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        named: list[tuple[zipfile.ZipInfo, str]] = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = _zip_name(info)
            if meeting_year is not None and filename_year_conflict(name, meeting_year):
                notes.append(f"year-mismatch {name}")
                continue
            named.append((info, name))
        classified, whale = audit_zip_entries([name for _info, name in named])
        by_name = {item.filename: item for item in classified}
        payloads: list[tuple[str, str, bytes]] = []
        for info, name in named:
            item = by_name.get(name)
            if item is None:
                continue
            payloads.append((item.kind, _safe_filename(name), archive.read(info)))
        payloads, dedup_notes = dedupe_payloads(payloads)
        notes.extend(dedup_notes)
    return payloads, whale, notes


def _resolution_keys(text: str) -> dict[tuple[int, str, str, int], str]:
    found: dict[tuple[int, str, str, int], str] = {}
    for _index, _end, title, block in _iter_resolution_blocks(text.splitlines()):
        key = _item_key(title, block)
        if key is not None and key not in found:
            found[key] = block
    return found


def _apply_agendas(text, posts, download, downloads: Path, written: list[Path], restores: list | None = None):
    report: list[str] = []
    blocks = _resolution_keys(text)
    seen_zip: set[str] = set()
    for key, block in blocks.items():
        group = _meeting_posts(key, posts)
        page_url, extra_pages, zip_urls = meeting_source_urls(group)
        agendas: list[AgendaFile] = []
        payloads: list[tuple[str, str, bytes]] = []
        whale: list[str] = []
        for url in zip_urls:
            if url in seen_zip:
                continue
            seen_zip.add(url)
            temporary = downloads / _agenda_temp_name(url)
            try:
                download(url, temporary)
                data = temporary.read_bytes()
                extracted, zip_whale, notes = _extract_kept(data, key[0])
                report.extend(notes)
            except zipfile.BadZipFile:
                report.append(f"zip-invalid {key[0]} {key[1]} {key[2]} {key[3]}")
                extracted, zip_whale = [], []
            finally:
                if temporary.is_file():
                    temporary.unlink()
            whale.extend(zip_whale)
            for kind, filename, payload in extracted:
                agendas.append(
                    AgendaFile(filename, kind, parse_agenda_number(filename), is_masked_label(filename))
                )
                payloads.append((kind, filename, payload))
        for name in whale:
            report.append(f"Whale 변환 필요: {name}")
        folder = sanction_folder(key)
        minute_urls = minutes_urls_for_key(key, posts)
        minute_note = ""
        if minute_urls is None:
            minute_note = "모호"
            minute_urls = []
        minute_files: list[tuple[str, str, bytes]] = []
        minute_paths: list[str] = []
        for url in minute_urls:
            name = _minutes_filename(url, key, _title_for_url(key, posts, url))
            dest = downloads / "sanctions" / folder / name
            if not dest.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                written.append(dest)
                download(url, dest)
            minute_paths.append(name)
            minute_files.append(("minutes", name, dest.read_bytes()))
        if not agendas and not whale and not minute_files and not minute_note:
            continue
        record_rows = _agenda_record_rows(block, agendas)
        by_name = {item.filename: (link, basis) for item, link, basis in record_rows}
        rows: list[tuple[AgendaFile, str, str]] = []
        marker_rows: list[tuple[AgendaFile, str, str]] = []
        bundle_files: list[tuple[str, str, bytes]] = []
        for agenda, (kind, filename, payload) in zip(agendas, payloads):
            relative = f"downloads/sanctions/{folder}/{kind}/{filename}"
            link, basis = by_name.get(agenda.filename, ("unmatched", ""))
            rows.append((agenda, link, basis))
            marker_rows.append((agenda, link, relative))
            bundle_files.append((kind, filename, payload))
        bundle_files.extend(minute_files)
        if minute_paths:
            minutes = minute_paths
        elif minute_note:
            minutes = [minute_note]
        else:
            minutes = []
        place_sanction_bundle(
            downloads / "sanctions",
            key,
            _record_text(
                key,
                page_url,
                ", ".join(zip_urls),
                resolve_meeting_day(
                    block,
                    group,
                    downloads / "sanctions" / folder / "minutes.pdf",
                ),
                minutes,
                rows,
                _press_label(block),
                extra_pages,
            ),
            bundle_files,
            written,
            restores,
        )
        text, item_report = attach_agenda_markers(text, key, marker_rows)
        report.extend(item_report)
    return text, report


def _list_url(board: str, page: int, start: date, end: date) -> str:
    return (
        f"{board}?curPage={page}&srchBeginDt={start.isoformat()}"
        f"&srchEndDt={end.isoformat()}&srchCtgry=&srchKey=&srchText="
    )


def _meeting_material(title: str) -> bool:
    return any(word in title for word in POST_TITLE_WORDS)


def collect_posts(
    fetch_text,
    start: date,
    end: date,
    pending: list | None = None,
    notes: list | None = None,
) -> list[DecisionPost]:
    posts: list[DecisionPost] = []
    for board in BOARDS:
        page = 1
        while True:
            rows = parse_board_rows(fetch_text(_list_url(board, page, start, end)))
            if not rows:
                break
            for title, url, posted in rows:
                key = decision_key(title, posted)
                if key is None or not _meeting_material(title):
                    continue
                detail = fetch_text(url)
                attachments = detail_attachments(detail)
                pdfs: list[str] = []
                zips: list[str] = []
                pending_names: list[tuple[str, str]] = []
                for name, link in attachments:
                    if filename_year_conflict(name, key[0]):
                        if notes is not None:
                            notes.append(f"year-mismatch {name}")
                        continue
                    if "의사록" in name and name.lower().endswith(".pdf"):
                        pdfs.append(link)
                    elif is_pending_minutes(name):
                        pending_names.append((name, link))
                    elif name.lower().endswith(".zip"):
                        zips.append(link)
                if pending is not None and not pdfs:
                    for name, link in pending_names:
                        pending.append(
                            {
                                "board": board_label(board),
                                "filename": name,
                                "page_url": url,
                                "post_id": post_id_from_url(url),
                                "reason": "not-pdf",
                                "ts": _now_iso(),
                                "url": link,
                            }
                        )
                if not pdfs:
                    posts.append(DecisionPost(*key, "", zips, title, url))
                else:
                    for pdf in pdfs:
                        posts.append(DecisionPost(*key, pdf, zips, title, url))
            page += 1
    return posts


def pending_downloads(text: str, posts: list[DecisionPost]) -> list[tuple[str, str]]:
    lines = text.splitlines()
    pending: list[tuple[str, str]] = []
    in_resolution = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#### "):
            in_resolution = stripped == "#### 제재 의결"
        elif stripped.startswith("### ") or stripped.startswith("## "):
            in_resolution = False
        matched = LINK_RE.match(lines[i]) if in_resolution else None
        if matched:
            block_end = i + 1
            while block_end < len(lines) and not LINK_RE.match(lines[block_end]):
                raw = lines[block_end]
                if _resolution_item_boundary(raw):
                    break
                block_end += 1
            block = "\n".join(lines[i:block_end])
            key = meeting_key(matched.group(4) + "\n" + block)
            if key and _eligible_block(block):
                found = minutes_urls_for_key(key, posts)
                if found:
                    for url in found:
                        name = _minutes_filename(url, key, _title_for_url(key, posts, url))
                        marker = _minutes_marker(key, name)
                        if marker not in block:
                            pending.append((url, marker.removeprefix("downloads/")))
            i = block_end
            continue
        i += 1
    return pending


def _quarter_window(quarter_name: str) -> tuple[date, date] | None:
    matched = QUARTER_NAME_RE.search(quarter_name)
    if matched is None:
        return None
    start = date.fromisoformat(matched.group(1))
    end = date.fromisoformat(matched.group(2)) + timedelta(days=70)
    return start, end


def _search_window(
    quarter_name: str,
    until: date | None = None,
    extra_days: int | None = None,
) -> tuple[date, date] | None:
    window = _quarter_window(quarter_name)
    if window is None:
        return None
    start, default_end = window
    if until is not None and until < default_end:
        raise ValueError("until precedes the default end")
    if extra_days is not None and extra_days < 0:
        raise ValueError("extra-days must not shrink the window")
    end = default_end
    if extra_days:
        end = default_end + timedelta(days=extra_days)
    if until is not None and until > end:
        end = until
    return start, end


def _rollback(downloads: Path, written: list[Path], restores: list[tuple[Path, bytes]]) -> None:
    parents: list[Path] = []
    for dest in written:
        parents.append(dest.parent)
        if dest.is_file():
            dest.unlink()
    for path, payload in restores:
        path.write_bytes(payload)
    for parent in parents:
        current = parent
        while downloads in current.parents:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


def run_minutes(
    text,
    quarter_name,
    fetch_text,
    download,
    downloads: Path,
    until: date | None = None,
    extra_days: int | None = None,
):
    try:
        window = _search_window(quarter_name, until, extra_days)
    except ValueError:
        return 2, text, []
    if window is None:
        return 2, text, []
    written: list[Path] = []
    restores: list[tuple[Path, bytes]] = []
    pending_rows: list[dict] = []
    year_notes: list[str] = []
    try:
        posts = collect_posts(fetch_text, *window, pending_rows, year_notes)
        pending = pending_downloads(text, posts)
        for url, relative in pending:
            dest = downloads / relative
            if dest.is_file():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            written.append(dest)
            download(url, dest)
        updated, report = attach_minutes(text, posts)
        report.extend(year_notes)
        updated, agenda_report = _apply_agendas(updated, posts, download, downloads, written, restores)
        report.extend(agenda_report)
    except Exception:
        _rollback(downloads, written, restores)
        return 1, text, []
    if pending_rows:
        pending_path = downloads / "sanctions" / "_pending-conversion.jsonl"
        for row in pending_rows:
            record_pending(pending_path, row)
    return 0, updated, report


def _before_request() -> None:
    global _requests_made
    if _requests_made and _request_delay > 0:
        time.sleep(_request_delay)
    _requests_made += 1


def _http_get(url: str, timeout: int):
    """목록·첨부 공통 요청. www 호스트는 fsc.go.kr로 바꾸고 재시도한다."""
    import requests

    url = normalize_fsc_url(url)
    attempt = 0
    forbidden_retries = 0
    while True:
        _before_request()
        attempt += 1
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": _BROWSER_UA})
        except requests.exceptions.RequestException as exc:
            if _transport_retryable(exc) and attempt < HTTP_RETRY_ATTEMPTS:
                time.sleep(_backoff_seconds(attempt))
                continue
            raise FetchFailed(url, None, f"{type(exc).__name__}: {exc}", attempt) from exc
        status = getattr(response, "status_code", 200)
        if status == 429 or status >= 500:
            if attempt < HTTP_RETRY_ATTEMPTS:
                time.sleep(_backoff_seconds(attempt))
                continue
            raise FetchFailed(url, status, f"HTTP {status}", attempt)
        if status == 403 and forbidden_retries < HTTP_FORBIDDEN_RETRIES:
            forbidden_retries += 1
            time.sleep(HTTP_FORBIDDEN_DELAY)
            continue
        if status == 403:
            raise FetchFailed(url, status, f"HTTP {status}", attempt)
        if status >= 400:
            response.raise_for_status()
        return response


def _http_text(url: str) -> str:
    return _http_get(url, 30).text


def _looks_like_pdf(content: bytes) -> bool:
    """본문 앞이 PDF 시그니처인지. ZIP·HWP에는 쓰지 않는다."""
    return content.lstrip(b"\xef\xbb\xbf\r\n\t ").startswith(b"%PDF-")


def _http_download(url: str, dest: Path) -> None:
    response = _http_get(url, 60)
    content = response.content
    if dest.suffix.lower() == ".pdf" and not _looks_like_pdf(content):
        if dest.is_file():
            dest.unlink()
        raise FetchFailed(url, None, "not a PDF", 1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)


def _failure_row(
    *,
    board: str,
    post_id: str,
    page_url: str,
    url: str,
    filename: str,
    http_status: int | None,
    error: str,
    attempts: int,
) -> dict:
    return {
        "attempts": attempts,
        "board": board,
        "error": error,
        "filename": filename,
        "http_status": http_status,
        "page_url": page_url,
        "post_id": post_id,
        "ts": _now_iso(),
        "url": url,
    }


def _download_or_record(
    download,
    dest: Path,
    *,
    board: str,
    post_id: str,
    page_url: str,
    url: str,
    filename: str,
    failures: Path,
) -> bool:
    """성공하면 True. 실패는 JSONL에 남기고 False."""
    existed = dest.exists()
    try:
        download(url, dest)
    except FetchFailed as exc:
        if not existed and dest.exists():
            dest.unlink()
        record_failure(
            failures,
            _failure_row(
                board=board,
                post_id=post_id,
                page_url=page_url,
                url=url,
                filename=filename,
                http_status=exc.http_status,
                error=exc.error,
                attempts=exc.attempts,
            ),
        )
        return False
    except Exception as exc:
        if not existed and dest.exists():
            dest.unlink()
        record_failure(
            failures,
            _failure_row(
                board=board,
                post_id=post_id,
                page_url=page_url,
                url=url,
                filename=filename,
                http_status=None,
                error=f"{type(exc).__name__}: {exc}",
                attempts=1,
            ),
        )
        return False
    clear_failure(failures, url)
    return True


def _choose_minutes(
    title: str,
    key: tuple[int, str, str, int],
    minutes: list[tuple[str, str]],
    report: list[str],
) -> list[tuple[str, str]]:
    if is_additional_minutes(title):
        return minutes
    primaries = minutes
    if len(primaries) > 1:
        report.append(f"ambiguous {key[0]} {key[1]} {key[2]} {key[3]}")
        return []
    return primaries


def run_backfill(
    fetch_text,
    download,
    downloads: Path,
    since: date,
    until: date,
    board: str | None = None,
    dry_run: bool = False,
    resume: bool = False,
    retry_failed: bool = False,
) -> dict:
    """목록 게시일 구간의 금융위·증선위 회차를 받는다. 분기 마크다운은 고치지 않는다.

    비공개기간 경과 안건은 건너뛴다. PDF가 아닌 의사록은 대기 목록에만 적고
    회차 폴더에 두지 않는다. 남길 PDF가 없으면 폴더를 만들지 않는다.
    사이트 목록에 없는 회차는 만들지 않는다.
    """
    selected = [item for item in BOARD_URLS.items() if board in (None, item[0])]
    state_path = downloads / "sanctions" / "_backfill-state.json"
    failure_path = downloads / "sanctions" / "_failed-downloads.jsonl"
    pending_path = downloads / "sanctions" / "_pending-conversion.jsonl"
    state = load_backfill_state(state_path)
    done = _done_ids(state) if resume else set()
    blocked = forbidden_urls(failure_path) if resume and not retry_failed else set()
    report: list[str] = []
    folders = 0
    files = 0
    skipped = 0
    import requests

    fetch_errors = (FetchFailed, requests.exceptions.RequestException)

    def note_fetch_failure(exc: BaseException, *, board: str, post_id: str, page_url: str, url: str) -> None:
        status = getattr(exc, "http_status", None)
        response = getattr(exc, "response", None)
        if status is None and response is not None:
            status = getattr(response, "status_code", None)
        error = getattr(exc, "error", "") or f"{type(exc).__name__}: {exc}"
        record_failure(
            failure_path,
            _failure_row(
                board=board,
                post_id=post_id,
                page_url=page_url,
                url=url,
                filename="",
                http_status=status,
                error=error,
                attempts=getattr(exc, "attempts", 1),
            ),
        )

    for label, board_url in selected:
        page = 1
        last_page = 0
        while True:
            list_url = _list_url(board_url, page, since, until)
            if list_url in blocked:
                break
            try:
                rows = parse_board_rows(fetch_text(list_url))
            except fetch_errors as exc:
                note_fetch_failure(exc, board=label, post_id="", page_url=list_url, url=list_url)
                break
            if not rows:
                break
            last_page = page
            for title, page_url, posted in rows:
                if posted is not None and (posted < since or posted > until):
                    skipped += 1
                    continue
                key = decision_key(title, posted)
                post_id = post_id_from_url(page_url)
                if key is None or not _meeting_material(title):
                    skipped += 1
                    continue
                if resume and post_id in done:
                    continue
                if page_url in blocked:
                    continue
                try:
                    detail = fetch_text(page_url)
                except fetch_errors as exc:
                    note_fetch_failure(
                        exc,
                        board=label,
                        post_id=post_id,
                        page_url=page_url,
                        url=page_url,
                    )
                    continue
                minutes: list[tuple[str, str]] = []
                zips: list[tuple[str, str]] = []
                pendings: list[tuple[str, str]] = []
                for name, url in detail_attachments(detail):
                    if filename_year_conflict(name, key[0]):
                        report.append(f"year-mismatch {name}")
                        continue
                    lowered = name.lower()
                    if "의사록" in name and lowered.endswith(".pdf"):
                        minutes.append((name, url))
                    elif is_pending_minutes(name):
                        pendings.append((name, url))
                    elif lowered.endswith(".zip"):
                        zips.append((name, url))
                chosen = _choose_minutes(title, key, minutes, report)
                if not chosen and not zips:
                    skipped += 1
                    if not dry_run:
                        for name, url in pendings:
                            record_pending(
                                pending_path,
                                {
                                    "board": label,
                                    "filename": name,
                                    "page_url": page_url,
                                    "post_id": post_id,
                                    "reason": "not-pdf",
                                    "ts": _now_iso(),
                                    "url": url,
                                },
                            )
                        _mark_done(state, post_id, page, label, page_url)
                        state["pages"][label] = last_page
                        save_backfill_state(state_path, state)
                        done.add(post_id)
                    continue
                folders += 1
                files += len(chosen) + len(zips)
                if dry_run:
                    continue
                folder = downloads / "sanctions" / sanction_folder(key)
                failed = False
                wrote = False
                if not chosen:
                    for name, url in pendings:
                        record_pending(
                            pending_path,
                            {
                                "board": label,
                                "filename": name,
                                "page_url": page_url,
                                "post_id": post_id,
                                "reason": "not-pdf",
                                "ts": _now_iso(),
                                "url": url,
                            },
                        )
                for name, url in chosen:
                    filename = _minutes_filename(url, key, title)
                    dest = folder / filename
                    if dest.is_file():
                        wrote = True
                        clear_failure(failure_path, url)
                        continue
                    if url in blocked:
                        failed = True
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if _download_or_record(
                        download,
                        dest,
                        board=label,
                        post_id=post_id,
                        page_url=page_url,
                        url=url,
                        filename=filename,
                        failures=failure_path,
                    ):
                        wrote = True
                    else:
                        failed = True
                for name, url in zips:
                    if url in blocked:
                        failed = True
                        continue
                    temporary = downloads / "sanctions" / _agenda_temp_name(url)
                    temporary.parent.mkdir(parents=True, exist_ok=True)
                    if not _download_or_record(
                        download,
                        temporary,
                        board=label,
                        post_id=post_id,
                        page_url=page_url,
                        url=url,
                        filename=name,
                        failures=failure_path,
                    ):
                        failed = True
                        continue
                    try:
                        extracted, zip_whale, notes = _extract_kept(temporary.read_bytes(), key[0])
                    except zipfile.BadZipFile:
                        report.append(f"zip-invalid {key[0]} {key[1]} {key[2]} {key[3]}")
                        extracted, zip_whale, notes = [], [], []
                    finally:
                        if temporary.is_file():
                            temporary.unlink()
                    report.extend(notes)
                    for whale_name in zip_whale:
                        report.append(f"Whale 변환 필요: {whale_name}")
                    for kind, filename, payload in extracted:
                        dest = _bundle_file(folder, kind, filename)
                        if dest.is_file():
                            wrote = True
                            continue
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(payload)
                        wrote = True
                if wrote:
                    ensure_sanctions_readme(downloads)
                else:
                    _prune_empty(folder)
                if not failed:
                    _mark_done(state, post_id, page, label, page_url)
                    state["pages"][label] = last_page
                    save_backfill_state(state_path, state)
            page += 1
        if last_page and not dry_run:
            state["pages"][label] = last_page
            save_backfill_state(state_path, state)
    return {"folders": folders, "files": files, "skipped": skipped, "report": report}


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="제재 의결 의사록과 의안을 회차 폴더에 붙입니다.",
        epilog=(
            "백필은 --backfill과 함께 쓴다. 요청 간격 기본 1초. "
            "금융위 기본 시작일은 2001-01-26이고, --board 증선위만 주면 2001-02-08이다. "
            "비공개기간 경과 안건은 건너뛴다. "
            "HWP/XLS 의사록은 변환하지 않고 대기 목록에만 적는다. "
            "시장질서교란 의결서·안건은 보존하지 않는다. "
            "남길 PDF가 없는 회차는 폴더를 만들지 않는다. "
            "사이트에 없는 회차는 만들지 않는다."
        ),
    )
    parser.add_argument("quarter", nargs="?", type=Path)
    parser.add_argument("--backfill", action="store_true", help="분기 파일 없이 목록 구간을 받는다")
    parser.add_argument("--since", help="목록 게시일 하한 YYYY-MM-DD. --backfill 전용")
    parser.add_argument("--board", choices=("금융위", "증선위"), help="한 위원회만 받는다")
    parser.add_argument("--dry-run", action="store_true", help="목록과 키만 보고 첨부는 받지 않는다")
    parser.add_argument("--resume", action="store_true", help="끝난 글과 403 URL을 다시 받지 않는다")
    parser.add_argument("--retry-failed", action="store_true", help="실패 목록의 403을 다시 받는다")
    parser.add_argument("--delay", type=float, default=1.0, help="요청 사이 최소 간격(초). 기본 1")
    parser.add_argument("--until")
    parser.add_argument("--extra-days", type=int, default=None)
    try:
        args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
        if not args.backfill and (args.since or args.board or args.dry_run or args.resume or args.retry_failed):
            parser.error("백필 옵션은 --backfill과 함께 써야 합니다")
    except SystemExit as exc:
        code = exc.code
        return 2 if code is None else int(code)
    global _request_delay
    _request_delay = args.delay
    downloads = Path(__file__).resolve().parent.parent / "downloads"
    if args.backfill:
        try:
            if args.since:
                since = date.fromisoformat(args.since)
            elif args.board == "증선위":
                since = FSC_SINCE["증선위"]
            else:
                since = FSC_SINCE["금융위"]
            until = date.fromisoformat(args.until) if args.until else date.today()
        except ValueError:
            return 2
        if until < since:
            return 2
        summary = run_backfill(
            _http_text,
            _http_download,
            downloads,
            since,
            until,
            board=args.board,
            dry_run=args.dry_run,
            resume=args.resume,
            retry_failed=args.retry_failed,
        )
        print(f"만들 폴더: {summary['folders']}")
        print(f"받을 파일: {summary['files']}")
        print(f"건너뛸 글: {summary['skipped']}")
        for line in summary["report"]:
            print(line)
        return 0
    if args.quarter is None or not args.quarter.is_file():
        return 2
    until = None
    if args.until:
        try:
            until = date.fromisoformat(args.until)
        except ValueError:
            return 2
    text = args.quarter.read_text(encoding="utf-8")
    code, updated, report = run_minutes(
        text,
        args.quarter.name,
        _http_text,
        _http_download,
        downloads,
        until=until,
        extra_days=args.extra_days,
    )
    if code == 0 and updated != text:
        args.quarter.write_text(updated, encoding="utf-8", newline="\n")
    for line in report:
        print(line)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

