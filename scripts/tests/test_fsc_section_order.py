import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler.unified import FSC_MAIN_HEADINGS
from repair_quarterly_structure import SECTIONS


def test_fsc_headings_match_repair_sections():
    repair = dict(SECTIONS)["금융위원회"]
    assert FSC_MAIN_HEADINGS == repair
    assert FSC_MAIN_HEADINGS.index("보도자료") < FSC_MAIN_HEADINGS.index("제재 의결")
    assert FSC_MAIN_HEADINGS.index("제재 의결") < FSC_MAIN_HEADINGS.index("고시/공고/훈령")


from crawler.unified import render_fsc_press

SANCTION = "- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회(’26.7.8.) 조치 의결](https://fsc.go.kr/no010101/87293)"
UNFAIR = "- (26-09-02) [상장사 IR 담당 임원의 불공정거래 혐의 적발·조치 - 제15차 증권선물위원회(9.2.) 의결](https://fsc.go.kr/no010101/87638)"
CARD = "- (26-07-31) [롯데카드(주)의 정보유출 관련 1.5개월 업무정지 및 50억원 과징금 부과 - 제14차 금융위원회(’26.7.31.) 조치 의결](https://fsc.go.kr/no010101/87455)"
NO_NUMBER = "- (26-07-23) [사업보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/87394)"


def test_split_fsc_press_puts_investigation_titles_under_sanctions():
    rendered = render_fsc_press([SANCTION, UNFAIR, CARD, NO_NUMBER])
    sanction_at = rendered.index("#### 제재 의결")
    press_at = rendered.index("#### 보도자료")
    assert press_at < sanction_at
    assert rendered.index(SANCTION) > sanction_at
    assert rendered.index(NO_NUMBER) > sanction_at
    assert rendered.index(UNFAIR) < sanction_at
    assert rendered.index(CARD) < sanction_at


def test_sanction_heading_remains_when_no_title_matches():
    rendered = render_fsc_press([UNFAIR])
    assert "#### 제재 의결" in rendered
    assert rendered.index(UNFAIR) < rendered.index("#### 제재 의결")
