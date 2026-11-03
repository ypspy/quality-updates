# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler import kasb_replies

LIST_HTML = """
<table>
<tbody>
<tr>
  <td>공지</td><td></td>
  <td><a onclick="javascript:fn_Detail('40533','016009');">비교표</a></td>
  <td><a onclick="javascript:fileDownload('-49990797','1'); return false;">compare.xlsx</a></td>
  <td></td><td></td>
</tr>
<tr>
  <td>2193</td><td>정착지원TF</td>
  <td><a onclick="javascript:fn_Detail('40689','016008');">제1118호 정착지원 TF 논의 내용(5차)</a></td>
  <td><a onclick="javascript:fileDownload('-49993299','1'); return false;">261016_note.hwpx</a></td>
  <td>2026-10-16</td><td></td>
</tr>
<tr>
  <td>1</td><td>없음</td><td><span>링크 없음</span></td><td></td><td></td><td></td>
</tr>
</tbody>
</table>
<div class="paging_wrap">
  <li class="pag_last"><a href="javascript:G_MovePage(220);">Last</a></li>
</div>
"""


def test_parse_list_page_reads_notice_and_item():
    rows = kasb_replies.parse_list_page(LIST_HTML)
    assert len(rows) == 2
    notice, item = rows
    assert notice.seq == "40533"
    assert notice.ctg_cd == "016009"
    assert notice.number == "공지"
    assert notice.reply_date is None
    assert notice.attachments[0].file_no == "-49990797"
    assert notice.attachments[0].name == "compare.xlsx"
    assert item.seq == "40689"
    assert item.ctg_cd == "016008"
    assert item.number == "2193"
    assert item.category == "정착지원TF"
    assert item.title == "제1118호 정착지원 TF 논의 내용(5차)"
    assert item.reply_date == "2026-10-16"
    assert item.published_date is None
    assert item.attachments[0].file_seq == "1"


def test_last_page_number_and_default():
    assert kasb_replies.last_page_number(LIST_HTML) == 220
    assert kasb_replies.last_page_number("<table></table>") == 1


def test_dedupe_rows_keeps_first_seq():
    rows = kasb_replies.parse_list_page(LIST_HTML)
    merged = kasb_replies.dedupe_rows(rows + rows)
    assert [row.seq for row in merged] == ["40533", "40689"]


DETAIL_HTML = """
<nav>주메뉴로 가기</nav>
<div class="board_view_wrap">
  <table>
    <tr><th>분류</th><td class="left">정착지원TF</td></tr>
    <tr>
      <th>관련기준서</th>
      <td>
        <table>
          <tr><th>기준서 구분</th><td>제1118호 재무제표 표시와 공시</td></tr>
          <tr><th>기준서 명</th><td></td></tr>
        </table>
      </td>
    </tr>
    <tr><th>등록일</th><td><p class="board_date">2026-10-16</p></td></tr>
    <tr>
      <th>첨부파일</th>
      <td>
        <a onclick="javascript:fileDownload('-49993299','1'); return false;"><span>261016_note.hwpx</span></a>
        <a onclick="javascript:fn_fileViewer('abc');">미리보기</a>
      </td>
    </tr>
  </table>
  <div class="board_view_cont"><p>※ 본 자료는 참고 목적으로 정리한 것입니다.</p></div>
</div>
"""


def test_parse_detail_page_reads_standards_and_notice():
    detail = kasb_replies.parse_detail_page(DETAIL_HTML)
    assert detail.category == "정착지원TF"
    assert detail.standards == ("제1118호 재무제표 표시와 공시",)
    assert detail.registered_date == "2026-10-16"
    assert detail.notice == "※ 본 자료는 참고 목적으로 정리한 것입니다."
    assert "주메뉴로 가기" not in detail.notice
    assert len(detail.attachments) == 1
    assert detail.attachments[0].name == "261016_note.hwpx"
    assert detail.attachments[0].file_no == "-49993299"


def test_parse_detail_page_joins_standard_code_and_name():
    html = """
    <div class="board_view_wrap">
      <table>
        <tr>
          <th>관련기준서</th>
          <td>
            <table>
              <tr><th>기준서 구분</th><td>제1118호</td></tr>
              <tr><th>기준서 명</th><td>재무제표 표시와 공시</td></tr>
            </table>
          </td>
        </tr>
      </table>
    </div>
    """
    detail = kasb_replies.parse_detail_page(html)
    assert detail.standards == ("제1118호 재무제표 표시와 공시",)


def test_parse_detail_page_standards_direct_text_without_inner_table():
    html = """
    <div class="board_view_wrap">
      <table>
        <tr><th>관련기준서</th><td>제1001호 재무제표 표시</td></tr>
      </table>
    </div>
    """
    detail = kasb_replies.parse_detail_page(html)
    assert detail.standards == ("제1001호 재무제표 표시",)


