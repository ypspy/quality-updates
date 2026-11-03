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
