# -*- coding: utf-8 -*-
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler import kasb_meetings

FIXTURES = kasb_meetings.default_fixture_dir()


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_fixtures_are_html_only():
    files = [path for path in FIXTURES.rglob("*") if path.is_file()]
    assert files
    assert {path.suffix for path in files} == {".html"}


def test_source_does_not_import_reply_or_schedule_modules():
    text = Path(kasb_meetings.__file__).read_text(encoding="utf-8")
    imports = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    joined = "\n".join(imports)
    assert "kasb_replies" not in joined
    assert "KASB" not in joined


def test_parse_list_page_keeps_only_accounting_committee():
    rows = kasb_meetings.parse_list_page(_read("list.html"))
    assert [row.seq for row in rows] == ["1109", "1106", "1105"]
    assert rows[0].round_no == 3
    assert rows[0].year == 2026
    assert rows[0].date == "2026-03-20"
    assert rows[1].date == "2026-02-13"
    assert rows[1].round_no == 2
    assert all(row.is_committee for row in rows)
    scheduled = kasb_meetings.parse_schedule_rows(_read("list.html"))
    categories = {row.category for row in scheduled}
    assert "지속가능성기준위원회" in categories
    assert "회계기준자문위원회" in categories
    assert "세미나" in categories


def test_parse_view_with_attachments_reads_agenda_and_files():
    page = kasb_meetings.parse_view_page(_read("view/1105.html"))
    assert page.date == "2026-01-16"
    assert page.category == "회계기준 > 회계기준위원회"
    assert page.decision_items == ["제1호 기업회계기준서 제1021호 개정 공개초안"]
    assert page.report_items == [
        "제1호 2025년 제13회 회계기준위원회 회의록(보고후공개)",
        "제2호 IASB 및 IFRS 동향보고",
    ]
    assert [(item.name, item.file_no, item.role) for item in page.attachments] == [
        ("의결1_예시안건.hwp", "-110501", "agenda"),
        ("보고2_동향보고.hwp", "-110502", "agenda"),
    ]


def test_parse_meet_with_attachments_marks_results():
    page = kasb_meetings.parse_meet_page(_read("meet/1105.html"))
    assert [item.role for item in page.attachments] == ["results", "results"]
    assert page.attachments[0].name.startswith("2026년_제1회")
    assert "회의록" in page.attachments[1].name


def test_parse_view_without_attachments_is_meta_ready():
    page = kasb_meetings.parse_view_page(_read("view/1109.html"))
    assert page.attachments == []
    assert page.decision_items == ["해당사항 없음"]
    assert len(page.report_items) == 2


def test_view_disclaimer_is_not_an_agenda_item():
    page = kasb_meetings.parse_view_page(_read("view/1106.html"))
    assert page.decision_items == ["제1호 기업회계기준서 제1021호 개정 공개초안"]
    assert page.report_items == ["제1호 2026년 제1회 회계기준위원회 회의록(보고후공개)"]
    joined = " ".join(page.decision_items + page.report_items)
    assert "해당자료는" not in joined


def test_richer_view_uses_secondary_only_when_primary_is_empty():
    empty = "<table><tr><th>일시</th><td>2026-01-16</td></tr></table>"
    filled = _read("view/1105.html")
    assert kasb_meetings.richer_view(filled, empty) == filled
    assert kasb_meetings.richer_view(empty, filled) == filled
    assert kasb_meetings.richer_view(empty, None) == empty


def test_other_committees_are_not_accounting_committee():
    assert kasb_meetings.is_accounting_committee("회계기준위원회")
    assert not kasb_meetings.is_accounting_committee("회계기준자문위원회")
    assert not kasb_meetings.is_accounting_committee("지속가능성기준위원회")
    assert not kasb_meetings.is_accounting_committee("세미나")


def _fetchers():
    def fetch_view(seq: str) -> str:
        return _read(f"view/{seq}.html")

    def fetch_meet(seq: str) -> str:
        return _read(f"meet/{seq}.html")

    def fetch_file(file_no: str, file_seq: str) -> bytes:
        return f"fixture-{file_no}-{file_seq}".encode("utf-8")

    return fetch_view, fetch_meet, fetch_file


