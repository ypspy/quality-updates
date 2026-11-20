"""위원 논의 의사록 출처. 주 링크는 첨부 목록의 의사록 fileNo, 게시물은 같은 줄에 남긴다."""

from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from attach_sanction_minutes import detail_attachments, minutes_source_bullet
from validate_content import validate_agenda_decision_sources, validate_minutes_sources

Q3 = Path("docs/quality-updates/2026/2026-07-01_to_2026-09-30.md")
Q1 = Path("docs/quality-updates/2026/2026-01-01_to_2026-03-31.md")
Q4_2025 = Path("docs/quality-updates/2025/2025-10-01_to_2025-12-31.md")
REPO = Path(__file__).resolve().parents[2]

# 87090: fileNo=2는 의결서 zip, 의사록 PDF는 fileNo=3.
FSC7 = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87090&fileTy=ATTACH&fileNo=2">2026년도 제7차 금융위원회 안건 및 제재안건 의결서(홈).zip</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87090&fileTy=ATTACH&fileNo=2">파일다운로드</a>
<a href="https://fsc.go.kr/comm/getFile?fileTy=ATTACH&fileNo=3&upperNo=87090&srvcId=BBSTY1">2026년 제7차 금융위원회 의사록(공개용).pdf</a>
<a href="https://fsc.go.kr/comm/getFile?fileTy=ATTACH&fileNo=3&upperNo=87090&srvcId=BBSTY1">파일다운로드</a>
"""

DECISION_ONLY = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87906&fileTy=ATTACH&fileNo=2">(공개용) 의결 234.pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87906&fileTy=ATTACH&fileNo=3">안건 및 제재안건 의결서.zip</a>
"""

HWP_ONLY = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=27601&fileTy=ATTACH&fileNo=4">제3차 금융위 의사록(홈).hwp</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=27601&fileTy=ATTACH&fileNo=5">안건 및 제재안건 의결서.zip</a>
"""

PDF_AND_HWP = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=86410&fileTy=ATTACH&fileNo=7">2026년 제1차 증권선물위원회 의사록(공개용).hwp</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=86410&fileTy=ATTACH&fileNo=1">2026년 제1차 증권선물위원회 의사록(공개용).pdf</a>
"""

LABEL = "2026년도 제7차 금융위원회 의사록"
TRAIL = "제190호(2026.6.12. 공개). 회사명은 가려져 있음"


def _note(*bullets: str) -> list[str]:
    lines = ['    !!! note "위원 논의"', ""]
    lines.extend(f"        {bullet}" for bullet in bullets)
    return lines


def test_minutes_source_uses_the_named_pdf_not_file_no_1():
    bullet = minutes_source_bullet(detail_attachments(FSC7), "/no020101/87090", LABEL, TRAIL)
    assert bullet == (
        "- (출처) [2026년도 제7차 금융위원회 의사록]"
        "(https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87090"
        "&fileTy=ATTACH&fileNo=3) 제190호(2026.6.12. 공개). 회사명은 가려져 있음"
        " \u00b7 [게시물](https://www.fsc.go.kr/no020101/87090)"
    )
    assert "fileNo=1" not in bullet
    assert "fileNo=2" not in bullet


def test_minutes_source_is_absent_when_only_decision_files_exist():
    assert minutes_source_bullet(detail_attachments(DECISION_ONLY), "https://fsc.go.kr/no020102/87906", LABEL) is None
    assert minutes_source_bullet([], "https://www.fsc.go.kr/no020101/87090", LABEL) is None


def test_hwp_minutes_attachment_is_a_getfile_link():
    bullet = minutes_source_bullet(
        detail_attachments(HWP_ONLY),
        "https://www.fsc.go.kr/no020101/27601",
        "제3차 금융위원회 의사록",
        "(2008.4.25. 공개)",
    )
    assert bullet == (
        "- (출처) [제3차 금융위원회 의사록]"
        "(https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=27601"
        "&fileTy=ATTACH&fileNo=4)(2008.4.25. 공개)"
        " \u00b7 [게시물](https://www.fsc.go.kr/no020101/27601)"
    )


def test_pdf_minutes_wins_when_an_hwp_copy_is_also_attached():
    bullet = minutes_source_bullet(
        detail_attachments(PDF_AND_HWP),
        "https://www.fsc.go.kr/no020102/86410",
        "2026년 제1차 증권선물위원회 의사록",
    )
    assert bullet is not None
    assert "fileNo=1" in bullet
    assert "fileNo=7" not in bullet


def test_label_without_minutes_word_is_not_emitted():
    attachments = detail_attachments(FSC7)
    assert minutes_source_bullet(attachments, "https://www.fsc.go.kr/no020101/87090", "의결서") is None


def test_minutes_source_line_passes():
    bullet = minutes_source_bullet(detail_attachments(FSC7), "https://www.fsc.go.kr/no020101/87090", LABEL, TRAIL)
    assert bullet is not None
    assert validate_minutes_sources(_note(bullet), Q3) == []


