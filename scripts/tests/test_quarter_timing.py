# -*- coding: utf-8 -*-
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quarter_timing import (
    front_matter_bounds,
    is_before_update,
    last_ready_quarter,
    load_allow_list,
    quarter_update_at,
)
from validate_content import main, quarter_timing_errors

SEOUL = ZoneInfo("Asia/Seoul")
NOV_20 = datetime(2026, 11, 20, 12, 0, tzinfo=SEOUL)
Q4_NAME = "2026-10-01_to_2026-12-31.md"
Q4_KEY = f"docs/quality-updates/2026/{Q4_NAME}"
REPO = Path(__file__).resolve().parents[2]


def test_update_instant_is_fifth_of_next_month_at_0900_kst():
    assert quarter_update_at(date(2026, 3, 31)) == datetime(2026, 4, 5, 9, 0, tzinfo=SEOUL)
    assert quarter_update_at(date(2026, 6, 30)) == datetime(2026, 7, 5, 9, 0, tzinfo=SEOUL)
    assert quarter_update_at(date(2026, 9, 30)) == datetime(2026, 10, 5, 9, 0, tzinfo=SEOUL)
    assert quarter_update_at(date(2026, 12, 31)) == datetime(2027, 1, 5, 9, 0, tzinfo=SEOUL)
    # A day inside Q4 uses 1/5, the update of the quarter, not the next month.
    assert quarter_update_at(date(2026, 10, 1)) == datetime(2027, 1, 5, 9, 0, tzinfo=SEOUL)
    assert quarter_update_at(date(2026, 10, 31)) == datetime(2027, 1, 5, 9, 0, tzinfo=SEOUL)


def test_update_instant_boundary_includes_0900_kst():
    end = date(2026, 12, 31)
    assert is_before_update(end, datetime(2027, 1, 5, 8, 59, tzinfo=SEOUL))
    assert not is_before_update(end, datetime(2027, 1, 5, 9, 0, tzinfo=SEOUL))
    # 2027-01-05 00:00 UTC is 09:00 KST.
    assert not is_before_update(end, datetime(2027, 1, 5, 0, 0, tzinfo=timezone.utc))
    assert is_before_update(end, datetime(2027, 1, 4, 23, 59, tzinfo=timezone.utc))


def test_last_ready_quarter_walks_back_to_a_passed_update():
    assert last_ready_quarter(NOV_20) == (2026, 3)
    assert last_ready_quarter(datetime(2027, 1, 5, 8, 59, tzinfo=SEOUL)) == (2026, 3)
    assert last_ready_quarter(datetime(2027, 1, 5, 9, 0, tzinfo=SEOUL)) == (2026, 4)
    assert last_ready_quarter(datetime(2026, 10, 5, 9, 0, tzinfo=SEOUL)) == (2026, 3)
    assert last_ready_quarter(datetime(2026, 10, 5, 8, 59, tzinfo=SEOUL)) == (2026, 2)
    assert last_ready_quarter(datetime(2026, 4, 5, 9, 0, tzinfo=SEOUL)) == (2026, 1)
    assert last_ready_quarter(datetime(2026, 4, 5, 8, 59, tzinfo=SEOUL)) == (2025, 4)


def test_allow_list_requires_an_exact_posix_path(tmp_path):
    path = tmp_path / "qu-early-allow.txt"
    path.write_text(
        "# docs/quality-updates/2026/2026-10-01_to_2026-12-31.md\n"
        "\n"
        "docs/quality-updates/2026/2026-10-01_to_2026-12-31.md.bak\n"
        "drafts/docs/quality-updates/2026/2026-10-01_to_2026-12-31.md\n"
        "docs\\quality-updates\\2026\\2026-10-01_to_2026-12-31.md\n"
        "  docs/quality-updates/2026/2026-01-01_to_2026-03-31.md\n"
        "docs/quality-updates/2026/2026-10-01_to_2026-12-31.md  \n",
        encoding="utf-8",
    )
    assert load_allow_list(path) == {Q4_KEY}


def test_naive_now_is_rejected():
    from quarter_timing import as_seoul

    with pytest.raises(TypeError, match="timezone-aware"):
        as_seoul(datetime(2026, 11, 20, 12, 0))


def test_missing_allow_list_is_empty(tmp_path):
    assert load_allow_list(tmp_path / "missing.txt") == set()


def test_committed_allow_list_is_empty_and_requires_owner_approval():
    path = REPO / "data" / "qu-early-allow.txt"
    text = path.read_text(encoding="utf-8")
    assert "명시 승인" in text
    assert load_allow_list(path) == set()


def _front_matter(start: str, end: str) -> str:
    return f"---\ntitle: t\nperiod:\n  start: {start}\n  end: {end}\n---\n"


def _mini_repo(tmp_path: Path) -> Path:
    (tmp_path / "docs" / "quality-updates" / "2026").mkdir(parents=True)
    (tmp_path / "data").mkdir()
    (tmp_path / "mkdocs.yml").write_text("nav: []\n", encoding="utf-8")
    (tmp_path / "docs" / "index.md").write_text("# home\n", encoding="utf-8")
    (tmp_path / "docs" / "quality-updates" / "index.md").write_text("# idx\n", encoding="utf-8")
    (tmp_path / "data" / "qu-early-allow.txt").write_text(
        "# 윤석님 본인의 명시 승인이 있어야 추가한다.\n",
        encoding="utf-8",
    )
    return tmp_path


def _codes(errors):
    return [err.code for _path, err in errors]