def test_collect_writes_record_agenda_and_results_without_real_binaries(tmp_path):
    rows = kasb_meetings.parse_list_page(_read("list.html"))
    fetch_view, fetch_meet, fetch_file = _fetchers()
    result = kasb_meetings.collect(
        tmp_path,
        rows,
        fetch_view=fetch_view,
        fetch_meet=fetch_meet,
        fetch_file=fetch_file,
        limit=3,
    )
    assert result["counts"] == {
        "saved": 2,
        "meta_only": 1,
        "skipped": 0,
        "failed": 0,
        "planned": 0,
    }
    meta_dir = tmp_path / "2026-회계기준위원회-3회"
    saved_dir = tmp_path / "2026-회계기준위원회-1회"
    assert (meta_dir / "record.md").is_file()
    assert (meta_dir / "agenda").is_dir()
    assert (meta_dir / "results").is_dir()
    assert list((meta_dir / "agenda").iterdir()) == []
    assert list((meta_dir / "results").iterdir()) == []
    meta = kasb_meetings.read_meta(meta_dir / "record.md")
    assert meta["status"] == "meta_only"
    assert meta["seq"] == "1109"
    assert (saved_dir / "agenda" / "의결1_예시안건.hwp").read_bytes() == b"fixture--110501-1"
    assert (saved_dir / "results" / "[별첨]_2025년_제13회_회계기준위원회_회의록.hwp").is_file()
    record = (saved_dir / "record.md").read_text(encoding="utf-8")
    assert "status: saved" in record
    assert b"HWP Document" not in (saved_dir / "agenda" / "의결1_예시안건.hwp").read_bytes()
    state = kasb_meetings.load_state(tmp_path / "_state.json")
    assert state["done"]["1105"]["status"] == "saved"
    assert state["done"]["1109"]["status"] == "meta_only"
    assert state["failed"] == {}


def test_collect_is_idempotent_until_retry_failed(tmp_path):
    rows = kasb_meetings.parse_list_page(_read("list.html"))
    calls = {"file": 0}
    failed_once = {"1106": False}

    def fetch_view(seq: str) -> str:
        if seq == "1106" and not failed_once["1106"]:
            failed_once["1106"] = True
            raise RuntimeError("temporary failure")
        return _read(f"view/{seq}.html")

    def fetch_meet(seq: str) -> str:
        return _read(f"meet/{seq}.html")

    def fetch_file(file_no: str, file_seq: str) -> bytes:
        calls["file"] += 1
        return b"fixture-bytes"

    first = kasb_meetings.collect(
        tmp_path,
        rows,
        fetch_view=fetch_view,
        fetch_meet=fetch_meet,
        fetch_file=fetch_file,
    )
    assert first["counts"]["failed"] == 1
    assert first["counts"]["saved"] == 1
    assert first["counts"]["meta_only"] == 1
    file_calls = calls["file"]
    second = kasb_meetings.collect(
        tmp_path,
        rows,
        fetch_view=fetch_view,
        fetch_meet=fetch_meet,
        fetch_file=fetch_file,
    )
    assert second["counts"]["skipped"] == 3
    assert second["counts"]["saved"] == 0
    assert calls["file"] == file_calls
    third = kasb_meetings.collect(
        tmp_path,
        rows,
        fetch_view=fetch_view,
        fetch_meet=fetch_meet,
        fetch_file=fetch_file,
        retry_failed=True,
    )
    assert third["counts"]["saved"] == 1
    assert third["counts"]["failed"] == 0
    state = kasb_meetings.load_state(tmp_path / "_state.json")
    assert "1106" in state["done"]
    assert "1106" not in state["failed"]
    assert (tmp_path / "2026-회계기준위원회-2회" / "agenda" / "의결1_환율공개초안.hwp").is_file()


