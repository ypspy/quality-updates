# -*- coding: utf-8 -*-
"""CLI entry point: python scripts/crawl.py [--year Y --quarter Q] [--start ... --end ...]

With no period flags, the target is the latest calendar quarter whose update
instant has passed (09:00 Asia/Seoul on the 5th of the month after that quarter
ends). An explicit period whose start or end is not yet due is refused with
exit 2. ``--allow-open-quarter`` does not override that refusal unless the
exact output path is listed in ``data/qu-early-allow.txt``.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from quarter_timing import (  # noqa: E402
    QuarterNotReady,
    as_seoul,
    is_standard_quarter_rel,
    last_ready_quarter,
    load_allow_list,
    quarter_bounds,
    quarter_update_at,
)


def repo_root() -> Path:
    return _SCRIPTS_DIR.parent


def quarter_dates(year: int, quarter: int) -> tuple[str, str]:
    start, end = quarter_bounds(year, quarter)
    return start.isoformat(), end.isoformat()


def current_quarter(today: date | None = None) -> tuple[int, int]:
    today = today or date.today()
    quarter = (today.month - 1) // 3 + 1
    return today.year, quarter


def compute_output_path(start_str: str, end_str: str) -> Path:
    start_year = datetime.strptime(start_str, "%Y-%m-%d").year
    return (
        repo_root()
        / "docs"
        / "quality-updates"
        / str(start_year)
        / f"{start_str}_to_{end_str}.md"
    )


def resolve_period(args: argparse.Namespace, now: datetime | None = None) -> tuple[str, str]:
    now = as_seoul(now)
    if args.start and args.end:
        start = datetime.strptime(args.start, "%Y-%m-%d")
        end = datetime.strptime(args.end, "%Y-%m-%d")
        if start > end:
            raise ValueError("start date must be on or before end date")
        return args.start, args.end

    year = args.year
    quarter = args.quarter
    if year is None and quarter is None:
        year, quarter = last_ready_quarter(now)
    elif year is not None and quarter is None:
        raise ValueError("--quarter is required when --year is set")
    elif year is None and quarter is not None:
        year = now.year

    return quarter_dates(year, quarter)


def guard_period(start: str, end: str, now: datetime, allow_open_quarter: bool) -> None:
    """Refuse a period whose calendar quarter is not yet due.

    Start and end are each mapped to the calendar quarter that contains them.
    The update instant is 09:00 KST on the 5th of the month after that quarter
    ends. The later of the two instants must already have passed.
    """
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    update_at = max(quarter_update_at(start_date), quarter_update_at(end_date))
    if as_seoul(now) < update_at and not allow_open_quarter:
        stamp = update_at.strftime("%Y-%m-%d %H:%M")
        raise QuarterNotReady(
            f"{start} ~ {end} 갱신일({stamp} KST) 전에는 수집하지 않습니다. "
            "예외는 윤석님 본인의 명시 승인만 인정합니다."
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl regulatory updates into docs/quality-updates/")
    parser.add_argument("--year", type=int, help="Calendar year for --quarter")
    parser.add_argument("--quarter", type=int, choices=[1, 2, 3, 4], help="Quarter 1-4")
    parser.add_argument("--start", help="Period start YYYY-MM-DD (overrides --quarter)")
    parser.add_argument("--end", help="Period end YYYY-MM-DD (overrides --quarter)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output file")
    parser.add_argument("--dry-run", action="store_true", help="Collect only; do not write file")
    parser.add_argument(
        "--allow-open-quarter",
        action="store_true",
        help=(
            "출력 경로가 data/qu-early-allow.txt에 정확히 있을 때만 갱신일 전 수집을 진행한다. "
            "그 목록은 윤석님 본인의 명시 승인으로만 채운다."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    now = as_seoul(now)
    try:
        args = parse_args(argv)
        start_str, end_str = resolve_period(args, now=now)
        output_key = compute_output_path(start_str, end_str).relative_to(repo_root()).as_posix()
        allowed = load_allow_list(repo_root() / "data" / "qu-early-allow.txt")
        permitted = bool(args.allow_open_quarter) and output_key in allowed and is_standard_quarter_rel(output_key)
        guard_period(start_str, end_str, now, allow_open_quarter=permitted)
    except (ValueError, QuarterNotReady) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    out_path = compute_output_path(start_str, end_str)
    if out_path.exists() and not args.force:
        print(f"[WARN] Output exists, skipping: {out_path}")
        return 0

    from crawler import unified

    unified.configure_period(start_str, end_str)
    print("[INFO] Unified crawler started")
    print(f"[INFO] Jurisdiction: {unified.JURISDICTION}")
    print(f"[INFO] Period: {start_str} ~ {end_str}")

    if args.dry_run:
        unified.run_collection()
        print(f"[DRY-RUN] Would write → {out_path}")
        return 0

    try:
        written = unified.write_markdown(out_path)
    except Exception as exc:
        print(f"[ERROR] Crawl failed: {exc}", file=sys.stderr)
        return 1

    print(f"[DONE] Markdown generated → {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
