# -*- coding: utf-8 -*-
"""Curation suggestions match editor markers and the published backtest."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auto_curate import (  # noqa: E402
    HOLDOUT_NAME,
    Item,
    decide_all,
    decide_one,
    label_collected,
    run_backtest,
    score_labeled,
)
from editor.parser import parse_links  # noqa: E402
from editor.saver import apply_curation  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
QUARTERS = ROOT / "docs" / "quality-updates"
REPORT = ROOT / "docs" / "project" / "curation-backtest.md"


def _item(title, agency="금융감독원", section="보도자료", date="26-04-02", url="https://www.fss.or.kr/a"):
    return Item(date=date, title=title, url=url, agency=agency, section=section)


def test_skip_marker_matches_editor_saver():
    decision = decide_one(_item("2025년 9월중 가계대출 동향"))
    assert decision.state == "skip"
    assert decision.marker() == "<!-- skip -->"
    updated = apply_curation(
        "- (26-04-02) [가계대출](https://www.fss.or.kr/a)\n",
        [{"line_index": 0, "state": "skip", "title": "가계대출"}],
    )
    assert decision.marker() in updated
    assert parse_links(updated)[0]["state"] == "skip"


def test_summary_marker_matches_editor_saver():
    decision = decide_one(_item("내부회계관리제도 관련 법규위반 사례 및 유의사항 안내"))
    assert decision.state == "needs_summary"
    assert decision.source_type == "pdf"
    assert decision.marker() == "<!-- source: pdf|pending -->"
    updated = apply_curation(
        "- (26-04-02) [T](https://www.fss.or.kr/a)\n",
        [{
            "line_index": 0,
            "state": "needs_summary",
            "title": "T",
            "source": {"type": decision.source_type, "ref": decision.source_ref},
        }],
    )
    assert decision.marker() in updated
    parsed = parse_links(updated)[0]
    assert parsed["state"] == "needs_summary"
    assert parsed["source"]["type"] == "pdf"
    assert parsed["source"]["ref"] == "pending"


def test_fss_enforcement_is_link_only_and_fsc_is_summary():
    title = "사업보고서 등에 대한 조사·감리결과 조치 - 제6차 금융위원회 조치 의결"
    fss = decide_one(_item(title, agency="금융감독원"))
    fsc = decide_one(_item(
        title,
        agency="금융위원회",
        url="https://fsc.go.kr/no010101/1",
    ))
    assert fss.state == "no_summary"
    assert fss.marker() == "<!-- no_summary -->"
    assert fsc.state == "needs_summary"
    assert fsc.rule_id == "R4-enforcement-fsc"


def test_unfair_trading_enforcement_is_not_treated_as_accounting_review():
    decision = decide_one(_item(
        "불공정거래 조사·심리기관 협의회 개최",
        agency="금융위원회",
        url="https://fsc.go.kr/no010101/2",
    ))
    assert decision.state == "skip"


def test_exam_and_newsletter_stay_as_links():
    exam = decide_one(_item("2026년도 제61회 공인회계사 제1차 시험 합격자 발표"))
    letter = decide_one(_item("회계뉴스레터(2025년 제4호)", section="회계감독 동향자료"))
    assert exam.state == "no_summary"
    assert letter.state == "no_summary"
    assert letter.marker() == "<!-- no_summary -->"


def test_institution_name_is_not_an_accounting_keyword():
    decision = decide_one(_item(
        "한국회계기준원 홈페이지 서버 임시 점검 안내",
        agency="한국회계기준원",
        section="소통광장 - 공지사항",
        url="https://www.kasb.or.kr/front/board/comm.do?seq=1",
    ))
    assert decision.state == "skip"


def test_kicpa_recruitment_and_standards():
    recruit = decide_one(_item(
        "[파주시] 파주희망프로젝트 제안서 평가위원 공개모집 안내",
        agency="한국공인회계사회",
        section="알림마당 - 공지사항",
        url="https://www.kicpa.or.kr/board/read.brd?bltnNo=1",
    ))
    standard = decide_one(_item(
        "회계감사기준 개정(2025) 안내",
        agency="한국공인회계사회",
        section="회계감사 - 감사인증기준",
        url="https://www.kicpa.or.kr/kicpa/sumBoard/detail.face?bltnNo=2",
    ))
    assert recruit.state == "skip"
    assert recruit.rule_id == "R9-recruitment"
    assert standard.state == "needs_summary"
    assert standard.source_type == "shot"
    assert standard.marker() == "<!-- source: shot|pending -->"


def test_kasb_meeting_and_sustainability_schedule():
    meeting = decide_one(_item(
        "2026년 제4회 회계기준위원회(K-IFRS 제1118호 제정안)",
        agency="한국회계기준원",
        section="주요일정",
        url="https://www.kasb.or.kr/front/board/calView.do?seq=9",
    ))
    kssb = decide_one(_item(
        "2026년 제4회 지속가능성기준위원회(ISSB 논의)",
        agency="한국회계기준원",
        section="주요일정",
        url="https://www.kasb.or.kr/front/board/calView.do?seq=10",
    ))
    assert meeting.state == "needs_summary"
    assert meeting.source_type == "clip"
    assert kssb.state == "skip"


def test_fss_duplicate_demoted_when_fsc_is_summarized():
    fss = _item("K-IFRS 제1118호 영향 관련 사전 주석공시 모범사례 마련")
    fsc = _item(
        "K-IFRS 제1118호 영향 관련 사전 주석공시 모범사례 마련",
        agency="금융위원회",
        url="https://fsc.go.kr/no010101/3",
    )
    decisions = decide_all([fss, fsc])
    assert decisions[0].state == "no_summary"
    assert decisions[0].rule_id == "R13-fss-duplicate"
    assert decisions[1].state == "needs_summary"


def test_legislation_scope():
    keep = decide_one(_item(
        "「주식회사 등의 외부감사에 관한 법률 시행령」 일부개정령안 입법예고",
        agency="금융위원회",
        section="입법예고/규정변경예고",
        url="https://fsc.go.kr/po040301/view?noticeId=1",
    ))
    drop = decide_one(_item(
        "보험업법 시행령 일부개정령안 입법예고",
        agency="금융위원회",
        section="입법예고/규정변경예고",
        url="https://fsc.go.kr/po040301/view?noticeId=2",
    ))
    assert keep.state == "needs_summary"
    assert drop.state == "skip"


def test_reconstructed_skip_and_summary_scores():
    text = """### 금융감독원

