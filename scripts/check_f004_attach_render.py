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
import sys
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

from fss_f004_attach import ATTACH_PATH, inject_f004_attach, load_attach
from fss_review_cards import YEAR_2025_PATH, load_year_2025, render_year_2025_html

ROOT = Path(__file__).resolve().parent.parent
SITE_HTML = ROOT / "site" / "fss-review" / "index.html"
ATTACH_SHA = "e575e0c126487c42e635944cd6a6c05ed7ff4dcf13eeeb6dd70fbde75b0a49dc"
ATTACH_BYTES = 240048
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
    "e8f7c3d54a44247ef1e7827970f90c55a5c6fb3f4a31257effa54ca0608470ab": (
        305535,
        "662c6a74f7c942c28e2690fa00875d738bc5c4fbfc6b33b7f47e4a33a780cedd",
    ),
    "1c6df2500ba918054bd4b22b3a983af9ef3bdecdedc54908d4a54a04e1ea72e4": (
        306273,
        "831b364b707cad8e94273bf50c552b9523f3ec03ce9c07475e233820fa24d217",
    ),
}
EXPECTED = {
    "attach": 128,
    "reason": 136,
    "no_date": 7,
    "no_action": 2,
    "note": 28,
    "mismatch": 0,
    "no_finding": 0,
    "dongsung": 0,
}


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


def _dongsung(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    count = 0
    for panel in soup.select("div.fss-original"):
        if panel.get("data-names") != "동성회계법인":
            continue
        count += len(panel.select(".fss-f004-attach, .fss-f004-reason"))
    return count


def build_report(html: str) -> dict:
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
    load_attach(ATTACH_PATH)
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
    counts = {
        "attach": html.count('class="fss-f004-attach"'),
        "reason": html.count('class="fss-f004-reason"'),
        "no_date": html.count("권고일 기재 없음"),
        "no_action": html.count("이행사항 기재 없음"),
        "note": html.count("한 행으로 공시"),
        "mismatch": html.count("권고일 표기 불일치"),
        "no_finding": html.count("지적사항 없음"),
        "dongsung": _dongsung(html),
    }
    for key, expected in EXPECTED.items():
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
        f"권고일 기재 없음: {counts['no_date']}",
        f"이행사항 기재 없음: {counts['no_action']}",
        f"한 행으로 공시: {counts['note']}",
        f"권고일 표기 불일치: {counts['mismatch']}",
        f"지적사항 없음: {counts['no_finding']}",
        f"동성회계법인 F004: {counts['dongsung']}",
        f"prior_year_sha_match: {str(report['prior_year_sha_match']).lower()}",
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
    args = parser.parse_args(argv)
    if not args.html.is_file():
        print(f"오류: {args.html} 이 없습니다. mkdocs build --strict 를 먼저 실행하세요.")
        return 1
    try:
        html = args.html.read_text(encoding="utf-8")
        report = build_report(html)
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
