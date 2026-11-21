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
    monkeypatch.setattr(kasb_meetings, "make_session", lambda *args, **kwargs: object())
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


def test_delay_defaults_to_0_3_and_parses_float():
    assert kasb_meetings.DEFAULT_DELAY == 0.3
    assert kasb_meetings.parse_args(["--dry-run"]).delay == 0.3
    parsed = kasb_meetings.parse_args(["--live", "--limit", "1", "--delay", "0.5"])
    assert parsed.delay == 0.5
    assert kasb_meetings.parse_args(["--live", "--limit", "1", "--delay", "0"]).delay == 0.0


def test_negative_delay_exits_without_a_socket(monkeypatch, capsys):
    _block_network(monkeypatch)
    code = kasb_meetings.main(["--live", "--limit", "1", "--delay", "-0.1"])
    assert code == 2
    assert "0 이상" in capsys.readouterr().err


def test_dry_run_ignores_delay(monkeypatch, capsys):
    def boom(seconds):
        raise AssertionError(seconds)

    monkeypatch.setattr(kasb_meetings.time, "sleep", boom)
    code = kasb_meetings.main(["--dry-run", "--limit", "1", "--delay", "5"])
    assert code == 0
    assert "network=no" in capsys.readouterr().out


def test_live_cli_passes_delay_into_make_session(monkeypatch, tmp_path):
    seen = {}

    def make_session(delay=kasb_meetings.DEFAULT_DELAY, **kwargs):
        seen["delay"] = delay
        return object()

    def crawl_live(*args, **kwargs):
        return {"counts": {"saved": 0, "meta_only": 0, "skipped": 0, "failed": 0}, "errors": []}

    monkeypatch.setattr(kasb_meetings, "make_session", make_session)
    monkeypatch.setattr(kasb_meetings, "crawl_live", crawl_live)
    assert kasb_meetings.main(["--live", "--limit", "1", "--dest", str(tmp_path)]) == 0
    assert seen["delay"] == 0.3
    assert kasb_meetings.main(
        ["--live", "--seq", "1105", "--delay", "1.25", "--dest", str(tmp_path)]
    ) == 0
    assert seen["delay"] == 1.25


def test_make_session_sleeps_after_the_opening_get(monkeypatch):
    sleeps = []
    calls = []

    class RawSession:
        def __init__(self):
            self.headers = {}

        def get(self, url, **kwargs):
            calls.append(("get", url))
            return _Response(200, "ok")

        def post(self, url, **kwargs):
            calls.append(("post", url))
            return _Response(200, "<table><tbody></tbody></table>")

    class RequestsModule:
        Session = RawSession

    monkeypatch.setitem(sys.modules, "requests", RequestsModule)
    session = kasb_meetings.make_session(delay=0.3, sleep=sleeps.append)
    kasb_meetings.http_fetch_list(session, 1, "", "")
    assert calls[0] == ("get", kasb_meetings.LIST_URL)
    assert calls[1][0] == "post"
    assert sleeps == [0.3]


def test_paced_session_skips_sleep_when_delay_is_zero():
    slept = []

    class Raw:
        def get(self, url, **kwargs):
            return url

        def post(self, url, **kwargs):
            return url

    session = kasb_meetings.PacedSession(Raw(), 0, sleep=slept.append)
    session.get("https://example.test/a")
    session.post("https://example.test/b")
    assert slept == []


def test_view_fallback_sleeps_between_the_two_gets():
    calls = []
    sleeps = []

    class Raw:
        def get(self, url, params=None, timeout=None):
            calls.append(url)
            if url == kasb_meetings.VIEW_URL:
                return _Response(200, "<html></html>")
            if url == kasb_meetings.VIEW_B_URL:
                return _Response(200, _read("view/1105.html"))
            raise AssertionError(url)

    session = kasb_meetings.PacedSession(Raw(), 0.3, sleep=sleeps.append)
    html = kasb_meetings.http_fetch_view(session, "1105")
    assert calls == [kasb_meetings.VIEW_URL, kasb_meetings.VIEW_B_URL]
    assert sleeps == [0.3]
    assert "의결1_예시안건.hwp" in html


