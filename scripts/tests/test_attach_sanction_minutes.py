# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attach_sanction_minutes import (
    DecisionPost,
    attach_minutes,
    decision_key,
    is_additional_minutes,
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
    assert decision_key("2026년도 제13차 금융위원회 의사록, 안건 및 제재안건 의결서") == (
        2026,
        "금융위",
        "정기",
        13,
    )
    assert decision_key("회의 안내") is None


def test_filled_discussion_does_not_receive_a_minutes_marker():
    filled = PRESS.replace("미공개임", "회사 조치는 원안임")
    updated, report = attach_minutes(filled, [POSTS[0]])
    assert updated == filled
    assert report == ["skipped discussion 2026 증선위 정기 13"]


PRESS_WITH_APPENDIX = """### 금융위원회

#### 제재 의결

- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회(’26.7.8.)](https://fsc.go.kr/no010101/87293)

    !!! note "위원 논의"

        - 미공개임

## Appendix

- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회(’26.7.8.)](https://fsc.go.kr/no010101/99999)

    !!! note "위원 논의"

        - 미공개임
"""


def test_appendix_links_outside_resolution_do_not_receive_minutes():
    posts = [POSTS[0]]
    updated, report = attach_minutes(PRESS_WITH_APPENDIX, posts)
    assert MINUTES_PDF in updated
    assert "no010101/99999" in updated
    assert updated.count("source: pdf|downloads/") == 1
    assert updated.index(MINUTES_PDF) < updated.index("99999")
    assert report == ["attached 2026 증선위 정기 13"]


def test_meeting_key_ignores_temporary_wording_in_note_body():
    title = "사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회(’26.7.8.)"
    block = '\n\n    !!! note "위원 논의"\n\n        - 임시주주총회 일정 관련\n\n        - 미공개임'
    assert meeting_key(title + "\n" + block) == (2026, "증선위", "정기", 13)

    press = PRESS.replace("미공개임", "임시주주총회 일정 관련\n\n        - 미공개임")
    updated_regular, report_regular = attach_minutes(press, [POSTS[0]])
    assert MINUTES_PDF in updated_regular
    assert report_regular == ["attached 2026 증선위 정기 13"]

    wrong_kind = [
        DecisionPost(2026, "증선위", "임시", 13, "https://fsc.go.kr/files/minutes-13.pdf", []),
    ]
    updated_wrong, report_wrong = attach_minutes(press, wrong_kind)
    assert MINUTES_PDF not in updated_wrong
    assert updated_wrong == press
    assert report_wrong == ["unpublished 2026 증선위 정기 13"]


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
        dest.parent.mkdir(parents=True, exist_ok=True)
        if "fileNo=2" in url:
            dest.write_bytes(
                _zip_bytes(
                    [
                        "(공개용) 의결 251. 선진회계법인의 중요한 감사절차 위반혐의에 대한 감리결과 조치안.pdf",
                        "(공개용) 의결 235. 교보증권㈜에 대한 정기검사 결과 조치안.pdf",
                    ]
                )
            )
            return
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
    assert "의결 251. 선진회계법인" in updated
    assert "정기검사" not in updated
    assert (tmp_path / "minutes-2026-증선위-정기-15.pdf").read_bytes() == b"pdf"
    agenda = list((tmp_path / "sanctions").rglob("*의결 251*"))
    assert len(agenda) == 1
    assert not list(tmp_path.rglob("*.zip"))
    assert not any("88015" in url for url in requested)
    assert any("srchBeginDt=2026-07-01" in url and "srchEndDt=2026-12-09" in url for url in requested)


