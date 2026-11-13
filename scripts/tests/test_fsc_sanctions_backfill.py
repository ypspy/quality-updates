# -*- coding: utf-8 -*-
"""Offline tests for FSC sanctions backfill. No live HTTP."""

import json
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attach_sanction_minutes import decision_key

ROOT = Path(__file__).resolve().parents[2]


def test_decision_key_covers_backfill_titles():
    assert decision_key("2026년도 제15차 금융위원회 의사록, 안건 및 제재안건 의결서") == (
        2026,
        "금융위",
        "정기",
        15,
    )
    assert decision_key("2026년도 제19차 금융위원회 회의결과") == (2026, "금융위", "정기", 19)
    assert decision_key("2026년도 제1차 임시 금융위원회 의사록 및 안건") == (
        2026,
        "금융위",
        "임시",
        1,
    )
    # 제목의 2022년도를 쓴다. 임시가 연도와 제N차 사이에 있어도 게시일 2023-02-27의 연도를 쓰지 않는다.
    assert decision_key("2022년도 임시 제4차 금융위원회 의사록", date(2023, 2, 27)) == (
        2022,
        "금융위",
        "임시",
        4,
    )
    assert decision_key("2022년도 임시 제4차 금융위원회 안건", date(2023, 2, 27)) == (
        2022,
        "금융위",
        "임시",
        4,
    )
    assert decision_key("2026년도 제1차 금융위원회 서면회의 의사록 및 안건") == (
        2026,
        "금융위",
        "서면",
        1,
    )
    assert decision_key("2026년 제1차 임시증권선물위원회 의사록 및 안건") == (
        2026,
        "증선위",
        "임시",
        1,
    )
    assert decision_key("2026년 제2차 증권선물위원회 임시회의 회의결과") == (
        2026,
        "증선위",
        "임시",
        2,
    )
    assert decision_key("2026년 제9차 증권선물위원회 의사록(추가), 안건 및 제재안건 의결서") == (
        2026,
        "증선위",
        "정기",
        9,
    )
    assert decision_key("2026년 제9차 증권선물위원회 의사록(재추가)") == (2026, "증선위", "정기", 9)
    # 제목에 2024년이 있으므로 게시일 2025-02-07의 연도를 쓰지 않는다.
    assert decision_key("2024년도 제21차 금융위원회 의사록(수정)", date(2025, 2, 7)) == (
        2024,
        "금융위",
        "정기",
        21,
    )
    # 제목에 연도가 없다. 게시일 2001-01-26의 연도를 쓴다.
    assert decision_key("제1차 금융감독위원회 의결안건", date(2001, 1, 26)) == (
        2001,
        "금융위",
        "정기",
        1,
    )
    # 제목에 연도가 없다. 게시일 2008-11-05의 연도를 쓴다.
    assert decision_key("제14차 증권선물의원회 의사록", date(2008, 11, 5)) == (
        2008,
        "증선위",
        "정기",
        14,
    )
    assert decision_key("2016년 제18증권선물위원회 의사록") == (2016, "증선위", "정기", 18)
    assert decision_key("2019년 제12차 증선위 시장질서교란행위 의결서") == (
        2019,
        "증선위",
        "정기",
        12,
    )
    # 제목에 연도가 없다. 게시일 2021-06-15의 연도를 쓴다.
    assert decision_key("제12차 증권선물위원회 시장질서교란행위 의결서", date(2021, 6, 15)) == (
        2021,
        "증선위",
        "정기",
        12,
    )
    assert decision_key("2025년도 비공개기간 경과 금융위원회 안건") is None
    assert decision_key("2025년 말 기준 비공개사유 종료 및 비공개기간 경과 안건") is None
    # 띄어쓴 비공개 경과 문구도 회의가 아니다. 게시일은 각각 2022-12-29, 2021-12-30, 2019-12-31.
    assert decision_key("2022년말 기준 비공개 사유 종료 및 비공개 기간 경과 안건", date(2022, 12, 29)) is None
    assert decision_key("비공개 사유 종료 및 비공개 기간 경과 안건", date(2021, 12, 30)) is None
    assert decision_key("2019년 증권선물위원회 비공개 기간 경과 안건", date(2019, 12, 31)) is None
    assert decision_key("증권선물위원회의 '증권범죄조사사무처리규정' 제정") is None


