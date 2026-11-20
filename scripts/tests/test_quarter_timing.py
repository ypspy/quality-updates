# -*- coding: utf-8 -*-
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quarter_timing import (
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


def test_load_allow_list_ignores_comments_and_normalizes(tmp_path):
    path = tmp_path / "qu-early-allow.txt"
    path.write_text(
        "# 윤석님 본인의 명시 승인이 있어야 추가한다.\n"
        "\n"
        "  docs/quality-updates/2026/2026-10-01_to_2026-12-31.md  \n"
        "# docs/quality-updates/2026/2026-01-01_to_2026-03-31.md\n",
        encoding="utf-8",
    )
    assert load_allow_list(path) == {Q4_KEY}


def test_missing_allow_list_is_empty(tmp_path):
    assert load_allow_list(tmp_path / "missing.txt") == set()


def test_committed_allow_list_is_empty_and_requires_owner_approval():
    path = REPO / "data" / "qu-early-allow.txt"
    text = path.read_text(encoding="utf-8")
    assert "명시 승인" in text
    assert load_allow_list(path) == set()


def _front_matter(end: str) -> str:
    return f"---\ntitle: t\nperiod:\n  start: 2026-01-01\n  end: {end}\n---\n"


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
    quarter.write_text(_front_matter("2026-12-31"), encoding="utf-8")
    errors = quarter_timing_errors(root, NOV_20)
    assert _codes(errors) == ["QUARTER_TOO_EARLY"]
    assert errors[0][0] == quarter
    assert "2027-01-05 09:00" in errors[0][1].message


def test_ready_quarter_file_is_quiet(tmp_path):
    root = _mini_repo(tmp_path)
    name = "2026-07-01_to_2026-09-30.md"
    (root / "docs" / "quality-updates" / "2026" / name).write_text(
        _front_matter("2026-09-30"),
        encoding="utf-8",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def test_file_is_allowed_at_the_update_instant(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / Q4_NAME).write_text(
        _front_matter("2026-12-31"),
        encoding="utf-8",
    )
    now = datetime(2027, 1, 5, 9, 0, tzinfo=SEOUL)
    assert quarter_timing_errors(root, now) == []


def test_front_matter_end_wins_over_filename(tmp_path):
    root = _mini_repo(tmp_path)
    folder = root / "docs" / "quality-updates" / "2026"
    (folder / Q4_NAME).write_text(_front_matter("2026-09-30"), encoding="utf-8")
    (folder / "2026-07-01_to_2026-09-30.md").write_text(
        _front_matter("2026-12-31"),
        encoding="utf-8",
    )
    errors = quarter_timing_errors(root, NOV_20)
    assert len(errors) == 1
    assert errors[0][0].name == "2026-07-01_to_2026-09-30.md"
    assert errors[0][1].code == "QUARTER_TOO_EARLY"


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
        _front_matter("2026-12-31"),
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


def test_link_uses_front_matter_of_existing_target(tmp_path):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / Q4_NAME).write_text(
        _front_matter("2026-09-30"),
        encoding="utf-8",
    )
    (root / "docs" / "index.md").write_text(
        f"[바로가기](quality-updates/2026/{Q4_NAME})\n",
        encoding="utf-8",
    )
    assert quarter_timing_errors(root, NOV_20) == []


def test_main_reports_early_quarter_and_honors_allow_list(tmp_path, capsys):
    root = _mini_repo(tmp_path)
    (root / "docs" / "quality-updates" / "2026" / Q4_NAME).write_text(
        _front_matter("2026-12-31"),
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