DETAIL_EXTRA = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87747&fileTy=ATTACH&fileNo=1">2026년 제15차 증권선물위원회 의사록(추가_의결안건 117호_공개용)_F.pdf</a>
"""


def test_additional_minutes_post_merges_into_the_same_meeting(tmp_path):
    extra = LIST_HTML.replace(
        "</ul>",
        '<li><div class="inner"><div class="subject"><a href="/no020102/87747">2026년 제15차 증권선물위원회 의사록(추가)</a></div><div class="day">2026-09-18</div></div></li></ul>',
    )

    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020102" in url:
            return extra
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/88040"):
            return DETAIL_MINUTES
        if url.endswith("/87747"):
            return DETAIL_EXTRA
        if url.endswith("/87906"):
            return DETAIL_SPECIAL
        return "<ul></ul>"

    def download(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if url.lower().endswith(".zip") or "fileNo=2" in url and ".pdf" not in url:
            dest.write_bytes(_zip_bytes(["(공개용) 의결 235. 교보증권 정기검사.pdf"]))
            return
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
    assert "minutes-2026-증선위-정기-15-추가.pdf" in updated
    assert is_additional_minutes("2026년 제15차 증권선물위원회 의사록(추가)")
    assert not any(line.startswith("ambiguous 2026 증선위 정기 15") for line in report)
    assert any(line.startswith("attached 2026 증선위 정기 15") for line in report)


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

    repo_downloads = Path(__file__).resolve().parent.parent.parent / "downloads"
    stand_in_names = (
        "minutes-2026-증선위-정기-15.pdf",
        "minutes-2026-증선위-임시-1.pdf",
    )

    fake_script = tmp_path / "scripts" / "attach_sanction_minutes.py"
    fake_script.parent.mkdir(parents=True, exist_ok=True)
    fake_script.write_text("# stub for __file__ redirect\n", encoding="utf-8")
    monkeypatch.setattr(asm, "__file__", str(fake_script))

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
    assert b"<!-- source: pdf|downloads/minutes-2026-" in data
    assert b"\r\n" not in data

    tmp_downloads = tmp_path / "downloads"
    for name in stand_in_names:
        assert (tmp_downloads / name).read_bytes() == b"pdf"
        assert not (repo_downloads / name).exists()


LIST_NO_MINUTES_TITLE = """
<ul>
  <li><div class="inner"><div class="subject"><a href="/no020102/87581">2026년 제12차 증권선물위원회 안건 및 제재안건 의결서</a></div><div class="day">2026-08-21</div></div></li>
</ul>
"""

DETAIL_87581 = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87581&fileTy=ATTACH&fileNo=1">2026년 제12차 증권선물위원회 의사록(공개용)_수정.pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87581&fileTy=ATTACH&fileNo=1">파일다운로드</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87581&fileTy=ATTACH&fileNo=2">2026년 제12차 증권선물위원회 안건 및 제재안건 의결서.Zip</a>
"""


def test_post_title_without_minutes_word_still_yields_minutes_pdf():
    requested = []

    def fetch_text(url: str) -> str:
        requested.append(url)
        if "curPage=1" in url and "no020102" in url:
            return LIST_NO_MINUTES_TITLE
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/87581"):
            return DETAIL_87581
        raise AssertionError(url)

    posts = collect_posts(fetch_text, date(2026, 4, 1), date(2026, 9, 9))
    assert posts == [
        DecisionPost(
            2026,
            "증선위",
            "정기",
            12,
            "https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87581&fileTy=ATTACH&fileNo=1",
            [
                "https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87581&fileTy=ATTACH&fileNo=2"
            ],
            "2026년 제12차 증권선물위원회 안건 및 제재안건 의결서",
            "https://www.fsc.go.kr/no020102/87581",
        )
    ]
    assert not any(url.endswith("/87581") and "fileNo=2" in url for url in requested)


def _zip_bytes(names: list[str]) -> bytes:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, b"%PDF-1.4\n")
    return buffer.getvalue()


