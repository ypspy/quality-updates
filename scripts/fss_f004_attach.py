# -*- coding: utf-8 -*-
"""품질관리감리 연도 블록의 지적 문단 바로 아래에 F004 개선권고 이행사항을 붙인다.

연도 블록을 다시 그리지 않는다. ``data/fss-review/f004-attach/manifest.json``에 있는 연도마다
그 연도 첨부 JSON이 정한 자리의 ``p.fss-finding`` 뒤에만 넣는다. 지금은 2025만 있다.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import unicodedata
from pathlib import Path

import fss_review_cards

ROOT = Path(__file__).resolve().parent.parent
ATTACH_DIR = ROOT / "data" / "fss-review" / "f004-attach"
MANIFEST_PATH = ATTACH_DIR / "manifest.json"
ALIASES_PATH = ATTACH_DIR / "aliases.json"
ATTACH_PATH = ATTACH_DIR / "2025.json"
_YEARS = range(2019, 2026)
_LOG = logging.getLogger("mkdocs.plugins.fss_f004_attach")
_DART_URL = re.compile(r"^https://dart\.fss\.or\.kr/dsaf001/main\.do\?rcpNo=\d{14}$")
_RCEPT_NO = re.compile(r"\d{14}")
_BANNED = "미" + "이행"
_NO_DATE = frozenset({"", "-"})
_FINDING = re.compile(r'<p class="fss-finding">(.*?)</p>', re.S)
_SEVERITY = re.compile(r'<span class="[^"]*">.*?</span>', re.S)
_ORIGINAL_NAME = re.compile(r'<div class="fss-original"[^>]*\bdata-names="([^"]*)"')
_BUNDLE_NAME = re.compile(r'<p class="fss-bundle-name">(.*?)</p>', re.S)
_H2 = re.compile(r"<h2>(.*?)</h2>", re.S)
_H3 = re.compile(r"<h3>(.*?)</h3>", re.S)
_GUN_NAME = re.compile(r'<p class="fss-gun-name">(.*?)</p>', re.S)
_REASON_P = re.compile(r'<p class="fss-f004-reason">.*?</p>', re.S)


def _esc_text(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=False)


def _esc_attr(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _one_line(fragment: str) -> str:
    if "\n" in fragment or "\r" in fragment:
        raise ValueError("F004 출력에 줄바꿈이 있습니다.")
    return fragment


def _read_manifest(manifest: Path = MANIFEST_PATH) -> dict:
    if not manifest.is_file():
        raise FileNotFoundError("F004 manifest가 없습니다.")
    try:
        meta = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("F004 manifest를 읽지 못했습니다.") from exc
    if not isinstance(meta, dict) or meta.get("schema") != "f004-attach-manifest/1":
        raise ValueError("F004 manifest 형식이 아닙니다.")
    years = meta.get("years")
    if not isinstance(years, dict) or not years:
        raise ValueError("F004 manifest years가 비어 있습니다.")
    for year, entry in years.items():
        if not isinstance(year, str) or not year.isdigit() or int(year) not in _YEARS:
            raise ValueError("F004 manifest 연도 형식이 아닙니다.")
        if not isinstance(entry, dict) or entry.get("file") != f"{year}.json":
            raise ValueError("F004 manifest 파일 이름이 연도와 다릅니다.")
    return meta


def _check_entry(path: Path, entry: object) -> None:
    if not path.is_file():
        raise FileNotFoundError("F004 파일이 없습니다.")
    if not isinstance(entry, dict):
        raise ValueError("F004 manifest 항목이 객체가 아닙니다.")
    digest_value = entry.get("sha256")
    size_value = entry.get("bytes")
    if not isinstance(digest_value, str) or type(size_value) is not int:
        raise ValueError("F004 manifest의 sha256 또는 bytes 형식이 아닙니다.")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest_value or len(raw) != size_value:
        raise ValueError("F004 sha256이 manifest와 다릅니다.")


def _verify_manifest(path: Path) -> None:
    """연도 파일 바이트 sha256과 길이가 manifest.json의 그 연도 항목과 같은지 확인한다."""
    meta = _read_manifest(path.parent / "manifest.json")
    entry = meta["years"].get(path.stem)
    if entry is None:
        raise ValueError("manifest에 없는 연도 파일입니다.")
    _check_entry(path, entry)


def manifest_years(manifest: Path | None = None) -> list[str]:
    """manifest에 적힌 연도(오름차순). 읽지 못하면 2025만(strip 기본값용)."""
    if manifest is None:
        manifest = Path(ATTACH_DIR) / "manifest.json"
    try:
        return sorted(_read_manifest(Path(manifest))["years"])
    except Exception:
        return ["2025"]


def load_aliases(path: Path | None = None) -> dict[tuple[str, int], str]:
    """별칭표를 읽어 (다른 이름, 감리연도) → 화면 이름 사전을 돌려준다.

    옆에 manifest.json이 있으면 그 ``aliases`` 항목의 sha256·bytes를 먼저 확인한다.
    """
    path = Path(ATTACH_DIR) / "aliases.json" if path is None else Path(path)
    manifest = path.parent / "manifest.json"
    if manifest.is_file() or path.parent.resolve() == Path(ATTACH_DIR).resolve():
        _check_entry(path, _read_manifest(manifest).get("aliases"))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("별칭표를 읽지 못했습니다.") from exc
    if not isinstance(data, dict) or data.get("schema") != "f004-attach-aliases/1":
        raise ValueError("별칭표 형식이 아닙니다.")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("별칭표 entries가 목록이 아닙니다.")
    table: dict[tuple[str, int], str] = {}
    canon_years: set[tuple[str, int]] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("별칭표 항목이 객체가 아닙니다.")
        canonical = entry.get("canonical")
        names = entry.get("aliases")
        years = entry.get("years")
        if not isinstance(canonical, str) or not canonical:
            raise ValueError("별칭표 canonical이 없습니다.")
        code = entry.get("corp_code")
        if code is not None and (not isinstance(code, str) or re.fullmatch(r"\d{8}", code) is None):
            raise ValueError("별칭표 corp_code 형식이 아닙니다.")
        if not isinstance(names, list) or not names or not all(isinstance(n, str) and n for n in names):
            raise ValueError("별칭표 aliases 형식이 아닙니다.")
        if canonical in names or len(set(names)) != len(names):
            raise ValueError("별칭표 aliases에 canonical이나 중복이 있습니다.")
        if (
            not isinstance(years, list)
            or not years
            or any(type(y) is not int or y not in _YEARS for y in years)
            or years != sorted(set(years))
        ):
            raise ValueError("별칭표 years 형식이 아닙니다.")
        for key in ("source", "decided_by"):
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"별칭표 {key}가 없습니다.")
            if _BANNED in value:
                raise ValueError("원문 필드 밖에 금지어가 있습니다.")
        for year in years:
            canon_years.add((canonical, year))
            for name in names:
                if (name, year) in table:
                    raise ValueError("같은 연도에 한 이름이 두 법인을 가리킵니다.")
                table[(name, year)] = canonical
    for name, year in table:
        if (name, year) in canon_years:
            raise ValueError("별칭이 같은 연도의 다른 canonical과 겹칩니다.")
    return table


def _reject_dart_url(obj: object) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "dart_url":
                if not isinstance(value, str) or not _DART_URL.fullmatch(value):
                    raise ValueError("dart_url 형식이 아닙니다.")
            else:
                _reject_dart_url(value)
        return
    if isinstance(obj, list):
        for value in obj:
            _reject_dart_url(value)


def _require_rcept_pair(rcept: object, url: object) -> None:
    if not isinstance(rcept, str) or _RCEPT_NO.fullmatch(rcept) is None:
        raise ValueError("rcept_no 형식이 아닙니다.")
    expected = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept}"
    if url != expected:
        raise ValueError("dart_url이 rcept_no와 맞지 않습니다.")


def _validate_f004_row(row_id: object, row: object) -> None:
    if not isinstance(row, dict):
        raise ValueError("f004_rows 행이 객체가 아닙니다.")
    _require_rcept_pair(row.get("rcept_no"), row.get("dart_url"))
    rcept = row["rcept_no"]
    if not isinstance(row_id, str) or not row_id.startswith(rcept + ":"):
        raise ValueError("행 id가 rcept_no로 시작하지 않습니다.")
    kind = row.get("action_kind")
    if not isinstance(kind, str) or not kind:
        raise ValueError("action_kind 형식이 아닙니다.")
    action = row.get("action")
    if kind == "none":
        if action is not None and not isinstance(action, str):
            raise ValueError("action 형식이 아닙니다.")
    elif not isinstance(action, str):
        raise ValueError("action 형식이 아닙니다.")
    raw_date = row.get("recommend_date_raw")
    if raw_date is not None and not isinstance(raw_date, str):
        raise ValueError("recommend_date_raw 형식이 아닙니다.")


def _path_key(path: dict) -> tuple:
    try:
        bundle = path["bundle"]
        section = path["section"]
        group = path["group"]
        gun = path["gun"]
        firm = path["firm"]
        index = path["index"]
    except KeyError as exc:
        raise ValueError("attachment path 키가 없습니다.") from exc
    for name, value in (
        ("bundle", bundle),
        ("section", section),
        ("group", group),
        ("firm", firm),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"path {name} 형식이 아닙니다.")
    if gun is not None and not isinstance(gun, str):
        raise ValueError("path gun 형식이 아닙니다.")
    if type(index) is not int:
        raise ValueError("attachment index가 정수가 아닙니다.")
    return (bundle, section, group, gun, firm, index)


def _validate(data: dict, aliases: dict | None = None) -> None:
    year = data.get("year")
    if not isinstance(year, str) or not year.isdigit() or int(year) not in _YEARS:
        raise ValueError("year 형식이 아닙니다.")
    attachments = data.get("attachments")
    reasons = data.get("firm_reasons")
    rows = data.get("f004_rows")
    counts = data.get("counts")
    if not isinstance(counts, dict):
        raise ValueError("counts가 객체가 아닙니다.")
    slots = counts.get("attach_slots")
    lines = counts.get("firm_reason_lines")
    if type(slots) is not int or type(lines) is not int:
        raise ValueError("counts 형식이 아닙니다.")
    if not isinstance(attachments, list) or not attachments:
        raise ValueError("attachments가 비어 있습니다.")
    if not isinstance(reasons, list):
        raise ValueError("firm_reasons가 목록이 아닙니다.")
    if slots != len(attachments) or lines != len(reasons):
        raise ValueError("counts가 목록 길이와 다릅니다.")
    reason_panels = counts.get("firm_reason_panels")
    if reason_panels is not None:
        if type(reason_panels) is not int or reason_panels < len(reasons):
            raise ValueError("counts.firm_reason_panels가 사유 법인 수보다 작습니다.")
    if not isinstance(rows, dict):
        raise ValueError("f004_rows가 없습니다.")
    _reject_dart_url(data)
    for row_id, row in rows.items():
        _validate_f004_row(row_id, row)
    seen: set[tuple] = set()
    for att in attachments:
        if not isinstance(att, dict):
            raise ValueError("attachment가 객체가 아닙니다.")
        path = att.get("path")
        if not isinstance(path, dict):
            raise ValueError("attachment path가 없습니다.")
        key = _path_key(path)
        if key in seen:
            raise ValueError("부착 자리가 겹칩니다.")
        seen.add(key)
        items = att.get("f004")
        if not isinstance(items, list) or not items:
            raise ValueError("f004 행이 없습니다.")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("f004 항목이 객체가 아닙니다.")
            row_id = item.get("f004_row_id")
            if not isinstance(row_id, str) or row_id not in rows:
                raise ValueError("f004_row_id가 f004_rows에 없습니다.")
            row_firm = rows[row_id]["firm"]
            if row_firm != path["firm"] and (aliases or {}).get((row_firm, int(year))) != path["firm"]:
                raise ValueError("F004 법인 이름이 화면 이름과 다르고 별칭표에도 없습니다.")
            note = item.get("note")
            if note is not None and not isinstance(note, str):
                raise ValueError("note 형식이 아닙니다.")
            if isinstance(note, str) and _BANNED in note:
                raise ValueError("원문 필드 밖에 금지어가 있습니다.")
    blocks = counts.get("attach_blocks")
    if blocks is not None:
        if type(blocks) is not int or blocks != sum(len(att["f004"]) for att in attachments):
            raise ValueError("counts가 목록 길이와 다릅니다.")
    seen_firms: set[str] = set()
    for reason in reasons:
        if not isinstance(reason, dict):
            raise ValueError("firm_reasons 항목이 객체가 아닙니다.")
        text = reason.get("text")
        if not isinstance(text, str):
            raise ValueError("text 형식이 아닙니다.")
        if _BANNED in text:
            raise ValueError("원문 필드 밖에 금지어가 있습니다.")
        firm = reason.get("firm")
        if not isinstance(firm, str) or not firm:
            raise ValueError("firm_reasons 법인 이름이 없습니다.")
        if firm in seen_firms:
            raise ValueError("firm_reasons 법인이 겹칩니다.")
        seen_firms.add(firm)
        disclosure = reason.get("disclosure")
        if disclosure is not None and not isinstance(disclosure, dict):
            raise ValueError("disclosure 형식이 아닙니다.")
        if isinstance(disclosure, dict):
            _require_rcept_pair(disclosure.get("rcept_no"), disclosure.get("dart_url"))


def load_attach(path: Path | None = None) -> dict:
    """manifest를 확인한 뒤 UTF-8 JSON을 읽고 부착 제약을 확인한다.

    기본은 ``ATTACH_DIR/2025.json``. 옆에 manifest.json이 있거나 ``ATTACH_DIR`` 안이면
    manifest의 그 연도 항목과 sha256·bytes를 비교한다. 옆에 aliases.json이 있으면 별칭표로 쓴다.
    """
    path = Path(ATTACH_DIR) / "2025.json" if path is None else Path(path)
    in_dir = path.parent.resolve() == Path(ATTACH_DIR).resolve()
    if in_dir or (path.parent / "manifest.json").is_file():
        _verify_manifest(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("F004 JSON을 읽지 못했습니다.") from exc
    if not isinstance(data, dict):
        raise ValueError("F004 JSON이 객체가 아닙니다.")
    if (in_dir or (path.parent / "manifest.json").is_file()) and data.get("year") != path.stem:
        raise ValueError("연도 파일 이름과 year가 다릅니다.")
    aliases_path = path.parent / "aliases.json"
    aliases = load_aliases(aliases_path) if in_dir or aliases_path.is_file() else {}
    _validate(data, aliases)
    return data


def load_all(directory: Path | None = None) -> dict[str, dict]:
    """manifest의 모든 연도 파일을 읽는다. manifest를 읽지 못하면 오류."""
    directory = Path(ATTACH_DIR) if directory is None else Path(directory)
    years = sorted(_read_manifest(directory / "manifest.json")["years"])
    return {year: load_attach(directory / f"{year}.json") for year in years}


def _finding_plain(inner: str) -> str:
    match = _SEVERITY.match(inner)
    if match:
        inner = inner[match.end() :]
    plain = html.unescape(inner).strip()
    return unicodedata.normalize("NFC", plain)


def _finding_sha(inner: str) -> str:
    return hashlib.sha256(_finding_plain(inner).encode("utf-8")).hexdigest()


def _render_one(item: dict, row: dict) -> str:
    note = item.get("note")
    note_html = "" if not note else " (" + _esc_text(note) + ")"
    raw = row.get("recommend_date_raw")
    raw_text = "" if raw is None else str(raw)
    date = "기재 없음" if raw_text.strip() in _NO_DATE else _esc_text(raw_text)
    if row.get("action_kind") == "none":
        action = "이행사항 기재 없음"
    else:
        action = _esc_text(row.get("action"))
    url = _esc_attr(row.get("dart_url"))
    rcept = _esc_text(row.get("rcept_no"))
    return _one_line(
        '<div class="fss-f004-attach"><p class="fss-f004-head">F004 개선권고 이행사항'
        f"{note_html} · 권고일 {date} · "
        f'<a href="{url}" rel="noopener" target="_blank">{rcept}</a></p>'
        f'<p class="fss-f004-action">{action}</p></div>'
    )


def _render_reason(reason: dict) -> str:
    link = ""
    disclosure = reason.get("disclosure")
    if disclosure:
        link = (
            " · "
            f'<a href="{_esc_attr(disclosure.get("dart_url"))}" rel="noopener" target="_blank">'
            f'{_esc_text(disclosure.get("rcept_no"))}</a>'
        )
    return _one_line(f'<p class="fss-f004-reason">{_esc_text(reason.get("text"))}{link}</p>')


def _iter_panels(block: str):
    """연도 블록 안 ``div.fss-original``을 문서 순서대로 연다."""
    for bundle_start, bundle_end in fss_review_cards._regions(block, '<div class="fss-bundle">'):
        bundle_html = block[bundle_start:bundle_end]
        bundle_match = _BUNDLE_NAME.search(bundle_html)
        if not bundle_match:
            raise ValueError("묶음 이름이 없습니다.")
        bundle_name = html.unescape(bundle_match.group(1))
        for section_start, section_end in fss_review_cards._iter_sections(bundle_html, "fss-dae"):
            section = bundle_html[section_start:section_end]
            section_match = _H2.search(section)
            if not section_match:
                raise ValueError("대분류 제목이 없습니다.")
            section_title = html.unescape(section_match.group(1))
            for group_start, group_end in fss_review_cards._iter_sections(section, "fss-jung"):
                group = section[group_start:group_end]
                group_match = _H3.search(group)
                if not group_match:
                    raise ValueError("중분류 제목이 없습니다.")
                group_title = html.unescape(group_match.group(1))
                cursor = 0
                while True:
                    at = group.find('<article class="fss-group"', cursor)
                    if at < 0:
                        break
                    article_end = group.find("</article>", at)
                    if article_end < 0:
                        raise ValueError("article이 닫히지 않습니다.")
                    article_end += len("</article>")
                    article = group[at:article_end]
                    gun_match = _GUN_NAME.search(article)
                    gun = html.unescape(gun_match.group(1)) if gun_match else None
                    base = bundle_start + section_start + group_start + at
                    for panel_start, panel_end in fss_review_cards._regions(
                        article, '<div class="fss-original"'
                    ):
                        yield {
                            "start": base + panel_start,
                            "end": base + panel_end,
                            "bundle": bundle_name,
                            "section": section_title,
                            "group": group_title,
                            "gun": gun,
                            "html": article[panel_start:panel_end],
                        }
                    cursor = article_end


def _index_attachments(data: dict) -> dict[tuple, dict[int, dict]]:
    indexed: dict[tuple, dict[int, dict]] = {}
    for att in data["attachments"]:
        path = att["path"]
        key = (path["bundle"], path["section"], path["group"], path["gun"], path["firm"])
        indexed.setdefault(key, {})[path["index"]] = att
    return indexed


def _fill_panel(panel: str, indexed: dict[int, dict], reason: dict | None, rows: dict):
    matches = list(_FINDING.finditer(panel))
    inserts: dict[int, str] = {}
    resolved: list[dict] = []
    skipped: list[dict] = []
    for index, att in indexed.items():
        if index < 0 or index >= len(matches):
            skipped.append(att)
            continue
        if _finding_sha(matches[index].group(1)) != att.get("text_sha256"):
            skipped.append(att)
            continue
        bits = []
        for item in att["f004"]:
            row_id = item["f004_row_id"]
            if row_id not in rows:
                raise ValueError("f004_row_id가 f004_rows에 없습니다.")
            bits.append(_render_one(item, rows[row_id]))
        inserts[matches[index].end()] = "".join(bits)
        resolved.append(att)
    if not panel.endswith("</div>"):
        raise ValueError("원문 패널이 닫히지 않습니다.")
    body_end = len(panel) - len("</div>")
    parts: list[str] = []
    cursor = 0
    for pos in sorted(inserts):
        if pos > body_end:
            raise ValueError("지적 문단이 패널 밖에 있습니다.")
        parts.append(panel[cursor:pos])
        parts.append(inserts[pos])
        cursor = pos
    parts.append(panel[cursor:body_end])
    if reason is not None:
        parts.append(_render_reason(reason))
    parts.append("</div>")
    return _one_line("".join(parts)), resolved, skipped


def _year_span(page: str, year: str = "2025") -> tuple[int, int]:
    found: list[tuple[int, int]] = []
    for start, end in fss_review_cards._year_regions(page):
        head_end = page.find(">", start)
        if head_end < 0 or head_end > end:
            raise ValueError("감리연도 태그가 닫히지 않았습니다.")
        if f'data-year="{year}"' in page[start : head_end + 1]:
            found.append((start, end))
    if len(found) != 1:
        raise ValueError(f"감리연도 {year} 블록이 하나가 아닙니다.")
    return found[0]


def _insert_attach(page: str, data: dict, *, strict: bool) -> str:
    year = data["year"]
    start, end = _year_span(page, year)
    block = page[start:end]
    by_key = _index_attachments(data)
    reasons = {reason["firm"]: reason for reason in data["firm_reasons"]}
    rows = data["f004_rows"]
    resolved: list[dict] = []
    skipped: list[dict] = []
    seen: set[int] = set()
    reason_panels = 0
    reason_firms: set[str] = set()
    parts: list[str] = []
    cursor = 0
    for panel in _iter_panels(block):
        name_match = _ORIGINAL_NAME.search(panel["html"])
        if not name_match:
            raise ValueError("원문 패널에 법인 이름이 없습니다.")
        firm = html.unescape(name_match.group(1))
        key = (panel["bundle"], panel["section"], panel["group"], panel["gun"], firm)
        indexed = {
            index: att
            for index, att in by_key.get(key, {}).items()
            if id(att) not in seen
        }
        # 사유 법인은 그 연도의 모든 패널에 같은 사유 줄 전체를 단다 (사용자 결정 2026-11-15 9:14 AM CT).
        reason = reasons.get(firm)
        updated, got, missed = _fill_panel(panel["html"], indexed, reason, rows)
        for att in got:
            seen.add(id(att))
        for att in missed:
            seen.add(id(att))
        resolved.extend(got)
        skipped.extend(missed)
        if reason is not None:
            reason_panels += 1
            reason_firms.add(firm)
        parts.append(block[cursor : panel["start"]])
        parts.append(updated)
        cursor = panel["end"]
    parts.append(block[cursor:])
    updated_block = "".join(parts)
    for att in data["attachments"]:
        if id(att) not in seen:
            skipped.append(att)
    if ("\n" not in block and "\r" not in block) and (
        "\n" in updated_block or "\r" in updated_block
    ):
        raise ValueError("F004 출력에 줄바꿈이 있습니다.")
    summary = (
        f"F004 부착 {year}: 자리 {len(resolved)}/{len(data['attachments'])}, "
        f"이행사항 {sum(len(att['f004']) for att in resolved)}, "
        f"법인 사유 {len(reason_firms)}곳({reason_panels}칸), 건너뜀 {len(skipped)}"
    )
    if strict and skipped:
        raise ValueError("F004 부착 자리를 맞추지 못했습니다.")
    _LOG.info("%s", summary)
    return page[:start] + updated_block + page[end:]


def inject_f004_attach(page: str, data: dict | None = None, *, strict: bool | None = None) -> str:
    """연도 블록의 지적 문단 바로 뒤에 이행사항을 붙인다. 블록 밖은 그대로 둔다.

    ``data``가 없으면 manifest의 모든 연도를 읽고, 실패하면 입력 페이지를 그대로 돌려준다.
    ``data``(한 연도)를 넘기면 기본은 엄격하다. ``strict=False``면 못 찾은 자리만 건너뛴다.
    """
    original = page
    if data is None:
        try:
            datasets = load_all()
        except Exception as exc:
            _LOG.info("F004 부착을 하지 않습니다: %s: %s", type(exc).__name__, exc)
            return original
        try:
            out = strip_f004_attach(page, list(datasets))
            for year in sorted(datasets):
                out = _insert_attach(out, datasets[year], strict=False)
            return out
        except Exception as exc:
            _LOG.info("F004 부착을 하지 않습니다: %s: %s", type(exc).__name__, exc)
            return original
    if strict is None:
        strict = True
    return _insert_attach(strip_f004_attach(page, [data["year"]]), data, strict=strict)


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not spans:
        return []
    merged: list[list[int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
            continue
        merged.append([start, end])
    return [(start, end) for start, end in merged]


def strip_f004_attach(page: str, years: list[str] | None = None) -> str:
    """부착 연도 블록 안에 붙인 이행사항과 법인 사유만 지운다. 다른 연도는 그대로 둔다."""
    for year in years if years is not None else manifest_years():
        try:
            start, end = _year_span(page, year)
        except ValueError:
            continue
        block = page[start:end]
        spans = list(fss_review_cards._regions(block, '<div class="fss-f004-attach"'))
        spans.extend((match.start(), match.end()) for match in _REASON_P.finditer(block))
        for rel_start, rel_end in reversed(_merge_spans(spans)):
            block = block[:rel_start] + block[rel_end:]
        page = page[:start] + block + page[end:]
    return page