def test_market_disruption_files_are_not_kept():
    from attach_sanction_minutes import audit_zip_entries

    kept, _whale = audit_zip_entries(
        [
            "(의결서) 의결 12. 시장질서교란 조사·감리결과.pdf",
            "(공개용) 의결 1. 회계법인 감리결과 조치안.pdf",
        ]
    )
    assert [item.filename for item in kept] == ["(공개용) 의결 1. 회계법인 감리결과 조치안.pdf"]


def test_foreign_year_and_duplicate_bytes_are_dropped():
    from attach_sanction_minutes import select_named_files

    body = b"same-minutes"
    kept, notes = select_named_files(
        2008,
        [
            ("2009-제18차 증권선물위원회 의사록.hwp", b"old-hwp"),
            ("제18차-09년 의사록.pdf", b"two-digit"),
            ("의결 1[1].pdf", body),
            ("의결 1 사본.pdf", body),
            ("의결 1.pdf", body),
            ("의결 2. 감사인 조사결과.pdf", b"other"),
            ("2008년 의사록.pdf", b"same-year"),
        ],
    )
    names = [name for name, _payload in kept]
    assert "2009-제18차 증권선물위원회 의사록.hwp" not in names
    assert "제18차-09년 의사록.pdf" not in names
    assert "의결 1.pdf" in names
    assert "의결 1[1].pdf" not in names
    assert "의결 1 사본.pdf" not in names
    assert "의결 2. 감사인 조사결과.pdf" in names
    assert "2008년 의사록.pdf" in names
    assert any("2009-제18차" in note for note in notes)
    assert any("09년" in note for note in notes)


def test_pending_minutes_suffixes():
    from attach_sanction_minutes import is_pending_minutes

    assert is_pending_minutes("제14차 의사록.hwp")
    assert is_pending_minutes("제14차 의사록.hwpx")
    assert is_pending_minutes("제14차 의사록.xls")
    assert is_pending_minutes("제14차 의사록.xlsx")
    assert not is_pending_minutes("제14차 의사록.pdf")
    assert not is_pending_minutes("감리결과.hwp")


def test_failure_log_overwrites_the_same_url_and_stays_one_line(tmp_path):
    from attach_sanction_minutes import record_failure

    path = tmp_path / "_failed-downloads.jsonl"
    first = {
        "ts": "2026-11-13T03:00:00+09:00",
        "board": "증선위",
        "post_id": "14",
        "page_url": "https://fsc.go.kr/no020102/14",
        "url": "https://fsc.go.kr/comm/getFile?fileNo=1",
        "filename": "minutes.pdf",
        "http_status": 403,
        "error": "HTTP 403",
        "attempts": 2,
    }
    record_failure(path, first)
    record_failure(path, first)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["http_status"] == 403

    updated = dict(first)
    updated["http_status"] = None
    updated["error"] = "SSLError: UNEXPECTED_EOF"
    updated["attempts"] = 5
    updated["ts"] = "2026-11-13T04:00:00+09:00"
    record_failure(path, updated)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["http_status"] is None
    assert "UNEXPECTED_EOF" in row["error"]
    assert row["attempts"] == 5
    assert row["ts"].endswith("+09:00")


