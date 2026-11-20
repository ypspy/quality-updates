"""안건 분석 의결서 출처 링크. 2026 Q1부터 필수이고, 그 전 문서는 검사하지 않는다."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from attach_sanction_minutes import decision_source_bullet
from validate_content import validate_agenda_decision_sources

Q3 = Path("docs/quality-updates/2026/2026-07-01_to_2026-09-30.md")
Q2 = Path("docs/quality-updates/2026/2026-04-01_to_2026-06-30.md")
Q1 = Path("docs/quality-updates/2026/2026-01-01_to_2026-03-31.md")
Q4_2025 = Path("docs/quality-updates/2025/2025-10-01_to_2025-12-31.md")
REPO = Path(__file__).resolve().parents[2]

FSC15 = [
    (
        "2026년 제15차 금융위원회 의사록(홈).pdf",
        "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=88102&fileTy=ATTACH&fileNo=1",
    ),
    (
        "2026년도 제15차 금융위원회 안건 및 제재안건 의결서(홈).zip",
        "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=88102&fileTy=ATTACH&fileNo=3",
    ),
]

SFC5 = [
    (
        "2026년 제5차 증권선물위원회 의사록(공개용).pdf",
        "/comm/getFile?srvcId=BBSTY1&upperNo=86850&fileTy=ATTACH&fileNo=1",
    ),
    (
        "2026년 제5차 증권선물위원회 안건 및 제재안건 의결서.zip",
        "/comm/getFile?srvcId=BBSTY1&upperNo=86850&fileTy=ATTACH&fileNo=4",
    ),
]


def _box(*bullets: str) -> list[str]:
    lines = ['    !!! info "안건 분석"', ""]
    lines.extend(f"        {bullet}" for bullet in bullets)
    lines.append("")
    lines.append('    !!! note "위원 논의"')
    return lines


def test_decision_source_uses_the_named_bundle_not_file_no_2():
    bullet = decision_source_bullet(FSC15, "제394호(2026.11.6. 공개)")
    assert bullet == (
        "- (출처) [2026년도 제15차 금융위원회 안건 및 제재안건 의결서]"
        "(https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=88102"
        "&fileTy=ATTACH&fileNo=3) 제394호(2026.11.6. 공개)"
    )
    assert "fileNo=2" not in bullet
    assert "의사록" not in bullet


def test_decision_source_keeps_file_no_4_and_a_zip_suffix():
    bullet = decision_source_bullet(SFC5, "의결 제72호(2026.5.8. 공개)")
    assert bullet is not None
    assert "fileNo=4" in bullet
    assert bullet.startswith("- (출처) [2026년 제5차 증권선물위원회 안건 및 제재안건 의결서](")

    zipped = decision_source_bullet(
        [
            (
                "2026년 제12차 증권선물위원회 안건 및 제재안건 의결서.Zip",
                "https://www.fsc.go.kr/comm/getFile?fileTy=ATTACH&fileNo=2&upperNo=87581&srvcId=BBSTY1",
            )
        ],
        "(2026.8.21. 공개)",
    )
    assert zipped == (
        "- (출처) [2026년 제12차 증권선물위원회 안건 및 제재안건 의결서]"
        "(https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87581"
        "&fileTy=ATTACH&fileNo=2)(2026.8.21. 공개)"
    )


def test_decision_source_is_absent_when_the_bundle_is_missing_or_ambiguous():
    assert decision_source_bullet(
        [("(공개용) 의결 234.pdf", "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87906&fileTy=ATTACH&fileNo=2")]
    ) is None
    assert decision_source_bullet(
        [
            ("안건 및 의결서.zip", "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=1&fileTy=ATTACH&fileNo=2"),
            ("안건 및 제재안건 의결서.zip", "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=1&fileTy=ATTACH&fileNo=3"),
        ]
    ) is None
    assert decision_source_bullet([]) is None


def test_q3_agenda_box_without_a_source_link_fails():
    errors = validate_agenda_decision_sources(_box("- (의결 211) 요약"), Q3)
    assert [error.code for error in errors] == ["AGENDA_SOURCE_MISSING"]


def test_q3_agenda_box_with_the_source_link_passes():
    bullet = decision_source_bullet(FSC15, "제394호(2026.11.6. 공개)")
    assert bullet is not None
    errors = validate_agenda_decision_sources(_box(bullet, "- (제394호) 요약"), Q3)
    assert errors == []


def test_q3_wrong_source_shape_fails():
    cases = [
        "- (출처) [2026년 제13차 증권선물위원회 의사록](https://www.fsc.go.kr/no020102/87654) 의결 제211호(2026.9.4. 공개)",
        "- (출처) [의결서](https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87654&fileTy=ATTACH)",
        "- (출처) [의결서](https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87654&fileTy=ATTACH&fileNo=2)",
        "- (출처) [의결서](https://www.fsc.go.kr/comm/getFile?fileNo=2&srvcId=BBSTY1&upperNo=87654&fileTy=ATTACH)",
    ]
    for bullet in cases:
        errors = validate_agenda_decision_sources(_box(bullet), Q3)
        assert [error.code for error in errors] == ["AGENDA_SOURCE_FORMAT"], bullet


def test_q3_source_link_after_the_summary_fails():
    bullet = decision_source_bullet(SFC5, "의결 제72호(2026.5.8. 공개)")
    assert bullet is not None
    errors = validate_agenda_decision_sources(_box("- (의결 72) 요약", bullet), Q3)
    assert [error.code for error in errors] == ["AGENDA_SOURCE_FORMAT"]


def test_q1_agenda_box_without_a_source_link_fails():
    errors = validate_agenda_decision_sources(_box("- (의결 22) 요약"), Q1)
    assert [error.code for error in errors] == ["AGENDA_SOURCE_MISSING"]


def test_q2_agenda_box_without_a_source_link_fails():
    errors = validate_agenda_decision_sources(_box("- (제151호) 요약"), Q2)
    assert [error.code for error in errors] == ["AGENDA_SOURCE_MISSING"]


def test_quarters_before_2026_q1_are_not_checked():
    lines = _box("- (의결 48) 요약")
    assert validate_agenda_decision_sources(lines, Q4_2025) == []


def test_2026_q1_document_agenda_boxes_have_decision_sources():
    text = (REPO / Q1).read_text(encoding="utf-8")
    errors = validate_agenda_decision_sources(text.splitlines(), Q1)
    assert errors == []
    assert text.count('!!! info "안건 분석"') == 9


def test_2026_q2_document_agenda_boxes_have_decision_sources():
    text = (REPO / Q2).read_text(encoding="utf-8")
    errors = validate_agenda_decision_sources(text.splitlines(), Q2)
    assert errors == []
    assert text.count('!!! info "안건 분석"') == 18


def test_2026_q3_document_agenda_boxes_have_decision_sources():
    text = (REPO / Q3).read_text(encoding="utf-8")
    errors = validate_agenda_decision_sources(text.splitlines(), Q3)
    assert errors == []
    assert text.count('!!! info "안건 분석"') == 10


def test_writer_template_requires_the_decision_source_line():
    skill = (REPO / ".claude/skills/quality-updates-writer/SKILL.md").read_text(encoding="utf-8")
    guide = (REPO / "docs/project/quarterly-operations-guide.md").read_text(encoding="utf-8")
    for text in (skill, guide):
        assert "decision_source_bullet" in text
        assert "2로 고정하지 않는다" in text
        assert "2026년 1분기부터 이 줄이 없으면" in text
        assert "2026년 3분기부터 이 줄이 없으면" not in text
