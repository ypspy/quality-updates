# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fss_review_cards import (  # noqa: E402
    BOILERPLATE,
    arrange_by_year,
    audit_review_html,
    collapse_document,
    place_labels,
    repair_severity_gap,
)

BODY = (
    '<p class="fss-finding"><span class="fss-sev fss-sev-part">일부미흡</span>품질성과급 비중이 낮습니다.</p>'
)
OTHER = (
    '<p class="fss-finding"><span class="fss-sev fss-sev-off">일부미운영</span>특수관계자 급여를 성과평가 없이 정합니다.</p>'
)


def _article(names, summary, bodies):
    badges = []
    for name, body in zip(names, bodies):
        badges.append(
            f'<button type="button" class="fss-badge" data-names="{name}">{name}</button>'
            f'<div class="fss-original" hidden data-names="{name}">{body}</div>'
        )
    joined = "|".join(names)
    summary_html = f'<p class="fss-summary">{summary}</p>' if summary else ""
    return (
        f'<article class="fss-group" data-names="{joined}">'
        f'<p class="fss-group-name">평가 결과와 보상</p>'
        f"{summary_html}"
        f'<div class="fss-badges">{"".join(badges)}</div></article>'
    )


def _gun(*articles):
    return '<div class="fss-gun"><p class="fss-gun-name">나군</p>' + "".join(articles) + "</div>"


def test_severity_badge_keeps_a_space_before_the_sentence():
    fixed = repair_severity_gap(
        '<span class="fss-sev fss-sev-part">일부미흡</span>품질성과급'
    )
    assert "</span> 품질" in fixed
    assert repair_severity_gap(fixed) == fixed


def test_same_topic_in_a_gun_lists_firms_without_a_summary():
    page = _gun(
        _article(["성현회계법인"], BOILERPLATE, [BODY]),
        _article(["한울회계법인"], "품질성과급 비중이 낮습니다.", [OTHER]),
    )
    rewritten = collapse_document(page)
    assert rewritten.count("<article") == 1
    assert "fss-summary" not in rewritten
    assert BOILERPLATE not in rewritten
    assert rewritten.count("평가 결과와 보상") == 1
    assert "성현회계법인" in rewritten and "한울회계법인" in rewritten
    assert "품질성과급 비중이 낮습니다." in rewritten
    assert "특수관계자 급여를 성과평가 없이 정합니다." in rewritten
    assert audit_review_html(rewritten) == []


def test_same_firm_findings_open_under_one_name():
    page = _gun(
        _article(["성현회계법인"], "", [BODY]),
        _article(["성현회계법인"], "", [OTHER]),
    )
    rewritten = collapse_document(page)
    assert rewritten.count('data-names="성현회계법인"') == 3
    assert "품질성과급 비중이 낮습니다." in rewritten
    assert "특수관계자 급여를 성과평가 없이 정합니다." in rewritten
    assert audit_review_html(rewritten) == []


def test_collapse_is_stable():
    page = _gun(
        _article(["성현회계법인"], BOILERPLATE, [BODY]),
        _article(["한울회계법인"], "다른 요약", [OTHER]),
    )
    once = collapse_document(page)
    assert collapse_document(once) == once


def test_firms_outside_a_gun_are_listed_without_a_summary():
    page = (
        '<div class="fss-bundle"><p class="fss-bundle-name">일반회계법인</p>'
        + _article(["예지회계법인"], "인사관리가 미흡합니다.", [BODY])
        + _article(["예지회계법인"], "", [OTHER])
        + "</div>"
    )
    rewritten = collapse_document(page)
    assert rewritten.count("<article") == 1
    assert "fss-summary" not in rewritten
    assert "인사관리가 미흡합니다." not in rewritten
    assert "품질성과급 비중이 낮습니다." in rewritten
    assert "특수관계자 급여를 성과평가 없이 정합니다." in rewritten
    assert audit_review_html(rewritten) == []


def test_audit_rejects_a_summary_under_the_topic():
    page = _gun(_article(["성현회계법인"], BOILERPLATE, [BODY]))
    errors = audit_review_html(page)
    assert any("요약" in error for error in errors)
    assert any("안내 문장" in error for error in errors)


def test_topic_moves_under_the_heading_and_gun_moves_into_the_card():
    filled = (
        '<div class="fss-gun"><p class="fss-gun-name">가군</p>'
        + _article(["삼일회계법인"], "", [BODY])
        + "</div>"
    )
    empty = '<div class="fss-gun"><p class="fss-gun-name">나군</p><p class="fss-none">분류된 지적 없음</p></div>'
    page = (
        '<section class="fss-jung"><h3>1.2 성과 연동 보상</h3>'
        '<div class="fss-year" data-year="2025">'
        '<div class="fss-bundle"><p class="fss-bundle-name">등록</p>'
        + filled
        + empty
        + "</div>"
        '<div class="fss-bundle"><p class="fss-bundle-name">일반회계법인</p>'
        + _article(["예지회계법인"], "", [OTHER])
        + "</div></div></section>"
    )
    moved = repair_severity_gap(place_labels(page))
    assert "</h3><p class=\"fss-group-name\">평가 결과와 보상</p>" in moved
    assert moved.count("평가 결과와 보상") == 1
    assert '<article class="fss-group" data-names="삼일회계법인"><p class="fss-gun-name">가군</p>' in moved
    assert empty in moved
    assert "등록</p>" in moved
    general = moved.split("일반회계법인", 1)[1]
    assert "fss-gun-name" not in general
    assert "fss-group-name" not in general
    assert place_labels(moved) == moved
    assert audit_review_html(moved) == []


def test_year_comes_before_the_component_report_and_the_firms():
    article = _article(["삼일회계법인"], "", [BODY])
    page = (
        '<section class="fss-dae"><h2>1. 회계법인 내 품질에 대한 리더십 책임</h2>'
        '<section class="fss-jung"><h3>1.2 성과 연동 보상</h3>'
        '<p class="fss-group-name">평가 결과와 보상</p>'
        '<div class="fss-year" data-year="2025">'
        '<div class="fss-bundle"><p class="fss-bundle-name">등록</p>'
        '<div class="fss-gun"><p class="fss-gun-name">가군</p>'
        + article
        + "</div></div></div></section>"
        '<section class="fss-jung"><h3>1.1 지배구조</h3>'
        '<p class="fss-group-name">담당이사와 지배구조</p>'
        '<div class="fss-year" data-year="2024" hidden>'
        '<div class="fss-bundle"><p class="fss-bundle-name">일반회계법인</p>'
        + _article(["예지회계법인"], "", [OTHER])
        + "</div></div></section></section>"
    )
    moved = repair_severity_gap(arrange_by_year(place_labels(page)))
    assert moved.index("<h2>2025년</h2>") < moved.index("<h2>2024년</h2>")
    assert moved.index("<h2>2025년</h2>") < moved.index("1. 회계법인 내 품질에 대한 리더십 책임")
    assert "품질우선 보상체계" in moved
    assert '<p class="fss-bundle-name">등록</p>' in moved
    assert "가군" in moved and "삼일회계법인" in moved
    assert "예지회계법인" in moved
    assert arrange_by_year(moved) == moved
    assert audit_review_html(moved) == []
