# -*- coding: utf-8 -*-
"""품질관리감리 카드.

같은 군, 같은 중분류 아래에는 요약을 두지 않는다. 해당 회계법인만 나열하고,
이름을 누르면 그 법인의 지적이 열린다.

새 지적도 ``collapse_document``가 만드는 목록과 같다.
``python scripts/fss_review_cards.py --write``로 발행 페이지에 적용한다.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "fss-review" / "index.md"
YEAR_2025_PATH = ROOT / "data" / "fss-review" / "year-2025.json"
YEAR_2025_MARK = '<!-- fss-review-year data-year="2025" -->'

BOILERPLATE = "같은 규칙으로 묶은 지적입니다."

_ARTICLE = re.compile(r"<article\b[^>]*>.*?</article>", re.S)
_ORIGINAL = re.compile(
    r'<div class="fss-original"[^>]*data-names="([^"]*)"[^>]*>(.*?)</div>',
    re.S,
)
_GUN = '<div class="fss-gun">'
_BUNDLE = '<div class="fss-bundle">'
_SPAN_GAP = re.compile(r"</span>(?=[^\s<])")


@dataclass(frozen=True)
class FirmFinding:
    name: str
    body_html: str


def repair_severity_gap(fragment: str) -> str:
    """심각도 뱃지 바로 뒤에 붙은 원문 첫 글자 앞에 공백을 둔다."""
    return _SPAN_GAP.sub("</span> ", fragment)


def _esc_text(value: str) -> str:
    return html.escape(value, quote=False)


def _esc_attr(value: str) -> str:
    return html.escape(value, quote=True)


def parse_article(article: str) -> tuple[str, list[FirmFinding]]:
    topic_match = re.search(r'<p class="fss-group-name">(.*?)</p>', article, re.S)
    topic = html.unescape(topic_match.group(1)).strip() if topic_match else ""
    firms = [
        FirmFinding(html.unescape(match.group(1)), match.group(2))
        for match in _ORIGINAL.finditer(article)
    ]
    return topic, firms


def merge_firms(firms: list[FirmFinding]) -> list[FirmFinding]:
    """같은 법인의 지적 원문은 이름 하나에 이어 붙인다."""
    order: list[str] = []
    bodies: dict[str, str] = {}
    for firm in firms:
        if firm.name not in bodies:
            order.append(firm.name)
            bodies[firm.name] = firm.body_html
        else:
            bodies[firm.name] += firm.body_html
    return [FirmFinding(name, bodies[name]) for name in order]


def render_topic(topic: str, firms: list[FirmFinding]) -> str:
    names = "|".join(firm.name for firm in firms)
    badges: list[str] = []
    for firm in firms:
        body = repair_severity_gap(firm.body_html)
        attr = _esc_attr(firm.name)
        badges.append(
            f'<button type="button" class="fss-badge" data-names="{attr}">'
            f"{_esc_text(firm.name)}</button>"
            f'<div class="fss-original" hidden data-names="{attr}">{body}</div>'
        )
    return (
        f'<article class="fss-group" data-names="{_esc_attr(names)}">'
        f'<p class="fss-group-name">{_esc_text(topic.strip())}</p>'
        f'<div class="fss-badges">{"".join(badges)}</div></article>'
    )


def _matching_div_end(text: str, open_at: int) -> int:
    i = text.find(">", open_at)
    if i < 0:
        raise ValueError("div 태그가 닫히지 않았습니다.")
    depth = 1
    i += 1
    while depth:
        next_open = text.find("<div", i)
        next_close = text.find("</div>", i)
        if next_close < 0:
            raise ValueError("div가 닫히지 않았습니다.")
        if next_open != -1 and next_open < next_close:
            depth += 1
            i = next_open + 4
        else:
            depth -= 1
            i = next_close + len("</div>")
    return i


def _regions(text: str, needle: str) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    cursor = 0
    while True:
        at = text.find(needle, cursor)
        if at < 0:
            break
        end = _matching_div_end(text, at)
        found.append((at, end))
        cursor = end
    return found


def _replace_regions(text: str, needle: str, transform) -> str:
    parts: list[str] = []
    cursor = 0
    for start, end in _regions(text, needle):
        parts.append(text[cursor:start])
        parts.append(transform(text[start:end]))
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def _mask(text: str, needle: str) -> tuple[str, list[str]]:
    kept: list[str] = []
    parts: list[str] = []
    cursor = 0
    for start, end in _regions(text, needle):
        parts.append(text[cursor:start])
        parts.append(f"\x00REGION{len(kept)}\x00")
        kept.append(text[start:end])
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts), kept


def _unmask(text: str, kept: list[str]) -> str:
    for index, region in enumerate(kept):
        text = text.replace(f"\x00REGION{index}\x00", region)
    return text


def collapse_gun(gun_html: str) -> str:
    matches = list(_ARTICLE.finditer(gun_html))
    if not matches:
        return gun_html
    if all('<p class="fss-group-name">' not in match.group(0) for match in matches):
        return gun_html
    grouped: dict[str, list[FirmFinding]] = {}
    order: list[str] = []
    for match in matches:
        topic, firms = parse_article(match.group(0))
        if topic not in grouped:
            order.append(topic)
            grouped[topic] = []
        grouped[topic].extend(firms)
    body = "".join(render_topic(topic, merge_firms(grouped[topic])) for topic in order)
    return gun_html[: matches[0].start()] + body + gun_html[matches[-1].end() :]


def collapse_document(text: str) -> str:
    """군 안과, 군이 없는 일반회계법인·감사반 묶음 안에서 중분류별로 법인을 모은다."""
    text = _replace_regions(text, _GUN, collapse_gun)

    def collapse_bundle(bundle_html: str) -> str:
        masked, guns = _mask(bundle_html, _GUN)
        return _unmask(collapse_gun(masked), guns)

    return _replace_regions(text, _BUNDLE, collapse_bundle)


def place_labels(text: str) -> str:
    """중분류 이름은 절 제목 아래로, 군 이름은 등록 카드 안으로 옮긴다."""
    needle = '<section class="fss-jung">'
    parts: list[str] = []
    cursor = 0
    while True:
        at = text.find(needle, cursor)
        if at < 0:
            parts.append(text[cursor:])
            break
        end = text.find("</section>", at)
        if end < 0:
            raise ValueError("중분류 절이 닫히지 않았습니다.")
        end += len("</section>")
        parts.append(text[cursor:at])
        parts.append(_place_jung(text[at:end]))
        cursor = end
    return "".join(parts)


def _place_jung(jung: str) -> str:
    topics = re.findall(r'<p class="fss-group-name">(.*?)</p>', jung)
    topic = topics[0] if topics else ""
    h3_end = jung.find("</h3>")
    if h3_end < 0:
        return jung
    h3_end += len("</h3>")
    body = jung[:h3_end] + re.sub(r'<p class="fss-group-name">.*?</p>', "", jung[h3_end:])
    body = _replace_regions(body, _GUN, _unwrap_filled_gun)
    if topic:
        body = body[:h3_end] + f'<p class="fss-group-name">{topic}</p>' + body[h3_end:]
    return body


def _unwrap_filled_gun(gun_html: str) -> str:
    if "<article" not in gun_html:
        return gun_html
    name_match = re.search(r'<p class="fss-gun-name">.*?</p>', gun_html)
    gun_name = name_match.group(0) if name_match else ""
    inner = gun_html
    if name_match:
        inner = inner[: name_match.start()] + inner[name_match.end() :]
    if inner.startswith(_GUN):
        inner = inner[len(_GUN) :]
    if inner.endswith("</div>"):
        inner = inner[: -len("</div>")]

    def insert(match: re.Match[str]) -> str:
        return match.group(0) + gun_name

    if gun_name:
        inner = re.sub(r"<article\b[^>]*>", insert, inner)
    return inner


def _gun_slices(text: str) -> list[str]:
    return [text[start:end] for start, end in _regions(text, _GUN)]


def _loose_bundle_slices(text: str) -> list[str]:
    slices: list[str] = []
    for start, end in _regions(text, _BUNDLE):
        masked, _guns = _mask(text[start:end], _GUN)
        if "<article" in masked:
            slices.append(masked)
    return slices


def audit_review_html(text: str) -> list[str]:
    errors: list[str] = []
    if BOILERPLATE in text:
        errors.append("안내 문장이 카드에 있습니다.")
    if 'class="fss-summary"' in text:
        errors.append("중분류 아래 요약 문장이 있습니다.")
    if _SPAN_GAP.search(text):
        errors.append("심각도 뱃지 뒤에 띄어쓰기가 없습니다.")
    if "<h3>" in text:
        errors.extend(_layout_errors(text))
    else:
        for scope in _gun_slices(text) + _loose_bundle_slices(text):
            seen: set[str] = set()
            for article in _ARTICLE.findall(scope):
                topic, firms = parse_article(article)
                if not topic:
                    errors.append("카드에 중분류 이름이 없습니다.")
                elif topic in seen:
                    errors.append(f"같은 군에 중분류가 두 번 있습니다: {topic}")
                else:
                    seen.add(topic)
                names = [firm.name for firm in firms]
                if len(names) != len(set(names)):
                    errors.append(f"같은 중분류에 법인 이름이 겹칩니다: {topic}")
    if len(errors) > 12:
        extra = len(errors) - 12
        errors = errors[:12]
        errors.append(f"같은 종류의 오류가 {extra}건 더 있습니다.")
    return errors


def _layout_errors(text: str) -> list[str]:
    errors: list[str] = []
    if any("fss-group-name" in article for article in _ARTICLE.findall(text)):
        errors.append("중분류 이름이 카드 안에 있습니다.")
    needle = '<section class="fss-jung">'
    cursor = 0
    while True:
        at = text.find(needle, cursor)
        if at < 0:
            break
        end = text.find("</section>", at)
        jung = text[at : end + len("</section>")]
        cursor = end + len("</section>")
        names = re.findall(r'<p class="fss-group-name">(.*?)</p>', jung)
        if len(names) != 1:
            errors.append("절 제목 아래 중분류 이름이 하나가 아닙니다.")
        elif "</h3><p class=\"fss-group-name\">" not in jung:
            errors.append("중분류 이름이 절 제목 바로 아래에 없습니다.")
    for start, end in _regions(text, _BUNDLE):
        bundle = text[start:end]
        kind_match = re.search(r'<p class="fss-bundle-name">(.*?)</p>', bundle)
        kind = kind_match.group(1) if kind_match else ""
        masked, _guns = _mask(bundle, _GUN)
        for article in _ARTICLE.findall(masked):
            has_gun = "fss-gun-name" in article
            if kind == "등록" and not has_gun:
                errors.append("등록 카드에 군 이름이 없습니다.")
            if kind != "등록" and has_gun:
                errors.append("등록이 아닌 카드에 군 이름이 있습니다.")
    return errors


_YEAR = '<div class="fss-year"'
_BUNDLE_ORDER = ("등록", "일반회계법인", "감사반")
_REPORTS = {
    ("2025", "등록", "1. 회계법인 내 품질에 대한 리더십 책임"): (
        "품질우선 보상체계 운영이 미흡한 지적이 8건으로 큰 비중을 차지하고, "
        "특수관계자와의 부당거래가 5건이다. 평가등급이나 성과급의 임의 조정, "
        "평가 기준 없는 특별상여, 본부별 기본급·퇴직금 결정이 여기에 들어 있다. "
        "품질관리담당자 전업의무 위반 2건, 지배구조 건전성 미흡 2건, 계약 등 일반 절차 미흡 1건이다."
    ),
    ("2025", "등록", "2. 관련 윤리적 요구사항"): (
        "독립성 정보의 수집·관리 미흡이 7건으로 주를 이룬다. "
        "신규 선임 사원에 대한 독립성 점검이 늦은 경우가 5건, "
        "감사업무 수임 시 독립성 점검 절차가 미흡한 경우가 2건이다."
    ),
    ("2025", "등록", "3. 의뢰인 관계 및 특정 업무의 수용과 유지"): (
        "계약 전 위험평가의 지연 승인, 재평가 누락, 작성자 본인에 의한 승인이 8건이다."
    ),
    ("2025", "등록", "4. 인적 자원"): (
        "감사투입시간 입력·승인 관리 소홀이 8건으로 주를 이룬다. "
        "공인회계사 채용 절차가 미흡한 경우가 5건, 전문성 자료와 역량평가 운영이 미흡한 경우가 4건이다."
    ),
    ("2025", "등록", "5. 업무의 수행"): (
        "비적격 심리담당자, 최소 투입시간·심리 요청 기한 미준수, 중요 지적의 문서화와 보완 누락이 8건이다. "
        "감사조서 취합 또는 반납 기한 미준수 5건, 부정과 통제 무력화 검토 누락 4건, 업무문서 접근통제 미흡 3건이다."
    ),
    ("2025", "등록", "6. 모니터링"): (
        "사후심리 시간 준수와 후속조치가 미흡한 지적이 3건이다."
    ),
    ("2021", "등록", "1. 회계법인 내 품질에 대한 리더십 책임"): (
        "품질 지향 조직문화를 위한 정책과 절차의 적정성과 운영을 점검했다. "
        "성과평가와 성과급에 품질 기여 기준이 없거나, 품질관리 업무에 대한 대표이사의 권한과 책임이 미흡했다."
    ),
    ("2021", "등록", "2. 관련 윤리적 요구사항"): (
        "재무적 이해관계 등 이해상충에 따른 독립성 위반을 막기 위한 절차와 운영을 점검했다. "
        "독립성 점검 체계와 절차, 비감사업무 수임 시 독립성 점검이 미흡했다."
    ),
    ("2021", "등록", "3. 의뢰인 관계 및 특정 업무의 수용과 유지"): (
        "감사계약과 감사계획 단계의 위험평가, 그리고 그 결과를 감사절차에 반영했는지를 점검했다. "
        "계약 전 위험평가를 형식적으로 운영하거나, 파악된 위험의 반영과 문서화가 미흡했다."
    ),
    ("2021", "등록", "4. 인적 자원"): (
        "과도한 업무수임과 감사시간 관리를 점검했다. "
        "감사투입시간을 미리 또는 늦게 입력·승인하거나, 그 시간으로 감사보고서에 공시한 사례가 있었다."
    ),
    ("2021", "등록", "5. 업무의 수행"): (
        "감사보고서 발행 전 사전심리 등 업무품질관리검토와 감사조서 관리를 점검했다. "
        "사전심리 통제와 조서 취합·내부통제가 일부 미흡했다."
    ),
    ("2021", "등록", "6. 모니터링"): (
        "품질관리시스템 자체 모니터링과 사후심리의 적정성을 점검했다. "
        "사후심리 운영, 미비점의 영향 평가와 후속조치 문서화, 구성요소별 모니터링이 미흡했다."
    ),
    ("2022", "등록", "1. 회계법인 내 품질에 대한 리더십 책임"): (
        "17개 법인의 평균 지적 1.6건(15.7%)이다. "
        "품질관리 업무에 대한 대표이사의 권한과 책임 부여가 미흡하고, "
        "성과평가의 구체적 기준이나 성과급에 품질 기여도를 반영하는 절차가 미흡했다."
    ),
    ("2022", "등록", "2. 관련 윤리적 요구사항"): (
        "평균 지적 1.9건(18.6%)이다. "
        "독립성 신고의 누락이나 지연 등 독립성 정보 수집·관리가 미흡하고, "
        "감사업무 수임 시 독립성 점검 절차도 미흡했다."
    ),
    ("2022", "등록", "3. 의뢰인 관계 및 특정 업무의 수용과 유지"): (
        "평균 지적 0.9건(8.7%)이다. "
        "계약 전 위험평가를 형식적으로 운영하거나, 파악된 위험을 감사절차에 반영하는 절차가 미흡했다."
    ),
    ("2022", "등록", "4. 인적 자원"): (
        "평균 지적 2.1건(20.3%)이다. "
        "감사투입시간을 늦게 입력하거나 승인하고, "
        "기업 특성과 참여자 전문성을 고려하지 않은 업무 배정이 있었다."
    ),
    ("2022", "등록", "5. 업무의 수행"): (
        "평균 지적 2.8건(27.9%)으로 가장 많다. "
        "사전심리 통제와 감사조서 취합·내부통제가 미흡했다."
    ),
    ("2022", "등록", "6. 모니터링"): (
        "평균 지적 0.9건(8.7%)이다. "
        "사후심리 절차가 미흡하거나, 미비점에 대한 후속조치 문서화가 미흡했다."
    ),
    ("2023", "등록", "1. 회계법인 내 품질에 대한 리더십 책임"): (
        "14개 법인 평균 1.8건, 전체 25건이다. "
        "특수관계자 자금관리와 특수관계 직원 감독 등 통합관리 미흡이 7개 법인, "
        "품질관리 승인 문서화·위임 규정·자금과 비감사 수임 통제 미흡이 7개 법인, "
        "품질에 근거한 성과평가와 성과급 연계 부족 또는 특별상여가 11개 법인이다."
    ),
    ("2023", "등록", "2. 관련 윤리적 요구사항"): (
        "평균 1.5건, 전체 22건이다. "
        "독립성 신고 누락·지연, 가족관계와 지배·종속회사 정보, 이해상충 정보 취합이 미흡한 법인이 13개이고, "
        "수임 시 독립성·이해상충 확인과 주식거래 완전성 확인이 미흡한 법인이 9개이다."
    ),
    ("2023", "등록", "3. 의뢰인 관계 및 특정 업무의 수용과 유지"): (
        "평균 0.9건, 전체 12건이다. "
        "위험평가 완료 전 감사계약, 평가표 부실, 평가기준 부재, 고위험 회사 관리 절차 미흡이 12개 법인이다."
    ),
    ("2023", "등록", "4. 인적 자원"): (
        "평균 1.8건, 전체 25건이다. "
        "업무수행이사 선임 기준과 산업 특성 고려가 미흡한 법인이 6개, "
        "채용 통합관리와 교육이 미흡한 법인이 8개, "
        "시간 수정 사유·승인권한·조기 또는 지연 입력·공시 불일치가 11개 법인이다."
    ),
    ("2023", "등록", "5. 업무의 수행"): (
        "평균 2.4건, 전체 34건으로 가장 많다. "
        "이해와 위험평가 문서화, 감독·검토가 미흡한 법인이 11개, "
        "심리담당자 적격성과 사전심리 시간·문서화가 미흡한 법인이 12개, "
        "보고서일 후 60일을 넘겨 조서를 취합하거나 임의 변형 방지가 미흡한 법인이 11개이다."
    ),
    ("2023", "등록", "6. 모니터링"): (
        "평균 0.7건, 전체 10건이다. 4대 법인 평균(1.0건)이 기타 등록법인 평균(0.7건)보다 많다. "
        "전산 정보보안, 사후심리 시간과 문서화, 미비점 보완 확인이 미흡한 법인이 10개이다."
    ),
    ("2024", "등록", "1. 회계법인 내 품질에 대한 리더십 책임"): (
        "14개 법인 평균 1.9건, 전체 27건이다. "
        "인사·자금 등 통합관리 미흡이 11건, 성과평가와 성과급 연계 미흡 또는 기준 없는 특별상여가 13건, "
        "품질관리 권한·책임 체계 미흡이 1건, 대표이사를 견제하는 지배구조 미흡이 2건이다."
    ),
    ("2024", "등록", "2. 관련 윤리적 요구사항"): (
        "평균 1.5건, 전체 21건이다. "
        "독립성 신고 누락·지연 등 정보 수집·관리 미흡이 12건, 수임 시 독립성 점검 미흡이 9건이다."
    ),
    ("2024", "등록", "3. 의뢰인 관계 및 특정 업무의 수용과 유지"): (
        "평균 0.9건, 전체 12건이다. "
        "계약 전 위험평가를 형식적으로 운영하거나, 파악된 위험을 감사절차에 반영하는 절차가 미흡하다."
    ),
    ("2024", "등록", "4. 인적 자원"): (
        "평균 1.5건, 전체 21건이다. "
        "감사투입시간 지연 입력·승인이 11건, 기업 특성과 전문성을 고려하지 않은 업무 배정이 5건, "
        "신규 공인회계사 채용 시 적격성 확인과 승인이 미흡한 경우가 5건이다."
    ),
    ("2024", "등록", "5. 업무의 수행"): (
        "평균 2.2건, 전체 31건으로 가장 많다. "
        "사전심리 통제 절차 미흡이 21건, 감사조서 취합과 내부통제 미흡이 10건이다."
    ),
    ("2024", "등록", "6. 모니터링"): (
        "평균 0.7건, 전체 10건이다. 4대 법인 평균(1.5건)이 기타 등록법인 평균(0.6건)보다 많다. "
        "정보보안 통제 미흡이 2건, 사후심리 절차 또는 미비점 후속조치 미흡이 8건이다."
    ),
}

_EARLY = (
    "이 문단은 2019년과 2020년을 함께 공개한 보고서의 결과이다. "
    "16개 법인 평균 지적은 11.5건이고, 업무의 수행 3.4건(29.3%)과 인적자원 2.3건(19.6%)이 약 절반이다. "
    "가군 평균은 5.8건으로 상대적으로 적고, 나군부터 라군은 통합관리의 실질 운영과 인력·설비 투자가 부족해 미흡이 많다."
)
for _year in ("2019", "2020"):
    _REPORTS[(_year, "등록", "1. 회계법인 내 품질에 대한 리더십 책임")] = (
        _EARLY + " 리더십 책임은 평균 1.3건(11.4%)이다."
    )
    _REPORTS[(_year, "등록", "2. 관련 윤리적 요구사항")] = (
        "2019·2020년 합본 기준 평균 1.6건(14.1%)이다. "
        "독립성 점검 절차가 여섯 구성요소 전반의 미흡 가운데 한 축이다."
    )
    _REPORTS[(_year, "등록", "3. 의뢰인 관계 및 특정 업무의 수용과 유지")] = (
        "2019·2020년 합본 기준 평균 1.4건(12.0%)이다. "
        "감사계약과 감사계획 단계의 위험평가, 그리고 그 결과를 감사절차에 반영했는지를 점검했다."
    )
    _REPORTS[(_year, "등록", "4. 인적 자원")] = (
        "2019·2020년 합본 기준 평균 2.3건(19.6%)이다. "
        "감사시간 관리가 핵심 점검이었고, 인적자원과 업무의 수행이 전체 지적의 약 절반이다."
    )
    _REPORTS[(_year, "등록", "5. 업무의 수행")] = (
        "2019·2020년 합본 기준 평균 3.4건(29.3%)으로 가장 많다. "
        "사전검토 등 업무품질관리검토와 감사조서 관리를 중심으로 점검했다."
    )
    _REPORTS[(_year, "등록", "6. 모니터링")] = (
        "2019·2020년 합본 기준 평균 1.6건(13.6%)이다. "
        "품질관리 모니터링 시스템이 작동하는지를 점검했다."
    )

_BUNDLE_REPORTS = {
    ("2022", "일반회계법인"): (
        "중점 점검은 감사조서 작성·관리와 업무품질관리검토(사전심리) 두 항목이다. "
        "조서에서 지적된 법인이 48개(미운영 41.7%, 일부미흡 58.3%)로 더 많고, "
        "사전심리는 43개(미운영 20.9%, 일부미흡 79.1%)이다. "
        "합계는 미운영 31.9%, 일부미흡 68.1%이다."
    ),
    ("2023", "일반회계법인"): (
        "중점 점검은 감사조서 작성·관리와 업무품질관리검토(사전심리) 두 항목이다. "
        "상반기 3개 법인을 포함한 50개 법인 기준이다. "
        "조서 지적이 47개 법인(미운영 25.5%)으로 더 많고, 사전심리는 40개 법인(미운영 12.5%)이다. "
        "합계는 미운영 19.5%, 일부미흡 80.5%이다."
    ),
    ("2024", "일반회계법인"): (
        "중점 점검은 감사조서 작성·관리와 업무품질관리검토(사전심리) 두 항목이다. "
        "조서와 사전심리 모두 50개 법인이 지적되었고, 미운영은 각각 20.0%와 24.0%이다. "
        "합계는 미운영 22.0%, 일부미흡 78.0%이다."
    ),
    ("2025", "일반회계법인"): (
        "1차 기획감리의 감사조서 작성·관리(35개 법인, 미운영 11.4%)와 "
        "업무품질관리검토(29개 법인, 미운영 6.9%)는 줄었다. "
        "2차에 더한 감사시간 관리(39개 법인, 미운영 48.7%)와 "
        "모니터링(사후심리, 43개 법인, 미운영 53.5%)은 다수 법인에서 미흡하다. "
        "합계는 미운영 32.9%, 일부미흡 67.1%이다."
    ),
    ("2022", "감사반"): (
        "중점 점검은 3인 참여와 업무 배분, 감사시간 관리와 문서화, 상호검토, 감사조서 작성·관리이다. "
        "상호검토는 20개 감사반 전부 일부미흡이고, 감사시간은 19개(미운영 5.3%), "
        "조서는 14개(미운영 28.6%), 3인 참여는 13개(미운영 30.8%)이다. "
        "합계는 미운영 13.6%, 일부미흡 86.4%이다."
    ),
    ("2023", "감사반"): (
        "19개 감사반을 점검했다. 3인 참여 14개(미운영 50.0%), 감사시간 17개와 상호검토 18개는 전부 일부미흡, "
        "조서 17개(미운영 17.6%)이다. 감사시간과 상호검토 비중이 높다. "
        "합계는 미운영 15.2%, 일부미흡 84.8%이다."
    ),
    ("2024", "감사반"): (
        "3인 참여 3개(전부 일부미흡), 감사시간 16개(미운영 12.5%), "
        "상호검토 19개(미운영 47.4%), 조서 18개(전부 일부미흡)이다. "
        "감사시간, 상호검토, 조서의 비중이 높다. 합계는 미운영 19.6%, 일부미흡 80.4%이다."
    ),
    ("2025", "감사반"): (
        "3인 참여 6개(미운영 83.3%), 감사시간 16개(미운영 25.0%), "
        "상호검토 20개(미운영 25.0%), 조서 19개(미운영 15.8%)이다. "
        "감사시간, 상호검토, 조서의 비중이 높다. 합계는 미운영 27.9%, 일부미흡 72.1%이다."
    ),
}


def _section_end(text: str, open_at: int) -> int:
    depth = 0
    i = open_at
    while i < len(text):
        nxt_open = text.find("<section", i)
        nxt_close = text.find("</section>", i)
        if nxt_close < 0:
            raise ValueError("section이 닫히지 않았습니다.")
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + len("<section")
        else:
            depth -= 1
            i = nxt_close + len("</section>")
            if depth == 0:
                return i
    raise ValueError("section이 닫히지 않았습니다.")


def _iter_sections(text: str, class_name: str) -> list[tuple[int, int]]:
    needle = f'<section class="{class_name}">'
    found: list[tuple[int, int]] = []
    cursor = 0
    while True:
        at = text.find(needle, cursor)
        if at < 0:
            break
        end = _section_end(text, at)
        found.append((at, end))
        cursor = end
    return found


def _year_regions(html: str) -> list[tuple[int, int]]:
    needle = '<div class="fss-year"'
    found: list[tuple[int, int]] = []
    cursor = 0
    while True:
        at = html.find(needle, cursor)
        if at < 0:
            break
        if html.startswith('<div class="fss-years"', at):
            cursor = at + len(needle)
            continue
        end = _matching_div_end(html, at)
        found.append((at, end))
        cursor = end
    return found


def arrange_by_year(text: str) -> str:
    """연도, 등록의 여섯 구성요소 또는 일반·감사반, 그 아래 법인 순으로 다시 둔다."""
    dae_at = text.find('<section class="fss-dae">')
    year_at = text.find(_YEAR)
    if dae_at < 0:
        return ensure_reports(_hide_older_years(text))
    if year_at != -1 and year_at < dae_at:
        return ensure_reports(_hide_older_years(text))
    preamble = text[:dae_at]
    blocks: list[tuple[str, str, str, str, str]] = []
    last_end = dae_at
    for start, end in _iter_sections(text, "fss-dae"):
        last_end = end
        dae_html = text[start:end]
        title_match = re.search(r"<h2>(.*?)</h2>", dae_html)
        dae_title = title_match.group(1) if title_match else ""
        for j_start, j_end in _iter_sections(dae_html, "fss-jung"):
            jung = dae_html[j_start:j_end]
            head_match = re.search(
                r'(<section class="fss-jung"><h3>.*?</h3>(?:<p class="fss-group-name">.*?</p>)?)',
                jung,
            )
            head = head_match.group(1) if head_match else '<section class="fss-jung">'
            for y_start, y_end in _year_regions(jung):
                year_html = jung[y_start:y_end]
                year_match = re.search(r'data-year="(\d{4})"', year_html)
                if not year_match:
                    continue
                year = year_match.group(1)
                for b_start, b_end in _regions(year_html, _BUNDLE):
                    bundle = year_html[b_start:b_end]
                    kind_match = re.search(r'<p class="fss-bundle-name">(.*?)</p>', bundle)
                    kind = kind_match.group(1) if kind_match else ""
                    inner = bundle[kind_match.end() :] if kind_match else bundle
                    if inner.endswith("</div>"):
                        inner = inner[: -len("</div>")]
                    if "<article" not in inner:
                        continue
                    blocks.append((year, kind, dae_title, head, inner))
    suffix = text[last_end:]
    years = sorted({year for year, *_rest in blocks}, reverse=True)
    parts = [preamble]
    for year in years:
        parts.append(f'<div class="fss-year" data-year="{year}"><h2>{year}년</h2>')
        for kind in _BUNDLE_ORDER:
            chosen = [item for item in blocks if item[0] == year and item[1] == kind]
            if not chosen:
                continue
            parts.append(f'<div class="fss-bundle"><p class="fss-bundle-name">{kind}</p>')
            dae_order: list[str] = []
            for _year, _kind, dae_title, _head, _inner in chosen:
                if dae_title not in dae_order:
                    dae_order.append(dae_title)
            for dae_title in dae_order:
                parts.append(f'<section class="fss-dae"><h2>{dae_title}</h2>')
                report = _REPORTS.get((year, kind, dae_title))
                if report:
                    parts.append(f'<p class="fss-report">{html.escape(report)}</p>')
                for item in chosen:
                    if item[2] == dae_title:
                        parts.append(item[3])
                        parts.append(item[4])
                        parts.append("</section>")
                parts.append("</section>")
            parts.append("</div>")
        parts.append("</div>")
    parts.append(suffix)
    return ensure_reports(_hide_older_years("".join(parts)))


def _hide_older_years(text: str) -> str:
    marks = list(re.finditer(r'<div class="fss-year" data-year="(\d{4})"(?: hidden)?>', text))
    if not marks:
        return text
    pieces: list[str] = []
    last = 0
    for index, mark in enumerate(marks):
        pieces.append(text[last : mark.start()])
        hidden = "" if index == 0 else " hidden"
        pieces.append(f'<div class="fss-year" data-year="{mark.group(1)}"{hidden}>')
        last = mark.end()
    pieces.append(text[last:])
    return "".join(pieces)


def ensure_reports(text: str) -> str:
    """연도별 보고 문단이 없으면 해당 연도와 구성요소 아래에 넣는다."""
    pieces: list[str] = []
    last = 0
    for start, end in _year_regions(text):
        pieces.append(text[last:start])
        pieces.append(_fill_year_reports(text[start:end]))
        last = end
    pieces.append(text[last:])
    return "".join(pieces)


def _fill_year_reports(year_html: str) -> str:
    year_match = re.search(r'data-year="(\d{4})"', year_html)
    if not year_match:
        return year_html
    year = year_match.group(1)
    pieces: list[str] = []
    last = 0
    for start, end in _regions(year_html, _BUNDLE):
        pieces.append(year_html[last:start])
        pieces.append(_fill_bundle_reports(year, year_html[start:end]))
        last = end
    pieces.append(year_html[last:])
    return "".join(pieces)


def _fill_bundle_reports(year: str, bundle: str) -> str:
    kind_match = re.search(r'<p class="fss-bundle-name">(.*?)</p>', bundle)
    if not kind_match:
        return bundle
    kind = kind_match.group(1)
    body = bundle[kind_match.end() :]
    if body.endswith("</div>"):
        inner, close = body[: -len("</div>")], "</div>"
    else:
        inner, close = body, ""
    report = _BUNDLE_REPORTS.get((year, kind))
    if report and not inner.startswith('<p class="fss-report">'):
        inner = f'<p class="fss-report">{html.escape(report)}</p>' + inner
    pieces: list[str] = []
    last = 0
    for start, end in _iter_sections(inner, "fss-dae"):
        pieces.append(inner[last:start])
        pieces.append(_fill_dae_report(year, kind, inner[start:end]))
        last = end
    pieces.append(inner[last:])
    return bundle[: kind_match.end()] + "".join(pieces) + close


def _fill_dae_report(year: str, kind: str, dae: str) -> str:
    title = re.search(r"<h2>(.*?)</h2>", dae)
    if not title:
        return dae
    report = _REPORTS.get((year, kind, title.group(1)))
    if not report or dae[title.end() :].startswith('<p class="fss-report">'):
        return dae
    return dae[: title.end()] + f'<p class="fss-report">{html.escape(report)}</p>' + dae[title.end() :]


_SEV_CLASS = {
    "일부미흡": "fss-sev fss-sev-part",
    "미운영": "fss-sev fss-sev-off",
    "일부미운영": "fss-sev fss-sev-off",
    "미설계": "fss-sev fss-sev-miss",
}


class _Cursor:
    def __init__(self, text: str) -> None:
        self.text = text
        self.i = 0

    def start(self, prefix: str) -> bool:
        return self.text.startswith(prefix, self.i)

    def take(self, prefix: str) -> None:
        if not self.start(prefix):
            raise ValueError(f"예상한 표식이 없습니다: {prefix}")
        self.i += len(prefix)

    def until(self, end: str) -> str:
        at = self.text.find(end, self.i)
        if at < 0:
            raise ValueError(f"표식 끝을 찾지 못했습니다: {end}")
        chunk = self.text[self.i:at]
        self.i = at + len(end)
        return chunk


def _parse_finding(cursor: _Cursor) -> dict:
    cursor.take('<p class="fss-finding">')
    if cursor.start('<span class="'):
        cursor.take('<span class="')
        css = cursor.until('">')
        severity = cursor.until("</span>")
        body = cursor.until("</p>")
        if _SEV_CLASS.get(severity) != css or not body.startswith(" "):
            raise ValueError("심각도 뱃지 형식이 아닙니다.")
        text = body[1:]
        if text != text.strip():
            raise ValueError("지적 본문 공백이 예상과 다릅니다.")
        return {"severity": severity, "badge": True, "text": text}
    text = cursor.until("</p>")
    if text != text.strip() or "<" in text:
        raise ValueError("지적 본문에 태그가 있습니다.")
    return {"severity": None, "badge": False, "text": text}


def _parse_firm(cursor: _Cursor) -> dict:
    cursor.take('<button type="button" class="fss-badge" data-names="')
    name = cursor.until('">')
    shown = cursor.until("</button>")
    cursor.take('<div class="fss-original" hidden data-names="')
    original = cursor.until('">')
    if shown != name or original != name:
        raise ValueError(f"법인 이름 표기가 다릅니다: {name}")
    findings = []
    while cursor.start('<p class="fss-finding">'):
        findings.append(_parse_finding(cursor))
    cursor.take("</div>")
    if not findings:
        raise ValueError(f"지적이 없는 법인입니다: {name}")
    return {"name": name, "findings": findings}


def _parse_block(cursor: _Cursor) -> dict:
    if cursor.start('<div class="fss-gun">'):
        cursor.take('<div class="fss-gun"><p class="fss-gun-name">')
        gun = cursor.until("</p>")
        cursor.take('<p class="fss-none">')
        empty = cursor.until("</p></div>")
        if empty != "분류된 지적 없음":
            raise ValueError("빈 군 문장이 다릅니다.")
        return {"kind": "empty", "gun": gun}
    cursor.take('<article class="fss-group" data-names="')
    names = cursor.until('">')
    block: dict = {"kind": "firms"}
    if cursor.start('<p class="fss-gun-name">'):
        cursor.take('<p class="fss-gun-name">')
        block["gun"] = cursor.until("</p>")
    cursor.take('<div class="fss-badges">')
    firms = []
    while cursor.start("<button "):
        firms.append(_parse_firm(cursor))
    cursor.take("</div></article>")
    if names != "|".join(firm["name"] for firm in firms):
        raise ValueError("법인 묶음 이름이 다릅니다.")
    block["firms"] = firms
    return block


def _parse_group(cursor: _Cursor) -> dict:
    cursor.take('<section class="fss-jung"><h3>')
    heading = cursor.until("</h3>")
    cursor.take('<p class="fss-group-name">')
    name = cursor.until("</p>")
    blocks = []
    while cursor.start('<div class="fss-gun">') or cursor.start("<article "):
        blocks.append(_parse_block(cursor))
    cursor.take("</section>")
    if not blocks:
        raise ValueError(f"중분류에 카드가 없습니다: {heading}")
    return {"heading": heading, "name": name, "blocks": blocks}


def _parse_section(cursor: _Cursor) -> dict:
    cursor.take('<section class="fss-dae"><h2>')
    title = cursor.until("</h2>")
    section: dict = {"title": title}
    if cursor.start('<p class="fss-report">'):
        cursor.take('<p class="fss-report">')
        section["report"] = cursor.until("</p>")
    groups = []
    while cursor.start('<section class="fss-jung">'):
        groups.append(_parse_group(cursor))
    cursor.take("</section>")
    section["groups"] = groups
    return section


def _parse_bundle(cursor: _Cursor) -> dict:
    cursor.take('<div class="fss-bundle"><p class="fss-bundle-name">')
    name = cursor.until("</p>")
    bundle: dict = {"name": name}
    if cursor.start('<p class="fss-report">'):
        cursor.take('<p class="fss-report">')
        bundle["report"] = cursor.until("</p>")
    sections = []
    while cursor.start('<section class="fss-dae">'):
        sections.append(_parse_section(cursor))
    cursor.take("</div>")
    bundle["sections"] = sections
    return bundle


def _iter_year_firms(data: dict):
    for bundle in data["bundles"]:
        for section in bundle["sections"]:
            for group in section["groups"]:
                for block in group["blocks"]:
                    if block.get("kind") != "firms":
                        continue
                    yield from block["firms"]


def _inherit_severity(data: dict) -> None:
    for firm in _iter_year_firms(data):
        last = None
        for finding in firm["findings"]:
            if finding["badge"]:
                last = finding["severity"]
                continue
            if not last:
                raise ValueError(
                    f"심각도 뱃지 없이 시작하는 지적이 있습니다: {firm['name']}"
                )
            finding["severity"] = last


def parse_year_2025_html(year_html: str) -> dict:
    """감리연도 2025 블록을 데이터로 읽는다. 문장과 뱃지 위치는 그대로 둔다."""
    cursor = _Cursor(year_html)
    cursor.take('<div class="fss-year" data-year="2025"><h2>')
    title = cursor.until("</h2>")
    bundles = []
    while cursor.start('<div class="fss-bundle">'):
        bundles.append(_parse_bundle(cursor))
    cursor.take("</div>")
    if cursor.i != len(year_html):
        raise ValueError("2025 블록 뒤에 남은 HTML이 있습니다.")
    data = {"year": "2025", "title": title, "bundles": bundles}
    _inherit_severity(data)
    return data


def iter_year_findings(data: dict):
    """문서 순서의 (법인 이름, 지적) 쌍."""
    for firm in _iter_year_firms(data):
        for finding in firm["findings"]:
            yield firm["name"], finding


def _render_finding(finding: dict) -> str:
    text = _esc_text(finding["text"])
    if not finding["badge"]:
        return f'<p class="fss-finding">{text}</p>'
    severity = finding["severity"]
    css = _SEV_CLASS[severity]
    return (
        f'<p class="fss-finding"><span class="{css}">'
        f"{_esc_text(severity)}</span> {text}</p>"
    )


def _render_block(block: dict) -> str:
    if block["kind"] == "empty":
        gun = _esc_text(block["gun"])
        return (
            f'<div class="fss-gun"><p class="fss-gun-name">{gun}</p>'
            f'<p class="fss-none">분류된 지적 없음</p></div>'
        )
    gun = ""
    if "gun" in block:
        gun = f'<p class="fss-gun-name">{_esc_text(block["gun"])}</p>'
    names = "|".join(firm["name"] for firm in block["firms"])
    badges = []
    for firm in block["firms"]:
        name = _esc_attr(firm["name"])
        body = "".join(_render_finding(finding) for finding in firm["findings"])
        badges.append(
            f'<button type="button" class="fss-badge" data-names="{name}">'
            f'{_esc_text(firm["name"])}</button>'
            f'<div class="fss-original" hidden data-names="{name}">{body}</div>'
        )
    return (
        f'<article class="fss-group" data-names="{_esc_attr(names)}">{gun}'
        f'<div class="fss-badges">{"".join(badges)}</div></article>'
    )


def render_year_2025_html(data: dict) -> str:
    """데이터 파일을 발행 페이지의 2025 연도 블록으로 다시 만든다."""
    parts = [
        f'<div class="fss-year" data-year="{_esc_attr(data["year"])}">'
        f'<h2>{_esc_text(data["title"])}</h2>'
    ]
    for bundle in data["bundles"]:
        parts.append(
            f'<div class="fss-bundle"><p class="fss-bundle-name">{_esc_text(bundle["name"])}</p>'
        )
        if "report" in bundle:
            parts.append(f'<p class="fss-report">{_esc_text(bundle["report"])}</p>')
        for section in bundle["sections"]:
            parts.append(f'<section class="fss-dae"><h2>{_esc_text(section["title"])}</h2>')
            if "report" in section:
                parts.append(f'<p class="fss-report">{_esc_text(section["report"])}</p>')
            for group in section["groups"]:
                parts.append(
                    f'<section class="fss-jung"><h3>{_esc_text(group["heading"])}</h3>'
                    f'<p class="fss-group-name">{_esc_text(group["name"])}</p>'
                )
                for block in group["blocks"]:
                    parts.append(_render_block(block))
                parts.append("</section>")
            parts.append("</section>")
        parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)


def load_year_2025() -> dict:
    return json.loads(YEAR_2025_PATH.read_text(encoding="utf-8"))


def _year_2025_payload(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _write_year_2025_payload(payload: str) -> None:
    YEAR_2025_PATH.parent.mkdir(parents=True, exist_ok=True)
    YEAR_2025_PATH.write_text(payload, encoding="utf-8")


def materialize_review_markdown(text: str) -> str:
    """2025 훅을 데이터에서 렌더한 연도 블록으로 바꾼다. 훅이 없으면 그대로 둔다."""
    if YEAR_2025_MARK not in text:
        return text
    if text.count(YEAR_2025_MARK) != 1:
        raise ValueError("감리연도 2025 훅이 하나가 아닙니다.")
    return text.replace(YEAR_2025_MARK, render_year_2025_html(load_year_2025()), 1)


def _year_2025_span(text: str) -> tuple[int, int]:
    found: list[tuple[int, int]] = []
    for start, end in _year_regions(text):
        head = text[start : text.find(">", start) + 1]
        if 'data-year="2025"' in head:
            found.append((start, end))
    if len(found) != 1:
        raise ValueError("감리연도 2025 블록이 하나가 아닙니다.")
    return found[0]


def park_year_2025(text: str) -> tuple[str, str]:
    """JSON payload와 훅 페이지를 메모리에서 만든다. 렌더가 원문과 같기 전에는 쓰지 않는다."""
    start, end = _year_2025_span(text)
    block = text[start:end]
    data = parse_year_2025_html(block)
    if render_year_2025_html(data) != block:
        raise ValueError("감리연도 2025 블록을 같은 HTML로 보존할 수 없습니다.")
    payload = _year_2025_payload(data)
    page = text[:start] + YEAR_2025_MARK + text[end:]
    return page, payload


def commit_parked_year_2025(text: str, newline: str) -> None:
    """검증된 payload와 페이지 바이트를 연달아 쓴다. 검증에 실패하면 아무 파일도 쓰지 않는다."""
    page, payload = park_year_2025(text)
    page_bytes = page.replace("\r\n", "\n").replace("\n", newline).encode("utf-8")
    _write_year_2025_payload(payload)
    PAGE.write_bytes(page_bytes)


def _newline_of(raw: bytes) -> str:
    return "\r\n" if b"\r\n" in raw else "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="품질관리감리 중분류 아래 법인 목록을 검사하거나 다시 씁니다.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="같은 군·중분류의 요약을 빼고 회계법인 목록으로 다시 씁니다.",
    )
    args = parser.parse_args(argv)
    raw = PAGE.read_bytes()
    text = materialize_review_markdown(raw.decode("utf-8"))
    before = len(_ARTICLE.findall(text))
    rewritten = arrange_by_year(place_labels(collapse_document(text))) if args.write else text
    errors = audit_review_html(rewritten)
    if args.write:
        commit_parked_year_2025(rewritten, _newline_of(raw))
        after = len(_ARTICLE.findall(rewritten))
        print(f"cards {before} -> {after}")
    for message in errors:
        print(message, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
