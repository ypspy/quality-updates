# -*- coding: utf-8 -*-
"""회계기준위원회 회의록·의안 수집기.

질의회신 수집기(kasb_replies)와 목록 크롤러(KASB.py)를 import하지 않는다.
인자가 없으면 안내 후 끝난다. --dry-run은 묶음 HTML만 읽고 소켓을 열지 않는다.
실사이트 수집은 --live와 함께 --limit 또는 --seq가 있을 때만 가능하다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

LIST_URL = "https://www.kasb.or.kr/front/board/calListA.do"
VIEW_URL = "https://www.kasb.or.kr/front/board/calView.do"
VIEW_B_URL = "https://www.kasb.or.kr/front/board/calViewB.do"
MEET_URL = "https://www.kasb.or.kr/front/board/calmeetView.do"
DOWNLOAD_URL = "https://www.kasb.or.kr/commonFile/fileDownload.do"
SITE_CD = "002000000000000"
COMMITTEE = "회계기준위원회"
MAX_LIST_PAGES = 200

_DETAIL_RE = re.compile(r"fn_Detail\s*\(\s*'(\d+)'")
_FILE_RE = re.compile(
    r"fileDownload\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_YEAR_ROUND_RE = re.compile(r"(\d{4})\s*년\s*제\s*(\d+)\s*회")
_ROUND_RE = re.compile(r"제\s*(\d+)\s*회")
_SECTION_RE = re.compile(r"(의결\s*안건|보고\s*안건)")
_ITEM_RE = re.compile(r"제\s*\d+\s*호\s*\S.*")
_DISCLAIMER_RE = re.compile(
    r"(이 회의결과는 잠정적인 것으로.*|※\s*해당자료는.*)",
)
_BAD_NAME_RE = re.compile(r"[\x00-\x1f/\\]+")
_DONE_STATUS = {"saved", "meta_only"}


@dataclass(frozen=True)
class Attachment:
    name: str
    file_no: str
    file_seq: str
    role: str
    saved_name: str = ""


@dataclass(frozen=True)
class ScheduleRow:
    seq: str
    date: str
    category: str
    title: str
    place: str
    year: int | None
    round_no: int | None

    @property
    def is_committee(self) -> bool:
        return is_accounting_committee(self.category)


@dataclass
class ParsedPage:
    title: str = ""
    date: str | None = None
    place: str = ""
    category: str = ""
    decision_items: list[str] = field(default_factory=list)
    report_items: list[str] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)


@dataclass
class MeetingPlan:
    seq: str
    folder: str
    status: str
    title: str
    date: str
    year: int | None
    round_no: int | None
    place: str
    category: str
    decision_items: list[str]
    report_items: list[str]
    attachments: list[Attachment]
    meet_error: str = ""

    def line(self) -> str:
        return (
            f"seq={self.seq} folder={self.folder} status={self.status} "
            f"decision={len(self.decision_items)} report={len(self.report_items)} "
            f"attachments={len(self.attachments)}"
        )


def default_dest() -> Path:
    return Path(__file__).resolve().parents[2] / "downloads" / "kasb-meetings"


def default_fixture_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "kasb_meetings"


def is_accounting_committee(category: str) -> bool:
    return re.sub(r"\s+", "", category or "") == COMMITTEE


def first_date(value: str | None) -> str | None:
    match = _DATE_RE.search(value or "")
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def year_and_round(title: str, date: str | None) -> tuple[int | None, int | None]:
    match = _YEAR_ROUND_RE.search(title or "")
    if match:
        return int(match.group(1)), int(match.group(2))
    year = int(date[:4]) if date and len(date) >= 4 and date[:4].isdigit() else None
    round_match = _ROUND_RE.search(title or "")
    round_no = int(round_match.group(1)) if round_match else None
    return year, round_no


def folder_name(year: int | None, round_no: int | None) -> str:
    year_text = str(year) if year else "연도미상"
    round_text = f"{round_no}회" if round_no else "회차미상"
    return f"{year_text}-{COMMITTEE}-{round_text}"


def parse_schedule_rows(html: str) -> list[ScheduleRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[ScheduleRow] = []
    for tr in soup.select("table tbody tr"):
        cells = tr.find_all("td")
        if len(cells) < 5:
            continue
        link = None
        seq = None
        for anchor in cells[3].find_all("a"):
            match = _DETAIL_RE.search(anchor.get("onclick") or "")
            if match:
                link = anchor
                seq = match.group(1)
                break
        if link is None or seq is None:
            continue
        title = link.get_text(strip=True)
        date = first_date(cells[0].get_text(" ", strip=True))
        if not title or not date:
            continue
        year, round_no = year_and_round(title, date)
        rows.append(
            ScheduleRow(
                seq=seq,
                date=date,
                category=cells[2].get_text(strip=True),
                title=title,
                place=cells[4].get_text(strip=True),
                year=year,
                round_no=round_no,
            )
        )
    return rows


def parse_list_page(html: str) -> list[ScheduleRow]:
    """회계기준위원회 행만 돌려준다. 자문·지속가능성·세미나는 빠진다."""
    return [row for row in parse_schedule_rows(html) if row.is_committee]


def _labeled_cells(soup) -> dict:
    found = {}
    for th in soup.find_all("th"):
        label = re.sub(r"\s+", "", th.get_text(strip=True))
        td = th.find_next("td")
        if label and td is not None and label not in found:
            found[label] = td
    return found


def _cell_text(cells: dict, label: str) -> str:
    node = cells.get(label)
    if node is None:
        return ""
    return node.get_text(" ", strip=True)


def parse_agenda_sections(text: str) -> tuple[list[str], list[str]]:
    cleaned = _DISCLAIMER_RE.sub("", text or "")
    cleaned = cleaned.replace("\xa0", " ")
    parts = _SECTION_RE.split(cleaned)
    decision: list[str] = []
    report: list[str] = []
    current: list[str] | None = None
    for part in parts:
        compact = re.sub(r"\s+", "", part)
        if compact == "의결안건":
            current = decision
            continue
        if compact == "보고안건":
            current = report
            continue
        if current is None:
            continue
        chunks = re.split(r"[\n\r]+|·|•", part)
        for chunk in chunks:
            line = chunk.strip(" \t-:")
            line = re.sub(r"\s+", " ", line).strip()
            if not line:
                continue
            if "해당사항 없음" in line and not _ITEM_RE.search(line):
                if "해당사항 없음" not in current:
                    current.append("해당사항 없음")
                continue
            match = _ITEM_RE.search(line)
            if match:
                item = re.sub(r"\s+", " ", match.group(0)).strip()
                if item not in current:
                    current.append(item)
    return decision, report


def _attachments_in(node, role: str) -> list[Attachment]:
    if node is None:
        return []
    found: list[Attachment] = []
    for link in node.find_all("a"):
        match = _FILE_RE.search(link.get("onclick") or "")
        if not match:
            continue
        name = link.get_text(strip=True) or f"file-{match.group(2)}"
        item_role = "results" if ("회의결과" in name or "회의록" in name) else role
        found.append(
            Attachment(
                name=name,
                file_no=match.group(1),
                file_seq=match.group(2),
                role=item_role,
            )
        )
    return found


def _page_from_labels(html: str, *, attachment_role: str, title_labels: tuple[str, ...]) -> ParsedPage:
    soup = BeautifulSoup(html or "", "html.parser")
    cells = _labeled_cells(soup)
    body_node = soup.select_one(".board_view_cont")
    body = body_node.get_text("\n", strip=True) if body_node else ""
    if not body:
        body = _cell_text(cells, "내용")
    decision, report = parse_agenda_sections(body)
    title = ""
    for label in title_labels:
        title = _cell_text(cells, label)
        if title:
            break
    if not title:
        heading = soup.find(["h3", "h2"])
        title = heading.get_text(strip=True) if heading else ""
    page = ParsedPage(
        title=title,
        date=first_date(_cell_text(cells, "일시")),
        place=_cell_text(cells, "장소"),
        category=_cell_text(cells, "일정분류"),
        decision_items=decision,
        report_items=report,
        attachments=_attachments_in(cells.get("첨부파일"), attachment_role),
    )
    return page


def parse_view_page(html: str) -> ParsedPage:
    """calView / calViewB. 안건 제목과 의안 첨부 메타를 읽는다."""
    return _page_from_labels(html, attachment_role="agenda", title_labels=("일정명", "회의명"))


def parse_meet_page(html: str) -> ParsedPage:
    """calmeetView. 회의결과·회의록 첨부 메타를 읽는다."""
    page = _page_from_labels(html, attachment_role="results", title_labels=("회의명", "일정명"))
    page.attachments = [
        Attachment(item.name, item.file_no, item.file_seq, "results") for item in page.attachments
    ]
    return page


def richer_view(primary_html: str, secondary_html: str | None) -> str:
    primary = parse_view_page(primary_html)
    if primary.attachments or primary.decision_items or primary.report_items:
        return primary_html
    if not secondary_html:
        return primary_html
    secondary = parse_view_page(secondary_html)
    if secondary.attachments or secondary.decision_items or secondary.report_items:
        return secondary_html
    return primary_html


def _prefer(items: list[str], fallback: list[str]) -> list[str]:
    return items or fallback


def safe_filename(name: str, file_seq: str) -> str:
    cleaned = _BAD_NAME_RE.sub("", name or "").strip().strip(".")
    if not cleaned or cleaned in {".."}:
        return f"attachment-{file_seq}"
    return cleaned[:180]


def assign_saved_names(attachments: list[Attachment]) -> list[Attachment]:
    used: dict[str, set[str]] = {"agenda": set(), "results": set()}
    named: list[Attachment] = []
    seen: set[tuple[str, str]] = set()
    for item in attachments:
        key = (item.file_no, item.file_seq)
        if key in seen:
            continue
        seen.add(key)
        role = item.role if item.role in used else "agenda"
        base = safe_filename(item.name, item.file_seq)
        candidate = base
        number = 2
        while candidate in used[role]:
            stem = Path(base).stem
            suffix = Path(base).suffix
            candidate = f"{stem}-{number}{suffix}"
            number += 1
        used[role].add(candidate)
        named.append(Attachment(item.name, item.file_no, item.file_seq, role, candidate))
    return named


def build_plan(row: ScheduleRow, view: ParsedPage, meet: ParsedPage) -> MeetingPlan:
    title = row.title or view.title or meet.title
    date = view.date or row.date or meet.date or ""
    year, round_no = year_and_round(title, date or None)
    if year is None:
        year = row.year
    if round_no is None:
        round_no = row.round_no
    attachments = assign_saved_names([*view.attachments, *meet.attachments])
    status = "saved" if attachments else "meta_only"
    return MeetingPlan(
        seq=row.seq,
        folder=folder_name(year, round_no),
        status=status,
        title=title,
        date=date,
        year=year,
        round_no=round_no,
        place=view.place or row.place,
        category=view.category or row.category,
        decision_items=_prefer(view.decision_items, meet.decision_items),
        report_items=_prefer(view.report_items, meet.report_items),
        attachments=attachments,
    )


def compose_record(plan: MeetingPlan, fetched_at: str) -> str:
    meta = {
        "seq": plan.seq,
        "year": plan.year,
        "round": plan.round_no,
        "title": plan.title,
        "date": plan.date,
        "place": plan.place,
        "category": plan.category,
        "status": plan.status,
        "view_url": f"{VIEW_URL}?seq={plan.seq}",
        "meet_url": f"{MEET_URL}?seq={plan.seq}",
        "decision_items": plan.decision_items,
        "report_items": plan.report_items,
        "attachments": [
            {
                "name": item.saved_name,
                "source_name": item.name,
                "file_no": item.file_no,
                "file_seq": item.file_seq,
                "role": item.role,
            }
            for item in plan.attachments
        ],
        "fetched_at": fetched_at,
    }
    if plan.meet_error:
        meta["meet_error"] = plan.meet_error
    dumped = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    lines = ["---", dumped, "---", "", "## 의결 안건", ""]
    lines.extend(_bullet_lines(plan.decision_items))
    lines.extend(["", "## 보고 안건", ""])
    lines.extend(_bullet_lines(plan.report_items))
    lines.extend(["", "## 첨부", ""])
    if plan.attachments:
        for item in plan.attachments:
            lines.append(f"- {item.role}: {item.saved_name}")
    else:
        lines.append("- 없음")
    return "\n".join(lines).rstrip() + "\n"


def _bullet_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- 없음"]
    return [f"- {item}" for item in items]


def read_meta(path: Path) -> dict | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return meta if isinstance(meta, dict) else None


def empty_state() -> dict:
    return {"done": {}, "failed": {}}


def load_state(path: Path) -> dict:
    if not path.is_file():
        return empty_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return empty_state()
    if not isinstance(data, dict):
        return empty_state()
    data.setdefault("done", {})
    data.setdefault("failed", {})
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def find_meeting_dir(dest: Path, seq: str, state: dict) -> Path | None:
    for bucket in (state.get("done") or {}, state.get("failed") or {}):
        entry = bucket.get(seq) or {}
        folder = entry.get("folder")
        if folder and (dest / folder / "record.md").is_file():
            return dest / folder
    if not dest.is_dir():
        return None
    for record in dest.glob("*/record.md"):
        meta = read_meta(record)
        if meta and str(meta.get("seq")) == str(seq):
            return record.parent
    return None


def should_skip(dest: Path, state: dict, seq: str, retry_failed: bool) -> bool:
    done = (state.get("done") or {}).get(seq)
    if isinstance(done, dict) and done.get("status") in _DONE_STATUS:
        return True
    directory = find_meeting_dir(dest, seq, state)
    if directory is not None:
        meta = read_meta(directory / "record.md") or {}
        if meta.get("status") in _DONE_STATUS:
            return True
    failed = (state.get("failed") or {}).get(seq)
    if failed and not retry_failed:
        return True
    return False


def select_rows(
    rows: list[ScheduleRow],
    *,
    limit: int | None,
    seqs: set[str] | None,
) -> list[ScheduleRow]:
    chosen: list[ScheduleRow] = []
    seen: set[str] = set()
    for row in rows:
        if row.seq in seen:
            continue
        if seqs is not None and row.seq not in seqs:
            continue
        seen.add(row.seq)
        chosen.append(row)
        if limit is not None and len(chosen) >= limit:
            break
    return chosen


def gather_rows(
    fetch_page,
    *,
    limit: int | None,
    seqs: set[str] | None,
    scan: dict | None = None,
) -> list[ScheduleRow]:
    """fetch_page(page) -> html. 빈 목록이면 멈추고, limit에 닿으면 다음 쪽을 열지 않는다.

    scan을 주면 complete(다음 쪽을 열지 않고 멈췄으면 False)와 observed(이번 스캔에서 본 회계기준위원회 seq)를 채운다.
    limit에 닿아도 그 페이지의 나머지 행은 봐 두고, 다음 페이지는 열지 않는다.
    """
    found: list[ScheduleRow] = []
    seen: set[str] = set()
    observed: set[str] = set()
    wanted = set(seqs) if seqs else None
    complete = True
    for page in range(1, MAX_LIST_PAGES + 1):
        rows = parse_schedule_rows(fetch_page(page))
        if not rows:
            break
        fresh = [row for row in rows if row.seq not in seen]
        if not fresh:
            break
        hit_limit = False
        for row in fresh:
            seen.add(row.seq)
            if not row.is_committee:
                continue
            observed.add(row.seq)
            if wanted is not None and row.seq not in wanted:
                continue
            if limit is not None and len(found) >= limit:
                hit_limit = True
                continue
            found.append(row)
            if limit is not None and len(found) >= limit:
                hit_limit = True
        if hit_limit:
            complete = False
            break
        if wanted is not None and wanted.issubset({row.seq for row in found}):
            break
    if scan is not None:
        scan["complete"] = complete
        scan["observed"] = observed
    return found


def _now_stamp(now) -> str:
    moment = now() if now else datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.isoformat()


def _allocate_folder(dest: Path, plan: MeetingPlan) -> Path:
    path = dest / plan.folder
    record = path / "record.md"
    if record.is_file():
        meta = read_meta(record) or {}
        if str(meta.get("seq") or "") not in {"", plan.seq}:
            path = dest / f"{plan.folder}-seq{plan.seq}"
    return path


def collect(
    dest: Path,
    rows: list[ScheduleRow],
    *,
    fetch_view,
    fetch_meet,
    fetch_file,
    dry_run: bool = False,
    limit: int | None = None,
    seqs: set[str] | None = None,
    retry_failed: bool = False,
    now=None,
) -> dict:
    selected = select_rows(rows, limit=limit, seqs=seqs)
    state_path = dest / "_state.json"
    state = empty_state() if dry_run else load_state(state_path)
    counts = {"saved": 0, "meta_only": 0, "skipped": 0, "failed": 0, "planned": 0}
    plans: list[MeetingPlan] = []
    errors: list[str] = []
    for row in selected:
        if not dry_run and should_skip(dest, state, row.seq, retry_failed):
            counts["skipped"] += 1
            continue
        try:
            view = parse_view_page(fetch_view(row.seq))
            meet_error = None
            try:
                meet_html = fetch_meet(row.seq) or ""
            except Exception as exc:
                meet_error = _short_error(exc)
                meet_html = ""
            meet = parse_meet_page(meet_html)
            plan = build_plan(row, view, meet)
            if meet_error:
                plan.status = "partial"
                plan.meet_error = meet_error
            plans.append(plan)
            if dry_run:
                counts["planned"] += 1
                if meet_error:
                    counts["failed"] += 1
                    errors.append(f"seq={row.seq} meet_error={meet_error}")
                continue
            blobs: list[tuple[Attachment, bytes]] = []
            if plan.attachments:
                for item in plan.attachments:
                    blobs.append((item, fetch_file(item.file_no, item.file_seq)))
            folder = _allocate_folder(dest, plan)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "agenda").mkdir(exist_ok=True)
            (folder / "results").mkdir(exist_ok=True)
            for item, payload in blobs:
                (folder / item.role / item.saved_name).write_bytes(payload)
            text = compose_record(plan, _now_stamp(now))
            (folder / "record.md").write_text(text, encoding="utf-8")
            if meet_error:
                counts["failed"] += 1
                errors.append(f"seq={row.seq} meet_error={meet_error}")
                state["done"].pop(row.seq, None)
                state["failed"][row.seq] = {
                    "error": meet_error,
                    "folder": folder.name,
                    "status": "partial",
                }
                save_state(state_path, state)
            else:
                state["done"][row.seq] = {"status": plan.status, "folder": folder.name}
                state["failed"].pop(row.seq, None)
                save_state(state_path, state)
                counts[plan.status] += 1
        except Exception as exc:
            counts["failed"] += 1
            message = _short_error(exc)
            errors.append(f"seq={row.seq} error={message}")
            if dry_run:
                continue
            state["failed"][row.seq] = {"error": message, "folder": None}
            save_state(state_path, state)
    return {"counts": counts, "plans": plans, "state": state, "errors": errors}


def absent_lines(seqs: set[str] | None, found: set[str], *, scan_complete: bool) -> list[str]:
    """요청 seq 중 이번에 본 목록에 없는 것의 안내.

    목록을 끝까지 봤으면 missing=list 다. limit 때문에 다음 쪽을 열지 않았으면 missing=limit 다.
    """
    if not seqs:
        return []
    reason = "list" if scan_complete else "limit"
    return [f"seq={seq} missing={reason}" for seq in sorted(set(seqs) - set(found))]


def _note_absent(result: dict, lines: list[str]) -> None:
    for line in lines:
        result["counts"]["failed"] += 1
        result["errors"].append(line)
    result["missing"] = lines


def _short_error(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    return text[:500] or exc.__class__.__name__


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def dry_run_from_fixtures(
    fixture_dir: Path,
    *,
    limit: int | None,
    seqs: set[str] | None,
) -> dict:
    list_path = fixture_dir / "list.html"
    if not list_path.is_file():
        raise FileNotFoundError(f"fixture list missing: {list_path}")
    rows = parse_list_page(_read(list_path))

    def fetch_view(seq: str) -> str:
        path = fixture_dir / "view" / f"{seq}.html"
        if not path.is_file():
            raise FileNotFoundError(f"view fixture missing: {seq}")
        return _read(path)

    def fetch_meet(seq: str) -> str:
        path = fixture_dir / "meet" / f"{seq}.html"
        if not path.is_file():
            return ""
        return _read(path)

    result = collect(
        fixture_dir,
        rows,
        fetch_view=fetch_view,
        fetch_meet=fetch_meet,
        fetch_file=_refuse_download,
        dry_run=True,
        limit=limit,
        seqs=seqs,
    )
    _note_absent(
        result,
        absent_lines(seqs, {row.seq for row in rows}, scan_complete=True),
    )
    lines = [f"dry-run network=no meetings={len(result['plans'])}"]
    lines.extend(plan.line() for plan in result["plans"])
    lines.extend(result["errors"])
    result["lines"] = lines
    return result


def _refuse_download(file_no: str, file_seq: str) -> bytes:
    raise RuntimeError("dry-run does not download")


def make_session():
    import requests

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    session.get(LIST_URL, timeout=30)
    return session


def _response_text(response) -> str:
    encoding = (response.encoding or "").lower()
    if not encoding or encoding == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def http_fetch_list(session, page: int, start: str, end: str) -> str:
    response = session.post(
        LIST_URL,
        data={
            "siteCd": SITE_CD,
            "searchfield": "ALL",
            "searchword": "",
            "s_date_start": start,
            "s_date_end": end,
            "page": page,
        },
        timeout=30,
    )
    response.raise_for_status()
    return _response_text(response)


def _http_get(session, url: str, seq: str):
    return session.get(url, params={"seq": seq}, timeout=30)


def http_fetch_view(session, seq: str) -> str:
    primary = _http_get(session, VIEW_URL, seq)
    primary.raise_for_status()
    primary_html = _response_text(primary)
    parsed = parse_view_page(primary_html)
    if parsed.attachments or parsed.decision_items or parsed.report_items:
        return primary_html
    secondary = _http_get(session, VIEW_B_URL, seq)
    secondary.raise_for_status()
    return richer_view(primary_html, _response_text(secondary))


def http_fetch_meet(session, seq: str) -> str:
    response = _http_get(session, MEET_URL, seq)
    if response.status_code == 404:
        return ""
    response.raise_for_status()
    return _response_text(response)


def http_fetch_file(session, file_no: str, file_seq: str) -> bytes:
    response = session.post(
        DOWNLOAD_URL,
        data={"fileNo": file_no, "fileSeq": file_seq},
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def crawl_live(
    dest: Path,
    session,
    *,
    start: str,
    end: str,
    limit: int | None,
    seqs: set[str] | None,
    retry_failed: bool,
) -> dict:
    scan: dict = {}
    rows = gather_rows(
        lambda page: http_fetch_list(session, page, start, end),
        limit=limit,
        seqs=seqs,
        scan=scan,
    )
    result = collect(
        dest,
        rows,
        fetch_view=lambda seq: http_fetch_view(session, seq),
        fetch_meet=lambda seq: http_fetch_meet(session, seq),
        fetch_file=lambda file_no, file_seq: http_fetch_file(session, file_no, file_seq),
        dry_run=False,
        retry_failed=retry_failed,
    )
    observed = scan.get("observed", {row.seq for row in rows})
    _note_absent(
        result,
        absent_lines(seqs, observed, scan_complete=bool(scan.get("complete", True))),
    )
    return result


def _parse_seqs(values: list[str] | None) -> set[str] | None:
    if not values:
        return None
    seqs: set[str] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                seqs.add(part)
    return seqs or None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="회계기준위원회 회의록·의안 수집. 기본은 네트워크를 열지 않는다.",
    )
    parser.add_argument("--dry-run", action="store_true", help="묶음 HTML만 읽고 저장하지 않는다")
    parser.add_argument("--limit", type=int, default=None, help="처리할 회의 수")
    parser.add_argument("--seq", action="append", default=None, help="이 seq만. 쉼표로 여러 개")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="끝난 seq는 건너뛴다. 실패 seq는 다시 시도하고, 이번 선택에 들어온 새 seq도 받는다.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="실사이트 수집. 별도 승인 전 사용하지 않는다. --limit 또는 --seq가 필요하다",
    )
    parser.add_argument("--dest", type=Path, default=default_dest())
    parser.add_argument("--fixtures", type=Path, default=default_fixture_dir())
    parser.add_argument("--start", default="", help="live 목록 s_date_start")
    parser.add_argument("--end", default="", help="live 목록 s_date_end")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    seqs = _parse_seqs(args.seq)
    if args.live and args.dry_run:
        print("dry-run과 live는 함께 쓸 수 없습니다.", file=sys.stderr)
        return 2
    if args.limit is not None and args.limit < 1:
        print("--limit는 1 이상이어야 합니다.", file=sys.stderr)
        return 2
    if not args.live:
        if not args.dry_run:
            print(
                "오프라인입니다. 확인은 --dry-run, 실수집은 승인 후 --live --limit 또는 --seq 입니다.",
                file=sys.stderr,
            )
            return 2
        try:
            result = dry_run_from_fixtures(args.fixtures, limit=args.limit, seqs=seqs)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        for line in result["lines"]:
            print(line)
        return 1 if result["counts"]["failed"] else 0
    if args.limit is None and not seqs:
        print("실수집은 --limit 또는 --seq가 필요합니다. 전량은 돌리지 않습니다.", file=sys.stderr)
        return 2
    session = make_session()
    result = crawl_live(
        args.dest,
        session,
        start=args.start,
        end=args.end,
        limit=args.limit,
        seqs=seqs,
        retry_failed=args.retry_failed,
    )
    for line in result["errors"]:
        print(line)
    counts = result["counts"]
    print(
        "saved={saved} meta_only={meta_only} skipped={skipped} failed={failed}".format(**counts)
    )
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
