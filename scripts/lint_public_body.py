#!/usr/bin/env python3
"""공개 분기 문서 본문 린트.

docs/quality-updates/**.md 에서 작성 지시·내부 메모·의사록 쪽번호·
기계 문장·회차 제목 링크 반복·trailing-dot 호스트를 찾는다.
HTML 주석은 공개 본문이 아니므로 검사하지 않는다.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

DEFAULT_MAX_HEADING_REPEATS = 3

PROCESS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("process_instruction", re.compile(r"의결서는 로컬에 없다")),
    ("process_instruction", re.compile(r"의결서 공개본은 미입수")),
    ("process_instruction", re.compile(r"의결서는?\s*미입수")),
    ("process_instruction", re.compile(r"로컬 폴더가 없어")),
    ("process_instruction", re.compile(r"로컬에 없어 미입수")),
    ("process_instruction", re.compile(r"풀어 만들지 않는다")),
    ("process_instruction", re.compile(r"풀어 표로 적지 않는다")),
    ("process_instruction", re.compile(r"풀어 적지 않는다")),
    ("process_instruction", re.compile(r"표로 적지 않는다")),
    ("process_instruction", re.compile(r"요약은 표의")),
    ("process_instruction", re.compile(r"질의 문답이 없으면")),
    ("process_instruction", re.compile(r"논의[·/]진술 문면은")),
    ("process_instruction", re.compile(r"이 작업에서 다시 세지")),
    ("process_instruction", re.compile(r"보도 링크는 위 URL")),
    ("process_instruction", re.compile(r"이 날짜는 보도 게시일")),
    ("process_instruction", re.compile(r"아래는 의사록 문면")),
    ("process_instruction", re.compile(r"아래는 보도 제목 범위만")),
    ("process_instruction", re.compile(r"금액 표는 첨부")),
    ("process_instruction", re.compile(r"보도 첨부·본문을 풀어")),
    ("process_instruction", re.compile(r"첨부·본문을 풀어")),
    ("process_instruction", re.compile(r"이 호의 회사명·조치·금액은 확인하지 못했")),
    ("process_instruction", re.compile(r"입수한 보도 붙임에 이 호의 대응 칸이 없다")),
)

MEMO_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("internal_memo", re.compile(r"Mint notes")),
    ("internal_memo", re.compile(r"Mint r1/r2")),
    ("internal_memo", re.compile(r"Mint r[12]")),
    ("internal_memo", re.compile(r"Mint 분류")),
    ("internal_memo", re.compile(r"열린 질문")),
    ("internal_memo", re.compile(r"보류함")),
)

MECHANICAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("mechanical_sentence", re.compile(r"결과는 각각 원안 의결함이다")),
    ("mechanical_sentence", re.compile(r"결과는 원안 의결함이다")),
    ("mechanical_sentence", re.compile(r"질의 문답이 의사록에 있다")),
    ("mechanical_sentence", re.compile(r"문면은 위 조치내역 인용과 같다")),
)

# (의사록) -2- / (의사록) - 2 -  와, 줄 전체가 쪽번호인 불릿(- 10-).
MINUTES_PAGE_INLINE = re.compile(r"\(의사록\)\s*-\s*\d+\s*-")
MINUTES_PAGE_BULLET = re.compile(r"^\s*-\s*(?:\(의사록\)\s*)?-\s*\d+\s*-\s*$")
MINUTES_PAGE_BARE = re.compile(r"^\s*-\s+\d{1,3}\s*-\s*$")

TRAILING_DOT_HOST = re.compile(r"https?://[^/\s)>\"]+\./")

# - (26-07-09) [제목](url)  및  [[증선위]제목](url)
HEADING_LINK = re.compile(
    r"^-\s+\([^)]+\)\s+\[(?:[^\[\]]|\[[^\[\]]*\])*\]\((https?://[^)]+)\)",
    re.MULTILINE,
)

SANCTIONS_HEADER = "#### 제재 의결"
NEXT_HEADER = "#### 고시/공고/훈령"

DROP_QUERY = {
    "curpage",
    "srchctgry",
    "srchkey",
    "srchtext",
    "srchbegindt",
    "srchenddt",
    "pageindex",
    "sdate",
    "edate",
    "searchcnd",
    "searchwrd",
    "menuno",
}

LINE_RULES = PROCESS_PATTERNS + MEMO_PATTERNS + MECHANICAL_PATTERNS


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.message}"


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def default_allow_path(root: Path) -> Path:
    return root / "scripts" / "lint-public-body-allow.txt"


def load_allow_list(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    allowed: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        allowed.add(line.replace("\\", "/"))
    return allowed


def visible_lines(text: str) -> list[tuple[int, str]]:
    """HTML 주석을 뺀 공개 줄. 줄 번호는 원문 기준 1부터."""
    out: list[tuple[int, str]] = []
    in_comment = False
    for idx, raw in enumerate(text.splitlines(), start=1):
        line = raw
        visible = ""
        i = 0
        while i < len(line):
            if not in_comment:
                start = line.find("<!--", i)
                if start == -1:
                    visible += line[i:]
                    break
                visible += line[i:start]
                end = line.find("-->", start + 4)
                if end == -1:
                    in_comment = True
                    break
                i = end + 3
            else:
                end = line.find("-->", i)
                if end == -1:
                    break
                in_comment = False
                i = end + 3
        out.append((idx, visible))
    return out


def canonical_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.endswith("."):
        host = host[:-1]
    kept: list[tuple[str, str]] = []
    for key, values in parse_qs(parsed.query, keep_blank_values=False).items():
        if key.lower() in DROP_QUERY:
            continue
        for value in values:
            kept.append((key.lower(), value))
    kept.sort()
    query = urlencode(kept)
    return f"{host}{parsed.path}" + (f"?{query}" if query else "")


def sanctions_section(text: str) -> str | None:
    start = text.find(SANCTIONS_HEADER)
    if start < 0:
        return None
    end = text.find(NEXT_HEADER, start)
    return text[start:end] if end > start else text[start:]


def lint_lines(rel_path: str, lines: list[tuple[int, str]]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[int, str, int]] = set()
    for number, line in lines:
        for rule, pattern in LINE_RULES:
            match = pattern.search(line)
            if not match:
                continue
            key = (number, rule, match.start())
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(rel_path, number, rule, f"{match.group(0)!r}")
            )
        if MINUTES_PAGE_INLINE.search(line) or MINUTES_PAGE_BULLET.match(line) or MINUTES_PAGE_BARE.match(line):
            snippet = line.strip()
            findings.append(
                Finding(rel_path, number, "minutes_page", f"의사록 쪽번호 {snippet!r}")
            )
        for match in TRAILING_DOT_HOST.finditer(line):
            findings.append(
                Finding(
                    rel_path,
                    number,
                    "trailing_dot_host",
                    f"호스트 끝 점 {match.group(0)!r}",
                )
            )
    return findings


def lint_repeated_heading_urls(
    rel_path: str,
    text: str,
    lines: list[tuple[int, str]],
    max_repeats: int,
) -> list[Finding]:
    visible_text = "\n".join(line for _, line in lines)
    section = sanctions_section(visible_text)
    if not section:
        return []

    # 제재 의결 절이 원문에서 몇 번째 줄인지 찾아, 제목 링크 줄 번호를 맞춘다.
    original_start = next((n for n, line in lines if SANCTIONS_HEADER in line), 1)
    counts: Counter[str] = Counter()
    first_line: dict[str, int] = {}
    for offset, line in enumerate(section.splitlines()):
        match = HEADING_LINK.match(line)
        if not match:
            continue
        key = canonical_url(match.group(1))
        counts[key] += 1
        first_line.setdefault(key, original_start + offset)

    findings: list[Finding] = []
    for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        if count > max_repeats:
            findings.append(
                Finding(
                    rel_path,
                    first_line[key],
                    "repeated_heading_url",
                    f"제재 의결 제목 링크가 같은 회차 URL을 {count}회 반복함 (허용 {max_repeats}회 이하): {key}",
                )
            )
    return findings


def lint_text(
    rel_path: str,
    text: str,
    *,
    max_heading_repeats: int = DEFAULT_MAX_HEADING_REPEATS,
) -> list[Finding]:
    lines = visible_lines(text)
    findings = lint_lines(rel_path, lines)
    findings.extend(
        lint_repeated_heading_urls(rel_path, text, lines, max_heading_repeats)
    )
    findings.sort(key=lambda item: (item.path, item.line, item.rule, item.message))
    return findings


def iter_quarter_files(root: Path) -> list[Path]:
    base = root / "docs" / "quality-updates"
    return sorted(
        path
        for path in base.rglob("*.md")
        if path.is_file() and path.name != "index.md"
    )


# 허용 목록 파일의 모든 규칙, 그리고 연도 본문을 고치지 않고 남은
# trailing-dot 호스트는 경고다. 경고만 있으면 종료 코드는 0이다.
WARNING_RULES = frozenset({"trailing_dot_host"})


def is_warning(item: Finding, allowed: set[str]) -> bool:
    return item.path in allowed or item.rule in WARNING_RULES


def partition_findings(
    findings: list[Finding], allowed: set[str]
) -> tuple[list[Finding], list[Finding]]:
    errors: list[Finding] = []
    warnings: list[Finding] = []
    for item in findings:
        (warnings if is_warning(item, allowed) else errors).append(item)
    return errors, warnings


def count_by_year_rule(findings: list[Finding]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for item in findings:
        parts = item.path.split("/")
        year = parts[2] if len(parts) > 2 else "?"
        year_counts = counts.setdefault(year, {})
        year_counts[item.rule] = year_counts.get(item.rule, 0) + 1
    return counts


def format_year_rule_counts(findings: list[Finding]) -> str:
    lines: list[str] = []
    counts = count_by_year_rule(findings)
    for year in sorted(counts):
        total = sum(counts[year].values())
        lines.append(f"  {year}: {total}")
        for rule in sorted(counts[year]):
            lines.append(f"    {rule}: {counts[year][rule]}")
    return "\n".join(lines)


def lint_repo(
    root: Path,
    *,
    allow: set[str] | None = None,
    max_heading_repeats: int = DEFAULT_MAX_HEADING_REPEATS,
    skip_allowed: bool = False,
) -> list[Finding]:
    allowed = allow or set()
    findings: list[Finding] = []
    for path in iter_quarter_files(root):
        rel = path.relative_to(root).as_posix()
        if skip_allowed and rel in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        findings.extend(
            lint_text(rel, text, max_heading_repeats=max_heading_repeats)
        )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="공개 본문 린트")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="저장소 루트 (기본: 이 스크립트의 상위)",
    )
    parser.add_argument(
        "--allow",
        type=Path,
        default=None,
        help="임시 허용 목록 (기본: scripts/lint-public-body-allow.txt)",
    )
    parser.add_argument(
        "--no-allow",
        action="store_true",
        help="허용 목록을 쓰지 않는다",
    )
    parser.add_argument(
        "--max-heading-repeats",
        type=int,
        default=DEFAULT_MAX_HEADING_REPEATS,
        help="제재 의결 제목에서 같은 URL을 허용하는 최대 횟수 (초과 시 실패)",
    )
    args = parser.parse_args(argv)
    root = (args.root or repo_root_from_script()).resolve()
    allow_path = None if args.no_allow else (args.allow or default_allow_path(root))
    allowed = load_allow_list(allow_path)
    findings = lint_repo(
        root, allow=allowed, max_heading_repeats=args.max_heading_repeats
    )
    errors, warnings = partition_findings(findings, allowed)
    for item in errors:
        print(item.format(), file=sys.stderr)
    allow_warnings = [item for item in warnings if item.path in allowed]
    other_warnings = [item for item in warnings if item.path not in allowed]
    if allow_warnings:
        print(
            "lint_public_body: allow-list warnings "
            f"({len(allow_warnings)}; 2012·2013 임시 허용, 이후 단계에서 목록을 지운다):",
            file=sys.stderr,
        )
        print(format_year_rule_counts(allow_warnings), file=sys.stderr)
    if other_warnings:
        print(
            "lint_public_body: other warnings "
            f"({len(other_warnings)}; 연도 파일을 고치지 않아 실패로 보지 않음):",
            file=sys.stderr,
        )
        print(format_year_rule_counts(other_warnings), file=sys.stderr)
    if errors:
        print(f"lint_public_body: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("lint_public_body: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