def test_http_retries_and_normalizes_www_host(monkeypatch):
    import requests

    import attach_sanction_minutes as asm

    sleeps: list[float] = []
    seen: list[str] = []
    monkeypatch.setattr(asm.time, "sleep", lambda seconds: sleeps.append(seconds))
    asm._requests_made = 0
    asm._request_delay = 0
    codes = [503, 503, 200]

    class Response:
        def __init__(self, status):
            self.status_code = status
            self.text = "ok"
            self.content = b"ok"

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(str(self.status_code))

    def fake_get(url, timeout=30, headers=None):
        seen.append(url)
        assert headers["User-Agent"].startswith("Mozilla/5.0")
        return Response(codes.pop(0))

    monkeypatch.setattr(requests, "get", fake_get)
    assert asm._http_text("https://www.fsc.go.kr/no020101") == "ok"
    assert seen == ["https://fsc.go.kr/no020101"] * 3
    assert sleeps == [asm.HTTP_BACKOFF_BASE, asm.HTTP_BACKOFF_BASE * 2]
    assert asm._backoff_seconds(10) == asm.HTTP_BACKOFF_CAP


def test_http_403_retries_once_then_fails(monkeypatch):
    import requests

    import attach_sanction_minutes as asm

    sleeps: list[float] = []
    monkeypatch.setattr(asm.time, "sleep", lambda seconds: sleeps.append(seconds))
    asm._requests_made = 0
    asm._request_delay = 0

    class Response:
        status_code = 403
        text = "no"
        content = b"no"

        def raise_for_status(self):
            raise requests.HTTPError("403")

    monkeypatch.setattr(requests, "get", lambda url, timeout=30, headers=None: Response())
    with pytest.raises(asm.FetchFailed) as caught:
        asm._http_text("https://www.fsc.go.kr/no020102/1")
    assert caught.value.http_status == 403
    assert caught.value.attempts == 2
    assert sleeps == [asm.HTTP_FORBIDDEN_DELAY]


def test_http_retries_tls_eof(monkeypatch):
    import requests

    import attach_sanction_minutes as asm

    monkeypatch.setattr(asm.time, "sleep", lambda seconds: None)
    asm._requests_made = 0
    asm._request_delay = 0
    calls = {"n": 0}

    class Response:
        status_code = 200
        text = "ok"
        content = b"ok"

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=30, headers=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.exceptions.SSLError("UNEXPECTED_EOF_WHILE_READING")
        return Response()

    monkeypatch.setattr(requests, "get", fake_get)
    assert asm._http_text("https://fsc.go.kr/no020101") == "ok"
    assert calls["n"] == 3


DRY_LIST = """
<ul>
  <li><div class="inner"><div class="subject"><a href="/no020102/19">2026년도 제19차 금융위원회 회의결과</a></div><div class="day">2026-11-01</div></div></li>
  <li><div class="inner"><div class="subject"><a href="/no020102/90">2025년도 비공개기간 경과 금융위원회 안건</a></div><div class="day">2025-12-31</div></div></li>
  <li><div class="inner"><div class="subject"><a href="/no020102/9">2026년 제9차 증권선물위원회 의사록(추가), 안건 및 제재안건 의결서</a></div><div class="day">2026-03-01</div></div></li>
  <li><div class="inner"><div class="subject"><a href="/no020102/14">제14차 증권선물의원회 의사록</a></div><div class="day">2008-11-05</div></div></li>
  <li><div class="inner"><div class="subject"><a href="/no020102/12">2019년 제12차 증선위 시장질서교란행위 의결서</a></div><div class="day">2019-04-02</div></div></li>
</ul>
"""

DRY_PDF = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=9&fileTy=ATTACH&fileNo=1">2026년 제9차 증권선물위원회 의사록(추가).pdf</a>
"""

DRY_HWP = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=14&fileTy=ATTACH&fileNo=3">제14차 증권선물의원회 의사록.hwp</a>
"""

