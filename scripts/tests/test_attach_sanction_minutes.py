# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attach_sanction_minutes import DecisionPost, attach_minutes, meeting_key, select_minutes_pdf

PRESS = """### 금융위원회

#### 제재 의결

- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회(’26.7.8.)](https://fsc.go.kr/no010101/87293)

    !!! note "위원 논의"

        - 미공개임

#### 보도자료

- (26-07-24) [외부감사 규정 예고](https://fsc.go.kr/no010101/1)
"""

LINK = "- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회(’26.7.8.)](https://fsc.go.kr/no010101/87293)"
RELEASE_PDF = "downloads/260708(보도참고) 사업보고서 등에 대한 조사·감리결과 조치.pdf"
MINUTES_PDF = "downloads/minutes-13.pdf"
ZIP_URL = "https://fsc.go.kr/comm/getFile?fileNo=2"

POSTS = [
    DecisionPost(2026, "증선위", "정기", 13, "https://fsc.go.kr/files/minutes-13.pdf", [ZIP_URL]),
    DecisionPost(2026, "증선위", "정기", 13, "https://fsc.go.kr/comm/getFile?other=1", []),
]


def _insert_marker(text: str, marker: str) -> str:
    return text.replace(LINK + "\n", LINK + "\n\n    " + marker + "\n", 1)


def test_ambiguous_key_does_not_attach_and_ignores_zip():
    updated, report = attach_minutes(PRESS, POSTS)
    assert updated == PRESS
    assert "fileNo=2" not in " ".join(report)
    assert ZIP_URL not in updated
    assert ZIP_URL not in " ".join(report)
    assert select_minutes_pdf((2026, "증선위", "정기", 13), POSTS) is None


def test_single_minutes_pdf_is_attached_without_rewriting_the_table():
    posts = [POSTS[0]]
    updated, report = attach_minutes(PRESS, posts)
    assert "source: pdf|downloads/" in updated
    assert MINUTES_PDF in updated
    assert "외부감사 규정" in updated
    assert updated.index("외부감사 규정") > updated.index("제재 의결")
    assert "fileNo=2" not in updated
    assert ZIP_URL not in updated
    assert ZIP_URL not in " ".join(report)
    assert report == ["attached 2026 증선위 정기 13"]


def test_press_release_pdf_does_not_block_minutes():
    marked = _insert_marker(PRESS, f"<!-- source: pdf|{RELEASE_PDF} -->")
    updated, report = attach_minutes(marked, [POSTS[0]])
    assert RELEASE_PDF in updated
    assert MINUTES_PDF in updated
    assert updated.count(MINUTES_PDF) == 1
    assert "fileNo=2" not in updated
    assert ZIP_URL not in " ".join(report)
    assert report == ["attached 2026 증선위 정기 13"]


def test_skips_only_when_minutes_filename_already_in_block():
    marked = _insert_marker(PRESS, f"<!-- source: pdf|{MINUTES_PDF} -->")
    updated, report = attach_minutes(marked, [POSTS[0]])
    assert updated == marked
    assert report == []
    assert ZIP_URL not in updated


def test_meeting_key_reads_year_after_the_committee_name():
    title = (
        "사업보고서 등에 대한 조사·감리결과 조치 - "
        "제13차 증권선물위원회(\u201926.7.8.) 조치 의결"
    )
    assert title == "사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회(’26.7.8.) 조치 의결"
    assert meeting_key(title) == (2026, "증선위", "정기", 13)
    assert meeting_key("제13차 증권선물위원회('26.7.8.) 조치 의결") == (
        2026,
        "증선위",
        "정기",
        13,
    )


def test_meeting_key_accepts_left_single_quote_before_year():
    title = (
        "사업보고서 등에 대한 조사·감리결과 조치 - "
        "제16차 증권선물위원회(\u201826.9.16.) 조치 의결"
    )
    assert "\u201826" in title
    assert meeting_key(title) == (2026, "증선위", "정기", 16)


def test_query_minutes_url_uses_meeting_filename():
    posts = [
        DecisionPost(
            2026,
            "증선위",
            "정기",
            13,
            "https://fsc.go.kr/comm/getFile?fileNo=9",
            [ZIP_URL],
        )
    ]
    updated, report = attach_minutes(PRESS, posts)
    assert "downloads/minutes-2026-증선위-정기-13.pdf" in updated
    assert "fileNo" not in updated
    assert "getFile" not in updated
    assert ZIP_URL not in updated
    assert ZIP_URL not in " ".join(report)
    assert report == ["attached 2026 증선위 정기 13"]
