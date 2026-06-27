# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler import KASB

SCHEDULE_HTML = """
<table>
<tbody>
<tr>
  <td>2026-03-31</td><td>공통</td><td>세미나</td>
  <td><a href="#" onclick="javascript:fn_Detail('1111');">지속가능성 공시기준 이행지원 세미나</a></td>
  <td>한국거래소</td>
</tr>
<tr>
  <td>2026-01-16</td><td>회계기준</td><td>회계기준위원회</td>
  <td><a href="#" onclick="javascript:fn_Detail('1105');">2026년 제1회 회계기준위원회</a></td>
  <td>BM Room</td>
</tr>
<tr>
  <td>2026-01-16</td><td>회계기준</td><td>회계기준위원회</td>
  <td><span>링크 없음</span></td>
  <td>BM Room</td>
</tr>
</tbody>
</table>
"""


def test_parse_schedule_page_extracts_rows():
    items = KASB.parse_schedule_page(SCHEDULE_HTML)
    assert len(items) == 2
    assert items[0] == (
        "26-03-31",
        "지속가능성 공시기준 이행지원 세미나",
        "https://www.kasb.or.kr/front/board/calView.do?seq=1111",
    )
    assert items[1] == (
        "26-01-16",
        "2026년 제1회 회계기준위원회",
        "https://www.kasb.or.kr/front/board/calView.do?seq=1105",
    )


def test_parse_schedule_page_empty_table():
    assert KASB.parse_schedule_page("<table><tbody></tbody></table>") == []


def test_crawl_schedule_sorts_ascending():
    session = MagicMock()
    session.headers.update = MagicMock()
    session.get = MagicMock()

    pages = [
        SCHEDULE_HTML,
        "<table><tbody></tbody></table>",
    ]

    with patch("crawler.KASB.requests.Session", return_value=session):
        with patch("crawler.KASB.fetch_page", side_effect=pages):
            items = KASB.crawl_schedule("2026-01-01", "2026-03-31")

    assert [t[0] for t in items] == ["26-01-16", "26-03-31"]