def test_live_http_sleeps_between_list_view_meet_and_files(tmp_path):
    sleeps = []
    calls = []

    class Raw:
        def post(self, url, data=None, timeout=None):
            calls.append(url)
            if url == kasb_meetings.LIST_URL:
                if (data or {}).get("page") == 1:
                    return _Response(200, _read("list.html"))
                return _Response(200, "<table><tbody></tbody></table>")
            if url == kasb_meetings.DOWNLOAD_URL:
                return _Response(200, content=b"bytes")
            raise AssertionError(url)

        def get(self, url, params=None, timeout=None):
            calls.append(url)
            if url == kasb_meetings.VIEW_URL:
                return _Response(200, _read("view/1105.html"))
            if url == kasb_meetings.MEET_URL:
                return _Response(200, _read("meet/1105.html"))
            raise AssertionError(url)

    session = kasb_meetings.PacedSession(Raw(), 0.3, sleep=sleeps.append)
    result = kasb_meetings.crawl_live(
        tmp_path,
        session,
        start="",
        end="",
        limit=1,
        seqs={"1105"},
        retry_failed=False,
    )
    assert result["counts"]["saved"] == 1
    assert calls == [
        kasb_meetings.LIST_URL,
        kasb_meetings.VIEW_URL,
        kasb_meetings.MEET_URL,
        kasb_meetings.DOWNLOAD_URL,
        kasb_meetings.DOWNLOAD_URL,
        kasb_meetings.DOWNLOAD_URL,
        kasb_meetings.DOWNLOAD_URL,
    ]
    assert sleeps == [0.3] * (len(calls) - 1)


def test_docs_record_the_live_delay_default():
    root = Path(kasb_meetings.__file__).resolve().parents[2]
    collector = (root / "docs/project/kasb-meetings-collector.md").read_text(encoding="utf-8")
    guide = (root / "docs/project/quarterly-operations-guide.md").read_text(encoding="utf-8")
    assert "--delay" in collector
    assert "0.3" in collector
    assert "적용하지 않는다" in collector
    checklist = collector.split("## 승인 전 실수집에서 정할 것", 1)[1]
    assert "요청 간격" not in checklist
    assert "--delay" in guide
    assert "0.3" in guide


def test_docs_keep_accounting_default_and_name_advisory_committee():
    root = Path(kasb_meetings.__file__).resolve().parents[2]
    collector = (root / "docs/project/kasb-meetings-collector.md").read_text(encoding="utf-8")
    assert "--committee" in collector
    assert "회계기준자문위원회" in collector
    assert "자문위원회와 지속가능성기준위원회는 넣지 않는다" not in collector
    assert "지속가능성기준위원회" in collector


def test_list_filter_follows_the_selected_committee():
    advisory = kasb_meetings.parse_list_page(
        _read("list.html"), committee="회계기준자문위원회"
    )
    advisory_seqs = [row.seq for row in advisory]
    assert advisory_seqs == ["9002", "1124", "1060", "847"]
    assert all(
        kasb_meetings.canonical_committee(row.category) == "회계기준자문위원회"
        for row in advisory
    )
    assert "1105" not in advisory_seqs
    default_rows = kasb_meetings.parse_list_page(_read("list.html"))
    explicit = kasb_meetings.parse_list_page(
        _read("list.html"), committee="회계기준위원회"
    )
    assert [row.seq for row in default_rows] == ["1109", "1106", "1105"]
    assert [row.seq for row in explicit] == ["1109", "1106", "1105"]
    spaced = kasb_meetings.parse_list_page(
        _read("list.html"), committee="회계기준 자문위원회"
    )
    assert [row.seq for row in spaced] == advisory_seqs


