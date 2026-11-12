# -*- coding: utf-8 -*-
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler import fss_replies
import crawl_fss_replies
import export_fss_replies_raw

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIST_132 = (FIXTURES / "fss_reply_B0000132_list.html").read_text(encoding="utf-8")
LIST_133 = (FIXTURES / "fss_reply_B0000133_list.html").read_text(encoding="utf-8")
VIEW_132 = (FIXTURES / "fss_reply_B0000132_view.html").read_text(encoding="utf-8")
VIEW_133 = (FIXTURES / "fss_reply_B0000133_view.html").read_text(encoding="utf-8")
HELLO_PDF = (FIXTURES / "fss_reply_hello.pdf").read_bytes()
EMPTY_PDF = (FIXTURES / "fss_reply_empty.pdf").read_bytes()


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("network disabled")

    monkeypatch.setattr(requests.Session, "request", boom)


def _meta(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def _by_ntt(rows):
    return {row.ntt_id: row for row in rows}


def test_parse_b0000132_list_reads_columns_and_ignores_other_boards():
    rows = fss_replies.parse_list_page(LIST_132)
    assert len(rows) == 10
    assert {row.board for row in rows} == {"B0000132"}
    assert "B0000134" not in LIST_132 or all(row.board != "B0000134" for row in rows)
    item = _by_ntt(rows)["189689"]
    assert item.menu_no == "200442"
    assert item.number == "49"
    assert item.title.startswith("2024-FSSQA03")
    assert "회신일 `24.12.27." in item.title
    assert item.department == "회계감독국"
    assert item.published_date == "2025-01-09"
    assert item.standards == ("K-IFRS 제1117호",)
    assert item.attachments[0].name.endswith(".hwp")
    assert item.attachments[0].atch_file_id == "6fffd4a8b6c5494e956ba19c81fdff72"
    assert item.attachments[0].file_sn == "1"
    multi = _by_ntt(rows)["134101"]
    assert multi.standards == ("K-IFRS 제1104호", "K-IFRS 제1117호", "K-IFRS 제1008호")
    assert multi.number == "46"
    assert fss_replies.page_url(item.board, item.ntt_id, item.menu_no) == (
        "https://www.fss.or.kr/fss/bbs/B0000132/view.do?nttId=189689&menuNo=200442"
    )


def test_parse_b0000133_list_has_no_standards_column():
    rows = fss_replies.parse_list_page(LIST_133)
    assert len(rows) == 10
    assert {row.board for row in rows} == {"B0000133"}
    item = _by_ntt(rows)["191435"]
    assert item.menu_no == "200443"
    assert item.number == "1147"
    assert item.department == "회계감독국"
    assert item.published_date == "2025-02-25"
    assert item.standards == ()
    assert item.title.startswith("「기업회계기준 등에 관한 해석 56-90」")
    assert item.attachments[0].name.endswith(".hwpx")
    assert item.attachments[0].atch_file_id == "640142c36c754e648eedf2005330dade"
    assert item.attachments[0].file_sn == "1"
    assert fss_replies.page_url(item.board, item.ntt_id, item.menu_no) == (
        "https://www.fss.or.kr/fss/bbs/B0000133/view.do?nttId=191435&menuNo=200443"
    )


def test_reply_date_uses_title_then_published_date():
    rows = _by_ntt(fss_replies.parse_list_page(LIST_132))
    assert fss_replies.resolve_reply_date(rows["189689"].title, "", rows["189689"].published_date) == "2024-12-27"
    assert fss_replies.resolve_reply_date(rows["189688"].title, "", rows["189688"].published_date) == "2024-06-21"
    assert fss_replies.resolve_reply_date(rows["136884"].title, "", rows["136884"].published_date) == "2024-01-03"
    assert fss_replies.resolve_reply_date(rows["18387"].title, "", rows["18387"].published_date) == "2015-06-22"
    withdrawn = rows["134101"]
    assert "회신일" not in withdrawn.title
    assert fss_replies.resolve_reply_date(withdrawn.title, "", withdrawn.published_date) == "2024-02-26"
    gaap = _by_ntt(fss_replies.parse_list_page(LIST_133))["191435"]
    assert fss_replies.resolve_reply_date(gaap.title, "", gaap.published_date) == "2025-02-25"
    assert fss_replies.resolve_reply_date("제목", "본문 회신일 '23.8.25. 참고", "2024-01-09") == "2023-08-25"


def test_parse_detail_pages_read_notice_and_one_download():
    kifr = fss_replies.parse_detail_page(VIEW_132)
    assert kifr.department == "회계감독국"
    assert kifr.registered_date == "2025-01-09"
    assert kifr.notice.startswith("기업의 회계처리기준 적용 및 결정에 참고할 수 있는")
    assert "문서뷰어" not in kifr.notice
    assert len(kifr.attachments) == 1
    assert kifr.attachments[0].atch_file_id == "6fffd4a8b6c5494e956ba19c81fdff72"
    assert kifr.attachments[0].file_sn == "1"
    assert kifr.attachments[0].name == (
        "2024-FSSQA03 직접참가특성이 없는 금리연동형 보험계약의 공시이율예실차 회계처리(회신일 '24.12.27.).hwp"
    )
    assert "파일크기" not in kifr.attachments[0].name
    gaap = fss_replies.parse_detail_page(VIEW_133)
    assert gaap.department == "회계감독국"
    assert gaap.registered_date == "2025-02-25"
    assert "더이상 유효하지 않은 질의회신" in gaap.notice
    assert "tableSet" not in gaap.notice
    assert len(gaap.attachments) == 1
    assert gaap.attachments[0].name.endswith(".hwpx")
    assert gaap.attachments[0].atch_file_id == "640142c36c754e648eedf2005330dade"


def test_extract_pdf_and_leave_hangul_pending():
    text, status = fss_replies.extract_saved("note.pdf", HELLO_PDF)
    assert status == "ok"
    assert "Hello Reply" in text
    text, status = fss_replies.extract_saved("empty.pdf", EMPTY_PDF)
    assert status == "empty"
    assert fss_replies.extract_saved("note.hwp", b"RAW-HWP")[1] == "pending_whale"
    assert fss_replies.extract_saved("note.hwpx", b"RAW-HWPX")[1] == "pending_whale"


def _list_table(rows_html: str) -> str:
    return f"""
    <table class="tbl col list-data">
      <thead><tr>
        <th>번호</th><th>관련기준서</th><th>제목</th><th>담당부서</th>
        <th>등록일</th><th>첨부파일</th><th>조회수</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    """


def _item_row(ntt_id, board, menu_no, title, attachment_html, number="1", standards="K-IFRS 제1001호"):
    return f"""
    <tr>
      <td class="num">{number}</td>
      <td>{standards}</td>
      <td class="title"><a href="/fss/bbs/{board}/view.do?nttId={ntt_id}&amp;menuNo={menu_no}">{title}</a></td>
      <td>회계감독국</td>
      <td>2025-01-09</td>
      <td>{attachment_html}</td>
      <td>1</td>
    </tr>
    """


def _file_link(name, atch, file_sn, menu_no="200442"):
    return (
        f'<a class="btn-attach-download" href="/fss/cmmn/file/fileDown.do?menuNo={menu_no}'
        f'&amp;atchFileId={atch}&amp;fileSn={file_sn}&amp;bbsId=">'
        f'<span class="name">{name}</span></a>'
    )


def _detail(subject, notice, files_html):
    return f"""
    <div class="krds-bd-view">
      <h3 class="subject">{subject}</h3>
      <dl class="bd-info">
        <div class="info-wrap"><dt>담당부서</dt><dd>회계감독국</dd></div>
        <div class="info-wrap"><dt>등록일</dt><dd>2025-01-09</dd></div>
      </dl>
      <ul class="attach-wrap">{files_html}</ul>
      <div class="dbdata"><p>{notice}</p></div>
    </div>
    """


def _crawl(tmp_path, pages, details, files, **kwargs):
    calls = {"list": [], "detail": [], "file": []}

    def fetch_list(board, menu_no, page):
        calls["list"].append((board, menu_no, page))
        return pages.get((board, page), "<table><tbody></tbody></table>")

    def fetch_detail(board, ntt_id, menu_no):
        calls["detail"].append((board, ntt_id, menu_no))
        return details[(board, ntt_id)]

    def fetch_file(menu_no, atch_file_id, file_sn):
        calls["file"].append((menu_no, atch_file_id, file_sn))
        return files[(atch_file_id, file_sn)]

    result = fss_replies.crawl_archive(
        tmp_path,
        boards=kwargs.get("boards", ["B0000132"]),
        fetch_list=fetch_list,
        fetch_detail=fetch_detail,
        fetch_file=fetch_file,
        delay=kwargs.get("delay", 0),
        limit=kwargs.get("limit"),
        retry_failed=kwargs.get("retry_failed", False),
        sleep=lambda seconds: None,
        now=lambda: datetime.fromisoformat("2026-11-12T09:00:00+09:00"),
    )
    return result, calls


def test_pdf_only_is_ok(tmp_path):
    row = _item_row(
        "11",
        "B0000132",
        "200442",
        "샘플 (회신일 `24.12.27.)",
        _file_link("note.pdf", "PDF1", "1"),
    )
    detail = _detail("샘플 (회신일 `24.12.27.)", "안내 문장", "<li>" + _file_link("note.pdf", "PDF1", "1") + "</li>")
    pages = {("B0000132", 1): _list_table(row)}
    result, calls = _crawl(tmp_path, pages, {("B0000132", "11"): detail}, {("PDF1", "1"): HELLO_PDF})
    assert result["saved"] == 1
    item = (tmp_path / "B0000132" / "11" / "item.md").read_text(encoding="utf-8")
    meta = _meta(item)
    assert meta["extract_status"] == "ok"
    assert meta["reply_date"] == "2024-12-27"
    assert meta["published_date"] == "2025-01-09"
    assert meta["page_url"] == "https://www.fss.or.kr/fss/bbs/B0000132/view.do?nttId=11&menuNo=200442"
    assert meta["attachments"][0]["name"] == "note.pdf"
    assert meta["attachments"][0]["extract_status"] == "ok"
    assert "Hello Reply" in item
    assert "## 상세 안내" in item
    assert "안내 문장" in item
    assert (tmp_path / "B0000132" / "11" / "note.pdf").is_file()
    record = json.loads((tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert record["board"] == "B0000132"
    assert record["ntt_id"] == "11"
    assert record["menu_no"] == "200442"
    assert record["path"] == "B0000132/11/item.md"
    assert record["extract_status"] == "ok"
    assert record["error"] is None
    assert calls["file"] == [("200442", "PDF1", "1")]


def test_pdf_and_hwp_keeps_pdf_only(tmp_path):
    files = _file_link("note.pdf", "PDF1", "1") + _file_link("note.hwp", "HWP1", "2")
    row = _item_row("12", "B0000132", "200442", "같이 있음 (회신일 `24.3.4.)", files)
    detail = _detail("같이 있음 (회신일 `24.3.4.)", "안내", f"<li>{files}</li>")
    result, calls = _crawl(
        tmp_path,
        {("B0000132", 1): _list_table(row)},
        {("B0000132", "12"): detail},
        {("PDF1", "1"): HELLO_PDF, ("HWP1", "2"): b"RAW-HWP"},
    )
    assert result["saved"] == 1
    folder = tmp_path / "B0000132" / "12"
    assert (folder / "note.pdf").is_file()
    assert not (folder / "note.hwp").exists()
    meta = _meta((folder / "item.md").read_text(encoding="utf-8"))
    assert meta["extract_status"] == "ok"
    assert [item["name"] for item in meta["attachments"]] == ["note.pdf"]
    assert calls["file"] == [("200442", "PDF1", "1")]


def test_hwp_only_is_pending_whale_and_keeps_bytes(tmp_path):
    row = _item_row(
        "189689",
        "B0000132",
        "200442",
        "2024-FSSQA03 (회신일 `24.12.27.)",
        _file_link("note.hwp", "HWP1", "1"),
    )
    detail = _detail(
        "2024-FSSQA03 (회신일 `24.12.27.)",
        "첨부파일을 참고하시기 바랍니다.",
        "<li>" + _file_link("note.hwp", "HWP1", "1") + "</li>",
    )
    result, calls = _crawl(
        tmp_path,
        {("B0000132", 1): _list_table(row)},
        {("B0000132", "189689"): detail},
        {("HWP1", "1"): b"RAW-HWP"},
    )
    folder = tmp_path / "B0000132" / "189689"
    assert result["saved"] == 1
    assert (folder / "note.hwp").read_bytes() == b"RAW-HWP"
    text = (folder / "item.md").read_text(encoding="utf-8")
    meta = _meta(text)
    assert meta["extract_status"] == "pending_whale"
    assert meta["attachments"][0]["extract_status"] == "pending_whale"
    body = text.split("---", 2)[2]
    assert "pending_whale\nWhale 변환 대기" in body
    assert calls["file"] == [("200442", "HWP1", "1")]
    again, calls_again = _crawl(
        tmp_path,
        {("B0000132", 1): _list_table(row)},
        {("B0000132", "189689"): detail},
        {("HWP1", "1"): b"NEW"},
    )
    assert again["skipped"] == 1
    assert again["saved"] == 0
    assert calls_again["detail"] == []
    assert calls_again["file"] == []
    assert (folder / "note.hwp").read_bytes() == b"RAW-HWP"


def test_empty_pdf_status_is_empty(tmp_path):
    row = _item_row("13", "B0000132", "200442", "빈 파일", _file_link("empty.pdf", "PDF0", "1"))
    detail = _detail("빈 파일", "(없음)", "<li>" + _file_link("empty.pdf", "PDF0", "1") + "</li>")
    result, _calls = _crawl(
        tmp_path,
        {("B0000132", 1): _list_table(row)},
        {("B0000132", "13"): detail},
        {("PDF0", "1"): EMPTY_PDF},
    )
    assert result["saved"] == 1
    meta = _meta((tmp_path / "B0000132" / "13" / "item.md").read_text(encoding="utf-8"))
    assert meta["extract_status"] == "empty"
    assert meta["reply_date"] == "2025-01-09"


def test_retry_failed_skips_pending_whale_and_retries_failed_and_empty(tmp_path):
    pending = tmp_path / "B0000132" / "21"
    failed = tmp_path / "B0000132" / "22"
    empty = tmp_path / "B0000132" / "23"
    for directory, status, filename in (
        (pending, "pending_whale", "a.hwp"),
        (failed, "failed", "b.pdf"),
        (empty, "empty", None),
    ):
        directory.mkdir(parents=True)
        attachments = []
        if filename:
            (directory / filename).write_bytes(b"on-disk")
            attachments = [
                {"name": filename, "atch_file_id": "X", "file_sn": "1", "extract_status": status}
            ]
        meta = {
            "board": "B0000132",
            "menu_no": "200442",
            "ntt_id": directory.name,
            "number": directory.name,
            "title": "기존",
            "department": "회계감독국",
            "standards": [],
            "reply_date": "2024-01-01",
            "published_date": "2024-01-02",
            "page_url": "https://www.fss.or.kr/fss/bbs/B0000132/view.do?nttId=" + directory.name + "&menuNo=200442",
            "attachments": attachments,
            "fetched_at": "2026-11-12T09:00:00+09:00",
            "extract_status": status,
        }
        dumped = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
        (directory / "item.md").write_text(f"---\n{dumped}\n---\n\n## 상세 안내\n\n기존\n", encoding="utf-8")

    assert fss_replies.should_attempt(pending, retry_failed=False) is False
    assert fss_replies.should_attempt(pending, retry_failed=True) is False
    assert fss_replies.should_attempt(failed, retry_failed=False) is False
    assert fss_replies.should_attempt(failed, retry_failed=True) is True
    assert fss_replies.should_attempt(empty, retry_failed=False) is False
    assert fss_replies.should_attempt(empty, retry_failed=True) is True
    (failed / "b.pdf").unlink()
    assert fss_replies.should_attempt(failed, retry_failed=False) is True

    rows = "".join(
        [
            _item_row("21", "B0000132", "200442", "대기", _file_link("a.hwp", "H", "1"), number="21"),
            _item_row("22", "B0000132", "200442", "실패", _file_link("b.pdf", "P", "1"), number="22"),
            _item_row("23", "B0000132", "200442", "비어 있음", "", number="23", standards=""),
        ]
    )
    details = {
        ("B0000132", "22"): _detail("실패", "다시", "<li>" + _file_link("b.pdf", "P", "1") + "</li>"),
        ("B0000132", "23"): _detail("비어 있음", "첨부 없음", ""),
    }
    result, calls = _crawl(
        tmp_path,
        {("B0000132", 1): _list_table(rows)},
        details,
        {("P", "1"): HELLO_PDF},
        retry_failed=True,
    )
    assert calls["detail"] == [("B0000132", "22", "200442"), ("B0000132", "23", "200442")]
    assert result["skipped"] == 1
    assert (pending / "a.hwp").read_bytes() == b"on-disk"
    assert _meta((failed / "item.md").read_text(encoding="utf-8"))["extract_status"] == "ok"
    assert _meta((empty / "item.md").read_text(encoding="utf-8"))["extract_status"] == "empty"


def test_board_filter_does_not_request_other_boards(tmp_path):
    rows = "".join(
        [
            _item_row("11", "B0000132", "200442", "대상 (회신일 `24.1.2.)", _file_link("a.pdf", "PDF1", "1")),
            _item_row("22", "B0000133", "200443", "일반", "", number="22", standards=""),
            _item_row("33", "B0000134", "200444", "과거", "", number="33", standards=""),
        ]
    )
    pages = {("B0000132", 1): _list_table(rows), ("B0000132", 2): "<table><tbody></tbody></table>"}
    detail = _detail("대상 (회신일 `24.1.2.)", "안내", "<li>" + _file_link("a.pdf", "PDF1", "1") + "</li>")
    _result, calls = _crawl(
        tmp_path,
        pages,
        {("B0000132", "11"): detail},
        {("PDF1", "1"): HELLO_PDF},
        boards=["B0000132"],
    )
    assert {board for board, _menu, _page in calls["list"]} == {"B0000132"}
    assert [ntt for _board, ntt, _menu in calls["detail"]] == ["11"]
    assert "B0000133" not in str(calls)
    assert "B0000134" not in str(calls)
    assert calls["list"][-1][2] == 2


def test_limit_does_not_count_skipped_items(tmp_path):
    done = tmp_path / "B0000132" / "11"
    done.mkdir(parents=True)
    (done / "a.pdf").write_bytes(HELLO_PDF)
    meta = {
        "board": "B0000132",
        "menu_no": "200442",
        "ntt_id": "11",
        "number": "1",
        "title": "완료",
        "department": "",
        "standards": [],
        "reply_date": "2024-01-02",
        "published_date": "2024-01-02",
        "page_url": "https://www.fss.or.kr/fss/bbs/B0000132/view.do?nttId=11&menuNo=200442",
        "attachments": [{"name": "a.pdf", "atch_file_id": "PDF1", "file_sn": "1", "extract_status": "ok"}],
        "fetched_at": "2026-11-12T09:00:00+09:00",
        "extract_status": "ok",
    }
    (done / "item.md").write_text(
        "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\n",
        encoding="utf-8",
    )
    rows = "".join(
        [
            _item_row("11", "B0000132", "200442", "완료", _file_link("a.pdf", "PDF1", "1")),
            _item_row("12", "B0000132", "200442", "다음 (회신일 `24.5.6.)", _file_link("b.pdf", "PDF2", "1"), number="2"),
        ]
    )
    detail = _detail("다음 (회신일 `24.5.6.)", "둘째", "<li>" + _file_link("b.pdf", "PDF2", "1") + "</li>")
    result, calls = _crawl(
        tmp_path,
        {("B0000132", 1): _list_table(rows)},
        {("B0000132", "12"): detail},
        {("PDF2", "1"): HELLO_PDF},
        limit=1,
    )
    assert result["skipped"] == 1
    assert result["saved"] == 1
    assert calls["detail"] == [("B0000132", "12", "200442")]


def test_download_failure_leaves_no_item_and_records_manifest(tmp_path):
    row = _item_row("11", "B0000132", "200442", "실패", _file_link("a.pdf", "PDF1", "1"))
    detail = _detail("실패", "안내", "<li>" + _file_link("a.pdf", "PDF1", "1") + "</li>")

    def fetch_list(board, menu_no, page):
        return _list_table(row) if page == 1 else "<table><tbody></tbody></table>"

    def fetch_file(menu_no, atch_file_id, file_sn):
        raise RuntimeError("file down")

    result = fss_replies.crawl_archive(
        tmp_path,
        boards=["B0000132"],
        fetch_list=fetch_list,
        fetch_detail=lambda board, ntt_id, menu_no: detail,
        fetch_file=fetch_file,
        delay=0,
        sleep=lambda seconds: None,
        now=lambda: datetime.fromisoformat("2026-11-12T09:00:00+09:00"),
    )
    assert result["failed"] == 1
    assert not (tmp_path / "B0000132" / "11" / "item.md").exists()
    record = json.loads((tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert record["path"] is None
    assert record["extract_status"] == "failed"
    assert record["error"] == "file down"


def test_copy_archive_markdown_skips_existing_and_skips_attachments(tmp_path):
    archive = tmp_path / "archive"
    folder = archive / "B0000132" / "189689"
    folder.mkdir(parents=True)
    (folder / "item.md").write_text("원문\n", encoding="utf-8")
    (folder / "note.hwp").write_bytes(b"bin")
    dest = tmp_path / "raw"
    copied, skipped = fss_replies.copy_archive_markdown(archive, dest)
    assert (copied, skipped) == (1, 0)
    target = dest / "B0000132" / "189689.md"
    assert target.read_text(encoding="utf-8") == "원문\n"
    assert not (dest / "B0000132" / "note.hwp").exists()
    (folder / "item.md").write_text("바뀐 원문\n", encoding="utf-8")
    copied, skipped = fss_replies.copy_archive_markdown(archive, dest)
    assert (copied, skipped) == (0, 1)
    assert target.read_text(encoding="utf-8") == "원문\n"
    code = export_fss_replies_raw.main(["--archive", str(archive), "--dest", str(dest)])
    assert code == 0


def test_http_helpers_use_fixture_query_and_browser_user_agent(monkeypatch):
    calls = []

    class Session:
        def __init__(self):
            self.headers = {}

        def get(self, url, params=None, timeout=None):
            calls.append((url, params, timeout))

            class Response:
                text = "ok"
                content = b"file"
                encoding = "utf-8"

                def raise_for_status(self):
                    return None

            return Response()

    monkeypatch.setattr(fss_replies.requests, "Session", Session)
    session = fss_replies.make_session()
    assert session.headers["User-Agent"] == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    assert fss_replies.http_fetch_list(session, "B0000132", "200442", 2) == "ok"
    assert fss_replies.http_fetch_detail(session, "B0000132", "189689", "200442") == "ok"
    assert fss_replies.http_fetch_file(session, "200442", "6fffd4a8b6c5494e956ba19c81fdff72", "1") == b"file"
    assert calls[0][0] == "https://www.fss.or.kr/fss/bbs/B0000132/list.do"
    assert calls[0][1] == {"menuNo": "200442", "pageIndex": 2}
    assert calls[1][0] == "https://www.fss.or.kr/fss/bbs/B0000132/view.do"
    assert calls[1][1] == {"nttId": "189689", "menuNo": "200442"}
    assert calls[2][0] == "https://www.fss.or.kr/fss/cmmn/file/fileDown.do"
    assert calls[2][1] == {
        "menuNo": "200442",
        "atchFileId": "6fffd4a8b6c5494e956ba19c81fdff72",
        "fileSn": "1",
        "bbsId": "",
    }


def test_cli_defaults_and_rejects_excluded_board():
    args = crawl_fss_replies.parse_args([])
    assert args.board == "all"
    assert args.delay == 0.3
    assert args.limit is None
    assert args.retry_failed is False
    assert args.archive == fss_replies.default_archive()
    assert fss_replies.selected_boards("all") == ["B0000132", "B0000133"]
    assert fss_replies.selected_boards("B0000132") == ["B0000132"]
    with pytest.raises(SystemExit):
        crawl_fss_replies.parse_args(["--board", "B0000134"])
    export_args = export_fss_replies_raw.parse_args([])
    assert export_args.dest == fss_replies.default_raw_dest()
    assert str(export_args.dest).endswith("raw\\fss-replies") or str(export_args.dest).endswith("raw/fss-replies")


def test_real_list_stops_after_empty_page(tmp_path):
    pages = {1: LIST_132, 2: "<table><tbody></tbody></table>"}
    seen_pages = []

    def fetch_list(board, menu_no, page):
        seen_pages.append(page)
        return pages[page]

    result = fss_replies.crawl_archive(
        tmp_path,
        boards=["B0000132"],
        fetch_list=fetch_list,
        fetch_detail=lambda board, ntt_id, menu_no: VIEW_132,
        fetch_file=lambda menu_no, atch_file_id, file_sn: b"RAW-HWP",
        delay=0,
        sleep=lambda seconds: None,
        now=lambda: datetime.fromisoformat("2026-11-12T09:00:00+09:00"),
    )
    assert seen_pages == [1, 2]
    assert result["saved"] == 10
    assert all(record_status == "pending_whale" for record_status in (
        _meta((tmp_path / "B0000132" / ntt / "item.md").read_text(encoding="utf-8"))["extract_status"]
        for ntt in [path.name for path in (tmp_path / "B0000132").iterdir()]
    ))
