#!/usr/bin/env python3
"""
Quality-updates 문서의 날짜순 리스트를 과거→현재 순으로 재정렬합니다.
한국회계기준원 주요일정 섹션은 이미 시간 순이므로 변경하지 않습니다.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional


# 날짜 패턴: 앞에 공백 있을 수 있음 (Appendix 등), - (YY-MM-DD)
DATE_PATTERN = re.compile(r'^(\s*)- \((\d{2})-(\d{2})-(\d{2})\) ')


def parse_date_from_line(line: str) -> Optional[tuple[str, tuple[int, int, int]]]:
    """라인에서 (YY-MM-DD) 파싱. (들여쓰기, (year, month, day)) 반환."""
    m = DATE_PATTERN.match(line)
    if not m:
        return None
    indent, yy, mm, dd = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    year = 2000 + yy
    return (indent, (year, mm, dd))


def process_file(filepath: Path, dry_run: bool = False) -> bool:
    """단일 파일 처리: dated list를 과거→현재 순으로 정렬 (한국회계기준원 주요일정 제외).
    Returns True if file was updated (or would be updated in dry_run)."""
    text = filepath.read_text(encoding='utf-8')
    lines = text.split('\n')

    output: list[str] = []
    i = 0

    # 컨텍스트: 한국회계기준원 섹션인지, 주요일정 하위섹션인지
    in_kasb = False
    in_main_schedule = False

    while i < len(lines):
        line = lines[i]

        # 섹션 헤더 추적
        if line.strip().startswith('### ') and '한국회계기준원' in line:
            in_kasb = True
            in_main_schedule = False
        elif line.strip().startswith('### '):
            in_kasb = False
            in_main_schedule = False
        elif '주요일정' in line and (line.strip().startswith('#### ') or '**주요일정**' in line):
            in_main_schedule = in_kasb
        elif line.strip().startswith('#### ') and '주요일정' not in line:
            in_main_schedule = False
        elif '??? info "한국회계기준원"' in line:
            in_kasb = True
            in_main_schedule = False
        elif '??? info "' in line and '한국회계기준원' not in line:
            in_kasb = False
            in_main_schedule = False
        elif '**' in line and '주요일정' in line and in_kasb:
            in_main_schedule = True
        elif '**' in line and '주요일정' not in line:
            if in_kasb:
                in_main_schedule = False

        parsed = parse_date_from_line(line)
        if parsed is not None and not in_main_schedule:
            indent, dt = parsed
            items: list[tuple[tuple[int, int, int], str]] = []
            j = i
            while j < len(lines):
                curr_line = lines[j]
                curr_parsed = parse_date_from_line(curr_line)
                if curr_parsed is not None:
                    _, curr_dt = curr_parsed
                    item_lines = [curr_line]
                    k = j + 1
                    while k < len(lines):
                        nxt = lines[k]
                        if parse_date_from_line(nxt) is not None:
                            break
                        if nxt.strip().startswith('###') or (nxt.strip().startswith('---') and len(output) > 0 and '---' in ''.join(output[-5:])):
                            break
                        # ??? info at 4 spaces = new Appendix agency block; 8+ spaces = nested, don't break
                        if re.match(r'^    \?\?\? info "', nxt):
                            break
                        if re.match(r'^\s*\*\*[^*]+\*\*\s*$', nxt.strip()):
                            break
                        if re.match(r'^\s*####\s+', nxt) and '주요일정' not in nxt:
                            break
                        item_lines.append(nxt)
                        k += 1
                    items.append((curr_dt, '\n'.join(item_lines)))
                    j = k
                else:
                    j += 1
                    break
            if items:
                sorted_items = sorted(items, key=lambda x: x[0])
                for _, item_text in sorted_items:
                    output.append(item_text)
                i = j
                continue

        output.append(line)
        i += 1

    new_text = '\n'.join(output)
    if new_text != text:
        if not dry_run:
            filepath.write_text(new_text, encoding='utf-8')
        print(f"Updated: {filepath}")
        return True
    else:
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
