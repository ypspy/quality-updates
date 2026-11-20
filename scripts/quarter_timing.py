# -*- coding: utf-8 -*-
"""Quarter update instant: 09:00 Asia/Seoul on the 5th of the month after period end.

1/5, 4/5, 7/5, and 10/5. A quarter may be created or linked only at or after that instant.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SEOUL = ZoneInfo("Asia/Seoul")

_FILENAME = re.compile(r"^(?P<start>\d{4}-\d{2}-\d{2})_to_(?P<end>\d{4}-\d{2}-\d{2})\.md$")
_QUARTER_REF = re.compile(
    r"(?:docs/)?(?:quality-updates/)?"
    r"(?P<year>\d{4})/(?P<name>\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}\.md)"
)


class QuarterNotReady(Exception):
    """The period's update instant has not arrived."""


def as_seoul(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(SEOUL)
    if now.tzinfo is None:
        return now.replace(tzinfo=SEOUL)
    return now.astimezone(SEOUL)


def quarter_update_at(period_end: date) -> datetime:
    """5th day, 09:00 Asia/Seoul, of the calendar month after period_end."""
    if period_end.month == 12:
        year, month = period_end.year + 1, 1
    else:
        year, month = period_end.year, period_end.month + 1
    return datetime(year, month, 5, 9, 0, tzinfo=SEOUL)


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


def find_period_end(text: str) -> tuple[date | None, int]:
    """Front matter period.end, if present, and its 1-based line number."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, 1
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
        match = re.match(r"^\s+end:\s*(\d{4}-\d{2}-\d{2})\s*$", line)
        if match:
            return date.fromisoformat(match.group(1)), index
    return None, 1


def period_end_from_text(text: str) -> date | None:
    end, _line = find_period_end(text)
    return end


def period_end_from_filename(name: str) -> date | None:
    match = _FILENAME.match(name)
    if not match:
        return None
    return date.fromisoformat(match.group("end"))


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
    """Repo-relative quarter paths. Blank lines and # comments are ignored."""
    if not path.is_file():
        return set()
    allowed: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _QUARTER_REF.search(stripped.replace("\\", "/"))
        if match:
            allowed.add(canonical_quarter_key(match.group("year"), match.group("name")))
    return allowed
