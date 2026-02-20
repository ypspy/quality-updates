#!/usr/bin/env python3
"""
Quality-updates 마크다운 문서 콘텐츠 검증 스크립트.
admonition 들여쓰기, YAML front matter, 날짜 형식, 테이블 스키마 등을 검사합니다.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple


class ValidationError(NamedTuple):
    line_no: int
    code: str
    message: str
    severity: str  # "error" | "warning"


# AGENT_INSTRUCTION 기준 테이블 헤더
TYPE_A_HEADER = "| 회사명 | 대상자 | 위반내용 | 과징금 부과액 |"
TYPE_B_HEADER_1 = "| 회사명 | 구분 | 주요 지적사항 | 주요 조치 |"
TYPE_B_HEADER_2 = "| 회사 | 주요 지적사항 | 대상 | 조치 |"

DATE_PATTERN = re.compile(r"\(\d{2}-\d{2}-\d{2}\)")


def _is_admonition_line(line: str) -> bool:
    return bool(re.match(r"^\s*(!!!|\?\?\?)\s+(note|info|warning|success|danger)\s+", line))


def validate_admonitions(lines: list[str], path: Path) -> list[ValidationError]:
    """admonition 들여쓰기 + 빈 줄 규칙 통합 검증."""
    errors: list[ValidationError] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not _is_admonition_line(line):
            i += 1
            continue

        base_indent = len(line) - len(line.lstrip())
        required_content = base_indent + 4
        j = i + 1

        while j < len(lines):
            nxt = lines[j]
            stripped = nxt.strip()
            if not stripped:
                j += 1
                continue
            curr_indent = len(nxt) - len(nxt.lstrip())
            if curr_indent <= base_indent and (stripped.startswith("###") or stripped.startswith("- (") or stripped.startswith("---")):
                break
            if j == i + 1:
                errors.append(
                    ValidationError(j + 1, "ADMON_BLANK", "!!!/??? 줄과 첫 내용 줄 사이에 빈 줄 1개 필요", "warning")
                )
            if curr_indent > base_indent and curr_indent < required_content:
                if not stripped.startswith("|"):
                    errors.append(
                        ValidationError(
                            j + 1,
                            "ADMON_INDENT",
                            f"admonition 내용은 4칸 추가 들여쓰기 필요 (현재 {curr_indent - base_indent}칸)",
                            "warning",
                        )
                    )
            j += 1
        i += 1
    return errors


def validate_yaml_frontmatter(lines: list[str], path: Path) -> list[ValidationError]:
    """YAML front matter 필수 키 검증."""
    errors: list[ValidationError] = []
    if not lines or lines[0].strip() != "---":
        return errors
    keys = set()
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        m = re.match(r"^([a-zA-Z_]+):", lines[i])
        if m:
            keys.add(m.group(1))
        i += 1
    if "title" not in keys:
        errors.append(ValidationError(1, "YAML_TITLE", "YAML front matter에 'title' 필수", "error"))
    if "period" not in keys and "period_label" not in keys:
        errors.append(ValidationError(1, "YAML_PERIOD", "YAML front matter에 'period' 또는 'period_label' 필수", "warning"))
    return errors


def validate_date_format(lines: list[str], path: Path) -> list[ValidationError]:
    """날짜 (YY-MM-DD) 패턴 일관성 검증."""
    errors: list[ValidationError] = []
    for i, line in enumerate(lines):
        bad = re.findall(r"\((\d{4}-\d{2}-\d{2})\)", line)
        if bad:
            errors.append(
                ValidationError(
                    i + 1,
                    "DATE_FMT",
                    f"날짜는 (YY-MM-DD) 형식 사용. (YYYY-MM-DD) 검출: {bad[0]}",
                    "warning",
                )
            )
    return errors


def _normalize_table_header(line: str) -> str:
    """표 헤더 행을 정규 형식으로 정규화 (공백 정리)."""
    parts = [s.strip() for s in line.strip().split("|")[1:-1] if s.strip()]
    return "| " + " | ".join(parts) + " |"


def validate_table_schema(lines: list[str], path: Path) -> list[ValidationError]:
    """Type A/B 제재 표 열 이름 검증."""
    errors: list[ValidationError] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            if "회사명" in stripped and "대상자" in stripped and "위반내용" in stripped and "과징금 부과액" in stripped:
                normalized = _normalize_table_header(line)
                if normalized != TYPE_A_HEADER:
                    errors.append(
                        ValidationError(
                            i + 1,
                            "TABLE_A",
                            f"Type A 표 헤더는 정확히 '{TYPE_A_HEADER}' 이어야 함",
                            "warning",
                        )
                    )
            elif "회사명" in stripped and "구분" in stripped and "주요 지적사항" in stripped and "주요 조치" in stripped:
                normalized = _normalize_table_header(line)
                if normalized != TYPE_B_HEADER_1:
                    errors.append(
                        ValidationError(
                            i + 1,
                            "TABLE_B1",
                            f"Type B 회사별 표 헤더는 '{TYPE_B_HEADER_1}' 이어야 함",
                            "warning",
                        )
                    )
            elif "회사" in stripped and "주요 지적사항" in stripped and "대상" in stripped and "조치" in stripped:
                if "회사명" in stripped:
                    continue
                normalized = _normalize_table_header(line)
                if normalized != TYPE_B_HEADER_2:
                    errors.append(
                        ValidationError(
                            i + 1,
                            "TABLE_B2",
                            f"Type B 감사인 표 헤더는 '{TYPE_B_HEADER_2}' 이어야 함",
                            "warning",
                        )
                    )
    return errors


def validate_file(filepath: Path, strict: bool) -> list[ValidationError]:
    """단일 파일 검증."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return [ValidationError(0, "READ", str(e), "error")]
    lines = text.split("\n")
    all_errors: list[ValidationError] = []
    for fn in [
        validate_admonitions,
        validate_yaml_frontmatter,
        validate_date_format,
        validate_table_schema,
    ]:
        all_errors.extend(fn(lines, filepath))
    if strict:
        all_errors = [e for e in all_errors if e.severity in ("error", "warning")]
    else:
        all_errors = [e._replace(severity="warning") if e.severity == "warning" else e for e in all_errors]
    return all_errors