def test_parse_detail_page_multiple_standards_from_separate_rows():
    html = """
    <div class="board_view_wrap">
      <table>
        <tr>
          <th>관련기준서</th>
          <td>
            <table>
              <tr><th>기준서 구분</th><td>제1118호</td></tr>
              <tr><th>기준서 명</th><td></td></tr>
              <tr><th>기준서 구분</th><td>제1001호</td></tr>
              <tr><th>기준서 명</th><td></td></tr>
            </table>
          </td>
        </tr>
      </table>
    </div>
    """
    detail = kasb_replies.parse_detail_page(html)
    assert detail.standards == ("제1118호", "제1001호")


import io
import struct
import zipfile

import pytest


def _hello_pdf() -> bytes:
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 55>>stream
BT /F1 12 Tf 20 100 Td (Hello Reply) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000101 00000 n 
0000000208 00000 n 
0000000313 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
382
%%EOF
"""


def _empty_pdf() -> bytes:
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R>>endobj
4 0 obj<</Length 0>>stream
endstream
endobj
trailer<</Size 5/Root 1 0 R>>
startxref
230
%%EOF
"""


def _hwpx(inner: str) -> bytes:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        f"<hp:p><hp:run><hp:t>{inner}</hp:t></hp:run></hp:p></hp:sec>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Contents/header.xml", "<hp:t>헤더</hp:t>")
        zf.writestr("Contents/section0.xml", xml)
    return buf.getvalue()


def _xlsx() -> bytes:
    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.title = "비교"
    sheet.append(["항목", "값"])
    sheet.append(["면제", "a|b"])
    buf = io.BytesIO()
    book.save(buf)
    return buf.getvalue()


def _empty_xlsx() -> bytes:
    from openpyxl import Workbook

    book = Workbook()
    buf = io.BytesIO()
    book.save(buf)
    return buf.getvalue()


def _ole_dir(name: str, typ: int, child: int, start: int, size: int) -> bytes:
    raw = name.encode("utf-16-le")
    buf = bytearray(128)
    buf[0 : len(raw)] = raw
    struct.pack_into("<H", buf, 0x40, len(raw) + 2)
    buf[0x42] = typ
    buf[0x43] = 1
    struct.pack_into("<III", buf, 0x44, 0xFFFFFFFF, 0xFFFFFFFF, child)
    struct.pack_into("<I", buf, 0x74, start)
    struct.pack_into("<I", buf, 0x78, size)
    return bytes(buf)


def _ole_with_stream(stream_name: str, data: bytes) -> bytes:
    if len(data) > 64:
        raise ValueError("fixture stream must fit in one mini sector")
    directory = _ole_dir("Root Entry", 5, 1, 3, 64) + _ole_dir(
        stream_name, 2, 0xFFFFFFFF, 0, len(data)
    )
    directory += bytes(256)
    fat = struct.pack("<IIII", 0xFFFFFFFD, 0xFFFFFFFE, 0xFFFFFFFE, 0xFFFFFFFE) + (b"\xff" * 4) * 124
    minifat = struct.pack("<I", 0xFFFFFFFE) + (b"\xff" * 4) * 127
    header = bytearray(512)
    header[0:8] = bytes.fromhex("D0CF11E0A1B11AE1")
    struct.pack_into("<H", header, 0x18, 0x003E)
    struct.pack_into("<H", header, 0x1A, 3)
    struct.pack_into("<H", header, 0x1C, 0xFFFE)
    struct.pack_into("<H", header, 0x1E, 9)
    struct.pack_into("<H", header, 0x20, 6)
    struct.pack_into("<I", header, 0x2C, 1)
    struct.pack_into("<I", header, 0x30, 1)
    struct.pack_into("<I", header, 0x38, 0x1000)
    struct.pack_into("<I", header, 0x3C, 2)
    struct.pack_into("<I", header, 0x40, 1)
    struct.pack_into("<I", header, 0x44, 0xFFFFFFFE)
    struct.pack_into("<I", header, 0x48, 0)
    struct.pack_into("<I", header, 0x4C, 0)
    mini = data + b"\x00" * (512 - len(data))
    return bytes(header) + fat + directory + minifat + mini


def _ole_with_prvtext(text: str) -> bytes:
    data = text.encode("utf-16-le")
    return _ole_with_stream("PrvText", data)


def test_extract_pdf_hwpx_and_xlsx():
    text, status = kasb_replies.extract_bytes("a.pdf", _hello_pdf())
    assert status == "ok"
    assert "Hello Reply" in text
    text, status = kasb_replies.extract_bytes("empty.pdf", _empty_pdf())
    assert status == "empty"
    text, status = kasb_replies.extract_bytes("a.hwpx", _hwpx("회신 문장"))
    assert status == "ok"
    assert "회신 문장" in text
    assert "헤더" not in text
    text, status = kasb_replies.extract_bytes("a.xlsx", _xlsx())
    assert status == "ok"
    assert "### 비교" in text
    assert "a\\|b" in text
    text, status = kasb_replies.extract_bytes("empty.xlsx", _empty_xlsx())
    assert status == "empty"


