# -*- coding: utf-8 -*-
"""B0000291 공개 목록에서 새 글을 감지한다(주간 감지기). 첨부는 받지 않는다.

종료 코드: 0 정상·새 글 없음, 10 새 글 또는 변경, 20 경고(사라짐·총건수 감소·건수 불일치),
2 접속 실패, 3 403·차단, 4 목록 구문 분석 실패, 5 상태 파일 오류,
6 기준선 없음(먼저 --init) 또는 기준선이 있는데 --force 없이 --init,
7 보고·상태 쓰기 실패(상태는 바뀌지 않음).

쓰기 순서: --report → `_weekly/YYYY-MM-DD.json` → `runs.jsonl` → 상태 파일(마지막).
보고 쓰기가 실패하면 상태를 바꾸지 않으므로 다음 실행이 같은 새 글을 다시 잡는다.

알림(D19): 결과의 `notify`는 새 글·변경, 경고(사라짐·총건수 감소·건수 불일치·8일 넘은 공백),
실패일 때만 참이다. 조용한 주는 `notify=false`이고 로컬 기록만 남는다.
dry-run이 아니면 실행마다(실패 포함) `<dest>/_weekly/runs.jsonl`에 한 줄을 덧붙인다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crawler import fss_b0000291  # noqa: E402
from crawler import fss_b0000291_list as watch  # noqa: E402

CT = ZoneInfo("America/Chicago")
EXIT_OK = 0
EXIT_NEW = 10
EXIT_WARN = 20
EXIT_FETCH = 2
EXIT_FORBIDDEN = 3
EXIT_PARSE = 4
EXIT_STATE = 5
EXIT_BASELINE = 6
EXIT_WRITE = 7


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="B0000291 목록(list.do) 새 글 감지. 첨부는 받지 않는다.")
    parser.add_argument("--dest", type=Path, default=None, help="기본 downloads/fss-review/B0000291")
    parser.add_argument("--state", type=Path, default=None, help="기본 <dest>/_list-state.json")
    parser.add_argument("--init", action="store_true", help="기준선: 새 글을 알리지 않고 known을 채운다")
    parser.add_argument(
        "--force", action="store_true", help="기준선이 이미 있어도 --init으로 덮어쓴다(새 글을 알리지 않고 흡수함)"
    )
    parser.add_argument("--dry-run", action="store_true", help="상태·주간 보고·HTML을 쓰지 않는다(--report만 씀)")
    parser.add_argument("--report", type=Path, default=None, help="JSON 보고를 이 경로에도 쓴다")
    parser.add_argument("--delay", type=float, default=fss_b0000291.DEFAULT_DELAY)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--tabs", default="01,02", help="감시할 탭 코드(쉼표). 01 개선권고사항, 02 이행 여부 확인 탭")
    args = parser.parse_args(argv)
    if args.dest is None:
        args.dest = fss_b0000291.default_dest()
    if args.state is None:
        args.state = args.dest / "_list-state.json"
    args.tabs = [tab.strip() for tab in args.tabs.split(",") if tab.strip()]
    for tab in args.tabs:
        if tab not in watch.TABS:
            parser.error(f"unknown tab {tab}")
    if args.max_pages < 1:
        parser.error("--max-pages must be >= 1")
    if args.force and not args.init:
        parser.error("--force is only valid with --init")
    return args


def _now_ct(now=None) -> datetime:
    return (now or datetime.now(CT)).astimezone(CT)


def _read_tab(tab: str, fetch_text, *, max_pages: int, pause) -> tuple[list, int, str]:
    """한 탭의 목록을 최대 max_pages쪽까지 읽는다. (행, 전체 건수, 마지막 HTML)."""
    rows: list = []
    seen: set[int] = set()
    text = ""
    total = 0
    for page_index in range(1, max_pages + 1):
        if page_index > 1:
            pause()
        text = fetch_text(watch.list_url(tab, page_index))
        try:
            page = watch.parse_list(text)
        except watch.ListParseError as exc:
            exc.html = text
            raise
        total = page.total
        for row in page.rows:
            if row.ntt_id not in seen:
                seen.add(row.ntt_id)
                rows.append(row)
        if len(rows) >= total or page_index >= page.pages or not page.rows:
            break
    return rows, total, text


def _report_text(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=1) + "\n"


def run(args, fetch_text, *, now=None, sleeper=time.sleep) -> tuple[int, dict]:
    """감지 1회. 보고를 모두 쓴 뒤에만 상태를 저장한다(실패한 실행은 다음에 다시 잡힘)."""
    code, result, new_state = _run(args, fetch_text, now=now, sleeper=sleeper)
    result["exit_code"] = code
    result["notify"] = needs_notify(code, result)
    run_log = args.dest / "_weekly" / "runs.jsonl"
    logged = False
    try:
        if args.report is not None:
            watch.atomic_write(args.report, _report_text(result))
        if not args.dry_run:
            if new_state is not None:
                day = result["date_ct"][:10]
                watch.atomic_write(args.dest / "_weekly" / f"{day}.json", _report_text(result))
            append_run_log(run_log, result)
            logged = True
            if new_state is not None:
                watch.atomic_write(args.state, watch.state_text(new_state))
    except OSError as exc:
        code = EXIT_WRITE
        result.update(status="write-error", error=f"보고·상태 쓰기 실패(상태는 바뀌지 않음): {exc}")
        result["exit_code"] = code
        result["notify"] = needs_notify(code, result)
        if not args.dry_run and not logged:
            try:
                append_run_log(run_log, result)
            except OSError:
                pass
        if args.report is not None:
            try:
                watch.atomic_write(args.report, _report_text(result))
            except OSError:
                pass
    return code, result


def needs_notify(code: int, result: dict) -> bool:
    """D19: 새 글·변경·경고·실패만 알린다. 조용한 주와 기준선 성공은 로컬 기록만."""
    if code in (EXIT_FETCH, EXIT_FORBIDDEN, EXIT_PARSE, EXIT_STATE, EXIT_BASELINE, EXIT_WRITE, EXIT_WARN):
        return True
    if result.get("missed_week") or result.get("warnings"):
        return True
    return code == EXIT_NEW


def append_run_log(path: Path, result: dict) -> None:
    """실행 한 줄을 JSON Lines로 덧붙인다(로컬 전용, git 밖)."""
    entry = {
        "date_ct": result.get("date_ct"),
        "mode": result.get("mode"),
        "status": result.get("status"),
        "exit_code": result.get("exit_code"),
        "notify": result.get("notify"),
        "summary": summary_line(result),
    }
    if result.get("error"):
        entry["error"] = result["error"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def _baseline_problem(args, state: dict) -> str | None:
    """기준선 규칙. 문제가 있으면 사람이 읽을 이유를, 없으면 None."""
    has_baseline = bool(state.get("last_ok_ct"))
    missing_tabs = [tab for tab in args.tabs if tab not in state["tabs"]]
    if args.init:
        if has_baseline and not args.force:
            return (
                f"기준선이 이미 있습니다({args.state}, last_ok_ct={state.get('last_ok_ct')}). "
                "--init은 새 글을 알리지 않고 흡수하므로 정말 다시 만들려면 --init --force를 쓰세요."
            )
        return None
    if not has_baseline:
        return (
            f"기준선이 없습니다({args.state}). 첫 실행은 모든 글을 새 글로 알리므로 거부합니다. "
            "먼저 --init으로 기준선을 만드세요(미리 보기는 --init --dry-run)."
        )
    if missing_tabs:
        return (
            f"기준선에 탭 {','.join(missing_tabs)}이(가) 없습니다({args.state}). "
            "--init --force로 기준선을 다시 만들거나 --tabs에서 빼세요."
        )
    return None


def _run(args, fetch_text, *, now=None, sleeper=time.sleep) -> tuple[int, dict, dict | None]:
    """목록을 읽고 판정한다. 파일은 쓰지 않고, 저장할 새 상태를 돌려준다(실패·dry-run이면 None).

    예외: 구문 분석 실패 때 받은 HTML 사본(`_weekly/YYYY-MM-DD-{탭}.html`)은 여기서 쓴다(실패해도 무시).
    """
    stamp = _now_ct(now)
    now_ct = stamp.isoformat(timespec="seconds")
    day = stamp.strftime("%Y-%m-%d")
    weekly = args.dest / "_weekly"
    result: dict = {"date_ct": now_ct, "mode": "init" if args.init else "watch", "dry_run": args.dry_run}
    try:
        state = watch.load_state(args.state)
    except (ValueError, OSError) as exc:
        result.update(status="state-error", error=str(exc))
        return EXIT_STATE, result, None
    problem = _baseline_problem(args, state)
    if problem is not None:
        result.update(status="no-baseline" if not args.init else "baseline-exists", error=problem)
        return EXIT_BASELINE, result, None
    previous_ok = state.get("last_ok_ct")
    if previous_ok:
        gap = stamp - datetime.fromisoformat(previous_ok)
        result["missed_week"] = gap.days > 8
    reports = []
    fetched: dict[str, tuple[list, int]] = {}
    for index, tab in enumerate(args.tabs):
        if index:
            sleeper(args.delay)
        try:
            rows, total, _ = _read_tab(
                tab, fetch_text, max_pages=args.max_pages, pause=lambda: sleeper(args.delay)
            )
        except watch.ListParseError as exc:
            result.update(status="parse-error", tab=tab, error=str(exc))
            if not args.dry_run:
                saved = weekly / f"{day}-{tab}.html"
                try:
                    watch.atomic_write(saved, getattr(exc, "html", ""))
                    result["saved_html"] = str(saved)
                except OSError as write_exc:
                    result["saved_html_error"] = str(write_exc)
            return EXIT_PARSE, result, None
        except fss_b0000291.FetchError as exc:
            forbidden = exc.http_status == 403
            result.update(
                status="forbidden" if forbidden else "fetch-error",
                tab=tab,
                error=str(exc),
                http_status=exc.http_status,
                attempts=exc.attempts,
                certificate=fss_b0000291._certificate_failure(exc.__cause__ or exc),
            )
            return (EXIT_FORBIDDEN if forbidden else EXIT_FETCH), result, None
        fetched[tab] = (rows, total)
        reports.append(watch.diff_tab(state["tabs"].get(tab), tab, rows, total))
    result["tabs"] = [report.to_dict() for report in reports]
    probe = watch.probe_max(args.dest)
    max_list = max((row.ntt_id for rows, _ in fetched.values() for row in rows), default=None)
    result["max_list_ntt_id"] = max_list
    result["probe_max_ntt_id"] = probe
    result["over_probe"] = bool(probe is not None and max_list is not None and max_list > probe)
    if args.init:
        code = EXIT_OK
        for item in result["tabs"]:
            item["baseline"] = len(item["new"])
            item["new"] = []
    elif any(r.new or r.changed for r in reports):
        code = EXIT_NEW
    elif any(r.missing or r.total_drop or r.count_mismatch for r in reports):
        code = EXIT_WARN
    else:
        code = EXIT_OK
    if code == EXIT_NEW and any(r.missing or r.total_drop or r.count_mismatch for r in reports):
        result["warnings"] = True
    result["status"] = {EXIT_OK: "ok", EXIT_NEW: "new", EXIT_WARN: "warn"}[code]
    if args.dry_run:
        return code, result, None
    for tab, (rows, total) in fetched.items():
        watch.apply_tab(state, tab, rows, total, now_ct)
    state["last_run_ct"] = now_ct
    state["last_ok_ct"] = now_ct
    watch.push_history(state, now_ct, reports)
    return code, result, state


def summary_line(result: dict) -> str:
    tabs = result.get("tabs") or []
    total = sum(item["total"] for item in tabs)
    new = sum(len(item["new"]) for item in tabs)
    changed = sum(len(item["changed"]) for item in tabs)
    missing = sum(len(item["missing"]) for item in tabs)
    notify = "yes" if result.get("notify") else "no"
    return (
        f"total={total} new={new} changed={changed} missing={missing} "
        f"status={result.get('status')} notify={notify}"
    )


def main(argv=None, *, fetch_text=None, now=None, sleeper=time.sleep) -> int:
    args = parse_args(argv)
    if fetch_text is None:
        session = fss_b0000291.make_session()

        def fetch_text(url: str) -> str:
            try:
                return fss_b0000291.fetch_bytes(session, url).decode("utf-8")
            except UnicodeDecodeError as exc:
                raise fss_b0000291.FetchError(str(exc), http_status=None, attempts=1, url=url) from exc

    code, result = run(args, fetch_text, now=now, sleeper=sleeper)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(summary_line(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
