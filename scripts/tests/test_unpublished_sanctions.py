# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validate_content import meeting_folders, unmatched_source_paths, validate_unpublished_sanctions

RECORD = """# 2026-증선위-5차

| 번호 | 구분 | 제목 | 마스킹 | 연결 |
| --- | --- | --- | --- | --- |
| 66 | agenda | staff-agenda.pdf | 아니오 | unmatched |
| 66 | decision | staff-decision.pdf | 아니오 | unmatched |
| 72 | decision | named.pdf | 예 | 이화전기공업㈜ |
"""

QUARTER = """#### 제재 의결

- (26-03-11) [조사·감리결과 조치](https://fsc.go.kr/no010101/1)

    <!-- source: pdf|downloads/sanctions/2026-증선위-5차/minutes.pdf -->
"""


def _root(tmp_path: Path) -> Path:
    folder = tmp_path / "2026-증선위-5차"
    folder.mkdir()
    (folder / "record.md").write_text(RECORD, encoding="utf-8")
    return tmp_path


def test_meeting_folder_comes_from_minutes_or_sanction_path():
    text = QUARTER + "<!-- source: pdf|downloads/sanctions/2026-금융위-5차/decision/a.pdf -->"
    assert meeting_folders(text) == {"2026-증선위-5차", "2026-금융위-5차"}


def test_temporary_folder_does_not_collapse_into_the_regular_name():
    text = "\n".join(
        [
            "<!-- source: pdf|downloads/sanctions/2026-금융위-1차/minutes.pdf -->",
            "<!-- source: pdf|downloads/sanctions/2026-금융위-임시-1차/minutes.pdf -->",
            "<!-- source: pdf|downloads/sanctions/2026-금융위-서면-1차/minutes-추가.pdf -->",
        ]
    )
    assert meeting_folders(text) == {
        "2026-금융위-1차",
        "2026-금융위-임시-1차",
        "2026-금융위-서면-1차",
    }


def test_unmatched_paths_skip_linked_rows():
    assert unmatched_source_paths(RECORD, "2026-증선위-5차") == [
        "downloads/sanctions/2026-증선위-5차/agenda/staff-agenda.pdf",
        "downloads/sanctions/2026-증선위-5차/decision/staff-decision.pdf",
    ]


def test_missing_source_fails_and_press_or_unpublished_source_passes(tmp_path):
    root = _root(tmp_path)
    doc = tmp_path / "2026-01-01_to_2026-03-31.md"
    missing = validate_unpublished_sanctions(QUARTER.splitlines(), doc, root)
    assert [error.code for error in missing] == ["UNPUBLISHED_SOURCE", "UNPUBLISHED_SOURCE"]

    on_press = QUARTER.replace(
        "downloads/sanctions/2026-증선위-5차/minutes.pdf -->",
        "downloads/sanctions/2026-증선위-5차/minutes.pdf -->\n"
        "    <!-- source: pdf|downloads/sanctions/2026-증선위-5차/agenda/staff-agenda.pdf -->\n"
        "    <!-- source: pdf|downloads/sanctions/2026-증선위-5차/decision/staff-decision.pdf -->",
    )
    assert validate_unpublished_sanctions(on_press.splitlines(), doc, root) == []

    unpublished = QUARTER + (
        "\n##### 미보도\n\n"
        "- 예시\n\n"
        "    <!-- source: pdf|downloads/sanctions/2026-증선위-5차/agenda/staff-agenda.pdf -->\n"
        "    <!-- source: pdf|downloads/sanctions/2026-증선위-5차/decision/staff-decision.pdf -->\n"
    )
    assert validate_unpublished_sanctions(unpublished.splitlines(), doc, root) == []


def test_quarter_without_a_meeting_skips_the_check(tmp_path):
    doc = tmp_path / "note.md"
    assert validate_unpublished_sanctions(["일반 문장"], doc, tmp_path) == []


def test_missing_record_skips_the_meeting(tmp_path):
    doc = tmp_path / "2026-01-01_to_2026-03-31.md"
    assert validate_unpublished_sanctions(QUARTER.splitlines(), doc, tmp_path) == []
