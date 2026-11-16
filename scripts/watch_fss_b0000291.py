# -*- coding: utf-8 -*-
"""B0000291 공개 목록에서 새 글을 감지한다(주간 감지기). 첨부는 받지 않는다.

종료 코드: 0 정상·새 글 없음, 10 새 글 또는 변경, 20 경고(사라짐·총건수 감소·건수 불일치),
2 접속 실패, 3 403·차단, 4 목록 구문 분석 실패, 5 상태 파일 오류.
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


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="B0000291 목록(list.do) 새 글 감지. 첨부는 받지 않는다.")
    parser.add_argument("--dest", type=Path, default=None, help="기본 downloads/fss-review/B0000291")
    parser.add_argument("--state", type=Path, default=None, help="기본 <dest>/_list-state.json")
    parser.add_argument("--init", action="store_true", help="기준선: 새 글을 알리지 않고 known을 채운다")
    parser.add_argument("--dry-run", action="store_true", help="상태·주간 보고·HTML을 쓰지 않는다(--report만 씀)")
    parser.add_argument("--report", type=Path, default=None, help="JSON 보고를 이 경로에도 쓴다")
    parser.add_argument("--delay", type=float, default=fss_b0000291.DEFAULT_DELAY)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--tabs", default="01,02", help="감시할 탭 코드(쉼표). 01 개선권고사항, 02 미이행사실")
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


def run(args, fetch_text, *, now=None, sleeper=time.sleep) -> tuple[int, dict]:
    stamp = _now_ct(now)
    now_ct = stamp.isoformat(timespec="seconds")
    day = stamp.strftime("%Y-%m-%d")
    weekly = args.dest / "_weekly"
    result: dict = {"date_ct": now_ct, "mode": "init" if args.init else "watch", "dry_run": args.dry_run}
    try:
        state = watch.load_state(args.state)
    except ValueError as exc:
        result.update(status="state-error", error=str(exc))
        return EXIT_STATE, result
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
                watch.atomic_write(saved, getattr(exc, "html", ""))
                result["saved_html"] = str(saved)
            return EXIT_PARSE, result
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
            return (EXIT_FORBIDDEN if forbidden else EXIT_FETCH), result
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
    if not args.dry_run:
        for tab, (rows, total) in fetched.items():
            watch.apply_tab(state, tab, rows, total, now_ct)
        state["last_run_ct"] = now_ct
        state["last_ok_ct"] = now_ct
        watch.push_history(state, now_ct, reports)
        watch.atomic_write(args.state, watch.state_text(state))
        watch.atomic_write(weekly / f"{day}.json", json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    return code, result


def summary_line(result: dict) -> str:
    tabs = result.get("tabs") or []
    total = sum(item["total"] for item in tabs)
    new = sum(len(item["new"]) for item in tabs)
    changed = sum(len(item["changed"]) for item in tabs)
    missing = sum(len(item["missing"]) for item in tabs)
    return f"total={total} new={new} changed={changed} missing={missing} status={result.get('status')}"


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
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(summary_line(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