def test_zip_listing_keeps_only_audit_agenda_and_decision_pdfs():
    from attach_sanction_minutes import audit_zip_entries

    names = [
        "(공개용) 의결 251. 선진회계법인의 중요한 감사절차 위반혐의에 대한 감리결과 조치안.pdf",
        "(의결서) 의결 251. 선진회계법인의 중요한 감사절차 위반혐의에 대한 감리결과 조치안.pdf",
        "(의결서) 의결 250. ㈜OO의 사업보고서 및 연결감사보고서 등에 대한 조사 감리 조치안.pdf",
        "(공개용) 의결 249. 2024 회계연도 감사 前 재무제표 제출의무 위반혐의 등에 대한 조사결과 조치안.pdf",
        "의결360 의왕백운프로젝트금융투자㈜의 감사보고서에 대한 위탁감리결과 조치안(공개용).pdf",
        "금융위 의결서(제2026-359호)_OOOO㈜의 사업보고서 및 연결감사보고서 등에 대한 조사·감리결과 조치안(공개용).pdf",
        "(공개용) 의결 188. ㈜아센디오의 사업보고서 및 감사보고서 등에 대한 조사･감리 결과 조치안.pdf",
        "(공개용) 의결 235. 교보증권㈜에 대한 정기검사 결과 조치안.pdf",
        "의결361 품질관리기준 개정안(공개용).pdf",
        "의결368_경남은행에 대한 정기검사 결과 조치안(공개용).pdf",
        "(공개용) 의결 190. 위탁감리결과 조치안.hwp",
        "readme.txt",
    ]
    kept, whale = audit_zip_entries(names)
    kept_names = [item.filename for item in kept]
    assert "(공개용) 의결 251. 선진회계법인의 중요한 감사절차 위반혐의에 대한 감리결과 조치안.pdf" in kept_names
    assert "(의결서) 의결 251. 선진회계법인의 중요한 감사절차 위반혐의에 대한 감리결과 조치안.pdf" in kept_names
    assert any(item.filename.startswith("(의결서) 의결 250") and item.kind == "decision" for item in kept)
    assert any(item.filename.startswith("의결360") and item.kind == "agenda" for item in kept)
    assert any("제2026-359호" in item.filename and item.kind == "decision" for item in kept)
    assert any("아센디오" in item.filename for item in kept)
    assert any("조사결과" in item.filename for item in kept)
    assert not any("정기검사" in name for name in kept_names)
    assert not any("품질관리기준" in name for name in kept_names)
    assert not any(name.endswith(".hwp") for name in kept_names)
    assert whale == ["(공개용) 의결 190. 위탁감리결과 조치안.hwp"]


def test_agenda_number_parses_the_four_filename_forms():
    from attach_sanction_minutes import parse_agenda_number

    assert parse_agenda_number("(공개용) 의결 251. 선진회계법인 감리결과 조치안.pdf") == 251
    assert parse_agenda_number("의결361 품질관리기준 개정안(공개용).pdf") == 361
    assert parse_agenda_number("의결368_경남은행에 대한 정기검사 결과 조치안(공개용).pdf") == 368
    assert parse_agenda_number("금융위 의결서(제2026-359호)_OOOO㈜ 조사·감리결과 조치안.pdf") == 359
    assert parse_agenda_number("제13차 증권선물위원회") is None


PRESS_NAMED = """### 금융위원회

#### 제재 의결

- (26-09-02) [사업보고서 등에 대한 조사·감리결과 조치 - 제15차 증권선물위원회(’26.9.2.)](https://fsc.go.kr/no010101/87639)

    <!-- source: pdf|downloads/press.pdf -->

    | 회사명 | 구분 | 주요 지적사항 | 주요 조치 |
    | --- | --- | --- | --- |
    | ㈜금양 | 유가증권시장 상장 | 허위 매출 | 과징금 |
    | 선진회계법인 | 감사 | 중요한 감사절차 위반 | 과징금 |

    !!! note "위원 논의"

        - 제250호는 회사명을 비공개로 두나 ㈜금양과 대응함
"""


def test_masked_company_names_are_not_linked():
    from attach_sanction_minutes import AgendaFile, link_agendas

    agendas = [
        AgendaFile("(의결서) 의결 250. ㈜OO의 사업보고서 등에 대한 조사 감리 조치안.pdf", "decision", 250, True),
        AgendaFile("(공개용) 의결 251. 선진회계법인의 중요한 감사절차 위반혐의에 대한 감리결과 조치안.pdf", "agenda", 251, False),
        AgendaFile("금융위 의결서(제2026-359호)_OOOO㈜의 조사·감리결과 조치안.pdf", "decision", 359, True),
    ]
    linked, unmatched = link_agendas(PRESS_NAMED, (2026, "증선위", "정기", 15), agendas)
    assert [item.filename for item, row in linked] == [
        "(공개용) 의결 251. 선진회계법인의 중요한 감사절차 위반혐의에 대한 감리결과 조치안.pdf"
    ]
    assert linked[0][1] == "선진회계법인"
    assert len(unmatched) == 2
    assert all(item.number != 251 for item in unmatched)


