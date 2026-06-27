#!/usr/bin/env python3
"""Rebuild quarterly .md main body: agency/subsection headers + chronological blocks."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LINK_RE = re.compile(
    r"^- \((\d{2})-(\d{2})-(\d{2})\) \[(.+?)\]\((https?://[^\)]+)\)"
)
APPENDIX_RE = re.compile(r"^## Appendix A\b")
FRONTMATTER_RE = re.compile(r"^---\s*$")

SECTIONS: list[tuple[str, list[str]]] = [
    ("금융감독원", ["보도자료", "세칙제ㆍ개정예고", "회계감독 동향자료"]),
    ("금융위원회", ["보도자료", "고시/공고/훈령", "입법예고/규정변경예고"]),
    ("한국공인회계사회", ["알림마당 - 공지사항", "회계감사 - 감사인증기준"]),
    (
        "한국회계기준원",
        ["소통광장 - 공지사항", "소통광장 - 보도자료", "주요일정"],
    ),
]


def _date_key(yy: str, mm: str, dd: str) -> tuple[int, int, int]:
    return (2000 + int(yy), int(mm), int(dd))


def classify_url(url: str) -> tuple[str, str]:
    if "fss.or.kr" in url:
        if "lrgRegItnPrvntc" in url or "lrgSlno" in url:
            return "금융감독원", "세칙제ㆍ개정예고"
        if "B0000154" in url or "menuNo=200467" in url:
            return "금융감독원", "회계감독 동향자료"
        return "금융감독원", "보도자료"
    if "fsc.go.kr" in url:
        if "/po040301/" in url or "po040301/view" in url:
            return "금융위원회", "입법예고/규정변경예고"
        if "/po040200/" in url or "po040200/" in url:
            return "금융위원회", "고시/공고/훈령"
        return "금융위원회", "보도자료"
    if "kicpa.or.kr" in url:
        if "sumboard" in url.lower() or "cmpBrdId=sum" in url:
            return "한국공인회계사회", "회계감사 - 감사인증기준"
        return "한국공인회계사회", "알림마당 - 공지사항"
    if "kasb.or.kr" in url:
        if "calView" in url:
            return "한국회계기준원", "주요일정"
        if "comm020" in url:
            return "한국회계기준원", "소통광장 - 보도자료"
        return "한국회계기준원", "소통광장 - 공지사항"
    raise ValueError(f"Unclassified URL: {url}")


def split_document(text: str) -> tuple[str, list[str], list[str]]:
    lines = text.split("\n")
    if not lines or not FRONTMATTER_RE.match(lines[0]):
        raise ValueError("Expected YAML frontmatter")
    end = 1
    while end < len(lines) and not (end > 0 and FRONTMATTER_RE.match(lines[end])):
        end += 1
    if end >= len(lines):
        raise ValueError("Unclosed frontmatter")
    frontmatter = "\n".join(lines[: end + 1])
    body = lines[end + 1 :]
    appendix_idx = next(
        (i for i, ln in enumerate(body) if APPENDIX_RE.match(ln.strip())),
        len(body),
    )
    return frontmatter, body[:appendix_idx], body[appendix_idx:]


def extract_blocks(main_lines: list[str]) -> list[tuple[tuple[int, int, int], str, str]]:
    """Return (date_key, url, block_text) for each top-level link item."""
    blocks: list[tuple[tuple[int, int, int], str, str]] = []
    i = 0
    while i < len(main_lines):
        line = main_lines[i]
        m = LINK_RE.match(line)
        if not m:
            i += 1
            continue
        yy, mm, dd, _title, url = m.groups()
        item_lines = [line]
        k = i + 1
        while k < len(main_lines):
            nxt = main_lines[k]
            if LINK_RE.match(nxt):
                break
            if nxt.strip().startswith("###"):
                break
            if nxt.strip().startswith("####"):
                break
            if APPENDIX_RE.match(nxt.strip()):
                break
            item_lines.append(nxt)
            k += 1
        blocks.append((_date_key(yy, mm, dd), url, "\n".join(item_lines).rstrip()))
        i = k
    return blocks


def dedupe_blocks(
    blocks: list[tuple[tuple[int, int, int], str, str]],
) -> list[tuple[tuple[int, int, int], str, str]]:
    """Keep richest block per URL (notes/source beat bare link)."""
    by_url: dict[str, tuple[tuple[int, int, int], str, str]] = {}
    for item in blocks:
        url = item[1]
        prev = by_url.get(url)
        if prev is None or len(item[2]) > len(prev[2]):
            by_url[url] = item
    return list(by_url.values())


def rebuild_main_body(blocks: list[tuple[tuple[int, int, int], str, str]]) -> str:
    grouped: dict[tuple[str, str], list[tuple[tuple[int, int, int], str, str]]] = {}
    for item in blocks:
        agency, subsection = classify_url(item[1])
        grouped.setdefault((agency, subsection), []).append(item)

    parts: list[str] = []
    for agency, subsections in SECTIONS:
        parts.append(f"### {agency}\n")
        first_sub = True
        for subsection in subsections:
            items = grouped.pop((agency, subsection), [])
            if not items:
                continue
            if not first_sub:
                parts.append("")
            first_sub = False
            parts.append(f"#### {subsection}\n")
            items.sort(key=lambda x: x[0])
            for idx, (_dt, _url, block) in enumerate(items):
                if idx:
                    parts.append("")
                parts.append(block)
        parts.append("")

    if grouped:
        unknown = ", ".join(f"{a}/{s}" for a, s in grouped)
        raise ValueError(f"Unplaced blocks after rebuild: {unknown}")

    return "\n".join(parts).rstrip() + "\n"


def repair_file(filepath: Path, dry_run: bool = False) -> bool:
    text = filepath.read_text(encoding="utf-8")
    frontmatter, main_lines, appendix_lines = split_document(text)
    blocks = dedupe_blocks(extract_blocks(main_lines))
    new_main = rebuild_main_body(blocks)
    appendix = "\n".join(appendix_lines).rstrip()
    new_text = frontmatter + "\n\n" + new_main
    if appendix:
        new_text += "\n" + appendix + "\n"
    if new_text != text:
        if not dry_run:
            filepath.write_text(new_text, encoding="utf-8")
        print(f"Repaired: {filepath} ({len(blocks)} blocks)")
        return True
    print(f"No change: {filepath}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild quarterly md agency/subsection structure.")
    parser.add_argument("files", nargs="+", help="Target .md file(s)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    for fp in args.files:
        path = Path(fp)
        if not path.exists():
            print(f"Error: not found: {fp}", file=sys.stderr)
            return 1
        repair_file(path.resolve(), dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
