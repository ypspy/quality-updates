# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import sys
from collections import Counter
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_f004_followup_render as check_mod  # noqa: E402
import fss_f004_followup  # noqa: E402
from fss_f004_followup import (  # noqa: E402
    FOLLOWUP_PATH,
    inject_f004_followup,
    load_followup,
    render_dae_block,
    render_individual_block,
    strip_f004_followup,
)
from fss_review_cards import (  # noqa: E402
    PAGE,
    YEAR_2025_PATH,
    audit_review_html,
    materialize_review_markdown,
)
from mkdocs_fss_review_year import on_page_markdown  # noqa: E402
from tests.test_fss_review_cards import (  # noqa: E402
    SEV_SHA,
    TEXT_SHA,
    YEAR_SHA,
    _Page,
    finding_records,
)

# sha256sum data/fss-review/f004-followup.json
FOLLOWUP_SHA = "617ccf2d8dd778c7235c6f9809b3fe57ea0798226b25eabc407b2f47e9132798"
# wc -c data/fss-review/f004-followup.json
FOLLOWUP_BYTES = 365025

# python scripts/check_f004_followup_render.py 출력 (main 94f4882 + 이 브랜치, 2026-11-15)
N_FIRMS = 78
N_DAE = 212
N_DAE_WITH_ITEMS = 90
N_ITEMS = 143
N_INDIVIDUAL = 0
N_HISTORY = 9
N_FALLBACK = 8
N_MISMATCH = 16
N_NONE_EMPTY = 86
N_NONE_NA = 34
N_DISPLAY_NULL = 90
N_NO_FINDING = 2
N_META_NO_DATE = 8
# 예지 7, 정일 3, 길인 3, 신성 2, 상록 1
MISMATCH_BY_FIRM = {
    "예지회계법인": 7,
    "정일회계법인": 3,
    "회계법인 길인": 3,
    "신성회계법인": 2,
    "상록회계법인": 1,
}
MATCH_LEVELS = {
    "matched_high": 45,
    "matched_medium": 72,
    "no_site_dae": 2,
    "year_fallback": 8,
    "date_mismatch": 16,
}

DAE = "5. 업무의 수행"
DART = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260630000001"


def _banned() -> str:
    return "미" + "이행"


def _sha_lines(lines) -> tuple[str, int]:
    blob = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), len(blob)


def _labels() -> dict:
    return {
        "match_level": {
            "matched_high": "권고일·대분류 일치",
            "date_mismatch": "권고일 표기 불일치",
            "year_fallback": "권고일 없음 · 공시 연도로 추정",
            "individual_audit": "개별 감사보고서",
        },
        "year_basis": {
            "recommend_date": "권고일 연도 − 1",
            "disclosure_year_fallback": "권고일 없음 → 처음 공시 연도 − 1 (대체)",
            "recommend_date_mismatch_exception": "권고일 표기 불일치 (예외)",
        },
    }


def _item(**kwargs) -> dict:
    item = {
        "report_nm": "회계법인사업보고서",
        "correction_type": "최초공시",
        "fiscal_year": 2026,
        "period_key": "2026-03",
        "rcept_dt": "2026-06-30",
        "rcept_no": "20260630000001",
        "dart_url": DART,
        "dae_standard": DAE,
        "category_raw": "업무의 수행",
        "recommend_date_raw": "2026.03.20",
        "recommendation": "원문 권고",
        "action": "기재 없음",
        "action_raw": "원문 조치",
        "doc_notes": [],
        "match_level": "matched_high",
        "match_level_label": "권고일·대분류 일치",
        "year_basis": "recommend_date",
        "year_basis_label": "권고일 연도 − 1",
        "date_mismatch": False,
        "history": [],
        "review_memo": "",
    }
    item.update(kwargs)
    return item


def _dae(firm: str = "회계법인 현", standard: str = DAE, items=None, display=None, memo: str = "") -> dict:
    return {
        "link_key": f"{firm}|2025|{standard}",
        "inspection_year": 2025,
        "dae_standard": standard,
        "items": [] if items is None else items,
        "f004_display": display,
        "review_memo": memo,
    }


def _firm(bundle: str, name: str, dae=None, individual=None, status: str = "has_items") -> dict:
    return {
        "firm": name,
        "bundle": bundle,
        "f004_status": status,
        "dae": [] if dae is None else dae,
        "individual_audit": [] if individual is None else individual,
    }


def _payload(firms: list[dict], labels: dict | None = None) -> dict:
    return {"inspection_year": 2025, "labels": _labels() if labels is None else labels, "firms": firms}


