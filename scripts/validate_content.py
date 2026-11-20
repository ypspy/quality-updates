#!/usr/bin/env python3
"""
Quality-updates 마크다운 문서 콘텐츠 검증 스크립트.
admonition 들여쓰기, YAML front matter, 날짜 형식, 테이블 스키마 등을 검사합니다.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from fss_review_cards import audit_review_html, materialize_review_markdown
from quarter_timing import (
    as_seoul,
    canonical_quarter_key,
    filename_bounds,
    front_matter_bounds,
    governing_update,
    iter_quarter_refs,
    load_allow_list,
    quarter_key_for_path,
)
from source_marker_layout import find_unsafe_source_layout


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

PHASE2_PATTERNS = [
    ("PHASE2_ES", re.compile(r"^#{2,3}\s+Executive Summary\s*$"), "error"),
    ("PHASE2_AGENCY", re.compile(r"^#{2,4}\s+기관별 요약\s*$"), "error"),
    ("PHASE2_IMPL", re.compile(r"^#{2,4}\s+시사점\s*$"), "error"),
    ("PHASE2_LEGACY", re.compile(r"^#{2,3}\s+요약\s*$"), "error"),
]

COLLAPSIBLE_NOTE = re.compile(r"^\s*\?\?\?\s+note\s+")


def validate_no_collapsible_note(lines: list[str], path: Path) -> list[ValidationError]:
    """Link-summary note must use !!! (non-collapsible); ??? info in Appendix remains allowed."""
    if path.name == "index.md":
        return []
    if "quality-updates" not in path.as_posix():
        return []
    errors: list[ValidationError] = []
    for i, line in enumerate(lines):
        if COLLAPSIBLE_NOTE.match(line):
            errors.append(
                ValidationError(
                    i + 1,
                    "COLLAPSIBLE_NOTE",
                    '링크 요약은 `!!! note` 사용 (`??? note` 금지). Appendix·중첩 `??? info`는 허용',
                    "error",
                )
            )
    return errors


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


def validate_source_layout(lines: list[str], path: Path) -> list[ValidationError]:
    """MkDocs 렌더를 깨는 source+note 배치 검출."""
    errors: list[ValidationError] = []
    for line_no, message in find_unsafe_source_layout(lines):
        errors.append(ValidationError(line_no, "SOURCE_LAYOUT", message, "error"))
    return errors


def validate_no_phase2(lines: list[str], path: Path) -> list[ValidationError]:
    """Phase 2 집계 요약 헤더 금지 (링크 note 접두어는 제외)."""
    if path.name == "index.md":
        return []
    if "quality-updates" not in path.as_posix():
        return []
    errors: list[ValidationError] = []
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        for code, pat, sev in PHASE2_PATTERNS:
            if pat.match(stripped):
                errors.append(
                    ValidationError(i + 1, code, f"Phase 2 헤더 금지: {stripped}", sev)
                )
    return errors


_LEGACY_MINUTES = re.compile(
    r"downloads/minutes-(?P<year>\d{4})-(?P<committee>증선위|금융위)-(?P<kind>정기|임시|서면)-(?P<number>\d+)(?:-추가)?\.pdf"
)
_LEGACY_BUNDLE = re.compile(
    r"downloads/sanctions/(?P<year>\d{4})-(?P<committee>증선위|금융위)-(?P<kind>정기|임시|서면)-(?P<number>\d+)차/"
)
_KALE_BUNDLE = re.compile(
    r"downloads/sanctions/(?P<year>\d{4})-(?P<committee>증선위|금융위)-(?:(?P<kind>임시|서면)-)?(?P<number>\d+)차/"
)


def _named_folder(match: re.Match[str], *, legacy: bool) -> str:
    year = match.group("year")
    committee = match.group("committee")
    number = match.group("number")
    kind = match.groupdict().get("kind")
    if kind in {"임시", "서면"}:
        return f"{year}-{committee}-{kind}-{number}차"
    if legacy and kind == "정기":
        return f"{year}-{committee}-정기-{number}차"
    return f"{year}-{committee}-{number}차"


def meeting_folders(text: str) -> set[str]:
    found: set[str] = set()
    for match in _LEGACY_MINUTES.finditer(text):
        found.add(_named_folder(match, legacy=True))
    for match in _LEGACY_BUNDLE.finditer(text):
        found.add(_named_folder(match, legacy=True))
    for match in _KALE_BUNDLE.finditer(text):
        found.add(_named_folder(match, legacy=False))
    return found


def unmatched_source_paths(record_text: str, folder: str) -> list[str]:
    paths: list[str] = []
    for line in record_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 5 or cells[1] not in {"agenda", "decision"} or cells[4] != "unmatched":
            continue
        paths.append(f"downloads/sanctions/{folder}/{cells[1]}/{cells[2]}")
    return paths


def validate_unpublished_sanctions(
    lines: list[str], path: Path, sanctions_root: Path
) -> list[ValidationError]:
    del path
    text = "\n".join(lines)
    errors: list[ValidationError] = []
    for folder in sorted(meeting_folders(text)):
        record = sanctions_root / folder / "record.md"
        if not record.is_file():
            continue
        for source in unmatched_source_paths(record.read_text(encoding="utf-8"), folder):
            if source not in text:
                errors.append(
                    ValidationError(1, "UNPUBLISHED_SOURCE", f"미연결 의안이 분기 문서에 없음: {source}", "error")
                )
    return errors


def validate_fss_review_cards(text: str) -> list[ValidationError]:
    """품질관리감리 카드 문장. 분기 문서 검사와 분리한다."""
    return [
        ValidationError(1, "FSS_REVIEW_CARD", message, "error")
        for message in audit_review_html(text)
    ]


_LINK_SOURCES = (
    Path("mkdocs.yml"),
    Path("docs/quality-updates/index.md"),
    Path("docs/index.md"),
)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


_LATEST_UPDATE = re.compile(r'^!!! info "Latest Update"\s*$')
_DATE_RANGE = re.compile(
    r"(?P<start>\d{4}-\d{2}-\d{2})\s*[~～]\s*(?P<end>\d{4}-\d{2}-\d{2})"
)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d %H:%M")


def _too_early_file_message(ends: list, stamp: str) -> str:
    if len({day.isoformat() for day in ends}) > 1:
        detail = f"파일명 종료일과 period.end 중 늦은 갱신일은 {stamp} KST"
    else:
        detail = f"기간 종료 {ends[0].isoformat()}의 갱신일은 {stamp} KST"
    return f"분기 갱신일 전 파일입니다. {detail}이며, 그 전에는 파일을 두거나 내용을 넣지 않습니다."


def quarter_timing_errors(
    repo_root: Path,
    now: datetime | None = None,
    allow: set[str] | None = None,
) -> list[tuple[Path, ValidationError]]:
    """Quarter files and nav/index links that appear before their update instant."""
    now = as_seoul(now)
    root = Path(repo_root)
    if allow is None:
        allow = load_allow_list(root / "data" / "qu-early-allow.txt")
    errors: list[tuple[Path, ValidationError]] = []

    docs = root / "docs" / "quality-updates"
    if docs.is_dir():
        for path in sorted(docs.rglob("*.md")):
            if quarter_key_for_path(path) is None:
                continue
            text = _read_text(path)
            if text is None:
                errors.append((path, ValidationError(0, "READ", f"파일을 읽지 못했습니다: {path.name}", "error")))
                continue
            errors.extend((path, err) for err in _file_timing_errors(path, text, now, allow))

    for rel in _LINK_SOURCES:
        source = root / rel
        text = _read_text(source)
        if text is None:
            continue
        errors.extend((source, err) for err in _link_timing_errors(root, text, now, allow))
        if rel.as_posix() == "docs/index.md":
            errors.extend((source, err) for err in _latest_update_errors(text, now))
    return errors


def _invalid_date_error(label: str, token) -> ValidationError | None:
    if not token.invalid:
        return None
    return ValidationError(
        token.line,
        "QUARTER_DATE_INVALID",
        f"{label} 값이 올바른 날짜가 아닙니다: {token.raw}",
        "error",
    )


def _file_timing_errors(path: Path, text: str, now: datetime, allow: set[str]) -> list[ValidationError]:
    key = quarter_key_for_path(path)
    bounds = filename_bounds(path.name)
    if key is None or bounds is None:
        return []
    filename_start, filename_end = bounds
    period_start, period_end = front_matter_bounds(text)
    errors: list[ValidationError] = []
    for label, token in (
        ("파일명 시작일", filename_start),
        ("파일명 종료일", filename_end),
        ("period.start", period_start),
        ("period.end", period_end),
    ):
        invalid = _invalid_date_error(label, token)
        if invalid is not None:
            errors.append(invalid)

    mismatches: list[str] = []
    if filename_start.value and period_start.value and filename_start.value != period_start.value:
        mismatches.append(
            f"시작일 파일명 {filename_start.value.isoformat()} / period.start {period_start.value.isoformat()}"
        )
    if filename_end.value and period_end.value and filename_end.value != period_end.value:
        mismatches.append(
            f"종료일 파일명 {filename_end.value.isoformat()} / period.end {period_end.value.isoformat()}"
        )
    if mismatches:
        line_no = period_end.line if period_end.value or period_end.invalid else period_start.line
        errors.append(
            ValidationError(
                line_no,
                "QUARTER_PERIOD_MISMATCH",
                "파일명과 front matter period가 다릅니다: " + "; ".join(mismatches),
                "error",
            )
        )

    ends = [token.value for token in (filename_end, period_end) if token.value is not None]
    if ends and key not in allow and now < governing_update(*ends):
        stamp = _stamp(governing_update(*ends))
        errors.append(
            ValidationError(1, "QUARTER_TOO_EARLY", _too_early_file_message(ends, stamp), "error")
        )
    return errors


def _link_timing_errors(root: Path, text: str, now: datetime, allow: set[str]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for year, name in iter_quarter_refs(line):
            key = canonical_quarter_key(year, name)
            if key in allow:
                continue
            bounds = filename_bounds(name)
            ends: list = []
            if bounds is None:
                continue
            filename_start, filename_end = bounds
            invalid = _invalid_date_error("링크 파일명의 종료일", filename_end)
            if invalid is not None:
                errors.append(invalid._replace(line_no=line_no))
            elif filename_end.value is not None:
                ends.append(filename_end.value)
            if filename_start.invalid:
                invalid_start = _invalid_date_error("링크 파일명의 시작일", filename_start)
                if invalid_start is not None:
                    errors.append(invalid_start._replace(line_no=line_no))
            target = root / key
            if target.is_file():
                target_text = _read_text(target)
                if target_text is not None:
                    _period_start, period_end = front_matter_bounds(target_text)
                    if period_end.value is not None:
                        ends.append(period_end.value)
            if not ends or not (now < governing_update(*ends)):
                continue
            stamp = _stamp(governing_update(*ends))
            errors.append(
                ValidationError(
                    line_no,
                    "QUARTER_LINK_TOO_EARLY",
                    f"분기 갱신일 전 링크입니다. {key} 의 갱신일은 {stamp} KST입니다.",
                    "error",
                )
            )
    return errors


def _latest_update_lines(text: str) -> list[tuple[int, str]]:
    """Body lines of the ``!!! info "Latest Update"`` admonition, with 1-based line numbers."""
    lines = text.splitlines()
    start = None
    base_indent = 0
    for index, line in enumerate(lines):
        if _LATEST_UPDATE.match(line.strip()):
            start = index
            base_indent = len(line) - len(line.lstrip(" "))
            break
    if start is None:
        return []
    body: list[tuple[int, str]] = []
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            body.append((index + 1, line))
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= base_indent:
            break
        body.append((index + 1, line))
    return body


def _latest_update_errors(text: str, now: datetime) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for line_no, line in _latest_update_lines(text):
        for match in _DATE_RANGE.finditer(line):
            start_raw = match.group("start")
            end_raw = match.group("end")
            try:
                start_day = datetime.strptime(start_raw, "%Y-%m-%d").date()
                end_day = datetime.strptime(end_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append(
                    ValidationError(
                        line_no,
                        "QUARTER_DATE_INVALID",
                        f"Latest Update 기간이 올바른 날짜가 아닙니다: {start_raw} ~ {end_raw}",
                        "error",
                    )
                )
                continue
            update_at = governing_update(start_day, end_day)
            if now < update_at:
                errors.append(
                    ValidationError(
                        line_no,
                        "QUARTER_HIGHLIGHT_TOO_EARLY",
                        "Latest Update가 갱신일 전 분기를 가리킵니다. "
                        f"{start_raw} ~ {end_raw} 의 갱신일은 {_stamp(update_at)} KST입니다.",
                        "error",
                    )
                )
    return errors


# 2026년 1분기부터. 그 전 분기 문서는 안건 분석 출처를 검사하지 않는다.
AGENDA_DECISION_SOURCE_FROM = (2026, 1)
_AGENDA_INFO = re.compile(r'^(\s*)!!! info "안건 분석"\s*$')
_DECISION_SOURCE = re.compile(
    r"^- \(출처\) \[[^\]\n]+\]"
    r"\(https://www\.fsc\.go\.kr/comm/getFile\?srvcId=BBSTY1&upperNo=\d+&fileTy=ATTACH&fileNo=\d+\)"
    r"(.*)$"
)


def agenda_decision_source_required(path: Path) -> bool:
    bounds = filename_bounds(path.name)
    if bounds is None or bounds[1].value is None:
        return False
    end = bounds[1].value
    quarter = (end.month - 1) // 3 + 1
    return (end.year, quarter) >= AGENDA_DECISION_SOURCE_FROM


def _admonition_body(lines: list[str], start: int) -> list[str]:
    header = lines[start]
    base = len(header) - len(header.lstrip(" "))
    body: list[str] = []
    index = start + 1
    while index < len(lines):
        nxt = lines[index]
        if nxt.strip() == "":
            body.append(nxt)
            index += 1
            continue
        indent = len(nxt) - len(nxt.lstrip(" "))
        if indent <= base:
            break
        body.append(nxt)
        index += 1
    return body


def validate_agenda_decision_sources(lines: list[str], path: Path) -> list[ValidationError]:
    """2026 Q1 이후 안건 분석의 첫 불릿은 의결서 첨부 출처다."""
    if not agenda_decision_source_required(path):
        return []
    errors: list[ValidationError] = []
    for index, line in enumerate(lines):
        if _AGENDA_INFO.match(line) is None:
            continue
        bullets = [item.strip() for item in _admonition_body(lines, index) if item.strip().startswith("- ")]
        if bullets and _DECISION_SOURCE.match(bullets[0]):
            continue
        if bullets and bullets[0].startswith("- (출처)"):
            code = "AGENDA_SOURCE_FORMAT"
            message = "안건 분석 출처 링크 형식이 위원 논의 출처와 같은 의결서 첨부 주소가 아닙니다."
        elif any(_DECISION_SOURCE.match(item) for item in bullets):
            code = "AGENDA_SOURCE_FORMAT"
            message = "안건 분석 의결서 출처 링크는 첫 불릿이어야 합니다."
        else:
            code = "AGENDA_SOURCE_MISSING"
            message = "안건 분석에 의결서 출처 링크가 없습니다."
        errors.append(ValidationError(index + 1, code, message, "error"))
    return errors


def validate_file(filepath: Path, strict: bool) -> list[ValidationError]:
    """단일 파일 검증."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return [ValidationError(0, "READ", str(e), "error")]
    if filepath.parent.name == "fss-review" and filepath.name == "index.md":
        return validate_fss_review_cards(materialize_review_markdown(text))
    lines = text.split("\n")
    all_errors: list[ValidationError] = []
    for fn in [
        validate_admonitions,
        validate_yaml_frontmatter,
        validate_date_format,
        validate_table_schema,
        validate_source_layout,
        validate_no_phase2,
        validate_no_collapsible_note,
        validate_agenda_decision_sources,
    ]:
        all_errors.extend(fn(lines, filepath))
    sanctions_root = Path(__file__).resolve().parent.parent / "downloads" / "sanctions"
    all_errors.extend(validate_unpublished_sanctions(lines, filepath, sanctions_root))
    if strict:
        all_errors = [e for e in all_errors if e.severity in ("error", "warning")]
    else:
        all_errors = [e._replace(severity="warning") if e.severity == "warning" else e for e in all_errors]
    return all_errors


def main(argv: list[str] | None = None, now: datetime | None = None, repo_root: Path | None = None) -> int:
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
    args = parser.parse_args(argv)

    repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parent.parent
    now = as_seoul(now)
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
        fss_page = repo_root / "docs" / "fss-review" / "index.md"
        if fss_page.is_file():
            paths.append(fss_page)

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

    for path, err in quarter_timing_errors(repo_root, now):
        rel = path.relative_to(repo_root) if path.is_relative_to(repo_root) else path
        print(f"{rel}:{err.line_no}: [ERROR] {err.code}: {err.message}")
        total_errors += 1

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
