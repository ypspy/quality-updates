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
MINUTES_PDF = "downloads/sanctions/2026-증선위-13차/minutes.pdf"
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
    assert "downloads/sanctions/2026-증선위-13차/minutes.pdf" in updated
    assert "downloads/minutes.pdf" not in updated
    assert "downloads/minutes-" not in updated
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
    assert rows[0][1] == "https://fsc.go.kr/no020102/88040"
    assert minutes_pdf_urls(DETAIL_MINUTES) == [
        "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=1"
    ]
    assert minutes_pdf_urls(DETAIL_RESULT) == []
    assert minutes_pdf_urls(DETAIL_SPECIAL) == [
        "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87906&fileTy=ATTACH&fileNo=1"
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
    assert "downloads/sanctions/2026-증선위-15차/minutes.pdf" in updated
    assert "downloads/sanctions/2026-증선위-임시-1차/minutes.pdf" in updated
    assert "downloads/minutes.pdf" not in updated
    assert "downloads/minutes-" not in updated
    assert "fileNo=2" not in updated
    assert "의결 251. 선진회계법인" not in updated
    assert "정기검사" not in updated
    assert not list(tmp_path.glob("minutes*.pdf"))
    agenda = list((tmp_path / "sanctions").rglob("*의결 251*"))
    assert len(agenda) == 1
    bundle = tmp_path / "sanctions" / "2026-증선위-15차"
    assert (bundle / "minutes.pdf").read_bytes() == b"pdf"
    record = (bundle / "record.md").read_text(encoding="utf-8")
    assert "- 회의일: 2026-09-02" in record
    assert "- 게시 URL: https://fsc.go.kr/no020102/88040" in record
    assert "fileNo=2" in record
    assert "사업보고서 등에 대한 조사·감리결과 조치 - 제15차 증권선물위원회" in record
    assert "https://fsc.go.kr/no010101/87639" in record
    assert "- 의사록: minutes.pdf" in record
    assert "| 번호 | 구분 | 제목 | 마스킹 | 연결 | 연결근거 |" in record
    temporary = tmp_path / "sanctions" / "2026-증선위-임시-1차"
    assert (temporary / "minutes.pdf").read_bytes() == b"pdf"
    assert "- 회의일: 2026-10-09" in (temporary / "record.md").read_text(encoding="utf-8")
    assert not list(tmp_path.rglob("*.zip"))
    assert not any("88015" in url for url in requested)
    assert any("srchBeginDt=2026-07-01" in url and "srchEndDt=2026-12-09" in url for url in requested)


DETAIL_EXTRA = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87747&fileTy=ATTACH&fileNo=1">2026년 제15차 증권선물위원회 의사록(추가_의결안건 117호_공개용)_F.pdf</a>
"""


def test_additional_minutes_post_merges_into_the_same_meeting(tmp_path):
    extra_item = (
        '<li><div class="inner"><div class="subject">'
        '<a href="/no020102/87747">2026년 제15차 증권선물위원회 의사록(추가)</a>'
        '</div><div class="day">2026-09-18</div></div></li>\n  '
    )
    extra = LIST_HTML.replace("<ul>\n  <li>", "<ul>\n  " + extra_item + "<li>", 1)

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
        if url.lower().endswith(".zip") or ("fileNo=2" in url and ".pdf" not in url):
            dest.write_bytes(_zip_bytes(["(공개용) 의결 235. 교보증권 정기검사.pdf"]))
            return
        if "upperNo=87747" in url:
            dest.write_bytes(b"extra-minutes")
            return
        dest.write_bytes(b"primary-minutes")

    code, updated, report = run_minutes(
        QUARTER,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download,
        tmp_path,
    )
    assert code == 0
    assert "downloads/sanctions/2026-증선위-15차/minutes.pdf" in updated
    assert "downloads/sanctions/2026-증선위-15차/minutes-추가.pdf" in updated
    assert "downloads/minutes-" not in updated
    assert is_additional_minutes("2026년 제15차 증권선물위원회 의사록(추가)")
    assert not any(line.startswith("ambiguous 2026 증선위 정기 15") for line in report)
    assert any(line.startswith("attached 2026 증선위 정기 15") for line in report)
    folder = tmp_path / "sanctions" / "2026-증선위-15차"
    assert (folder / "minutes.pdf").read_bytes() == b"primary-minutes"
    assert (folder / "minutes-추가.pdf").read_bytes() == b"extra-minutes"
    record = (folder / "record.md").read_text(encoding="utf-8")
    assert "- 게시 URL: https://fsc.go.kr/no020102/88040" in record
    assert "- 게시 URL: https://fsc.go.kr/no020102/87747\n" not in record
    assert "- 추가 게시 URL: https://fsc.go.kr/no020102/87747" in record
    zip_line = next(line for line in record.splitlines() if line.startswith("- ZIP URL:"))
    assert "upperNo=88040" in zip_line
    assert "87747" not in zip_line


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
        Path("sanctions") / "2026-증선위-15차" / "minutes.pdf",
        Path("sanctions") / "2026-증선위-임시-1차" / "minutes.pdf",
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
    assert b"<!-- source: pdf|downloads/sanctions/2026-" in data
    assert b"/minutes.pdf -->" in data
    assert b"downloads/minutes-" not in data
    assert b"downloads/minutes.pdf" not in data
    assert b"\r\n" not in data

    tmp_downloads = tmp_path / "downloads"
    for name in stand_in_names:
        assert (tmp_downloads / name).read_bytes() == b"pdf"
        repo_file = repo_downloads / name
        assert not repo_file.exists() or repo_file.read_bytes() != b"pdf"


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
            "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87581&fileTy=ATTACH&fileNo=1",
            [
                "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87581&fileTy=ATTACH&fileNo=2"
            ],
            "2026년 제12차 증권선물위원회 안건 및 제재안건 의결서",
            "https://fsc.go.kr/no020102/87581",
        )
    ]
    assert not any(url.endswith("/87581") and "fileNo=2" in url for url in requested)


def _zip_bytes(names: list[str]) -> bytes:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, b"%PDF-1.4\n" + name.encode("utf-8"))
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
        "금융위 의결서(제2026-336호)_ ○○○ 가상자산에 대한 불공정거래 조사결과 과징금부과 조치안(공개용).pdf",
        "(공개용) 의결 336. 가상자산 불공정거래 조사결과.hwp",
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
    assert not any("불공정거래" in name for name in kept_names)
    assert not any(name.endswith(".hwp") for name in kept_names)
    assert whale == ["(공개용) 의결 190. 위탁감리결과 조치안.hwp"]


def test_unfair_trading_and_rule_amendments_are_not_audit_files():
    from attach_sanction_minutes import audit_zip_entries

    names = [
        "금융위 의결서(제2026-336호)_가상자산에 대한 불공정거래 조사결과 과징금부과 조치안(공개용).pdf",
        "(공개용) 의결 401. 시세조종 조사결과 조치안.pdf",
        "(공개용) 의결 402. 미공개정보 이용 조사결과 조치안.pdf",
        "(공개용) 의결 214. 한국공인회계사회 「위탁감리위원회 운영규정」 및 「감리조사업무규정」 일부개정규정안.pdf",
        "(공개용) 의결 403. 시장동향 조사.pdf",
        "(공개용) 의결 249. 재무제표 제출의무 위반혐의 등에 대한 조사결과 조치안.pdf",
        "(공개용) 의결 215. 대주회계법인의 감리결과 조치안.pdf",
    ]
    kept, whale = audit_zip_entries(names)
    kept_names = [item.filename for item in kept]
    assert any("249" in name for name in kept_names)
    assert any("215" in name for name in kept_names)
    assert whale == []
    for token in ("불공정거래", "시세조종", "미공개정보", "214", "시장동향"):
        assert not any(token in name for name in kept_names)


def test_agenda_temp_name_uses_a_stable_sha256_prefix():
    import hashlib

    from attach_sanction_minutes import _agenda_temp_name

    url = "https://www.fsc.go.kr/comm/getFile?fileNo=2"
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    assert _agenda_temp_name(url) == f"_agenda-{digest}.zip"
    assert _agenda_temp_name(url) == _agenda_temp_name(url)


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
    assert linked[0][1] == "실명"
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
    assert [row for _, row in linked] == ["의안번호"]
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
            (agendas[0], "선진회계법인", "downloads/sanctions/2026-증선위-15차/agenda/251.pdf"),
            (agendas[1], "unmatched", "downloads/sanctions/2026-증선위-15차/decision/250.pdf"),
        ],
    )
    assert "251.pdf" in text
    assert "250.pdf" not in text
    assert "과징금" in text
    assert "제250호는 회사명을 비공개로 두나 ㈜금양과 대응함" in text
    assert "위원 논의" in text
    assert any(line.startswith("unmatched 2026 증선위 정기 15 250") for line in report)
    assert any(line.startswith("linked 2026 증선위 정기 15 251 선진회계법인") for line in report)
    assert "fileNo=2" not in text
    assert tmp_path is not None


def test_masked_filename_does_not_link_by_company_name():
    from attach_sanction_minutes import AgendaFile, link_agendas

    agendas = [
        AgendaFile(
            "(공개용) 의결 249. 선진회계법인 ㈜OO 조사결과 조치안.pdf",
            "agenda",
            249,
            False,
        ),
    ]
    linked, unmatched = link_agendas(PRESS_NAMED, (2026, "증선위", "정기", 15), agendas)
    assert linked == []
    assert [item.number for item in unmatched] == [249]


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
    folder = tmp_path / "2026-증선위-15차"
    original = "\n".join(
        [
            "# 2026-증선위-15차",
            "",
            "- 회의일: 없음",
            "- 게시 URL: https://www.fsc.go.kr/no020102/87747",
            "- ZIP URL: 없음",
            "- 보도: 미보도",
            "- 의사록: minutes.pdf, minutes-추가.pdf",
            "",
            "| 번호 | 구분 | 제목 | 마스킹 | 연결 |",
            "| --- | --- | --- | --- | --- |",
            "",
        ]
    )
    first = place_sanction_bundle(
        tmp_path,
        key,
        original,
        [
            ("minutes", "minutes.pdf", b"minutes-one"),
            ("minutes", "minutes-추가.pdf", b"extra-one"),
            ("agenda", "251.pdf", b"one"),
        ],
    )
    assert first == [folder]
    refreshed = "\n".join(
        [
            "# 2026-증선위-15차",
            "",
            "- 회의일: 2026-09-02",
            "- 게시 URL: https://www.fsc.go.kr/no020102/88040",
            "- ZIP URL: https://www.fsc.go.kr/comm/getFile?upperNo=88040",
            "- 보도: 보도 (https://fsc.go.kr/no010101/87639)",
            "- 의사록: minutes.pdf",
            "",
            "| 번호 | 구분 | 제목 | 마스킹 | 연결 | 연결근거 |",
            "| --- | --- | --- | --- | --- | --- |",
            "| 251 | agenda | 251.pdf | 아니오 | https://fsc.go.kr/no010101/87639 | 의안번호 |",
            "",
        ]
    )
    second = place_sanction_bundle(
        tmp_path,
        key,
        refreshed,
        [
            ("minutes", "minutes.pdf", b"minutes-two"),
            ("agenda", "251.pdf", b"two"),
            ("decision", "251-decision.pdf", b"new"),
        ],
    )
    assert second == [folder]
    assert (folder / "minutes.pdf").read_bytes() == b"minutes-one"
    assert (folder / "minutes-추가.pdf").read_bytes() == b"extra-one"
    assert (folder / "agenda" / "251.pdf").read_bytes() == b"one"
    assert (folder / "decision" / "251-decision.pdf").read_bytes() == b"new"
    record = (folder / "record.md").read_text(encoding="utf-8")
    assert record != original
    assert "회차 기록" not in record
    assert "- 회의일: 2026-09-02" in record
    assert "- 게시 URL: https://www.fsc.go.kr/no020102/88040" in record
    assert "- 의사록: minutes.pdf, minutes-추가.pdf" in record
    assert "| 251 | agenda | 251.pdf | 아니오 | https://fsc.go.kr/no010101/87639 | 의안번호 |" in record
    assert not list(tmp_path.rglob("*.zip"))


def test_unpublished_section_stays_outside_the_press_item():
    text = """### 금융위원회

#### 제재 의결

- (26-03-11) [감사보고서 등에 대한 조사·감리결과 조치 - 제5차 증권선물위원회('26.3.11.)](https://fsc.go.kr/no010101/1)

    !!! note "위원 논의"

        - 미공개

##### 미보도

- 제5차 증권선물위원회(2026.3.11.) 의결 66. 예시

    <!-- source: pdf|downloads/sanctions/2026-증선위-5차/decision/staff.pdf -->

#### 고시/공고/훈령
"""
    posts = [DecisionPost(2026, "증선위", "정기", 5, "https://fsc.go.kr/files/minutes-5.pdf", [])]
    updated, _report = attach_minutes(text, posts)
    assert "##### 미보도" in updated
    marker = "downloads/sanctions/2026-증선위-5차/minutes.pdf"
    assert updated.index(marker) < updated.index("##### 미보도")
    assert updated.index("##### 미보도") < updated.index("staff.pdf")
    assert updated.index("staff.pdf") < updated.index("#### 고시/공고/훈령")


def test_unpublished_bullet_stays_outside_the_press_item():
    text = """### 금융위원회

#### 제재 의결

- (26-03-11) [감사보고서 등에 대한 조사·감리결과 조치 - 제5차 증권선물위원회('26.3.11.)](https://fsc.go.kr/no010101/1)

    !!! note "위원 논의"

        - 미공개

- 분기중 미보도 항목

    <!-- source: pdf|downloads/sanctions/2026-증선위-5차/decision/staff.pdf -->

#### 고시/공고/훈령
"""
    posts = [DecisionPost(2026, "증선위", "정기", 5, "https://fsc.go.kr/files/minutes-5.pdf", [])]
    updated, _report = attach_minutes(text, posts)
    assert "##### 미보도" not in updated
    marker = "downloads/sanctions/2026-증선위-5차/minutes.pdf"
    assert updated.index(marker) < updated.index("- 분기중 미보도 항목")
    assert updated.index("- 분기중 미보도 항목") < updated.index("staff.pdf")
    assert updated.index("staff.pdf") < updated.index("#### 고시/공고/훈령")


def test_regular_temporary_and_written_folders_stay_distinct():
    from attach_sanction_minutes import sanction_folder

    regular = sanction_folder((2026, "금융위", "정기", 1))
    temporary = sanction_folder((2026, "금융위", "임시", 1))
    written = sanction_folder((2026, "금융위", "서면", 1))
    assert regular == "2026-금융위-1차"
    assert temporary == "2026-금융위-임시-1차"
    assert written == "2026-금융위-서면-1차"
    assert len({regular, temporary, written}) == 3
    assert sanction_folder((2026, "증선위", "정기", 16)) == "2026-증선위-16차"


def test_existing_folder_marker_does_not_add_an_outside_minutes_path():
    marked = _insert_marker(PRESS, f"<!-- source: pdf|{MINUTES_PDF} -->")
    updated, report = attach_minutes(marked, [POSTS[0]])
    assert updated == marked
    assert "downloads/minutes.pdf" not in updated
    assert "downloads/minutes-" not in updated
    assert report == []


def test_record_says_unpublished_when_the_press_link_is_missing():
    from attach_sanction_minutes import _record_text

    record = _record_text((2026, "증선위", "정기", 16), "", "", "없음", [], [], "미보도")
    assert "- 보도: 미보도" in record
    assert "- 의사록: 없음" in record
    assert "- 추가 게시 URL:" not in record
    assert "| 번호 | 구분 | 제목 | 마스킹 | 연결 | 연결근거 |" in record
    assert "|  |  |  |  |  |  |" in record
    assert "# 2026-증선위-16차" in record


LATE_QUARTER = """### 금융위원회

#### 제재 의결

- (26-09-02) [사업보고서 등에 대한 조사·감리결과 조치 - 제15차 증권선물위원회(’26.9.2.) 조치 의결](https://fsc.go.kr/no010101/87639)

    요약은 그대로 둔다.

    | 회사명 | 구분 |
    | --- | --- |
    | 선진회계법인 | 감사 |

##### 미보도

- 분기중 미보도 항목
"""

LATE_LIST = """
<ul>
  <li><div class="inner"><div class="subject"><a href="/no020102/88040">2026년 제15차 증권선물위원회 의사록, 안건 및 제재안건 의결서</a></div></div></li>
</ul>
"""

LATE_LIST_EXTRA = """
<ul>
  <li><div class="inner"><div class="subject"><a href="/no020102/88040">2026년 제15차 증권선물위원회 의사록, 안건 및 제재안건 의결서</a></div></div></li>
  <li><div class="inner"><div class="subject"><a href="/no020102/89001">2026년 제15차 증권선물위원회 의사록(추가)</a></div></div></li>
  <li><div class="inner"><div class="subject"><a href="/no020102/89002">2026년 제4차 증권선물위원회 의사록</a></div></div></li>
</ul>
"""

LATE_DETAIL = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=1">2026년 제15차 증권선물위원회 의사록 (공개용)_F.pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=2">안건.zip</a>
"""

LATE_EXTRA_DETAIL = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=89001&fileTy=ATTACH&fileNo=8">의사록(추가).pdf</a>
"""

LATE_OTHER_DETAIL = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=89002&fileTy=ATTACH&fileNo=3">제4차 의사록.pdf</a>
"""


def _search_end(url: str) -> date:
    return date.fromisoformat(url.split("srchEndDt=")[1].split("&", 1)[0])


def _late_fetch(url: str) -> str:
    if "curPage=1" in url and "no020102" in url:
        if _search_end(url) >= date(2026, 12, 20):
            return LATE_LIST_EXTRA
        return LATE_LIST
    if "curPage=" in url:
        return "<ul></ul>"
    if url.endswith("/88040"):
        return LATE_DETAIL
    if url.endswith("/89001"):
        return LATE_EXTRA_DETAIL
    if url.endswith("/89002"):
        return LATE_OTHER_DETAIL
    raise AssertionError(url)


def _late_download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if "fileNo=2" in url:
        dest.write_bytes(
            _zip_bytes(
                [
                    "(공개용) 의결 251. 선진회계법인의 중요한 감사절차 위반혐의에 대한 감리결과 조치안.pdf",
                    "(의결서) 의결 251. 선진회계법인의 중요한 감사절차 위반혐의에 대한 감리결과 조치안.pdf",
                ]
            )
        )
        return
    if "fileNo=8" in url:
        dest.write_bytes(b"extra-minutes")
        return
    if "fileNo=3" in url:
        dest.write_bytes(b"other-meeting")
        return
    dest.write_bytes(b"primary-minutes")


def test_late_additional_minutes_stay_out_until_the_window_grows(tmp_path):
    code, updated, _report = run_minutes(
        LATE_QUARTER,
        "2026-07-01_to_2026-09-30.md",
        _late_fetch,
        _late_download,
        tmp_path,
    )
    folder = tmp_path / "sanctions" / "2026-증선위-15차"
    assert code == 0
    assert not (folder / "minutes-추가.pdf").exists()
    assert "minutes-추가.pdf" not in updated
    assert not (tmp_path / "sanctions" / "2026-증선위-4차").exists()

    code, updated, _report = run_minutes(
        updated,
        "2026-07-01_to_2026-09-30.md",
        _late_fetch,
        _late_download,
        tmp_path,
        until=date(2026, 12, 31),
    )
    assert code == 0
    assert (folder / "minutes-추가.pdf").read_bytes() == b"extra-minutes"
    assert updated.count("downloads/sanctions/2026-증선위-15차/minutes-추가.pdf") == 1
    assert not (tmp_path / "sanctions" / "2026-증선위-4차").exists()


def test_extra_days_collects_the_same_meeting_key(tmp_path):
    code, updated, _report = run_minutes(
        LATE_QUARTER,
        "2026-07-01_to_2026-09-30.md",
        _late_fetch,
        _late_download,
        tmp_path,
        extra_days=20,
    )
    assert code == 0
    assert "downloads/sanctions/2026-증선위-15차/minutes-추가.pdf" in updated
    assert not (tmp_path / "sanctions" / "2026-증선위-4차").exists()


def test_existing_bundle_keeps_bytes_when_a_late_supplement_arrives(tmp_path):
    code, seeded, _report = run_minutes(
        LATE_QUARTER,
        "2026-07-01_to_2026-09-30.md",
        _late_fetch,
        _late_download,
        tmp_path,
    )
    assert code == 0
    folder = tmp_path / "sanctions" / "2026-증선위-15차"
    minutes = (folder / "minutes.pdf").read_bytes()
    agenda = {path.name: path.read_bytes() for path in (folder / "agenda").iterdir()}
    decision = {path.name: path.read_bytes() for path in (folder / "decision").iterdir()}
    record_before = (folder / "record.md").read_text(encoding="utf-8")
    assert "- 의사록: minutes.pdf" in record_before
    assert "- 추가 게시 URL:" not in record_before
    assert "| 번호 | 구분 | 제목 | 마스킹 | 연결 | 연결근거 |" in record_before

    code, updated, _report = run_minutes(
        seeded,
        "2026-07-01_to_2026-09-30.md",
        _late_fetch,
        _late_download,
        tmp_path,
        extra_days=30,
        until=date(2026, 12, 15),
    )
    assert code == 0
    assert (folder / "minutes.pdf").read_bytes() == minutes
    assert {path.name: path.read_bytes() for path in (folder / "agenda").iterdir()} == agenda
    assert {path.name: path.read_bytes() for path in (folder / "decision").iterdir()} == decision
    assert (folder / "minutes-추가.pdf").read_bytes() == b"extra-minutes"
    record_after = (folder / "record.md").read_text(encoding="utf-8")

    def stable(text: str) -> list[str]:
        return [
            line
            for line in text.splitlines()
            if not line.startswith("- 의사록:") and not line.startswith("- 추가 게시 URL:")
        ]

    assert stable(record_before) == stable(record_after)
    assert "- 의사록: minutes.pdf, minutes-추가.pdf" in record_after
    assert "- 추가 게시 URL: https://fsc.go.kr/no020102/89001" in record_after
    assert "- 게시 URL: https://fsc.go.kr/no020102/88040" in record_after
    assert "요약은 그대로 둔다." in updated
    assert "| 선진회계법인 | 감사 |" in updated
    assert "- 분기중 미보도 항목" in updated
    assert updated.count("downloads/sanctions/2026-증선위-15차/minutes.pdf") == 1
    assert updated.count("downloads/sanctions/2026-증선위-15차/minutes-추가.pdf") == 1
    assert "downloads/minutes.pdf" not in updated
    assert not (tmp_path / "sanctions" / "2026-증선위-4차").exists()


def test_repeat_run_keeps_markers_and_pdf_bytes(tmp_path):
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
        dest.parent.mkdir(parents=True, exist_ok=True)
        if "fileNo=2" in url:
            dest.write_bytes(_zip_bytes(["(공개용) 의결 251. 선진회계법인 감리결과 조치안.pdf"]))
            return
        dest.write_bytes(b"first-pdf")

    code, updated, _report = run_minutes(
        QUARTER,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download,
        tmp_path,
    )
    assert code == 0
    regular = tmp_path / "sanctions" / "2026-증선위-15차" / "minutes.pdf"
    special = tmp_path / "sanctions" / "2026-증선위-임시-1차" / "minutes.pdf"
    assert regular.read_bytes() == b"first-pdf"
    assert updated.count("downloads/sanctions/2026-증선위-15차/minutes.pdf") == 1
    assert "downloads/minutes.pdf" not in updated

    def download_again(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"second-pdf")

    code, again, _report = run_minutes(
        updated,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download_again,
        tmp_path,
    )
    assert code == 0
    assert again.count("downloads/sanctions/2026-증선위-15차/minutes.pdf") == 1
    assert again.count("downloads/sanctions/2026-증선위-임시-1차/minutes.pdf") == 1
    assert "downloads/minutes.pdf" not in again
    assert "downloads/minutes-" not in again
    assert regular.read_bytes() == b"first-pdf"
    assert special.read_bytes() == b"first-pdf"


def test_failed_supplement_does_not_delete_existing_files(tmp_path):
    folder = tmp_path / "sanctions" / "2026-증선위-15차"
    (folder / "agenda").mkdir(parents=True)
    (folder / "decision").mkdir()
    (folder / "minutes.pdf").write_bytes(b"original-minutes")
    (folder / "agenda" / "251.pdf").write_bytes(b"original-agenda")
    (folder / "decision" / "251.pdf").write_bytes(b"original-decision")
    (folder / "record.md").write_text(
        "\n".join(
            [
                "# 2026-증선위-15차",
                "",
                "- 회의일: 2026-09-02",
                "- 게시 URL: https://www.fsc.go.kr/no020102/88040",
                "- ZIP URL: https://www.fsc.go.kr/comm/getFile?fileNo=2",
                "- 보도: 기존 보도 (https://fsc.go.kr/no010101/87639)",
                "- 의사록: 없음",
                "",
                "| 번호 | 구분 | 제목 | 마스킹 | 연결 |",
                "| --- | --- | --- | --- | --- |",
                "| 251 | agenda | 251.pdf | 아니오 | 선진회계법인 |",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    marked = LATE_QUARTER.replace(
        "요약은 그대로 둔다.",
        "요약은 그대로 둔다.\n\n    <!-- source: pdf|downloads/sanctions/2026-증선위-15차/minutes.pdf -->",
    )

    def download(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if "fileNo=8" in url:
            dest.write_bytes(b"partial-extra")
            raise OSError("disk full")
        dest.write_bytes(b"should-not-land")

    code, updated, _report = run_minutes(
        marked,
        "2026-07-01_to_2026-09-30.md",
        _late_fetch,
        download,
        tmp_path,
        until=date(2026, 12, 31),
    )
    assert code == 1
    assert updated == marked
    assert (folder / "minutes.pdf").read_bytes() == b"original-minutes"
    assert (folder / "agenda" / "251.pdf").read_bytes() == b"original-agenda"
    assert (folder / "decision" / "251.pdf").read_bytes() == b"original-decision"
    assert not (folder / "minutes-추가.pdf").exists()
    assert "- 의사록: 없음" in (folder / "record.md").read_text(encoding="utf-8")
    assert "- 보도: 기존 보도 (https://fsc.go.kr/no010101/87639)" in (folder / "record.md").read_text(encoding="utf-8")


def test_until_before_the_default_end_exits_2(tmp_path):
    def fetch_text(url: str) -> str:
        raise AssertionError(url)

    code, updated, report = run_minutes(
        LATE_QUARTER,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        lambda url, dest: None,
        tmp_path,
        until=date(2026, 12, 1),
    )
    assert code == 2
    assert updated == LATE_QUARTER
    assert report == []


def test_http_helpers_use_a_browser_agent_and_delay(tmp_path, monkeypatch):
    import attach_sanction_minutes as asm

    sleeps: list[float] = []
    seen: list[str] = []
    monkeypatch.setattr(asm.time, "sleep", lambda seconds: sleeps.append(seconds))
    asm._requests_made = 0
    asm._request_delay = 0.3

    class Response:
        text = "ok"
        content = b"%PDF-1.4\nok"

        def raise_for_status(self) -> None:
            return None

    def fake_get(url, timeout=30, headers=None):
        assert "fsc.go.kr" not in url
        seen.append(headers["User-Agent"])
        return Response()

    import requests

    monkeypatch.setattr(requests, "get", fake_get)
    assert asm._http_text("https://example.test/list") == "ok"
    minutes = tmp_path / "minutes.pdf"
    asm._http_download("https://example.test/file", minutes)
    assert minutes.read_bytes().startswith(b"%PDF-")
    assert sleeps == [0.3]
    assert seen[0].startswith("Mozilla/5.0")
    assert "Chrome/" in seen[0]
    assert seen[0] == seen[1]


def test_http_download_rejects_html_saved_as_pdf(tmp_path, monkeypatch):
    import pytest
    import requests

    import attach_sanction_minutes as asm

    monkeypatch.setattr(asm.time, "sleep", lambda seconds: None)
    asm._requests_made = 0
    asm._request_delay = 0
    html = b"<!DOCTYPE html><html>Access denied</html>"
    bodies = [html, b"%PDF-1.4\n%", html, html]

    class Response:
        def __init__(self, content: bytes):
            self.content = content
            self.text = ""
            self.status_code = 200

        def raise_for_status(self) -> None:
            return None

    def fake_get(url, timeout=30, headers=None):
        return Response(bodies.pop(0))

    monkeypatch.setattr(requests, "get", fake_get)
    assert asm._looks_like_pdf(b"%PDF-1.4\n") is True
    assert asm._looks_like_pdf(html) is False

    rejected = tmp_path / "minutes.pdf"
    with pytest.raises(asm.FetchFailed) as caught:
        asm._http_download("https://example.test/denied", rejected)
    assert not rejected.exists()
    assert caught.value.error == "not a PDF"

    saved = tmp_path / "minutes-good.pdf"
    asm._http_download("https://example.test/good", saved)
    assert saved.read_bytes().startswith(b"%PDF-1.4")

    archive = tmp_path / "agenda.zip"
    asm._http_download("https://example.test/zip", archive)
    assert archive.read_bytes() == html

    failures = tmp_path / "_failed-downloads.jsonl"
    recorded = asm._download_or_record(
        asm._http_download,
        tmp_path / "again.pdf",
        board="증선위",
        post_id="15",
        page_url="https://example.test/page",
        url="https://example.test/again",
        filename="minutes.pdf",
        failures=failures,
    )
    assert recorded is False
    assert not (tmp_path / "again.pdf").exists()
    assert "https://example.test/again" in failures.read_text(encoding="utf-8")


def test_main_delay_until_and_extra_days(tmp_path, monkeypatch):
    import attach_sanction_minutes as asm

    requested: list[str] = []

    def fetch_text(url: str) -> str:
        requested.append(url)
        assert "fsc.go.kr" not in url or "srchBeginDt" in url
        if "curPage=" in url:
            return "<ul></ul>"
        raise AssertionError(url)

    fake_script = tmp_path / "scripts" / "attach_sanction_minutes.py"
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text("# stub\n", encoding="utf-8")
    monkeypatch.setattr(asm, "__file__", str(fake_script))
    monkeypatch.setattr(asm, "_http_text", fetch_text)
    monkeypatch.setattr(asm, "_http_download", lambda url, dest: (_ for _ in ()).throw(AssertionError(url)))

    quarter = tmp_path / "2026-07-01_to_2026-09-30.md"
    quarter.write_text("### 금융위원회\n", encoding="utf-8")
    assert asm.main([str(quarter), "--until", "2026-10-01"]) == 2
    assert requested == []

    assert asm.main([str(quarter), "--delay", "0", "--until", "2026-12-20", "--extra-days", "10"]) == 0
    assert asm._request_delay == 0
    assert any(
        "srchBeginDt=2026-07-01" in url and "srchEndDt=2026-12-20" in url for url in requested
    )

    requested.clear()
    assert asm.main([str(quarter)]) == 0
    assert asm._request_delay == 1.0
    assert any(
        "srchBeginDt=2026-07-01" in url and "srchEndDt=2026-12-09" in url for url in requested
    )


SAMJONG = "(공개용) 의결 212. 삼정회계법인의 사업보고서에 대한 조사결과 조치안_마스킹.pdf"
FSC_MASKED = (
    "금융위 의결서(제2026-337호)_OOOO㈜의 사업보고서 및 연결감사보고서 등에 대한 "
    "조사·감리결과 조치안(공개용).pdf"
)


def test_samjong_masking_suffix_does_not_hide_the_real_name():
    from attach_sanction_minutes import is_masked_label

    assert is_masked_label(SAMJONG) is False
    assert is_masked_label(SAMJONG.replace("(공개용) ", "(의결서) ")) is False
    assert is_masked_label("OOOO㈜") is True
    assert is_masked_label("㈜OO") is True
    assert is_masked_label("(주)OO") is True
    assert is_masked_label("OO(주)") is True


def test_parenthesized_agenda_number_links_a_masked_decision():
    from attach_sanction_minutes import AgendaFile, _agenda_record_rows, press_agenda_numbers

    press = """- (26-08-12) [금융회사 제재](https://fsc.go.kr/no010101/85337)

    2026년 제13차 금융위원회 제25조에서 (제337호)를 의결하였다.
    의결 211

    !!! note "위원 논의"

        - (제338호)는 여기 있다.
"""
    assert press_agenda_numbers(press) == {337, 211}
    assert 13 not in press_agenda_numbers(press)
    assert 25 not in press_agenda_numbers(press)
    assert 338 not in press_agenda_numbers(press)
    rows = _agenda_record_rows(
        press,
        [
            AgendaFile(FSC_MASKED, "decision", 337, True),
            AgendaFile(SAMJONG, "agenda", 212, False),
            AgendaFile("(의결서) 의결 249. 조사결과 조치안.pdf", "decision", 249, False),
        ],
    )
    url = "https://fsc.go.kr/no010101/85337"
    assert [(item.number, link, basis) for item, link, basis in rows] == [
        (337, url, "의안번호"),
        (212, "unmatched", ""),
        (249, "unmatched", ""),
    ]


def test_agenda_number_basis_wins_when_one_company_also_matches():
    from attach_sanction_minutes import AgendaFile, _agenda_record_rows

    press = PRESS_NAMED.replace(
        "| 선진회계법인 | 감사 | 중요한 감사절차 위반 | 과징금 |",
        "| 선진회계법인 | 감사 | 중요한 감사절차 위반 의결 251 | 과징금 |",
    )
    filename = "(공개용) 의결 251. 선진회계법인의 중요한 감사절차 위반혐의에 대한 감리결과 조치안.pdf"
    rows = _agenda_record_rows(press, [AgendaFile(filename, "agenda", 251, False)])
    assert rows[0][1] == "https://fsc.go.kr/no010101/87639"
    assert rows[0][2] == "의안번호"
    name_only = _agenda_record_rows(PRESS_NAMED, [AgendaFile(filename, "agenda", 251, False)])
    assert name_only[0][1] == "https://fsc.go.kr/no010101/87639"
    assert name_only[0][2] == "실명"


def test_primary_page_and_zip_win_when_the_additional_post_is_first():
    from attach_sanction_minutes import meeting_source_urls

    additional = DecisionPost(
        2026,
        "증선위",
        "정기",
        13,
        "https://www.fsc.go.kr/comm/getFile?upperNo=87747&fileNo=1",
        ["https://www.fsc.go.kr/comm/getFile?upperNo=87747&fileNo=9"],
        "2026년 제13차 증권선물위원회 의사록(추가)",
        "https://www.fsc.go.kr/no020102/87747",
    )
    primary = DecisionPost(
        2026,
        "증선위",
        "정기",
        13,
        "https://www.fsc.go.kr/comm/getFile?upperNo=87654&fileNo=1",
        ["https://www.fsc.go.kr/comm/getFile?upperNo=87654&fileNo=2"],
        "2026년 제13차 증권선물위원회 의사록",
        "https://www.fsc.go.kr/no020102/87654",
    )
    page, extras, zips = meeting_source_urls([additional, primary])
    assert page == "https://www.fsc.go.kr/no020102/87654"
    assert extras == ["https://www.fsc.go.kr/no020102/87747"]
    assert zips[0] == "https://www.fsc.go.kr/comm/getFile?upperNo=87654&fileNo=2"
    assert "87747" in zips[1]

    quiet = DecisionPost(
        2026,
        "증선위",
        "정기",
        13,
        additional.pdf_url,
        [],
        additional.title,
        additional.page_url,
    )
    page, extras, zips = meeting_source_urls([quiet, primary])
    assert page == "https://www.fsc.go.kr/no020102/87654"
    assert extras == ["https://www.fsc.go.kr/no020102/87747"]
    assert zips == ["https://www.fsc.go.kr/comm/getFile?upperNo=87654&fileNo=2"]
    second = DecisionPost(
        2026,
        "증선위",
        "정기",
        13,
        "https://www.fsc.go.kr/comm/getFile?upperNo=87748&fileNo=1",
        [],
        "2026년 제13차 증권선물위원회 의사록(추가_2)",
        "https://www.fsc.go.kr/no020102/87748",
    )
    _page, extras, _zips = meeting_source_urls([second, quiet, primary])
    assert extras == [
        "https://www.fsc.go.kr/no020102/87748",
        "https://www.fsc.go.kr/no020102/87747",
    ]


def test_meeting_date_ignores_a_publication_note_and_reads_the_minutes_front():
    from attach_sanction_minutes import meeting_date, meeting_date_from_minutes_text

    assert meeting_date("(2026.9.18. 공개)") == "없음"
    assert meeting_date("사업보고서 등에 대한 조사·감리결과 조치") == "없음"
    assert meeting_date("제14차 증권선물위원회('26.7.22.)") == "2026-07-22"
    dotted = """제14차 증권선물위원회 의사록
2026. 7. 22.
(2026.9.18. 공개)
안건 2026. 8. 1.
"""
    assert meeting_date_from_minutes_text(dotted) == "2026-07-22"
    spoken = """제14차 증권선물위원회 의사록
(2026.9.18. 공개)
1. 일시: 2026년 7월 22일 (수)
이후 2026년 8월 1일 제출
"""
    assert meeting_date_from_minutes_text(spoken) == "2026-07-22"
    buried = """제14차 증권선물위원회 의사록
회의를 개의한다.
안건 2026. 8. 1.
2026년 8월 1일 제출
"""
    assert meeting_date_from_minutes_text(buried) == "없음"


def _minutes_pdf(pages: list[list[str]]) -> bytes:
    import io

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type0"),
                NameObject("/BaseFont"): NameObject("/Identity"),
                NameObject("/Encoding"): NameObject("/Identity-H"),
            }
        )
    )

    def literal(text: str) -> bytes:
        raw = b"\xfe\xff" + text.encode("utf-16-be")
        return b"<" + raw.hex().encode("ascii") + b">"

    for lines in pages:
        writer.add_blank_page(width=612, height=792)
        commands = [b"BT /F1 12 Tf"]
        y = 740
        for line in lines:
            commands.append(f"1 0 0 1 72 {y} Tm ".encode("ascii") + literal(line) + b" Tj")
            y -= 18
        commands.append(b"ET")
        stream = DecodedStreamObject()
        stream.set_data(b"\n".join(commands))
        page = writer.pages[-1]
        page[NameObject("/Contents")] = writer._add_object(stream)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_minutes_pdf_text_uses_the_first_page_only(tmp_path):
    from attach_sanction_minutes import meeting_date_from_minutes_text, read_minutes_pdf_text

    path = tmp_path / "minutes.pdf"
    path.write_bytes(
        _minutes_pdf(
            [
                [
                    "제14차 증권선물위원회 의사록",
                    "(2026.9.18. 공개)",
                    "일시: 2026년 7월 22일 (수)",
                ],
                [
                    "제14차 증권선물위원회 의사록",
                    "2026. 8. 1.",
                    "일시: 2026년 8월 1일 (토)",
                ],
            ]
        )
    )
    text = read_minutes_pdf_text(path)
    assert "2026. 8. 1." not in text
    assert "8월 1일" not in text
    assert meeting_date_from_minutes_text(text) == "2026-07-22"


def test_dateless_press_takes_the_meeting_day_from_minutes_pdf(tmp_path):
    from attach_sanction_minutes import DecisionPost, resolve_meeting_day

    press = """### 금융위원회

#### 제재 의결

- (26-07-24) [사업보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/87014)

    2026년 제14차 증권선물위원회 조사·감리결과이다.
    (2026.9.18. 공개)

    !!! note "위원 논의"

        - 미공개임
"""
    listing = """
<ul>
  <li><div class="inner"><div class="subject"><a href="/no020102/87014">2026년 제14차 증권선물위원회 의사록 (2026.9.18. 공개)</a></div></div></li>
</ul>
"""
    detail = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87014&fileTy=ATTACH&fileNo=1">제14차 의사록.pdf</a>
"""
    pdf = _minutes_pdf(
        [
            [
                "제14차 증권선물위원회 의사록",
                "2026. 7. 22.",
                "(2026.9.18. 공개)",
                "일시: 2026년 7월 22일 (수)",
            ],
            ["안건", "2026. 8. 1.", "일시: 2026년 8월 1일 (토)"],
        ]
    )

    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020102" in url:
            return listing
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/87014"):
            return detail
        raise AssertionError(url)

    def download(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(pdf)

    code, _updated, _report = run_minutes(
        press,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download,
        tmp_path,
    )
    assert code == 0
    record = (tmp_path / "sanctions" / "2026-증선위-14차" / "record.md").read_text(encoding="utf-8")
    assert "- 회의일: 2026-07-22" in record
    assert "2026-09-18" not in record
    assert "2026-08-01" not in record

    titled = [
        DecisionPost(
            2026,
            "증선위",
            "정기",
            14,
            "https://example.test/minutes.pdf",
            [],
            "2026년 제14차 증권선물위원회 의사록('26.7.22.)",
            "https://www.fsc.go.kr/no020102/87014",
        )
    ]
    other = tmp_path / "other.pdf"
    other.write_bytes(
        _minutes_pdf([["제14차 증권선물위원회 의사록", "2026. 8. 1."]])
    )
    block = press.split("#### 제재 의결", 1)[1]
    assert resolve_meeting_day(block, titled, other) == "2026-07-22"


def test_rewrite_rolls_back_to_the_original_record_bytes(tmp_path):
    from attach_sanction_minutes import _rollback, place_sanction_bundle

    key = (2026, "증선위", "정기", 15)
    root = tmp_path / "sanctions"
    folder = root / "2026-증선위-15차"
    folder.mkdir(parents=True)
    (folder / "agenda").mkdir()
    original = "원본 기록\n- 의사록: minutes.pdf, minutes-추가.pdf\n".encode()
    (folder / "record.md").write_bytes(original)
    (folder / "minutes.pdf").write_bytes(b"keep-minutes")
    (folder / "agenda" / "251.pdf").write_bytes(b"keep-agenda")
    written: list[Path] = []
    restores: list[tuple[Path, bytes]] = []
    place_sanction_bundle(
        root,
        key,
        "\n".join(
            [
                "# 2026-증선위-15차",
                "- 회의일: 2026-09-02",
                "- 게시 URL: https://www.fsc.go.kr/no020102/88040",
                "- 의사록: minutes.pdf",
                "",
            ]
        ),
        [
            ("minutes", "minutes.pdf", b"replace-me"),
            ("decision", "252.pdf", b"new-decision"),
        ],
        written,
        restores,
    )
    assert (folder / "record.md").read_text(encoding="utf-8").startswith("# 2026-증선위-15차")
    assert "minutes-추가.pdf" in (folder / "record.md").read_text(encoding="utf-8")
    assert (folder / "minutes.pdf").read_bytes() == b"keep-minutes"
    assert (folder / "decision" / "252.pdf").read_bytes() == b"new-decision"
    _rollback(tmp_path, written, restores)
    assert (folder / "record.md").read_bytes() == original
    assert (folder / "minutes.pdf").read_bytes() == b"keep-minutes"
    assert (folder / "agenda" / "251.pdf").read_bytes() == b"keep-agenda"
    assert not (folder / "decision" / "252.pdf").exists()


FSC_QUARTER = """### 금융위원회

#### 제재 의결

- (26-08-12) [금융회사 제재](https://fsc.go.kr/no010101/85337)

    2026년 제13차 금융위원회 제25조에서 (제337호)를 의결하였다.

    !!! note "위원 논의"

        - 미공개임
"""

FSC_LIST = """
<ul>
  <li><div class="inner"><div class="subject"><a href="/no020101/86001">2026년 제13차 금융위원회 의사록 및 의결서</a></div></div></li>
</ul>
"""

FSC_DETAIL = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=86001&fileTy=ATTACH&fileNo=1">의사록.pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=86001&fileTy=ATTACH&fileNo=2">안건.zip</a>
"""


def test_masked_fsc_decision_links_to_the_press_url(tmp_path):
    samjong_decision = SAMJONG.replace("(공개용) ", "(의결서) ")

    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020101" in url:
            return FSC_LIST
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/86001"):
            return FSC_DETAIL
        raise AssertionError(url)

    def download(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if "fileNo=2" in url:
            dest.write_bytes(
                _zip_bytes(
                    [
                        FSC_MASKED,
                        samjong_decision,
                        "(의결서) 의결 249. 조사결과 조치안.pdf",
                    ]
                )
            )
            return
        dest.write_bytes(b"pdf")

    code, _updated, _report = run_minutes(
        FSC_QUARTER,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download,
        tmp_path,
    )
    assert code == 0
    record = (tmp_path / "sanctions" / "2026-금융위-13차" / "record.md").read_text(encoding="utf-8")
    assert "| 번호 | 구분 | 제목 | 마스킹 | 연결 | 연결근거 |" in record
    assert f"| 337 | decision | {FSC_MASKED} | 예 | https://fsc.go.kr/no010101/85337 | 의안번호 |" in record
    assert f"| 212 | decision | {samjong_decision} | 아니오 | unmatched |  |" in record
    assert "| 249 | decision | (의결서) 의결 249. 조사결과 조치안.pdf | 아니오 | unmatched |  |" in record