def test_early_quarter_file_is_an_error(tmp_path):
    root = _mini_repo(tmp_path)
    quarter = root / "docs" / "quality-updates" / "2026" / Q4_NAME
    quarter.write_text(_front_matter("2026-10-01", "2026-12-31"), encoding="utf-8")
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_TOO_EARLY"]
    assert errors[0][0] == quarter
    assert "2027-01-05 09:00" in errors[0][1].message


def test_ready_quarter_file_is_quiet(tmp_path):
    root = _mini_repo(tmp_path)
    name = "2026-07-01_to_2026-09-30.md"
    (root / "docs" / "quality-updates" / "2026" / name).write_text(
        _front_matter("2026-07-01", "2026-09-30"),
        encoding="utf-8",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def test_file_is_allowed_at_the_update_instant(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / Q4_NAME).write_text(
        _front_matter("2026-10-01", "2026-12-31"),
        encoding="utf-8",
    )
    now = datetime(2027, 1, 5, 9, 0, tzinfo=SEOUL)
    assert quarter_timing_errors(root, now) == []


def test_q4_filename_with_earlier_period_end_is_blocked(tmp_path):
    """2026-10-01_to_2026-12-31.md with period.end 2026-09-30 is still before 2027-01-05."""
    root = _mini_repo(tmp_path)
    quarter = root / "docs" / "quality-updates" / "2026" / Q4_NAME
    quarter.write_text(_front_matter("2026-10-01", "2026-09-30"), encoding="utf-8")
    errors = quarter_timing_errors(root, NOV_20)
    codes = _codes(errors)
    assert "QUARTER_TOO_EARLY" in codes
    assert "QUARTER_PERIOD_MISMATCH" in codes
    early = next(err for _path, err in errors if err.code == "QUARTER_TOO_EARLY")
    assert "2027-01-05 09:00" in early.message


def test_later_period_end_blocks_an_otherwise_ready_filename(tmp_path):
    root = _mini_repo(tmp_path)
    name = "2026-07-01_to_2026-09-30.md"
    (root / "docs" / "quality-updates" / "2026" / name).write_text(
        _front_matter("2026-07-01", "2026-12-31"),
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    codes = _codes(errors)
    assert "QUARTER_TOO_EARLY" in codes
    assert "QUARTER_PERIOD_MISMATCH" in codes
    early = next(err for _path, err in errors if err.code == "QUARTER_TOO_EARLY")
    assert "2027-01-05 09:00" in early.message


def test_period_mismatch_is_an_error_after_both_updates(tmp_path):
    root = _mini_repo(tmp_path)
    name = "2026-01-01_to_2026-03-31.md"
    (root / "docs" / "quality-updates" / "2026" / name).write_text(
        _front_matter("2026-01-02", "2026-03-31"),
        encoding="utf-8",
    )
    assert _codes(quarter_timing_errors(root, NOV_20)) == ["QUARTER_PERIOD_MISMATCH"]


def test_mid_quarter_end_uses_that_quarters_update(tmp_path):
    root = _mini_repo(tmp_path)
    name = "2026-10-01_to_2026-10-31.md"
    (root / "docs" / "quality-updates" / "2026" / name).write_text(
        _front_matter("2026-10-01", "2026-10-31"),
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_TOO_EARLY"]
    assert "2027-01-05 09:00" in errors[0][1].message


def test_invalid_date_is_reported_and_validation_continues(tmp_path):
    root = _mini_repo(tmp_path)
    folder = root / "docs" / "quality-updates" / "2026"
    (folder / "2026-01-01_to_2026-02-31.md").write_text(
        "---\ntitle: t\nperiod:\n  start: 2026-01-01\n  end: 2026-02-31\n---\n",
        encoding="utf-8",
    )
    (folder / Q4_NAME).write_text(_front_matter("2026-10-01", "2026-12-31"), encoding="utf-8")
    codes = _codes(quarter_timing_errors(root, NOV_20))
    assert "QUARTER_DATE_INVALID" in codes
    assert "QUARTER_TOO_EARLY" in codes


def test_filename_dates_used_when_front_matter_has_no_end(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / Q4_NAME).write_text(
        "### 금융감독원\n",
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_TOO_EARLY"]


def test_early_links_in_nav_and_indexes(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "mkdocs.yml").write_text(
        f"nav:\n  - 4분기: quality-updates/2026/{Q4_NAME}\n",
        encoding="utf-8",
    )
    (root / "docs" / "index.md").write_text(
        f"[바로가기](quality-updates/2026/{Q4_NAME})\n",
        encoding="utf-8",
    )
    (root / "docs" / "quality-updates" / "index.md").write_text(
        f"[2026년](2026/{Q4_NAME})\n",
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == [
        "QUARTER_LINK_TOO_EARLY",
        "QUARTER_LINK_TOO_EARLY",
        "QUARTER_LINK_TOO_EARLY",
    ]
    assert {path.relative_to(root).as_posix() for path, _err in errors} == {
        "mkdocs.yml",
        "docs/index.md",
        "docs/quality-updates/index.md",
    }


def test_allow_list_suppresses_file_and_links(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / Q4_NAME).write_text(
        _front_matter("2026-10-01", "2026-12-31"),
        encoding="utf-8",
    )
    (root / "mkdocs.yml").write_text(
        f"nav:\n  - 4분기: quality-updates/2026/{Q4_NAME}\n",
        encoding="utf-8",
    )
    (root / "docs" / "index.md").write_text(
        f"[바로가기](quality-updates/2026/{Q4_NAME})\n",
        encoding="utf-8",
    )
    (root / "docs" / "quality-updates" / "index.md").write_text(
        f"[2026년](2026/{Q4_NAME})\n",
        encoding="utf-8",
    )
    (root / "data" / "qu-early-allow.txt").write_text(
        "# 윤석님 본인의 명시 승인이 있어야 추가한다.\n" + Q4_KEY + "\n",
        encoding="utf-8",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def test_link_uses_later_of_filename_and_period_end(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / Q4_NAME).write_text(
        _front_matter("2026-10-01", "2026-09-30"),
        encoding="utf-8",
    )
    (root / "docs" / "index.md").write_text(
        f"[바로가기](quality-updates/2026/{Q4_NAME})\n",
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    codes = _codes(errors)
    assert "QUARTER_TOO_EARLY" in codes
    assert "QUARTER_PERIOD_MISMATCH" in codes
    assert "QUARTER_LINK_TOO_EARLY" in codes
    link = next(err for _path, err in errors if err.code == "QUARTER_LINK_TOO_EARLY")
    assert "2027-01-05 09:00" in link.message


def test_allow_list_does_not_hide_a_period_mismatch(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / Q4_NAME).write_text(
        _front_matter("2026-10-01", "2026-09-30"),
        encoding="utf-8",
    )
    (root / "data" / "qu-early-allow.txt").write_text(
        "# 윤석님 본인의 명시 승인이 있어야 추가한다.\n" + Q4_KEY + "\n",
        encoding="utf-8",
    )
    assert _codes(quarter_timing_errors(root, NOV_20)) == [
        "QUARTER_PERIOD_MISMATCH",
        "QUARTER_DATE_ORDER",
    ]


def test_latest_update_prose_names_a_future_quarter(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    **2026-10-01 ~ 2026-12-31 규제 업데이트가 추가되었습니다.**\n"
        "    주요 테마:\n",
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_HIGHLIGHT_TOO_EARLY"]
    assert "2027-01-05 09:00" in errors[0][1].message


def test_ready_latest_update_range_is_quiet(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    **2026-07-01 ~ 2026-09-30 규제 업데이트가 추가되었습니다.**\n",
        encoding="utf-8",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def test_main_reports_early_quarter_and_honors_allow_list(tmp_path, capsys):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / Q4_NAME).write_text(
        _front_matter("2026-10-01", "2026-12-31"),
        encoding="utf-8",
    )
    (root / "docs" / "index.md").write_text(
        f"[바로가기](quality-updates/2026/{Q4_NAME})\n",
        encoding="utf-8",
    )
    assert main([], now=NOV_20, repo_root=root) == 1
    first = capsys.readouterr().out
    assert "QUARTER_TOO_EARLY" in first
    assert "QUARTER_LINK_TOO_EARLY" in first

    (root / "data" / "qu-early-allow.txt").write_text(
        "# 윤석님 본인의 명시 승인이 있어야 추가한다.\n" + Q4_KEY + "\n",
        encoding="utf-8",
    )
    assert main([], now=NOV_20, repo_root=root) == 0


def test_repository_has_no_quarter_before_its_update_date():
    errors = quarter_timing_errors(REPO, datetime.now(SEOUL))
    assert errors == []


def test_docs_state_the_update_instant():
    agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    guide = (REPO / "docs" / "project" / "quarterly-operations-guide.md").read_text(encoding="utf-8")
    for text in (agents, guide):
        assert "09:00 KST" in text
    assert "인자 없는 `crawl.py`는 갱신일이 지난 마지막 분기" in guide
    assert "윤석님 본인의 명시 승인" in guide


def test_approved_non_quarter_pages_are_listed_explicitly():
    from quarter_timing import APPROVED_NON_QUARTER_PAGES

    assert APPROVED_NON_QUARTER_PAGES == frozenset({"docs/quality-updates/index.md"})


def test_front_matter_reads_quoted_and_flow_periods():
    quoted = '---\ntitle: "t"\nperiod:\n  start: "2026-10-01"\n  end: "2026-12-31"\n---\n'
    flow = '---\nperiod: {start: "2026-10-01", end: "2026-12-31"}\n---\n'
    single = "---\nperiod:\n  start: '2026-10-01'\n  end: '2026-12-31'\n---\n"
    for text in (quoted, flow, single):
        start, end = front_matter_bounds(text)
        assert (start.value, end.value) == (date(2026, 10, 1), date(2026, 12, 31))
        assert not start.invalid and not end.invalid


def test_quoted_period_overrides_a_ready_filename(tmp_path):
    """Writer skeleton quotes dates. A ready filename must not hide an early period."""
    root = _mini_repo(tmp_path)
    name = "2026-07-01_to_2026-09-30.md"
    (root / "docs" / "quality-updates" / "2026" / name).write_text(
        '---\nperiod:\n  start: "2026-10-01"\n  end: "2026-12-31"\n---\n',
        encoding="utf-8",
    )
    codes = _codes(quarter_timing_errors(root, NOV_20))
    assert "QUARTER_TOO_EARLY" in codes
    assert "QUARTER_PERIOD_MISMATCH" in codes


def test_flow_period_is_not_treated_as_empty(tmp_path):
    root = _mini_repo(tmp_path)
    name = "2026-07-01_to_2026-09-30.md"
    (root / "docs" / "quality-updates" / "2026" / name).write_text(
        '---\nperiod: {start: "2026-10-01", end: "2026-12-31"}\n---\n',
        encoding="utf-8",
    )
    codes = _codes(quarter_timing_errors(root, NOV_20))
    assert "QUARTER_TOO_EARLY" in codes
    assert "QUARTER_PERIOD_MISMATCH" in codes


def test_nonstandard_markdown_is_an_error_and_still_judged(tmp_path):
    root = _mini_repo(tmp_path)
    year = root / "docs" / "quality-updates" / "2026"
    (year / "2026Q4.md").write_text(
        '---\nperiod:\n  start: "2026-10-01"\n  end: "2026-12-31"\n---\n',
        encoding="utf-8",
    )
    nested = year / "q4"
    nested.mkdir()
    (nested / Q4_NAME).write_text(_front_matter("2026-10-01", "2026-12-31"), encoding="utf-8")
    (root / "docs" / "quality-updates" / Q4_NAME).write_text(
        _front_matter("2026-10-01", "2026-12-31"),
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    nonstandard = [err for _path, err in errors if err.code == "QUARTER_NONSTANDARD_PATH"]
    assert len(nonstandard) == 3
    assert any(err.code == "QUARTER_TOO_EARLY" for _path, err in errors)
    assert main([], now=NOV_20, repo_root=root) == 1


def test_nonstandard_file_without_dates_still_errors(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / "2026Q4.md").write_text("# 4분기\n", encoding="utf-8")
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_NONSTANDARD_PATH"]


def test_ready_nonstandard_file_is_still_an_error(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / "2026Q3.md").write_text(
        _front_matter("2026-07-01", "2026-09-30"),
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_NONSTANDARD_PATH"]


def test_index_page_is_the_only_approved_non_quarter_page(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "mkdocs.yml").write_text(
        "nav:\n  - 개요: quality-updates/index.md\n",
        encoding="utf-8",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def test_nonstandard_nav_and_index_targets_are_errors(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "mkdocs.yml").write_text(
        "nav:\n"
        "  - 별칭: quality-updates/2026/2026Q4.md\n"
        "  - 중첩: quality-updates/2026/q4/2026-10-01_to_2026-12-31.md\n"
        "  - 연도없음: quality-updates/2026-10-01_to_2026-12-31.md\n",
        encoding="utf-8",
    )
    (root / "docs" / "index.md").write_text(
        "[바로가기](quality-updates/2026/2026Q4.md)\n",
        encoding="utf-8",
    )
    (root / "docs" / "quality-updates" / "index.md").write_text(
        "[2026년](2026/q4/2026-10-01_to_2026-12-31.md)\n",
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert "QUARTER_NONSTANDARD_PATH" in _codes(errors)
    assert "QUARTER_LINK_TOO_EARLY" in _codes(errors)
    assert main([], now=NOV_20, repo_root=root) == 1


def test_allow_list_does_not_exempt_dash_or_path_variants(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "data" / "qu-early-allow.txt").write_text(
        "# 윤석님 본인의 명시 승인이 있어야 추가한다.\n"
        + Q4_KEY
        + "\n"
        + "docs/quality-updates/2026/q4/2026-10-01_to_2026-12-31.md\n"
        + "docs/quality-updates/2026/2026-10-01_to_2026-12-31.md.bak\n",
        encoding="utf-8",
    )
    nested = root / "docs" / "quality-updates" / "2026" / "q4"
    nested.mkdir()
    (nested / Q4_NAME).write_text(_front_matter("2026-10-01", "2026-12-31"), encoding="utf-8")
    (root / "mkdocs.yml").write_text(
        "nav:\n"
        "  - 표준: quality-updates/2026/2026-10-01_to_2026-12-31.md\n"
        "  - 중첩: quality-updates/2026/q4/2026-10-01_to_2026-12-31.md\n"
        "  - 접미: quality-updates/2026/2026-10-01_to_2026-12-31.md.bak\n",
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    messages = [err.message for _path, err in errors]
    assert any("q4/" in message for message in messages)
    assert any(message.endswith(".md.bak") or ".md.bak" in message for message in messages)
    assert not any(
        err.code == "QUARTER_LINK_TOO_EARLY" and "q4/" not in err.message and ".bak" not in err.message
        for _path, err in errors
    )
    assert main([], now=NOV_20, repo_root=root) == 1


def test_start_after_end_is_an_error_even_when_the_end_quarter_is_ready(tmp_path):
    root = _mini_repo(tmp_path)
    name = "2026-03-31_to_2026-01-01.md"
    (root / "docs" / "quality-updates" / "2026" / name).write_text(
        _front_matter("2026-03-31", "2026-01-01"),
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_DATE_ORDER", "QUARTER_DATE_ORDER"]
    assert "2026-03-31" in errors[0][1].message
    assert "2026-01-01" in errors[0][1].message


def test_filename_start_in_a_later_quarter_is_not_judged_by_the_end_alone(tmp_path):
    root = _mini_repo(tmp_path)
    name = "2026-10-01_to_2026-09-30.md"
    quarter = root / "docs" / "quality-updates" / "2026" / name
    quarter.write_text(_front_matter("2026-10-01", "2026-09-30"), encoding="utf-8")
    errors = quarter_timing_errors(root, NOV_20)
    codes = _codes(errors)
    assert "QUARTER_DATE_ORDER" in codes
    assert "QUARTER_TOO_EARLY" in codes
    early = next(err for _path, err in errors if err.code == "QUARTER_TOO_EARLY")
    assert "2027-01-05 09:00" in early.message


@pytest.mark.parametrize(
    "line",
    [
        "    **2026-10-01 – 2026-12-31 규제 업데이트가 추가되었습니다.**",
        "    **2026-10-01 — 2026-12-31 규제 업데이트가 추가되었습니다.**",
        "    **2026-10-01 - 2026-12-31 규제 업데이트가 추가되었습니다.**",
        "    **2026-10-01 to 2026-12-31 규제 업데이트가 추가되었습니다.**",
        "    **2026년 10월 1일 ~ 2026년 12월 31일 규제 업데이트가 추가되었습니다.**",
        "    **2026년 10월 1일 – 2026년 12월 31일 규제 업데이트가 추가되었습니다.**",
        "    **2026년 10월 1일부터 2026년 12월 31일까지 규제 업데이트가 추가되었습니다.**",
    ],
)
def test_latest_update_detects_other_range_forms(tmp_path, line):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n' + line + "\n",
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_HIGHLIGHT_TOO_EARLY"]
    assert "2027-01-05 09:00" in errors[0][1].message


def test_latest_update_dates_on_the_heading_line(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update 2026-10-01 – 2026-12-31"\n'
        "    본문에는 날짜가 없다.\n",
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_HIGHLIGHT_TOO_EARLY"]


def test_ready_latest_update_en_dash_is_quiet(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    **2026-07-01 – 2026-09-30 규제 업데이트가 추가되었습니다.**\n",
        encoding="utf-8",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def test_second_latest_update_block_is_not_skipped(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    **2026-07-01 ~ 2026-09-30 규제 업데이트가 추가되었습니다.**\n"
        "\n"
        '!!! info "Latest Update"\n'
        "    **2026-10-01 ~ 2026-12-31 규제 업데이트가 추가되었습니다.**\n",
        encoding="utf-8",
    )
    assert "QUARTER_HIGHLIGHT_TOO_EARLY" in _codes(quarter_timing_errors(root, NOV_20))


@pytest.mark.parametrize(
    "heading",
    [
        '??? note "Latest Update"',
        "!!! warning 'Latest Update'",
        "!!! tip “Latest Update”",
        "!!! abstract ‘Latest Update’",
        "!!! danger Latest Update",
        '!!! info "latest update"',
        '??? INFO "LATEST UPDATE"',
    ],
)
def test_latest_update_accepts_admonition_and_quote_forms(tmp_path, heading):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        f"{heading}\n    2026-10-01 ~ 2026-12-31\n",
        encoding="utf-8",
    )
    assert "QUARTER_HIGHLIGHT_TOO_EARLY" in _codes(quarter_timing_errors(root, NOV_20))


def test_quarter_index_latest_update_is_checked(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "index.md").write_text(
        '??? note "Latest Update"\n'
        "    2026-10-01 ~ 2026-12-31\n",
        encoding="utf-8",
    )
    assert "QUARTER_HIGHLIGHT_TOO_EARLY" in _codes(quarter_timing_errors(root, NOV_20))


def test_latest_update_reversed_range_is_date_order(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    2026-03-31 ~ 2026-01-01\n",
        encoding="utf-8",
    )
    assert "QUARTER_DATE_ORDER" in _codes(quarter_timing_errors(root, NOV_20))


@pytest.mark.parametrize(
    "line",
    [
        "    2026-10-01 〜 2026-12-31",
        "    2026-10-01 ∼ 2026-12-31",
        "    2026-10-01 － 2026-12-31",
        "    2026-10-01 − 2026-12-31",
        "    2026.10.01 ~ 2026.12.31",
        "    2026/10/01 ~ 2026/12/31",
        "    **2026-10-01** ~ **2026-12-31**",
    ],
)
def test_latest_update_reads_more_date_and_separator_forms(tmp_path, line):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n' + line + "\n",
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_HIGHLIGHT_TOO_EARLY"]


def test_latest_update_range_may_split_across_lines(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    2026-10-01\n"
        "    ~\n"
        "    2026-12-31\n",
        encoding="utf-8",
    )
    assert _codes(quarter_timing_errors(root, NOV_20)) == ["QUARTER_HIGHLIGHT_TOO_EARLY"]


def test_visible_latest_update_date_without_a_range_is_an_error(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    2026.10.01 규제 업데이트\n",
        encoding="utf-8",
    )
    assert "QUARTER_DATE_INVALID" in _codes(quarter_timing_errors(root, NOV_20))


def test_html_href_on_both_indexes_is_timed(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "index.md").write_text(
        '<a href="2026/2026-10-01_to_2026-12-31.md">4분기</a>\n',
        encoding="utf-8",
    )
    (root / "docs" / "index.md").write_text(
        '<a href="quality-updates&#47;2026&#47;2026-10-01_to_2026-12-31.md">4분기</a>\n',
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_LINK_TOO_EARLY", "QUARTER_LINK_TOO_EARLY"]
    assert {path.relative_to(root).as_posix() for path, _err in errors} == {
        "docs/quality-updates/index.md",
        "docs/index.md",
    }


def test_html_href_with_reversed_dates_is_date_order(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "index.md").write_text(
        '<a href="2026/2026-03-31_to_2026-01-01.md">거꾸로</a>\n',
        encoding="utf-8",
    )
    assert "QUARTER_DATE_ORDER" in _codes(quarter_timing_errors(root, NOV_20))


_LATEST_HEADINGS = [
    '???+ note "Latest Update"',
    '???+note "Latest Update"',
    '???+ info "Latest Update"',
    '!!! info "**Latest Update**"',
    '!!! info **Latest Update**',
    '!!! info inline "Latest Update"',
    '!!! info inline end "Latest Update"',
]


@pytest.mark.parametrize("heading", _LATEST_HEADINGS)
@pytest.mark.parametrize(
    "index_rel",
    ["docs/index.md", "docs/quality-updates/index.md"],
)
def test_latest_update_heading_variants_on_both_indexes(tmp_path, heading, index_rel):
    root = _mini_repo(tmp_path)
    (root / index_rel).write_text(
        f"{heading}\n    2026-10-01 ~ 2026-12-31\n",
        encoding="utf-8",
    )
    assert "QUARTER_HIGHLIGHT_TOO_EARLY" in _codes(quarter_timing_errors(root, NOV_20))


def test_collapsed_plus_block_after_a_normal_latest_update(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    2026-07-01 ~ 2026-09-30\n"
        "\n"
        '???+ note "Latest Update"\n'
        "    2026-10-01 ~ 2026-12-31\n",
        encoding="utf-8",
    )
    (root / "docs" / "quality-updates" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    2026-07-01 ~ 2026-09-30\n"
        "\n"
        '???+info "Latest Update"\n'
        "    2026-10-01 ~ 2026-12-31\n",
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors).count("QUARTER_HIGHLIGHT_TOO_EARLY") == 2


@pytest.mark.parametrize(
    "line",
    [
        "    2026. 10. 1. ~ 2026. 12. 31.",
        "    2026. 10. 01 ~ 2026. 12. 31",
        "    2026. 10. 1.부터 2026. 12. 31.까지",
    ],
)
def test_spaced_dot_dates_are_early_highlights(tmp_path, line):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n' + line + "\n",
        encoding="utf-8",
    )
    assert _codes(quarter_timing_errors(root, NOV_20)) == ["QUARTER_HIGHLIGHT_TOO_EARLY"]


def test_lone_spaced_dot_date_uses_the_same_token(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    2026. 10. 1.\n",
        encoding="utf-8",
    )
    assert "QUARTER_DATE_INVALID" in _codes(quarter_timing_errors(root, NOV_20))


def test_past_press_title_dot_date_is_not_a_false_positive(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(
        '!!! info "Latest Update"\n'
        "    **2026-07-01 ~ 2026-09-30 규제 업데이트가 추가되었습니다.**\n"
        "    본인 인증 서비스 일시 점검 안내(2026. 9. 19.(토) 21:00 ~ 2026. 9 20.(일) 05:00)\n",
        encoding="utf-8",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def test_tab_indented_latest_update_body_is_checked(tmp_path):
    body = '!!! info "Latest Update"\n\t2026-10-01 ~ 2026-12-31\n'
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(body, encoding="utf-8")
    (root / "docs" / "quality-updates" / "index.md").write_text(body, encoding="utf-8")
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_HIGHLIGHT_TOO_EARLY", "QUARTER_HIGHLIGHT_TOO_EARLY"]


_READY_NAME = "2026-07-01_to_2026-09-30.md"


def _write_ready_quarter(root: Path, body: str) -> None:
    (root / "docs" / "quality-updates" / "2026" / _READY_NAME).write_text(body, encoding="utf-8")


@pytest.mark.parametrize(
    "body",
    [
        "---\ntitle: t\nperiod:\n  from: 2026-10-01\n  to: 2026-12-31\n---\n",
        '---\ntitle: t\nperiod: {from: "2026-10-01", to: "2026-12-31"}\n---\n',
    ],
)
def test_period_without_start_end_keys_is_invalid(tmp_path, body):
    root = _mini_repo(tmp_path)
    _write_ready_quarter(root, body)
    assert _codes(quarter_timing_errors(root, NOV_20)) == ["QUARTER_DATE_INVALID"]


@pytest.mark.parametrize(
    "body",
    [
        "---\ntitle: t\nperiod.start: 2026-10-01\nperiod.end: 2026-12-31\n---\n",
        '---\ntitle: t\nperiod.start: "2026-10-01"\nperiod.end: "2026-12-31"\n---\n',
    ],
)
def test_toplevel_period_start_end_keys_are_invalid(tmp_path, body):
    root = _mini_repo(tmp_path)
    _write_ready_quarter(root, body)
    assert _codes(quarter_timing_errors(root, NOV_20)) == ["QUARTER_DATE_INVALID"]


def test_allow_list_does_not_hide_unreadable_period(tmp_path):
    root = _mini_repo(tmp_path)
    _write_ready_quarter(
        root,
        "---\nperiod:\n  from: 2026-10-01\n  to: 2026-12-31\n---\n",
    )
    (root / "data" / "qu-early-allow.txt").write_text(
        "# 윤석님 본인의 명시 승인\n"
        f"docs/quality-updates/2026/{_READY_NAME}\n",
        encoding="utf-8",
    )
    assert _codes(quarter_timing_errors(root, NOV_20)) == ["QUARTER_DATE_INVALID"]


def test_bom_front_matter_period_is_not_ignored(tmp_path):
    root = _mini_repo(tmp_path)
    _write_ready_quarter(
        root,
        "\ufeff---\ntitle: t\nperiod:\n  start: 2026-10-01\n  end: 2026-12-31\n---\n",
    )
    errors = quarter_timing_errors(root, NOV_20)
    codes = _codes(errors)
    assert "QUARTER_TOO_EARLY" in codes
    assert "QUARTER_PERIOD_MISMATCH" in codes
    assert "QUARTER_DATE_INVALID" not in codes
    early = next(err for _path, err in errors if err.code == "QUARTER_TOO_EARLY")
    assert "2027-01-05 09:00" in early.message


def test_bom_front_matter_matching_ready_period_is_quiet(tmp_path):
    root = _mini_repo(tmp_path)
    _write_ready_quarter(
        root,
        "\ufeff---\ntitle: t\nperiod:\n  start: 2026-07-01\n  end: 2026-09-30\n---\n",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def test_early_period_outside_latest_update_is_highlight(tmp_path):
    prose = (
        "## 최근 업데이트 하이라이트\n\n"
        "2026-10-01 ~ 2026-12-31 규제 업데이트가 추가되었습니다.\n\n"
        '!!! info "Latest Update"\n'
        "    **2026-07-01 ~ 2026-09-30 규제 업데이트가 추가되었습니다.**\n"
    )
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(prose, encoding="utf-8")
    (root / "docs" / "quality-updates" / "index.md").write_text(prose, encoding="utf-8")
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_HIGHLIGHT_TOO_EARLY", "QUARTER_HIGHLIGHT_TOO_EARLY"]
    assert all("2027-01-05 09:00" in err.message for _path, err in errors)


@pytest.mark.parametrize(
    "body",
    [
        "## 최근 업데이트 하이라이트\n\n26. 10. 1. ~ 26. 12. 31.\n",
        '!!! info "Latest Update"\n    26. 10. 1. ~ 26. 12. 31.\n',
    ],
)
def test_two_digit_year_range_is_too_early(tmp_path, body):
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(body, encoding="utf-8")
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_HIGHLIGHT_TOO_EARLY"]
    assert "2027-01-05 09:00" in errors[0][1].message


def test_past_press_dates_outside_latest_update_are_quiet(tmp_path):
    text = (
        "## 최근 업데이트 하이라이트\n\n"
        "본인 인증 서비스 일시 점검 안내(2026. 9. 19.(토) 21:00 ~ 2026. 9 20.(일) 05:00)\n"
        "2026. 9. 19. ~ 2026. 9. 20. 점검이 끝났다.\n"
        "26. 7. 8. ~ 26. 7. 9. 조치 의결 보도.\n"
        "- (26-09-19) [보도자료](https://example.test/press)\n"
        '!!! info "Latest Update"\n'
        "    **2026-07-01 ~ 2026-09-30 규제 업데이트가 추가되었습니다.**\n"
        "    본인 인증 서비스 일시 점검 안내(2026. 9. 19.(토) 21:00 ~ 2026. 9 20.(일) 05:00)\n"
    )
    root = _mini_repo(tmp_path)
    (root / "docs" / "index.md").write_text(text, encoding="utf-8")
    (root / "docs" / "quality-updates" / "index.md").write_text(text, encoding="utf-8")
    assert quarter_timing_errors(root, NOV_20) == []


def test_encoded_early_links_are_too_early(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "mkdocs.yml").write_text(
        "nav:\n  - 4분기: quality-updates%2F2026%2F2026-10-01_to_2026-12-31.md\n",
        encoding="utf-8",
    )
    (root / "docs" / "index.md").write_text(
        '<a href="quality-updates&#38;#47;2026&#38;#47;2026-10-01_to_2026-12-31.md">4분기</a>\n',
        encoding="utf-8",
    )
    (root / "docs" / "quality-updates" / "index.md").write_text(
        '<a href="2026%2F2026-10-01_to_2026-12-31.md">4분기</a>\n',
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == [
        "QUARTER_LINK_TOO_EARLY",
        "QUARTER_LINK_TOO_EARLY",
        "QUARTER_LINK_TOO_EARLY",
    ]
    assert {path.relative_to(root).as_posix() for path, _err in errors} == {
        "mkdocs.yml",
        "docs/index.md",
        "docs/quality-updates/index.md",
    }


def test_encoded_ready_quarter_link_is_quiet(tmp_path):
    root = _mini_repo(tmp_path)
    ready = "2026-07-01_to_2026-09-30.md"
    (root / "mkdocs.yml").write_text(
        f"nav:\n  - 3분기: quality-updates%2F2026%2F{ready}\n",
        encoding="utf-8",
    )
    (root / "docs" / "index.md").write_text(
        f'<a href="quality-updates&#38;#47;2026&#38;#47;{ready}">3분기</a>\n',
        encoding="utf-8",
    )
    (root / "docs" / "quality-updates" / "index.md").write_text(
        f'<a href="2026%2F{ready}">3분기</a>\n',
        encoding="utf-8",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def _join_slash(parts: list[str], kind: str) -> str:
    slash = {"double": "%252F", "entity": "%26%2347%3B", "triple": "%25252F"}[kind]
    return slash.join(parts)


def _write_encoded_surface(root: Path, surface: str, kind: str, filename: str) -> None:
    nav_path = _join_slash(["quality-updates", "2026", filename], kind)
    quarter_path = _join_slash(["2026", filename], kind)
    if surface == "nav":
        (root / "mkdocs.yml").write_text(f"nav:\n  - 분기: {nav_path}\n", encoding="utf-8")
    elif surface == "index-md":
        (root / "docs" / "index.md").write_text(f"[4분기]({nav_path})\n", encoding="utf-8")
    elif surface == "index-href":
        (root / "docs" / "index.md").write_text(f'<a href="{nav_path}">4분기</a>\n', encoding="utf-8")
    else:
        (root / "docs" / "quality-updates" / "index.md").write_text(
            f'<a href="{quarter_path}">4분기</a>\n',
            encoding="utf-8",
        )


@pytest.mark.parametrize("kind", ["double", "entity", "triple"])
@pytest.mark.parametrize("surface", ["nav", "index-md", "index-href", "quarter-index"])
def test_nested_encoded_early_link_is_too_early(tmp_path, kind, surface):
    root = _mini_repo(tmp_path)
    _write_encoded_surface(root, surface, kind, Q4_NAME)
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_LINK_TOO_EARLY"]
    assert "2027-01-05 09:00" in errors[0][1].message


@pytest.mark.parametrize("kind", ["double", "entity", "triple"])
@pytest.mark.parametrize("surface", ["nav", "index-md", "index-href", "quarter-index"])
def test_nested_encoded_ready_link_is_quiet(tmp_path, kind, surface):
    root = _mini_repo(tmp_path)
    _write_encoded_surface(root, surface, kind, "2026-07-01_to_2026-09-30.md")
    assert quarter_timing_errors(root, NOV_20) == []


def test_decode_past_the_cap_is_nonstandard(tmp_path):
    import urllib.parse

    root = _mini_repo(tmp_path)
    token = "quality-updates/2026/2026-10-01_to_2026-12-31.md"
    for _ in range(12):
        token = urllib.parse.quote(token, safe="")
    (root / "mkdocs.yml").write_text(f"nav:\n  - 4분기: {token}\n", encoding="utf-8")
    (root / "docs" / "index.md").write_text(f"[4분기]({token})\n", encoding="utf-8")
    (root / "docs" / "quality-updates" / "index.md").write_text(
        f'<a href="{token}">4분기</a>\n',
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == [
        "QUARTER_NONSTANDARD_PATH",
        "QUARTER_NONSTANDARD_PATH",
        "QUARTER_NONSTANDARD_PATH",
    ]


@pytest.mark.parametrize(
    "line",
    [
        "'26. 10. 1. ~ '26. 12. 31.",
        "'26.10.1.~'26.12.31.",
        "(26-10-01) ~ (26-12-31)",
        "\u201926. 10. 1. ~ \u201926. 12. 31.",
    ],
)
@pytest.mark.parametrize("inside", [False, True])
def test_apostrophe_and_paren_year_ranges_are_early(tmp_path, line, inside):
    root = _mini_repo(tmp_path)
    if inside:
        body = f'!!! info "Latest Update"\n    {line}\n'
    else:
        body = f"## 최근 업데이트 하이라이트\n\n{line}\n"
    (root / "docs" / "index.md").write_text(body, encoding="utf-8")
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_HIGHLIGHT_TOO_EARLY"]
    assert "2027-01-05 09:00" in errors[0][1].message


@pytest.mark.parametrize("inside", [False, True])
def test_apostrophe_ready_quarter_range_is_quiet(tmp_path, inside):
    root = _mini_repo(tmp_path)
    line = "'26. 7. 1. ~ '26. 9. 30."
    if inside:
        body = f'!!! info "Latest Update"\n    {line}\n'
    else:
        body = f"## 최근 업데이트 하이라이트\n\n{line}\n"
    (root / "docs" / "index.md").write_text(body, encoding="utf-8")
    assert quarter_timing_errors(root, NOV_20) == []


@pytest.mark.parametrize("inside", [False, True])
def test_underscore_to_early_range_is_highlight(tmp_path, inside):
    root = _mini_repo(tmp_path)
    line = "2026-10-01_to_2026-12-31 규제 업데이트가 추가되었습니다."
    if inside:
        body = f'!!! info "Latest Update"\n    {line}\n'
    else:
        body = line + "\n"
    (root / "docs" / "index.md").write_text(body, encoding="utf-8")
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_HIGHLIGHT_TOO_EARLY"]
    assert "2027-01-05 09:00" in errors[0][1].message


@pytest.mark.parametrize("inside", [False, True])
def test_underscore_to_ready_range_is_quiet(tmp_path, inside):
    root = _mini_repo(tmp_path)
    line = "2026-07-01_to_2026-09-30 규제 업데이트가 추가되었습니다."
    if inside:
        body = f'!!! info "Latest Update"\n    {line}\n'
    else:
        body = line + "\n"
    (root / "docs" / "index.md").write_text(body, encoding="utf-8")
    (root / "docs" / "quality-updates" / "index.md").write_text(
        "- **[2014년](2014/2014-10-01_to_2014-12-31.md)** — 1·2·3·4분기 (01–12월)\n"
        "- **[2026년](2026/2026-07-01_to_2026-09-30.md)** — 1·2·3분기 (01–09월)\n",
        encoding="utf-8",
    )
    assert quarter_timing_errors(root, NOV_20) == []


@pytest.mark.parametrize(
    "body",
    [
        "---\nPeriod: {start: 2026-10-01, end: 2026-12-31}\n---\n",
        "---\nperiod_start: 2026-10-01\nperiod_end: 2026-12-31\n---\n",
        "---\nperiod: {start: 2026-07-01, to: 2026-12-31}\n---\n",
        "---\nperiod:\n  start: 2026-07-01\n---\n",
    ],
)
def test_misspelled_or_partial_period_is_invalid(tmp_path, body):
    root = _mini_repo(tmp_path)
    _write_ready_quarter(root, body)
    assert _codes(quarter_timing_errors(root, NOV_20)) == ["QUARTER_DATE_INVALID"]


def test_blank_line_and_bom_before_front_matter_is_read(tmp_path):
    root = _mini_repo(tmp_path)
    _write_ready_quarter(
        root,
        "\n\ufeff---\nperiod:\n  start: 2026-10-01\n  end: 2026-12-31\n---\n",
    )
    errors = quarter_timing_errors(root, NOV_20)
    codes = _codes(errors)
    assert "QUARTER_TOO_EARLY" in codes
    assert "QUARTER_PERIOD_MISMATCH" in codes
    assert "QUARTER_DATE_INVALID" not in codes
    early = next(err for _path, err in errors if err.code == "QUARTER_TOO_EARLY")
    assert "2027-01-05 09:00" in early.message


def test_null_period_and_period_label_stay_quiet(tmp_path):
    root = _mini_repo(tmp_path)
    _write_ready_quarter(
        root,
        "---\ntitle: t\nperiod_label: 2026-Q3\nperiod: null\n---\n",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def test_ready_period_and_front_matterless_2024_quarters_stay_quiet(tmp_path):
    root = _mini_repo(tmp_path)
    _write_ready_quarter(
        root,
        "---\ntitle: t\nperiod_label: 2026-Q3\nperiod:\n  start: 2026-07-01\n  end: 2026-09-30\n---\n",
    )
    folder = root / "docs" / "quality-updates" / "2024"
    folder.mkdir()
    for name in (
        "2024-01-01_to_2024-03-31.md",
        "2024-04-01_to_2024-06-30.md",
        "2024-07-01_to_2024-09-30.md",
    ):
        (folder / name).write_text("### 금융감독원\n", encoding="utf-8")
    assert quarter_timing_errors(root, NOV_20) == []
