# -*- coding: utf-8 -*-
"""F004 hook 출력의 불변식을 표준출력으로 확인하고, 통과할 때만 JSON 보고서를 쓴다."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

from fss_f004_followup import (
    FOLLOWUP_PATH,
    load_followup,
    strip_f004_followup,
)
from fss_review_cards import (
    PAGE,
    YEAR_2025_PATH,
    audit_review_html,
    materialize_review_markdown,
)
from mkdocs_fss_review_year import on_page_markdown

# scripts/tests/test_fss_review_cards.py YEAR_SHA (main 94f4882).
# 2025 블록은 F004가 붙으므로 여기서 비교하지 않는다.
PRIOR_YEAR_SHA = {
    "2024": "dd252ed36a6f3debb59d9c5c831dfab643bb3dc51a4918b5f4649b0087f87763",
    "2023": "a04efa16f933d3aac44bb98434af3bc21160d028790e140c50d77a3f38416baf",
    "2022": "5cf332453ec91121dbbc37aec0c15f540842b5cf845cfde7df98708c839601dc",
    "2021": "9b278810dd0ff9a0e19300d5d8c1f67cb5ef34db2a07b8bcc437eed11ea2b821",
    "2020": "24375fe9c10e2a0fa0513dea5831fc4141471cca9be2e0c1ea9414c01465ce92",
    "2019": "fb13f1d4d54aaf8126f97bf802feb37ef40b2fee7852694ca22c3215e607d098",
}
_BANNED = "미" + "이행"
_ANCHOR = re.compile(r'<([A-Za-z0-9]+)([^>]*\bid="f004-2025-[0-9a-f]+"[^>]*)>')


class _File:
    def __init__(self, src: str) -> None:
        self.src_uri = src


class _Page:
    def __init__(self, src: str) -> None:
        self.file = _File(src)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _year_inventory(data: dict) -> tuple[int, int]:
    names: list[str] = []
    findings = 0
    for bundle in data["bundles"]:
        for section in bundle["sections"]:
            for group in section["groups"]:
                for block in group["blocks"]:
                    if block.get("kind") != "firms":
                        continue
                    for firm in block["firms"]:
                        names.append(firm["name"])
                        findings += len(firm["findings"])
    return len(set(names)), findings


def _rendered_source_banned(data: dict) -> int:
    """화면에 원문 span으로 나가는 필드만 센다."""
    count = 0

    def take(item: dict) -> None:
        nonlocal count
        count += str(item.get("recommendation") or "").count(_BANNED)
        count += str(item.get("action") or "").count(_BANNED)
        for note in item.get("doc_notes") or []:
            count += str(note).count(_BANNED)
        for row in item.get("history") or []:
            count += str(row.get("action_text") or "").count(_BANNED)

    for firm in data["firms"]:
        for dae in firm.get("dae") or []:
            for item in dae.get("items") or []:
                take(item)
        for item in firm.get("individual_audit") or []:
            take(item)
    return count


def _non_source_banned(obj: object, *, skip: bool = False) -> int:
    if skip:
        return 0
    if isinstance(obj, str):
        return obj.count(_BANNED)
    if isinstance(obj, dict):
        source = {
            "recommendation",
            "action",
            "action_raw",
            "doc_notes",
            "action_text",
            "action_text_raw",
        }
        return sum(_non_source_banned(value, skip=key in source) for key, value in obj.items())
    if isinstance(obj, list):
        return sum(_non_source_banned(value) for value in obj)
    return 0


def _json_counts(data: dict) -> dict[str, int]:
    dae_rows = [dae for firm in data["firms"] for dae in firm.get("dae") or []]
    items = [item for dae in dae_rows for item in dae.get("items") or []]
    display: dict[str, int] = {}
    for dae in dae_rows:
        label = dae.get("f004_display")
        if isinstance(label, str):
            display[label] = display.get(label, 0) + 1
    return {
        "firm": len(dae_rows),
        "item": len(items),
        "hist": sum(len(item.get("history") or []) for item in items),
        "fallback": sum(1 for item in items if item.get("year_basis") == "disclosure_year_fallback"),
        "mismatch": sum(1 for item in items if item.get("date_mismatch") is True),
        "none_empty": display.get("기재 없음", 0),
        "none_na": display.get("해당 없음", 0),
        "individual": sum(1 for firm in data["firms"] if firm.get("individual_audit")),
        "banned_inside": _rendered_source_banned(data),
        "banned_outside": _non_source_banned(data),
    }


def _html_counts(built: str) -> dict[str, object]:
    soup = BeautifulSoup(built, "html.parser")
    none_empty = 0
    none_na = 0
    for node in soup.select(".fss-f004-none"):
        text = node.get_text(strip=True)
        if text == "기재 없음":
            none_empty += 1
        elif text == "해당 없음":
            none_na += 1
    prior_match = True
    seen: set[str] = set()
    for div in soup.select("div.fss-year"):
        year = div.get("data-year")
        if year not in PRIOR_YEAR_SHA:
            continue
        seen.add(year)
        digest = hashlib.sha256(str(div).encode("utf-8")).hexdigest()
        if digest != PRIOR_YEAR_SHA[year]:
            prior_match = False
    if seen != set(PRIOR_YEAR_SHA):
        prior_match = False
    anchors = 0
    anchors_only_on_firm = True
    for match in _ANCHOR.finditer(built):
        anchors += 1
        if "fss-f004-firm" not in match.group(0):
            anchors_only_on_firm = False
    outside, inside = _banned_in_f004(built)
    return {
        "firm": len(soup.select(".fss-f004-firm")),
        "item": len(soup.select(".fss-f004-item")),
        "hist": len(soup.select(".fss-f004-hist")),
        "fallback": len(soup.select(".fss-f004-fallback")),
        "mismatch": len(soup.select(".fss-f004-mismatch")),
        "none_empty": none_empty,
        "none_na": none_na,
        "individual": len(soup.select(".fss-f004-individual")),
        "anchors": anchors,
        "anchors_only_on_firm": anchors_only_on_firm,
        "prior_year_sha_match": prior_match,
        "banned_outside": outside,
        "banned_inside": inside,
    }


def _banned_in_f004(built: str) -> tuple[int, int]:
    soup = BeautifulSoup(built, "html.parser")
    inside = 0
    outside = 0
    for region in soup.select("div.fss-f004-block, div.fss-f004-individual"):
        for span in region.select("span.fss-f004-src"):
            inside += span.get_text().count(_BANNED)
            span.decompose()
        outside += region.get_text("\n").count(_BANNED)
    return outside, inside


def build_report() -> dict:
    followup = load_followup(FOLLOWUP_PATH)
    year = json.loads(YEAR_2025_PATH.read_text(encoding="utf-8"))
    firms, findings = _year_inventory(year)
    expected = _json_counts(followup)
    source = PAGE.read_text(encoding="utf-8")
    built = on_page_markdown(source, _Page("fss-review/index.md"), None, None)
    html_counts = _html_counts(built)
    materialized = materialize_review_markdown(source)
    strip_ok = strip_f004_followup(built) == materialized
    audit_errors = audit_review_html(built)
    errors: list[str] = []
    pairs = (
        ("fss-f004-firm", "firm"),
        ("fss-f004-item", "item"),
        ("fss-f004-hist", "hist"),
        ("fss-f004-fallback", "fallback"),
        ("fss-f004-mismatch", "mismatch"),
        ("fss-f004-none 기재 없음", "none_empty"),
        ("fss-f004-none 해당 없음", "none_na"),
        ("fss-f004-individual", "individual"),
        ("금지어 원문 안", "banned_inside"),
        ("금지어 원문 밖", "banned_outside"),
    )
    for label, key in pairs:
        if html_counts[key] != expected[key]:
            errors.append(f"{label} 화면 {html_counts[key]} / 데이터 {expected[key]}")
    if html_counts["anchors"] != expected["firm"]:
        errors.append(f"앵커 화면 {html_counts['anchors']} / 데이터 {expected['firm']}")
    if not html_counts["anchors_only_on_firm"]:
        errors.append("앵커가 법인 요소 밖에 있습니다.")
    if not html_counts["prior_year_sha_match"]:
        errors.append("2019-2024 연도 블록 sha256이 고정값과 다릅니다.")
    if not strip_ok:
        errors.append("strip 결과가 materialize 출력과 다릅니다.")
    if audit_errors:
        errors.append(f"audit_review_html 오류 {len(audit_errors)}건")
    return {
        "year_2025_sha256": _sha256(YEAR_2025_PATH),
        "followup_sha256": _sha256(FOLLOWUP_PATH),
        "firms": firms,
        "findings": findings,
        "fss_f004_firm": html_counts["firm"],
        "fss_f004_item": html_counts["item"],
        "fss_f004_hist": html_counts["hist"],
        "fss_f004_fallback": html_counts["fallback"],
        "fss_f004_mismatch": html_counts["mismatch"],
        "fss_f004_none_empty": html_counts["none_empty"],
        "fss_f004_none_na": html_counts["none_na"],
        "fss_f004_individual": html_counts["individual"],
        "anchors": html_counts["anchors"],
        "anchors_only_on_firm": html_counts["anchors_only_on_firm"],
        "prior_year_sha_match": html_counts["prior_year_sha_match"],
        "strip_equals_materialize": strip_ok,
        "audit_error_count": len(audit_errors),
        "banned_outside": html_counts["banned_outside"],
        "banned_inside": html_counts["banned_inside"],
        "errors": errors,
    }


def render_text(report: dict) -> str:
    lines = [
        f"year-2025.json sha256: {report['year_2025_sha256']}",
        f"f004-followup.json sha256: {report['followup_sha256']}",
        f"firms: {report['firms']}",
        f"findings: {report['findings']}",
        f"fss-f004-firm: {report['fss_f004_firm']}",
        f"fss-f004-item: {report['fss_f004_item']}",
        f"fss-f004-hist: {report['fss_f004_hist']}",
        f"fss-f004-fallback: {report['fss_f004_fallback']}",
        f"fss-f004-mismatch: {report['fss_f004_mismatch']}",
        f"fss-f004-none 기재 없음: {report['fss_f004_none_empty']}",
        f"fss-f004-none 해당 없음: {report['fss_f004_none_na']}",
        f"fss-f004-individual: {report['fss_f004_individual']}",
        f"anchors: {report['anchors']}",
        f"anchors_only_on_firm: {str(report['anchors_only_on_firm']).lower()}",
        f"prior_year_sha_match: {str(report['prior_year_sha_match']).lower()}",
        f"strip_equals_materialize: {str(report['strip_equals_materialize']).lower()}",
        f"audit_error_count: {report['audit_error_count']}",
        f"banned_outside: {report['banned_outside']}",
        f"banned_inside: {report['banned_inside']}",
        f"errors: {len(report['errors'])}",
    ]
    for error in report["errors"]:
        lines.append(f"error: {error}")
    return "\n".join(lines)


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False)
    tmp_name = handle.name
    try:
        with handle:
            handle.write(payload)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F004 hook 출력 불변식을 확인합니다.")
    parser.add_argument("--report", type=Path, help="통과할 때만 같은 결과를 JSON으로 씁니다.")
    args = parser.parse_args(argv)
    try:
        report = build_report()
    except Exception as exc:
        print(f"오류: {exc}")
        return 1
    text = render_text(report)
    print(text)
    if report["errors"]:
        return 1
    if args.report is not None:
        try:
            payload = dict(report)
            payload["text"] = text
            _atomic_write(args.report, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        except Exception as exc:
            print(f"오류: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