def _page(bundles: list[tuple[str, list[str]]]) -> str:
    parts = ['<div class="fss-year" data-year="2025"><h2>2025년</h2>']
    for name, titles in bundles:
        parts.append(f'<div class="fss-bundle"><p class="fss-bundle-name">{name}</p>')
        for title in titles:
            parts.append(f'<section class="fss-dae"><h2>{title}</h2></section>')
        parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "followup.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _iter_items(data: dict):
    for firm in data["firms"]:
        for dae in firm["dae"]:
            for item in dae["items"]:
                yield firm, dae, item


@pytest.fixture(scope="module")
def built_page() -> tuple[str, str]:
    source = PAGE.read_text(encoding="utf-8")
    built = on_page_markdown(source, _Page("fss-review/index.md"), None, None)
    return source, built


def test_followup_file_matches_locked_counts():
    raw = FOLLOWUP_PATH.read_bytes()
    assert len(raw) == FOLLOWUP_BYTES
    assert hashlib.sha256(raw).hexdigest() == FOLLOWUP_SHA
    data = load_followup()
    assert data["version"] == "draft-2026-11-15-v4"
    assert data["status"] == "draft"
    assert {firm["alias_status"] for firm in data["firms"]} == {"proposed"}
    year = json.loads(YEAR_2025_PATH.read_text(encoding="utf-8"))
    year_names = {
        firm["name"]
        for bundle in year["bundles"]
        for section in bundle["sections"]
        for group in section["groups"]
        for block in group["blocks"]
        if block.get("kind") == "firms"
        for firm in block["firms"]
    }
    assert {firm["firm"] for firm in data["firms"]} == year_names
    assert len(data["firms"]) == len(year_names) == N_FIRMS
    dae_rows = [dae for firm in data["firms"] for dae in firm["dae"]]
    items = [item for _firm_row, _dae_row, item in _iter_items(data)]
    assert len(dae_rows) == N_DAE
    assert sum(1 for dae in dae_rows if dae["items"]) == N_DAE_WITH_ITEMS
    assert len(items) == N_ITEMS
    assert sum(len(firm["individual_audit"]) for firm in data["firms"]) == N_INDIVIDUAL
    assert sum(len(item["history"]) for item in items) == N_HISTORY
    assert sum(1 for item in items if item["year_basis"] == "disclosure_year_fallback") == N_FALLBACK
    assert sum(1 for item in items if item["date_mismatch"] is True) == N_MISMATCH
    mismatch_firms = Counter(
        firm["firm"] for firm, _dae_row, item in _iter_items(data) if item["date_mismatch"]
    )
    assert dict(mismatch_firms) == MISMATCH_BY_FIRM
    display = Counter(dae["f004_display"] for dae in dae_rows)
    assert display["기재 없음"] == N_NONE_EMPTY
    assert display["해당 없음"] == N_NONE_NA
    assert display["지적사항 없음"] == N_NO_FINDING
    assert display[None] == N_DISPLAY_NULL
    finding_ids = {
        row.get("row_id")
        for dae in dae_rows
        for row in dae.get("no_finding_rows") or []
    }
    assert finding_ids == {"20260930000134:0:5", "20260930000134:0:11"}
    item_ids = {item.get("row_id") for item in items}
    assert finding_ids.isdisjoint(item_ids)
    assert Counter(item["match_level"] for item in items) == MATCH_LEVELS
    assert sum(
        1
        for item in items
        if item["year_basis"] == "disclosure_year_fallback" and item["date_mismatch"]
    ) == 0


def test_hook_output_keeps_year_bytes_and_counts(built_page):
    source, built = built_page
    assert strip_f004_followup(built) == materialize_review_markdown(source)
    assert built.count('data-year="2025"') == 1
    assert audit_review_html(built) == []
    soup = BeautifulSoup(built, "html.parser")
    for div in soup.select("div.fss-year"):
        year = div.get("data-year")
        if year == "2025":
            continue
        assert hashlib.sha256(str(div).encode("utf-8")).hexdigest() == YEAR_SHA[year]
    stripped = BeautifulSoup(strip_f004_followup(built), "html.parser")
    year_2025 = stripped.select_one('div.fss-year[data-year="2025"]')
    assert hashlib.sha256(str(year_2025).encode("utf-8")).hexdigest() == YEAR_SHA["2025"]
    assert len(soup.select(".fss-f004-firm")) == N_DAE
    assert len(soup.select(".fss-f004-item")) == N_ITEMS
    assert len(soup.select(".fss-f004-hist")) == N_HISTORY
    assert len(soup.select(".fss-f004-fallback")) == N_FALLBACK
    assert len(soup.select(".fss-f004-mismatch")) == N_MISMATCH
    assert len(soup.select(".fss-f004-individual")) == N_INDIVIDUAL
    assert len(soup.select(".fss-f004-nofinding")) == N_NO_FINDING
    metas = [node.get_text() for node in soup.select(".fss-f004-meta")]
    assert sum("권고일 기재 없음" in text for text in metas) == N_META_NO_DATE
    assert sum("권고일 -" in text for text in metas) == 0
    records = finding_records(soup.select_one('div.fss-year[data-year="2025"]'))
    assert len(records) == 370
    assert len({record["firm"] for record in records}) == N_FIRMS
    assert _sha_lines(record["text"] for record in records) == (TEXT_SHA, 129054)
    assert _sha_lines(f'{record["severity"]}\t{record["text"]}' for record in records) == (SEV_SHA, 133729)


