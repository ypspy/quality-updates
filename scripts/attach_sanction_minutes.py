from __future__ import annotations

import re
from dataclasses import dataclass

LINK_RE = re.compile(r"^- \((\d{2})-(\d{2})-(\d{2})\) \[(.+?)\]\((https?://[^\)]+)\)")
_YEAR_QUOTES = "'\u2018\u2019"
KEY_RE = re.compile(
    rf"제\s*(\d+)\s*차\s*(증권선물위원회|금융위원회)"
    rf"[^()\n]{{0,30}}?"
    rf"\(\s*[{_YEAR_QUOTES}]\s*(\d{{2}})"
)
KIND_RE = re.compile(r"임시|서면")
DECISION_KEY_RE = re.compile(
    r"(?P<year>\d{4})년\s*제\s*(?P<number>\d+)\s*차\s*"
    r"(?P<early>임시|서면)?\s*"
    r"(?P<committee>증권선물위원회|금융위원회)"
)


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
            if not _eligible_block(block):
                if key := meeting_key(matched.group(4) + "\n" + block):
                    report.append(
                        f"skipped discussion {key[0]} {key[1]} {key[2]} {key[3]}"
                    )
                i = block_end
                continue
            key = meeting_key(matched.group(4) + "\n" + block)
            pdf = select_minutes_pdf(key, posts) if key else None
            name = _minutes_filename(pdf, key) if pdf and key else ""
            if name and f"downloads/{name}" not in block:
                lines.insert(i + 1, "")
                lines.insert(i + 2, f"    <!-- source: pdf|downloads/{name} -->")
                report.append(f"attached {key[0]} {key[1]} {key[2]} {key[3]}")
                i = block_end + 2
                continue
        i += 1
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), report
