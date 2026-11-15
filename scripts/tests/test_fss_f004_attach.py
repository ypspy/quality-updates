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

import fss_f004_attach  # noqa: E402

# sha256sum data/fss-review/f004-item-attach.json
ATTACH_SHA = "e575e0c126487c42e635944cd6a6c05ed7ff4dcf13eeeb6dd70fbde75b0a49dc"
ATTACH_BYTES = 240048
# render_year_2025_html(load_year_2025())에 부착한 2025 블록.
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
_SUMMARY = "F004 부착: 자리 124/124, 이행사항 128, 법인 사유 41곳(136칸), 건너뜀 0"


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
    assert len(data["attachments"]) == 124
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
    assert items == 128
    assert no_date == 7
    assert no_action == 2
    assert notes == 28
    counts = data["counts"]
    assert counts["attach_slots"] == 124
    assert counts["firm_reason_lines"] == 41
    assert counts["pending_review31"] == 20
    assert counts["pending_dongsung"] == 14
    assert counts["pending_f004_rows"] == 22


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
    assert built.count('class="fss-f004-attach"') == 128
    assert built.count('class="fss-f004-reason"') == 136
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
    assert "자리 123/124" in caplog.text
    assert "건너뜀 1" in caplog.text
    assert built.count('class="fss-f004-attach"') == 127
    at = built.find(marker + "추가")
    end = built.find("</p>", at)
    assert not built.startswith('<div class="fss-f004-attach"', end + len("</p>"))
    assert built.count('class="fss-f004-reason"') == 136


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
    for panel in daeju:
        assert panel.count('class="fss-f004-reason"') == 1
        assert "20260630000869" in panel
        assert 'href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260630000869"' in panel
    audit_firms = [reason["firm"] for reason in data["firm_reasons"] if reason["reason"] == "audit_team"]
    assert len(audit_firms) == 19
    seen = 0
    for firm in audit_firms:
        panels = _panels_named(html, firm)
        assert panels
        for panel in panels:
            seen += 1
            match = re.search(r'<p class="fss-f004-reason">.*?</p>', panel)
            assert match
            assert "<a " not in match.group(0)
    assert seen > 0


def test_dongsung_and_pending_paragraphs_have_no_f004():
    data = load_attach()
    html = _injected()
    dongsung = _panels_named(html, "동성회계법인")
    assert dongsung
    for panel in dongsung:
        assert "fss-f004-attach" not in panel
        assert "fss-f004-reason" not in panel
    pending = {}
    for key in ("qu_review31", "qu_dongsung"):
        for row in data["pending"][key]:
            _, bundle, group_no, gun, firm, index = row["finding_id"].split("/")
            ident = (bundle, group_no, None if gun == "-" else gun, firm, int(index))
            pending[ident] = row["text_sha256"]
    assert len(pending) == 34
    hits = 0
    for panel in fss_f004_attach._iter_panels(html):
        name = fss_f004_attach._ORIGINAL_NAME.search(panel["html"])
        assert name
        firm = html_lib.unescape(name.group(1))
        group_no = panel["group"].split(" ", 1)[0]
        for index, match in enumerate(re.finditer(r'<p class="fss-finding">(.*?)</p>', panel["html"])):
            ident = (panel["bundle"], group_no, panel["gun"], firm, index)
            if ident not in pending:
                continue
            hits += 1
            assert fss_f004_attach._finding_sha(match.group(1)) == pending[ident]
            assert not panel["html"].startswith('<div class="fss-f004-attach"', match.end())
    assert hits == 34


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
    assert built[start:end].count('class="fss-f004-attach"') == 128
    assert built.count('class="fss-f004-attach"') == 129


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