def test_extract_hwp_preview_and_garbage():
    text, status = kasb_replies.extract_bytes("a.hwp", _ole_with_prvtext("회신결론"))
    assert status == "partial"
    assert "회신결론" in text
    text, status = kasb_replies.extract_bytes("a.hwp", b"not-ole")
    assert status == "failed"
    text, status = kasb_replies.extract_bytes("a.zip", b"PK")
    assert status == "failed"


def test_extract_hwp_fails_without_prvtext_stream():
    _, status = kasb_replies.extract_bytes(
        "a.hwp", _ole_with_stream("OtherStream", b"\xff\xfe")
    )
    assert status == "failed"


def test_extract_hwp_fails_on_invalid_utf16_prvtext():
    _, status = kasb_replies.extract_bytes("a.hwp", _ole_with_stream("PrvText", b"\xff"))
    assert status == "failed"


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([], "empty"),
        (["ok", "ok"], "ok"),
        (["partial", "ok"], "partial"),
        (["failed", "ok"], "failed"),
        (["empty", "empty"], "empty"),
        (["ok", "empty"], "partial"),
    ],
)
def test_aggregate_status(statuses, expected):
    assert kasb_replies.aggregate_status(statuses) == expected


import json

import yaml


def _sample_row():
    return kasb_replies.ListRow(
        seq="40689",
        ctg_cd="016008",
        number="2193",
        category="",
        title="제목",
        reply_date=None,
        published_date=None,
        attachments=(),
    )


def _sample_detail():
    return kasb_replies.DetailPage(
        category="정착지원TF",
        standards=("제1118호 재무제표 표시와 공시",),
        registered_date="2026-10-16",
        notice="",
        attachments=(kasb_replies.AttachmentRef("note.hwpx", "-49993299", "1"),),
    )


def test_attachment_filename_strips_directories_and_dedupes():
    used = set()
    assert kasb_replies.attachment_filename(r"..\a\note.hwpx", "1", used) == "note.hwpx"
    assert kasb_replies.attachment_filename("note.hwpx", "2", used) == "note-2.hwpx"


def test_compose_item_uses_detail_category_and_registered_date():
    text = kasb_replies.compose_item(
        _sample_row(),
        _sample_detail(),
        [("note.hwpx", "본문", "ok")],
        "2026-11-04T07:00:00+09:00",
    )
    meta, body = text.split("---", 2)[1:]
    loaded = yaml.safe_load(meta)
    assert loaded["seq"] == "40689"
    assert loaded["category"] == "정착지원TF"
    assert loaded["reply_date"] == "2026-10-16"
    assert loaded["published_date"] is None
    assert loaded["standards"] == ["제1118호 재무제표 표시와 공시"]
    assert loaded["extract_status"] == "ok"
    assert loaded["attachments"][0]["file_no"] == "-49993299"
    assert loaded["attachments"][0]["extract_status"] == "ok"
    assert "## 상세 안내" in body
    assert "(없음)" in body
    assert "## 첨부: note.hwpx" in body
    assert "본문" in body


def test_compose_item_writes_failed_attachment_line():
    text = kasb_replies.compose_item(
        _sample_row(),
        _sample_detail(),
        [("note.hwpx", "PrvText missing", "failed")],
        "2026-11-04T07:00:00+09:00",
    )
    assert "failed: PrvText missing" in text
    assert yaml.safe_load(text.split("---", 2)[1])["extract_status"] == "failed"


def test_should_attempt_and_manifest(tmp_path):
    directory = tmp_path / "40689"
    directory.mkdir()
    assert kasb_replies.should_attempt(directory, retry_failed=False) is True
    (directory / "note.hwpx").write_bytes(b"x")
    item = kasb_replies.compose_item(
        _sample_row(),
        _sample_detail(),
        [("note.hwpx", "본문", "ok")],
        "2026-11-04T07:00:00+09:00",
    )
    (directory / "item.md").write_text(item, encoding="utf-8")
    assert kasb_replies.should_attempt(directory, retry_failed=True) is False
    (directory / "note.hwpx").unlink()
    assert kasb_replies.should_attempt(directory, retry_failed=False) is True
    partial = kasb_replies.compose_item(
        _sample_row(),
        _sample_detail(),
        [("note.hwpx", "미리보기", "partial")],
        "2026-11-04T07:00:00+09:00",
    )
    (directory / "item.md").write_text(partial, encoding="utf-8")
    (directory / "note.hwpx").write_bytes(b"x")
    assert kasb_replies.should_attempt(directory, retry_failed=False) is False
    assert kasb_replies.should_attempt(directory, retry_failed=True) is True
    manifest = tmp_path / "manifest.jsonl"
    kasb_replies.append_manifest(
        manifest,
        {
            "seq": "40689",
            "ctg_cd": "016008",
            "number": "2193",
            "category": "정착지원TF",
            "title": "제목",
            "reply_date": "2026-10-16",
            "published_date": None,
            "extract_status": "ok",
            "path": "40689/item.md",
            "error": None,
        },
    )
    record = json.loads(manifest.read_text(encoding="utf-8").splitlines()[-1])
    assert record["path"] == "40689/item.md"
    assert record["error"] is None