DRY_MARKET = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=12&fileTy=ATTACH&fileNo=4">2019년 제12차 증선위 시장질서교란행위 의결서.pdf</a>
"""


def _dry_fetch(url: str) -> str:
    if "curPage=1" in url and "no020102" in url:
        return DRY_LIST
    if "curPage=" in url:
        return "<ul></ul>"
    if url.endswith("/9"):
        return DRY_PDF
    if url.endswith("/14"):
        return DRY_HWP
    if url.endswith("/12"):
        return DRY_MARKET
    raise AssertionError(url)


def test_backfill_dry_run_does_not_download(tmp_path, monkeypatch, capsys):
    import attach_sanction_minutes as asm

    downloads = []

    def download(url, dest):
        downloads.append(url)
        raise AssertionError(url)

    fake_script = tmp_path / "scripts" / "attach_sanction_minutes.py"
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text("# stub\n", encoding="utf-8")
    monkeypatch.setattr(asm, "__file__", str(fake_script))
    monkeypatch.setattr(asm, "_http_text", _dry_fetch)
    monkeypatch.setattr(asm, "_http_download", download)
    monkeypatch.setattr(requests_module(), "get", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live")))

    quarter = tmp_path / "2026-07-01_to_2026-09-30.md"
    quarter.write_text("unchanged\n", encoding="utf-8")
    code = asm.main(
        [
            str(quarter),
            "--backfill",
            "--dry-run",
            "--board",
            "증선위",
            "--since",
            "2001-02-08",
            "--until",
            "2026-11-13",
            "--delay",
            "0",
        ]
    )
    output = capsys.readouterr().out
    assert code == 0
    assert quarter.read_text(encoding="utf-8") == "unchanged\n"
    assert downloads == []
    assert "만들 폴더: 1" in output
    assert "받을 파일: 1" in output
    assert "건너뛸 글: 4" in output
    assert not (tmp_path / "downloads" / "sanctions").exists()


def requests_module():
    import requests

    return requests


def test_since_without_backfill_is_an_error(tmp_path, monkeypatch):
    import attach_sanction_minutes as asm

    monkeypatch.setattr(
        requests_module(),
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live")),
    )
    quarter = tmp_path / "2026-07-01_to_2026-09-30.md"
    quarter.write_text("unchanged\n", encoding="utf-8")
    assert asm.main([str(quarter), "--since", "2001-01-26"]) == 2
    assert quarter.read_text(encoding="utf-8") == "unchanged\n"


def test_default_since_follows_the_board(tmp_path, monkeypatch, capsys):
    import attach_sanction_minutes as asm

    seen: list[str] = []

    def fetch_text(url: str) -> str:
        seen.append(url)
        return "<ul></ul>"

    fake_script = tmp_path / "scripts" / "attach_sanction_minutes.py"
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text("# stub\n", encoding="utf-8")
    monkeypatch.setattr(asm, "__file__", str(fake_script))
    monkeypatch.setattr(asm, "_http_text", fetch_text)
    monkeypatch.setattr(
        asm,
        "_http_download",
        lambda url, dest: (_ for _ in ()).throw(AssertionError(url)),
    )
    assert asm.main(["--backfill", "--dry-run", "--board", "증선위", "--delay", "0", "--until", "2026-11-13"]) == 0
    assert any("no020102" in url and "srchBeginDt=2001-02-08" in url for url in seen)
    assert all("no020101" not in url for url in seen)
    capsys.readouterr()

    seen.clear()
    assert asm.main(["--backfill", "--dry-run", "--delay", "0", "--until", "2026-11-13"]) == 0
    assert any("no020101" in url and "srchBeginDt=2001-01-26" in url for url in seen)
    assert any("no020102" in url and "srchBeginDt=2001-01-26" in url for url in seen)


def _zip_with(entries: list[tuple[str, bytes]]) -> bytes:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return buffer.getvalue()


BYTE_LIST = """
<ul>
  <li><div class="inner"><div class="subject"><a href="/no020102/14">제14차 증권선물의원회 의사록</a></div><div class="day">2008-11-05</div></div></li>
</ul>
"""

BYTE_DETAIL = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=14&fileTy=ATTACH&fileNo=1">2008년 제14차 증권선물의원회 의사록.pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=14&fileTy=ATTACH&fileNo=2">안건.zip</a>
"""


