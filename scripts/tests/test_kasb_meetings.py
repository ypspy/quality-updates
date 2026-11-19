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


def _block_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("socket")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "socket", blocked)


def _committee_row(seq: str, title: str) -> str:
    return (
        "<tr><td>2026-03-20</td><td>회계기준</td><td>회계기준위원회</td>"
        f"<td><a onclick=\"fn_Detail('{seq}');\">{title}</a></td><td>홀</td></tr>"
    )


def _patch_live(monkeypatch, fetch_list):
    monkeypatch.setattr(kasb_meetings, "make_session", lambda: object())
    monkeypatch.setattr(kasb_meetings, "http_fetch_list", fetch_list)
    monkeypatch.setattr(
        kasb_meetings,
        "http_fetch_view",
        lambda session, seq: _read(f"view/{seq}.html"),
    )
    monkeypatch.setattr(
        kasb_meetings,
        "http_fetch_meet",
        lambda session, seq: _read(f"meet/{seq}.html"),
    )
    monkeypatch.setattr(
        kasb_meetings,
        "http_fetch_file",
        lambda session, file_no, file_seq: b"fixture-bytes",
    )


def test_dry_run_missing_seq_exits_nonzero(capsys):
    code = kasb_meetings.main(["--dry-run", "--seq", "99999"])
    out = capsys.readouterr().out
    assert code == 1
    assert "seq=99999 missing=list" in out


def test_dry_run_reports_missing_seq_and_keeps_found_seq(capsys):
    code = kasb_meetings.main(["--dry-run", "--seq", "1105,99999"])
    out = capsys.readouterr().out
    assert code == 1
    assert "seq=1105" in out
    assert "seq=99999 missing=list" in out
    assert "status=saved" in out


def test_dry_run_limit_does_not_call_a_listed_seq_missing(capsys):
    code = kasb_meetings.main(["--dry-run", "--limit", "1", "--seq", "1105,1109"])
    out = capsys.readouterr().out
    assert code == 0
    assert "missing=" not in out
    assert "seq=1109" in out


