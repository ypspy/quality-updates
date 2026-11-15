# -*- coding: utf-8 -*-
"""품질관리감리 2025 블록에 붙는 이행내역 공시 (F004).

연도 HTML을 데이터로 다시 읽어 바이트를 비교하는 검증 밖에, 빌드 hook 출력에만 넣는다.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import re
from pathlib import Path

import fss_review_cards

ROOT = Path(__file__).resolve().parent.parent
FOLLOWUP_PATH = ROOT / "data" / "fss-review" / "f004-followup.json"
_LOG = logging.getLogger("mkdocs.plugins.fss_f004")
_DISCLAIMER = (
    '<p class="fss-f004-disclaimer">'
    "회사가 DART에 공시한 이행내역 원문이며, 이 사이트가 검증하지 않았습니다."
    "</p>"
)

_SOURCE_KEYS = frozenset(
    {
        "recommendation",
        "action",
        "action_raw",
        "doc_notes",
        "action_text",
        "action_text_raw",
    }
)
_DAE_STANDARDS = frozenset(
    {
        "1. 회계법인 내 품질에 대한 리더십 책임",
        "2. 관련 윤리적 요구사항",
        "3. 의뢰인 관계 및 특정 업무의 수용과 유지",
        "4. 인적 자원",
        "5. 업무의 수행",
        "6. 모니터링",
    }
)
_DART_URL = re.compile(r"^https://dart\.fss\.or\.kr/dsaf001/main\.do\?rcpNo=\d{14}$")
_BANNED = "미" + "이행"
_BUNDLE_NAME = re.compile(r'<p class="fss-bundle-name">(.*?)</p>')
_DAE_TITLE = re.compile(r"<h2>(.*?)</h2>")


def _esc_text(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=False)


def _esc_attr(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _element_id(link_key: str) -> str:
    digest = hashlib.sha1(link_key.encode("utf-8")).hexdigest()[:10]
    return f"f004-2025-{digest}"


def _one_line(fragment: str) -> str:
    if "\n" in fragment or "\r" in fragment:
        raise ValueError("F004 출력에 줄바꿈이 있습니다.")
    return fragment


def _reject_banned(obj: object, *, skip: bool = False) -> None:
    if skip:
        return
    if isinstance(obj, str):
        if _BANNED in obj:
            raise ValueError("원문 필드 밖에 금지어가 있습니다.")
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            _reject_banned(value, skip=key in _SOURCE_KEYS)
        return
    if isinstance(obj, list):
        for value in obj:
            _reject_banned(value)


def _reject_dart_url(obj: object) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "dart_url":
                if not isinstance(value, str) or not _DART_URL.match(value):
                    raise ValueError("dart_url 형식이 아닙니다.")
            else:
                _reject_dart_url(value)
        return
    if isinstance(obj, list):
        for value in obj:
            _reject_dart_url(value)


def _validate_item(item: object, match_labels: dict, year_labels: dict, *, individual: bool) -> None:
    if not isinstance(item, dict):
        raise ValueError("항목이 객체가 아닙니다.")
    level = item.get("match_level")
    basis = item.get("year_basis")
    if level not in match_labels:
        raise ValueError("match_level을 알 수 없습니다.")
    if basis not in year_labels:
        raise ValueError("year_basis를 알 수 없습니다.")
    url = item.get("dart_url")
    if not isinstance(url, str) or not _DART_URL.match(url):
        raise ValueError("dart_url 형식이 아닙니다.")
    standard = item.get("dae_standard")
    if individual:
        if standard is not None and standard not in _DAE_STANDARDS:
            raise ValueError("dae_standard가 표준 여섯 값이 아닙니다.")
    elif standard not in _DAE_STANDARDS:
        raise ValueError("dae_standard가 표준 여섯 값이 아닙니다.")
    flag = item.get("date_mismatch")
    if not isinstance(flag, bool) or flag != (basis == "recommend_date_mismatch_exception"):
        raise ValueError("date_mismatch가 year_basis와 맞지 않습니다.")
    history = item.get("history") or []
    if not isinstance(history, list):
        raise ValueError("history가 목록이 아닙니다.")
    for row in history:
        if not isinstance(row, dict):
            raise ValueError("history 항목이 객체가 아닙니다.")
        hist_url = row.get("dart_url")
        if not isinstance(hist_url, str) or not _DART_URL.match(hist_url):
            raise ValueError("dart_url 형식이 아닙니다.")


def _manifest_path(path: Path) -> Path:
    name = path.name
    if name.endswith(".json"):
        return path.with_name(name[: -len(".json")] + ".manifest.json")
    return path.with_name(name + ".manifest.json")


def _verify_manifest(path: Path) -> None:
    """파일 바이트 sha256과 길이가 옆의 manifest와 같은지 확인한다."""
    if not path.is_file():
        raise FileNotFoundError("F004 파일이 없습니다.")
    manifest = _manifest_path(path)
    if not manifest.is_file():
        raise FileNotFoundError("F004 manifest가 없습니다.")
    try:
        meta = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("F004 manifest를 읽지 못했습니다.") from exc
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != meta.get("sha256") or len(raw) != meta.get("bytes"):
        raise ValueError("F004 sha256이 manifest와 다릅니다.")


def load_followup(path: Path = FOLLOWUP_PATH) -> dict:
    """UTF-8 JSON을 읽고 2025 이행내역 제약을 확인한다."""
    if Path(path).resolve() == Path(FOLLOWUP_PATH).resolve():
        _verify_manifest(Path(path))
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("이행내역 JSON이 객체가 아닙니다.")
    if data.get("inspection_year") != 2025:
        raise ValueError("inspection_year가 2025가 아닙니다.")
    labels = data.get("labels")
    if not isinstance(labels, dict):
        raise ValueError("labels가 없습니다.")
    match_labels = labels.get("match_level")
    year_labels = labels.get("year_basis")
    if not isinstance(match_labels, dict) or not isinstance(year_labels, dict):
        raise ValueError("labels에 match_level 또는 year_basis가 없습니다.")
    _reject_banned(data)
    _reject_dart_url(data)
    firms = data.get("firms")
    if not isinstance(firms, list):
        raise ValueError("firms가 목록이 아닙니다.")
    for firm in firms:
        if not isinstance(firm, dict):
            raise ValueError("법인 항목이 객체가 아닙니다.")
        for dae in firm.get("dae") or []:
            if not isinstance(dae, dict):
                raise ValueError("dae 항목이 객체가 아닙니다.")
            if dae.get("dae_standard") not in _DAE_STANDARDS:
                raise ValueError("dae_standard가 표준 여섯 값이 아닙니다.")
            items = dae.get("items") or []
            if not isinstance(items, list):
                raise ValueError("items가 목록이 아닙니다.")
            for item in items:
                _validate_item(item, match_labels, year_labels, individual=False)
        individual = firm.get("individual_audit") or []
        if not isinstance(individual, list):
            raise ValueError("individual_audit가 목록이 아닙니다.")
        for item in individual:
            _validate_item(item, match_labels, year_labels, individual=True)
    return data


def _meta_line(item: dict) -> str:
    parts: list[str] = []
    report = item.get("report_nm") or ""
    correction = item.get("correction_type") or ""
    if report and correction:
        parts.append(f"{_esc_text(report)} ({_esc_text(correction)})")
    elif report:
        parts.append(_esc_text(report))
    period = item.get("period_key")
    if period:
        fiscal = item.get("fiscal_year")
        if fiscal is not None and fiscal != "":
            parts.append(f"결산기 {_esc_text(period)} ({_esc_text(fiscal)})")
        else:
            parts.append(f"결산기 {_esc_text(period)}")
    if item.get("rcept_dt"):
        parts.append(f"접수일 {_esc_text(item['rcept_dt'])}")
    if item.get("dart_url") and item.get("rcept_no"):
        parts.append(
            f'<a href="{_esc_attr(item["dart_url"])}" rel="noopener" target="_blank">'
            f'{_esc_text(item["rcept_no"])}</a>'
        )
    standard = item.get("dae_standard")
    category = item.get("category_raw")
    if standard and category:
        parts.append(f"대분류 {_esc_text(standard)} (원문 구분: {_esc_text(category)})")
    elif standard:
        parts.append(f"대분류 {_esc_text(standard)}")
    elif category:
        parts.append(f"원문 구분: {_esc_text(category)}")
    if item.get("recommend_date_raw"):
        parts.append(f"권고일 {_esc_text(item['recommend_date_raw'])}")
    return '<p class="fss-f004-meta">' + " · ".join(parts) + "</p>"


def _labels_line(item: dict, labels: dict) -> str:
    spans: list[str] = []
    if item.get("year_basis") == "disclosure_year_fallback":
        spans.append(
            f'<span class="fss-f004-fallback">{_esc_text(item.get("year_basis_label") or "")}</span>'
        )
    if item.get("date_mismatch") is True:
        mismatch = labels["match_level"]["date_mismatch"]
        spans.append(f'<span class="fss-f004-mismatch">{_esc_text(mismatch)}</span>')
    if not spans:
        return ""
    return '<p class="fss-f004-labels">' + " ".join(spans) + "</p>"


def _history_block(item: dict) -> str:
    rows = item.get("history") or []
    if not rows:
        return ""
    parts = ['<div class="fss-f004-history"><p class="fss-f004-k">이전 공시</p>']
    for row in rows:
        changed = "이행 내용 다름" if row.get("action_changed") else "이행 내용 같음"
        link = (
            f'<a href="{_esc_attr(row.get("dart_url"))}" rel="noopener" target="_blank">'
            f'{_esc_text(row.get("rcept_no"))}</a>'
        )
        parts.append(
            f'<p class="fss-f004-hist">{_esc_text(row.get("rcept_dt"))} {_esc_text(row.get("correction_type"))}'
            f' · {link} · <span class="fss-f004-src">{_esc_text(row.get("action_text"))}</span>'
            f" ({changed})</p>"
        )
    parts.append("</div>")
    return "".join(parts)


def _render_item(item: dict, labels: dict) -> str:
    notes = []
    for note in item.get("doc_notes") or []:
        notes.append(f'<p class="fss-f004-note"><span class="fss-f004-src">{_esc_text(note)}</span></p>')
    return (
        '<div class="fss-f004-item">'
        + _meta_line(item)
        + _labels_line(item, labels)
        + '<p class="fss-f004-rec"><span class="fss-f004-k">개선권고</span> '
        + f'<span class="fss-f004-src">{_esc_text(item.get("recommendation"))}</span></p>'
        + '<p class="fss-f004-act"><span class="fss-f004-k">이행 내용</span> '
        + f'<span class="fss-f004-src">{_esc_text(item.get("action"))}</span></p>'
        + "".join(notes)
        + _history_block(item)
        + "</div>"
    )


def _memo_box(memo: object) -> str:
    if not memo:
        return ""
    return (
        '<div class="fss-f004-memo"><p class="fss-f004-memo-title">검토 메모</p>'
        f'<div class="fss-f004-memo-body">{_esc_text(memo)}</div></div>'
    )


def _disclosure_link(firm: dict) -> str:
    latest = firm.get("latest_2026_disclosure")
    if not isinstance(latest, dict):
        return ""
    url = latest.get("dart_url")
    number = latest.get("rcept_no")
    if not isinstance(url, str) or not _DART_URL.match(url) or not number:
        return ""
    return (
        f'<p class="fss-f004-latest"><a href="{_esc_attr(url)}" rel="noopener" target="_blank">'
        f"{_esc_text(number)}</a></p>"
    )


def _firm_details(firm: dict, dae: dict, labels: dict) -> str:
    items = dae.get("items") or []
    element_id = _element_id(str(dae["link_key"]))
    name = firm.get("firm") or ""
    body = "".join(_render_item(item, labels) for item in items)
    if not items and dae.get("f004_display") is not None:
        body = (
            f'<p class="fss-f004-none">{_esc_text(dae.get("f004_display"))}</p>'
            + _disclosure_link(firm)
        )
    return (
        f'<details class="fss-f004-firm" id="{_esc_attr(element_id)}" '
        f'data-f004-firm="{_esc_attr(name)}">'
        f'<summary><span class="fss-f004-firm-name">{_esc_text(name)}</span> '
        f'<span class="fss-f004-count">{len(items)}건</span> '
        f'<a class="fss-f004-anchor" href="#{_esc_attr(element_id)}">#</a></summary>'
        f"{body}{_memo_box(dae.get('review_memo') or '')}</details>"
    )


def render_dae_block(bundle_firms: list[dict], dae_title: str, labels: dict) -> str:
    """한 묶음의 한 대분류 끝에 붙일 이행내역. 해당 법인이 없으면 빈 문자열."""
    details = []
    for firm in bundle_firms:
        for dae in firm.get("dae") or []:
            if dae.get("dae_standard") == dae_title:
                details.append(_firm_details(firm, dae, labels))
    if not details:
        return ""
    return _one_line(
        f'<div class="fss-f004-block" data-f004-dae="{_esc_attr(dae_title)}">'
        '<p class="fss-f004-title">이행내역 공시 (F004)</p>'
        + _DISCLAIMER
        + "".join(details)
        + "</div>"
    )


def render_individual_block(bundle_firms: list[dict], labels: dict) -> str:
    """법인별 개별 감사보고서 이행내역. 항목이 없는 법인은 뺀다."""
    blocks = []
    for firm in bundle_firms:
        items = firm.get("individual_audit") or []
        if not items:
            continue
        name = firm.get("firm") or ""
        body = "".join(_render_item(item, labels) for item in items)
        blocks.append(
            f'<div class="fss-f004-individual" data-f004-firm="{_esc_attr(name)}">'
            '<p class="fss-f004-title">개별 감사보고서 관련 이행내역</p>'
            f'<p><span class="fss-f004-firm-name">{_esc_text(name)}</span> '
            f'<span class="fss-f004-count">{len(items)}건</span></p>'
            f"{body}</div>"
        )
    if not blocks:
        return ""
    return _one_line(
        '<div class="fss-f004-individual-group">'
        + _DISCLAIMER
        + "".join(blocks)
        + "</div>"
    )


def _firms_by_bundle(data: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for firm in data.get("firms") or []:
        grouped.setdefault(firm.get("bundle"), []).append(firm)
    return grouped


def _inject_bundle(bundle_html: str, firms: list[dict], labels: dict) -> str:
    """firms는 이 묶음 법인만, firms[] 순서대로다."""
    if not _BUNDLE_NAME.search(bundle_html):
        raise ValueError("묶음 이름이 없습니다.")
    parts: list[str] = []
    cursor = 0
    for start, end in fss_review_cards._iter_sections(bundle_html, "fss-dae"):
        section = bundle_html[start:end]
        title_match = _DAE_TITLE.search(section)
        if not title_match:
            raise ValueError("대분류 제목이 없습니다.")
        if not section.endswith("</section>"):
            raise ValueError("대분류 절이 닫히지 않습니다.")
        title = html.unescape(title_match.group(1))
        extra = render_dae_block(firms, title, labels)
        parts.append(bundle_html[cursor:start])
        parts.append(section[: -len("</section>")] + extra + "</section>")
        cursor = end
    parts.append(bundle_html[cursor:])
    injected = "".join(parts)
    if not injected.endswith("</div>"):
        raise ValueError("묶음이 닫히지 않습니다.")
    individual = render_individual_block(firms, labels)
    return injected[: -len("</div>")] + individual + "</div>"


def _site_firm_names(block: str) -> set[str]:
    names: set[str] = set()
    for raw in re.findall(r'data-names="([^"]*)"', block):
        for part in html.unescape(raw).split("|"):
            if part:
                names.add(part)
    return names


def _bundle_titles(block: str) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for start, end in fss_review_cards._regions(block, '<div class="fss-bundle">'):
        bundle_html = block[start:end]
        name_match = _BUNDLE_NAME.search(bundle_html)
        if not name_match:
            continue
        titles: set[str] = set()
        for section_start, section_end in fss_review_cards._iter_sections(bundle_html, "fss-dae"):
            title_match = _DAE_TITLE.search(bundle_html[section_start:section_end])
            if title_match:
                titles.add(html.unescape(title_match.group(1)))
        found[html.unescape(name_match.group(1))] = titles
    return found


def _classify(data: dict, bundles: dict[str, set[str]], site_firms: set[str]) -> tuple[list[str], list[str], int]:
    """렌더할 link_key, 사이트에 없는 link_key, no_site_dae 항목 수."""
    matched: list[str] = []
    unmatched: list[str] = []
    no_site = 0
    for firm in data.get("firms") or []:
        bundle = firm.get("bundle")
        name = firm.get("firm") or ""
        off_site = bundle not in bundles or (bool(site_firms) and name not in site_firms)
        titles = bundles.get(bundle, set())
        for dae in firm.get("dae") or []:
            link_key = str(dae.get("link_key") or "")
            if off_site or dae.get("dae_standard") not in titles:
                unmatched.append(link_key)
            else:
                matched.append(link_key)
            for item in dae.get("items") or []:
                if item.get("match_level") == "no_site_dae":
                    no_site += 1
        for item in firm.get("individual_audit") or []:
            if item.get("match_level") == "no_site_dae":
                no_site += 1
    return matched, unmatched, no_site


def _visible_firms(firms: list[dict], site_firms: set[str]) -> list[dict]:
    if not site_firms:
        return firms
    return [firm for firm in firms if (firm.get("firm") or "") in site_firms]


def _summary(data: dict, matched: list[str], unmatched: list[str], no_site: int) -> str:
    matched_set = set(matched)
    firms: set[str] = set()
    slots = 0
    items = 0
    history = 0
    for firm in data.get("firms") or []:
        for dae in firm.get("dae") or []:
            if str(dae.get("link_key") or "") not in matched_set:
                continue
            firms.add(firm.get("firm") or "")
            slots += 1
            rows = dae.get("items") or []
            items += len(rows)
            history += sum(len(row.get("history") or []) for row in rows)
    zero_slots = 0
    zero_items = 0
    for firm in data.get("firms") or []:
        for dae in firm.get("dae") or []:
            if str(dae.get("link_key") or "") not in matched_set:
                continue
            rows = dae.get("items") or []
            if dae.get("site_finding_count") == 0 and rows:
                zero_slots += 1
                zero_items += len(rows)
    return (
        f"F004 이행내역: 법인 {len(firms)}, 대분류 {slots}, 항목 {items}, "
        f"이전 공시 {history}, 비매칭 {len(unmatched)}, 사이트 대분류 없음 {no_site}, "
        f"사이트 지적 0칸 {zero_slots}칸/{zero_items}건"
    )


def _insert_followup(page: str, data: dict, *, strict: bool) -> str:
    found: list[tuple[int, int]] = []
    for start, end in fss_review_cards._year_regions(page):
        head_end = page.find(">", start)
        if head_end < 0:
            raise ValueError("감리연도 태그가 닫히지 않았습니다.")
        if 'data-year="2025"' in page[start : head_end + 1]:
            found.append((start, end))
    if len(found) != 1:
        raise ValueError("감리연도 2025 블록이 하나가 아닙니다.")
    start, end = found[0]
    block = page[start:end]
    bundles = _bundle_titles(block)
    site_firms = _site_firm_names(block)
    matched, unmatched, no_site = _classify(data, bundles, site_firms)
    if strict and unmatched:
        raise ValueError("대분류 이행내역을 한 번씩 그리지 못했습니다.")
    by_bundle = _firms_by_bundle(data)
    parts: list[str] = []
    cursor = 0
    for bundle_start, bundle_end in fss_review_cards._regions(block, '<div class="fss-bundle">'):
        bundle_html = block[bundle_start:bundle_end]
        name_match = _BUNDLE_NAME.search(bundle_html)
        if not name_match:
            raise ValueError("묶음 이름이 없습니다.")
        bundle_name = html.unescape(name_match.group(1))
        firms = _visible_firms(by_bundle.get(bundle_name, []), site_firms)
        parts.append(block[cursor:bundle_start])
        parts.append(_inject_bundle(bundle_html, firms, data["labels"]))
        cursor = bundle_end
    parts.append(block[cursor:])
    updated = "".join(parts)
    if updated.count('class="fss-f004-firm"') != len(matched):
        raise ValueError("대분류 이행내역을 한 번씩 그리지 못했습니다.")
    for link_key in matched:
        if updated.count(f'id="{_element_id(link_key)}"') != 1:
            raise ValueError("대분류 이행내역을 한 번씩 그리지 못했습니다.")
    if ("\n" not in block and "\r" not in block) and ("\n" in updated or "\r" in updated):
        raise ValueError("F004 출력에 줄바꿈이 있습니다.")
    _LOG.info("%s", _summary(data, matched, unmatched, no_site))
    return page[:start] + updated + page[end:]


def inject_f004_followup(page: str, data: dict | None = None, *, strict: bool | None = None) -> str:
    """2025 연도 블록의 대분류 절 끝에 이행내역을 붙인다. 블록 밖은 그대로 둔다.

    파일을 직접 읽는 빌드 경로는 실패 대신 입력 페이지를 그대로 돌려준다.
    ``data``를 넘기면 기본은 엄격하다. ``strict=False``면 사이트에 없는 키만 건너뛴다.
    """
    original = page
    cleaned = strip_f004_followup(page)
    if data is None:
        try:
            data = load_followup(FOLLOWUP_PATH)
        except (OSError, ValueError) as exc:
            _LOG.info("F004 이행내역을 붙이지 않습니다: %s", exc)
            return original
        try:
            return _insert_followup(cleaned, data, strict=False)
        except ValueError as exc:
            _LOG.info("F004 이행내역을 붙이지 않습니다: %s", exc)
            return original
    if strict is None:
        strict = True
    return _insert_followup(cleaned, data, strict=strict)


def strip_f004_followup(page: str) -> str:
    """hook이 붙인 이행내역 블록을 지운다."""
    needles = (
        '<div class="fss-f004-block"',
        '<div class="fss-f004-individual-group"',
        '<div class="fss-f004-individual"',
    )
    spans: list[tuple[int, int]] = []
    for needle in needles:
        spans.extend(fss_review_cards._regions(page, needle))
    outer = [
        (start, end)
        for start, end in spans
        if not any(os <= start and end <= oe and (os, oe) != (start, end) for os, oe in spans)
    ]
    for start, end in sorted(outer, reverse=True):
        page = page[:start] + page[end:]
    return page