def test_backfill_two_runs_match_bytes_and_keep_existing_minutes(tmp_path):
    import attach_sanction_minutes as asm

    downloads = tmp_path / "downloads"
    folder = downloads / "sanctions" / "2008-증선위-14차"
    folder.mkdir(parents=True)
    minutes = folder / "minutes.pdf"
    minutes.write_bytes(b"keep-me")
    same = b"agenda-bytes"
    downloaded: list[str] = []

    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020102" in url:
            return BYTE_LIST
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/14"):
            return BYTE_DETAIL
        raise AssertionError(url)

    def download(url: str, dest: Path) -> None:
        downloaded.append(url)
        assert "fileNo=1" not in url
        dest.write_bytes(
            _zip_with(
                [
                    ("2009-제18차 증권선물위원회 의사록.hwp", b"hwp"),
                    ("(공개용) 의결 1. 회계법인 감리결과 사본.pdf", same),
                    ("(공개용) 의결 1. 회계법인 감리결과.pdf", same),
                    ("(공개용) 의결 2. 감사인 조사결과.pdf", b"different"),
                ]
            )
        )

    def run():
        return asm.run_backfill(
            fetch_text,
            download,
            downloads,
            since=date(2001, 2, 8),
            until=date(2026, 11, 13),
            board="증선위",
            dry_run=False,
            resume=False,
            retry_failed=False,
        )

    first = run()
    assert any("2009-제18차" in line for line in first["report"])

    def snapshot():
        found = {}
        for path in downloads.rglob("*"):
            if path.is_file():
                found[str(path.relative_to(downloads))] = path.read_bytes()
        return found

    shot = snapshot()
    assert shot["sanctions/2008-증선위-14차/minutes.pdf"] == b"keep-me"
    names = "\n".join(shot)
    assert "2009-제18차" not in names
    assert "사본" not in names
    assert "감리결과.pdf" in names
    assert "조사결과.pdf" in names
    state = json.loads((downloads / "sanctions" / "_backfill-state.json").read_text(encoding="utf-8"))
    assert state["posts"][0]["post_id"] == "14"
    assert state["posts"][0]["page"] == 1
    readme = downloads / "sanctions" / "README.md"
    assert readme.read_bytes() == (ROOT / "docs" / "project" / "sanctions-downloads-readme.md").read_bytes()

    downloaded.clear()
    second = run()
    assert snapshot() == shot
    assert second["folders"] == first["folders"]
    assert not any("fileNo=1" in url for url in downloaded)


RESUME_LIST = """
<ul>
  <li><div class="inner"><div class="subject"><a href="/no020102/14">제14차 증권선물의원회 의사록</a></div><div class="day">2008-11-05</div></div></li>
</ul>
"""