def main():
    parser = argparse.ArgumentParser(description="Quality-updates 마크다운 문서 콘텐츠 검증")
    parser.add_argument(
        "files",
        nargs="*",
        help="대상 파일. 미지정 시 docs/quality-updates/ 전체",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="경고도 에러로 처리",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    docs_dir = repo_root / "docs" / "quality-updates"

    if args.files:
        paths = []
        for f in args.files:
            p = Path(f)
            if not p.is_absolute():
                p = repo_root / f
            p = p.resolve()
            if p.exists():
                paths.append(p)
            else:
                print(f"Warning: 파일 없음 {f}", file=sys.stderr)
    else:
        paths = sorted(docs_dir.rglob("*.md"))
        paths = [p for p in paths if "AGENT_INSTRUCTION" not in p.name]

    total_errors = 0
    for fp in paths:
        errs = validate_file(fp, args.strict)
        err_count = sum(1 for e in errs if e.severity == "error")
        warn_count = sum(1 for e in errs if e.severity == "warning")
        if args.strict:
            err_count += warn_count
        total_errors += err_count
        rel = fp.relative_to(repo_root) if repo_root in fp.parents else fp
        for e in errs:
            sev = "ERROR" if e.severity == "error" else "WARN"
            if args.strict and e.severity == "warning":
                sev = "ERROR"
            print(f"{rel}:{e.line_no}: [{sev}] {e.code}: {e.message}")
        if errs:
            print(f"  → {err_count} error(s), {warn_count} warning(s)")
    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
