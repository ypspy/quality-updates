# -*- coding: utf-8 -*-
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler import FSS

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "fss_press_list_krds.html"


def test_parse_press_list_html_extracts_krds_rows():
    html = FIXTURE.read_text(encoding="utf-8")
    items = FSS.parse_press_list_html(html)
    assert len(items) == 2
    assert items[0]["title"] == "공모 목표전환형 펀드 현황 및 투자자 유의사항 안내"
    assert "B0000188/view.do" in items[0]["href"]
    assert "nttId=227554" in items[0]["href"]
    assert items[0]["posted_on"] == datetime(2026, 9, 9)
    assert items[1]["title"] == "2026년 8월 가계대출 동향(잠정) 및 가계부채 점검회의 개최"
    assert "nttId=227555" in items[1]["href"]
    assert items[1]["posted_on"] == datetime(2026, 9, 8)


def test_parse_press_list_html_empty_tbody():
    assert FSS.parse_press_list_html("<table><tbody></tbody></table>") == []
    assert FSS.parse_press_list_html("<div></div>") == []


def test_parse_press_list_html_finds_rows_without_bd_list():
    html = FIXTURE.read_text(encoding="utf-8")
    assert "bd-list" not in html
    items = FSS.parse_press_list_html(html)
    assert len(items) == 2


def test_parse_press_list_html_skips_invalid_rows():
    html = """
    <table><tbody>
      <tr><td class="num">1</td><td>제목없음</td><td>부서</td><td>2026-09-09</td></tr>
      <tr>
        <td class="num">2</td>
        <td class="title"><a href="/fss/bbs/B0000188/view.do?nttId=1">유효</a></td>
        <td>부서</td>
        <td>not-a-date</td>
      </tr>
      <tr>
        <td class="num">3</td>
        <td class="title"><a href="/fss/bbs/B0000188/view.do?nttId=2">정상</a></td>
        <td>부서</td>
        <td>2026-09-01</td>
      </tr>
    </tbody></table>
    """
    items = FSS.parse_press_list_html(html)
    assert len(items) == 1
    assert items[0]["title"] == "정상"
    assert items[0]["posted_on"] == datetime(2026, 9, 1)


def test_fetch_press_release_uses_krds_parser(monkeypatch):
    html = FIXTURE.read_text(encoding="utf-8")
    empty = "<table><tbody></tbody></table>"

    def fake_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.text = html if (params or {}).get("pageIndex") == 1 else empty
        return resp

    monkeypatch.setattr(FSS, "START_DATE", "2026-09-01")
    monkeypatch.setattr(FSS, "END_DATE", "2026-09-30")
    monkeypatch.setattr(FSS, "start_dt", datetime(2026, 9, 1))
    monkeypatch.setattr(FSS.session, "get", fake_get)

    items = FSS.fetch_press_release(max_page=3)
    assert len(items) == 2
    assert items[0]["date"] == "26-09-09"
    assert items[0]["title"] == "공모 목표전환형 펀드 현황 및 투자자 유의사항 안내"
    assert items[0]["link"].startswith("https://www.fss.or.kr/")
    assert "nttId=227554" in items[0]["link"]
    assert items[1]["date"] == "26-09-08"
    assert "nttId=227555" in items[1]["link"]


def test_fetch_press_release_stops_before_start_dt(monkeypatch):
    html = FIXTURE.read_text(encoding="utf-8")

    def fake_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.text = html
        return resp

    monkeypatch.setattr(FSS, "START_DATE", "2026-09-09")
    monkeypatch.setattr(FSS, "END_DATE", "2026-09-30")
    monkeypatch.setattr(FSS, "start_dt", datetime(2026, 9, 9))
    monkeypatch.setattr(FSS.session, "get", fake_get)

    items = FSS.fetch_press_release(max_page=1)
    assert len(items) == 1
    assert items[0]["date"] == "26-09-09"
