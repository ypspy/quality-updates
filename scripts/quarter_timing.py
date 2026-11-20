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
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SEOUL = ZoneInfo("Asia/Seoul")

_FILENAME = re.compile(r"^(?P<start>\d{4}-\d{2}-\d{2})_to_(?P<end>\d{4}-\d{2}-\d{2})\.md$")
_QUARTER_REF = re.compile(
    r"(?:docs/)?(?:quality-updates/)?"
    r"(?P<year>\d{4})/(?P<name>\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}\.md)"
)
_EXACT_ALLOW = re.compile(
    r"docs/quality-updates/\d{4}/\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}\.md"
)


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


def front_matter_bounds(text: str) -> tuple[DateToken, DateToken]:
    """``period.start`` and ``period.end`` from YAML front matter. Invalid dates do not raise."""
    start = DateToken.absent()
    end = DateToken.absent()
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return start, end
    in_period = False
    for index, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            break
        if re.match(r"^period:\s*$", line):
            in_period = True
            continue
        if not in_period:
            continue
        if line[:1] not in {" ", "\t"}:
            in_period = False
            continue
        start_match = re.match(r"^\s+start:\s*(\d{4}-\d{2}-\d{2})\s*$", line)
        end_match = re.match(r"^\s+end:\s*(\d{4}-\d{2}-\d{2})\s*$", line)
        if start_match:
            start = _date_token(start_match.group(1), index)
        elif end_match:
            end = _date_token(end_match.group(1), index)
    return start, end


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