def test_recommendation_and_firm_name_are_escaped():
    name = '가&"나"'
    recommendation = '<b>&"x"</b>'
    firm = _firm("일반회계법인", name, dae=[_dae(firm=name, items=[_item(recommendation=recommendation)])])
    rendered = render_dae_block([firm], DAE, _labels())
    assert "<b>" not in rendered
    assert '&lt;b&gt;&amp;"x"&lt;/b&gt;' in rendered
    assert f'data-f004-firm="{html_escape_attr(name)}"' in rendered
    assert f'<span class="fss-f004-firm-name">{html_escape_text(name)}</span>' in rendered


def html_escape_text(value: str) -> str:
    return value.replace("&", "&amp;")


def html_escape_attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;")


def test_empty_dae_shows_display_text():
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae(display="기재 없음")])
    rendered = render_dae_block([firm], DAE, _labels())
    soup = BeautifulSoup(rendered, "html.parser")
    assert soup.select_one(".fss-f004-none").get_text(strip=True) == "기재 없음"
    assert soup.select(".fss-f004-item") == []


def test_audit_team_without_rows_shows_display_text():
    firm = _firm(
        "감사반",
        "나라공인회계사감사반(제47호)",
        dae=[_dae(firm="나라공인회계사감사반(제47호)", display="해당 없음")],
        status="해당 없음",
    )
    rendered = render_dae_block([firm], DAE, _labels())
    soup = BeautifulSoup(rendered, "html.parser")
    assert firm["f004_status"] == "해당 없음"
    assert soup.select_one(".fss-f004-none").get_text(strip=True) == "해당 없음"
    assert soup.select(".fss-f004-item") == []


def test_fallback_label_only_on_fallback_items():
    label = "대체 표시 문구"
    fallback = _item(
        year_basis="disclosure_year_fallback",
        year_basis_label=label,
        match_level="year_fallback",
        match_level_label="권고일 없음 · 공시 연도로 추정",
        rcept_no="20260630000002",
        dart_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260630000002",
    )
    ordinary = _item()
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[fallback, ordinary])])
    soup = BeautifulSoup(render_dae_block([firm], DAE, _labels()), "html.parser")
    marks = soup.select(".fss-f004-fallback")
    assert len(marks) == 1
    assert marks[0].get_text(strip=True) == label
    assert soup.select(".fss-f004-item")[1].select(".fss-f004-fallback") == []


def test_date_mismatch_mark_keeps_raw_recommend_date():
    labels = _labels()
    labels["match_level"]["date_mismatch"] = "표기 확인"
    mismatched = _item(
        date_mismatch=True,
        year_basis="recommend_date_mismatch_exception",
        match_level="date_mismatch",
        match_level_label="권고일 표기 불일치",
        recommend_date_raw="2025.05.12",
    )
    ordinary = _item(
        rcept_no="20260630000002",
        dart_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260630000002",
    )
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[mismatched, ordinary])])
    soup = BeautifulSoup(render_dae_block([firm], DAE, labels), "html.parser")
    first, second = soup.select(".fss-f004-item")
    mark = first.select_one(".fss-f004-mismatch")
    assert mark is not None
    assert mark.get_text(strip=True) == "표기 확인"
    assert first.select_one(".fss-f004-level") is None
    assert "2025.05.12" in first.select_one(".fss-f004-meta").get_text()
    assert second.select_one(".fss-f004-mismatch") is None
    assert first.select_one(".fss-f004-fallback") is None


def test_real_mismatch_counts_and_raw_dates(built_page):
    _source, built = built_page
    soup = BeautifulSoup(built, "html.parser")
    counts: Counter[str] = Counter()
    raw_seen = False
    both = 0
    for item in soup.select(".fss-f004-item"):
        has_mismatch = item.select_one(".fss-f004-mismatch") is not None
        has_fallback = item.select_one(".fss-f004-fallback") is not None
        if has_mismatch and has_fallback:
            both += 1
        if not has_mismatch:
            continue
        firm = item.find_parent(class_="fss-f004-firm")
        counts[firm.get("data-f004-firm")] += 1
        assert item.select_one(".fss-f004-mismatch").get_text(strip=True) == "권고일 표기 불일치"
        if "2025.05.12" in item.select_one(".fss-f004-meta").get_text():
            raw_seen = True
    assert both == 0
    assert dict(counts) == MISMATCH_BY_FIRM
    assert sum(counts.values()) == N_MISMATCH
    assert raw_seen


