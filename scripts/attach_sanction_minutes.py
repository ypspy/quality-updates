from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

LINK_RE = re.compile(r"^- \((\d{2})-(\d{2})-(\d{2})\) \[(.+?)\]\((https?://[^\)]+)\)")
_YEAR_QUOTES = "'\u2018\u2019"
KEY_RE = re.compile(
    rf"제\s*(\d+)\s*차\s*(?:임시|서면)?\s*(증권선물위원회|금융위원회)"
    rf"[^()\n]{{0,30}}?"
    rf"\(\s*[{_YEAR_QUOTES}]\s*(\d{{2}})"
)
KIND_RE = re.compile(r"임시|서면")
DECISION_KEY_RE = re.compile(
    r"(?P<year>\d{4})년\s*제\s*(?P<number>\d+)\s*차\s*"
    r"(?P<early>임시|서면)?\s*"
    r"(?P<committee>증권선물위원회|금융위원회)"
)
BOARDS = ("https://www.fsc.go.kr/no020101", "https://www.fsc.go.kr/no020102")
QUARTER_NAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})\.md$")


@dataclass(frozen=True)
class DecisionPost:
    year: int
    committee: str
    kind: str
    number: int
    pdf_url: str
    zip_urls: list[str]


def meeting_key(text: str) -> tuple[int, str, str, int] | None:
    """제N차 and 증권선물위원회 or 금융위원회, then a parenthetical '26, ‘26, or ’26."""
    matched = KEY_RE.search(text) or KEY_RE.search(re.sub(r"\s+", "", text))
    if not matched:
        return None
    number, committee, year_digits = matched.groups()
    year = 2000 + int(year_digits)
    if "임시" in text:
        kind = "임시"
    elif KIND_RE.search(text):
        kind = "서면"
    else:
        kind = "정기"
    name = "증선위" if committee == "증권선물위원회" else "금융위"
    return year, name, kind, int(number)


def decision_key(title: str) -> tuple[int, str, str, int] | None:
    """Year, committee, kind, and number from a decision-board title."""
    matched = DECISION_KEY_RE.search(title)
    if matched is None:
        return None
    if matched.group("early"):
        kind = matched.group("early")
    elif "임시" in title:
        kind = "임시"
    elif "서면" in title:
        kind = "서면"
    else:
        kind = "정기"
    committee = "증선위" if matched.group("committee") == "증권선물위원회" else "금융위"
    return int(matched.group("year")), committee, kind, int(matched.group("number"))


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


def _minutes_filename(pdf_url: str, key: tuple[int, str, str, int]) -> str:
    path = pdf_url.split("#", 1)[0].split("?", 1)[0]
    segment = path.rstrip("/").rsplit("/", 1)[-1]
    if segment.lower().endswith(".pdf"):
        return segment
    year, committee, kind, number = key
    return f"minutes-{year}-{committee}-{kind}-{number}.pdf"


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
        if in_resolution and (matched := LINK_RE.match(lines[i])):
            block_end = i + 1
            while block_end < len(lines) and not LINK_RE.match(lines[block_end]) and not lines[block_end].startswith("####"):
                block_end += 1
            block = "\n".join(lines[i:block_end])
            key = meeting_key(matched.group(4) + "\n" + block)
            if key and not _eligible_block(block):
                report.append(f"skipped discussion {key[0]} {key[1]} {key[2]} {key[3]}")
                i = block_end
                continue
            found = [
                post.pdf_url
                for post in posts
                if key and (post.year, post.committee, post.kind, post.number) == key and post.pdf_url
            ]
            if key and len(found) == 0:
                report.append(f"unpublished {key[0]} {key[1]} {key[2]} {key[3]}")
            elif key and len(found) > 1:
                report.append(f"ambiguous {key[0]} {key[1]} {key[2]} {key[3]}")
            elif key and len(found) == 1:
                name = _minutes_filename(found[0], key)
                if f"downloads/{name}" not in block:
                    lines.insert(i + 1, "")
                    lines.insert(i + 2, f"    <!-- source: pdf|downloads/{name} -->")
                    report.append(f"attached {key[0]} {key[1]} {key[2]} {key[3]}")
                    i = block_end + 2
                    continue
            i = block_end
            continue
        i += 1
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), report


