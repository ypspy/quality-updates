# -*- coding: utf-8 -*-
"""F004 부착 결과를 빌드된 감리 페이지에서 센다.

``mkdocs build --strict`` 뒤 ``site/fss-review/index.html``의 5절 값,
2019~2024 블록 sha, 첨부 JSON·manifest sha가 하나라도 다르면 0이 아닌 코드로 끝난다.
"""

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

from fss_f004_attach import ATTACH_PATH, inject_f004_attach, load_attach
from fss_review_cards import YEAR_2025_PATH, load_year_2025, render_year_2025_html

ROOT = Path(__file__).resolve().parent.parent
SITE_HTML = ROOT / "site" / "fss-review" / "index.html"
ATTACH_SHA = "241b0edcd6eae831ef38a8d5a742be3f1bb09672cc1560fd93a54ddccc80e682"
ATTACH_BYTES = 246423
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
RENDERED = {
    "1c6df2500ba918054bd4b22b3a983af9ef3bdecdedc54908d4a54a04e1ea72e4": (
        317065,
        "c250624d21907095667438d0326c1e7765464575da6655d3a119db3dc7e774cc",
    ),
}
_INTERNAL_IDS = (
    "f004_row_id",
    "text_sha256",
    "finding_id",
    "match_level",
    "year_basis",
    "date_mismatch",
    "f004_no_finding",
    "pending",
    "qu_review31",
    "qu_dongsung",
)
SEARCH_INDEX = ROOT / "site" / "search" / "search_index.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_path(path: Path) -> Path:
    return path.with_name("f004-item-attach.manifest.json")


def _prior_year_hashes(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, str] = {}
    for div in soup.select("div.fss-year"):
        year = str(div.get("data-year") or "")
        if year in PRIOR_YEAR_SHA:
            found[year] = hashlib.sha256(str(div).encode("utf-8")).hexdigest()
    return found


def _internal_hits(text: str) -> int:
    return sum(text.count(token) for token in _INTERNAL_IDS)


def _phrase_counts(html: str) -> dict[str, int]:
    """F004로 붙인 요소의 텍스트만 센다."""
    soup = BeautifulSoup(html, "html.parser")
    text = "\n".join(
        node.get_text() for node in soup.select(".fss-f004-attach, .fss-f004-reason")
    )
    return {
        "no_date": text.count("권고일 기재 없음"),
        "no_action": text.count("이행사항 기재 없음"),
        "note": text.count("한 행으로 공시"),
        "mismatch": text.count("권고일 표기 불일치"),
        "no_finding": text.count("지적사항 없음"),
    }


def _search_index_report(path: Path) -> dict:
    """검색 색인의 내부 id와 화면 밖 문구를 센다."""
    if not path.is_file():
        return {"ids": 0, "mismatch": 0, "errors": ["search_index.json이 없습니다."]}
    search_text = path.read_text(encoding="utf-8")
    ids = _internal_hits(search_text)
    mismatch = search_text.count("권고일 표기 불일치")
    errors: list[str] = []
    if ids:
        errors.append(f"내부 id가 검색 색인에 {ids}건 있습니다.")
    if mismatch:
        errors.append(f"검색 색인의 권고일 표기 불일치 {mismatch}건")
    return {"ids": ids, "mismatch": mismatch, "errors": errors}


