# -*- coding: utf-8 -*-
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawl import compute_output_path, current_quarter, parse_args, quarter_dates, resolve_period


def test_quarter_dates_q1():
    start, end = quarter_dates(2026, 1)
    assert start == "2026-01-01"
    assert end == "2026-03-31"


def test_quarter_dates_q4():
    start, end = quarter_dates(2026, 4)
    assert start == "2026-10-01"
    assert end == "2026-12-31"


def test_output_path_uses_start_year():
    p = compute_output_path("2022-12-15", "2023-04-03")
    assert "docs/quality-updates/2022" in str(p).replace("\\", "/")
    assert p.name == "2022-12-15_to_2023-04-03.md"


def test_current_quarter():
    assert current_quarter(date(2026, 2, 15)) == (2026, 1)


def test_resolve_period_defaults_to_current_quarter():
    year, quarter = current_quarter()
    start, end = resolve_period(parse_args([]))
    assert (start, end) == quarter_dates(year, quarter)


def test_resolve_period_explicit_quarter():
    start, end = resolve_period(parse_args(["--year", "2026", "--quarter", "2"]))
    assert start == "2026-04-01"
    assert end == "2026-06-30"


def test_resolve_period_start_end():
    start, end = resolve_period(
        parse_args(["--start", "2026-01-15", "--end", "2026-03-31"])
    )
    assert start == "2026-01-15"
    assert end == "2026-03-31"


def test_year_without_quarter_raises():
    with pytest.raises(ValueError, match="--quarter"):
        resolve_period(parse_args(["--year", "2026"]))


def test_skip_if_exists(tmp_path, monkeypatch):
    start, end = "2099-01-01", "2099-03-31"
    out = tmp_path / "docs/quality-updates/2099/2099-01-01_to_2099-03-31.md"
    out.parent.mkdir(parents=True)
    out.write_text("existing", encoding="utf-8")

    monkeypatch.setattr("crawl.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "crawler.unified.configure_period",
        lambda s, e: None,
    )
    monkeypatch.setattr("crawler.unified.run_collection", lambda: "md")
    monkeypatch.setattr("crawler.unified.write_markdown", lambda p: p)

    from crawl import main

    assert main(["--year", "2099", "--quarter", "1"]) == 0
    assert out.read_text(encoding="utf-8") == "existing"