def parse_decision_list(html: str) -> list[tuple[str, str]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    rows: list[tuple[str, str]] = []
    for item in soup.select("li > div.inner"):
        subject = item.select_one(".subject a")
        if subject is None or not subject.get("href"):
            continue
        href = subject["href"]
        if href.startswith("http"):
            url = href
        else:
            url = "https://www.fsc.go.kr" + href
        rows.append((subject.get_text(" ", strip=True), url.split("?", 1)[0]))
    return rows


def minutes_pdf_urls(detail_html: str) -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(detail_html, "html.parser")
    found: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = anchor.get("href") or ""
        name = anchor.get_text(" ", strip=True)
        if "getFile" not in href or "의사록" not in name or not name.lower().endswith(".pdf"):
            continue
        url = href if href.startswith("http") else "https://www.fsc.go.kr" + href
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
    return found


def _list_url(board: str, page: int, start: date, end: date) -> str:
    return (
        f"{board}?curPage={page}&srchBeginDt={start.isoformat()}"
        f"&srchEndDt={end.isoformat()}&srchCtgry=&srchKey=&srchText="
    )


def collect_posts(fetch_text, start: date, end: date) -> list[DecisionPost]:
    posts: list[DecisionPost] = []
    for board in BOARDS:
        page = 1
        while True:
            rows = parse_decision_list(fetch_text(_list_url(board, page, start, end)))
            if not rows:
                break
            for title, url in rows:
                key = decision_key(title)
                if key is None or "의사록" not in title:
                    continue
                pdfs = minutes_pdf_urls(fetch_text(url))
                if not pdfs:
                    posts.append(DecisionPost(*key, "", []))
                else:
                    for pdf in pdfs:
                        posts.append(DecisionPost(*key, pdf, []))
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
        matched = LINK_RE.match(lines[i]) if in_resolution else None
        if matched:
            block_end = i + 1
            while block_end < len(lines) and not LINK_RE.match(lines[block_end]) and not lines[block_end].startswith("####"):
                block_end += 1
            block = "\n".join(lines[i:block_end])
            key = meeting_key(matched.group(4) + "\n" + block)
            if key and _eligible_block(block):
                found = [post.pdf_url for post in posts if (post.year, post.committee, post.kind, post.number) == key and post.pdf_url]
                if len(found) == 1:
                    name = _minutes_filename(found[0], key)
                    if f"downloads/{name}" not in block:
                        pending.append((found[0], name))
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


def run_minutes(text, quarter_name, fetch_text, download, downloads: Path):
    window = _quarter_window(quarter_name)
    if window is None:
        return 2, text, []
    written: list[Path] = []
    try:
        posts = collect_posts(fetch_text, *window)
        pending = pending_downloads(text, posts)
        for url, name in pending:
            dest = downloads / name
            if dest.is_file():
                continue
            written.append(dest)
            download(url, dest)
        updated, report = attach_minutes(text, posts)
    except Exception:
        for dest in written:
            if dest.is_file():
                dest.unlink()
        return 1, text, []
    return 0, updated, report


def _http_text(url: str) -> str:
    import requests

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def _http_download(url: str, dest: Path) -> None:
    import requests

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)


def main(argv: list[str] | None = None) -> int:
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        return 2
    path = Path(args[0])
    if not path.is_file():
        return 2
    text = path.read_text(encoding="utf-8")
    downloads = Path(__file__).resolve().parent.parent / "downloads"
    code, updated, report = run_minutes(text, path.name, _http_text, _http_download, downloads)
    if code == 0 and updated != text:
        path.write_text(updated, encoding="utf-8", newline="\n")
    for line in report:
        print(line)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

