# -*- coding: utf-8 -*-
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fss_review_cards import (  # noqa: E402
    BOILERPLATE,
    PAGE,
    YEAR_2025_MARK,
    arrange_by_year,
    audit_review_html,
    collapse_document,
    load_year_2025,
    materialize_review_markdown,
    place_labels,
    render_year_2025_html,
    repair_severity_gap,
)
from mkdocs_fss_review_year import on_page_markdown  # noqa: E402

TEXT_SHA = "1bcd9dfc6a4f96534765a756e936c5d066a999a069a2bc92317c70ab29d0431f"
SEV_SHA = "c2133bc29c69c0404da2b8e8a93a77c639f9f10698fda75c910977c8abeebf99"
YEAR_SHA = {
    "2025": "05eeae40046d772179a57ad3579ae822f52ba5494a1df36ab541571c887f92c6",
    "2024": "dd252ed36a6f3debb59d9c5c831dfab643bb3dc51a4918b5f4649b0087f87763",
    "2023": "a04efa16f933d3aac44bb98434af3bc21160d028790e140c50d77a3f38416baf",
    "2022": "5cf332453ec91121dbbc37aec0c15f540842b5cf845cfde7df98708c839601dc",
    "2021": "9b278810dd0ff9a0e19300d5d8c1f67cb5ef34db2a07b8bcc437eed11ea2b821",
    "2020": "24375fe9c10e2a0fa0513dea5831fc4141471cca9be2e0c1ea9414c01465ce92",
    "2019": "fb13f1d4d54aaf8126f97bf802feb37ef40b2fee7852694ca22c3215e607d098",
}

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


def test_firm_index_is_not_a_content_script():
    text = PAGE.read_text(encoding="utf-8")
    open_tag = '<div id="fss-firm-index" hidden>'
    start = text.find(open_tag)
    assert start >= 0
    end = text.find("</div>", start)
    names = json.loads(text[start + len(open_tag) : end])
    assert names
    assert "<script" not in text


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


def _review_page() -> str:
    return materialize_review_markdown(PAGE.read_text(encoding="utf-8"))


def test_card_rewrite_keeps_original_sentences():
    text = _review_page()
    rewritten = arrange_by_year(place_labels(collapse_document(text)))

    def bodies(html):
        return sorted(
            repair_severity_gap(body)
            for body in re.findall(r'<div class="fss-original"[^>]*>(.*?)</div>', html)
        )

    assert bodies(rewritten) == bodies(text)


def test_samil_time_finding_is_two_paragraphs():
    text = _review_page()
    marker = "Time report에 입력"
    at = text.find(marker)
    assert at >= 0
    original_start = text.rfind('<div class="fss-original"', 0, at)
    original_end = text.find("</div>", at)
    body = text[original_start:original_end]
    assert body.count('<p class="fss-finding">') == 2
    assert "입력·승인하였으나" in body
    assert "입력· 승인" not in body
    assert "통제절차가 미흡</p>" in body
    assert "통제절차가 미흡하고" not in body
    assert "통제절차가 미흡함" not in body
    assert body.count('<span class="fss-sev') == 1
    assert "공시되는 외부감사 투입시간을 집계하는 절차 운영이 일부 미흡</p>" in body


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value or "")


def finding_records(year_div):
    records = []
    last_sev = None
    for paragraph in year_div.select("p.fss-finding"):
        original = paragraph.find_parent("div", class_="fss-original")
        firm = original.get("data-names") if original else None
        span = paragraph.select_one("span.fss-sev")
        full = paragraph.get_text()
        if span:
            severity = span.get_text(strip=True)
            last_sev = severity
            body = full.lstrip()
            if body.startswith(severity):
                body = body[len(severity):].lstrip()
            else:
                body = body.strip()
        else:
            severity = last_sev
            body = full.strip()
        records.append({
            "firm": firm,
            "severity": severity,
            "badge": bool(span),
            "text": _nfc(body.strip()),
        })
    return records


def _sha_lines(lines) -> tuple[str, int]:
    blob = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), len(blob)


def _bundle_counts(data: dict) -> tuple[dict, dict]:
    firms: dict[str, list[str]] = {}
    findings: dict[str, int] = {}
    for bundle in data["bundles"]:
        names: list[str] = []
        count = 0
        for section in bundle["sections"]:
            for group in section["groups"]:
                for block in group["blocks"]:
                    if block["kind"] != "firms":
                        continue
                    for firm in block["firms"]:
                        names.append(firm["name"])
                        count += len(firm["findings"])
        firms[bundle["name"]] = names
        findings[bundle["name"]] = count
    return firms, findings


def test_year_2025_inventory_is_locked():
    data = load_year_2025()
    rendered = render_year_2025_html(data)
    json_records = [
        {"severity": finding["severity"], "text": _nfc(finding["text"])}
        for bundle in data["bundles"]
        for section in bundle["sections"]
        for group in section["groups"]
        for block in group["blocks"]
        if block["kind"] == "firms"
        for firm in block["firms"]
        for finding in firm["findings"]
    ]
    html_records = finding_records(BeautifulSoup(rendered, "html.parser").select_one("div.fss-year"))
    assert _sha_lines(record["text"] for record in json_records) == (TEXT_SHA, 129054)
    assert _sha_lines(record["text"] for record in html_records) == (TEXT_SHA, 129054)
    assert _sha_lines(f'{record["severity"]}\t{record["text"]}' for record in json_records) == (SEV_SHA, 133729)
    assert _sha_lines(f'{record["severity"]}\t{record["text"]}' for record in html_records) == (SEV_SHA, 133729)

    firms, findings = _bundle_counts(data)
    assert {name: len(dict.fromkeys(values)) for name, values in firms.items()} == {
        "등록": 7,
        "일반회계법인": 52,
        "감사반": 19,
    }
    assert len({name for values in firms.values() for name in values}) == 78
    assert findings == {"등록": 86, "일반회계법인": 227, "감사반": 57}
    assert sum(findings.values()) == len(json_records) == len(html_records) == 370
    severities = {}
    for record in json_records:
        severities[record["severity"]] = severities.get(record["severity"], 0) + 1
    assert severities == {"일부미흡": 269, "미운영": 73, "일부미운영": 28}
    assert all(record["severity"] != "미설계" for record in html_records)

    source = PAGE.read_text(encoding="utf-8")
    assert source.count('data-year="2025"') == 1
    assert source.count(YEAR_2025_MARK) == 1
    assert 'data-year="2026"' not in source
    page = _review_page()
    assert page.count('data-year="2025"') == 1
    assert YEAR_2025_MARK not in page
    assert 'data-year="2026"' not in page
    assert rendered in page

    soup = BeautifulSoup(page, "html.parser")
    years = soup.select("div.fss-year")
    assert [div.get("data-year") for div in years] == ["2025", "2024", "2023", "2022", "2021", "2020", "2019"]
    for div in years:
        year = div.get("data-year")
        assert hashlib.sha256(str(div).encode("utf-8")).hexdigest() == YEAR_SHA[year]
        assert div.has_attr("hidden") is (year != "2025")


class _File:
    def __init__(self, src: str) -> None:
        self.src_uri = src


class _Page:
    def __init__(self, src: str) -> None:
        self.file = _File(src)


def test_build_hook_inserts_the_2025_year_once():
    source = PAGE.read_text(encoding="utf-8")
    built = on_page_markdown(source, _Page("fss-review/index.md"), None, None)
    assert built == _review_page()
    assert built.count('data-year="2025"') == 1
    untouched = on_page_markdown("본문", _Page("index.md"), None, None)
    assert untouched == "본문"