def test_advisory_round_uses_hoe_and_keeps_gi_as_term():
    title = "2017년 제9기 제4회 회계기준자문위원회"
    year, round_no = kasb_meetings.year_and_round(title, "2017-11-01")
    assert year == 2017
    assert round_no == 4
    assert kasb_meetings.term_from_title(title) == 9
    assert (
        kasb_meetings.folder_name(year, round_no, "회계기준자문위원회")
        == "2017-회계기준자문위원회-4회"
    )
    assert kasb_meetings.folder_name(2026, 1) == "2026-회계기준위원회-1회"
    assert kasb_meetings.folder_name(2020, 0, "회계기준자문위원회") == "2020-회계기준자문위원회-0회"
    assert kasb_meetings.term_from_title("2026년 제1회 회계기준위원회") is None
    with pytest.raises(ValueError, match="폴더"):
        kasb_meetings.folder_name(2020, 1, "회계기준 > 회계기준자문위원회")


def test_advisory_view_1124_maps_agenda_and_written_report():
    page = kasb_meetings.parse_view_page(_read("view/1124.html"))
    assert page.title == (
        "2026년 제1회 KK-IFRS 제1118호 등 개정 공개초안 "
        "‘재무제표에서의 불확실성 공시 – 사례’ 등"
    )
    assert "KK-IFRS" in page.title
    assert page.date == "2026-05-14"
    assert page.place == "한국회계기준원 BM Room"
    assert page.category == "회계기준 > 회계기준자문위원회"
    assert page.attachments == []
    assert page.decision_items == [
        "1) K-IFRS 제1118호 등 개정 공개초안 ‘재무제표에서의 불확실성 공시 – 사례’",
        "2) K-IFRS 제1016호 개정 공개초안 ‘토지 공시지가 주석공시’",
        "3) IASB 공개초안 위험경감회계(ED) 주요 내용 및 예비적 견해",
        "4) 무형자산 연구 ‘사업결합으로 취득한 무형자산의 정보유용성’",
    ]
    assert page.report_items == ["1) 지난 회의록 보고"]
    meet = kasb_meetings.parse_meet_page(_read("meet/1124.html"))
    assert meet.attachments == []


def test_advisory_view_1060_keeps_ho_items_and_closed_minutes():
    page = kasb_meetings.parse_view_page(_read("view/1060.html"))
    assert page.title == "2023년 제2회 회계기준 개정 주요 내용 등"
    assert page.decision_items == [
        "제1호: 회계기준 개정 주요 내용",
        "제2호: IASB의 손익계산서 표시와 공시 기준 개정안",
        "제3호: 재무제표의 기후관련 및 기타 불확실성",
        "제4호: 회계자문위원회 활성화 방안(안)",
    ]
    assert page.report_items == [
        "제1호: 2023년 제1회 회계자문위원회 회의록(비공개)",
        "제2호: 국제동향 보고",
        "제3호: K-IFRS 정규절차 질의회신",
    ]
    assert page.attachments == []


def test_advisory_view_847_reads_term_and_numbered_agenda():
    page = kasb_meetings.parse_view_page(_read("view/847.html"))
    assert page.title == "1999년 제1기 제1회 회계기준자문위원회"
    assert page.decision_items == ["1. KASB 중단기 Agendas"]
    assert page.report_items == []
    assert kasb_meetings.term_from_title(page.title) == 1
    year, round_no = kasb_meetings.year_and_round(page.title, page.date)
    assert (year, round_no) == (1999, 1)
    assert (
        kasb_meetings.folder_name(year, round_no, "회계기준자문위원회")
        == "1999-회계기준자문위원회-1회"
    )


