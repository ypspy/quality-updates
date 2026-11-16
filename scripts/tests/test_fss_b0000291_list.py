# -*- coding: utf-8 -*-
"""B0000291 주간 감지기 테스트. 네트워크를 쓰지 않는다(요청 함수 주입, 소켓 차단)."""
import json
import os
import socket
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler import fss_b0000291  # noqa: E402
from crawler import fss_b0000291_list as watch  # noqa: E402
import watch_fss_b0000291 as cli  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "b0000291"
LIST = (FIXTURES / "list_cl01.html").read_text(encoding="utf-8")
EMPTY = (FIXTURES / "list_empty.html").read_text(encoding="utf-8")
CT = ZoneInfo("America/Chicago")
MON = datetime(2026, 11, 23, 7, 30, tzinfo=CT)
NEXT_MON = datetime(2026, 11, 30, 7, 30, tzinfo=CT)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("테스트에서 네트워크를 쓰면 안 됩니다.")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _extra_row(ntt_id: int, no: int, firm: str, files: str = "새파일.hwpx") -> str:
    return (
        f'<tr ><td>{no}</td><td><a href="/fss/bbs/B0000291/view.do?nttId={ntt_id}&amp;menuNo=200620'
        f'&amp;cl1Cd=01&amp;pageIndex=1">{firm}</a></td><td>2023-04-01~2026-03-31</td>'
        f'<td>2027-03-02</td><td><ul class="list-board-attach-file"><li><a href="#">'
        f'<span class="name">{files}</span></a></li></ul></td></tr>'
    )


def _with_rows(page: str, rows: list[str], total: int) -> str:
    out = page.replace("<tbody>", "<tbody>\n" + "\n".join(rows), 1)
    return out.replace("전체 <em>3</em>건", f"전체 <em>{total}</em>건")


class Fetcher:
    """탭별 HTML을 돌려주는 가짜 요청 함수. 부른 URL을 기록한다."""

    def __init__(self, pages: dict[str, str | Exception]):
        self.pages = pages
        self.calls: list[str] = []

    def __call__(self, url: str) -> str:
        self.calls.append(url)
        tab = "02" if "cl1Cd=02" in url else "01"
        value = self.pages[tab]
        if isinstance(value, Exception):
            raise value
        return value


def _args(tmp_path: Path, *extra: str):
    return cli.parse_args(["--dest", str(tmp_path / "dest"), *extra])


def _files(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*")) if root.exists() else []


# --- 구문 분석 ---


def test_parse_fixture_rows_and_total():
    page = watch.parse_list(LIST)
    assert (page.total, page.page, page.pages) == (3, 1, 1)
    assert [row.ntt_id for row in page.rows] == [218147, 218146, 218145]
    first = page.rows[0]
    assert (first.no, first.firm, first.period, first.action_date) == (
        "252",
        "태일회계법인",
        "2022-04-01~2025-06-30",
        "2026-05-12",
    )
    assert first.files == ("태일회계법인_개선권고사항.hwpx",)


def test_parse_empty_tab():
    page = watch.parse_list(EMPTY)
    assert page.total == 0 and page.rows == ()


def test_notice_rows_are_skipped():
    notice = (
        '<tr class="notice"><td>공지</td><td><a href="/fss/bbs/B0000291/view.do?nttId=1">안내</a></td>'
        "<td></td><td></td><td></td></tr>"
    )
    page = watch.parse_list(LIST.replace("<tbody>", "<tbody>" + notice, 1))
    assert [row.ntt_id for row in page.rows] == [218147, 218146, 218145]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda t: t.replace("nttId=218146", "x=218146"),
        lambda t: t.replace("전체 <em>3</em>건", ""),
        lambda t: t.replace('class="tbl col list-data"', 'class="tbl"'),
        lambda t: EMPTY.replace("전체 <em>0</em>건", "전체 <em>5</em>건"),
        lambda t: t.replace("<tbody>", '<tbody><tr><td colspan="5" class="nodata">자료가 없습니다.</td></tr>', 1),
        lambda t: "<html></html>",
    ],
)
def test_parse_errors(mutate):
    with pytest.raises(watch.ListParseError):
        watch.parse_list(mutate(LIST))


def test_list_url_uses_the_tab_menu_and_page_unit():
    assert watch.list_url("01") == (
        "https://www.fss.or.kr/fss/bbs/B0000291/list.do?menuNo=200620&pageIndex=1&cl1Cd=01&pageUnit=300"
    )
    assert "menuNo=200621" in watch.list_url("02", 2) and "pageIndex=2" in watch.list_url("02", 2)
    with pytest.raises(ValueError):
        watch.list_url("03")


