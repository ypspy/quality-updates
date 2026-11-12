# -*- coding: utf-8 -*-
import json
import subprocess
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
    copied, updated, skipped = fss_replies.copy_archive_markdown(archive, dest)
    assert (copied, updated, skipped) == (1, 0, 0)
    target = dest / "B0000132" / "189689.md"
    assert target.read_text(encoding="utf-8") == "원문\n"
    assert not (dest / "B0000132" / "note.hwp").exists()
    (folder / "item.md").write_text("바뀐 원문\n", encoding="utf-8")
    copied, updated, skipped = fss_replies.copy_archive_markdown(archive, dest)
    assert (copied, updated, skipped) == (0, 0, 1)
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
    assert args.refresh_standards is False
    assert args.extract_local is False
    assert args.from_extracted_body is False
    assert args.archive == fss_replies.default_archive()
    assert fss_replies.selected_boards("all") == ["B0000132", "B0000133"]
    assert fss_replies.selected_boards("B0000132") == ["B0000132"]
    with pytest.raises(SystemExit):
        crawl_fss_replies.parse_args(["--board", "B0000134"])
    export_args = export_fss_replies_raw.parse_args([])
    assert export_args.update_pending is False
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


def test_parse_detail_page_reads_related_standards():
    kifr = fss_replies.parse_detail_page(VIEW_132)
    assert kifr.standards == ("K-IFRS 제1117호",)
    gaap = fss_replies.parse_detail_page(VIEW_133)
    assert gaap.standards == ()
    multi = """
    <div class="krds-bd-view">
      <dl><div><dt>관련기준서</dt><dd>K-IFRS 제1109호<br>K-IFRS 제1115호</dd></div></dl>
    </div>
    """
    assert fss_replies.parse_detail_page(multi).standards == ("K-IFRS 제1109호", "K-IFRS 제1115호")


def test_infer_standards_from_title_attachment_and_notice():
    posting = "기업의 회계처리기준 적용 및 결정에 참고할 수 있는 일반기업회계기준 질의회신요약을 게시하오니, 첨부파일을 참고하시기 바랍니다."
    maintenance = "일반기업회계기준 도입에 따른 기존 질의회신 정비작업의 일환으로 '11.5.4일자로 폐기(사유 :존치유익미미)"
    assert fss_replies.infer_standards(
        "B0000133",
        "[2024-002] 일정 기간 양수인의 대출채권 매각이 특정 방법만 가능한 경우 회계처리",
        ["(일반기업회계기준) 일정 기간 양수인의 대출채권 매각이 특정 방법만 가능한 경우 회계처리.hwpx"],
        posting,
    ) == ["일반기업회계기준"]
    assert fss_replies.infer_standards(
        "B0000133",
        "저축은행이 취득한 사모사채",
        ["(일반기준)저축은행이 취득한 사모사채.hwp"],
        "(없음)",
    ) == ["일반기업회계기준"]
    assert fss_replies.infer_standards(
        "B0000133",
        "「기업회계기준 등에 관한 해석 56-90」 유효기간 경과에 따른 관련 질의회신 수정 또는 폐기(`25.2.25)",
        ["기업회계기준 등에 관한 해석 56-90 유효기간 경과에 따른 관련 질의회신 수정 또는 폐기(`25.2.25.).hwpx"],
        "「기업회계기준 등에 관한 해석 56-90」유효기간(`23.12.31.) 경과에 따라 더이상 유효하지 않은 질의회신을 수정 또는 폐기",
    ) == ["기업회계기준 등에 관한 해석 56-90"]
    assert fss_replies.infer_standards(
        "B0000133",
        "공백 「 기업회계기준 등에 관한 해석 56 - 90 」",
        [],
        "",
    ) == ["기업회계기준 등에 관한 해석 56-90"]
    chapter_notice = (
        "일반기업회계기준 연차개선 (2018) 으로 특별 퇴직금을 포함한 모든 종업원 급여가 "
        "일반 기업회계기준 제21장 (종업원급여) 의 적용 범위에 포함됨에 따라, '18.12.24.일자로 폐기"
    )
    assert fss_replies.infer_standards(
        "B0000133",
        "[2007-023] 준정년특별퇴직제도의 퇴직금 회계처리('18.12.24. 폐기)",
        ["2007-023 준정년특별퇴직제도의 퇴직금 회계처리.hwp"],
        chapter_notice,
    ) == ["일반기업회계기준 제21장 (종업원급여)"]
    assert fss_replies.infer_standards(
        "B0000133",
        "붙여 쓴 장",
        [],
        "일반기업 회계기준 제22장 (법인세회계) 의 적용범위",
    ) == ["일반기업회계기준 제22장 (법인세회계)"]
    assert fss_replies.infer_standards(
        "B0000133",
        "[2004-100]기업회계기준서 제8호(유가증권) 문단14의 적용적합 여부('11.5.4 수정)",
        [
            "2004-100(회제이 8360-00090) 기업회계기준서 제8호(유가증권) 문단 14의 적용적합 여부.hwp",
            "(수정) 2004-100 일반기업회계기준 제6장 문단25 및 26의 적용 적합 여부.hwp_.hwp",
        ],
        "일반기업회계기준 도입에 따른 기존 질의회신 정비작업의 일환으로 ’11.5.4일자로 수정(사유 : 관련조문변경)",
    ) == ["기업회계기준서 제8호(유가증권)", "일반기업회계기준 제6장"]
    assert fss_replies.infer_standards(
        "B0000133",
        "[2003-117] 기업회계기준서 제8호 유가증권의 적용관련 질의('11.5.4)",
        ["(수정) 2003-117 일반기업회계기준 제6장 금융자산금융부채의 적용관련 질의.hwp_.hwp"],
        maintenance,
    ) == ["기업회계기준서 제8호", "일반기업회계기준 제6장"]
    assert fss_replies.infer_standards(
        "B0000133",
        "[2006-064]기업회계기준서 제15호 적용에 따른 전기누적손실 반영에 대한 질의('11.5.4 폐기)",
        ["2006-064 기업회계기준서 제15호 적용에 따른 전기누적손실 반영에 대한 질의.hwp"],
        maintenance,
    ) == ["기업회계기준서 제15호"]
    assert fss_replies.infer_standards(
        "B0000133",
        "[2005-059] 기업회계기준서 제16호 법인세회계에 대한 질의 ('11.5.4 수정)",
        [],
        maintenance,
    ) == ["기업회계기준서 제16호"]
    kifrs = fss_replies.infer_standards(
        "B0000133",
        "[2010-029]K-IFRS 도입에 따른 영향 사전공시 관련 질의회신('11.5.4 폐기)",
        ["[2010-029] K-IFRS 도입에 따른 영향 사전공시 관련 질의회신.hwp"],
        maintenance,
    )
    assert kifrs == ["일반기업회계기준"]
    assert not any("제" in item and "호" in item for item in kifrs)
    assert fss_replies.infer_standards(
        "B0000133",
        "[2011-040] 유형자산 재평가 관련 질의",
        [],
        "유사한 K-IFRS 질의회신에서 같은 결론을 제시하였다",
    ) == ["일반기업회계기준"]
    assert fss_replies.infer_standards(
        "B0000133",
        "[2008-056] 파생상품의 중소기업회계처리 특례 적용여부에 대한 질의",
        ["2008-056 파생상품의 중소기업회계처리 특례 적용여부에 대한 질의.hwp"],
        "(없음)",
    ) == ["중소기업회계처리 특례"]
    assert fss_replies.infer_standards(
        "B0000133",
        "[2006-061]지분법관련 중소기업회계처리특례에 대한 질의회신('11.5.4 폐기)",
        [],
        maintenance,
    ) == ["중소기업회계처리 특례"]
    assert fss_replies.infer_standards(
        "B0000133",
        "[2007-070] 중소기업 회계처리 특례 적용",
        [],
        "(없음)",
    ) == ["중소기업회계처리 특례"]
    assert fss_replies.infer_standards("B0000133", "대출채권 양도", [], "(없음)") == ["일반기업회계기준"]
    assert fss_replies.infer_standards("B0000133", "제목", [], maintenance) == ["일반기업회계기준"]
    assert fss_replies.infer_standards("B0000132", "일반 공지", [], maintenance) == []
    assert fss_replies.infer_standards(
        "B0000133",
        "수익인식 실무지침 제2호(예시) 문단4",
        [],
        posting,
    ) == ["실무지침 제2호(예시)"]


