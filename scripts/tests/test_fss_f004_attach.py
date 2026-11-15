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
    load_year_2025,
    materialize_review_markdown,
    render_year_2025_html,
)
from mkdocs_fss_review_year import on_page_markdown  # noqa: E402
from tests.test_fss_review_cards import _Page  # noqa: E402

import check_f004_attach_render as check_mod  # noqa: E402
import fss_f004_attach  # noqa: E402

# sha256sum data/fss-review/f004-item-attach.json
ATTACH_SHA = "241b0edcd6eae831ef38a8d5a742be3f1bb09672cc1560fd93a54ddccc80e682"
ATTACH_BYTES = 246423
# render_year_2025_html(load_year_2025())에 부착한 2025 블록.
RENDERED = {
    "1c6df2500ba918054bd4b22b3a983af9ef3bdecdedc54908d4a54a04e1ea72e4": (
        313703,
        "ef266044ee0914a1f81aed7765d2b9771f2e05201e5cc0fd41574ed82850293e",
    ),
}
_SUMMARY = "F004 부착: 자리 143/143, 이행사항 151, 법인 사유 41곳(136칸), 건너뜀 0"
_SAME = 'class="fss-f004-reason fss-f004-same"'


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
    assert built.count('class="fss-f004-reason"') == 41
    assert built.count(_SAME) == 95
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
    assert built.count('class="fss-f004-reason"') == 41
    assert built.count(_SAME) == 95


def test_bad_file_keeps_the_materialized_page(tmp_path, monkeypatch, caplog):
    source = PAGE.read_text(encoding="utf-8")
    expected = materialize_review_markdown(source)
    monkeypatch.setattr(fss_f004_attach, "ATTACH_PATH", Path("/tmp/f004-item-attach-missing.json"))
    assert _hook(source, caplog) == expected
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
    assert _hook(source, caplog) == expected
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
    assert _hook(source, caplog) == expected
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
    for panel in daeju[1:]:
        assert 'class="fss-f004-reason"' not in panel
        assert panel.count(_SAME) == 1
        assert "F004 이행사항: 위와 같음 · " in panel
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
            assert 'class="fss-f004-reason"' not in panel
            same = re.search(r'<p class="fss-f004-reason fss-f004-same">.*?</p>', panel)
            assert same
            assert same.group(0) == '<p class="fss-f004-reason fss-f004-same">F004 이행사항: 위와 같음</p>'
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
    start, end = fss_f004_attach._year_span(built)
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
        assert _hook(source, caplog) == expected
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
        assert _hook(source, caplog) == expected
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
    data["firm_reasons"].pop()
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
    assert built.count('class="fss-f004-attach"') == 151 - len(removed["f004"])
    assert built.count('class="fss-f004-reason"') == 40
    assert "자리 142/142" in caplog.text
    assert "법인 사유 40곳(" in caplog.text
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


def test_each_firm_reason_is_full_on_the_first_panel_and_short_after():
    data = load_attach()
    html = _injected()
    assert html.count('class="fss-f004-reason"') == 41
    assert html.count(_SAME) == 95
    total = 0
    for reason in data["firm_reasons"]:
        panels = _panels_named(html, reason["firm"])
        assert panels
        total += len(panels)
        assert panels[0].count('class="fss-f004-reason"') == 1
        assert _SAME not in panels[0]
        assert reason["text"] in panels[0]
        for panel in panels[1:]:
            assert 'class="fss-f004-reason"' not in panel
            assert panel.count(_SAME) == 1
            assert panel.endswith("</p></div>")
    assert total == 136


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
        assert _hook(source, caplog) == expected
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
    assert _hook(source, caplog) == expected
    assert "ValueError" in caplog.text