def _base_parse_agenda_sections(text: str):
    """f0c4e5c2의 parse_agenda_sections. 회계기준위원회 경로는 이 결과와 같아야 한다."""
    import re

    section_re = re.compile(r"(의결\s*안건|보고\s*안건)")
    item_re = re.compile(r"제\s*\d+\s*호\s*\S.*")
    disclaimer_re = re.compile(r"(이 회의결과는 잠정적인 것으로.*|※\s*해당자료는.*)")
    cleaned = disclaimer_re.sub("", text or "").replace("\xa0", " ")
    decision: list[str] = []
    report: list[str] = []
    current = None
    for part in section_re.split(cleaned):
        compact = re.sub(r"\s+", "", part)
        if compact == "의결안건":
            current = decision
            continue
        if compact == "보고안건":
            current = report
            continue
        if current is None:
            continue
        for chunk in re.split(r"[\n\r]+|·|•", part):
            line = re.sub(r"\s+", " ", chunk.strip(" \t-:")).strip()
            if not line:
                continue
            if "해당사항 없음" in line and not item_re.search(line):
                if "해당사항 없음" not in current:
                    current.append("해당사항 없음")
                continue
            match = item_re.search(line)
            if match:
                item = re.sub(r"\s+", " ", match.group(0)).strip()
                if item not in current:
                    current.append(item)
    return decision, report


def _accounting_body_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one(".board_view_cont")
    body = node.get_text("\n", strip=True) if node else ""
    if body:
        return body
    for th in soup.find_all("th"):
        label = "".join(th.get_text(strip=True).split())
        if label != "내용":
            continue
        td = th.find_next("td")
        return td.get_text(" ", strip=True) if td else ""
    return ""


def test_accounting_fixtures_match_base_agenda_parser():
    for name in ("view/1105.html", "view/1106.html", "view/1109.html", "meet/1105.html"):
        html = _read(name)
        page = kasb_meetings.parse_view_page(html) if "/view/" in name else kasb_meetings.parse_meet_page(html)
        decision, report = _base_parse_agenda_sections(_accounting_body_text(html))
        assert page.decision_items == decision
        assert page.report_items == report


def test_accounting_view_1132_matches_base_parser():
    from bs4 import BeautifulSoup

    html = _read("view/1132.html")
    page = kasb_meetings.parse_view_page(html)
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".board_view_cont").get_text("\n", strip=True)
    decision, report = _base_parse_agenda_sections(body)
    assert page.title == ""
    assert page.category == "회계기준 > 회계기준위원회"
    assert page.decision_items == decision == [
        "제1119호 제정안 ‘공공에 대한 회계책임이 없는 종속기업: 공시’(K-IFRS 1119 ‘Subsidiaries without Public Accountability: Disclosures’)",
        "제1028호 개정안 ‘관계기업 및 공동기업에 대한 투자의 공정가치선택권 개정’(Amendments to K-IFRS 1028 ‘Amendments to the Fair Value Option for Investments in Associates and Joint Ventures’)",
    ]
    assert page.report_items == report == []
    assert len(page.decision_items) == 2


def test_advisory_view_1123_keeps_the_span_paragraph_and_colon():
    page = kasb_meetings.parse_view_page(_read("view/1123.html"))
    assert page.decision_items == [
        "제1호: 회계기준적용의견서(안) 25-1 '기업회계기준서 제1001호 문단 19에 따른 일탈 적용의 제한'",
        "제2호: K-IFRS 질의회신 - RPS 공급의무자의 REC 매입계약 회계처리",
        "제3호: K-IFRS 용어 정비",
    ]
    assert page.report_items == ["제1호: 2025년 제1회 회계자문위원회 회의록(비공개)"]
    assert "제1001호 문단" not in page.decision_items[0] or page.decision_items[0].startswith("제1호:")
    assert page.decision_items[0].startswith("제1호:")
    assert "제1001호" in page.decision_items[0]


