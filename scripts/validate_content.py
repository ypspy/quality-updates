#!/usr/bin/env python3
"""
Quality-updates 마크다운 문서 콘텐츠 검증 스크립트.
admonition 들여쓰기, YAML front matter, 날짜 형식, 테이블 스키마 등을 검사합니다.
"""

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import NamedTuple

import yaml

from fss_review_cards import audit_review_html, materialize_review_markdown
from quarter_timing import (
    APPROVED_NON_QUARTER_PAGES,
    as_seoul,
    filename_bounds,
    front_matter_bounds,
    governing_update,
    iso_dates_in,
    is_standard_quarter_rel,
    iter_doc_targets,
    load_allow_list,
    normalize_scan_text,
    quarter_bounds,
    quarter_update_at,
    unescape_prose_line,
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


_ADMONITION_OPEN = re.compile(r"^[!?]{3}\+?\s*(.*)$")
_QUOTED_TITLE = re.compile(r"""["'“”‘’](.*?)["'“”‘’]""")
_EMPH_MARK = re.compile(r"\*\*|__|\*|_")
_EMPH = r"(?:\*\*|__|\*|_)?"
_ISO_FLEX = r"(?<!\d)(?:\d{4}|\d{2})(?!\d)\s*[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{1,2}\.?"
_KR_DATE = r"\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일"
_KR_MONTH_DAY = r"\d{1,2}\s*월\s*\d{1,2}\s*일"
_DATE_TOKEN = rf"(?:{_ISO_FLEX}|{_KR_DATE})"
_DATE_OPEN = r"['’‘(]?"
_WEEKDAY_PAREN = r"\([월화수목금토일]\)"
_DATE_CLOSE = rf"(?:{_WEEKDAY_PAREN}|\))?"
_RANGE_SEP = r"(?:~|～|〜|∼|·|부터|에서|(?<![A-Za-z])to(?![A-Za-z])|-)"
_CLOCK = r"(?:오전|오후)?\s*\d{1,2}\s*(?:시(?:\s*\d{1,2}\s*분?)?|:\d{2})"
_GAP = rf"(?:\s*{_WEEKDAY_PAREN})?(?:\s*{_CLOCK})?"
_DOT_MD = r"(?<!\d)\d{1,2}\s*[.\-/]\s*\d{1,2}\.?"
_DATE_RANGE = re.compile(
    rf"{_EMPH}\s*{_DATE_OPEN}\s*(?P<start>{_DATE_TOKEN})\s*{_DATE_CLOSE}{_GAP}\s*{_EMPH}"
    rf"\s*{_RANGE_SEP}\s*"
    rf"{_EMPH}\s*{_DATE_OPEN}\s*(?P<end>{_DATE_TOKEN}|{_KR_MONTH_DAY}|{_DOT_MD})\s*{_DATE_CLOSE}{_GAP}\s*{_EMPH}",
    re.IGNORECASE,
)
_YEARLESS_KR_RANGE = re.compile(
    rf"(?P<sm>\d{{1,2}})\s*월\s*(?P<sd>\d{{1,2}})\s*일\s*{_RANGE_SEP}\s*"
    rf"(?P<em>\d{{1,2}})\s*월\s*(?P<ed>\d{{1,2}})\s*일"
)
_QUARTER_NAME = re.compile(
    r"(?<!\d)(?P<year>\d{4})\s*년(?:도)?\s*제?\s*(?P<quarter>[1-4])(?:\s*/\s*4)?\s*분기"
)
_RELATIVE_QUARTER = re.compile(r"(?<!\d)제?\s*[1-4](?:\s*/\s*4)?\s*분기")
_YEAR_SECTION = re.compile(r"(\d{4})\s*년")
_EXPLICIT_DATE = re.compile(_DATE_TOKEN)
_LONE_DATE = re.compile(_DATE_TOKEN)
_NAV_KEY = re.compile(r"^[A-Za-z0-9_]+:")
_NAV_ITEM = re.compile(r"^\s*-\s+(.*)$")
_MD_DEST = re.compile(r"\[[^\]]*\]\(([^)]*)\)")
_HREF_DEST = re.compile(r"""href\s*=\s*(['"])(.*?)\1""", re.IGNORECASE)
_HIGHLIGHT_SOURCES = {"docs/index.md", "docs/quality-updates/index.md"}


def _link_destination_spans(text: str) -> list[tuple[int, int]]:
    """Spans of markdown and href targets. A filename there is a link, not prose."""
    spans = [match.span(1) for match in _MD_DEST.finditer(text)]
    spans.extend(match.span(2) for match in _HREF_DEST.finditer(text))
    return spans


def _inside_span(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(opening <= start and end <= closing for opening, closing in spans)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d %H:%M")


def _too_early_file_message(days: list, stamp: str) -> str:
    shown = ", ".join(day.isoformat() for day in sorted(set(days)))
    return (
        f"분기 갱신일 전 파일입니다. 기간 {shown}의 갱신일은 {stamp} KST이며, "
        "그 전에는 파일을 두거나 내용을 넣지 않습니다."
    )


def _nonstandard_message(rel: str) -> str:
    approved = ", ".join(sorted(APPROVED_NON_QUARTER_PAGES))
    return (
        f"분기 문서 경로가 표준이 아닙니다: {rel}. "
        "표준은 docs/quality-updates/YYYY/YYYY-MM-DD_to_YYYY-MM-DD.md 이고, "
        f"분기가 아닌 페이지는 {approved} 뿐입니다."
    )


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
            rel = path.relative_to(root).as_posix()
            if rel in APPROVED_NON_QUARTER_PAGES:
                continue
            text = _read_text(path)
            if text is None:
                errors.append((path, ValidationError(0, "READ", f"파일을 읽지 못했습니다: {path.name}", "error")))
                continue
            if not is_standard_quarter_rel(rel):
                errors.append(
                    (path, ValidationError(1, "QUARTER_NONSTANDARD_PATH", _nonstandard_message(rel), "error"))
                )
                errors.extend((path, err) for err in _loose_timing_errors(path.name, text, now))
                continue
            errors.extend((path, err) for err in _file_timing_errors(rel, path, text, now, allow))
            errors.extend(
                (path, err)
                for err in _outside_highlight_errors(
                    text,
                    now,
                    file_year=_filename_year(path.name),
                    skip_latest=False,
                    exact_quarter_only=True,
                )
            )

    for rel in _LINK_SOURCES:
        source = root / rel
        text = _read_text(source)
        if text is None:
            continue
        errors.extend((source, err) for err in _link_timing_errors(root, rel.as_posix(), text, now, allow))
        if rel.as_posix() in _HIGHLIGHT_SOURCES:
            errors.extend((source, err) for err in _latest_update_errors(text, now))
            errors.extend((source, err) for err in _outside_highlight_errors(text, now))
        elif rel.as_posix() == "mkdocs.yml":
            errors.extend((source, err) for err in _nav_title_errors(text, now))
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


def _order_error(label: str, start, end) -> ValidationError | None:
    if start.value and end.value and start.value > end.value:
        return ValidationError(
            end.line or start.line,
            "QUARTER_DATE_ORDER",
            f"{label} 시작일 {start.value.isoformat()}이 종료일 {end.value.isoformat()}보다 늦습니다.",
            "error",
        )
    return None


def _period_pair_errors(filename_start, filename_end, period_start, period_end) -> list[ValidationError]:
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
    for label, start, end in (
        ("파일명", filename_start, filename_end),
        ("period", period_start, period_end),
    ):
        order = _order_error(label, start, end)
        if order is not None:
            errors.append(order)
    return errors


def _governed_days(*tokens) -> list:
    return [token.value for token in tokens if token.value is not None]


def _file_timing_errors(rel: str, path: Path, text: str, now: datetime, allow: set[str]) -> list[ValidationError]:
    bounds = filename_bounds(path.name)
    if bounds is None or not is_standard_quarter_rel(rel):
        return []
    filename_start, filename_end = bounds
    period_start, period_end = front_matter_bounds(text)
    errors = _period_pair_errors(filename_start, filename_end, period_start, period_end)
    days = _governed_days(filename_start, filename_end, period_start, period_end)
    if days and rel not in allow and now < governing_update(*days):
        stamp = _stamp(governing_update(*days))
        errors.append(ValidationError(1, "QUARTER_TOO_EARLY", _too_early_file_message(days, stamp), "error"))
    return errors


def _loose_timing_errors(name: str, text: str, now: datetime) -> list[ValidationError]:
    """Judge a non-standard file by front matter and any dates in its name."""
    period_start, period_end = front_matter_bounds(text)
    named = iso_dates_in(name)
    errors: list[ValidationError] = []
    for label, token in (("period.start", period_start), ("period.end", period_end)):
        invalid = _invalid_date_error(label, token)
        if invalid is not None:
            errors.append(invalid)
    for token in named:
        invalid = _invalid_date_error("파일명의 날짜", token)
        if invalid is not None:
            errors.append(invalid)
    order = _order_error("period", period_start, period_end)
    if order is not None:
        errors.append(order)
    if len(named) > 1:
        named_order = _order_error("파일명", named[0], named[1])
        if named_order is not None:
            errors.append(named_order)
    days = _governed_days(period_start, period_end, *named)
    if days and now < governing_update(*days):
        stamp = _stamp(governing_update(*days))
        errors.append(ValidationError(1, "QUARTER_TOO_EARLY", _too_early_file_message(days, stamp), "error"))
    return errors


def _link_timing_errors(
    root: Path,
    source_rel: str,
    text: str,
    now: datetime,
    allow: set[str],
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for rel in iter_doc_targets(source_rel, line):
            if rel in APPROVED_NON_QUARTER_PAGES:
                continue
            if not is_standard_quarter_rel(rel):
                errors.append(
                    ValidationError(line_no, "QUARTER_NONSTANDARD_PATH", _nonstandard_message(rel), "error")
                )
                target = root / rel
                target_text = _read_text(target) if target.is_file() else ""
                for err in _loose_timing_errors(rel, target_text or "", now):
                    if err.code == "QUARTER_TOO_EARLY":
                        errors.append(
                            ValidationError(
                                line_no,
                                "QUARTER_LINK_TOO_EARLY",
                                f"분기 갱신일 전 링크입니다. {rel} 의 {err.message}",
                                "error",
                            )
                        )
                    else:
                        errors.append(err._replace(line_no=line_no))
                continue
            errors.extend(_standard_link_errors(root, rel, line_no, now, allow))
    return errors


def _standard_link_errors(
    root: Path,
    rel: str,
    line_no: int,
    now: datetime,
    allow: set[str],
) -> list[ValidationError]:
    bounds = filename_bounds(Path(rel).name)
    if bounds is None:
        return [ValidationError(line_no, "QUARTER_NONSTANDARD_PATH", _nonstandard_message(rel), "error")]
    filename_start, filename_end = bounds
    period_start, period_end = front_matter_bounds("")
    target = root / rel
    if target.is_file():
        target_text = _read_text(target)
        if target_text is not None:
            period_start, period_end = front_matter_bounds(target_text)
    errors: list[ValidationError] = []
    for label, token in (
        ("링크 파일명의 시작일", filename_start),
        ("링크 파일명의 종료일", filename_end),
        ("period.start", period_start),
        ("period.end", period_end),
    ):
        invalid = _invalid_date_error(label, token)
        if invalid is not None:
            errors.append(invalid._replace(line_no=line_no))
    for label, start, end in (
        ("파일명", filename_start, filename_end),
        ("period", period_start, period_end),
    ):
        order = _order_error(label, start, end)
        if order is not None:
            errors.append(order._replace(line_no=line_no))
    if rel in allow:
        return errors
    days = _governed_days(filename_start, filename_end, period_start, period_end)
    if days and now < governing_update(*days):
        stamp = _stamp(governing_update(*days))
        errors.append(
            ValidationError(
                line_no,
                "QUARTER_LINK_TOO_EARLY",
                f"분기 갱신일 전 링크입니다. {rel} 의 갱신일은 {stamp} KST입니다.",
                "error",
            )
        )
    return errors


def _indent_columns(line: str) -> int:
    """Leading indent after tab stops of width 4, matching Python-Markdown."""
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip(" "))


def _latest_title(rest: str) -> str:
    """Title text with emphasis removed. Quoted titles win over the type token."""
    quoted = _QUOTED_TITLE.search(rest)
    if quoted:
        title = quoted.group(1)
    else:
        parts = rest.split(None, 1)
        title = parts[1] if len(parts) > 1 else ""
        while title:
            word, _, tail = title.partition(" ")
            if word.casefold() in {"inline", "end"}:
                title = tail
                continue
            break
    return re.sub(r"\s+", " ", _EMPH_MARK.sub("", title)).strip()


def _is_latest_heading(line: str) -> bool:
    """True when an admonition title is Latest Update, ignoring case and emphasis.

    Accepts ``!!!``, ``???``, and ``???+`` with the type glued or spaced, plus
    extra words such as ``inline`` and ``end``.
    """
    match = _ADMONITION_OPEN.match(line.strip())
    if not match or not match.group(1).strip():
        return False
    title = _latest_title(match.group(1).strip()).casefold()
    return title == "latest update" or title.startswith("latest update ")


def _latest_update_blocks(text: str) -> list[list[tuple[int, str]]]:
    """Every Latest Update admonition, heading plus body, with 1-based line numbers.

    A later block is not dropped because an earlier one was found.
    """
    lines = text.splitlines()
    blocks: list[list[tuple[int, str]]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not _is_latest_heading(line):
            index += 1
            continue
        base_indent = _indent_columns(line)
        block = [(index + 1, line)]
        index += 1
        while index < len(lines):
            nxt = lines[index]
            if not nxt.strip():
                block.append((index + 1, nxt))
                index += 1
                continue
            if _indent_columns(nxt) <= base_indent:
                break
            block.append((index + 1, nxt))
            index += 1
        blocks.append(block)
    return blocks


def _filename_year(name: str) -> int | None:
    bounds = filename_bounds(name)
    if bounds and bounds[0].value:
        return bounds[0].value.year
    return None


def _highlight_date(raw: str) -> date:
    if "년" in raw:
        match = re.fullmatch(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", raw.strip())
        if not match:
            raise ValueError(raw)
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    normalized = raw.strip().rstrip(".")
    normalized = re.sub(r"\s+", "", normalized).replace(".", "-").replace("/", "-")
    parts = normalized.split("-")
    if len(parts) != 3:
        raise ValueError(raw)
    year = int(parts[0])
    if len(parts[0]) == 2:
        year += 2000
    elif len(parts[0]) != 4:
        raise ValueError(raw)
    return date(year, int(parts[1]), int(parts[2]))


def _month_day(raw: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", raw.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _dotted_month_day(raw: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"(\d{1,2})\s*[.\-/]\s*(\d{1,2})\.?", raw.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _range_days(start_raw: str, end_raw: str) -> tuple[date, date]:
    start_day = _highlight_date(start_raw)
    month_day = _month_day(end_raw) or _dotted_month_day(end_raw)
    if month_day is not None:
        return start_day, date(start_day.year, month_day[0], month_day[1])
    return start_day, _highlight_date(end_raw)


def _paragraph_span(text: str, offset: int) -> tuple[int, int]:
    """Blank-line paragraph that contains ``offset``. Distant dates stay outside."""
    start = text.rfind("\n\n", 0, offset)
    start = 0 if start < 0 else start + 2
    end = text.find("\n\n", offset)
    end = len(text) if end < 0 else end
    return start, end


def _explicit_years_between(text: str, start: int, end: int) -> list[int]:
    years: list[int] = []
    for match in _EXPLICIT_DATE.finditer(text, start, end):
        try:
            year = _highlight_date(match.group(0)).year
        except ValueError:
            continue
        if year not in years:
            years.append(year)
    return years


def _candidate_years(text: str, span: tuple[int, int], now: datetime, file_year: int | None) -> list[int]:
    """Same paragraph years, plus the file year and ``now`` when those exist.

    A year from another paragraph does not count. ``now.year`` stays even when
    a nearby past year is present, so that year cannot hide an unpublished
    full quarter.
    """
    paragraph = _paragraph_span(text, span[0])
    years = _explicit_years_between(text, paragraph[0], paragraph[1])
    if file_year is not None and file_year not in years:
        years.append(file_year)
    if now.year not in years:
        years.append(now.year)
    return years


def _exact_quarter(start: date, end: date) -> tuple[int, int] | None:
    if start.year != end.year or start > end:
        return None
    quarter = (start.month - 1) // 3 + 1
    quarter_start, quarter_end = quarter_bounds(start.year, quarter)
    if start == quarter_start and end == quarter_end:
        return start.year, quarter
    return None


def _overlaps(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(start < closing and end > opening for opening, closing in spans)


def _prepare_scan_line(line: str) -> str:
    return normalize_scan_text(unescape_prose_line(line).replace("\r", ""), strip_emphasis=True)


def _prepare_scan_text(text: str) -> str:
    """Per-line scan fold. Newlines stay, so reported line numbers are the source lines."""
    return "\n".join(_prepare_scan_line(line) for line in text.split("\n"))


def _dated_range_errors(
    start_raw: str,
    end_raw: str,
    line_no: int,
    now: datetime,
    *,
    latest: bool,
    exact_quarter_only: bool = False,
) -> list[ValidationError]:
    try:
        start_day, end_day = _range_days(start_raw, end_raw)
    except ValueError:
        if exact_quarter_only:
            return []
        if latest:
            message = f"Latest Update 기간이 올바른 날짜가 아닙니다: {start_raw} ~ {end_raw}"
        else:
            message = f"하이라이트 기간이 올바른 날짜가 아닙니다: {start_raw} ~ {end_raw}"
        return [ValidationError(line_no, "QUARTER_DATE_INVALID", message, "error")]
    if exact_quarter_only and _exact_quarter(start_day, end_day) is None:
        return []
    errors: list[ValidationError] = []
    if start_day > end_day:
        if latest:
            message = (
                "Latest Update 시작일 "
                f"{start_day.isoformat()}이 종료일 {end_day.isoformat()}보다 늦습니다."
            )
        else:
            message = (
                "하이라이트 시작일 "
                f"{start_day.isoformat()}이 종료일 {end_day.isoformat()}보다 늦습니다."
            )
        errors.append(ValidationError(line_no, "QUARTER_DATE_ORDER", message, "error"))
    update_at = governing_update(start_day, end_day)
    if now < update_at:
        if latest:
            message = (
                "Latest Update가 갱신일 전 분기를 가리킵니다. "
                f"{start_raw} ~ {end_raw} 의 갱신일은 {_stamp(update_at)} KST입니다."
            )
        else:
            message = (
                "하이라이트가 갱신일 전 분기를 가리킵니다. "
                f"{start_raw} ~ {end_raw} 의 갱신일은 {_stamp(update_at)} KST입니다."
            )
        errors.append(ValidationError(line_no, "QUARTER_HIGHLIGHT_TOO_EARLY", message, "error"))
    return errors


def _yearless_range_errors(
    match: re.Match[str],
    line_no: int,
    text: str,
    now: datetime,
    file_year: int | None,
    *,
    latest: bool,
) -> list[ValidationError]:
    """Reject only when a candidate year makes the span one whole unpublished quarter.

    Candidates are explicit years in the same paragraph, the file's year, and
    the year of ``now``. One published year does not cancel another candidate.
    """
    shown = match.group(0)
    month = int(match.group("sm"))
    day = int(match.group("sd"))
    end_month = int(match.group("em"))
    end_day_num = int(match.group("ed"))
    for year in _candidate_years(text, match.span(), now, file_year):
        try:
            start_day = date(year, month, day)
            end_day = date(year, end_month, end_day_num)
        except ValueError:
            continue
        if _exact_quarter(start_day, end_day) is None:
            continue
        update_at = governing_update(start_day, end_day)
        if now >= update_at:
            continue
        if latest:
            message = (
                "Latest Update가 갱신일 전 분기를 가리킵니다. "
                f"{shown} 의 갱신일은 {_stamp(update_at)} KST입니다."
            )
        else:
            message = (
                "하이라이트가 갱신일 전 분기를 가리킵니다. "
                f"{shown} 의 갱신일은 {_stamp(update_at)} KST입니다."
            )
        return [ValidationError(line_no, "QUARTER_HIGHLIGHT_TOO_EARLY", message, "error")]
    return []


def _quarter_name_errors(match: re.Match[str], line_no: int, now: datetime, *, latest: bool) -> list[ValidationError]:
    year = int(match.group("year"))
    quarter = int(match.group("quarter"))
    start_day, end_day = quarter_bounds(year, quarter)
    update_at = governing_update(start_day, end_day)
    if now >= update_at:
        return []
    shown = f"{year}년 {quarter}분기"
    if latest:
        message = f"Latest Update가 갱신일 전 분기를 가리킵니다. {shown}의 갱신일은 {_stamp(update_at)} KST입니다."
    else:
        message = f"하이라이트가 갱신일 전 분기를 가리킵니다. {shown}의 갱신일은 {_stamp(update_at)} KST입니다."
    return [ValidationError(line_no, "QUARTER_HIGHLIGHT_TOO_EARLY", message, "error")]


def _extra_highlight_errors(
    text: str,
    now: datetime,
    *,
    file_year: int | None,
    latest: bool,
    consumed: list[tuple[int, int]],
    line_of,
    skip,
    include_names: bool,
    include_yearless: bool,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if include_yearless:
        for match in _YEARLESS_KR_RANGE.finditer(text):
            if _overlaps(consumed, match.start(), match.end()) or skip(match.start(), match.end()):
                continue
            errors.extend(
                _yearless_range_errors(match, line_of(match.start()), text, now, file_year, latest=latest)
            )
    if include_names:
        for match in _QUARTER_NAME.finditer(text):
            if skip(match.start(), match.end()):
                continue
            errors.extend(_quarter_name_errors(match, line_of(match.start()), now, latest=latest))
    return errors


def _line_for_offset(block: list[tuple[int, str]], offset: int) -> int:
    cursor = 0
    line_no = block[0][0]
    for number, line in block:
        if cursor <= offset:
            line_no = number
        cursor += len(line) + 1
    return line_no


def _latest_update_errors(text: str, now: datetime) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for block in _latest_update_blocks(text):
        unescaped = [(number, _prepare_scan_line(line)) for number, line in block]
        joined = "\n".join(line for _number, line in unescaped)
        destinations = _link_destination_spans(joined)
        consumed: list[tuple[int, int]] = []

        def line_of(offset: int, lines: list[tuple[int, str]] = unescaped) -> int:
            return _line_for_offset(lines, offset)

        def skip(start: int, end: int) -> bool:
            return _inside_span(destinations, start, end)

        for match in _DATE_RANGE.finditer(joined):
            consumed.append(match.span())
            if skip(match.start(), match.end()):
                continue
            errors.extend(
                _dated_range_errors(
                    match.group("start"),
                    match.group("end"),
                    line_of(match.start()),
                    now,
                    latest=True,
                )
            )
        errors.extend(
            _extra_highlight_errors(
                joined,
                now,
                file_year=None,
                latest=True,
                consumed=consumed,
                line_of=line_of,
                skip=skip,
                include_names=True,
                include_yearless=True,
            )
        )
        for match in _LONE_DATE.finditer(joined):
            if any(start <= match.start() and match.end() <= end for start, end in consumed):
                continue
            if skip(match.start(), match.end()):
                continue
            raw_date = match.group(0)
            line_no = line_of(match.start())
            try:
                day = _highlight_date(raw_date)
            except ValueError:
                errors.append(
                    ValidationError(
                        line_no,
                        "QUARTER_DATE_INVALID",
                        f"Latest Update에 날짜가 있으나 기간으로 읽지 못했습니다: {raw_date}",
                        "error",
                    )
                )
                continue
            # A press title such as ``2026. 9. 19.`` in an already-ready quarter is not a range.
            if now < quarter_update_at(day):
                errors.append(
                    ValidationError(
                        line_no,
                        "QUARTER_DATE_INVALID",
                        f"Latest Update에 날짜가 있으나 기간으로 읽지 못했습니다: {raw_date}",
                        "error",
                    )
                )
    return errors


def _outside_highlight_errors(
    text: str,
    now: datetime,
    file_year: int | None = None,
    *,
    skip_latest: bool = True,
    exact_quarter_only: bool = False,
) -> list[ValidationError]:
    """Quarter ranges outside Latest Update.

    The text is scan-folded per line before matching, so line numbers stay on
    the source. ``exact_quarter_only`` is the quarter-file body scan: a dated
    range counts only when it is the whole span of a quarter that is not yet
    releasable. Deadlines and partial windows in that body stay quiet.
    """
    unescaped = _prepare_scan_text(text)
    covered: set[int] = set()
    if skip_latest:
        covered = {number for block in _latest_update_blocks(text) for number, _line in block}
    destinations = _link_destination_spans(unescaped)
    errors: list[ValidationError] = []
    consumed: list[tuple[int, int]] = []

    def line_of(offset: int) -> int:
        return unescaped.count("\n", 0, offset) + 1

    def skip(start: int, end: int) -> bool:
        return line_of(start) in covered or _inside_span(destinations, start, end)

    for match in _DATE_RANGE.finditer(unescaped):
        consumed.append(match.span())
        if skip(match.start(), match.end()):
            continue
        errors.extend(
            _dated_range_errors(
                match.group("start"),
                match.group("end"),
                line_of(match.start()),
                now,
                latest=False,
                exact_quarter_only=exact_quarter_only,
            )
        )
    errors.extend(
        _extra_highlight_errors(
            unescaped,
            now,
            file_year=file_year,
            latest=False,
            consumed=consumed,
            line_of=line_of,
            skip=skip,
            include_names=True,
            include_yearless=True,
        )
    )
    return errors


_NAV_FOLD = frozenset({">", "|", ">-", "|-", ">+", "|+"})


def _strip_nav_quotes(key: str) -> str:
    key = key.strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {"'", '"'}:
        return key[1:-1].strip()
    return key


def _nav_key_from_body(body: str) -> str | None:
    """Visible nav key, including a section whose value is a nested list.

    ``20:00`` has no space after the colon, so only ``": "`` splits a path.
    A trailing colon with no path is a section title. Quotes around the key
    are removed.
    """
    if body in _NAV_FOLD:
        return None
    if ": " in body:
        key = body.rsplit(": ", 1)[0]
    elif body.endswith(":"):
        key = body[:-1]
    else:
        return None
    key = _strip_nav_quotes(key.strip())
    return key or None


def _nav_key_on_line(line: str) -> tuple[int, str] | None:
    item = _NAV_ITEM.match(line)
    if item:
        indent = len(line) - len(line.lstrip(" "))
        key = _nav_key_from_body(item.group(1).strip())
    else:
        folded = re.match(r"^(\s+)(?!-\s)(.*)$", line)
        if not folded:
            return None
        indent = len(folded.group(1))
        key = _nav_key_from_body(folded.group(2).strip())
    if key is None:
        return None
    return indent, key


def _year_section_number(key: str) -> int | None:
    folded = normalize_scan_text(key).strip()
    match = _YEAR_SECTION.fullmatch(folded)
    if not match:
        return None
    return int(match.group(1))


def _title_with_inherited_year(key: str, inherited_year: int | None) -> str | None:
    """Section titles to judge. A bare year section such as ``2026년`` is not one.

    A relative title (``4분기 (10–12월)``) takes the nearest parent year section.
    """
    if _year_section_number(key) is not None:
        return None
    folded = normalize_scan_text(key).strip()
    if inherited_year is None or re.search(r"(?<!\d)\d{4}(?!\d)", folded):
        return key
    if _RELATIVE_QUARTER.search(folded):
        return f"{inherited_year}년 {key}"
    return key


def _walk_nav_yaml(node: object, inherited_year: int | None):
    if isinstance(node, list):
        for item in node:
            yield from _walk_nav_yaml(item, inherited_year)
        return
    if not isinstance(node, dict):
        return
    for raw_key, value in node.items():
        key = str(raw_key).strip()
        year_here = _year_section_number(key)
        child_year = year_here if year_here is not None else inherited_year
        yield key, inherited_year
        if isinstance(value, list):
            yield from _walk_nav_yaml(value, child_year)


def _nav_block_end(lines: list[str], start: int) -> int:
    for index in range(start, len(lines)):
        line = lines[index]
        if line and not line[0].isspace() and not line.startswith(("#", "-")) and _NAV_KEY.match(line):
            return index
    return len(lines)


def _map_keys_to_nav_lines(lines: list[str], start: int, keys: list[str]) -> list[int] | None:
    found: list[int] = []
    cursor = start
    end = _nav_block_end(lines, start)
    for key in keys:
        matched = None
        for index in range(cursor, end):
            parsed = _nav_key_on_line(lines[index])
            if parsed and parsed[1] == key:
                matched = index
                break
        if matched is None:
            return None
        found.append(matched)
        cursor = matched + 1
    return found


def _nav_titles_from_yaml(lines: list[str], nav: object) -> list[tuple[int, str]] | None:
    walked = list(_walk_nav_yaml(nav, None))
    if not walked:
        return None
    start = None
    for index, line in enumerate(lines):
        if re.fullmatch(r"nav:\s*(#.*)?", line):
            start = index + 1
            break
    if start is None:
        return None
    mapped = _map_keys_to_nav_lines(lines, start, [key for key, _year in walked])
    if mapped is None:
        return None
    titles: list[tuple[int, str]] = []
    for line_index, (key, inherited) in zip(mapped, walked):
        title = _title_with_inherited_year(key, inherited)
        if title:
            titles.append((line_index + 1, title))
    return titles


def _nav_titles_from_indent(lines: list[str]) -> list[tuple[int, str]]:
    """Indent stack used when the YAML nav tree cannot be lined up with the file."""
    in_nav = False
    stack: list[tuple[int, int | None]] = []
    titles: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if not in_nav:
            if re.fullmatch(r"nav:\s*(#.*)?", line):
                in_nav = True
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if _NAV_KEY.match(line):
            break
        parsed = _nav_key_on_line(line)
        if parsed is None:
            continue
        indent, key = parsed
        while stack and stack[-1][0] >= indent:
            stack.pop()
        inherited = next((year for _indent, year in reversed(stack) if year is not None), None)
        year_here = _year_section_number(key)
        stack.append((indent, year_here if year_here is not None else inherited))
        title = _title_with_inherited_year(key, inherited)
        if title:
            titles.append((index + 1, title))
    return titles


def _iter_nav_titles(text: str):
    """Yield ``(line_no, title)`` for visible mkdocs nav keys, including section titles.

    A year section (``2026년``) is kept only as context for a child such as
    ``4분기 (10–12월)``. The path after a colon is not a title. YAML order is
    preferred; a bad parse falls back to indentation.
    """
    lines = text.splitlines()
    titles: list[tuple[int, str]] | None = None
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError:
        loaded = None
    nav = loaded.get("nav") if isinstance(loaded, dict) else None
    if nav is not None:
        titles = _nav_titles_from_yaml(lines, nav)
    if titles is None:
        titles = _nav_titles_from_indent(lines)
    yield from titles


def _nav_title_errors(text: str, now: datetime) -> list[ValidationError]:
    """Highlight rules applied to the visible nav title, not the target path."""
    errors: list[ValidationError] = []
    for line_no, title in _iter_nav_titles(text):
        for err in _outside_highlight_errors(title, now, skip_latest=False):
            errors.append(err._replace(line_no=line_no))
    return errors


# 2026년 1분기부터. 그 전 분기 문서는 안건 분석 출처를 검사하지 않는다.
AGENDA_DECISION_SOURCE_FROM = (2026, 1)
_AGENDA_INFO = re.compile(r'^(\s*)!!! info "안건 분석"\s*$')
_DECISION_SOURCE = re.compile(
    r"^- \(출처\) \[(?P<label>[^\]\n]+)\]"
    r"\((?P<url>https://www\.fsc\.go\.kr/comm/getFile\?srvcId=BBSTY1&upperNo=\d+&fileTy=ATTACH&fileNo=\d+)\)"
    r"(?P<trail>.*)$"
)
# 금융위 임시회차처럼 첨부명이 「(공개용) 의결 NNN. …」인 경우.
_PUBLIC_DECISION_LABEL = re.compile(r"^\(공개용\)\s*의결\s+\d+\.")
_AGENDA_NUMBER = re.compile(r"(?:의결|보고)\s*제\d+호")


def _decision_source_label_ok(label: str) -> bool:
    """의결서 묶음 이름 또는 공개용 의결 파일명. 의사록 이름만으로는 통과하지 않는다."""
    if "의사록" in label:
        return False
    if "안건" in label and "의결서" in label:
        return True
    return _PUBLIC_DECISION_LABEL.match(label) is not None


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
        matched = _DECISION_SOURCE.match(bullets[0]) if bullets else None
        if (
            matched
            and _decision_source_label_ok(matched.group("label"))
            and _AGENDA_NUMBER.search(matched.group("trail"))
        ):
            continue
        if bullets and bullets[0].startswith("- (출처)"):
            code = "AGENDA_SOURCE_FORMAT"
            message = (
                "안건 분석 출처는 의결서 첨부 이름과 의결 제N호(보고 안건은 보고 제N호)가 있어야 합니다. "
                "의사록 첨부 이름만으로는 통과하지 않습니다."
            )
        elif any(_DECISION_SOURCE.match(item) for item in bullets):
            code = "AGENDA_SOURCE_FORMAT"
            message = "안건 분석 의결서 출처 링크는 첫 불릿이어야 합니다."
        else:
            code = "AGENDA_SOURCE_MISSING"
            message = "안건 분석에 의결서 출처 링크가 없습니다."
        errors.append(ValidationError(index + 1, code, message, "error"))
    return errors


_MINUTES_NOTE = re.compile(r'^(\s*)!!! note "위원 논의"\s*$')
_MINUTES_SOURCE = re.compile(
    r"^- \(출처\) \[(?P<label>[^\]\n]+)\]"
    r"\((?P<url>https://www\.fsc\.go\.kr/comm/getFile\?srvcId=BBSTY1&upperNo=(?P<upper>\d+)&fileTy=ATTACH&fileNo=\d+)\)"
    r"(?P<trail>.*)"
    r" \u00b7 \[게시물\]\((?P<post>https://www\.fsc\.go\.kr/no02010[12]/(?P<post_id>\d+))\)\s*$"
)


def validate_minutes_sources(lines: list[str], path: Path) -> list[ValidationError]:
    """2026 Q1 이후 위원 논의의 의사록 출처는 getFile 주 링크다.

    미공개 줄은 통과한다. 확장자는 보지 않는다. 안건 분석 의결서 검사는 별도다.
    """
    if not agenda_decision_source_required(path):
        return []
    errors: list[ValidationError] = []
    for index, line in enumerate(lines):
        if _MINUTES_NOTE.match(line) is None:
            continue
        body = _admonition_body(lines, index)
        for offset, item in enumerate(body):
            stripped = item.strip()
            if not stripped.startswith("- (출처)"):
                continue
            if "미공개" in stripped and "](" not in stripped:
                continue
            matched = _MINUTES_SOURCE.match(stripped)
            if matched and "의사록" in matched.group("label") and matched.group("upper") == matched.group("post_id"):
                continue
            errors.append(
                ValidationError(
                    index + 2 + offset,
                    "MINUTES_SOURCE_FORMAT",
                    "위원 논의 의사록 출처의 주 링크는 getFile 주소이고 표시 이름에 의사록이 있어야 합니다.",
                    "error",
                )
            )
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
        validate_minutes_sources,
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
