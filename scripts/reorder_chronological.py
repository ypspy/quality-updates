#!/usr/bin/env python3
"""
Quality-updates 문서의 날짜순 리스트를 과거→현재 순으로 재정렬합니다.
#### 하위섹션 단위로만 정렬하며 ###/#### 헤더는 유지합니다.
한국회계기준원 주요일정 섹션은 이미 시간 순이므로 변경하지 않습니다.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional


DATE_PATTERN = re.compile(r"^(\s*)- \((\d{2})-(\d{2})-(\d{2})\) ")
APPENDIX_RE = re.compile(r"^## Appendix A\b")
SUBSECTION_RE = re.compile(r"^####\s+")
AGENCY_RE = re.compile(r"^###\s+")


def _appendix_boundary(lines: list[str]) -> int:
    for idx, line in enumerate(lines):
        if APPENDIX_RE.match(line.strip()):
            return idx
    return len(lines)


def parse_date_from_line(line: str) -> Optional[tuple[str, tuple[int, int, int]]]:
    m = DATE_PATTERN.match(line)
    if not m:
        return None
    indent, yy, mm, dd = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    year = 2000 + yy
    return (indent, (year, mm, dd))


def _is_schedule_subsection(header_line: str, in_kasb: bool) -> bool:
    return in_kasb and "주요일정" in header_line


def _extract_item_block(lines: list[str], start: int) -> tuple[str, int]:
    item_lines = [lines[start]]
    k = start + 1
    while k < len(lines):
        nxt = lines[k]
        if parse_date_from_line(nxt) is not None:
            break
        if SUBSECTION_RE.match(nxt.strip()) or AGENCY_RE.match(nxt.strip()):
            break
        if APPENDIX_RE.match(nxt.strip()):
            break
        if nxt.strip().startswith("---"):
            break
        item_lines.append(nxt)
        k += 1
    return "\n".join(item_lines), k


def _sort_subsection_items(lines: list[str], start: int, end: int) -> list[str]:
    items: list[tuple[tuple[int, int, int], str]] = []
    prefix: list[str] = []
    i = start
    while i < end:
        line = lines[i]
        parsed = parse_date_from_line(line)
        if parsed is None:
            prefix.append(line)
            i += 1
            continue
        _, dt = parsed
        block, i = _extract_item_block(lines, i)
        items.append((dt, block))
    if not items:
        return lines[start:end]
    sorted_blocks = [block for _, block in sorted(items, key=lambda x: x[0])]
    out = prefix[:]
    for idx, block in enumerate(sorted_blocks):
        if out and out[-1].strip() != "":
            out.append("")
        out.append(block)
    return out


def process_file(filepath: Path, dry_run: bool = False) -> bool:
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")
    appendix_start = _appendix_boundary(lines)
    main_lines = lines[:appendix_start]
    appendix_lines = lines[appendix_start:]

    output: list[str] = []
    i = 0
    in_kasb = False

    while i < len(main_lines):
        line = main_lines[i]

        if AGENCY_RE.match(line.strip()):
            in_kasb = "한국회계기준원" in line
            output.append(line)
            i += 1
            continue

        if SUBSECTION_RE.match(line.strip()):
            header = line
            output.append(header)
            i += 1
            if _is_schedule_subsection(header, in_kasb):
                while i < len(main_lines):
                    nxt = main_lines[i]
                    if SUBSECTION_RE.match(nxt.strip()) or AGENCY_RE.match(nxt.strip()):
                        break
                    output.append(nxt)
                    i += 1
                continue

            subsection_start = i
            while i < len(main_lines):
                nxt = main_lines[i]
                if SUBSECTION_RE.match(nxt.strip()) or AGENCY_RE.match(nxt.strip()):
                    break
                i += 1
            output.extend(_sort_subsection_items(main_lines, subsection_start, i))
            continue

        output.append(line)
        i += 1

    if appendix_lines:
        if output and appendix_lines and output[-1].strip() != "":
            output.append("")
        output.extend(appendix_lines)

    new_text = "\n".join(output)
    if new_text != text:
        if not dry_run:
            filepath.write_text(new_text, encoding="utf-8")
        print(f"Updated: {filepath}")
        return True
    print(f"No change: {filepath}")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Quality-updates 문서의 날짜순 리스트를 과거→현재 순으로 재정렬합니다."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="대상 파일 경로. 미지정 시 docs/quality-updates/ 전체 처리",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="변경 사항 미적용, 변경 여부만 출력",
    )
    args = parser.parse_args()

    docs_dir = Path(__file__).resolve().parent.parent / "docs" / "quality-updates"

    if args.files:
        file_paths: list[Path] = []
        for fp in args.files:
            p = Path(fp)
            if not p.exists():
                print(f"Error: 파일을 찾을 수 없습니다: {fp}", file=sys.stderr)
                sys.exit(1)
            file_paths.append(p.resolve())
    else:
        if not docs_dir.exists():
            print("Docs directory not found", file=sys.stderr)
            sys.exit(1)
        md_files = sorted(docs_dir.rglob("*.md"))
        file_paths = [f for f in md_files if "AGENT_INSTRUCTION" not in f.name]

    for f in file_paths:
        process_file(f, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