RESUME_DETAIL = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=14&fileTy=ATTACH&fileNo=1">2008년 제14차 증권선물의원회 의사록.pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=14&fileTy=ATTACH&fileNo=2">안건.zip</a>
"""


def test_resume_skips_403_and_retries_tls_only_with_retry_failed(tmp_path):
    import attach_sanction_minutes as asm

    downloads = tmp_path / "downloads"
    pdf_url = "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=14&fileTy=ATTACH&fileNo=1"
    zip_url = "https://fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=14&fileTy=ATTACH&fileNo=2"
    asm.record_failure(
        downloads / "sanctions" / "_failed-downloads.jsonl",
        {
            "ts": "2026-11-13T03:00:00+09:00",
            "board": "증선위",
            "post_id": "14",
            "page_url": "https://fsc.go.kr/no020102/14",
            "url": pdf_url,
            "filename": "2008년 제14차 증권선물의원회 의사록.pdf",
            "http_status": 403,
            "error": "HTTP 403",
            "attempts": 2,
        },
    )
    asm.record_failure(
        downloads / "sanctions" / "_failed-downloads.jsonl",
        {
            "ts": "2026-11-13T03:00:01+09:00",
            "board": "증선위",
            "post_id": "14",
            "page_url": "https://fsc.go.kr/no020102/14",
            "url": zip_url,
            "filename": "안건.zip",
            "http_status": None,
            "error": "SSLError: UNEXPECTED_EOF",
            "attempts": 5,
        },
    )
    calls: list[str] = []

    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020102" in url:
            return RESUME_LIST
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/14"):
            return RESUME_DETAIL
        raise AssertionError(url)

    def download(url: str, dest: Path) -> None:
        calls.append(url)
        dest.write_bytes(_zip_with([("(공개용) 의결 1. 회계법인 감리결과.pdf", b"pdf")]))

    common = dict(
        fetch_text=fetch_text,
        download=download,
        downloads=downloads,
        since=date(2008, 1, 1),
        until=date(2008, 12, 31),
        board="증선위",
        dry_run=False,
    )
    asm.run_backfill(**common, resume=True, retry_failed=False)
    assert zip_url in calls
    assert pdf_url not in calls

    calls.clear()
    asm.run_backfill(**common, resume=True, retry_failed=True)
    assert pdf_url in calls


def test_backfill_records_403_and_pending_hwp(tmp_path):
    import attach_sanction_minutes as asm

    downloads = tmp_path / "downloads"
    calls: list[str] = []

    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020102" in url:
            return DRY_LIST
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/9"):
            return DRY_PDF
        if url.endswith("/14"):
            return DRY_HWP
        if url.endswith("/12"):
            return DRY_MARKET
        raise AssertionError(url)

    def download(url, dest):
        calls.append(url)
        raise asm.FetchFailed(url, 403, "HTTP 403", 2)

    summary = asm.run_backfill(
        fetch_text,
        download,
        downloads,
        since=date(2001, 2, 8),
        until=date(2026, 11, 13),
        board="증선위",
        dry_run=False,
        resume=False,
        retry_failed=False,
    )
    assert summary["folders"] == 1
    assert calls
    failed = (downloads / "sanctions" / "_failed-downloads.jsonl").read_text(encoding="utf-8")
    row = json.loads(failed.splitlines()[0])
    assert row["http_status"] == 403
    assert row["attempts"] == 2
    assert row["board"] == "증선위"
    parsed_ts = datetime.fromisoformat(row["ts"])
    assert parsed_ts.tzinfo is not None and parsed_ts.utcoffset() is not None
    assert "T" in row["ts"]
    pending_path = downloads / "sanctions" / "_pending-conversion.jsonl"
    pending = [json.loads(line) for line in pending_path.read_text(encoding="utf-8").splitlines()]
    assert pending[0]["reason"] == "not-pdf"
    assert pending[0]["filename"].endswith(".hwp")
    assert not (downloads / "sanctions" / "2008-증선위-14차").exists()
    assert not (downloads / "sanctions" / "2019-증선위-12차").exists()
    assert not list(downloads.rglob("*.hwp"))
    assert not list(downloads.rglob("*.zip"))


def test_readme_is_tracked_and_originals_stay_ignored():
    import subprocess

    doc = ROOT / "docs" / "project" / "sanctions-downloads-readme.md"
    tracked = ROOT / "downloads" / "sanctions" / "README.md"
    assert doc.read_bytes() == tracked.read_bytes()
    text = doc.read_text(encoding="utf-8")
    assert "README.md" in text
    assert "2001-01-26" in text
    assert "2001-02-08" in text
    assert "시장질서교란" in text
    assert "_failed-downloads.jsonl" in text

    def ignored(path: str) -> bool:
        completed = subprocess.run(
            ["git", "check-ignore", "-q", path],
            cwd=ROOT,
            check=False,
        )
        return completed.returncode == 0

    assert not ignored("downloads/sanctions/README.md")
    assert ignored("downloads/sanctions/_failed-downloads.jsonl")
    assert ignored("downloads/sanctions/_backfill-state.json")
    assert ignored("downloads/sanctions/_pending-conversion.jsonl")
    assert ignored("downloads/sanctions/2008-증선위-14차/minutes.pdf")