def test_advisory_parenthesized_items_stay_whole_paragraphs():
    seq_666 = kasb_meetings.parse_view_page(_read("view/666.html"))
    assert seq_666.decision_items == [
        "안 건 : (1) 금융상품(예상손실, 분류측정, 위험회피 등) (2) 보험계약 "
        "(3) 요율규제활동 (4) 비영리조직 회계기준 (5) 재무회계개념체계 "
        "(6) 일반기업회계기준의 개정 필요성에 대한 의견"
    ]
    assert seq_666.report_items == []
    seq_145 = kasb_meetings.parse_view_page(_read("view/145.html"))
    assert seq_145.decision_items == [
        "(1) 기업회계기준서 제1호-제10호에 대한 의견 검토 및 토론",
        "(2) 중소기업회계특례(안) 및 최종 토론",
        "(3) 기업회계기준서 공개초안 제01-15호 '지분법' 수정(안)",
        "(4) 회계기준서 제정현황 및 향후계획",
        "(5) 국제적 회계현황",
        "(6) 회계기준적용의견서",
    ]
    assert seq_145.decision_items[0].startswith("(1)")
    assert "제1호-제10호" in seq_145.decision_items[0]


def test_advisory_middle_dot_stays_inside_the_paragraph():
    page = kasb_meetings.parse_view_page(_read("view/652.html"))
    assert "2. 2016년 회계기준 제정·개정 및 유지 업무" in page.decision_items
    assert "2. 2016년 회계기준 제정" not in page.decision_items
    assert page.title.startswith("2015년 제9기 제1회")


def test_advisory_appendix_is_not_a_decision_item(tmp_path):
    page = kasb_meetings.parse_view_page(_read("view/861.html"))
    assert page.decision_items == [
        "■ 안 건: 1) 질의회신 공개(안) 2) IASB 공개초안 '일반적 표시와 공시' "
        "3) IASB 토론서 ‘사업결합 - 공시, 영업권과 손상’ 4) 2020년도 교육계획(안) "
        "5) K-IFRS 제1116호 ‘리스’ 개정(안)"
    ]
    assert page.report_items == []
    assert page.appendix_items == [
        "■ 붙 임: 1) 2019년 제2회 회계기준자문위원회 회의록 2) 국제동향 보고"
    ]
    row = kasb_meetings.ScheduleRow(
        seq="861",
        date="2020-05-21",
        category="회계기준자문위원회",
        title=page.title,
        place=page.place,
        year=2020,
        round_no=1,
    )
    result = kasb_meetings.collect(
        tmp_path,
        [row],
        fetch_view=lambda seq: _read("view/861.html"),
        fetch_meet=lambda seq: "",
        fetch_file=lambda file_no, file_seq: (_ for _ in ()).throw(AssertionError("download")),
    )
    assert result["counts"]["meta_only"] == 1
    record = (tmp_path / "2020-회계기준자문위원회-1회" / "record.md").read_text(encoding="utf-8")
    assert "## 붙임" in record
    assert "국제동향 보고" in record
    meta = kasb_meetings.read_meta(tmp_path / "2020-회계기준자문위원회-1회" / "record.md")
    assert meta["decision_items"] == page.decision_items
    assert "붙임" not in " ".join(meta["decision_items"])
    assert meta["appendix_items"] == page.appendix_items


def test_unknown_row_category_is_not_saved_as_accounting_committee():
    row = kasb_meetings.ScheduleRow(
        seq="1",
        date="2020-01-01",
        category="회계기준 > 회계기준자문위원회",
        title="2020년 제1회 회계기준자문위원회",
        place="홀",
        year=2020,
        round_no=1,
    )
    with pytest.raises(ValueError, match="중분류"):
        kasb_meetings.build_plan(row, kasb_meetings.ParsedPage(), kasb_meetings.ParsedPage())


