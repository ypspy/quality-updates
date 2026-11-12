# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from repair_quarterly_structure import classify_block, classify_url, rebuild_main_body, repair_file


def test_classify_fsc_subsections():
    assert classify_url("https://fsc.go.kr/no010101/1")[1] == "보도자료"
    assert classify_url("https://fsc.go.kr/po040200/1")[1] == "고시/공고/훈령"
    assert classify_url("https://fsc.go.kr./po040301/view?noticeId=1")[1] == "입법예고/규정변경예고"


def test_rebuild_restores_agency_headers():
    blocks = [
        ((2026, 3, 31), "https://fsc.go.kr/no010101/1", "- (26-03-31) [a](https://fsc.go.kr/no010101/1)"),
        ((2026, 1, 8), "https://fss.or.kr/fss/bbs/B0000188/view.do?nttId=1", "- (26-01-08) [b](https://fss.or.kr/fss/bbs/B0000188/view.do?nttId=1)"),
        ((2026, 2, 1), "https://fsc.go.kr/po040200/2", "- (26-02-01) [c](https://fsc.go.kr/po040200/2)"),
    ]
    body = rebuild_main_body(blocks)
    assert "### 금융감독원" in body
    assert "### 금융위원회" in body
    assert "#### 보도자료" in body
    assert "#### 고시/공고/훈령" in body
    assert body.index("### 금융감독원") < body.index("### 금융위원회")


def test_sanction_title_goes_to_resolution_section():
    url = "https://fsc.go.kr/no010101/87293"
    title = "사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회"
    assert classify_url(url, title) == ("금융위원회", "제재 의결")


def test_unfair_trade_title_stays_in_press():
    url = "https://fsc.go.kr/no010101/9"
    assert classify_url(url, "불공정거래 조치")[1] == "보도자료"
    assert classify_url(url, "불공정거래 심사·조사결과 조치")[1] == "보도자료"


def test_fsc_audit_action_titles_are_sanctions():
    url = "https://fsc.go.kr/no010101/50"
    titles = [
        "감사인에 대한 감리결과 조치",
        "심사‧조사결과 조치",
        "심사·조사결과 조치",
        "심사, 조사결과 조치",
        "심사ㆍ조사결과 조치",
        "외부감사법 위반 등에 대한 감리결과 조치",
    ]
    for title in titles:
        assert classify_url(url, title) == ("금융위원회", "제재 의결")
        block = f"- (26-03-01) [{title}]({url})\n\n    본문"
        assert classify_block(url, block) == ("금융위원회", "제재 의결")


def test_fss_link_is_not_moved_to_sanctions():
    url = "https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=9"
    assert classify_url(url, "감사인에 대한 감리결과 조치") == ("금융감독원", "보도자료")
    assert classify_block(url, f"- (26-03-01) [심사·조사결과 조치]({url})")[1] != "제재 의결"


def test_rebuild_keeps_discussion_note_under_resolution():
    block = "\n".join([
        "- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/87293)",
        "",
        "    !!! note \"위원 논의\"",
        "",
        "        - (의결) 수정의결함",
    ])
    body = rebuild_main_body([((2026, 7, 9), "https://fsc.go.kr/no010101/87293", block)])
    assert body.index("#### 제재 의결") < body.index("수정의결함")
    assert "#### 보도자료" not in body


QUARTER = """---
title: t
---

### 금융위원회

#### 보도자료

- (26-01-02) [일반 보도](https://fsc.go.kr/no010101/9)

#### 제재 의결

- (26-03-11) [감사보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/1)

##### 미보도

- 제5차 증권선물위원회(2026.3.11.) 의결 66. 예시

    <!-- source: pdf|downloads/sanctions/2026-증선위-5차/decision/staff.pdf -->

#### 고시/공고/훈령

- (26-03-12) [고시](https://fsc.go.kr/po040200/2)
"""


def test_repair_keeps_unpublished_after_resolution_items(tmp_path):
    path = tmp_path / "quarter.md"
    path.write_text(QUARTER, encoding="utf-8", newline="\n")
    repair_file(path)
    text = path.read_text(encoding="utf-8")
    assert text.index("#### 제재 의결") < text.index("##### 미보도")
    assert text.index("##### 미보도") < text.index("staff.pdf")
    assert text.index("staff.pdf") < text.index("#### 고시/공고/훈령")
    assert text.index("- (26-03-11)") < text.index("##### 미보도")


def test_repair_keeps_unpublished_bullet_without_heading(tmp_path):
    source = QUARTER.replace(
        "##### 미보도\n\n- 제5차 증권선물위원회(2026.3.11.) 의결 66. 예시",
        "- 분기중 미보도 항목",
    )
    path = tmp_path / "quarter.md"
    path.write_text(source, encoding="utf-8", newline="\n")
    repair_file(path)
    text = path.read_text(encoding="utf-8")
    assert "##### 미보도" not in text
    assert text.index("#### 제재 의결") < text.index("- 분기중 미보도 항목")
    assert text.index("- 분기중 미보도 항목") < text.index("staff.pdf")
    assert text.index("staff.pdf") < text.index("#### 고시/공고/훈령")
    assert text.index("- (26-03-11)") < text.index("- 분기중 미보도 항목")


def test_repair_keeps_unpublished_when_resolution_has_no_dated_link(tmp_path):
    source = QUARTER.replace(
        "- (26-03-11) [감사보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/1)\n\n",
        "",
    )
    path = tmp_path / "quarter.md"
    path.write_text(source, encoding="utf-8", newline="\n")
    repair_file(path)
    text = path.read_text(encoding="utf-8")
    assert "#### 제재 의결" in text
    assert text.index("#### 제재 의결") < text.index("##### 미보도")
    assert "staff.pdf" in text
    assert text.index("staff.pdf") < text.index("#### 고시/공고/훈령")