def test_anchors_belong_only_to_firm_blocks():
    history = {
        "rcept_no": "20260930000001",
        "rcept_dt": "2026-09-30",
        "correction_type": "기재정정",
        "period_key": "2026-03",
        "dart_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260930000001",
        "action_text": "이전 원문",
        "action_changed": False,
    }
    changed = dict(history)
    changed["rcept_no"] = "20260930000002"
    changed["dart_url"] = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260930000002"
    changed["action_changed"] = True
    item = _item(history=[history, changed], doc_notes=["주석 원문"])
    link_key = "회계법인 현|2025|" + DAE
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[item])])
    individual = _item(
        dae_standard=None,
        match_level="individual_audit",
        match_level_label="개별 감사보고서",
        rcept_no="20260630000009",
        dart_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260630000009",
    )
    other = _firm("일반회계법인", "다른 법인", individual=[individual])
    page = "앞" + _page([("일반회계법인", [DAE])]) + "뒤"
    built = inject_f004_followup(page, _payload([firm, other]))
    expected_id = "f004-2025-" + hashlib.sha1(link_key.encode("utf-8")).hexdigest()[:10]
    soup = BeautifulSoup(built, "html.parser")
    identified = soup.select("[id]")
    assert [node.get("id") for node in identified] == [expected_id]
    assert identified[0].get("class") == ["fss-f004-firm"]
    assert identified[0].select_one(".fss-f004-anchor").get("href") == f"#{expected_id}"
    for selector in (".fss-f004-item", ".fss-f004-hist", ".fss-f004-individual"):
        for node in soup.select(selector):
            assert not node.select("[id]")
            for link in node.select("a[href]"):
                assert not link["href"].startswith("#")
    for link in soup.select(".fss-f004-item a[href]"):
        assert link["href"].startswith("https://dart.fss.or.kr/dsaf001/main.do?rcpNo=")
    hist_text = " ".join(node.get_text() for node in soup.select(".fss-f004-hist"))
    assert "이행 내용 같음" in hist_text
    assert "이행 내용 다름" in hist_text
    assert "\n" not in built


def test_banned_word_in_source_stays_inside_span():
    word = _banned()
    item = _item(recommendation=f"앞 {word} 뒤", doc_notes=[f"주석 {word}"])
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[item])])
    rendered = render_dae_block([firm], DAE, _labels())
    soup = BeautifulSoup(rendered, "html.parser")
    inside = "".join(span.get_text() for span in soup.select("span.fss-f004-src"))
    for span in soup.select("span.fss-f004-src"):
        span.decompose()
    assert inside.count(word) == 2
    assert word not in soup.get_text("\n")


def test_banned_word_outside_source_is_rejected(tmp_path):
    word = _banned()
    shown = _payload([
        _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[_item(action_raw=word)])])
    ])
    load_followup(_write(tmp_path, shown))
    hidden = render_dae_block(shown["firms"], DAE, shown["labels"])
    assert word not in hidden
    rejected = _payload([
        _firm("일반회계법인", "회계법인 현", dae=[_dae(display=word)])
    ])
    with pytest.raises(ValueError):
        load_followup(_write(tmp_path, rejected))


def test_real_page_banned_word_is_only_inside_source_span(built_page):
    _source, built = built_page
    word = _banned()
    soup = BeautifulSoup(built, "html.parser")
    inside = 0
    outside = 0
    for region in soup.select("div.fss-f004-block, div.fss-f004-individual"):
        for span in region.select("span.fss-f004-src"):
            inside += span.get_text().count(word)
            span.decompose()
        outside += region.get_text("\n").count(word)
    assert outside == 0
    assert inside == 1


def test_individual_block_is_per_firm_and_has_no_id():
    item = _item(
        dae_standard=None,
        match_level="individual_audit",
        match_level_label="개별 감사보고서",
    )
    filled = _firm("일반회계법인", "회계법인 현", individual=[item])
    empty = _firm("일반회계법인", "빈 법인")
    rendered = render_individual_block([filled, empty], _labels())
    assert rendered.count('class="fss-f004-individual"') == 1
    assert " id=" not in rendered
    page = _page([("일반회계법인", [DAE])])
    built = inject_f004_followup(page, _payload([filled, empty]))
    assert built.count('class="fss-f004-individual"') == 1
    assert built.index("</section>") < built.index("fss-f004-individual") < built.rindex("</div></div>")
    assert " id=" not in built


