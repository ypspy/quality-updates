# -*- coding: utf-8 -*-
"""금융감독원 게시판 B0000291 공개 목록(list.do)에서 새 글을 감지한다.

목록만 읽는다. view.do 본문과 첨부는 받지 않는다(일회 입수는 ``crawl_fss_b0000291.py --seed``로 따로).
요청은 탭마다 최대 ``max_pages``번이고 재시도·백오프는 #117 ``fetch_bytes``를 그대로 쓴다.
"""
from __future__ import annotations

import html as html_lib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from crawler import fss_b0000291

STATE_SCHEMA = "fss-b0000291-list-state/1"
HISTORY_KEEP = 12
DEFAULT_PAGE_UNIT = 300
# 탭 코드 → menuNo. 01 개선권고사항, 02 이행 여부 확인 탭. TAB_NAMES 값은 게시판 원문 탭 이름이다.
TABS = {"01": "200620", "02": "200621"}
TAB_NAMES = {"01": "개선권고사항", "02": "개선권고 미이행사실"}
_TOTAL = re.compile(r"전체\s*<em>\s*([\d,]+)\s*</em>\s*건")
_PAGES = re.compile(r"페이지\s*<em>\s*(\d+)\s*</em>\s*/\s*(\d+)")


class ListParseError(ValueError):
    """목록 화면을 읽지 못함(구조 바뀜, 빈 응답 등)."""


@dataclass(frozen=True)
class Row:
    ntt_id: int
    no: str
    firm: str
    period: str
    action_date: str
    files: tuple[str, ...]

    def to_state(self) -> dict:
        return {
            "no": self.no,
            "firm": self.firm,
            "period": self.period,
            "action_date": self.action_date,
            "files": list(self.files),
        }


@dataclass(frozen=True)
class ListPage:
    total: int
    page: int
    pages: int
    rows: tuple[Row, ...]


@dataclass
class Report:
    tab: str
    total: int
    rows: int
    new: list[dict] = field(default_factory=list)
    changed: list[dict] = field(default_factory=list)
    missing: list[dict] = field(default_factory=list)
    count_mismatch: bool = False
    total_drop: bool = False
    previous_total: int | None = None

    def to_dict(self) -> dict:
        return {
            "tab": self.tab,
            "tab_name": TAB_NAMES.get(self.tab, self.tab),
            "total": self.total,
            "previous_total": self.previous_total,
            "rows": self.rows,
            "new": self.new,
            "changed": self.changed,
            "missing": self.missing,
            "count_mismatch": self.count_mismatch,
            "total_drop": self.total_drop,
        }


def list_url(tab: str = "01", page_index: int = 1, page_unit: int = DEFAULT_PAGE_UNIT) -> str:
    if tab not in TABS:
        raise ValueError(f"unknown tab {tab}")
    return (
        f"{fss_b0000291.ORIGIN}/fss/bbs/{fss_b0000291.BOARD}/list.do"
        f"?menuNo={TABS[tab]}&pageIndex={page_index}&cl1Cd={tab}&pageUnit={page_unit}"
    )


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node is not None else ""


def _ntt_id(href: str) -> int | None:
    values = parse_qs(urlparse(html_lib.unescape(href)).query).get("nttId")
    if not values or not values[0].isdigit():
        return None
    return int(values[0])


def parse_list(text: str) -> ListPage:
    """list.do 화면을 읽는다. 공지 행은 뺀다. 형식이 다르면 ``ListParseError``."""
    total_match = _TOTAL.search(text)
    if total_match is None:
        raise ListParseError("전체 건수 문구가 없습니다.")
    total = int(total_match.group(1).replace(",", ""))
    pages_match = _PAGES.search(text)
    page, pages = (int(pages_match.group(1)), int(pages_match.group(2))) if pages_match else (1, 1)
    soup = BeautifulSoup(text, "html.parser")
    table = soup.select_one("table.list-data")
    if table is None or table.tbody is None:
        raise ListParseError("목록 표가 없습니다.")
    rows: list[Row] = []
    empty_row = False
    for tr in table.tbody.find_all("tr", recursive=False):
        classes = tr.get("class") or []
        cells = tr.find_all("td", recursive=False)
        if any(cell.get("colspan") for cell in cells) and "nodata" in " ".join(
            " ".join(cell.get("class") or []) for cell in cells
        ):
            empty_row = True
            continue
        no = _text(cells[0]) if cells else ""
        if "notice" in classes or no == "공지":
            continue
        if len(cells) < 4:
            raise ListParseError("목록 행의 칸 수가 모자랍니다.")
        link = cells[1].find("a", href=True)
        ntt_id = _ntt_id(link["href"]) if link else None
        if ntt_id is None:
            raise ListParseError("nttId가 없는 목록 행이 있습니다.")
        files = tuple(
            _text(span) for span in tr.select("ul.list-board-attach-file span.name") if _text(span)
        )
        rows.append(
            Row(
                ntt_id=ntt_id,
                no=no,
                firm=_text(cells[1]),
                period=_text(cells[2]),
                action_date=_text(cells[3]),
                files=files,
            )
        )
    if not rows and not (total == 0 and empty_row):
        raise ListParseError("목록 행이 없습니다.")
    if rows and empty_row:
        raise ListParseError("자료 없음 행과 목록 행이 함께 있습니다.")
    return ListPage(total=total, page=page, pages=pages, rows=tuple(rows))


