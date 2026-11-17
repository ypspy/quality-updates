# -*- coding: utf-8 -*-
import hashlib
import html as html_lib
import json
import logging
import re
from pathlib import Path

import pytest

from fss_f004_attach import (  # noqa: E402
    ATTACH_PATH,
    inject_f004_attach,
    load_attach,
    strip_f004_attach,
)
from fss_review_cards import (  # noqa: E402
    PAGE,
    YEAR_2025_PATH,
    _matching_div_end,
    _regions,
    load_year,
    load_year_2025,
    materialize_review_markdown,
    render_year_html,
    render_year_2025_html,
)
from mkdocs_fss_review_year import on_page_markdown  # noqa: E402
from tests.test_fss_review_cards import _Page  # noqa: E402

import check_f004_attach_render as check_mod  # noqa: E402
import fss_f004_attach  # noqa: E402

# sha256sum data/fss-review/f004-item-attach.json
ATTACH_SHA = "2d8820567ad80dd4a6484cdd88a2e9891573e6ad250b931e6ebee8b53c6e93f9"
ATTACH_BYTES = 246646
# render_year_2025_html(load_year_2025())에 부착한 2025 블록.
RENDERED = {
    "1c6df2500ba918054bd4b22b3a983af9ef3bdecdedc54908d4a54a04e1ea72e4": (
        317065,
        "c250624d21907095667438d0326c1e7765464575da6655d3a119db3dc7e774cc",
    ),
}
_SUMMARY = "F004 부착: 자리 143/143, 이행사항 151, 법인 사유 41곳(136칸), 건너뜀 0"
_REASON = 'class="fss-f004-reason"'


def _banned() -> str:
    return "미" + "이행"


def _year_block() -> str:
    return render_year_2025_html(load_year_2025())


def _injected() -> str:
    return inject_f004_attach(_year_block(), load_attach())


def _panel_with(html: str, marker: str) -> str:
    at = html.find(marker)
    assert at >= 0
    start = html.rfind('<div class="fss-original"', 0, at)
    assert start >= 0
    end = _matching_div_end(html, start)
    return html[start:end]


def _panels_named(html: str, firm: str) -> list[str]:
    found = []
    needle = f'data-names="{firm}"'
    for start, end in _regions(html, '<div class="fss-original"'):
        chunk = html[start:end]
        if needle in chunk.split(">", 1)[0]:
            found.append(chunk)
    return found


def _hook(source: str, caplog) -> str:
    with caplog.at_level(logging.INFO, logger="mkdocs.plugins.fss_f004_attach"):
        return on_page_markdown(source, _Page("fss-review/index.md"), None, None)


def _year_slice(page: str, year: str) -> str:
    start, end = fss_f004_attach._year_span(page, year)
    return page[start:end]


def _same_2025_block(built: str, expected: str) -> None:
    assert _year_slice(built, "2025") == _year_slice(expected, "2025")


def test_attach_file_matches_sha_and_manifest():
    raw = ATTACH_PATH.read_bytes()
    assert len(raw) == ATTACH_BYTES
    assert hashlib.sha256(raw).hexdigest() == ATTACH_SHA
    manifest = json.loads((ATTACH_PATH.parent / "f004-item-attach.manifest.json").read_text(encoding="utf-8"))
    assert manifest == {"file": "f004-item-attach.json", "sha256": ATTACH_SHA, "bytes": ATTACH_BYTES}


def test_load_attach_counts_match_the_locked_table():
    data = load_attach()
    assert len(data["attachments"]) == 143
    assert len(data["firm_reasons"]) == 41
    items = 0
    no_date = 0
    no_action = 0
    notes = 0
    for att in data["attachments"]:
        for item in att["f004"]:
            items += 1
            row = data["f004_rows"][item["f004_row_id"]]
            raw = row.get("recommend_date_raw")
            if raw is None or str(raw).strip() in {"", "-"}:
                no_date += 1
            if row.get("action_kind") == "none":
                no_action += 1
            note = item.get("note") or ""
            if "한 행으로 공시" in note:
                notes += 1
    assert items == 151
    assert no_date == 9
    assert no_action == 14
    assert notes == 35
    counts = data["counts"]
    assert counts["attach_slots"] == 143
    assert counts["attach_blocks"] == 151
    assert counts["firm_reason_lines"] == 41
    assert counts["firm_reason_panels"] == 41
    assert counts["attached_f004_rows"] == 143
    assert counts["unattached_f004_rows"] == 0
    assert counts["unattached_qu_findings"] == 9
    assert counts["dongsung_blocks"] == 10
    assert "pending" not in data


def test_rendered_2025_block_matches_the_locked_bytes():
    year_sha = hashlib.sha256(YEAR_2025_PATH.read_bytes()).hexdigest()
    assert year_sha in RENDERED
    size, digest = RENDERED[year_sha]
    raw = _injected().encode("utf-8")
    assert len(raw) == size
    assert hashlib.sha256(raw).hexdigest() == digest


def test_every_slot_resolves(caplog):
    with caplog.at_level(logging.INFO, logger="mkdocs.plugins.fss_f004_attach"):
        built = _injected()
    assert _SUMMARY in caplog.text
    assert built.count('class="fss-f004-attach"') == 151
    assert built.count(_REASON) == 136
    assert "위와 같음" not in built
    assert "fss-f004-same" not in built
    assert "건너뜀 0" in caplog.text


def test_changed_paragraph_is_strict_or_skipped(caplog):
    data = load_attach()
    block = _year_block()
    marker = "감사업무프로그램(Aura)"
    assert block.count(marker) == 1
    altered = block.replace(marker, marker + "추가", 1)
    with pytest.raises(ValueError):
        inject_f004_attach(altered, data)
    with caplog.at_level(logging.INFO, logger="mkdocs.plugins.fss_f004_attach"):
        built = inject_f004_attach(altered, data, strict=False)
    assert "자리 142/143" in caplog.text
    assert "건너뜀 1" in caplog.text
    assert built.count('class="fss-f004-attach"') == 150
    at = built.find(marker + "추가")
    end = built.find("</p>", at)
    assert not built.startswith('<div class="fss-f004-attach"', end + len("</p>"))
    assert built.count(_REASON) == 136
    assert "위와 같음" not in built