def test_live_missing_seq_exits_nonzero_and_prints_notice(capsys, monkeypatch, tmp_path):
    _block_network(monkeypatch)
    calls = []

    def fetch_list(session, page, start, end):
        calls.append(page)
        if page == 1:
            return _read("list.html")
        return "<table><tbody></tbody></table>"

    _patch_live(monkeypatch, fetch_list)
    code = kasb_meetings.main(
        ["--live", "--seq", "1105,99999", "--dest", str(tmp_path)]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "seq=99999 missing=list" in out
    assert "failed=1" in out
    assert "saved=1" in out
    state = kasb_meetings.load_state(tmp_path / "_state.json")
    assert "1105" in state["done"]
    assert "99999" not in state["failed"]
    assert "99999" not in state["done"]
    assert calls == [1, 2]


def test_live_unscanned_seq_past_limit_is_missing(capsys, monkeypatch, tmp_path):
    _block_network(monkeypatch)
    calls = []
    page = (
        "<table><tbody>"
        + _committee_row("1109", "2026년 제3회 회계기준위원회")
        + "</tbody></table>"
    )

    def fetch_list(session, page_no, start, end):
        calls.append(page_no)
        if page_no != 1:
            raise AssertionError("next page")
        return page

    _patch_live(monkeypatch, fetch_list)
    code = kasb_meetings.main(
        ["--live", "--limit", "1", "--seq", "1109,1105", "--dest", str(tmp_path)]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "seq=1105 missing=limit" in out
    assert calls == [1]
    assert (tmp_path / "2026-회계기준위원회-3회" / "record.md").is_file()
    assert not (tmp_path / "2026-회계기준위원회-1회").exists()


def test_live_same_page_seq_beyond_limit_is_not_missing(capsys, monkeypatch, tmp_path):
    _block_network(monkeypatch)
    page = (
        "<table><tbody>"
        + _committee_row("1109", "2026년 제3회 회계기준위원회")
        + _committee_row("1105", "2026년 제1회 회계기준위원회")
        + "</tbody></table>"
    )

    def fetch_list(session, page_no, start, end):
        if page_no != 1:
            raise AssertionError("next page")
        return page

    _patch_live(monkeypatch, fetch_list)
    code = kasb_meetings.main(
        ["--live", "--limit", "1", "--seq", "1109,1105", "--dest", str(tmp_path)]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "missing=" not in out
    assert (tmp_path / "2026-회계기준위원회-3회" / "record.md").is_file()
    assert not (tmp_path / "2026-회계기준위원회-1회").exists()


def test_retry_failed_help_matches_new_and_failed_seqs(capsys):
    with pytest.raises(SystemExit) as caught:
        kasb_meetings.parse_args(["--help"])
    assert caught.value.code == 0
    out = capsys.readouterr().out
    assert "새 seq" in out
    assert "실패 seq만" not in out


def test_retry_failed_collects_new_seq_and_skips_done(tmp_path):
    rows = kasb_meetings.parse_list_page(_read("list.html"))
    fetch_view, fetch_meet, fetch_file = _fetchers()
    by_seq = {row.seq: row for row in rows}
    first = kasb_meetings.collect(
        tmp_path,
        [by_seq["1105"]],
        fetch_view=fetch_view,
        fetch_meet=fetch_meet,
        fetch_file=fetch_file,
    )
    assert first["counts"]["saved"] == 1

    def fail_view(seq: str) -> str:
        raise RuntimeError("temporary failure")

    failed = kasb_meetings.collect(
        tmp_path,
        [by_seq["1106"]],
        fetch_view=fail_view,
        fetch_meet=fetch_meet,
        fetch_file=fetch_file,
    )
    assert failed["counts"]["failed"] == 1
    retry = kasb_meetings.collect(
        tmp_path,
        rows,
        fetch_view=fetch_view,
        fetch_meet=fetch_meet,
        fetch_file=fetch_file,
        retry_failed=True,
    )
    assert retry["counts"]["skipped"] == 1
    assert retry["counts"]["saved"] == 1
    assert retry["counts"]["meta_only"] == 1
    assert retry["counts"]["failed"] == 0
    state = kasb_meetings.load_state(tmp_path / "_state.json")
    assert state["done"]["1105"]["status"] == "saved"
    assert state["done"]["1106"]["status"] == "saved"
    assert state["done"]["1109"]["status"] == "meta_only"


def test_docs_match_default_run_and_retry_scope():
    root = Path(kasb_meetings.__file__).resolve().parents[2]
    guide = (root / "docs/project/quarterly-operations-guide.md").read_text(encoding="utf-8")
    collector = (root / "docs/project/kasb-meetings-collector.md").read_text(encoding="utf-8")
    source = Path(kasb_meetings.__file__).read_text(encoding="utf-8")
    assert "기본 실행은 오프라인 `--dry-run`이다." not in guide
    assert "인자가 없으면 안내 후 끝난다" in guide
    assert "실패 seq만" not in collector
    assert "새 seq" in collector
    assert "partial" in collector
    docstring = source.split('"""', 2)[1]
    assert "인자가 없으면 안내 후 끝난다" in docstring
    assert "실패 seq만" not in source


class _Response:
    def __init__(self, status: int, text: str = "", content: bytes = b""):
        self.status_code = status
        self.text = text
        self.content = content
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_http_fetch_meet_blank_on_404_and_raises_otherwise():
    def session(status: int, text: str = ""):
        class Session:
            def get(self, url, params=None, timeout=None):
                assert url == kasb_meetings.MEET_URL
                return _Response(status, text)

        return Session()

    assert kasb_meetings.http_fetch_meet(session(404), "1105") == ""
    assert kasb_meetings.http_fetch_meet(session(200, "<p>meet</p>"), "1105") == "<p>meet</p>"
    with pytest.raises(RuntimeError, match="HTTP 500"):
        kasb_meetings.http_fetch_meet(session(500, "nope"), "1105")


def test_non_404_meet_error_keeps_agenda_as_partial(tmp_path):
    rows = [
        row
        for row in kasb_meetings.parse_list_page(_read("list.html"))
        if row.seq == "1105"
    ]
    meet_status = {"code": 500}
    downloads = {"n": 0}

    class Session:
        def get(self, url, params=None, timeout=None):
            if url == kasb_meetings.MEET_URL:
                return _Response(meet_status["code"], _read("meet/1105.html"))
            if url == kasb_meetings.VIEW_URL:
                return _Response(200, _read("view/1105.html"))
            raise AssertionError(url)

        def post(self, url, data=None, timeout=None):
            assert url == kasb_meetings.DOWNLOAD_URL
            downloads["n"] += 1
            return _Response(200, content=b"fixture-bytes")

    session = Session()

    def run(**kwargs):
        return kasb_meetings.collect(
            tmp_path,
            rows,
            fetch_view=lambda seq: kasb_meetings.http_fetch_view(session, seq),
            fetch_meet=lambda seq: kasb_meetings.http_fetch_meet(session, seq),
            fetch_file=lambda file_no, file_seq: kasb_meetings.http_fetch_file(
                session, file_no, file_seq
            ),
            **kwargs,
        )

    failed = run()
    folder = tmp_path / "2026-회계기준위원회-1회"
    record = folder / "record.md"
    assert failed["counts"]["failed"] == 1
    assert failed["counts"]["saved"] == 0
    assert record.is_file()
    meta = kasb_meetings.read_meta(record)
    assert meta["status"] == "partial"
    assert "HTTP 500" in meta["meet_error"]
    assert meta["decision_items"] == ["제1호 기업회계기준서 제1021호 개정 공개초안"]
    assert (folder / "agenda" / "의결1_예시안건.hwp").read_bytes() == b"fixture-bytes"
    assert list((folder / "results").iterdir()) == []
    state = kasb_meetings.load_state(tmp_path / "_state.json")
    assert state["failed"]["1105"]["status"] == "partial"
    assert state["failed"]["1105"]["folder"] == folder.name
    assert "1105" not in state["done"]
    saved_downloads = downloads["n"]

    skipped = run()
    assert skipped["counts"]["skipped"] == 1
    assert skipped["counts"]["failed"] == 0
    assert downloads["n"] == saved_downloads
    assert kasb_meetings.read_meta(record)["status"] == "partial"

    meet_status["code"] = 200
    recovered = run(retry_failed=True)
    assert recovered["counts"]["saved"] == 1
    assert recovered["counts"]["failed"] == 0
    assert (folder / "results" / "[별첨]_2025년_제13회_회계기준위원회_회의록.hwp").is_file()
    recovered_meta = kasb_meetings.read_meta(record)
    assert recovered_meta["status"] == "saved"
    assert "meet_error" not in recovered_meta
    state = kasb_meetings.load_state(tmp_path / "_state.json")
    assert state["done"]["1105"]["status"] == "saved"
    assert "1105" not in state["failed"]


def test_meet_404_still_saves_agenda(tmp_path):
    rows = [
        row
        for row in kasb_meetings.parse_list_page(_read("list.html"))
        if row.seq == "1105"
    ]

    class Session:
        def get(self, url, params=None, timeout=None):
            if url == kasb_meetings.MEET_URL:
                return _Response(404, "missing")
            if url == kasb_meetings.VIEW_URL:
                return _Response(200, _read("view/1105.html"))
            raise AssertionError(url)

        def post(self, url, data=None, timeout=None):
            return _Response(200, content=b"fixture-bytes")

    session = Session()
    result = kasb_meetings.collect(
        tmp_path,
        rows,
        fetch_view=lambda seq: kasb_meetings.http_fetch_view(session, seq),
        fetch_meet=lambda seq: kasb_meetings.http_fetch_meet(session, seq),
        fetch_file=lambda file_no, file_seq: kasb_meetings.http_fetch_file(
            session, file_no, file_seq
        ),
    )
    meta = kasb_meetings.read_meta(tmp_path / "2026-회계기준위원회-1회" / "record.md")
    assert result["counts"]["saved"] == 1
    assert result["counts"]["failed"] == 0
    assert meta["status"] == "saved"
    assert "meet_error" not in meta


def test_view_fetch_error_still_fails_the_whole_seq(tmp_path):
    rows = [
        row
        for row in kasb_meetings.parse_list_page(_read("list.html"))
        if row.seq == "1105"
    ]

    def fetch_view(seq: str) -> str:
        raise RuntimeError("view down")

    result = kasb_meetings.collect(
        tmp_path,
        rows,
        fetch_view=fetch_view,
        fetch_meet=lambda seq: _read(f"meet/{seq}.html"),
        fetch_file=lambda file_no, file_seq: b"fixture-bytes",
    )
    assert result["counts"]["failed"] == 1
    assert result["counts"]["saved"] == 0
    assert list(tmp_path.rglob("record.md")) == []
