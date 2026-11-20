# -*- coding: utf-8 -*-
"""Quarter update instant: 09:00 Asia/Seoul on the 5th after the calendar quarter.

A date belongs to the calendar quarter that contains it (Q1 Jan–Mar, Q2 Apr–Jun,
Q3 Jul–Sep, Q4 Oct–Dec). The update instant is 09:00 Asia/Seoul on the 5th of the
month after that quarter ends: 4/5, 7/5, 10/5, or 1/5. A quarter may be created
or linked only at or after that instant.

``now`` must be timezone-aware. ``None`` means the current Asia/Seoul time.
A naive datetime is rejected and is not read as KST.
"""

from __future__ import annotations

import calendar
import html
import re
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

SEOUL = ZoneInfo("Asia/Seoul")

# Pages under docs/quality-updates/ that are not a quarter document.
APPROVED_NON_QUARTER_PAGES = frozenset({
    "docs/quality-updates/index.md",
})

_FILENAME = re.compile(r"^(?P<start>\d{4}-\d{2}-\d{2})_to_(?P<end>\d{4}-\d{2}-\d{2})\.md$")
_QUARTER_REF = re.compile(
    r"(?:docs/)?(?:quality-updates/)?"
    r"(?P<year>\d{4})/(?P<name>\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}\.md)"
)
_EXACT_ALLOW = re.compile(
    r"docs/quality-updates/\d{4}/\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}\.md"
)
_EXACT_NAV = re.compile(
    r"^(?:docs/)?quality-updates/(?P<year>\d{4})/(?P<name>\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}\.md)$"
)
_EXACT_INDEX = re.compile(r"^(?:docs/)?quality-updates/index\.md$")
_EXACT_REL = re.compile(
    r"^(?P<year>\d{4})/(?P<name>\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}\.md)$"
)
_PAREN_TARGET = re.compile(r"\(([^()\s]+)\)")
_YAML_VALUE = re.compile(r":\s*[\"']?(\S+)")
_BARE_QUARTER = re.compile(r"(?:docs/)?quality-updates/\S+")
_HREF = re.compile(r"""href\s*=\s*(['"])(.*?)\1""", re.IGNORECASE)
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class _NoTimestampLoader(yaml.SafeLoader):
    """SafeLoader that leaves YYYY-MM-DD as text.

    PyYAML otherwise builds a date and raises ValueError on 2026-02-31, which
    would hide the invalid token and stop the rest of the file.
    """