def test_collect_advisory_record_keeps_section_titles_and_meta_only(tmp_path):
    rows = {
        row.seq: row
        for row in kasb_meetings.parse_list_page(
            _read("list.html"), committee="회계기준자문위원회"
        )
    }
    def fetch_file(file_no: str, file_seq: str) -> bytes:
        raise AssertionError("download")

    result = kasb_meetings.collect(
        tmp_path,
        [rows["1124"], rows["847"]],
        fetch_view=lambda seq: _read(f"view/{seq}.html"),
        fetch_meet=lambda seq: _read(f"meet/{seq}.html") if seq == "1124" else "",
        fetch_file=fetch_file,
    )
    assert result["counts"]["meta_only"] == 2
    assert result["counts"]["saved"] == 0
    recent = tmp_path / "2026-회계기준자문위원회-1회"
    early = tmp_path / "1999-회계기준자문위원회-1회"
    assert not (tmp_path / "2026-회계기준위원회-1회").exists()
    assert not (tmp_path / "1999-회계기준위원회-1회").exists()
    record = (recent / "record.md").read_text(encoding="utf-8")
    assert "## 의결 안건" in record
    assert "## 보고 안건" in record
    assert "■ 안 건" not in record
    assert "KK-IFRS" in record
    meta = kasb_meetings.read_meta(recent / "record.md")
    assert meta["status"] == "meta_only"
    assert meta["category"] == "회계기준 > 회계기준자문위원회"
    assert meta["seq"] == "1124"
    assert "term" not in meta
    assert meta["decision_items"][0].startswith("1) K-IFRS 제1118호")
    assert meta["report_items"] == ["1) 지난 회의록 보고"]
    early_meta = kasb_meetings.read_meta(early / "record.md")
    assert early_meta["term"] == 1
    assert early_meta["round"] == 1
    assert early_meta["year"] == 1999
    assert early_meta["decision_items"] == ["1. KASB 중단기 Agendas"]
    assert list((recent / "agenda").iterdir()) == []
    assert list((recent / "results").iterdir()) == []


def test_dry_run_advisory_uses_its_folder_and_does_not_open_a_socket(capsys, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("socket")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "socket", blocked)
    code = kasb_meetings.main(
        ["--dry-run", "--committee", "회계기준자문위원회", "--limit", "3"]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "dry-run network=no meetings=3" in out
    assert "folder=2026-회계기준자문위원회-2회" in out
    assert "folder=2026-회계기준자문위원회-1회" in out
    assert "folder=2026-회계기준위원회-" not in out
    assert "seq=1105" not in out
    assert "seq=1109" not in out


def test_unknown_committee_exits_without_a_socket(capsys, monkeypatch):
    _block_network(monkeypatch)
    code = kasb_meetings.main(
        ["--dry-run", "--committee", "세미나", "--limit", "1"]
    )
    assert code == 2
    assert "회계기준자문위원회" in capsys.readouterr().err


def test_default_list_post_omits_category_filter():
    seen = {}

    class Session:
        def post(self, url, data=None, timeout=None):
            seen["url"] = url
            seen["data"] = dict(data)
            return _Response(200, "<table></table>")

    assert kasb_meetings.http_fetch_list(Session(), 1, "2020-01-01", "2020-12-31")
    assert seen["url"] == kasb_meetings.LIST_URL
    assert seen["data"]["page"] == 1
    assert seen["data"]["s_date_start"] == "2020-01-01"
    assert "category" not in seen["data"]
    assert "subCategoryList" not in seen["data"]


def test_advisory_list_post_sends_category_filter():
    seen = {}

    class Session:
        def post(self, url, data=None, timeout=None):
            seen["data"] = dict(data)
            return _Response(200, "<table></table>")

    kasb_meetings.http_fetch_list(
        Session(), 1, "", "", kasb_meetings.ADVISORY_COMMITTEE
    )
    assert seen["data"]["category"] == "012005001000"
    assert seen["data"]["subCategoryList"] == "012005001002"
    assert seen["data"]["siteCd"] == kasb_meetings.SITE_CD
    assert seen["data"]["page"] == 1


def test_gather_rows_selects_only_the_requested_committee():
    pages = {1: _read("list.html")}

    def fetch_page(page: int) -> str:
        return pages.get(page, "<table><tbody></tbody></table>")

    advisory = kasb_meetings.gather_rows(
        fetch_page,
        limit=2,
        seqs=None,
        committee="회계기준자문위원회",
    )
    assert [row.seq for row in advisory] == ["9002", "1124"]
    accounting = kasb_meetings.gather_rows(fetch_page, limit=1, seqs=None)
    assert [row.seq for row in accounting] == ["1109"]