def test_collect_dry_run_does_not_write_or_download(tmp_path):
    rows = kasb_meetings.parse_list_page(_read("list.html"))

    def fetch_file(file_no: str, file_seq: str) -> bytes:
        raise AssertionError("download")

    result = kasb_meetings.collect(
        tmp_path,
        rows,
        fetch_view=lambda seq: _read(f"view/{seq}.html"),
        fetch_meet=lambda seq: _read(f"meet/{seq}.html"),
        fetch_file=fetch_file,
        dry_run=True,
        limit=2,
    )
    assert result["counts"]["planned"] == 2
    assert list(tmp_path.rglob("*")) == []
    assert [plan.seq for plan in result["plans"]] == ["1109", "1106"]


def test_gather_rows_stops_at_limit_and_skips_other_committees():
    pages = {
        1: "<table><tbody>"
        "<tr><td>2026-05-01</td><td>공통</td><td>세미나</td>"
        "<td><a onclick=\"fn_Detail('1');\">세미나</a></td><td>홀</td></tr>"
        "<tr><td>2026-04-01</td><td>회계기준</td><td>회계기준위원회</td>"
        "<td><a onclick=\"fn_Detail('1109');\">2026년 제3회 회계기준위원회</a></td><td>홀</td></tr>"
        "</tbody></table>",
        2: _read("list.html"),
    }
    calls = []

    def fetch_page(page: int) -> str:
        calls.append(page)
        if page > 2:
            raise AssertionError("next page")
        return pages[page]

    rows = kasb_meetings.gather_rows(fetch_page, limit=1, seqs=None)
    assert [row.seq for row in rows] == ["1109"]
    assert calls == [1]

    calls.clear()

    def fetch_all(page: int) -> str:
        calls.append(page)
        return pages.get(page, "<table><tbody></tbody></table>")

    rows = kasb_meetings.gather_rows(fetch_all, limit=None, seqs={"1105"})
    assert [row.seq for row in rows] == ["1105"]
    assert calls == [1, 2]


def test_duplicate_attachment_names_get_a_suffix():
    items = [
        kasb_meetings.Attachment("같은이름.hwp", "1", "1", "agenda"),
        kasb_meetings.Attachment("같은이름.hwp", "2", "2", "agenda"),
    ]
    named = kasb_meetings.assign_saved_names(items)
    assert [item.saved_name for item in named] == ["같은이름.hwp", "같은이름-2.hwp"]


def test_dry_run_cli_uses_fixtures_and_does_not_open_a_socket(capsys, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("socket")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "socket", blocked)
    code = kasb_meetings.main(["--dry-run", "--limit", "3"])
    captured = capsys.readouterr()
    assert code == 0
    assert "dry-run network=no meetings=3" in captured.out
    assert "seq=1109 folder=2026-회계기준위원회-3회 status=meta_only" in captured.out
    assert "seq=1106 folder=2026-회계기준위원회-2회 status=saved" in captured.out
    assert "seq=1105 folder=2026-회계기준위원회-1회 status=saved" in captured.out
    assert "attachments=0" in captured.out
    assert "seq=9001" not in captured.out
    assert "seq=9002" not in captured.out
    assert "지속가능성" not in captured.out


def test_default_and_bare_live_do_not_open_a_socket(capsys, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("socket")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "socket", blocked)
    assert kasb_meetings.main([]) == 2
    assert kasb_meetings.main(["--live"]) == 2
    assert kasb_meetings.main(["--live", "--dry-run", "--limit", "1"]) == 2
    err = capsys.readouterr().err
    assert "전량은 돌리지 않습니다" in err
    assert "함께 쓸 수 없습니다" in err


def test_cli_seq_filter(capsys):
    code = kasb_meetings.main(["--dry-run", "--seq", "1105"])
    out = capsys.readouterr().out
    assert code == 0
    assert "meetings=1" in out
    assert "seq=1105" in out
    assert "seq=1109" not in out


@pytest.mark.parametrize("bad", ["../evil.hwp", "a/b.hwp", "a\\b.hwp", "", ".."])
def test_safe_filename_strips_paths(bad):
    name = kasb_meetings.safe_filename(bad, "9")
    assert "/" not in name
    assert "\\" not in name
    assert name != ".."