def test_review_memo_is_empty_or_escaped():
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae(display="기재 없음")])
    empty = render_dae_block([firm], DAE, _labels())
    assert "fss-f004-memo" not in empty
    filled = _firm(
        "일반회계법인",
        "회계법인 현",
        dae=[_dae(display="기재 없음", memo="<i>메모</i>")],
    )
    rendered = render_dae_block([filled], DAE, _labels())
    assert "&lt;i&gt;메모&lt;/i&gt;" in rendered
    assert "<i>" not in rendered


def test_missing_section_bad_url_and_unknown_level_raise(tmp_path):
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae()])
    page = _page([("일반회계법인", ["4. 인적 자원"])])
    with pytest.raises(ValueError):
        inject_f004_followup(page, _payload([firm]))
    bad_url = _payload([
        _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[_item(dart_url="https://example.invalid/x")])])
    ])
    with pytest.raises(ValueError):
        load_followup(_write(tmp_path, bad_url))
    bad_level = _payload([
        _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[_item(match_level="not-a-level")])])
    ])
    with pytest.raises(ValueError):
        load_followup(_write(tmp_path, bad_level))


def test_strip_round_trip_restores_the_page():
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[_item()])])
    page = "앞" + _page([("일반회계법인", [DAE])]) + "뒤"
    built = inject_f004_followup(page, _payload([firm]))
    assert built != page
    assert strip_f004_followup(built) == page
    assert "\n" not in built


def test_check_script_writes_report_on_success(tmp_path):
    report = tmp_path / "r.json"
    assert check_mod.main(["--report", str(report)]) == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["firms"] == N_FIRMS
    assert payload["findings"] == 370
    assert payload["fss_f004_firm"] == N_DAE
    assert payload["fss_f004_item"] == N_ITEMS
    assert payload["fss_f004_nofinding"] == N_NO_FINDING
    assert payload["meta_no_date"] == N_META_NO_DATE
    assert payload["fss_f004_hist"] == N_HISTORY
    assert payload["fss_f004_fallback"] == N_FALLBACK
    assert payload["fss_f004_mismatch"] == N_MISMATCH
    assert payload["fss_f004_none_empty"] == N_NONE_EMPTY
    assert payload["fss_f004_none_na"] == N_NONE_NA
    assert payload["fss_f004_individual"] == N_INDIVIDUAL
    assert payload["anchors"] == N_DAE
    assert payload["anchors_only_on_firm"] is True
    assert payload["prior_year_sha_match"] is True
    assert payload["strip_equals_materialize"] is True
    assert payload["audit_error_count"] == 0
    assert payload["banned_outside"] == 0
    assert payload["banned_inside"] == 1
    assert payload["errors"] == []
    assert payload["followup_sha256"] == FOLLOWUP_SHA
    assert "firms: 78" in payload["text"]
    assert [path.name for path in tmp_path.iterdir()] == ["r.json"]


def test_check_script_keeps_existing_report_when_data_breaks(tmp_path, monkeypatch):
    report = tmp_path / "r.json"
    report.write_text("keep", encoding="utf-8")
    broken = _payload([
        _firm(
            "일반회계법인",
            "회계법인 현",
            dae=[_dae(items=[_item(dart_url="https://example.invalid/x")])],
        )
    ])
    monkeypatch.setattr(check_mod, "FOLLOWUP_PATH", _write(tmp_path, broken))
    assert check_mod.main(["--report", str(report)]) == 1
    assert report.read_text(encoding="utf-8") == "keep"
    assert all(not path.name.startswith("tmp") for path in tmp_path.iterdir())


def test_check_script_removes_temp_file_when_replace_fails(tmp_path, monkeypatch):
    def boom(_src, _dst):
        raise OSError("replace failed")

    monkeypatch.setattr(check_mod.os, "replace", boom)
    report = tmp_path / "r.json"
    assert check_mod.main(["--report", str(report)]) == 1
    assert not report.exists()
    assert list(tmp_path.iterdir()) == []


_DISCLAIMER = "회사가 DART에 공시한 이행내역 원문이며, 이 사이트가 검증하지 않았습니다."


def _hook(source: str, caplog) -> str:
    with caplog.at_level(logging.INFO, logger="mkdocs.plugins.fss_f004"):
        return on_page_markdown(source, _Page("fss-review/index.md"), None, None)


def test_missing_file_keeps_the_materialized_page(monkeypatch, caplog):
    monkeypatch.setattr(fss_f004_followup, "FOLLOWUP_PATH", Path("/tmp/f004-followup-missing.json"))
    source = PAGE.read_text(encoding="utf-8")
    built = _hook(source, caplog)
    assert built == materialize_review_markdown(source)
    assert "F004 이행내역을 붙이지 않습니다" in caplog.text