def test_source_marker_is_not_a_press_agenda_number():
    from attach_sanction_minutes import AgendaFile, link_agendas

    press = PRESS_NAMED.replace(
        "<!-- source: pdf|downloads/press.pdf -->",
        "<!-- source: pdf|downloads/의결 250. 가림.pdf -->",
    )
    agendas = [
        AgendaFile("(의결서) 의결 250. ㈜OO의 사업보고서 등에 대한 조사 감리 조치안.pdf", "decision", 250, True),
    ]
    linked, unmatched = link_agendas(press, (2026, "증선위", "정기", 15), agendas)
    assert linked == []
    assert [item.number for item in unmatched] == [250]


def test_press_agenda_number_is_the_primary_key():
    from attach_sanction_minutes import AgendaFile, link_agendas

    press = PRESS_NAMED.replace(
        "| ㈜금양 | 유가증권시장 상장 | 허위 매출 | 과징금 |",
        "| ㈜금양 | 유가증권시장 상장 | 허위 매출 | 과징금 의결 250 |",
    )
    agendas = [
        AgendaFile("(의결서) 의결 250. ㈜OO의 사업보고서 등에 대한 조사 감리 조치안.pdf", "decision", 250, True),
        AgendaFile("(공개용) 의결 249. 조사결과 조치안.pdf", "agenda", 249, False),
    ]
    linked, unmatched = link_agendas(press, (2026, "증선위", "정기", 15), agendas)
    assert [row for _, row in linked] == ["의안 250"]
    assert [item.number for item in unmatched] == [249]


def test_unmatched_agendas_are_reported_and_discussion_notes_stay(tmp_path):
    from attach_sanction_minutes import AgendaFile, attach_agenda_markers

    agendas = [
        AgendaFile("(공개용) 의결 251. 선진회계법인 감리결과 조치안.pdf", "agenda", 251, False),
        AgendaFile("(의결서) 의결 250. ㈜OO 조사 감리 조치안.pdf", "decision", 250, True),
    ]
    text, report = attach_agenda_markers(
        PRESS_NAMED,
        (2026, "증선위", "정기", 15),
        [
            (agendas[0], "선진회계법인", "downloads/sanctions/2026-증선위-정기-15차/agenda/251.pdf"),
            (agendas[1], "unmatched", "downloads/sanctions/2026-증선위-정기-15차/decision/250.pdf"),
        ],
    )
    assert "251.pdf" in text
    assert "250.pdf" in text
    assert "과징금" in text
    assert "제250호는 회사명을 비공개로 두나 ㈜금양과 대응함" in text
    assert "위원 논의" in text
    assert any(line.startswith("unmatched 2026 증선위 정기 15 250") for line in report)
    assert any(line.startswith("linked 2026 증선위 정기 15 251 선진회계법인") for line in report)
    assert "fileNo=2" not in text
    assert tmp_path is not None


def test_cp949_zip_names_round_trip():
    import zipfile

    from attach_sanction_minutes import _zip_name

    original = "(공개용) 의결 251. 감리결과 조치안.pdf"
    info = zipfile.ZipInfo(original.encode("cp949").decode("cp437"))
    info.flag_bits = 0
    assert _zip_name(info) == original


def test_raw_bundle_does_not_overwrite_an_existing_snapshot(tmp_path):
    from attach_sanction_minutes import place_sanction_bundle

    key = (2026, "증선위", "정기", 15)
    first = place_sanction_bundle(
        tmp_path,
        key,
        "회차 기록\n",
        [("agenda", "251.pdf", b"one")],
        "https://www.fsc.go.kr/no020102/88040",
        "https://www.fsc.go.kr/comm/getFile?fileNo=2",
    )
    assert first == [tmp_path / "2026-증선위-정기-15차"]
    second = place_sanction_bundle(
        tmp_path,
        key,
        "다른 기록\n",
        [("agenda", "251.pdf", b"two"), ("decision", "251-decision.pdf", b"new")],
        "https://www.fsc.go.kr/no020102/88040",
        "https://www.fsc.go.kr/comm/getFile?fileNo=2",
    )
    folder = tmp_path / "2026-증선위-정기-15차"
    assert (folder / "record.md").read_text(encoding="utf-8") == "회차 기록\n"
    assert (folder / "agenda" / "251.pdf").read_bytes() == b"one"
    assert (folder / "decision" / "251-decision.pdf").read_bytes() == b"new"
    assert second == [folder]
    assert not list(tmp_path.rglob("*.zip"))