_NoTimestampLoader.yaml_implicit_resolvers = {
    ch: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for ch, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


class QuarterNotReady(Exception):
    """The period's update instant has not arrived."""


def as_seoul(now: datetime | None) -> datetime:
    """Return ``now`` as Asia/Seoul.

    ``None`` is the current Asia/Seoul time. A naive datetime raises TypeError.
    It is not treated as KST, because a wall time without a zone is ambiguous.
    Aware values are converted with ``astimezone``.
    """
    if now is None:
        return datetime.now(SEOUL)
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise TypeError("now must be timezone-aware; naive datetimes are not treated as KST")
    return now.astimezone(SEOUL)


def quarter_update_at(day: date) -> datetime:
    """09:00 Asia/Seoul on the 5th of the month after the calendar quarter containing ``day``."""
    year, quarter = day.year, (day.month - 1) // 3 + 1
    _start, quarter_end = quarter_bounds(year, quarter)
    if quarter_end.month == 12:
        update_year, update_month = quarter_end.year + 1, 1
    else:
        update_year, update_month = quarter_end.year, quarter_end.month + 1
    return datetime(update_year, update_month, 5, 9, 0, tzinfo=SEOUL)


def governing_update(*days: date) -> datetime:
    """Latest update instant among the calendar quarters that contain ``days``."""
    if not days:
        raise ValueError("governing_update requires at least one date")
    return max(quarter_update_at(day) for day in days)


def quarter_bounds(year: int, quarter: int) -> tuple[date, date]:
    if quarter < 1 or quarter > 4:
        raise ValueError(f"quarter must be 1-4, got {quarter}")
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    last_day = calendar.monthrange(year, end_month)[1]
    return date(year, start_month, 1), date(year, end_month, last_day)


def _previous_quarter(year: int, quarter: int) -> tuple[int, int]:
    if quarter == 1:
        return year - 1, 4
    return year, quarter - 1


def last_ready_quarter(now: datetime | None = None) -> tuple[int, int]:
    """Latest calendar quarter whose update instant is at or before now."""
    current = as_seoul(now)
    year = current.year
    quarter = (current.month - 1) // 3 + 1
    for _ in range(80):
        _start, end = quarter_bounds(year, quarter)
        if current >= quarter_update_at(end):
            return year, quarter
        year, quarter = _previous_quarter(year, quarter)
    raise ValueError("갱신일이 지난 분기가 없습니다")


def is_before_update(period_end: date, now: datetime | None = None) -> bool:
    return as_seoul(now) < quarter_update_at(period_end)


@dataclass(frozen=True)
class DateToken:
    """A parsed YYYY-MM-DD token. ``invalid`` means the token is not a real calendar date."""

    value: date | None
    line: int
    invalid: bool
    raw: str

    @staticmethod
    def absent() -> DateToken:
        return DateToken(None, 1, False, "")


def _date_token(raw: str, line: int) -> DateToken:
    try:
        return DateToken(date.fromisoformat(raw), line, False, raw)
    except ValueError:
        return DateToken(None, line, True, raw)


def filename_bounds(name: str) -> tuple[DateToken, DateToken] | None:
    """Start and end tokens from ``YYYY-MM-DD_to_YYYY-MM-DD.md``, or None if the name is not one."""
    match = _FILENAME.match(name)
    if not match:
        return None
    return _date_token(match.group("start"), 1), _date_token(match.group("end"), 1)


def _front_matter_lines(text: str) -> list[str] | None:
    lines = text.splitlines()
    while lines and lines[0].lstrip("\ufeff").strip() == "":
        del lines[0]
    if not lines:
        return None
    lines[0] = lines[0].lstrip("\ufeff")
    if lines[0].strip() != "---":
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[1:index]
    return None


def _key_line(body_lines: list[str], key: str) -> int:
    pattern = re.compile(rf"(^|[{{,])\s*{re.escape(key)}\s*:")
    for offset, line in enumerate(body_lines):
        if pattern.search(line):
            return offset + 2
    return 2


def _coerce_period_value(value: object, line: int) -> DateToken:
    if value is None:
        return DateToken.absent()
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return DateToken(value, line, False, value.isoformat())
    raw = str(value).strip().strip("\"'")
    if not raw:
        return DateToken.absent()
    return _date_token(raw, line)


def front_matter_bounds(text: str) -> tuple[DateToken, DateToken]:
    """``period.start`` and ``period.end`` from YAML front matter.

    Quoted block form and the one-line flow form are both read. Invalid dates
    do not raise. A front matter block that is not YAML becomes an invalid token
    so the period is not treated as empty. Leading blank lines and a UTF-8 BOM
    are skipped before the opening ``---``.

    Only an exact ``period`` mapping with both ``start`` and ``end`` is a
    period. A different spelling (``Period``, ``period_start``), a ``period.``
    / ``period_`` / ``period-`` key other than ``period_label``, or a mapping
    that is missing either date or carries another key is an invalid token.
    ``period: null`` stays absent.
    """
    body_lines = _front_matter_lines(text)
    if body_lines is None:
        return DateToken.absent(), DateToken.absent()
    raw = "\n".join(body_lines)
    if not raw.strip():
        return DateToken.absent(), DateToken.absent()
    try:
        meta = yaml.load(raw, Loader=_NoTimestampLoader) or {}
    except yaml.YAMLError:
        return DateToken(None, 2, True, "period"), DateToken.absent()
    if not isinstance(meta, dict):
        return DateToken(None, 2, True, "period"), DateToken.absent()
    misspelled = [key for key in meta if _is_misspelled_period_key(key)]
    if misspelled:
        shown = str(misspelled[0])
        return DateToken(None, _key_line(body_lines, shown), True, shown), DateToken.absent()
    period = meta.get("period")
    if period is None:
        return DateToken.absent(), DateToken.absent()
    if not isinstance(period, dict):
        line = _key_line(body_lines, "period")
        return DateToken(None, line, True, str(period)), DateToken.absent()
    if set(period) != {"start", "end"}:
        line = _key_line(body_lines, "period")
        return DateToken(None, line, True, "period"), DateToken.absent()
    start = _coerce_period_value(period.get("start"), _key_line(body_lines, "start"))
    end = _coerce_period_value(period.get("end"), _key_line(body_lines, "end"))
    if not start.invalid and not end.invalid and (start.value is None or end.value is None):
        line = _key_line(body_lines, "period")
        return DateToken(None, line, True, "period"), DateToken.absent()
    return start, end


def _is_misspelled_period_key(key: object) -> bool:
    """True for a period-shaped key that is not the exact ``period`` field.

    ``period_label`` is the separate display label on every quarter file.
    """
    if not isinstance(key, str) or key == "period":
        return False
    folded = key.casefold()
    if folded == "period_label":
        return False
    if folded == "period":
        return True
    return folded.startswith(("period.", "period_", "period-"))


def is_standard_quarter_rel(rel: str) -> bool:
    """True only for ``docs/quality-updates/YYYY/YYYY-MM-DD_to_YYYY-MM-DD.md``."""
    return _EXACT_ALLOW.fullmatch(rel.replace("\\", "/")) is not None


def nonstandard_quarter_paths(repo_root: Path) -> list[str]:
    """Markdown under ``docs/quality-updates/`` that is neither standard nor approved."""
    docs = Path(repo_root) / "docs" / "quality-updates"
    if not docs.is_dir():
        return []
    found: list[str] = []
    root = Path(repo_root)
    for path in sorted(docs.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if rel in APPROVED_NON_QUARTER_PAGES or is_standard_quarter_rel(rel):
            continue
        found.append(rel)
    return found


def iso_dates_in(text: str) -> list[DateToken]:
    return [_date_token(match.group(0), 1) for match in _ISO_DATE.finditer(text)]


_DECODE_LIMIT = 8
_UNSTABLE_LINK = "docs/quality-updates/undecoded-link.md"


def _normalize_link_line(line: str) -> tuple[str, bool]:
    """HTML-unescape and URL-decode until the line stops changing.

    The second value is False when ``_DECODE_LIMIT`` rounds were not enough.
    ``#`` fragments are split only after this returns.
    """
    current = line
    for _ in range(_DECODE_LIMIT):
        nxt = urllib.parse.unquote(html.unescape(current))
        if nxt == current:
            return current, True
        current = nxt
    nxt = urllib.parse.unquote(html.unescape(current))
    return current, nxt == current


def _clean_target(raw: str) -> str:
    token = raw.strip().strip("\"'")
    token = re.split(r"[<>'\"\s]", token, maxsplit=1)[0]
    token = token.replace("\\", "/")
    token = token.split("#", 1)[0].split("?", 1)[0]
    return token.rstrip(".,;:\"')")


def quarter_release_blockers(
    repo_root: Path,
    now: datetime | None = None,
    allow: set[str] | None = None,
) -> list[str]:
    """Standard quarter files that are early or whose start date is after the end.

    Judged from the filename and from ``period`` front matter. ``now`` defaults
    to the current Asia/Seoul time. An exact path in ``data/qu-early-allow.txt``
    skips the early refusal. A start date after the end date is still refused,
    and a dash or path variant is never an exemption. A string ``period`` or any
    other unreadable period token is refused as well. The allow list does not
    hide that token.
    """
    current = as_seoul(now)
    docs = Path(repo_root) / "docs" / "quality-updates"
    if not docs.is_dir():
        return []
    root = Path(repo_root)
    if allow is None:
        allow = load_allow_list(root / "data" / "qu-early-allow.txt")
    problems: list[str] = []
    for path in sorted(docs.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if not is_standard_quarter_rel(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            problems.append(f"{rel}: unreadable")
            continue
        bounds = filename_bounds(path.name)
        period_start, period_end = front_matter_bounds(text)
        if bounds is not None:
            filename_start, filename_end = bounds
            if filename_start.value and filename_end.value and filename_start.value > filename_end.value:
                problems.append(f"{rel}: 시작일이 종료일보다 늦습니다")
        if period_start.value and period_end.value and period_start.value > period_end.value:
            problems.append(f"{rel}: period 시작일이 종료일보다 늦습니다")
        for token in (period_start, period_end):
            if token.invalid:
                problems.append(f"{rel}: period 값이 올바른 날짜가 아닙니다: {token.raw}")
        days = [
            token.value
            for token in (*(bounds or ()), period_start, period_end)
            if token.value is not None
        ]
        if days and rel not in allow and current < governing_update(*days):
            problems.append(f"{rel}: 갱신일 전")
    return problems


def iter_doc_targets(source_rel: str, line: str) -> list[str]:
    """Repo-relative quarter-doc targets on one nav or index line.

    Exact standard paths stay exact. A suffix, extra directory, missing year
    folder, or other variant is returned unchanged in shape so it cannot inherit
    an allow-list entry for the canonical file. HTML ``href`` values are
    included. HTML unescape and URL decoding repeat until the line is stable,
    including ``%252F`` and ``%26%2347%3B``, and only then are ``#`` fragments
    removed. A line that is still changing after the decode cap is returned as
    an undecoded path so the caller can reject it.
    """
    decoded, stable = _normalize_link_line(line)
    if not stable:
        return [_UNSTABLE_LINK]
    raws: list[str] = []
    raws.extend(match.group(1) for match in _PAREN_TARGET.finditer(decoded))
    raws.extend(match.group(1) for match in _YAML_VALUE.finditer(decoded))
    raws.extend(match.group(0) for match in _BARE_QUARTER.finditer(decoded))
    raws.extend(match.group(2) for match in _HREF.finditer(decoded))
    found: list[str] = []
    for raw in raws:
        rel = _resolve_doc_target(source_rel, _clean_target(raw))
        if rel and rel not in found:
            found.append(rel)
    return found


def _resolve_doc_target(source_rel: str, token: str) -> str | None:
    if not token or "://" in token:
        return None
    quarter_index = source_rel == "docs/quality-updates/index.md"
    in_scope = "quality-updates/" in token or token.startswith("quality-updates/")
    if quarter_index and (token.endswith(".md") or ".md" in token) and not token.startswith(("http://", "https://")):
        in_scope = True
    if not in_scope:
        return None
    if _EXACT_INDEX.fullmatch(token) or (quarter_index and token == "index.md"):
        return "docs/quality-updates/index.md"
    nav = _EXACT_NAV.fullmatch(token)
    if nav:
        return f"docs/quality-updates/{nav.group('year')}/{nav.group('name')}"
    if quarter_index:
        rel = _EXACT_REL.fullmatch(token)
        if rel:
            return f"docs/quality-updates/{rel.group('year')}/{rel.group('name')}"
        if not token.startswith(("docs/", "quality-updates/")):
            return "docs/quality-updates/" + token.lstrip("/")
    if token.startswith("docs/"):
        return token
    if token.startswith("quality-updates/"):
        return "docs/" + token
    return "docs/quality-updates/" + token.lstrip("/")


def canonical_quarter_key(year: str, name: str) -> str:
    return f"docs/quality-updates/{year}/{name}"


def quarter_key_for_path(path: Path) -> str | None:
    if not _FILENAME.match(path.name):
        return None
    year = path.parent.name
    if not re.fullmatch(r"\d{4}", year):
        return None
    return canonical_quarter_key(year, path.name)


def iter_quarter_refs(line: str):
    for match in _QUARTER_REF.finditer(line):
        yield match.group("year"), match.group("name")


def load_allow_list(path: Path) -> set[str]:
    """Exact repo-relative POSIX quarter paths.

    Blank lines and comment lines (optional indent, then ``#``) are ignored.
    Only trailing whitespace is removed. The remaining text is allowed only when
    it equals ``docs/quality-updates/YYYY/YYYY-MM-DD_to_YYYY-MM-DD.md``.
    Leading spaces, backslashes, prefixes, suffixes, and inline comments do not match.
    """
    if not path.is_file():
        return set()
    allowed: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip(" \t")
        if not line.strip() or line.lstrip(" \t").startswith("#"):
            continue
        if _EXACT_ALLOW.fullmatch(line):
            allowed.add(line)
    return allowed
