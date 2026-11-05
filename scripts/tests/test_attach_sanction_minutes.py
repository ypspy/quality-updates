# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attach_sanction_minutes import (
    DecisionPost,
    attach_minutes,
    decision_key,
    meeting_key,
    select_minutes_pdf,
)

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


def test_decision_key_reads_the_live_board_title():
    assert decision_key("2026년 제15차 증권선물위원회 의사록, 안건 및 제재안건 의결서") == (
        2026,
        "증선위",
        "정기",
        15,
    )
    assert decision_key("2026년 제1차 임시증권선물위원회 의사록 및 안건") == (
        2026,
        "증선위",
        "임시",
        1,
    )
    assert decision_key("2026년 제2차 증권선물위원회 임시회의 회의결과") == (
        2026,
        "증선위",
        "임시",
        2,
    )
    assert decision_key("2026년 제14차 금융위원회 의사록") == (2026, "금융위", "정기", 14)
    assert decision_key("회의 안내") is None


def test_filled_discussion_does_not_receive_a_minutes_marker():
    filled = PRESS.replace("미공개임", "회사 조치는 원안임")
    updated, report = attach_minutes(filled, [POSTS[0]])
    assert updated == filled
    assert report == ["skipped discussion 2026 증선위 정기 13"]


from datetime import date
from attach_sanction_minutes import (
    collect_posts,
    minutes_pdf_urls,
    parse_decision_list,
    run_minutes,
)

LIST_HTML = """
<ul>
  <li><div class="inner"><div class="subject"><a href="/no020102/88040">2026년 제15차 증권선물위원회 의사록, 안건 및 제재안건 의결서</a></div><div class="day">2026-10-30</div></div></li>
  <li><div class="inner"><div class="subject"><a href="/no020102/88015">2026년 제19차 증권선물위원회 회의결과</a></div><div class="day">2026-10-29</div></div></li>
  <li><div class="inner"><div class="subject"><a href="/no020102/87906">2026년 제1차 임시증권선물위원회 의사록 및 안건</a></div><div class="day">2026-10-09</div></div></li>
</ul>
"""

DETAIL_MINUTES = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=1">2026년 제15차 증권선물위원회 의사록 (공개용)_F.pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=1">파일다운로드</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=2">2026년 제15차 증권선물위원회 안건 및 제재안건 의결서.zip</a>
"""

DETAIL_RESULT = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=88015&fileTy=ATTACH&fileNo=1">제19차 증권선물위원회 정례회의 결과(홈).pdf</a>
"""

DETAIL_SPECIAL = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87906&fileTy=ATTACH&fileNo=1">2026년 제1차 임시증권선물위원회 의사록 (공개용)_F.pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87906&fileTy=ATTACH&fileNo=2">(공개용) 의결 234.pdf</a>
"""

QUARTER = """### 금융위원회

#### 제재 의결