def test_bad_file_keeps_the_materialized_page(tmp_path, monkeypatch, caplog):
    source = PAGE.read_text(encoding="utf-8")
    expected = materialize_review_markdown(source)
    monkeypatch.setattr(fss_f004_attach, "ATTACH_PATH", Path("/tmp/f004-item-attach-missing.json"))
    _same_2025_block(_hook(source, caplog), expected)
    assert "F004 부착을 하지 않습니다" in caplog.text

    caplog.clear()
    raw = bytearray(ATTACH_PATH.read_bytes())
    raw[20] ^= 0x01
    path = tmp_path / "f004-item-attach.json"
    path.write_bytes(raw)
    (tmp_path / "f004-item-attach.manifest.json").write_text(
        json.dumps({"file": "f004-item-attach.json", "sha256": ATTACH_SHA, "bytes": ATTACH_BYTES}),
        encoding="utf-8",
    )
    monkeypatch.setattr(fss_f004_attach, "ATTACH_PATH", path)
    _same_2025_block(_hook(source, caplog), expected)
    assert "sha256" in caplog.text

    caplog.clear()
    payload = b"{"
    broken = tmp_path / "broken" / "f004-item-attach.json"
    broken.parent.mkdir()
    broken.write_bytes(payload)
    (broken.parent / "f004-item-attach.manifest.json").write_text(
        json.dumps(
            {
                "file": "f004-item-attach.json",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(fss_f004_attach, "ATTACH_PATH", broken)
    _same_2025_block(_hook(source, caplog), expected)
    assert "F004 부착을 하지 않습니다" in caplog.text


def test_strip_restores_the_page_and_output_has_no_newline():
    block = _year_block()
    injected = _injected()
    assert "\n" not in injected and "\r" not in injected
    assert strip_f004_attach(injected) == block
    page = materialize_review_markdown(PAGE.read_text(encoding="utf-8"))
    built = inject_f004_attach(page)
    assert strip_f004_attach(built) == page
    wrapped = "앞\n" + block + "\n뒤"
    out = inject_f004_attach(wrapped, load_attach())
    assert out.startswith("앞\n") and out.endswith("\n뒤")
    assert "\n" not in out[len("앞\n") : -len("\n뒤")]
    assert strip_f004_attach(out) == wrapped
    assert inject_f004_attach(injected, load_attach()) == injected


def test_samil_54_panel_uses_the_attach_shape():
    data = load_attach()
    att = next(
        item
        for item in data["attachments"]
        if item["path"]["firm"] == "삼일회계법인" and item["path"]["group"].startswith("5.4")
    )
    assert len(att["f004"]) == 1
    row = data["f004_rows"][att["f004"][0]["f004_row_id"]]
    assert row["recommend_date_raw"] == "2026.05.12"
    assert row["rcept_no"] == "20260930000134"
    expected = (
        '<div class="fss-f004-attach"><p class="fss-f004-head">F004 개선권고 이행사항'
        f' · 권고일 {row["recommend_date_raw"]} · '
        f'<a href="{row["dart_url"]}" rel="noopener" target="_blank">{row["rcept_no"]}</a></p>'
        f'<p class="fss-f004-action">{row["action"]}</p></div>'
    )
    panel = _panel_with(_injected(), "감사업무프로그램(Aura)")
    assert panel.count(expected) == 1
    assert panel.count('class="fss-f004-attach"') == 1
    at = panel.find("감사업무프로그램(Aura)")
    end = panel.find("</p>", at)
    assert panel.startswith(expected, end + len("</p>"))


def test_samil_41_second_paragraph_has_the_shared_row_note():
    html = _injected()
    panel = _panel_with(html, "Time report에 입력")
    assert panel.count('<p class="fss-finding">') == 2
    assert panel.count('class="fss-f004-attach"') == 1
    note = "위 2개 문단을 F004 한 행으로 공시"
    assert f"F004 개선권고 이행사항 ({note}) · 권고일 2026.05.12" in panel
    first_end = panel.find("</p>")
    assert not panel.startswith('<div class="fss-f004-attach"', first_end + len("</p>"))
    second = panel.find('<p class="fss-finding">', first_end)
    second_end = panel.find("</p>", second)
    assert panel.startswith('<div class="fss-f004-attach"', second_end + len("</p>"))


def test_seowon_61_keeps_two_followups_in_data_order():
    data = load_attach()
    att = next(
        item
        for item in data["attachments"]
        if item["path"]["firm"] == "서원회계법인" and item["path"]["group"].startswith("6.1")
    )
    actions = [data["f004_rows"][item["f004_row_id"]]["action"] for item in att["f004"]]
    assert len(actions) == 2
    panel = _panel_with(_injected(), "심리결과 등이 형식적으로 작성되고")
    assert panel.count('class="fss-f004-attach"') == 2
    first = panel.find(actions[0])
    second = panel.find(actions[1])
    assert 0 <= first < second
    finding_end = panel.find("</p>")
    assert panel.startswith('<div class="fss-f004-attach"', finding_end + len("</p>"))


def test_daeju_panels_link_the_disclosure_and_audit_teams_do_not():
    data = load_attach()
    html = _injected()
    daeju = _panels_named(html, "대주회계법인")
    assert daeju
    assert daeju[0].count('class="fss-f004-reason"') == 1
    assert "20260630000869" in daeju[0]
    assert 'href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260630000869"' in daeju[0]
    assert len(daeju) >= 2
    first = re.search(r'<p class="fss-f004-reason">.*?</p>', daeju[0]).group(0)
    for panel in daeju[1:]:
        assert panel.count(_REASON) == 1
        assert first in panel
        assert 'href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260630000869"' in panel
    audit_firms = [reason["firm"] for reason in data["firm_reasons"] if reason["reason"] == "audit_team"]
    assert len(audit_firms) == 19
    seen = 0
    for firm in audit_firms:
        panels = _panels_named(html, firm)
        assert panels
        seen += 1
        match = re.search(r'<p class="fss-f004-reason">.*?</p>', panels[0])
        assert match
        assert "<a " not in match.group(0)
        for panel in panels[1:]:
            again = re.search(r'<p class="fss-f004-reason">.*?</p>', panel)
            assert again
            assert again.group(0) == match.group(0)
            assert "<a " not in again.group(0)
    assert seen == 19


def test_dongsung_gets_ten_blocks_and_unattached_paragraphs_have_none():
    data = load_attach()
    html = _injected()
    dongsung = _panels_named(html, "동성회계법인")
    assert dongsung
    assert sum(panel.count('class="fss-f004-attach"') for panel in dongsung) == 10
    assert sum(panel.count("fss-f004-reason") for panel in dongsung) == 0
    assert sum(panel.count("이행사항 기재 없음") for panel in dongsung) == 10
    unattached = {}
    for row in data["unattached"]["qu_findings"]:
        _, bundle, group_no, gun, firm, index = row["finding_id"].split("/")
        ident = (bundle, group_no, None if gun == "-" else gun, firm, int(index))
        unattached[ident] = row["text_sha256"]
    assert len(unattached) == 9
    hits = 0
    for panel in fss_f004_attach._iter_panels(html):
        name = fss_f004_attach._ORIGINAL_NAME.search(panel["html"])
        assert name
        firm = html_lib.unescape(name.group(1))
        group_no = panel["group"].split(" ", 1)[0]
        for index, match in enumerate(re.finditer(r'<p class="fss-finding">(.*?)</p>', panel["html"])):
            ident = (panel["bundle"], group_no, panel["gun"], firm, index)
            if ident not in unattached:
                continue
            hits += 1
            assert fss_f004_attach._finding_sha(match.group(1)) == unattached[ident]
            assert not panel["html"].startswith('<div class="fss-f004-attach"', match.end())
    assert hits == 9


def test_hidden_labels_are_absent():
    html = _injected()
    assert "권고일 표기 불일치" not in html
    assert "F004: 지적사항 없음" not in html
    assert "지적사항 없음" not in html


def test_our_phrases_do_not_contain_the_banned_word(tmp_path):
    banned = _banned()
    html = _injected()
    for pattern in (r'<p class="fss-f004-head">(.*?)</p>', r'<p class="fss-f004-reason">(.*?)</p>'):
        found = list(re.finditer(pattern, html))
        assert found
        for match in found:
            assert banned not in match.group(1)
    data = load_attach()
    for att in data["attachments"]:
        for item in att["f004"]:
            assert banned not in (item.get("note") or "")
    for reason in data["firm_reasons"]:
        assert banned not in reason["text"]
    copied = json.loads(json.dumps(data))
    copied["attachments"][0]["f004"][0]["note"] = "확인 " + banned
    path = tmp_path / "f004-item-attach.json"
    path.write_text(json.dumps(copied, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        load_attach(path)


_LOOKALIKE_REASON = '<p class="fss-f004-reason">2024 원문</p>'
_LOOKALIKE_ATTACH = '<div class="fss-f004-attach"><p>2024 원문</p></div>'
_LOOKALIKE_MENTION = '<p class="fss-f004-reason">2024 짝없음'
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


def _copy_attach() -> dict:
    return json.loads(json.dumps(load_attach()))


def _dump_attach(directory: Path, data: dict) -> Path:
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "f004-item-attach.json"
    path.write_bytes(payload)
    manifest = {
        "file": "f004-item-attach.json",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }
    (directory / "f004-item-attach.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _with_2024_lookalikes(page: str) -> str:
    marker = '<div class="fss-year" data-year="2024" hidden>'
    at = page.find(marker)
    assert at >= 0
    insert_at = at + len(marker)
    extra = _LOOKALIKE_REASON + _LOOKALIKE_ATTACH + _LOOKALIKE_MENTION
    return page[:insert_at] + extra + page[insert_at:]


def test_lookalikes_outside_2025_stay_in_place():
    page = _with_2024_lookalikes(materialize_review_markdown(PAGE.read_text(encoding="utf-8")))
    built = inject_f004_attach(page, data=load_attach())
    assert _LOOKALIKE_REASON in built
    assert _LOOKALIKE_ATTACH in built
    assert _LOOKALIKE_MENTION in built
    start, end = fss_f004_attach._year_span(built, "2025")
    assert built[start:end].count('class="fss-f004-attach"') == 151
    assert built.count('class="fss-f004-attach"') == 152


def test_strip_ignores_pages_without_2025_and_outside_lookalikes():
    lone = _LOOKALIKE_REASON + _LOOKALIKE_ATTACH + _LOOKALIKE_MENTION
    assert strip_f004_attach(lone) == lone
    page = _with_2024_lookalikes(materialize_review_markdown(PAGE.read_text(encoding="utf-8")))
    stripped = strip_f004_attach(page)
    assert _LOOKALIKE_REASON in stripped
    assert _LOOKALIKE_ATTACH in stripped
    assert _LOOKALIKE_MENTION in stripped
    assert strip_f004_attach(stripped) == stripped


def test_counts_mismatch_rejects_and_build_falls_back(tmp_path, monkeypatch, caplog):
    source = PAGE.read_text(encoding="utf-8")
    expected = materialize_review_markdown(source)
    for name, key in (("slots", "attach_slots"), ("lines", "firm_reason_lines")):
        data = _copy_attach()
        data["counts"][key] = data["counts"][key] + 1
        path = _dump_attach(tmp_path / name, data)
        with pytest.raises(ValueError):
            load_attach(path)
        monkeypatch.setattr(fss_f004_attach, "ATTACH_PATH", path)
        _same_2025_block(_hook(source, caplog), expected)
        caplog.clear()


def test_f004_row_shape_rejects_and_build_falls_back(tmp_path, monkeypatch, caplog):
    source = PAGE.read_text(encoding="utf-8")
    expected = materialize_review_markdown(source)
    row_id = next(iter(load_attach()["f004_rows"]))

    def set_rcept_list(data: dict) -> None:
        data["f004_rows"][row_id]["rcept_no"] = []

    def set_rcept_short(data: dict) -> None:
        data["f004_rows"][row_id]["rcept_no"] = "1234567890123"

    def set_url_mismatch(data: dict) -> None:
        data["f004_rows"][row_id]["dart_url"] = (
            "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=00000000000000"
        )

    def set_action_none(data: dict) -> None:
        data["f004_rows"][row_id]["action"] = None
        data["f004_rows"][row_id]["action_kind"] = "text"

    def set_date_number(data: dict) -> None:
        data["f004_rows"][row_id]["recommend_date_raw"] = 5

    def set_row_none(data: dict) -> None:
        data["f004_rows"][row_id] = None

    cases = (
        set_rcept_list,
        set_rcept_short,
        set_url_mismatch,
        set_action_none,
        set_date_number,
        set_row_none,
    )
    for index, mutate in enumerate(cases):
        data = _copy_attach()
        mutate(data)
        path = _dump_attach(tmp_path / str(index), data)
        with pytest.raises(ValueError):
            load_attach(path)
        monkeypatch.setattr(fss_f004_attach, "ATTACH_PATH", path)
        _same_2025_block(_hook(source, caplog), expected)
        caplog.clear()


def test_disclosure_shape_is_rejected(tmp_path):
    data = _copy_attach()
    target = next(reason for reason in data["firm_reasons"] if reason.get("disclosure"))
    saved = json.loads(json.dumps(target["disclosure"]))

    target["disclosure"] = "x"
    with pytest.raises(ValueError):
        load_attach(_dump_attach(tmp_path / "text", data))

    data = _copy_attach()
    target = next(reason for reason in data["firm_reasons"] if reason.get("disclosure"))
    target["disclosure"]["rcept_no"] = "123"
    with pytest.raises(ValueError):
        load_attach(_dump_attach(tmp_path / "short", data))

    data = _copy_attach()
    target = next(reason for reason in data["firm_reasons"] if reason.get("disclosure"))
    target["disclosure"] = saved
    target["disclosure"]["dart_url"] = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=00000000000000"
    with pytest.raises(ValueError):
        load_attach(_dump_attach(tmp_path / "url", data))


def test_duplicate_firm_reason_is_rejected(tmp_path):
    data = _copy_attach()
    data["firm_reasons"].append(json.loads(json.dumps(data["firm_reasons"][0])))
    data["counts"]["firm_reason_lines"] = len(data["firm_reasons"])
    with pytest.raises(ValueError):
        load_attach(_dump_attach(tmp_path, data))


def test_path_type_errors_are_value_errors(tmp_path):
    data = _copy_attach()
    data["attachments"][0]["path"]["section"] = []
    with pytest.raises(ValueError):
        load_attach(_dump_attach(tmp_path / "section", data))

    data = _copy_attach()
    data["attachments"][0]["path"]["firm"] = None
    with pytest.raises(ValueError):
        load_attach(_dump_attach(tmp_path / "firm", data))


def test_bad_note_type_says_format(tmp_path):
    data = _copy_attach()
    data["attachments"][0]["f004"][0]["note"] = 5
    with pytest.raises(ValueError, match="형식"):
        load_attach(_dump_attach(tmp_path, data))


def test_rendered_block_has_no_internal_ids():
    html = _injected()
    for token in _INTERNAL_IDS:
        assert token not in html


_OUTSIDE_PHRASE = "<p>원문: 지적사항 없음, 권고일 표기 불일치, 권고일 기재 없음</p>"
_INSIDE_PHRASE = "원문: 지적사항 없음, 권고일 표기 불일치, 권고일 기재 없음"


def test_phrase_counts_only_inside_f004_elements():
    html = _injected()
    finding = html.find('<p class="fss-finding">')
    assert finding >= 0
    outside = html[:finding] + _OUTSIDE_PHRASE + html[finding:]
    counts = check_mod._phrase_counts(outside)
    assert counts["no_finding"] == 0
    assert counts["mismatch"] == 0
    assert counts["no_date"] == 9
    action = '<p class="fss-f004-action">'
    at = html.find(action)
    assert at >= 0
    insert_at = at + len(action)
    inside = html[:insert_at] + _INSIDE_PHRASE + html[insert_at:]
    assert check_mod._phrase_counts(inside)["no_finding"] == 1


def test_search_index_report(tmp_path):
    clean = tmp_path / "clean" / "search_index.json"
    clean.parent.mkdir()
    clean.write_text(
        '{"docs":[{"location":"x","title":"t","text":"본문"}]}',
        encoding="utf-8",
    )
    report = check_mod._search_index_report(clean)
    assert report["ids"] == 0
    assert report["errors"] == []

    dirty = tmp_path / "dirty" / "search_index.json"
    dirty.parent.mkdir()
    dirty.write_text(
        '{"docs":[{"text":"date_mismatch qu_dongsung"}]}',
        encoding="utf-8",
    )
    report = check_mod._search_index_report(dirty)
    assert report["ids"] == 2
    assert report["errors"]

    mismatch = tmp_path / "mismatch" / "search_index.json"
    mismatch.parent.mkdir()
    mismatch.write_text(
        '{"docs":[{"text":"권고일 표기 불일치"}]}',
        encoding="utf-8",
    )
    report = check_mod._search_index_report(mismatch)
    assert report["mismatch"] == 1
    assert report["errors"]

    missing = check_mod._search_index_report(tmp_path / "missing" / "search_index.json")
    assert "search_index.json이 없습니다." in missing["errors"]
    assert check_mod._internal_hits("<p>pending f004_row_id</p>") == 2


def test_consistent_new_counts_still_attach(tmp_path, monkeypatch, caplog):
    data = _copy_attach()
    removed = data["attachments"].pop()
    assert data["firm_reasons"].pop()["firm"] == "효림회계법인"
    data["counts"]["attach_slots"] = 142
    data["counts"]["firm_reason_lines"] = 40
    data["counts"]["attach_blocks"] = 151 - len(removed["f004"])
    data["counts"]["firm_reason_panels"] = 40
    path = _dump_attach(tmp_path, data)
    assert len(load_attach(path)["attachments"]) == 142
    source = PAGE.read_text(encoding="utf-8")
    plain = materialize_review_markdown(source)
    monkeypatch.setattr(fss_f004_attach, "ATTACH_PATH", path)
    built = _hook(source, caplog)
    assert built != plain
    year = _year_slice(built, "2025")
    assert year.count('class="fss-f004-attach"') == 151 - len(removed["f004"])
    # 빠진 사유 법인(효림회계법인) 패널 4개만큼 사유 줄이 준다: 136 - 4 = 132칸.
    assert year.count(_REASON) == 132
    assert "위와 같음" not in built
    assert "자리 142/142" in caplog.text
    assert "법인 사유 40곳(132칸)" in caplog.text
    assert "건너뜀 0" in caplog.text


def _firm_group_panel(html: str, firm: str, group_prefix: str) -> str:
    found = []
    for panel in fss_f004_attach._iter_panels(html):
        name = fss_f004_attach._ORIGINAL_NAME.search(panel["html"])
        assert name
        if html_lib.unescape(name.group(1)) != firm:
            continue
        if panel["group"].startswith(group_prefix):
            found.append(panel["html"])
    assert len(found) == 1
    return found[0]


def test_each_firm_reason_is_full_and_identical_on_every_panel():
    data = load_attach()
    html = _injected()
    assert html.count(_REASON) == 136
    assert "위와 같음" not in html
    total = 0
    for reason in data["firm_reasons"]:
        panels = _panels_named(html, reason["firm"])
        assert panels
        total += len(panels)
        first = re.search(r'<p class="fss-f004-reason">.*?</p>', panels[0])
        assert first
        assert reason["text"] in first.group(0)
        for panel in panels:
            assert panel.count(_REASON) == 1
            assert first.group(0) in panel
            assert panel.endswith("</p></div>")
    assert total == 136


def test_check_compares_reason_lines_with_the_data():
    data = load_attach()
    html = _injected()
    assert check_mod._reason_content(html, data["firm_reasons"]) == (41, 0)
    taesung = next(r for r in data["firm_reasons"] if r["firm"] == "태성회계법인")
    rcept = taesung["disclosure"]["rcept_no"]
    wrong_text = html.replace(f">{rcept}</a>", ">20990101000000</a>")
    assert wrong_text.count(">20990101000000</a>") == 9
    assert check_mod._reason_content(wrong_text, data["firm_reasons"]) == (41, 1)
    url = taesung["disclosure"]["dart_url"]
    wrong_link = html.replace(f'href="{url}"', 'href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=0"')
    assert check_mod._reason_content(wrong_link, data["firm_reasons"]) == (41, 1)
    extra = dict(taesung, firm="없는회계법인")
    assert check_mod._reason_content(html, data["firm_reasons"] + [extra]) == (41, 0)


def test_dongsung_11_and_52_follow_the_confirmed_rows():
    data = load_attach()
    html = _injected()
    panel = _firm_group_panel(html, "동성회계법인", "1.1")
    findings = list(re.finditer(r'<p class="fss-finding">.*?</p>', panel))
    assert len(findings) == 6
    assert panel.count('class="fss-f004-attach"') == 2
    assert panel.startswith('<div class="fss-f004-attach"', findings[3].end())
    assert "위 4개 문단을 F004 한 행으로 공시" in panel[findings[3].end() : findings[4].start()]
    assert panel.startswith('<div class="fss-f004-attach"', findings[5].end())
    assert "위 2개 문단을 F004 한 행으로 공시" in panel[findings[5].end() :]
    assert panel.count("권고일 2026년 05월 13일") == 2
    assert panel.count(">20260929000399</a>") == 2
    later = _firm_group_panel(html, "동성회계법인", "5.2")
    later_findings = list(re.finditer(r'<p class="fss-finding">.*?</p>', later))
    assert len(later_findings) == 1
    row_ids = ("20260929000399:0:10", "20260929000399:0:11")
    blocks = []
    for row_id in row_ids:
        row = data["f004_rows"][row_id]
        assert row["action_kind"] == "none"
        blocks.append(
            '<div class="fss-f004-attach"><p class="fss-f004-head">F004 개선권고 이행사항'
            f' · 권고일 {row["recommend_date_raw"]} · '
            f'<a href="{row["dart_url"]}" rel="noopener" target="_blank">{row["rcept_no"]}</a></p>'
            '<p class="fss-f004-action">이행사항 기재 없음</p></div>'
        )
    assert later.startswith("".join(blocks), later_findings[0].end())


def test_seonil_54_last_paragraph_has_the_shared_note():
    html = _injected()
    panel = _firm_group_panel(html, "선일회계법인", "5.4")
    findings = list(re.finditer(r'<p class="fss-finding">.*?</p>', panel))
    assert len(findings) == 5
    assert panel.count('class="fss-f004-attach"') == 1
    for finding in findings[:-1]:
        assert not panel.startswith('<div class="fss-f004-attach"', finding.end())
    assert panel.startswith('<div class="fss-f004-attach"', findings[-1].end())
    assert "위 5개 문단을 F004 한 행으로 공시" in panel
    assert "20261006000135" in panel


def test_gonggam_41_and_sangnok_53_keep_row_order():
    data = load_attach()
    html = _injected()
    gonggam = _firm_group_panel(html, "회계법인 공감", "4.1")
    gonggam_actions = [
        data["f004_rows"][row_id]["action"]
        for row_id in ("20260630000442:0:9", "20260630000442:0:10")
    ]
    assert gonggam.find(gonggam_actions[0]) < gonggam.find(gonggam_actions[1])
    assert gonggam.count('class="fss-f004-attach"') == 2
    sangnok = _firm_group_panel(html, "상록회계법인", "5.3")
    assert sangnok.count('class="fss-f004-attach"') == 2
    assert sangnok.count("권고일 기재 없음") == 2
    assert sangnok.count("이행사항 기재 없음") == 2
    sangnok_actions = [
        data["f004_rows"][row_id]["action"]
        for row_id in ("20260630001078:0:1", "20260630001078:0:4")
    ]
    assert sangnok.find("이행사항 기재 없음") < sangnok.rfind("이행사항 기재 없음")
    assert sangnok_actions == ["기재 없음", "기재 없음"]


def test_short_action_marks_stay_verbatim():
    html = _injected()
    assert html.count('<p class="fss-f004-action">(*)</p>') == 9
    assert html.count('<p class="fss-f004-action">상동</p>') == 3
    assert html.count('<p class="fss-f004-action">3</p>') == 2
    assert html.count('<p class="fss-f004-action">1</p>') == 1


def test_block_count_mismatch_rejects_and_build_falls_back(tmp_path, monkeypatch, caplog):
    source = PAGE.read_text(encoding="utf-8")
    expected = materialize_review_markdown(source)
    for name, key in (("blocks", "attach_blocks"), ("panels", "firm_reason_panels")):
        data = _copy_attach()
        data["counts"][key] = data["counts"][key] + 1
        path = _dump_attach(tmp_path / name, data)
        with pytest.raises(ValueError):
            load_attach(path)
        monkeypatch.setattr(fss_f004_attach, "ATTACH_PATH", path)
        _same_2025_block(_hook(source, caplog), expected)
        caplog.clear()


def test_malformed_attachment_raises_value_error_before_block_sum(tmp_path, monkeypatch, caplog):
    source = PAGE.read_text(encoding="utf-8")
    expected = materialize_review_markdown(source)
    missing = _copy_attach()
    del missing["attachments"][0]["f004"]
    missing_path = _dump_attach(tmp_path / "missing", missing)
    with pytest.raises(ValueError):
        load_attach(missing_path)
    text = _copy_attach()
    text["attachments"][0] = "x"
    with pytest.raises(ValueError):
        load_attach(_dump_attach(tmp_path / "text", text))
    null_rows = _copy_attach()
    null_rows["attachments"][0]["f004"] = None
    with pytest.raises(ValueError):
        load_attach(_dump_attach(tmp_path / "null", null_rows))
    null_item = _copy_attach()
    null_item["attachments"][0] = None
    with pytest.raises(ValueError):
        load_attach(_dump_attach(tmp_path / "item", null_item))
    monkeypatch.setattr(fss_f004_attach, "ATTACH_PATH", missing_path)
    _same_2025_block(_hook(source, caplog), expected)
    assert "ValueError" in caplog.text


_ATTACH_2021_SHA = "04423aac698c95a7b246ec3c23d9e3d2f9bc14c0a9a43c57b3ef34bab357568e"
_ATTACH_2021_BYTES = 291537
_RENDER_2021_SHA = "ae6c6f4eb2433ab8e5fd898f82aa693b9e44726641303ec0d59338a7892ec1d7"
_RENDER_2021_BYTES = 164196
_SUMMARY_2021 = "F004 부착 2021: 자리 180/180, 이행사항 180, 법인 사유 0곳(0칸), 건너뜀 0"


def _injected_2021() -> str:
    return inject_f004_attach(render_year_html(load_year("2021")))


def test_2021_attach_file_matches_sha_and_manifest():
    path = fss_f004_attach.ATTACH_PATHS["2021"]
    raw = path.read_bytes()
    assert len(raw) == _ATTACH_2021_BYTES
    assert hashlib.sha256(raw).hexdigest() == _ATTACH_2021_SHA
    manifest = json.loads((path.parent / "f004-item-attach-2021.manifest.json").read_text(encoding="utf-8"))
    assert manifest == {
        "file": "f004-item-attach-2021.json",
        "sha256": _ATTACH_2021_SHA,
        "bytes": _ATTACH_2021_BYTES,
    }


def test_load_2021_attach_counts():
    data = load_attach(fss_f004_attach.ATTACH_PATHS["2021"])
    counts = data["counts"]
    assert counts["attach_slots"] == 180
    assert counts["attach_blocks"] == 180
    assert counts["attached_f004_rows"] == 180
    assert counts["unattached_f004_rows"] == 0
    assert len(data["firm_reasons"]) == 0
    assert counts["firm_reason_lines"] == 0
    assert counts["firm_reason_panels"] == 0


def test_2021_every_slot_resolves(caplog):
    with caplog.at_level(logging.INFO, logger="mkdocs.plugins.fss_f004_attach"):
        built = _injected_2021()
    assert _SUMMARY_2021 in caplog.text
    assert built.count('class="fss-f004-attach"') == 180
    assert built.count(_REASON) == 0
    assert "건너뜀 0" in caplog.text


def test_rendered_2021_block_matches_the_locked_bytes():
    raw = _injected_2021().encode("utf-8")
    assert len(raw) == _RENDER_2021_BYTES
    assert hashlib.sha256(raw).hexdigest() == _RENDER_2021_SHA


def test_strip_restores_materialized_page_after_both_years():
    page = materialize_review_markdown(PAGE.read_text(encoding="utf-8"))
    built = inject_f004_attach(page)
    assert strip_f004_attach(built) == page
    assert _year_slice(built, "2025").count('class="fss-f004-attach"') == 151
    assert _year_slice(built, "2021").count('class="fss-f004-attach"') == 180


def test_hanul_41_second_paragraph_has_one_shared_block():
    panel = _firm_group_panel(_injected_2021(), "한울회계법인", "4.1")
    findings = list(re.finditer(r'<p class="fss-finding">.*?</p>', panel))
    assert len(findings) >= 2
    assert not panel.startswith('<div class="fss-f004-attach"', findings[0].end())
    assert panel.startswith('<div class="fss-f004-attach"', findings[1].end())
    block = panel[findings[1].end() : panel.find("</div>", findings[1].end())]
    assert block.count('class="fss-f004-attach"') == 1
    assert "(위 2개 문단을 F004 한 행으로 공시)" in block


def test_gwanggyo_keeps_the_same_as_above_action_verbatim():
    html = _injected_2021()
    action = '<p class="fss-f004-action">상동</p>'
    assert html.count(action) == 1
    at = html.find(action)
    assert "20250627000684" in html[at - 500 : at]


# M2(사용자 결정 2026-11-16 9:18 PM CT)로 2021 데이터에서 뺀 정인회계법인 품질관리기준 인용 27문단.
# 값은 PR-C 부착 JSON(b3271fe9…)의 unattached.qu_findings[].text_sha256(NFC 문단 텍스트 sha256).
_JEONGIN_REMOVED_TEXT_SHA = frozenset(
    {
        "0d0604cbf8866a11e0ecff8ebabb7e87b69895394d913dfcf03f70db33ad12f3",
        "1c22a73515e5381cccdb4c801df3cb3e4e5cf33140b3934cb70bc4b940d8dd25",
        "39f9ee7a8e279c527380be8718ef6ea041e8b96d6776c18712647f1547183d58",
        "3aa7a05b7c1377a50cda9e57049b2f7665c5f1e39245440e6960416c9e52f782",
        "43b4c6cc667a67a013aa48f9305a691bb0badad639d8590147ebd444c99b9bdc",
        "475846d6c0379b928085fcbbf1c12b4178e69f4f464022da041163d434989739",
        "48b6c8a16123f911b48a1cacb5ca59588cf86fb17aa335f01926082be416a513",
        "4947b59c0ec56f208f9ef85466926f15bad6b8d0695f8111352f7ec11ab208e0",
        "4dbdbc8eeac1ab6ac3ce513d3d673f1d1a295cbb28eef54e43b433e853cc66f7",
        "54f81408c9eece7110ba39cb38217da1ae7c91c3e90d6c02ebe463407f88242b",
        "578513b1971d725f4f57f014a0c9cd8a5fdc627e69f5c8b84352a8fb8ffc3f53",
        "6e4229ccad3278e6f278f3579a3774eb84db418a1adf50b378fda3c33e94f8c6",
        "7523c1fe8940781e77a913f648b57ec5315e54e4fa1e06ec963e148bcc1af6e7",
        "80504de78e4daad3f80635e12efdbd70d5f675c06d42a4e14cba280d54a30940",
        "8ab9dbebf78b8142d01ee4a7c0da57e4c053138b483ddabf3a01869f49ac6497",
        "8ec72a8f46d34e573c6707c67b5249b177809bff1f8e64fabe94b3dcea87e2c8",
        "939c619c732fe6d703668c6a10ea64c30d10b07319f681e3472ef1da30ae708d",
        "97be3f5a05e8369bad1e1595493a07b0a5cbc8de38c5868070a96d05afcafdba",
        "990beb3fa43024c4f3ca75537bcef8223302fb5ecf275c34a4d68c980577e537",
        "994799d2547664d7d10798b66b5a40a407fecd58755fd6eda528eda3f16936cc",
        "a353418034ff5f1afdea1680ecfb6cedf9c3f30bbc8640e4829180efe5eb6b2c",
        "a668e609463e0904237b736275aa01aee09883b9f78b43f9c77d90bad83f03a4",
        "b2dfdecdcf792adbd9b4bfcd19fd755c26ea07a5f5fbb83a097b11590f90aa30",
        "bb2afafffaa2b14af67a530f86c73236a5624162c4fd777d4fe6e1547487eca5",
        "c3c488264ed48eb613933114c5a7b9489effc0b49151d95cd3122acdb2348146",
        "cc3c95bb37bdc1797a5f7a7443707214632d40f9c17ded136fe7527e565cb2e2",
        "eb8b95f4b29e9146f7b59d8c82d5c0a4a45c382367de11f3d17b88cd58d05fbf",
    }
)
# 남는 정인 지적 16문단(중분류별 문단 수). 모두 F004 이행사항이 바로 아래에 붙는다.
_JEONGIN_KEPT = {"1.2": 2, "2.2": 2, "3.1": 2, "4.3": 3, "5.2": 4, "6.1": 3}


def test_jeongin_quote_paragraphs_are_removed_from_2021():
    data = load_attach(fss_f004_attach.ATTACH_PATHS["2021"])
    assert data["unattached"]["qu_findings"] == []
    counts = data["counts"]
    assert counts["unattached_qu_findings"] == 0
    assert counts["unattached_by_reason"] == {}
    assert counts["qu_findings"] == counts["qu_findings_with_attach"] == 181
    assert counts["qu_panels"] == 79
    assert len(_JEONGIN_REMOVED_TEXT_SHA) == 27

    year = load_year("2021")
    for section in year["bundles"][0]["sections"]:
        for group in section["groups"]:
            if group["heading"].startswith("1.1 "):
                assert group["blocks"] == [
                    {"kind": "empty", "gun": gun} for gun in ("가군", "나군", "다군", "라군")
                ]

    html = _injected_2021()
    kept = {}
    for panel in fss_f004_attach._iter_panels(html):
        name = fss_f004_attach._ORIGINAL_NAME.search(panel["html"])
        assert name
        firm = html_lib.unescape(name.group(1))
        group_no = panel["group"].split(" ", 1)[0]
        for match in re.finditer(r'<p class="fss-finding">(.*?)</p>', panel["html"]):
            assert fss_f004_attach._finding_sha(match.group(1)) not in _JEONGIN_REMOVED_TEXT_SHA
            if firm == "정인회계법인":
                kept[group_no] = kept.get(group_no, 0) + 1
                assert panel["html"].startswith('<div class="fss-f004-attach"', match.end())
    assert kept == _JEONGIN_KEPT
    for token in ("(참고2)", "(참고3)", "□"):
        assert token not in html


def test_broken_2021_file_leaves_that_year_plain(tmp_path, monkeypatch, caplog):
    source = PAGE.read_text(encoding="utf-8")
    plain = materialize_review_markdown(source)
    payload = b"{"
    broken = tmp_path / "f004-item-attach-2021.json"
    broken.write_bytes(payload)
    (tmp_path / "f004-item-attach-2021.manifest.json").write_text(
        json.dumps(
            {
                "file": "f004-item-attach-2021.json",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setitem(fss_f004_attach.ATTACH_PATHS, "2021", broken)
    built = _hook(source, caplog)
    assert _year_slice(built, "2021") == _year_slice(plain, "2021")
    assert _year_slice(built, "2025").count('class="fss-f004-attach"') == 151
    assert "F004 부착을 하지 않습니다" in caplog.text


def test_broken_2025_file_keeps_2021_blocks(tmp_path, monkeypatch, caplog):
    source = PAGE.read_text(encoding="utf-8")
    plain = materialize_review_markdown(source)
    monkeypatch.setattr(fss_f004_attach, "ATTACH_PATH", tmp_path / "missing-2025.json")
    built = _hook(source, caplog)
    assert _year_slice(built, "2025") == _year_slice(plain, "2025")
    assert _year_slice(built, "2021").count('class="fss-f004-attach"') == 180


def test_2021_block_hides_internal_ids_and_the_banned_word():
    html = _injected_2021()
    assert _banned() not in html
    for token in _INTERNAL_IDS + ("history_row_ids",):
        assert token not in html


def test_attach_years_match_the_check_table():
    assert set(fss_f004_attach.ATTACH_PATHS) == set(check_mod.ATTACH_YEARS)


def test_on_screen_count_is_an_int_and_not_tied_to_firm_count(tmp_path):
    data = _copy_attach()
    data["counts"]["firm_reason_panels_on_screen"] = "0"
    with pytest.raises(ValueError):
        load_attach(_dump_attach(tmp_path / "text", data))
    data = _copy_attach()
    data["counts"]["firm_reason_panels_on_screen"] = 0
    loaded = load_attach(_dump_attach(tmp_path / "zero", data))
    assert loaded["counts"]["firm_reason_panels_on_screen"] == 0
    assert loaded["counts"]["firm_reason_panels"] == len(loaded["firm_reasons"])


def test_year_finding_ids_must_start_with_that_year(tmp_path):
    data = json.loads(json.dumps(load_attach(fss_f004_attach.ATTACH_PATHS["2021"])))
    data["attachments"][0]["finding_id"] = "2025/등록/1.2/가군/삼일회계법인/0"
    with pytest.raises(ValueError, match="finding_id"):
        load_attach(_dump_attach(tmp_path, data))


# PR-D: 2019·2020·2022·2023·2024 F004 부착 잠금. 연도마다 커밋 하나로 한 칸씩 더한다.
# 연도: (부착 JSON sha256, bytes, 부착 뒤 연도 블록 sha256, bytes, 빌드 로그 줄)
_ATTACH_YEAR_LOCK = {
    "2023": (
        "0d9e6bb5a9e98c6ee0270dd59178f25d82ba30cd8a714cc17892b05f7fac254b",
        420495,
        "4dcc58e5454747e4a5656c8719a95d4dfa674bab1f536c2c6e86ba1fe58f6317",
        359218,
        "F004 부착 2023: 자리 216/216, 이행사항 226, 법인 사유 35곳(81칸), 건너뜀 0",
    ),
    "2022": (
        "be4346280732b70de2a9dc6accd64a66bd5022a0dd609c7da36b000b4e224978",
        425305,
        "41569935b6fed1565fdd6d72be992b4d73458dcf54056be85c1e4680a2823046",
        393312,
        "F004 부착 2022: 자리 221/221, 이행사항 224, 법인 사유 35곳(107칸), 건너뜀 0",
    ),
    "2020": (
        "32b5a4f91e684e2a24eba1d5cf63a6935de4bcc315ac8ec072ff036715838688",
        207382,
        "2b2eca6a299523e0caef51f0c798f9a42264ac4d14c5128871d1da9cb5319d5b",
        114206,
        "F004 부착 2020: 자리 110/110, 이행사항 119, 법인 사유 0곳(0칸), 건너뜀 0",
    ),
    "2019": (
        "36493a0b48433b5cf3fcc39416f9d0c3112c512c535c7f375754912270043b62",
        128666,
        "be6d53fd6f04f28617b18311268ccd6834c0932fe403b23f7c67b8ca6a3055b7",
        75280,
        "F004 부착 2019: 자리 71/71, 이행사항 73, 법인 사유 0곳(0칸), 건너뜀 0",
    ),
}


def _injected_year(year: str) -> str:
    return inject_f004_attach(render_year_html(load_year(year)))


@pytest.mark.parametrize("year", list(_ATTACH_YEAR_LOCK))
def test_year_attach_file_matches_sha_manifest_and_serialization(year):
    attach_sha, attach_bytes, _render_sha, _render_bytes, _summary = _ATTACH_YEAR_LOCK[year]
    path = fss_f004_attach.ATTACH_PATHS[year]
    assert path.name == f"f004-item-attach-{year}.json"
    raw = path.read_bytes()
    assert len(raw) == attach_bytes
    assert hashlib.sha256(raw).hexdigest() == attach_sha
    assert raw.decode("utf-8") == json.dumps(json.loads(raw), ensure_ascii=False, indent=1)
    manifest = json.loads(path.with_name(f"f004-item-attach-{year}.manifest.json").read_text(encoding="utf-8"))
    assert manifest == {"file": path.name, "sha256": attach_sha, "bytes": attach_bytes}


@pytest.mark.parametrize("year", list(_ATTACH_YEAR_LOCK))
def test_year_every_slot_resolves_and_matches_locked_bytes(year, caplog):
    _attach_sha, _attach_bytes, render_sha, render_bytes, summary = _ATTACH_YEAR_LOCK[year]
    counts = load_attach(fss_f004_attach.ATTACH_PATHS[year])["counts"]
    with caplog.at_level(logging.INFO, logger="mkdocs.plugins.fss_f004_attach"):
        built = _injected_year(year)
    assert summary in caplog.text
    assert built.count('class="fss-f004-attach"') == counts["attach_blocks"]
    assert built.count(_REASON) == counts["firm_reason_panels_on_screen"]
    raw = built.encode("utf-8")
    assert len(raw) == render_bytes
    assert hashlib.sha256(raw).hexdigest() == render_sha
    assert _banned() not in built
    for token in _INTERNAL_IDS + ("history_row_ids",):
        assert token not in built


# N11(사용자 결정 2026-11-16 9:48 PM CT, 「N11 4개 모두 붙이지 마」): 2023 네 문단은 붙이지 않는다.
_N11_2023 = (
    "2023/등록/1.1/라군/정동회계법인/0",
    "2023/등록/1.1/라군/정동회계법인/2",
    "2023/등록/1.2/나군/삼덕회계법인/4",
    "2023/등록/2.1/나군/삼덕회계법인/3",
)


def test_2023_n11_paragraphs_stay_unattached():
    data = load_attach(fss_f004_attach.ATTACH_PATHS["2023"])
    held = [
        row["finding_id"]
        for row in data["unattached"]["qu_findings"]
        if row["reason"] == "user_decision_no_attach"
    ]
    assert held == list(_N11_2023)
    assert data["counts"]["unattached_by_reason"]["user_decision_no_attach"] == 4
    assert "review_pending" not in data["counts"]["unattached_by_reason"]
    used = {att["finding_id"] for att in data["attachments"]}
    used |= {fid for att in data["attachments"] for item in att["f004"] for fid in item.get("covers", [])}
    assert not used & set(_N11_2023)