# --- 실행 흐름 ---


def test_init_writes_baseline_without_alerting(tmp_path):
    args = _args(tmp_path, "--init")
    fetch = Fetcher({"01": LIST, "02": EMPTY})
    code, result = cli.run(args, fetch, now=MON, sleeper=lambda s: None)
    assert code == cli.EXIT_OK
    assert result["status"] == "ok"
    assert [item["new"] for item in result["tabs"]] == [[], []]
    assert [item["baseline"] for item in result["tabs"]] == [3, 0]
    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert sorted(state["tabs"]["01"]["known"]) == ["218145", "218146", "218147"]
    assert state["tabs"]["01"]["total_count"] == 3
    assert state["tabs"]["01"]["max_ntt_id"] == 218147
    assert state["tabs"]["02"]["known"] == {}
    assert state["last_ok_ct"] == "2026-11-23T07:30:00-06:00"
    assert (args.dest / "_weekly" / "2026-11-23.json").is_file()
    assert len(fetch.calls) == 2


def _baseline(tmp_path):
    args = _args(tmp_path, "--init")
    cli.run(args, Fetcher({"01": LIST, "02": EMPTY}), now=MON, sleeper=lambda s: None)
    return _args(tmp_path)


def test_quiet_week(tmp_path):
    args = _baseline(tmp_path)
    code, result = cli.run(args, Fetcher({"01": LIST, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert code == cli.EXIT_OK
    assert cli.summary_line(result) == "total=3 new=0 changed=0 missing=0 status=ok notify=no"
    assert result["missed_week"] is False


def test_new_post_is_reported_and_remembered(tmp_path):
    args = _baseline(tmp_path)
    page = _with_rows(LIST, [_extra_row(220001, 253, "새회계법인")], 4)
    code, result = cli.run(args, Fetcher({"01": page, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert code == cli.EXIT_NEW
    new = result["tabs"][0]["new"]
    assert [item["nttId"] for item in new] == [220001]
    assert new[0]["firm"] == "새회계법인" and new[0]["action_date"] == "2027-03-02"
    assert new[0]["url"].endswith("nttId=220001&menuNo=200620&cl1Cd=01")
    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert state["tabs"]["01"]["known"]["220001"]["first_seen_ct"] == "2026-11-30T07:30:00-06:00"
    again, _ = cli.run(args, Fetcher({"01": page, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert again == cli.EXIT_OK


def test_changed_post(tmp_path):
    args = _baseline(tmp_path)
    page = LIST.replace("태일회계법인_개선권고사항.hwpx", "태일회계법인_개선권고사항(수정).hwpx")
    code, result = cli.run(args, Fetcher({"01": page, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert code == cli.EXIT_NEW
    changed = result["tabs"][0]["changed"]
    assert changed[0]["nttId"] == 218147 and changed[0]["fields"] == ["files"]


def test_missing_post_and_total_drop_warn(tmp_path):
    args = _baseline(tmp_path)
    start = LIST.index("<tr >")
    end = LIST.index("</tr>", start) + len("</tr>")
    page = (LIST[:start] + LIST[end:]).replace("전체 <em>3</em>건", "전체 <em>2</em>건")
    code, result = cli.run(args, Fetcher({"01": page, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert code == cli.EXIT_WARN
    tab = result["tabs"][0]
    assert tab["missing"] == [{"nttId": 218147, "firm": "태일회계법인"}]
    assert tab["total_drop"] is True and tab["previous_total"] == 3
    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert state["tabs"]["01"]["known"]["218147"]["missing_since"] == "2026-11-30T07:30:00-06:00"


def test_count_mismatch_warns(tmp_path):
    args = _baseline(tmp_path)
    page = LIST.replace("전체 <em>3</em>건", "전체 <em>4</em>건")
    code, result = cli.run(args, Fetcher({"01": page, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert code == cli.EXIT_WARN
    assert result["tabs"][0]["count_mismatch"] is True


def test_second_page_is_read_only_when_needed(tmp_path):
    args = _args(tmp_path, "--init")
    first = LIST.replace("전체 <em>3</em>건", "전체 <em>4</em>건").replace("페이지 <em>1</em> / 1", "페이지 <em>1</em> / 2")
    second = _with_rows(LIST, [_extra_row(100, 1, "옛회계법인")], 4)
    calls = []

    def fetch(url):
        calls.append(url)
        if "cl1Cd=02" in url:
            return EMPTY
        return second if "pageIndex=2" in url else first

    code, result = cli.run(args, fetch, now=MON, sleeper=lambda s: None)
    assert code == cli.EXIT_OK
    assert result["tabs"][0]["rows"] == 4  # 둘째 쪽의 중복 nttId 3개는 한 번만 셈
    assert sum("cl1Cd=01" in url for url in calls) == 2


@pytest.mark.parametrize(
    "error,code,status",
    [
        (fss_b0000291.FetchError("HTTP 500", http_status=500, attempts=5, url="u"), cli.EXIT_FETCH, "fetch-error"),
        (fss_b0000291.FetchError("HTTP 403", http_status=403, attempts=2, url="u"), cli.EXIT_FORBIDDEN, "forbidden"),
    ],
)
def test_fetch_failures_leave_state_bytes_unchanged(tmp_path, error, code, status):
    args = _baseline(tmp_path)
    before = args.state.read_bytes()
    files = _files(args.dest)
    got, result = cli.run(args, Fetcher({"01": error, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert got == code and result["status"] == status
    assert args.state.read_bytes() == before
    assert _files(args.dest) == files


def test_parse_failure_keeps_state_and_saves_html(tmp_path):
    args = _baseline(tmp_path)
    before = args.state.read_bytes()
    broken = "<html>바뀐 화면</html>"
    code, result = cli.run(args, Fetcher({"01": broken, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert code == cli.EXIT_PARSE and result["status"] == "parse-error"
    assert args.state.read_bytes() == before
    saved = args.dest / "_weekly" / "2026-11-30-01.html"
    assert saved.read_text(encoding="utf-8") == broken


def test_second_tab_failure_does_not_apply_the_first_tab(tmp_path):
    args = _baseline(tmp_path)
    before = args.state.read_bytes()
    page = _with_rows(LIST, [_extra_row(220001, 253, "새회계법인")], 4)
    error = fss_b0000291.FetchError("HTTP 502", http_status=502, attempts=5, url="u")
    code, _ = cli.run(args, Fetcher({"01": page, "02": error}), now=NEXT_MON, sleeper=lambda s: None)
    assert code == cli.EXIT_FETCH
    assert args.state.read_bytes() == before


def test_dry_run_writes_nothing(tmp_path):
    args = _args(tmp_path, "--dry-run")
    code, result = cli.run(args, Fetcher({"01": LIST, "02": EMPTY}), now=MON, sleeper=lambda s: None)
    assert code == cli.EXIT_NEW and result["dry_run"] is True
    assert _files(tmp_path) == []
    broken, _ = cli.run(args, Fetcher({"01": "<html></html>", "02": EMPTY}), now=MON, sleeper=lambda s: None)
    assert broken == cli.EXIT_PARSE
    assert _files(tmp_path) == []


def test_bad_state_file_stops_before_fetching(tmp_path):
    args = _args(tmp_path)
    args.state.parent.mkdir(parents=True)
    args.state.write_text("{", encoding="utf-8")
    fetch = Fetcher({"01": LIST, "02": EMPTY})
    code, result = cli.run(args, fetch, now=MON, sleeper=lambda s: None)
    assert code == cli.EXIT_STATE and fetch.calls == []
    args.state.write_text(json.dumps({"schema": "other"}), encoding="utf-8")
    assert cli.run(args, fetch, now=MON, sleeper=lambda s: None)[0] == cli.EXIT_STATE


def test_missed_week_and_over_probe_flags(tmp_path):
    args = _baseline(tmp_path)
    (args.dest / "_state.json").write_text(json.dumps({"done": [], "probed": [127800, 136220], "empty": []}))
    later = datetime(2026, 12, 14, 7, 30, tzinfo=CT)
    _, result = cli.run(args, Fetcher({"01": LIST, "02": EMPTY}), now=later, sleeper=lambda s: None)
    assert result["missed_week"] is True
    assert result["probe_max_ntt_id"] == 136220
    assert result["max_list_ntt_id"] == 218147
    assert result["over_probe"] is True


def _run_log(args) -> list[dict]:
    path = args.dest / "_weekly" / "runs.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_quiet_week_is_logged_locally_without_notify(tmp_path):
    args = _baseline(tmp_path)
    _, result = cli.run(args, Fetcher({"01": LIST, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert result["notify"] is False and result["exit_code"] == cli.EXIT_OK
    log = _run_log(args)
    assert [entry["mode"] for entry in log] == ["init", "watch"]
    assert [entry["notify"] for entry in log] == [False, False]
    assert log[-1]["summary"].endswith("status=ok notify=no")
    assert log[-1]["date_ct"] == "2026-11-30T07:30:00-06:00"


def test_new_posts_warnings_and_failures_notify(tmp_path):
    args = _baseline(tmp_path)
    page = _with_rows(LIST, [_extra_row(220001, 253, "새회계법인")], 4)
    _, new = cli.run(args, Fetcher({"01": page, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert new["notify"] is True
    error = fss_b0000291.FetchError("HTTP 500", http_status=500, attempts=5, url="u")
    code, failed = cli.run(args, Fetcher({"01": error, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert code == cli.EXIT_FETCH and failed["notify"] is True
    log = _run_log(args)
    assert [entry["status"] for entry in log] == ["ok", "new", "fetch-error"]
    assert log[-1]["error"] == "HTTP 500" and log[-1]["exit_code"] == cli.EXIT_FETCH
    mismatch = page.replace("전체 <em>4</em>건", "전체 <em>5</em>건")
    _, warn = cli.run(args, Fetcher({"01": mismatch, "02": EMPTY}), now=NEXT_MON, sleeper=lambda s: None)
    assert warn["status"] == "warn" and warn["notify"] is True


def test_missed_week_alone_notifies(tmp_path):
    args = _baseline(tmp_path)
    later = datetime(2026, 12, 14, 7, 30, tzinfo=CT)
    code, result = cli.run(args, Fetcher({"01": LIST, "02": EMPTY}), now=later, sleeper=lambda s: None)
    assert code == cli.EXIT_OK and result["missed_week"] is True and result["notify"] is True


def test_dry_run_does_not_append_the_run_log(tmp_path):
    args = _args(tmp_path, "--dry-run")
    _, result = cli.run(args, Fetcher({"01": LIST, "02": EMPTY}), now=MON, sleeper=lambda s: None)
    assert "notify" in result
    assert not (args.dest / "_weekly" / "runs.jsonl").exists()


def test_history_keeps_twelve_runs(tmp_path):
    args = _baseline(tmp_path)
    for week in range(14):
        now = datetime(2027, 1, 1 + week, 7, 30, tzinfo=CT)
        cli.run(args, Fetcher({"01": LIST, "02": EMPTY}), now=now, sleeper=lambda s: None)
    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert len(state["history"]) == watch.HISTORY_KEEP


def test_atomic_write_keeps_the_old_file_on_failure(tmp_path, monkeypatch):
    target = tmp_path / "state.json"
    target.write_text("old", encoding="utf-8")

    def boom(src, dst):
        raise OSError("disk")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        watch.atomic_write(target, "new")
    assert target.read_text(encoding="utf-8") == "old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json"]


def test_state_text_is_stable():
    state = watch.empty_state()
    assert watch.state_text(state) == watch.state_text(json.loads(watch.state_text(state)))
    assert watch.state_text(state).endswith("\n")


# --- 재시도 (#117 fetch_bytes 재사용) ---


class _Response:
    def __init__(self, status: int, content: bytes = b"ok"):
        self.status_code = status
        self.content = content


class _Session:
    def __init__(self, statuses: list[int]):
        self.statuses = list(statuses)
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        return _Response(self.statuses.pop(0))


def test_forbidden_is_retried_twice_only():
    session = _Session([403, 403, 200])
    with pytest.raises(fss_b0000291.FetchError) as info:
        fss_b0000291.fetch_bytes(session, watch.list_url(), sleeper=lambda s: None)
    assert info.value.http_status == 403 and session.calls == 2


def test_server_errors_back_off_five_times():
    session = _Session([500] * 5)
    sleeps = []
    with pytest.raises(fss_b0000291.FetchError):
        fss_b0000291.fetch_bytes(session, watch.list_url(), sleeper=sleeps.append)
    assert session.calls == 5 and len(sleeps) == 4


# --- CLI ---


def test_main_prints_summary_and_writes_report(tmp_path, capsys):
    report = tmp_path / "out" / "report.json"
    code = cli.main(
        ["--dest", str(tmp_path / "dest"), "--init", "--report", str(report)],
        fetch_text=Fetcher({"01": LIST, "02": EMPTY}),
        now=MON,
        sleeper=lambda s: None,
    )
    assert code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[-1] == "total=3 new=0 changed=0 missing=0 status=ok notify=no"
    assert json.loads(report.read_text(encoding="utf-8"))["mode"] == "init"


def test_cli_rejects_unknown_tab_and_bad_pages(tmp_path):
    with pytest.raises(SystemExit):
        cli.parse_args(["--tabs", "03"])
    with pytest.raises(SystemExit):
        cli.parse_args(["--max-pages", "0"])
    args = cli.parse_args(["--dest", str(tmp_path)])
    assert args.state == tmp_path / "_list-state.json"
    assert args.tabs == ["01", "02"]