def _compose(row_standards, detail_standards, title, notice, filenames=()):
    row = fss_replies.ListRow(
        board="B0000133",
        menu_no="200443",
        ntt_id="1",
        number="1",
        title=title,
        department="회계감독국",
        standards=tuple(row_standards),
        published_date="2024-01-02",
        attachments=(),
    )
    detail = fss_replies.DetailPage(
        subject=title,
        department="회계감독국",
        registered_date="2024-01-02",
        notice=notice,
        attachments=(),
        standards=tuple(detail_standards),
    )
    sections = []
    for name in filenames:
        ref = fss_replies.AttachmentRef(name, "ID", "1", "200443")
        sections.append((ref, name, "", "pending_whale"))
    text = fss_replies.compose_item(row, detail, sections, "2026-11-12T09:00:00+09:00")
    return _meta(text)["standards"]


def test_compose_prefers_list_then_detail_then_inference():
    notice = "일반기업회계기준 제21장 (종업원급여) 적용"
    assert _compose(
        ["K-IFRS 제1102호"],
        ["K-IFRS 제9999호"],
        "기업회계기준서 제15호 문단3",
        notice,
    ) == ["K-IFRS 제1102호"]
    assert _compose(
        [],
        ["K-IFRS 제1117호"],
        "기업회계기준서 제15호 문단3",
        notice,
    ) == ["K-IFRS 제1117호"]
    assert _compose(
        [],
        [],
        "기업회계기준서 제15호 문단3",
        "일반기업회계기준 도입에 따른 기존 질의회신 정비작업의 일환으로 폐기",
    ) == ["기업회계기준서 제15호"]


def test_crawl_keeps_list_standards_and_uses_detail_when_list_is_empty(tmp_path):
    kept = _item_row(
        "11",
        "B0000132",
        "200442",
        "기업회계기준서 제15호 문단3",
        "",
        standards="K-IFRS 제1102호",
    )
    detail_kept = """
    <div class="krds-bd-view">
      <h3 class="subject">기업회계기준서 제15호 문단3</h3>
      <dl><div><dt>관련기준서</dt><dd>K-IFRS 제9999호</dd></div></dl>
      <div class="dbdata"><p>일반기업회계기준 제21장 (종업원급여)</p></div>
    </div>
    """
    result, _calls = _crawl(
        tmp_path / "kept",
        {("B0000132", 1): _list_table(kept)},
        {("B0000132", "11"): detail_kept},
        {},
    )
    assert result["saved"] == 1
    assert _meta((tmp_path / "kept" / "B0000132" / "11" / "item.md").read_text(encoding="utf-8"))["standards"] == [
        "K-IFRS 제1102호"
    ]

    empty = _item_row(
        "77",
        "B0000133",
        "200443",
        "기업회계기준서 제15호 문단3",
        "",
        standards="",
    )
    detail_empty = """
    <div class="krds-bd-view">
      <h3 class="subject">기업회계기준서 제15호 문단3</h3>
      <dl><div><dt>관련기준서</dt><dd>K-IFRS 제1117호</dd></div>
      <div><dt>등록일</dt><dd>2025-01-09</dd></div></dl>
      <div class="dbdata"><p>일반기업회계기준 제6장 문단1</p></div>
    </div>
    """
    result, _calls = _crawl(
        tmp_path / "detail",
        {("B0000133", 1): _list_table(empty)},
        {("B0000133", "77"): detail_empty},
        {},
        boards=["B0000133"],
    )
    assert result["saved"] == 1
    meta = _meta((tmp_path / "detail" / "B0000133" / "77" / "item.md").read_text(encoding="utf-8"))
    assert meta["standards"] == ["K-IFRS 제1117호"]


def _item_markdown(meta: dict, notice: str, attachment_sections: str) -> str:
    dumped = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{dumped}\n---\n\n## 상세 안내\n\n{notice}\n{attachment_sections}"


