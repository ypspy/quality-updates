# -*- coding: utf-8 -*-
"""F004 부착 결과를 빌드된 감리 페이지에서 센다.

``mkdocs build --strict`` 뒤 ``site/fss-review/index.html``의 연도별 값,
부착 없는 연도 블록 sha, 첨부 JSON·manifest sha가 하나라도 다르면 0이 아닌 코드로 끝난다.
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

from fss_f004_attach import ATTACH_PATHS, _year_span, inject_f004_attach, load_attach
from fss_review_cards import (
    YEAR_FILES,
    load_year,
    load_year_2025,
    render_year_html,
    render_year_2025_html,
)

ROOT = Path(__file__).resolve().parent.parent
SITE_HTML = ROOT / "site" / "fss-review" / "index.html"
# 키 집합은 fss_f004_attach.ATTACH_PATHS와 같아야 한다.
# 2025 화면 수치는 이 표의 잠금과 부착 JSON counts로만 만든다.
ATTACH_YEARS = {
    "2025": {
        "sha": "a27862374326741a2c39a1e59eb371d67ffe614160b23bcd0e9d2db43870d899",
        "bytes": 247081,
        "rendered": {
            "b885f6ceb580551acf411cfa49532b57cb3288865533910f25bdc999fef3725a": (
                317076,
                "5f03782787e8eb8e7b9e646b9c04175953534c2a9337fcb0aead9397d0b8cf46",
            ),
        },
        "site_div_sha": "6dedeef72cf4970cd6455fc999dc89eb73e181bcb13f23e7ca502d2cf53af661",
    },
    "2024": {
        "sha": "74b7fa25d5f8aa7e67f0197a0c9d268d1ff3c0921f0f5a4f77616cd876e7ea05",
        "bytes": 427581,
        "rendered": {
            "908d225b9f0ef0c09aee962fd4b0b645d817d583c9da91d39e83b53fdc5019b7": (
                421977,
                "91691b822ecd2d3ae241638b820f3b1e101309506fc22bb0090131488ba53fa5",
            ),
        },
        "site_div_sha": "8679d1c336d753170c8dc0a7f8964c676790f6d0eed6b895a4a8fec3e12be060",
    },
    "2023": {
        "sha": "e0c8411786330160aa24f4fcb27911c32b0262884b22f142622fdcf79fe29659",
        "bytes": 421019,
        "rendered": {
            "cff5f578f58a112631417f0306fc74994255aa53865f2bda941c48aeaffd95b6": (
                359271,
                "3858c983781a45eae5832013b2d45b3798a7bba207e159bd0d2a97fd6a519c64",
            ),
        },
        "site_div_sha": "46b44b8a91eab39599f8d1f086dc68fdb53538ddb38c5e15f4cd04c042d05ebe",
    },
    "2022": {
        "sha": "6329b4cc77e42530a3da252a63919119b2bccfbc80ed32616cac5494f054a8e6",
        "bytes": 425948,
        "rendered": {
            "1ff091e283eb705480a6ed9b8f53a16ebd5107173a400f786628000b2c38bfb4": (
                396411,
                "1c80f054774ea8e3d205e53bb655b27b88b1201bdc6020e65a646b0128059bae",
            ),
        },
        "site_div_sha": "8aa8846e43ea9f8bd29a3d361662619ef55bddbc6e1975b096cbfad647f0fa6f",
    },
    "2021": {
        "sha": "7b06fcd190a5b4a84b593b46f34729513a00d39de95aaf306c4d1bbd2d6aed03",
        "bytes": 291764,
        "rendered": {
            "dd8805af68f14beb9d222da9019d10e5337f06aff48fc0bc66cf66f79b1a6410": (
                164196,
                "ae6c6f4eb2433ab8e5fd898f82aa693b9e44726641303ec0d59338a7892ec1d7",
            ),
        },
        "site_div_sha": "7928d4b8a973ec66f7ddbf2a6bfb29f3190a55f44eeb66c2f528f8868120b5e7",
    },
    "2020": {
        "sha": "ea6545c7d2fbbcdd57efa7397705749ae4ff2b2f899a61b98f9971cfc31afb1c",
        "bytes": 195561,
        "rendered": {
            "6e426ceea925c53b6d5f360b3f938c5160d13aa1fe59b078c163467f1ca710a8": (
                104112,
                "b2008599c4fcac92aeb0071760a3c3f8ee8e1332d4a8cb2bcb3f1244ff530f63",
            ),
        },
        "site_div_sha": "e4ad036362c52e47ec47ac3e2ca0f9a9ae05d7ffced38e70daad8fbbe48369b5",
    },
    "2019": {
        "sha": "9a06e99c8a2d9cde51aa323d718d3d114937312254ae6148b1bf38d135c0b9b7",
        "bytes": 128914,
        "rendered": {
            "4438ab7f1555c0260e2534cfdb863fbec08349821d9e38554bfe90d8098a79a0": (
                75280,
                "be6d53fd6f04f28617b18311268ccd6834c0932fe403b23f7c67b8ca6a3055b7",
            ),
        },
        "site_div_sha": "83ab5cebfeef2b16cebd1972ff5c7d3fc67554675ba004fb3e58d12495c4116b",
    },
}
# 부착 없는 연도가 없어 비어 있다(PR-D: 2019·2020·2022·2023·2024 부착).
# 부착 연도는 ATTACH_YEARS.site_div_sha로 비교한다.
PRIOR_YEAR_SHA: dict[str, str] = {}
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


def _manifest_for(path: Path) -> Path:
    name = path.name
    if name.endswith(".json"):
        return path.with_name(name[: -len(".json")] + ".manifest.json")
    return path.with_name(name + ".manifest.json")


def _year_slice(html: str, year: str) -> str:
    try:
        start, end = _year_span(html, year)
    except ValueError:
        return ""
    return html[start:end]


def _div_sha(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, str] = {}
    for div in soup.select("div.fss-year"):
        year = str(div.get("data-year") or "")
        if year:
            found[year] = hashlib.sha256(str(div).encode("utf-8")).hexdigest()
    return found


def _same_as_above_count(html: str) -> int:
    return html.count('<p class="fss-f004-action">상동</p>')


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


def _count_error(year: str, key: str, got: int, expected: int) -> str:
    if year == "2025":
        return f"{key} 화면 {got} / 기대 {expected}"
    return f"{year} {key} 화면 {got} / 기대 {expected}"


def _year_section(html: str, year: str, spec: dict) -> tuple[dict, list[str]]:
    errors: list[str] = []
    path = ATTACH_PATHS[year]
    attach_raw = path.read_bytes()
    attach_sha = hashlib.sha256(attach_raw).hexdigest()
    manifest = json.loads(_manifest_for(path).read_text(encoding="utf-8"))
    if attach_sha != spec["sha"] or len(attach_raw) != spec["bytes"]:
        errors.append(f"{path.name} sha {attach_sha} bytes {len(attach_raw)}")
    manifest_mismatch = manifest.get("sha256") != spec["sha"] or manifest.get("bytes") != spec["bytes"]
    if manifest_mismatch:
        if year == "2025":
            errors.append("manifest sha 또는 bytes가 첨부 파일과 다릅니다.")
        else:
            errors.append(f"{year} manifest sha 또는 bytes가 첨부 파일과 다릅니다.")
    if manifest.get("file") != path.name:
        if year == "2025":
            errors.append("manifest file 이름이 다릅니다.")
        else:
            errors.append(f"{year} manifest file 이름이 다릅니다.")
    loaded = load_attach(path)
    count_source = loaded["counts"]
    year_sha = hashlib.sha256(YEAR_FILES[year].read_bytes()).hexdigest()
    slice_html = _year_slice(html, year)
    phrases = _phrase_counts(slice_html)
    counts = {
        "attach": slice_html.count('class="fss-f004-attach"'),
        "reason": slice_html.count('class="fss-f004-reason"'),
        "same": _short_reason_lines(slice_html),
        "no_date": phrases["no_date"],
        "no_action": phrases["no_action"],
        "note": phrases["note"],
        "mismatch": phrases["mismatch"],
        "no_finding": phrases["no_finding"],
    }
    expected = {
        "attach": count_source["attach_blocks"],
        "same": 0,
        "no_date": count_source["no_date_blocks"],
        "no_action": count_source["no_action_blocks"],
        "note": count_source["notes"],
        "mismatch": 0,
        "no_finding": 0,
    }
    if year == "2025":
        counts["dongsung"] = _dongsung(slice_html)
        expected["dongsung"] = count_source["dongsung_blocks"]
        reason_firms = {reason["firm"] for reason in loaded["firm_reasons"]}
        # 기대 패널 수는 검사할 페이지가 아니라 year-2025.json 렌더(부착 전)에서 센다.
        source_total, source_reason, _, _ = _reason_panels(
            render_year_2025_html(load_year_2025()), reason_firms
        )
        page_total, page_reason, reason_panel_bad, reason_firm_differ = _reason_panels(
            html, reason_firms
        )
        expected["reason"] = source_reason
        if page_total != source_total or page_reason != source_reason:
            errors.append(
                f"2025 패널 화면 {page_total}(사유 법인 {page_reason})"
                f" / 기대 {source_total}(사유 법인 {source_reason})"
            )
        # 사유 줄이 있는 법인 수는 counts.firm_reason_panels(= firm_reasons 수, load_attach가 확인)와 같아야 한다.
        present, wrong = _reason_content(html, loaded["firm_reasons"])
        if present != count_source["firm_reason_panels"]:
            errors.append(
                f"사유 줄이 있는 사유 법인 화면 {present} / 기대 {count_source['firm_reason_panels']}"
            )
        if wrong:
            errors.append(f"사유 줄 글·링크가 데이터와 다른 사유 법인 {wrong}곳")
        if reason_panel_bad:
            errors.append(f"사유 줄이 하나가 아닌 사유 법인 패널 {reason_panel_bad}개")
        if reason_firm_differ:
            errors.append(f"패널마다 사유 줄이 다른 사유 법인 {reason_firm_differ}곳")
    else:
        on_screen = count_source.get("firm_reason_panels_on_screen")
        if type(on_screen) is not int:
            errors.append(f"{year} firm_reason_panels_on_screen 형식이 아닙니다.")
            expected["reason"] = -1
        else:
            expected["reason"] = on_screen
    marks = count_source.get("verbatim_short_mark_blocks")
    same_above = None
    if isinstance(marks, dict) and "same_as_above_verbatim" in marks:
        same_above = _same_as_above_count(slice_html)
        if same_above != marks["same_as_above_verbatim"]:
            errors.append(
                f"{year} 상동 원문 화면 {same_above} / 기대 {marks['same_as_above_verbatim']}"
            )
    if year_sha not in spec["rendered"]:
        errors.append(f"year-{year}.json sha를 알 수 없습니다: {year_sha}")
        rendered_size = 0
        rendered_sha = ""
    else:
        rendered = inject_f004_attach(render_year_html(load_year(year))).encode("utf-8")
        rendered_size = len(rendered)
        rendered_sha = hashlib.sha256(rendered).hexdigest()
        expect_size, expect_sha = spec["rendered"][year_sha]
        if rendered_size != expect_size or rendered_sha != expect_sha:
            errors.append(
                f"{year} 렌더 부착 {rendered_size} B {rendered_sha} / 기대 {expect_size} B {expect_sha}"
            )
    for key, expected_value in expected.items():
        if counts[key] != expected_value:
            errors.append(_count_error(year, key, counts[key], expected_value))
    section = {
        "year_sha256": year_sha,
        "attach_sha256": attach_sha,
        "attach_bytes": len(attach_raw),
        "manifest_sha256": manifest.get("sha256"),
        "rendered_bytes": rendered_size,
        "rendered_sha256": rendered_sha,
        "counts": counts,
        "verbatim_same_as_above": same_above,
    }
    return section, errors


def build_report(html: str, search_index: Path = SEARCH_INDEX) -> dict:
    errors: list[str] = []
    div_sha = _div_sha(html)
    years: dict[str, dict] = {}
    for year, spec in ATTACH_YEARS.items():
        section, year_errors = _year_section(html, year, spec)
        site_sha = div_sha.get(year, "")
        section["site_div_sha256"] = site_sha
        if site_sha != spec["site_div_sha"]:
            year_errors.append(f"{year} 연도 블록 sha256이 고정값과 다릅니다: {site_sha}")
        years[year] = section
        errors.extend(year_errors)
    page_ids = _internal_hits(html)
    if page_ids:
        errors.append(f"내부 id가 페이지에 {page_ids}건 있습니다.")
    search = _search_index_report(search_index)
    errors.extend(search["errors"])
    prior = {year: div_sha[year] for year in PRIOR_YEAR_SHA if year in div_sha}
    prior_match = prior == PRIOR_YEAR_SHA
    if not prior_match:
        missing = sorted(set(PRIOR_YEAR_SHA) - set(prior))
        changed = sorted(year for year, digest in prior.items() if digest != PRIOR_YEAR_SHA[year])
        errors.append(f"부착 없는 연도 블록 sha256이 고정값과 다릅니다: 없음 {missing} 다름 {changed}")
    current = years["2025"]
    return {
        "years": years,
        "year_2025_sha256": current["year_sha256"],
        "attach_sha256": current["attach_sha256"],
        "attach_bytes": current["attach_bytes"],
        "manifest_sha256": current["manifest_sha256"],
        "rendered_bytes": current["rendered_bytes"],
        "rendered_sha256": current["rendered_sha256"],
        "counts": current["counts"],
        "prior_year_sha_match": prior_match,
        "internal_ids_in_page": page_ids,
        "internal_ids_in_search_index": search["ids"],
        "errors": errors,
    }


def _section_lines(year: str, section: dict) -> list[str]:
    counts = section["counts"]
    if year == "2025":
        file_sha = "f004-item-attach.json sha256"
        file_bytes = "f004-item-attach.json bytes"
    else:
        file_sha = f"f004-item-attach-{year}.json sha256"
        file_bytes = f"f004-item-attach-{year}.json bytes"
    lines = [
        f"year-{year}.json sha256: {section['year_sha256']}",
        f"{file_sha}: {section['attach_sha256']}",
        f"{file_bytes}: {section['attach_bytes']}",
        f"manifest sha256: {section['manifest_sha256']}",
        f"rendered bytes: {section['rendered_bytes']}",
        f"rendered sha256: {section['rendered_sha256']}",
        f"fss-f004-attach: {counts['attach']}",
        f"fss-f004-reason: {counts['reason']}",
        f"위와 같음·fss-f004-same: {counts['same']}",
        f"권고일 기재 없음: {counts['no_date']}",
        f"이행사항 기재 없음: {counts['no_action']}",
        f"한 행으로 공시: {counts['note']}",
        f"권고일 표기 불일치: {counts['mismatch']}",
        f"지적사항 없음: {counts['no_finding']}",
    ]
    if "dongsung" in counts:
        lines.append(f"동성회계법인 F004: {counts['dongsung']}")
    if year != "2025" and section.get("verbatim_same_as_above") is not None:
        lines.append(f"짧은 표시 상동: {section['verbatim_same_as_above']}")
    return lines


def render_text(report: dict) -> str:
    lines: list[str] = []
    for year, section in report["years"].items():
        lines.extend(_section_lines(year, section))
    lines.extend(
        [
            f"prior_year_sha_match: {str(report['prior_year_sha_match']).lower()}",
            f"internal_ids_in_page: {report['internal_ids_in_page']}",
            f"internal_ids_in_search_index: {report['internal_ids_in_search_index']}",
            f"errors: {len(report['errors'])}",
        ]
    )
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