def test_post_only_minutes_link_fails():
    old = (
        "- (출처) [2026년 제16차 증권선물위원회 의사록](https://www.fsc.go.kr/no020102/88144)"
        " 의결 제267호(2026.11.13. 공개)"
    )
    errors = validate_minutes_sources(_note(old), Q1)
    assert [error.code for error in errors] == ["MINUTES_SOURCE_FORMAT"]


def test_getfile_without_minutes_in_the_label_fails():
    bullet = (
        "- (출처) [의결서]"
        "(https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=88144"
        "&fileTy=ATTACH&fileNo=1) 의결 제267호(2026.11.13. 공개)"
        " \u00b7 [게시물](https://www.fsc.go.kr/no020102/88144)"
    )
    errors = validate_minutes_sources(_note(bullet), Q3)
    assert [error.code for error in errors] == ["MINUTES_SOURCE_FORMAT"]


def test_hwp_label_is_not_rejected_for_its_extension():
    bullet = minutes_source_bullet(
        detail_attachments(HWP_ONLY),
        "https://www.fsc.go.kr/no020101/27601",
        "제3차 금융위원회 의사록.hwp",
    )
    assert bullet is not None
    assert ".hwp" in bullet
    assert validate_minutes_sources(_note(bullet), Q1) == []


def test_unpublished_minutes_line_passes():
    assert validate_minutes_sources(_note("- 미공개"), Q1) == []
    assert validate_minutes_sources(_note("- (출처) 미공개"), Q3) == []


def test_quarters_before_2026_q1_are_not_checked():
    old = "- (출처) [2014년 제2차 증권선물위원회 의사록](https://www.fsc.go.kr/no020102/1)"
    assert validate_minutes_sources(_note(old), Q4_2025) == []


def test_decision_box_is_not_a_minutes_source():
    lines = [
        '    !!! info "안건 분석"',
        "",
        "        - (출처) [2026년 제13차 증권선물위원회 안건 및 제재안건 의결서]"
        "(https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87654"
        "&fileTy=ATTACH&fileNo=2) 의결 제211호(2026.9.4. 공개)",
        "",
        '    !!! note "위원 논의"',
        "",
        "        - 미공개",
    ]
    assert validate_minutes_sources(lines, Q3) == []
    assert validate_agenda_decision_sources(lines, Q3) == []


TWO_PDFS = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=86410&fileTy=ATTACH&fileNo=1">2026년 제1차 증권선물위원회 의사록(공개용).pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=86410&fileTy=ATTACH&fileNo=8">2026년 제1차 증권선물위원회 의사록(수정).pdf</a>
"""


def test_two_primary_minutes_pdfs_are_not_guessed():
    assert minutes_source_bullet(
        detail_attachments(TWO_PDFS),
        "https://www.fsc.go.kr/no020102/86410",
        "2026년 제1차 증권선물위원회 의사록",
    ) is None


def test_2026_quarter_minutes_sources_use_getfile_and_the_post():
    expected = {
        "2026-01-01_to_2026-03-31.md": {
            "86410": "1", "86506": "1", "86569": "1", "86774": "1",
            "86850": "1", "86904": "1", "86967": "1",
        },
        "2026-04-01_to_2026-06-30.md": {
            "87010": "1", "87090": "3", "87251": "1", "87483": "1",
            "87508": "1", "87581": "1",
        },
        "2026-07-01_to_2026-09-30.md": {
            "87654": "1", "87703": "1", "87748": "1", "87823": "1",
            "88040": "1", "88102": "1", "88144": "1",
        },
    }
    source = re.compile(r"^- \(출처\) \[(?P<label>[^\]]+)\]\((?P<url>[^)]+)\)(?P<rest>.*)$")
    for name, posts in expected.items():
        path = REPO / "docs/quality-updates/2026" / name
        text = path.read_text(encoding="utf-8")
        assert validate_minutes_sources(text.splitlines(), path) == []
        found = {}
        for line in text.splitlines():
            matched = source.match(line.strip())
            if matched is None or "의사록" not in matched.group("label"):
                continue
            post = re.search(r"/no02010[12]/(\d+)\)\s*$", matched.group("rest"))
            assert post is not None, line
            assert matched.group("url").startswith("https://www.fsc.go.kr/comm/getFile?")
            assert f"upperNo={post.group(1)}&fileTy=ATTACH&fileNo={posts[post.group(1)]}" in matched.group("url")
            found[post.group(1)] = line
        assert found.keys() == posts.keys()


def test_writer_template_states_the_minutes_source_rule():
    skill = (REPO / ".claude/skills/quality-updates-writer/SKILL.md").read_text(encoding="utf-8")
    guide = (REPO / "docs/project/quarterly-operations-guide.md").read_text(encoding="utf-8")
    for text in (skill, guide):
        assert "minutes_source_bullet" in text
        assert "fileNo를 하드코딩하지 않는다" in text
        assert "2026년 1분기부터" in text
        assert "미공개" in text
        assert "HWP" in text