def test_refresh_standards_rewrites_front_matter_and_manifest(tmp_path):
    gaap = tmp_path / "B0000133" / "43613"
    kifr = tmp_path / "B0000132" / "189689"
    gaap.mkdir(parents=True)
    kifr.mkdir(parents=True)
    (gaap / "note.hwp").write_bytes(b"RAW-HWP")
    (kifr / "keep.hwp").write_bytes(b"KEEP")
    gaap_meta = {
        "board": "B0000133",
        "menu_no": "200443",
        "ntt_id": "43613",
        "number": "420",
        "title": "[2004-100]기업회계기준서 제8호(유가증권) 문단14의 적용적합 여부",
        "department": "회계제도실",
        "standards": [],
        "reply_date": "2008-12-24",
        "published_date": "2008-12-24",
        "page_url": "https://www.fss.or.kr/fss/bbs/B0000133/view.do?nttId=43613&menuNo=200443",
        "attachments": [
            {
                "name": "(수정) 2004-100 일반기업회계기준 제6장 문단25 및 26의 적용 적합 여부.hwp",
                "atch_file_id": "ABC",
                "file_sn": "2",
                "extract_status": "pending_whale",
            }
        ],
        "fetched_at": "2026-11-12T14:03:34.486978+09:00",
        "extract_status": "pending_whale",
    }
    gaap_notice = "일반기업회계기준 도입에 따른 기존 질의회신 정비작업의 일환으로 수정"
    gaap_tail = "\n## 첨부: (수정) 2004-100 일반기업회계기준 제6장 문단25 및 26의 적용 적합 여부.hwp\n\npending_whale\nWhale 변환 대기\n"
    gaap_text = _item_markdown(gaap_meta, gaap_notice, gaap_tail)
    (gaap / "item.md").write_text(gaap_text, encoding="utf-8")
    kifr_meta = {
        "board": "B0000132",
        "menu_no": "200442",
        "ntt_id": "189689",
        "number": "49",
        "title": "기업회계기준서 제15호를 제목에 적어도 목록 값을 유지",
        "department": "회계감독국",
        "standards": ["K-IFRS 제1117호"],
        "reply_date": "2024-12-27",
        "published_date": "2025-01-09",
        "page_url": "https://www.fss.or.kr/fss/bbs/B0000132/view.do?nttId=189689&menuNo=200442",
        "attachments": [
            {"name": "keep.hwp", "atch_file_id": "K", "file_sn": "1", "extract_status": "pending_whale"}
        ],
        "fetched_at": "2026-11-12T12:57:50.899766+09:00",
        "extract_status": "pending_whale",
    }
    kifr_text = _item_markdown(kifr_meta, "(없음)", "\n## 첨부: keep.hwp\n\npending_whale\nWhale 변환 대기\n")
    (kifr / "item.md").write_text(kifr_text, encoding="utf-8")
    first = {
        "board": "B0000132",
        "ntt_id": "189689",
        "menu_no": "200442",
        "number": "49",
        "title": kifr_meta["title"],
        "reply_date": "2024-12-27",
        "published_date": "2025-01-09",
        "extract_status": "pending_whale",
        "path": "B0000132/189689/item.md",
        "error": None,
    }
    second = {
        "board": "B0000133",
        "ntt_id": "43613",
        "menu_no": "200443",
        "number": "420",
        "title": gaap_meta["title"],
        "reply_date": "2008-12-24",
        "published_date": "2008-12-24",
        "extract_status": "pending_whale",
        "path": "B0000133/43613/item.md",
        "error": None,
    }
    duplicate = json.dumps(first, ensure_ascii=False)
    (tmp_path / "manifest.jsonl").write_text(
        duplicate + "\n" + json.dumps(second, ensure_ascii=False) + "\n" + duplicate + "\n",
        encoding="utf-8",
    )

    result = fss_replies.refresh_standards(tmp_path)
    assert result["updated"] == 1
    assert result["unchanged"] == 1
    assert result["items"] == 2
    rewritten = (gaap / "item.md").read_text(encoding="utf-8")
    assert rewritten.split("---", 2)[2] == gaap_text.split("---", 2)[2]
    meta = _meta(rewritten)
    assert meta["standards"] == ["기업회계기준서 제8호(유가증권)", "일반기업회계기준 제6장"]
    assert meta["fetched_at"] == gaap_meta["fetched_at"]
    assert meta["extract_status"] == "pending_whale"
    assert meta["attachments"] == gaap_meta["attachments"]
    assert "문단" not in " ".join(meta["standards"])
    assert (gaap / "note.hwp").read_bytes() == b"RAW-HWP"
    assert (kifr / "item.md").read_text(encoding="utf-8") == kifr_text
    assert (kifr / "keep.hwp").read_bytes() == b"KEEP"
    lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    assert [(row["board"], row["ntt_id"]) for row in records] == [("B0000132", "189689"), ("B0000133", "43613")]
    assert records[0]["standards"] == ["K-IFRS 제1117호"]
    assert records[0]["error"] is None
    assert records[0]["path"] == "B0000132/189689/item.md"
    assert records[1]["standards"] == meta["standards"]
    assert records[1]["title"] == gaap_meta["title"]
    again = fss_replies.refresh_standards(tmp_path)
    assert again["updated"] == 0
    assert again["unchanged"] == 2
    assert (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines() == lines
    assert (gaap / "item.md").read_text(encoding="utf-8") == rewritten


def test_refresh_standards_cli_does_not_crawl(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("crawl")

    monkeypatch.setattr(fss_replies, "crawl_archive", boom)
    folder = tmp_path / "B0000133" / "1"
    folder.mkdir(parents=True)
    meta = {
        "board": "B0000133",
        "menu_no": "200443",
        "ntt_id": "1",
        "number": "1",
        "title": "첨부 없는 일반 질의",
        "department": "회계감독국",
        "standards": [],
        "reply_date": "2024-01-02",
        "published_date": "2024-01-02",
        "page_url": "https://www.fss.or.kr/fss/bbs/B0000133/view.do?nttId=1&menuNo=200443",
        "attachments": [],
        "fetched_at": "2026-11-12T09:00:00+09:00",
        "extract_status": "empty",
    }
    (folder / "item.md").write_text(_item_markdown(meta, "(없음)", ""), encoding="utf-8")
    args = crawl_fss_replies.parse_args([])
    assert args.refresh_standards is False
    code = crawl_fss_replies.main(["--refresh-standards", "--archive", str(tmp_path)])
    assert code == 0
    assert _meta((folder / "item.md").read_text(encoding="utf-8"))["standards"] == ["일반기업회계기준"]


_SAMPLE_HTML = """<html><head><style>.x{color:red}</style></head>
<body><style>.y{font-size:1px}</style>
<p>첫째 문단</p>
<p>둘째 문단</p>
<table><tr><th>열1</th><th>열2</th></tr><tr><td>가</td><td>나</td></tr></table>
<script>alert(1)</script>
</body></html>"""


def test_html_to_markdown_keeps_paragraphs_and_tables_and_drops_style():
    text = fss_replies.html_to_markdown(_SAMPLE_HTML)
    assert "첫째 문단" in text
    assert "둘째 문단" in text
    assert text.index("첫째 문단") < text.index("둘째 문단")
    assert "첫째 문단둘째" not in text
    assert "가" in text and "나" in text
    assert "|" in text
    lowered = text.lower()
    assert "color" not in lowered
    assert "alert" not in lowered
    assert "<style" not in lowered
    assert "<head" not in lowered
    assert "<script" not in lowered


def _hwpx_bytes() -> bytes:
    import io
    import zipfile

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
        xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">
  <hp:p><hp:run><hp:t>회신 본문</hp:t></hp:run></hp:p>
  <hp:p><hp:run><hp:tbl>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>왼쪽</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>오른쪽</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>1</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>2</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
  </hp:tbl></hp:run></hp:p>
</hs:sec>
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Contents/section0.xml", xml)
        archive.writestr("Contents/header.xml", "<hp:t>머리글은 본문이 아니다</hp:t>")
    return buffer.getvalue()


def test_hwpx_zip_reads_paragraphs_and_table_cells():
    text = fss_replies.hwpx_to_text(_hwpx_bytes())
    assert "회신 본문" in text
    assert "왼쪽" in text and "오른쪽" in text
    assert "1" in text and "2" in text
    assert "회신 본문 왼쪽" not in text
    assert "머리글은 본문이 아니다" not in text
    assert "|" in text


def _archive_item(
    archive: Path,
    *,
    board: str,
    ntt_id: str,
    filename: str,
    standards: list,
    title: str,
    notice: str = "(없음)",
    attachments=None,
    sections: str | None = None,
    item_status: str = "pending_whale",
) -> Path:
    folder = archive / board / ntt_id
    folder.mkdir(parents=True, exist_ok=True)
    if attachments is None:
        attachments = [
            {"name": filename, "atch_file_id": "ID", "file_sn": "1", "extract_status": "pending_whale"}
        ]
    meta = {
        "board": board,
        "menu_no": "200442" if board == "B0000132" else "200443",
        "ntt_id": ntt_id,
        "number": "1",
        "title": title,
        "department": "회계감독국",
        "standards": standards,
        "reply_date": "2024-01-02",
        "published_date": "2024-01-02",
        "page_url": f"https://www.fss.or.kr/fss/bbs/{board}/view.do?nttId={ntt_id}&menuNo=200442",
        "attachments": attachments,
        "fetched_at": "2026-11-12T09:00:00+09:00",
        "extract_status": item_status,
    }
    if sections is None:
        sections = f"\n## 첨부: {filename}\n\npending_whale\nWhale 변환 대기\n"
    text = _item_markdown(meta, notice, sections)
    (folder / "item.md").write_text(text, encoding="utf-8")
    record = {
        "board": board,
        "ntt_id": ntt_id,
        "menu_no": meta["menu_no"],
        "number": "1",
        "title": title,
        "reply_date": "2024-01-02",
        "published_date": "2024-01-02",
        "extract_status": item_status,
        "path": f"{board}/{ntt_id}/item.md",
        "error": None,
        "standards": standards,
    }
    manifest = archive / "manifest.jsonl"
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return folder


def test_hwp_file_to_html_uses_temp_html_and_not_hwp5txt(tmp_path, monkeypatch):
    from crawler import fss_hwp_text

    hwp = tmp_path / "note.hwp"
    hwp.write_bytes(b"not-a-real-hwp")

    def fake_run(command, cwd, timeout, check, capture_output):
        assert "--html" in command
        assert "hwp5txt" not in " ".join(command)
        assert str(hwp) in command
        assert timeout == 60
        out = Path(command[command.index("--output") + 1])
        out.write_text("<html><body><p>임시 본문</p></body></html>", encoding="utf-8")

        class Result:
            returncode = 0
            stderr = b""
            stdout = b""

        return Result()

    monkeypatch.setattr(fss_hwp_text.subprocess, "run", fake_run)
    html = fss_hwp_text.hwp_file_to_html(hwp, timeout=60)
    assert "임시 본문" in html
    assert not list(tmp_path.glob("*.html"))
    assert list(tmp_path.iterdir()) == [hwp]

    def fail_run(command, cwd, timeout, check, capture_output):
        class Result:
            returncode = 1
            stderr = b"boom"
            stdout = b""

        return Result()

    monkeypatch.setattr(fss_hwp_text.subprocess, "run", fail_run)
    with pytest.raises(fss_replies.HwpConvertError):
        fss_hwp_text.hwp_file_to_html(hwp, timeout=60)


def test_hwp5html_command_uses_html_not_hwp5txt(tmp_path):
    argv = fss_replies.hwp5html_command(tmp_path / "note.hwp", tmp_path / "out.html")
    joined = " ".join(argv)
    assert "--html" in argv
    assert "--output" in argv
    assert str(tmp_path / "note.hwp") in argv
    assert "hwp5txt" not in joined
    assert any("hwp5html" in part for part in argv)


def test_extract_local_hwp_success_updates_section_and_manifest(tmp_path):
    folder = _archive_item(
        tmp_path,
        board="B0000132",
        ntt_id="133043",
        filename="note.hwp",
        standards=["K-IFRS 제1109호"],
        title="목록 값을 유지하는 질의",
        notice="상세 안내 문장",
    )
    (folder / "note.hwp").write_bytes(b"RAW-HWP")
    duplicate = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8")
    (tmp_path / "manifest.jsonl").write_text(duplicate + duplicate, encoding="utf-8")

    def fake_html(path, timeout=90):
        assert Path(path).name == "note.hwp"
        assert timeout >= 60
        return _SAMPLE_HTML

    result = fss_replies.extract_local(tmp_path, hwp_to_html=fake_html)
    assert result["parsed"] == 1
    assert result["failed"] == 0
    assert result["missing"] == 0
    text = (folder / "item.md").read_text(encoding="utf-8")
    meta = _meta(text)
    assert meta["extract_status"] == "ok"
    assert meta["attachments"][0]["extract_status"] == "hwp_parsed"
    assert meta["fetched_at"] == "2026-11-12T09:00:00+09:00"
    assert meta["standards"] == ["K-IFRS 제1109호"]
    assert "상세 안내 문장" in text
    assert "첫째 문단" in text
    assert "pending_whale" not in text.split("---", 2)[2]
    assert "color" not in text.split("## 첨부:", 1)[1].lower()
    assert (folder / "note.hwp").read_bytes() == b"RAW-HWP"
    assert sorted(path.name for path in folder.iterdir()) == ["item.md", "note.hwp"]
    lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["extract_status"] == "ok"
    assert record["standards"] == ["K-IFRS 제1109호"]
    assert record["title"] == "목록 값을 유지하는 질의"
    assert fss_replies.should_attempt(folder, False) is False
    assert fss_replies.should_attempt(folder, True) is False


def test_extract_local_missing_file_stays_pending(tmp_path):
    folder = _archive_item(
        tmp_path,
        board="B0000133",
        ntt_id="1",
        filename="gone.hwp",
        standards=["일반기업회계기준"],
        title="파일 없는 질의",
    )
    before = sorted(path.name for path in folder.iterdir())
    result = fss_replies.extract_local(tmp_path, hwp_to_html=lambda path, timeout=90: "본문")
    assert result["missing"] == 1
    assert result["parsed"] == 0
    assert result["failed"] == 0
    text = (folder / "item.md").read_text(encoding="utf-8")
    meta = _meta(text)
    assert meta["extract_status"] == "pending_whale"
    assert meta["attachments"][0]["extract_status"] == "pending_whale"
    assert "pending_whale\nWhale 변환 대기" in text
    assert sorted(path.name for path in folder.iterdir()) == before


def test_extract_local_timeout_and_failure_keep_parsed_sibling(tmp_path):
    sections = (
        "\n## 첨부: done.hwp\n\n이미 있는 본문\n"
        "\n## 첨부: slow.hwp\n\npending_whale\nWhale 변환 대기\n"
    )
    folder = _archive_item(
        tmp_path,
        board="B0000133",
        ntt_id="2",
        filename="slow.hwp",
        standards=["일반기업회계기준"],
        title="일부만 실패",
        attachments=[
            {"name": "done.hwp", "atch_file_id": "A", "file_sn": "1", "extract_status": "hwp_parsed"},
            {"name": "slow.hwp", "atch_file_id": "B", "file_sn": "2", "extract_status": "pending_whale"},
        ],
        sections=sections,
    )
    (folder / "done.hwp").write_bytes(b"DONE")
    (folder / "slow.hwp").write_bytes(b"SLOW")

    def explode(path, timeout=90):
        raise subprocess.TimeoutExpired(cmd="hwp5html", timeout=timeout)

    result = fss_replies.extract_local(tmp_path, hwp_to_html=explode)
    assert result["failed"] == 1
    assert result["parsed"] == 0
    text = (folder / "item.md").read_text(encoding="utf-8")
    meta = _meta(text)
    assert meta["extract_status"] == "pending_whale"
    by_name = {item["name"]: item["extract_status"] for item in meta["attachments"]}
    assert by_name == {"done.hwp": "hwp_parsed", "slow.hwp": "pending_whale"}
    assert "이미 있는 본문" in text
    slow = text.split("## 첨부: slow.hwp", 1)[1]
    assert "오류:" in slow
    assert "pending_whale" in slow
    assert (folder / "done.hwp").read_bytes() == b"DONE"
    assert (folder / "slow.hwp").read_bytes() == b"SLOW"

    broken = _archive_item(
        tmp_path,
        board="B0000133",
        ntt_id="3",
        filename="bad.hwp",
        standards=["일반기업회계기준"],
        title="변환 실패",
    )
    (broken / "bad.hwp").write_bytes(b"BAD")

    def fail(path, timeout=90):
        raise fss_replies.HwpConvertError("hwp5html exit 1")

    failed = fss_replies.extract_local(tmp_path, hwp_to_html=fail)
    assert failed["failed"] >= 1
    bad_text = (broken / "item.md").read_text(encoding="utf-8")
    assert _meta(bad_text)["extract_status"] == "pending_whale"
    assert "오류:" in bad_text.split("## 첨부: bad.hwp", 1)[1]
    assert "이미 있는 본문" in (folder / "item.md").read_text(encoding="utf-8")


def test_extract_local_is_idempotent(tmp_path):
    folder = _archive_item(
        tmp_path,
        board="B0000133",
        ntt_id="4",
        filename="note.hwp",
        standards=["일반기업회계기준"],
        title="두 번 돌려도 본문을 유지",
    )
    (folder / "note.hwp").write_bytes(b"RAW")
    calls = {"n": 0}

    def fake_html(path, timeout=90):
        calls["n"] += 1
        return "<html><body><p>유지되는 본문</p></body></html>"

    first = fss_replies.extract_local(tmp_path, hwp_to_html=fake_html)
    assert first["parsed"] == 1
    once = (folder / "item.md").read_text(encoding="utf-8")
    second = fss_replies.extract_local(tmp_path, hwp_to_html=fake_html)
    assert second["parsed"] == 0
    assert second["skipped"] >= 1
    assert calls["n"] == 1
    assert (folder / "item.md").read_text(encoding="utf-8") == once
    assert "유지되는 본문" in once
    assert "pending_whale" not in once.split("---", 2)[2]


def test_extract_local_hwpx_sets_hwpx_parsed(tmp_path):
    folder = _archive_item(
        tmp_path,
        board="B0000133",
        ntt_id="191435",
        filename="note.hwpx",
        standards=["일반기업회계기준"],
        title="HWPX 합성",
    )
    (folder / "note.hwpx").write_bytes(_hwpx_bytes())
    result = fss_replies.extract_local(tmp_path, hwp_to_html=lambda path, timeout=90: (_ for _ in ()).throw(AssertionError("hwp")))
    assert result["parsed"] == 1
    text = (folder / "item.md").read_text(encoding="utf-8")
    meta = _meta(text)
    assert meta["attachments"][0]["extract_status"] == "hwpx_parsed"
    assert meta["extract_status"] == "ok"
    assert "회신 본문" in text
    assert "왼쪽" in text
    assert (folder / "note.hwpx").read_bytes() == _hwpx_bytes()


def test_extract_local_empty_html_stays_pending(tmp_path):
    folder = _archive_item(
        tmp_path,
        board="B0000133",
        ntt_id="5",
        filename="blank.hwp",
        standards=["일반기업회계기준"],
        title="빈 HTML",
    )
    (folder / "blank.hwp").write_bytes(b"BLANK")
    result = fss_replies.extract_local(
        tmp_path,
        hwp_to_html=lambda path, timeout=90: "<html><head><style>.x{}</style></head><body></body></html>",
    )
    assert result["parsed"] == 0
    assert result["failed"] == 1
    text = (folder / "item.md").read_text(encoding="utf-8")
    assert _meta(text)["extract_status"] == "pending_whale"
    assert _meta(text)["attachments"][0]["extract_status"] == "pending_whale"
    assert "오류:" in text


def test_body_citation_replaces_bare_fallback_but_not_list_values(tmp_path):
    bare = _archive_item(
        tmp_path,
        board="B0000133",
        ntt_id="21",
        filename="chap.hwp",
        standards=["일반기업회계기준"],
        title="장 번호가 본문에만 있는 질의",
        notice="(없음)",
    )
    (bare / "chap.hwp").write_bytes(b"CHAP")
    listed = _archive_item(
        tmp_path,
        board="B0000132",
        ntt_id="22",
        filename="keep.hwp",
        standards=["K-IFRS 제1117호"],
        title="목록 기준서를 본문이 바꾸지 않는다",
        notice="일반기업회계기준 제6장",
    )
    (listed / "keep.hwp").write_bytes(b"KEEP")
    false_positive = _archive_item(
        tmp_path,
        board="B0000133",
        ntt_id="44253",
        filename="kifrs.hwp",
        standards=["K-IFRS", "일반기업회계기준"],
        title="[2010-029]K-IFRS 도입에 따른 영향 사전공시 관련 질의회신('11.5.4 폐기)",
        notice="일반기업회계기준 도입에 따른 기존 질의회신 정비작업의 일환으로 폐기",
    )
    (false_positive / "kifrs.hwp").write_bytes(b"K")

    def fake_html(path, timeout=90):
        name = Path(path).name
        if name == "chap.hwp":
            return "<html><body><p>일반기업회계기준 제21장 (종업원급여) 적용</p></body></html>"
        if name == "keep.hwp":
            return "<html><body><p>일반기업회계기준 제6장</p></body></html>"
        return "<html><body><p>도입 경위만 적힌 본문</p></body></html>"

    untouched = fss_replies.refresh_standards(tmp_path)
    assert _meta((bare / "item.md").read_text(encoding="utf-8"))["standards"] == ["일반기업회계기준"]
    assert untouched["updated"] == 0

    fss_replies.extract_local(tmp_path, hwp_to_html=fake_html)
    assert _meta((bare / "item.md").read_text(encoding="utf-8"))["standards"] == [
        "일반기업회계기준 제21장 (종업원급여)"
    ]
    assert _meta((listed / "item.md").read_text(encoding="utf-8"))["standards"] == ["K-IFRS 제1117호"]
    assert _meta((false_positive / "item.md").read_text(encoding="utf-8"))["standards"] == ["일반기업회계기준"]

    again = fss_replies.refresh_standards(tmp_path, from_body=True)
    assert again["updated"] == 0
    assert _meta((listed / "item.md").read_text(encoding="utf-8"))["standards"] == ["K-IFRS 제1117호"]


def test_compose_item_writes_parsed_hangul_body():
    row = fss_replies.ListRow(
        board="B0000133",
        menu_no="200443",
        ntt_id="9",
        number="1",
        title="합성",
        department="회계감독국",
        standards=(),
        published_date="2024-01-02",
        attachments=(),
    )
    detail = fss_replies.DetailPage(
        subject="합성",
        department="회계감독국",
        registered_date="2024-01-02",
        notice="안내",
        attachments=(),
        standards=(),
    )
    ref = fss_replies.AttachmentRef("a.hwp", "ID", "1", "200443")
    text = fss_replies.compose_item(
        row,
        detail,
        [(ref, "a.hwp", "표가 있는 본문", "hwp_parsed"), (ref, "b.hwpx", "둘째", "hwpx_parsed")],
        "2026-11-12T09:00:00+09:00",
    )
    meta = _meta(text)
    assert meta["extract_status"] == "ok"
    assert [item["extract_status"] for item in meta["attachments"]] == ["hwp_parsed", "hwpx_parsed"]
    body = text.split("---", 2)[2]
    assert "표가 있는 본문" in body
    assert "둘째" in body
    assert "pending_whale" not in body
    assert fss_replies.aggregate_status(["hwp_parsed", "hwpx_parsed"]) == "ok"
    assert fss_replies.aggregate_status(["hwp_parsed", "pending_whale"]) == "pending_whale"
    assert fss_replies.aggregate_status(["failed", "hwp_parsed"]) == "failed"


def test_should_attempt_skips_item_level_hwp_parsed(tmp_path):
    folder = _archive_item(
        tmp_path,
        board="B0000133",
        ntt_id="8",
        filename="a.hwp",
        standards=["일반기업회계기준"],
        title="항목 상태가 hwp_parsed",
        item_status="hwp_parsed",
        attachments=[
            {"name": "a.hwp", "atch_file_id": "A", "file_sn": "1", "extract_status": "hwp_parsed"}
        ],
        sections="\n## 첨부: a.hwp\n\n이미 추출한 본문\n",
    )
    (folder / "a.hwp").write_bytes(b"A")
    assert fss_replies.should_attempt(folder, False) is False
    assert fss_replies.should_attempt(folder, True) is False


def _front_item(status: str, title: str = "제목") -> str:
    meta = {
        "board": "B0000133",
        "ntt_id": "1",
        "title": title,
        "standards": ["일반기업회계기준"],
        "extract_status": status,
    }
    return _item_markdown(meta, "(없음)", "\n## 첨부: a.hwp\n\n본문\n")


def test_update_pending_overwrites_only_when_target_is_pending(tmp_path):
    archive = tmp_path / "archive"
    dest = tmp_path / "raw"

    def put(ntt_id: str, status: str, body: str = "원문") -> None:
        folder = archive / "B0000133" / ntt_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "a.hwp").write_bytes(b"bin")
        (folder / "item.md").write_text(_front_item(status).replace("본문", body), encoding="utf-8")

    put("10", "ok", "새 원문")
    copied, updated, skipped = fss_replies.copy_archive_markdown(archive, dest)
    assert (copied, updated, skipped) == (1, 0, 0)
    target = dest / "B0000133" / "10.md"
    assert "새 원문" in target.read_text(encoding="utf-8")
    assert not (dest / "B0000133" / "a.hwp").exists()

    put("11", "pending_whale", "아직 대기")
    (dest / "B0000133").mkdir(parents=True, exist_ok=True)
    (dest / "B0000133" / "11.md").write_text(_front_item("pending_whale").replace("본문", "대상 대기"), encoding="utf-8")
    put("12", "ok", "소스 완료")
    (dest / "B0000133" / "12.md").write_text(_front_item("pending_whale").replace("본문", "대상 대기"), encoding="utf-8")
    put("13", "ok", "다시 씀")
    (dest / "B0000133" / "13.md").write_text(_front_item("ok").replace("본문", "이미 ok"), encoding="utf-8")
    (dest / "B0000133" / "14.md").write_text("프론트매터 없음\n", encoding="utf-8")
    put("14", "ok", "소스만 있음")
    (dest / "B0000133" / "15.md").write_text(_front_item("pending_whale"), encoding="utf-8")
    orphan = dest / "B0000132" / "999.md"
    orphan.parent.mkdir(parents=True)
    orphan.write_text(_front_item("pending_whale"), encoding="utf-8")

    copied, updated, skipped = fss_replies.copy_archive_markdown(archive, dest, update_pending=True)
    assert copied == 0
    assert updated == 1
    assert "대상 대기" in (dest / "B0000133" / "11.md").read_text(encoding="utf-8")
    assert "소스 완료" in (dest / "B0000133" / "12.md").read_text(encoding="utf-8")
    assert "이미 ok" in (dest / "B0000133" / "13.md").read_text(encoding="utf-8")
    assert (dest / "B0000133" / "14.md").read_text(encoding="utf-8") == "프론트매터 없음\n"
    assert orphan.read_text(encoding="utf-8") == _front_item("pending_whale")

    code = export_fss_replies_raw.main(
        ["--archive", str(archive), "--dest", str(dest), "--update-pending"]
    )
    assert code == 0
    plain = export_fss_replies_raw.main(["--archive", str(archive), "--dest", str(dest)])
    assert plain == 0
    assert "이미 ok" in (dest / "B0000133" / "13.md").read_text(encoding="utf-8")


def test_extract_local_cli_does_not_crawl(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("crawl")

    monkeypatch.setattr(fss_replies, "crawl_archive", boom)
    monkeypatch.setattr(fss_replies, "make_session", boom)
    code = crawl_fss_replies.main(["--extract-local", "--archive", str(tmp_path)])
    assert code == 0
    code = crawl_fss_replies.main(
        ["--refresh-standards", "--from-extracted-body", "--archive", str(tmp_path)]
    )
    assert code == 0


def test_hwp5html_import_loads_six():
    completed = subprocess.run(
        [sys.executable, "-c", "from hwp5.hwp5html import main"],
        capture_output=True,
        text=True,
    )
    combined = completed.stderr + completed.stdout
    assert completed.returncode == 0
    assert "No module named 'six'" not in combined
    assert "No module named \"six\"" not in combined


def test_refresh_standards_normalizes_sme_labels_without_body(tmp_path):
    originals = {}
    for ntt_id, label in (
        ("43865", "중소기업회계처리 특례"),
        ("43469", "중소기업 회계처리 특례"),
        ("43236", "중소기업회계처리특례"),
    ):
        folder = _archive_item(
            tmp_path,
            board="B0000133",
            ntt_id=ntt_id,
            filename="note.hwp",
            standards=[label],
            title="특례 표기",
            notice="상세 안내는 그대로",
        )
        originals[ntt_id] = (folder / "item.md").read_text(encoding="utf-8")
    listed = _archive_item(
        tmp_path,
        board="B0000132",
        ntt_id="133043",
        filename="keep.hwp",
        standards=["K-IFRS 제1109호", "기업회계기준서 제1115호"],
        title="목록 기준서",
        notice="일반기업회계기준 제6장",
    )
    listed_text = (listed / "item.md").read_text(encoding="utf-8")

    result = fss_replies.refresh_standards(tmp_path)
    assert result["updated"] == 2
    assert result["unchanged"] == 2
    for ntt_id in ("43865", "43469", "43236"):
        text = (tmp_path / "B0000133" / ntt_id / "item.md").read_text(encoding="utf-8")
        meta = _meta(text)
        assert meta["standards"] == ["중소기업회계처리 특례"]
        assert meta["extract_status"] == "pending_whale"
        assert meta["fetched_at"] == "2026-11-12T09:00:00+09:00"
        assert text.split("---", 2)[2] == originals[ntt_id].split("---", 2)[2]
    assert (listed / "item.md").read_text(encoding="utf-8") == listed_text


def test_numbered_kifrs_drops_bare_label_from_body():
    found = fss_replies.infer_standards(
        "B0000133",
        "제목만 있는 질의",
        [],
        "(없음)",
        "공표된 K-IFRS 중 현행 K-IFRS 제1101호 문단 B2",
    )
    assert found == ["K-IFRS 제1101호"]
    korean = fss_replies.infer_standards(
        "B0000133",
        "제목",
        [],
        "한국채택국제회계기준을 참고",
        "한국채택국제회계기준 제1116호",
    )
    assert "한국채택국제회계기준 제1116호" in korean
    assert "한국채택국제회계기준" not in korean


def test_extract_failure_message_is_stable_and_omits_temp_paths(tmp_path):
    folder = _archive_item(
        tmp_path,
        board="B0000133",
        ntt_id="188484",
        filename="bad.hwp",
        standards=["일반기업회계기준"],
        title="변환에 실패하는 첨부",
        notice="상세 안내",
    )
    (folder / "bad.hwp").write_bytes(b"BAD")
    calls = {"n": 0}

    def fail(path, timeout=90):
        calls["n"] += 1
        raise fss_replies.HwpConvertError(
            "Traceback (most recent call last):\n"
            f'  File "/tmp/tmp{calls["n"]}abc/hwp5.xml", line 2, in transform\n'
            "    parser.feed(xml)\n"
            "lxml.etree.XMLSyntaxError: invalid character in attribute value, line 2, column 233548\n"
        )

    first = fss_replies.extract_local(tmp_path, hwp_to_html=fail)
    once = (folder / "item.md").read_bytes()
    second = fss_replies.extract_local(tmp_path, hwp_to_html=fail)
    assert first["failed"] == 1
    assert second["failed"] == 1
    assert calls["n"] == 2
    assert (folder / "item.md").read_bytes() == once
    text = once.decode("utf-8")
    assert "/tmp/tmp" not in text
    assert "Traceback" not in text
    assert "XMLSyntaxError: invalid character in attribute value, line 2, column 233548" in text
    assert _meta(text)["extract_status"] == "pending_whale"
    assert (folder / "bad.hwp").read_bytes() == b"BAD"


def _init_git(repo: Path) -> str:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    (repo / "README").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "README"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    completed = subprocess.run(
        ["git", "rev-parse", "--short=8", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def test_fss_sibling_rev_keeps_raw_and_is_idempotent(tmp_path, capsys):
    archive = tmp_path / "archive"
    folder = archive / "B0000132" / "189689"
    folder.mkdir(parents=True)
    (folder / "item.md").write_text("원문\n", encoding="utf-8")
    (folder / "note.hwp").write_bytes(b"bin")
    (archive / "manifest.jsonl").write_text('{"board": "B0000132"}\n', encoding="utf-8")
    dest = tmp_path / "raw"
    raw_dir = dest / "B0000132"
    raw_dir.mkdir(parents=True)
    (raw_dir / "189689.md").write_text("기존 raw\n", encoding="utf-8")
    (dest / "manifest.jsonl").write_text("기존 manifest\n", encoding="utf-8")
    args = ["--archive", str(archive), "--dest", str(dest), "--sibling-rev", "abc1234"]
    assert export_fss_replies_raw.main(args) == 0
    assert capsys.readouterr().out.strip() == "copied=2 updated=0 skipped=0"
    assert (raw_dir / "189689.md").read_text(encoding="utf-8") == "기존 raw\n"
    assert (dest / "manifest.jsonl").read_text(encoding="utf-8") == "기존 manifest\n"
    assert (raw_dir / "189689.abc1234.md").read_text(encoding="utf-8") == "원문\n"
    assert (dest / "manifest-abc1234.jsonl").read_text(encoding="utf-8") == '{"board": "B0000132"}\n'
    assert not (raw_dir / "note.hwp").exists()
    assert export_fss_replies_raw.main(args) == 0
    assert capsys.readouterr().out.strip() == "copied=0 updated=0 skipped=2"
    (folder / "item.md").write_text("새 원문\n", encoding="utf-8")
    assert export_fss_replies_raw.main(args) == 0
    assert capsys.readouterr().out.strip() == "copied=0 updated=1 skipped=1"
    assert (raw_dir / "189689.abc1234.md").read_text(encoding="utf-8") == "새 원문\n"
    assert (raw_dir / "189689.md").read_text(encoding="utf-8") == "기존 raw\n"
    assert (dest / "manifest.jsonl").read_text(encoding="utf-8") == "기존 manifest\n"


def test_fss_sibling_rev_rejects_invalid_update_pending_and_git_failure(tmp_path, capsys):
    with pytest.raises(SystemExit) as caught:
        export_fss_replies_raw.parse_args(["--sibling-rev", "bad rev", "--update-pending"])
    assert caught.value.code != 0
    with pytest.raises(SystemExit) as caught:
        export_fss_replies_raw.main(["--update-pending", "--sibling-rev", "abc1234"])
    assert caught.value.code != 0
    with pytest.raises(SystemExit) as caught:
        export_fss_replies_raw.parse_args(["--sibling-rev", "a/b"])
    assert caught.value.code != 0
    repo = tmp_path / "repo"
    repo.mkdir()
    sha = _init_git(repo)
    archive = repo / "archive"
    folder = archive / "B0000133" / "42"
    folder.mkdir(parents=True)
    (folder / "item.md").write_text("git 원문\n", encoding="utf-8")
    (archive / "manifest.jsonl").write_text("{}\n", encoding="utf-8")
    dest = tmp_path / "raw"
    assert export_fss_replies_raw.main(
        ["--archive", str(archive), "--dest", str(dest), "--sibling-rev"]
    ) == 0
    assert (dest / "B0000133" / f"42.{sha}.md").read_text(encoding="utf-8") == "git 원문\n"
    assert (dest / f"manifest-{sha}.jsonl").is_file()
    assert not (dest / "B0000133" / "42.md").exists()
    capsys.readouterr()
    missing = tmp_path / "no-git"
    missing.mkdir()
    outside = tmp_path / "outside"
    assert export_fss_replies_raw.main(
        ["--archive", str(missing), "--dest", str(outside), "--sibling-rev"]
    ) == 1
    assert capsys.readouterr().err.strip()
    assert not outside.exists() or not list(outside.rglob("*"))