def test_sha_mismatch_keeps_the_materialized_page(tmp_path, monkeypatch, caplog):
    raw = bytearray(FOLLOWUP_PATH.read_bytes())
    raw[20] ^= 0x01
    path = tmp_path / "f004-followup.json"
    path.write_bytes(raw)
    (tmp_path / "f004-followup.manifest.json").write_text(
        json.dumps({"file": "f004-followup.json", "sha256": FOLLOWUP_SHA, "bytes": FOLLOWUP_BYTES}),
        encoding="utf-8",
    )
    monkeypatch.setattr(fss_f004_followup, "FOLLOWUP_PATH", path)
    source = PAGE.read_text(encoding="utf-8")
    built = _hook(source, caplog)
    assert built == materialize_review_markdown(source)
    assert "sha256" in caplog.text


def test_missing_manifest_and_broken_json_keep_the_page(tmp_path, monkeypatch, caplog):
    source = PAGE.read_text(encoding="utf-8")
    expected = materialize_review_markdown(source)
    plain = tmp_path / "f004-followup.json"
    plain.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(fss_f004_followup, "FOLLOWUP_PATH", plain)
    assert _hook(source, caplog) == expected
    assert "manifest" in caplog.text
    caplog.clear()
    broken = tmp_path / "broken" / "f004-followup.json"
    broken.parent.mkdir()
    payload = b"{"
    broken.write_bytes(payload)
    (broken.parent / "f004-followup.manifest.json").write_text(
        json.dumps(
            {
                "file": "f004-followup.json",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(fss_f004_followup, "FOLLOWUP_PATH", broken)
    assert _hook(source, caplog) == expected
    assert "F004 이행내역을 붙이지 않습니다" in caplog.text


def test_unmatched_bundle_and_dae_are_skipped(caplog):
    page = _page([("일반회계법인", [DAE])])
    kept = _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[_item()])])
    other_bundle = _firm("없는묶음", "없는 법인", dae=[_dae(firm="없는 법인")])
    with caplog.at_level(logging.INFO, logger="mkdocs.plugins.fss_f004"):
        built = inject_f004_followup(page, _payload([kept, other_bundle]), strict=False)
    assert "회계법인 현" in built
    assert "없는 법인" not in built
    assert "비매칭 1," in caplog.text or "비매칭 1 " in caplog.text
    caplog.clear()
    both = _firm(
        "일반회계법인",
        "회계법인 현",
        dae=[
            _dae(items=[_item()]),
            _dae(standard="6. 모니터링", display="기재 없음"),
        ],
    )
    with caplog.at_level(logging.INFO, logger="mkdocs.plugins.fss_f004"):
        built = inject_f004_followup(page, _payload([both]), strict=False)
    assert built.count('class="fss-f004-firm"') == 1
    assert "비매칭 1" in caplog.text


def test_inject_is_idempotent():
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[_item()])])
    page = _page([("일반회계법인", [DAE])])
    data = _payload([firm])
    once = inject_f004_followup(page, data)
    assert inject_f004_followup(once, data) == once


def test_disclaimer_replaces_empty_memo_and_level_label(built_page):
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[_item()], display=None)])
    rendered = render_dae_block([firm], DAE, _labels())
    assert rendered.count("fss-f004-disclaimer") == 1
    assert _DISCLAIMER in rendered
    assert "fss-f004-level" not in rendered
    assert "fss-f004-memo" not in rendered
    _source, built = built_page
    soup = BeautifulSoup(built, "html.parser")
    assert soup.select(".fss-f004-level") == []
    assert soup.select(".fss-f004-memo") == []
    assert len(soup.select(".fss-f004-disclaimer")) == len(
        soup.select(".fss-f004-block, .fss-f004-individual-group")
    )
    assert all(node.get_text(strip=True) == _DISCLAIMER for node in soup.select(".fss-f004-disclaimer"))


def test_empty_slot_can_link_the_latest_disclosure():
    firm = _firm("일반회계법인", "회계법인 현", dae=[_dae(display="기재 없음")])
    firm["latest_2026_disclosure"] = {"rcept_no": "20260630000001", "dart_url": DART}
    rendered = render_dae_block([firm], DAE, _labels())
    assert "fss-f004-none" in rendered
    assert f'href="{DART}"' in rendered
    assert "20260630000001" in rendered
    firm["latest_2026_disclosure"] = {"rcept_no": "1", "dart_url": "https://example.invalid/x"}
    hidden = render_dae_block([firm], DAE, _labels())
    assert "example.invalid" not in hidden
    assert "fss-f004-latest" not in hidden