- (26-09-02) [사업보고서 등에 대한 조사·감리결과 조치 - 제15차 증권선물위원회(’26.9.2.) 조치 의결](https://fsc.go.kr/no010101/87639)

    !!! note "위원 논의"

        - 미공개임

- (26-10-09) [사업보고서 등에 대한 조사·감리결과 조치 - 제1차 임시증권선물위원회(’26.10.9.) 조치 의결](https://fsc.go.kr/no010101/87900)

    !!! note "위원 논의"

        - 미공개임
"""


def test_parser_keeps_minutes_pdfs_and_drops_other_attachments():
    rows = parse_decision_list(LIST_HTML)
    assert rows[0][0].startswith("2026년 제15차")
    assert rows[0][1] == "https://www.fsc.go.kr/no020102/88040"
    assert minutes_pdf_urls(DETAIL_MINUTES) == [
        "https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=1"
    ]
    assert minutes_pdf_urls(DETAIL_RESULT) == []
    assert minutes_pdf_urls(DETAIL_SPECIAL) == [
        "https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87906&fileTy=ATTACH&fileNo=1"
    ]


def test_run_minutes_downloads_only_minutes_pdfs(tmp_path):
    requested = []

    def fetch_text(url: str) -> str:
        requested.append(url)
        if "curPage=1" in url and "no020102" in url:
            return LIST_HTML
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/88040"):
            return DETAIL_MINUTES
        if url.endswith("/87906"):
            return DETAIL_SPECIAL
        if url.endswith("/88015"):
            raise AssertionError("meeting-result page must not be fetched")
        raise AssertionError(url)

    def download(url: str, dest: Path) -> None:
        assert "fileNo=2" not in url
        assert url.endswith("fileNo=1")
        dest.write_bytes(b"pdf")

    code, updated, report = run_minutes(
        QUARTER,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download,
        tmp_path,
    )
    assert code == 0
    assert "minutes-2026-증선위-정기-15.pdf" in updated
    assert "minutes-2026-증선위-임시-1.pdf" in updated
    assert "fileNo=2" not in updated
    assert (tmp_path / "minutes-2026-증선위-정기-15.pdf").read_bytes() == b"pdf"
    assert not any("88015" in url for url in requested)
    assert any("srchBeginDt=2026-07-01" in url and "srchEndDt=2026-12-09" in url for url in requested)


def test_two_minutes_pdfs_for_one_meeting_do_not_attach(tmp_path):
    extra = LIST_HTML.replace(
        "</ul>",
        '<li><div class="inner"><div class="subject"><a href="/no020102/87747">2026년 제15차 증권선물위원회 의사록(추가)</a></div><div class="day">2026-09-18</div></div></li></ul>',
    )

    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020102" in url:
            return extra
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/88040") or url.endswith("/87747"):
            return DETAIL_MINUTES
        if url.endswith("/87906"):
            return DETAIL_SPECIAL
        return "<ul></ul>"

    def download(url: str, dest: Path) -> None:
        if "upperNo=88040" in url or "upperNo=87747" in url:
            raise AssertionError("ambiguous minutes must not be downloaded")
        dest.write_bytes(b"pdf")

    code, updated, report = run_minutes(
        QUARTER,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download,
        tmp_path,
    )
    assert code == 0
    assert "정기-15.pdf" not in updated
    assert any(line.startswith("ambiguous 2026 증선위 정기 15") for line in report)


def test_download_failure_leaves_the_quarter_text_unchanged(tmp_path):
    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020102" in url:
            return LIST_HTML
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/88040"):
            return DETAIL_MINUTES
        if url.endswith("/87906"):
            return DETAIL_SPECIAL
        return "<ul></ul>"

    def download(url: str, dest: Path) -> None:
        dest.write_bytes(b"partial")
        raise OSError("disk full")

    code, updated, report = run_minutes(
        QUARTER,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download,
        tmp_path,
    )
    assert code == 1
    assert updated == QUARTER
    assert list(tmp_path.iterdir()) == []


def test_bad_quarter_filename_exits_2(tmp_path):
    code, updated, report = run_minutes("x", "notes.md", lambda url: "", lambda url, dest: None, tmp_path)
    assert code == 2
    assert updated == "x"


def test_main_writes_quarter_file_with_lf_newlines(tmp_path, monkeypatch):
    import attach_sanction_minutes as asm

    quarter_path = tmp_path / "2026-07-01_to_2026-09-30.md"
    quarter_path.write_bytes(QUARTER.encode("utf-8"))

    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020102" in url:
            return LIST_HTML
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/88040"):
            return DETAIL_MINUTES
        if url.endswith("/87906"):
            return DETAIL_SPECIAL
        raise AssertionError(url)

    def download(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"pdf")

    monkeypatch.setattr(asm, "_http_text", fetch_text)
    monkeypatch.setattr(asm, "_http_download", download)

    assert asm.main([str(quarter_path)]) == 0

    data = quarter_path.read_bytes()
    assert b"\n" in data
    assert b"\r\n" not in data