def _dongsung(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    count = 0
    for panel in soup.select("div.fss-original"):
        if panel.get("data-names") != "동성회계법인":
            continue
        count += len(panel.select(".fss-f004-attach, .fss-f004-reason"))
    return count


def _short_reason_lines(html: str) -> int:
    """「위와 같음」 짧은 사유 줄(v2 R1 형식) 수. 지금 형식에서는 0이어야 한다."""
    return sum(
        1
        for line in re.findall(r'<p class="fss-f004-reason[^"]*">.*?</p>', html, re.S)
        if "fss-f004-same" in line or "위와 같음" in line
    )


def _reason_panels(html: str, firms: set[str]) -> tuple[int, int, int, int]:
    """2025 패널 수, 그중 사유 법인 패널 수, 사유 줄이 정확히 하나가 아닌 사유 법인 패널 수,
    패널마다 사유 줄이 같지 않은 사유 법인 수."""
    soup = BeautifulSoup(html, "html.parser")
    year = soup.select_one('div.fss-year[data-year="2025"]')
    if year is None:
        return 0, 0, 0, 0
    total = panels = bad = 0
    lines: dict[str, set[str]] = {}
    for panel in year.select("div.fss-original"):
        total += 1
        firm = panel.get("data-names")
        if firm not in firms:
            continue
        panels += 1
        found = panel.select("p.fss-f004-reason")
        if len(found) != 1:
            bad += 1
            continue
        lines.setdefault(firm, set()).add(str(found[0]))
    differ = sum(1 for seen in lines.values() if len(seen) > 1)
    return total, panels, bad, differ


def _reason_content(html: str, reasons: list[dict]) -> tuple[int, int]:
    """사유 줄이 있는 사유 법인 수와, 사유 줄의 글·링크가 데이터(firm_reasons)와 다른 법인 수."""
    soup = BeautifulSoup(html, "html.parser")
    year = soup.select_one('div.fss-year[data-year="2025"]')
    if year is None:
        return 0, 0
    found: dict[str, list] = {}
    for panel in year.select("div.fss-original"):
        for line in panel.select("p.fss-f004-reason"):
            found.setdefault(panel.get("data-names"), []).append(line)
    present = wrong = 0
    for reason in reasons:
        lines = found.get(reason["firm"])
        if not lines:
            continue
        present += 1
        disclosure = reason.get("disclosure")
        text = reason["text"]
        if disclosure:
            text = f"{text} · {disclosure['rcept_no']}"
        for line in lines:
            link = line.find("a")
            if line.get_text() != text or (
                link.get("href") != disclosure["dart_url"] if disclosure else link is not None
            ):
                wrong += 1
                break
    return present, wrong


def build_report(html: str, search_index: Path = SEARCH_INDEX) -> dict:
    errors: list[str] = []
    year_sha = _sha256(YEAR_2025_PATH)
    attach_raw = ATTACH_PATH.read_bytes()
    attach_sha = hashlib.sha256(attach_raw).hexdigest()
    manifest_file = _manifest_path(ATTACH_PATH)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if attach_sha != ATTACH_SHA or len(attach_raw) != ATTACH_BYTES:
        errors.append(f"f004-item-attach.json sha {attach_sha} bytes {len(attach_raw)}")
    if manifest.get("sha256") != ATTACH_SHA or manifest.get("bytes") != ATTACH_BYTES:
        errors.append("manifest sha 또는 bytes가 첨부 파일과 다릅니다.")
    if manifest.get("file") != "f004-item-attach.json":
        errors.append("manifest file 이름이 다릅니다.")
    loaded = load_attach(ATTACH_PATH)
    count_source = loaded["counts"]
    expected_counts = {
        "attach": count_source["attach_blocks"],
        "same": 0,
        "no_date": count_source["no_date_blocks"],
        "no_action": count_source["no_action_blocks"],
        "note": count_source["notes"],
        "mismatch": 0,
        "no_finding": 0,
        "dongsung": count_source["dongsung_blocks"],
    }
    reason_firms = {reason["firm"] for reason in loaded["firm_reasons"]}
    # 기대 패널 수는 검사할 페이지가 아니라 year-2025.json 렌더(부착 전)에서 센다.
    # 고정 상수(136)를 두지 않아 데이터가 바뀌어도 그대로 맞고, 페이지에서 패널이 빠지면 잡힌다.
    source_total, source_reason, _, _ = _reason_panels(
        render_year_2025_html(load_year_2025()), reason_firms
    )
    page_total, page_reason, reason_panel_bad, reason_firm_differ = _reason_panels(
        html, reason_firms
    )
    # 사유 법인은 모든 패널에 같은 사유 줄 전체(사용자 결정 2026-11-15 9:14 AM CT).
    expected_counts["reason"] = source_reason
    if page_total != source_total or page_reason != source_reason:
        errors.append(
            f"2025 패널 화면 {page_total}(사유 법인 {page_reason})"
            f" / 기대 {source_total}(사유 법인 {source_reason})"
        )
    # 사유 줄이 있는 법인 수는 counts.firm_reason_panels(= firm_reasons 수, load_attach가 확인)와 같아야 한다.
    present, wrong = _reason_content(html, loaded["firm_reasons"])
    if present != count_source["firm_reason_panels"]:
        errors.append(f"사유 줄이 있는 사유 법인 화면 {present} / 기대 {count_source['firm_reason_panels']}")
    if wrong:
        errors.append(f"사유 줄 글·링크가 데이터와 다른 사유 법인 {wrong}곳")
    if year_sha not in RENDERED:
        errors.append(f"year-2025.json sha를 알 수 없습니다: {year_sha}")
        rendered_size = 0
        rendered_sha = ""
    else:
        rendered = inject_f004_attach(render_year_2025_html(load_year_2025())).encode("utf-8")
        rendered_size = len(rendered)
        rendered_sha = hashlib.sha256(rendered).hexdigest()
        expect_size, expect_sha = RENDERED[year_sha]
        if rendered_size != expect_size or rendered_sha != expect_sha:
            errors.append(
                f"2025 렌더 부착 {rendered_size} B {rendered_sha} / 기대 {expect_size} B {expect_sha}"
            )
    phrases = _phrase_counts(html)
    counts = {
        "attach": html.count('class="fss-f004-attach"'),
        "reason": html.count('class="fss-f004-reason"'),
        "same": _short_reason_lines(html),
        "no_date": phrases["no_date"],
        "no_action": phrases["no_action"],
        "note": phrases["note"],
        "mismatch": phrases["mismatch"],
        "no_finding": phrases["no_finding"],
        "dongsung": _dongsung(html),
    }
    if reason_panel_bad:
        errors.append(f"사유 줄이 하나가 아닌 사유 법인 패널 {reason_panel_bad}개")
    if reason_firm_differ:
        errors.append(f"패널마다 사유 줄이 다른 사유 법인 {reason_firm_differ}곳")
    page_ids = _internal_hits(html)
    if page_ids:
        errors.append(f"내부 id가 페이지에 {page_ids}건 있습니다.")
    search = _search_index_report(search_index)
    errors.extend(search["errors"])
    for key, expected in expected_counts.items():
        if counts[key] != expected:
            errors.append(f"{key} 화면 {counts[key]} / 기대 {expected}")
    prior = _prior_year_hashes(html)
    prior_match = prior == PRIOR_YEAR_SHA
    if not prior_match:
        missing = sorted(set(PRIOR_YEAR_SHA) - set(prior))
        changed = sorted(year for year, digest in prior.items() if digest != PRIOR_YEAR_SHA[year])
        errors.append(f"2019-2024 연도 블록 sha256이 고정값과 다릅니다: 없음 {missing} 다름 {changed}")
    return {
        "year_2025_sha256": year_sha,
        "attach_sha256": attach_sha,
        "attach_bytes": len(attach_raw),
        "manifest_sha256": manifest.get("sha256"),
        "rendered_bytes": rendered_size,
        "rendered_sha256": rendered_sha,
        "counts": counts,
        "prior_year_sha_match": prior_match,
        "internal_ids_in_page": page_ids,
        "internal_ids_in_search_index": search["ids"],
        "errors": errors,
    }


def render_text(report: dict) -> str:
    counts = report["counts"]
    lines = [
        f"year-2025.json sha256: {report['year_2025_sha256']}",
        f"f004-item-attach.json sha256: {report['attach_sha256']}",
        f"f004-item-attach.json bytes: {report['attach_bytes']}",
        f"manifest sha256: {report['manifest_sha256']}",
        f"rendered bytes: {report['rendered_bytes']}",
        f"rendered sha256: {report['rendered_sha256']}",
        f"fss-f004-attach: {counts['attach']}",
        f"fss-f004-reason: {counts['reason']}",
        f"위와 같음·fss-f004-same: {counts['same']}",
        f"권고일 기재 없음: {counts['no_date']}",
        f"이행사항 기재 없음: {counts['no_action']}",
        f"한 행으로 공시: {counts['note']}",
        f"권고일 표기 불일치: {counts['mismatch']}",
        f"지적사항 없음: {counts['no_finding']}",
        f"동성회계법인 F004: {counts['dongsung']}",
        f"prior_year_sha_match: {str(report['prior_year_sha_match']).lower()}",
        f"internal_ids_in_page: {report['internal_ids_in_page']}",
        f"internal_ids_in_search_index: {report['internal_ids_in_search_index']}",
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
    parser = argparse.ArgumentParser(description="F004 부착 렌더를 확인합니다.")
    parser.add_argument("--report", type=Path, help="통과할 때만 같은 결과를 JSON으로 씁니다.")
    parser.add_argument("--html", type=Path, default=SITE_HTML, help="빌드된 감리 페이지")
    parser.add_argument("--search-index", type=Path, help="빌드된 검색 색인")
    args = parser.parse_args(argv)
    if not args.html.is_file():
        print(f"오류: {args.html} 이 없습니다. mkdocs build --strict 를 먼저 실행하세요.")
        return 1
    search_index = args.search_index
    if search_index is None:
        search_index = args.html.parent.parent / "search" / "search_index.json"
    try:
        html = args.html.read_text(encoding="utf-8")
        report = build_report(html, search_index)
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
