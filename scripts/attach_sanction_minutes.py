from __future__ import annotations

import re
from dataclasses import dataclass

LINK_RE = re.compile(r"^- \((\d{2})-(\d{2})-(\d{2})\) \[(.+?)\]\((https?://[^\)]+)\)")
KEY_RE = re.compile(
    r"(20\d{2}|'\d{2}|’\d{2}).{0,40}?(제\s*(\d+)\s*차)\s*(증권선물위원회|금융위원회)"
)
KIND_RE = re.compile(r"임시|서면")


@dataclass(frozen=True)
class DecisionPost:
    year: int
    committee: str
    kind: str
    number: int
    pdf_url: str
    zip_urls: list[str]


def meeting_key(text: str) -> tuple[int, str, str, int] | None:
    # Year follows 제N차 in the sample title, so the match reaches the same
    # meeting on the next line. DOTALL lets '.' cross that newline, and the
    # 40-character window fits after spaces are removed.
    pattern = re.compile(KEY_RE.pattern, KEY_RE.flags | re.DOTALL)
    matched = pattern.search(text) or pattern.search(text.replace(" ", ""))
    if not matched:
        return None
    raw_year, _nth, number, committee = matched.groups()
    year = int(raw_year.replace("'", "20").replace("’", "20"))
    if year < 100:
        year += 2000
    if "임시" in text:
        kind = "임시"
    elif KIND_RE.search(text):
        kind = "서면"
    else:
        kind = "정기"
    name = "증선위" if committee == "증권선물위원회" else "금융위"
    return year, name, kind, int(number)


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
            pdf = select_minutes_pdf(key, posts) if key else None
            name = pdf.rsplit("/", 1)[-1] if pdf else ""
            if name and f"downloads/{name}" not in block:
                lines.insert(i + 1, "")
                lines.insert(i + 2, f"    <!-- source: pdf|downloads/{name} -->")
                report.append(f"attached {key[0]} {key[1]} {key[2]} {key[3]}")
                i = block_end + 2
                continue
        i += 1
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), report
