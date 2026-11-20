# -*- coding: utf-8 -*-
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawl import compute_output_path, current_quarter, parse_args, quarter_dates, resolve_period

SEOUL = ZoneInfo("Asia/Seoul")
NOV_20 = datetime(2026, 11, 20, 12, 0, tzinfo=SEOUL)


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


def test_resolve_period_defaults_to_last_ready_quarter():
    """No args must not select the in-progress quarter. Its update instant is always later."""
    start, end = resolve_period(parse_args([]), now=NOV_20)
    assert (start, end) == quarter_dates(2026, 3)
    assert (start, end) != quarter_dates(*current_quarter(NOV_20.date()))


def test_resolve_period_default_flips_at_update_instant():
    before = datetime(2027, 1, 5, 8, 59, tzinfo=SEOUL)
    at = datetime(2027, 1, 5, 9, 0, tzinfo=SEOUL)
    assert resolve_period(parse_args([]), now=before) == quarter_dates(2026, 3)
    assert resolve_period(parse_args([]), now=at) == quarter_dates(2026, 4)


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

    ready = datetime(2099, 4, 5, 9, 0, tzinfo=SEOUL)
    assert main(["--year", "2099", "--quarter", "1"], now=ready) == 0
    assert out.read_text(encoding="utf-8") == "existing"


def test_guard_refuses_before_update_instant():
    from crawl import QuarterNotReady, guard_period

    with pytest.raises(QuarterNotReady, match=r"2027-01-05 09:00"):
        guard_period("2026-10-01", "2026-12-31", NOV_20, allow_open_quarter=False)


def test_guard_allows_at_update_instant():
    from crawl import guard_period

    guard_period(
        "2026-10-01",
        "2026-12-31",
        datetime(2027, 1, 5, 9, 0, tzinfo=SEOUL),
        allow_open_quarter=False,
    )


def _block_crawl(monkeypatch, tmp_path):
    monkeypatch.setattr("crawl.repo_root", lambda: tmp_path)

    def boom(*_args, **_kwargs):
        raise AssertionError("crawl should not run")

    monkeypatch.setattr("crawler.unified.configure_period", lambda _s, _e: None)
    monkeypatch.setattr("crawler.unified.run_collection", boom)
    monkeypatch.setattr("crawler.unified.write_markdown", boom)


def test_main_refuses_early_quarter(tmp_path, monkeypatch, capsys):
    _block_crawl(monkeypatch, tmp_path)
    from crawl import main

    code = main(["--year", "2026", "--quarter", "4"], now=NOV_20)
    assert code == 2
    err = capsys.readouterr().err
    assert "2027-01-05 09:00" in err
    assert "--allow-open-quarter" in err


def test_october_partial_range_uses_q4_update(tmp_path, monkeypatch, capsys):
    _block_crawl(monkeypatch, tmp_path)
    from crawl import main

    code = main(["--start", "2026-10-01", "--end", "2026-10-31"], now=NOV_20)
    assert code == 2
    err = capsys.readouterr().err
    assert "2027-01-05 09:00" in err
    assert "--allow-open-quarter" in err


def test_partial_range_inside_a_ready_quarter_is_allowed():
    from crawl import guard_period

    guard_period("2026-01-15", "2026-03-20", NOV_20, allow_open_quarter=False)


def test_span_into_an_unready_quarter_is_refused():
    from crawl import QuarterNotReady, guard_period

    with pytest.raises(QuarterNotReady, match="2027-01-05 09:00"):
        guard_period("2026-09-15", "2026-10-31", NOV_20, allow_open_quarter=False)


def test_main_rejects_naive_now():
    from crawl import main

    with pytest.raises(TypeError, match="timezone-aware"):
        main(["--year", "2026", "--quarter", "3"], now=datetime(2026, 11, 20, 12, 0))


def test_start_end_before_update_is_refused(tmp_path, monkeypatch, capsys):
    _block_crawl(monkeypatch, tmp_path)
    from crawl import main

    code = main(["--start", "2026-10-01", "--end", "2026-12-31"], now=NOV_20)
    assert code == 2
    assert "--allow-open-quarter" in capsys.readouterr().err


def test_existing_file_does_not_skip_the_guard(tmp_path, monkeypatch, capsys):
    out = tmp_path / "docs/quality-updates/2026/2026-10-01_to_2026-12-31.md"
    out.parent.mkdir(parents=True)
    out.write_text("existing", encoding="utf-8")
    monkeypatch.setattr("crawl.repo_root", lambda: tmp_path)

    from crawl import main

    code = main(["--year", "2026", "--quarter", "4"], now=NOV_20)
    assert code == 2
    captured = capsys.readouterr()
    assert "skipping" not in captured.out
    assert "--allow-open-quarter" in captured.err
    assert out.read_text(encoding="utf-8") == "existing"


def test_allow_open_quarter_can_see_existing_file(tmp_path, monkeypatch, capsys):
    out = tmp_path / "docs/quality-updates/2026/2026-10-01_to_2026-12-31.md"
    out.parent.mkdir(parents=True)
    out.write_text("existing", encoding="utf-8")
    monkeypatch.setattr("crawl.repo_root", lambda: tmp_path)

    from crawl import main

    code = main(
        ["--year", "2026", "--quarter", "4", "--allow-open-quarter"],
        now=NOV_20,
    )
    assert code == 0
    assert "skipping" in capsys.readouterr().out
    assert out.read_text(encoding="utf-8") == "existing"


def test_explicit_ready_quarter_is_not_refused(tmp_path, monkeypatch):
    out = tmp_path / "docs/quality-updates/2026/2026-07-01_to_2026-09-30.md"
    out.parent.mkdir(parents=True)
    out.write_text("existing", encoding="utf-8")
    monkeypatch.setattr("crawl.repo_root", lambda: tmp_path)

    from crawl import main

    assert main(["--year", "2026", "--quarter", "3"], now=NOV_20) == 0


def test_force_does_not_bypass_guard(tmp_path, monkeypatch):
    out = tmp_path / "docs/quality-updates/2026/2026-10-01_to_2026-12-31.md"
    out.parent.mkdir(parents=True)
    out.write_text("existing", encoding="utf-8")
    monkeypatch.setattr("crawl.repo_root", lambda: tmp_path)

    def boom(*_args, **_kwargs):
        raise AssertionError("crawl should not run")

    monkeypatch.setattr("crawler.unified.configure_period", lambda _s, _e: None)
    monkeypatch.setattr("crawler.unified.run_collection", boom)
    monkeypatch.setattr("crawler.unified.write_markdown", boom)

    from crawl import main

    assert main(["--year", "2026", "--quarter", "4", "--force"], now=NOV_20) == 2
    assert out.read_text(encoding="utf-8") == "existing"
