# -*- coding: utf-8 -*-
"""CLI entry point: python scripts/crawl.py [--year Y --quarter Q] [--start ... --end ...]"""

from __future__ import annotations

import argparse
import calendar
import os
import sys
from datetime import date, datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def repo_root() -> Path:
    return _SCRIPTS_DIR.parent


def quarter_dates(year: int, quarter: int) -> tuple[str, str]:
    if quarter < 1 or quarter > 4:
        raise ValueError(f"quarter must be 1-4, got {quarter}")
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    last_day = calendar.monthrange(year, end_month)[1]
    return (
        f"{year:04d}-{start_month:02d}-01",
        f"{year:04d}-{end_month:02d}-{last_day:02d}",
    )


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


def resolve_period(args: argparse.Namespace) -> tuple[str, str]:
    if args.start and args.end:
        start = datetime.strptime(args.start, "%Y-%m-%d")
        end = datetime.strptime(args.end, "%Y-%m-%d")
        if start > end:
            raise ValueError("start date must be on or before end date")
        return args.start, args.end

    year = args.year
    quarter = args.quarter
    if year is None and quarter is None:
        year, quarter = current_quarter()
    elif year is not None and quarter is None:
        raise ValueError("--quarter is required when --year is set")
    elif year is None and quarter is not None:
        year = date.today().year

    return quarter_dates(year, quarter)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl regulatory updates into docs/quality-updates/")
    parser.add_argument("--year", type=int, help="Calendar year for --quarter")
    parser.add_argument("--quarter", type=int, choices=[1, 2, 3, 4], help="Quarter 1-4")
    parser.add_argument("--start", help="Period start YYYY-MM-DD (overrides --quarter)")
    parser.add_argument("--end", help="Period end YYYY-MM-DD (overrides --quarter)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output file")
    parser.add_argument("--dry-run", action="store_true", help="Collect only; do not write file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        start_str, end_str = resolve_period(args)
    except ValueError as exc:
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