#### 보도자료

- (26-01-02) [내부회계관리제도 유의사항 안내](https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=10)

    !!! note "주요 내용"

        - 내용

## Appendix A. Complete List of Retrieved Items (Unfiltered)

??? info "금융감독원"

    **보도자료**

    - (26-01-02) [내부회계관리제도 유의사항 안내](https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=10)
    - (26-01-03) [가계대출 동향](https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=11)
"""
    labeled, manual = label_collected(text)
    assert manual == []
    assert [row.actual for row in labeled] == ["summarize", "skip"]
    scored = score_labeled(labeled)
    assert [(row.actual, row.predicted) for row in scored] == [
        ("summarize", "summarize"),
        ("skip", "skip"),
    ]


def test_holdout_agreement_and_committed_report():
    holdout = QUARTERS / "2026" / HOLDOUT_NAME
    if not holdout.exists():
        pytest.skip("holdout quarter is not in the tree")
    payload = run_backtest(QUARTERS, HOLDOUT_NAME)
    metrics = payload["metrics"]["holdout"]
    assert metrics["skip_precision"] >= 0.98
    assert metrics["skip_recall"] >= 0.97
    assert metrics["three_way_accuracy"] >= 0.96
    assert metrics["source_type_n"] > 0
    text = REPORT.read_text(encoding="utf-8")
    assert "99.1%" in text
    assert "98.0%" in text
    assert "97.0%" in text
    assert "52.4%" in text
    assert HOLDOUT_NAME in text