def empty_state() -> dict:
    return {"schema": STATE_SCHEMA, "last_run_ct": None, "last_ok_ct": None, "tabs": {}, "history": []}


def load_state(path: Path) -> dict:
    if not path.is_file():
        return empty_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"상태 파일을 읽지 못했습니다: {path}") from exc
    if not isinstance(data, dict) or data.get("schema") != STATE_SCHEMA:
        raise ValueError("상태 파일 형식이 아닙니다.")
    if not isinstance(data.get("tabs"), dict) or not isinstance(data.get("history"), list):
        raise ValueError("상태 파일 형식이 아닙니다.")
    return data


def state_text(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    )
    try:
        with handle:
            handle.write(text)
        os.replace(handle.name, path)
    except BaseException:
        try:
            os.unlink(handle.name)
        except FileNotFoundError:
            pass
        raise


def diff_tab(tab_state: dict | None, tab: str, rows: list[Row], total: int) -> Report:
    """지난 상태와 이번 목록을 비교한다. 상태는 바꾸지 않는다."""
    known = (tab_state or {}).get("known", {})
    previous_total = (tab_state or {}).get("total_count")
    report = Report(tab=tab, total=total, rows=len(rows), previous_total=previous_total)
    seen: set[str] = set()
    for row in rows:
        key = str(row.ntt_id)
        seen.add(key)
        current = row.to_state()
        before = known.get(key)
        if before is None:
            report.new.append({"nttId": row.ntt_id, **current, "url": view_url(tab, row.ntt_id)})
            continue
        fields = [name for name in ("firm", "period", "action_date", "files") if before.get(name) != current[name]]
        if fields:
            report.changed.append(
                {
                    "nttId": row.ntt_id,
                    "fields": fields,
                    "before": {name: before.get(name) for name in fields},
                    "after": {name: current[name] for name in fields},
                }
            )
    for key, before in sorted(known.items(), key=lambda item: int(item[0])):
        if key not in seen and not before.get("missing_since"):
            report.missing.append({"nttId": int(key), "firm": before.get("firm", "")})
    report.count_mismatch = total != len(rows)
    report.total_drop = previous_total is not None and total < previous_total
    return report


def view_url(tab: str, ntt_id: int) -> str:
    return (
        f"{fss_b0000291.ORIGIN}/fss/bbs/{fss_b0000291.BOARD}/view.do"
        f"?nttId={ntt_id}&menuNo={TABS[tab]}&cl1Cd={tab}"
    )


def apply_tab(state: dict, tab: str, rows: list[Row], total: int, now_ct: str) -> None:
    """정상 실행 결과를 상태에 반영한다."""
    tab_state = state["tabs"].setdefault(tab, {"known": {}, "total_count": None, "max_ntt_id": None})
    known = tab_state["known"]
    seen = set()
    for row in rows:
        key = str(row.ntt_id)
        seen.add(key)
        entry = known.get(key, {"first_seen_ct": now_ct})
        entry.update(row.to_state())
        entry.pop("missing_since", None)
        known[key] = entry
    for key, entry in known.items():
        if key not in seen and not entry.get("missing_since"):
            entry["missing_since"] = now_ct
    tab_state["total_count"] = total
    ids = [int(key) for key in known]
    tab_state["max_ntt_id"] = max(ids) if ids else None


def push_history(state: dict, now_ct: str, reports: list[Report]) -> None:
    state["history"].append(
        {
            "date_ct": now_ct,
            "tabs": {
                r.tab: {"total": r.total, "new": len(r.new), "changed": len(r.changed), "missing": len(r.missing)}
                for r in reports
            },
        }
    )
    del state["history"][:-HISTORY_KEEP]


def probe_max(dest: Path) -> int | None:
    """#117 ``_state.json``(숨은 2022 탐색)의 probed 최댓값."""
    path = dest / "_state.json"
    if not path.is_file():
        return None
    try:
        probed = json.loads(path.read_text(encoding="utf-8")).get("probed") or []
        return max(int(item) for item in probed) if probed else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
