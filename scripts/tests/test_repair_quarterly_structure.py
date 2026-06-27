# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from repair_quarterly_structure import classify_url, rebuild_main_body


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