def test_individual_group_has_one_disclaimer_and_strips():
    def person(name: str, rcept: str) -> dict:
        item = _item(
            dae_standard=None,
            match_level="individual_audit",
            match_level_label="개별 감사보고서",
            rcept_no=rcept,
            dart_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept}",
        )
        return _firm("일반회계법인", name, individual=[item])

    firms = [
        person("회계법인 현", "20260630000001"),
        person("다른 법인", "20260630000002"),
    ]
    page = "앞" + _page([("일반회계법인", [DAE])]) + "뒤"
    built = inject_f004_followup(page, _payload(firms))
    assert built.count("fss-f004-disclaimer") == 1
    assert built.count('class="fss-f004-individual"') == 2
    assert 'class="fss-f004-individual-group"' in built
    assert strip_f004_followup(built) == page


def test_summary_counts_slots_without_site_findings(caplog):
    source = PAGE.read_text(encoding="utf-8")
    with caplog.at_level(logging.INFO, logger="mkdocs.plugins.fss_f004"):
        on_page_markdown(source, _Page("fss-review/index.md"), None, None)
    assert "사이트 대분류 없음 2" in caplog.text
    assert "사이트 지적 0칸 3칸/5건" in caplog.text
    assert "지적사항 없음 2칸" in caplog.text


def _finding_row(**kwargs) -> dict:
    row = {
        "row_id": "20260630000001:0:0",
        "rcept_no": "20260630000001",
        "rcept_dt": "2026-06-30",
        "correction_type": "최초공시",
        "dart_url": DART,
        "category_raw": "업무의 수행",
        "recommend_date_raw": "-",
        "recommend_date_iso": None,
        "recommendation": "지적사항 없음",
        "action_raw": "해당사항 없음",
    }
    row.update(kwargs)
    return row


def test_no_finding_slot_shows_f004_mark():
    dae = _dae(display="지적사항 없음")
    dae["no_finding_rows"] = [_finding_row()]
    firm = _firm("일반회계법인", "회계법인 현", dae=[dae])
    soup = BeautifulSoup(render_dae_block([firm], DAE, _labels()), "html.parser")
    mark = soup.select_one(".fss-f004-nofinding")
    assert mark.get_text(strip=True).startswith("F004: 지적사항 없음")
    assert [link.get("href") for link in mark.select("a")] == [DART]
    assert soup.select(".fss-f004-none") == []
    assert soup.select(".fss-f004-item") == []
    assert soup.select(".fss-f004-latest") == []
    assert soup.select_one(".fss-f004-count").get_text(strip=True) == "0건"
    assert mark.get("id") is None
    assert mark.select("[id]") == []


def test_no_finding_mark_with_items_comes_first():
    dae = _dae(items=[_item()], display="지적사항 없음")
    dae["no_finding_rows"] = [_finding_row()]
    rendered = render_dae_block([_firm("일반회계법인", "회계법인 현", dae=[dae])], DAE, _labels())
    assert rendered.index("fss-f004-nofinding") < rendered.index("fss-f004-item")
    assert rendered.count('class="fss-f004-item"') == 1


def test_missing_recommend_date_shows_gisae_eopseum():
    raws = ["-", "", None, "2026.03.20"]
    items = []
    for index, raw in enumerate(raws, start=1):
        number = f"2026063000000{index}"
        items.append(
            _item(
                recommend_date_raw=raw,
                rcept_no=number,
                dart_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={number}",
            )
        )
    rendered = render_dae_block(
        [_firm("일반회계법인", "회계법인 현", dae=[_dae(items=items)])],
        DAE,
        _labels(),
    )
    metas = [node.get_text() for node in BeautifulSoup(rendered, "html.parser").select(".fss-f004-meta")]
    assert len(metas) == 4
    for text in metas[:3]:
        assert "권고일 기재 없음" in text
        assert "권고일 -" not in text
    assert "권고일 2026.03.20" in metas[3]
    assert [item["recommend_date_raw"] for item in items] == raws


def test_load_followup_rejects_bad_no_finding_data(tmp_path):
    missing_rows = _dae(display="지적사항 없음")
    bad_url = _dae(display="지적사항 없음")
    bad_url["no_finding_rows"] = [_finding_row(dart_url="https://example.invalid/x")]
    unknown = _dae(display="없음")
    mismatch = _dae(display="기재 없음")
    mismatch["f004_item_count"] = 2
    cases = (missing_rows, bad_url, unknown, mismatch)
    for dae in cases:
        payload = _payload([_firm("일반회계법인", "회계법인 현", dae=[dae])])
        with pytest.raises(ValueError):
            load_followup(_write(tmp_path, payload))


def test_no_finding_source_banned_word_stays_in_data_only(tmp_path):
    word = _banned()
    dae = _dae(display="지적사항 없음")
    dae["no_finding_rows"] = [_finding_row(recommendation=word)]
    dae["f004_item_count"] = 0
    payload = _payload([_firm("일반회계법인", "회계법인 현", dae=[dae])])
    load_followup(_write(tmp_path, payload))
    rendered = render_dae_block(payload["firms"], DAE, payload["labels"])
    assert word not in rendered


def test_individual_disclaimer_matches_group_count():
    def person(name: str, rcept: str) -> dict:
        item = _item(
            dae_standard=None,
            match_level="individual_audit",
            match_level_label="개별 감사보고서",
            rcept_no=rcept,
            dart_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept}",
        )
        return _firm("일반회계법인", name, individual=[item])

    firms = [
        person("회계법인 현", "20260630000021"),
        person("다른 법인", "20260630000022"),
    ]
    built = inject_f004_followup(_page([("일반회계법인", [DAE])]), _payload(firms))
    soup = BeautifulSoup(built, "html.parser")
    blocks = soup.select(".fss-f004-block")
    groups = soup.select(".fss-f004-individual-group")
    assert len(groups) == 1
    assert len(soup.select(".fss-f004-individual")) == 2
    assert len(soup.select(".fss-f004-disclaimer")) == len(blocks) + len(groups)
    for node in soup.select(".fss-f004-individual"):
        assert node.select(".fss-f004-disclaimer") == []
    counts = check_mod._html_counts(built)
    assert counts["disclaimer"] == counts["block"] + counts["individual_group"]


def test_dart_url_trailing_newline_is_rejected(tmp_path):
    broken = DART + "\n"
    item = _item(dart_url=broken)
    history = _item(
        rcept_no="20260630000031",
        dart_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260630000031",
        history=[{
            "rcept_no": "20260630000032",
            "rcept_dt": "2026-06-30",
            "correction_type": "기재정정",
            "dart_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260630000032" + "\n",
            "action_text": "이전",
            "action_changed": False,
        }],
    )
    finding = _dae(display="지적사항 없음")
    finding["no_finding_rows"] = [_finding_row(dart_url=broken)]
    finding["f004_item_count"] = 0
    disclosed = _firm("일반회계법인", "회계법인 현", dae=[_dae(display="기재 없음")])
    disclosed["latest_2026_disclosure"] = {"rcept_no": "20260630000001", "dart_url": broken}
    cases = (
        _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[item])]),
        _firm("일반회계법인", "회계법인 현", dae=[_dae(items=[history])]),
        _firm("일반회계법인", "회계법인 현", dae=[finding]),
        disclosed,
    )
    for firm in cases:
        with pytest.raises(ValueError):
            load_followup(_write(tmp_path, _payload([firm])))


def test_blank_action_renders_as_gisae_eopseum():
    def numbered(index: int, **kwargs) -> dict:
        number = f"2026063000004{index}"
        return _item(
            rcept_no=number,
            dart_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={number}",
            **kwargs,
        )

    items = [
        numbered(1, action=""),
        numbered(2, action="-"),
        numbered(3, action=None),
        numbered(4, action="완료", history=[{
            "rcept_no": "20260630000045",
            "rcept_dt": "2026-06-30",
            "correction_type": "기재정정",
            "dart_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260630000045",
            "action_text": "-",
            "action_changed": True,
        }]),
    ]
    soup = BeautifulSoup(
        render_dae_block([_firm("일반회계법인", "회계법인 현", dae=[_dae(items=items)])], DAE, _labels()),
        "html.parser",
    )
    acts = [node.get_text() for node in soup.select(".fss-f004-act")]
    assert [text for text in acts[:3]] == ["이행 내용기재 없음"] * 3 or all("기재 없음" in text for text in acts[:3])
    assert all("기재 없음" in text for text in acts[:3])
    assert "완료" in acts[3]
    assert "기재 없음" in soup.select_one(".fss-f004-hist").get_text()


def test_malformed_display_falls_back_to_the_page(tmp_path, monkeypatch, caplog):
    dae = _dae(display="기재 없음")
    dae["f004_display"] = []
    payload = _payload([_firm("일반회계법인", "회계법인 현", dae=[dae])])
    path = tmp_path / "f004-followup.json"
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    path.write_bytes(raw)
    (tmp_path / "f004-followup.manifest.json").write_text(
        json.dumps({
            "file": "f004-followup.json",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(fss_f004_followup, "FOLLOWUP_PATH", path)
    source = PAGE.read_text(encoding="utf-8")
    built = _hook(source, caplog)
    assert built == materialize_review_markdown(source)
    assert "ValueError:" in caplog.text
