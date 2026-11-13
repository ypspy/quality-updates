# -*- coding: utf-8 -*-
"""금융감독원 게시판 B0000291에서 목록에 없는 2022년 글을 view.do로 받는다.

공개 목록은 2023년 이후만 보여 준다. 이 모듈은 list.do를 돌지 않는다.
첨부 .hwp/.hwpx는 변환하지 않고 그대로 저장한다. 노트북 백업 경로는 다루지 않는다.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ORIGIN = "https://www.fss.or.kr"
BOARD = "B0000291"
MENU_NO = "200620"
CL1_CD = "01"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_DELAY = 1.0
DEFAULT_RANGE = "127800-128800"
DEFAULT_COARSE_FROM = 128800
DEFAULT_COARSE_TO = 136220
DEFAULT_COARSE_STRIDE = 200
MAX_ATTEMPTS = 5
FORBIDDEN_ATTEMPTS = 2
BACKOFF_BASE = 1.0
BACKOFF_CAP = 30.0
SHORT_RETRY = 0.5
ANNUAL_MARK = "품질관리 감리대상"
_SIZE_RE = re.compile(r"\(파일크기:.*?\)")
_CONVERT_EXT = {".hwp", ".hwpx"}


class FetchError(Exception):
    def __init__(self, message: str, *, http_status: int | None, attempts: int, url: str):
        super().__init__(message)
        self.http_status = http_status
        self.attempts = attempts
        self.url = url


@dataclass(frozen=True)
class SeedRow:
    ntt_id: int
    action_date: str
    period: str
    firm: str
    kind: str
    attach: str
    disclose_end: str
    url: str


@dataclass(frozen=True)
class Attachment:
    name: str
    url: str
    ext: str


@dataclass(frozen=True)
class Post:
    ntt_id: int
    firm: str
    period: str
    action_date: str
    disclose_end: str
    kind: str
    attachments: tuple[Attachment, ...]

    def to_manifest(self) -> dict:
        return {
            "nttId": self.ntt_id,
            "firm": self.firm,
            "period": self.period,
            "action_date": self.action_date,
            "disclose_end": self.disclose_end,
            "kind": self.kind,
            "attachments": [
                {"name": item.name, "url": item.url, "ext": item.ext} for item in self.attachments
            ],
        }


def default_dest() -> Path:
    return Path(__file__).resolve().parents[2] / "downloads" / "fss-review" / BOARD


def view_url(ntt_id: int | str) -> str:
    return (
        f"{ORIGIN}/fss/bbs/{BOARD}/view.do"
        f"?nttId={ntt_id}&menuNo={MENU_NO}&cl1Cd={CL1_CD}"
    )


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    session.verify = True
    return session


def load_seed(path: Path) -> list[SeedRow]:
    rows: list[SeedRow] = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                SeedRow(
                    ntt_id=int(raw["nttId"]),
                    action_date=(raw.get("action_date") or "").strip(),
                    period=(raw.get("period") or "").strip(),
                    firm=(raw.get("firm") or "").strip(),
                    kind=(raw.get("kind") or "").strip(),
                    attach=(raw.get("attach") or "").strip(),
                    disclose_end=(raw.get("disclose_end") or "").strip(),
                    url=(raw.get("url") or "").strip(),
                )
            )
    return rows


def resolve_kind(firm: str, seed_kind: str | None) -> str:
    if seed_kind:
        return seed_kind
    if ANNUAL_MARK in firm:
        return "연간 종합본"
    return "업체별"


def parse_view(html: str, ntt_id: int, kind: str | None = None) -> Post | None:
    soup = BeautifulSoup(html, "html.parser")
    fields = _info_fields(soup)
    firm = fields.get("감사인", "").strip()
    if not firm:
        return None
    period = (fields.get("감시대상기간") or fields.get("감리대상기간") or "").strip()
    return Post(
        ntt_id=int(ntt_id),
        firm=firm,
        period=period,
        action_date=fields.get("개선권고일", "").strip(),
        disclose_end=fields.get("공시종료일", "").strip(),
        kind=resolve_kind(firm, kind),
        attachments=tuple(_attachments(soup)),
    )


def sweep_ids(
    range_spec: str,
    coarse_from: int = DEFAULT_COARSE_FROM,
    coarse_to: int = DEFAULT_COARSE_TO,
    coarse_stride: int = DEFAULT_COARSE_STRIDE,
) -> list[int]:
    start, end = _parse_range(range_spec)
    ids = list(range(start, end + 1))
    seen = set(ids)
    if coarse_stride <= 0:
        raise ValueError(f"coarse stride must be positive, got {coarse_stride}")
    if coarse_from <= coarse_to:
        for ntt_id in range(coarse_from, coarse_to + 1, coarse_stride):
            if ntt_id not in seen:
                ids.append(ntt_id)
                seen.add(ntt_id)
        if coarse_to not in seen:
            ids.append(coarse_to)
            seen.add(coarse_to)
    return ids


def fetch_bytes(
    session,
    url: str,
    *,
    sleeper=time.sleep,
    timeout: float = 30,
    max_attempts: int = MAX_ATTEMPTS,
    forbidden_attempts: int = FORBIDDEN_ATTEMPTS,
    backoff_base: float = BACKOFF_BASE,
    backoff_cap: float = BACKOFF_CAP,
    short_retry: float = SHORT_RETRY,
) -> bytes:
    attempt = 0
    while True:
        attempt += 1
        try:
            response = session.get(url, timeout=timeout)
        except requests.RequestException as exc:
            if _retryable_transport(exc) and attempt < max_attempts:
                sleeper(min(backoff_cap, backoff_base * (2 ** (attempt - 1))))
                continue
            raise FetchError(str(exc), http_status=None, attempts=attempt, url=url) from exc
        status = response.status_code
        if 500 <= status <= 599:
            if attempt < max_attempts:
                sleeper(min(backoff_cap, backoff_base * (2 ** (attempt - 1))))
                continue
            raise FetchError(f"HTTP {status}", http_status=status, attempts=attempt, url=url)
        if status == 403:
            if attempt < forbidden_attempts:
                sleeper(short_retry)
                continue
            raise FetchError("HTTP 403", http_status=403, attempts=attempt, url=url)
        if status >= 400:
            raise FetchError(f"HTTP {status}", http_status=status, attempts=attempt, url=url)
        return response.content


def http_fetch_text(session, ntt_id: int) -> str:
    return fetch_bytes(session, view_url(ntt_id)).decode("utf-8")


def http_fetch_file(session, url: str) -> bytes:
    return fetch_bytes(session, url)


def crawl_seed(
    seed: list[SeedRow],
    dest: Path,
    *,
    fetch_html,
    fetch_file,
    dry_run: bool = False,
    resume: bool = False,
    delay: float = DEFAULT_DELAY,
    sleeper=time.sleep,
) -> dict:
    dest = Path(dest)
    done, probed = _load_state(dest / "_state.json")
    failed = _load_keyed(dest / "_failed.jsonl", _failure_key)
    manifest = {row["nttId"]: row for row in _read_jsonl(dest / "manifest.jsonl")}
    pending = {
        (row["nttId"], row["name"]): row for row in _read_jsonl(dest / "_pending-conversion.jsonl")
    }
    summary = {"posts": 0, "attachments": 0, "empty": 0, "failed": 0}
    requested = False

    def pause() -> None:
        nonlocal requested
        if requested and delay > 0:
            sleeper(delay)
        requested = True

    def flush() -> None:
        _write_seed_ledger(dest, manifest, done, pending, failed, probed)

    for row in seed:
        if resume and row.ntt_id in done:
            continue
        pause()
        try:
            html = fetch_html(row.ntt_id)
        except FetchError as exc:
            summary["failed"] += 1
            if not dry_run:
                failed[_failure_key({"nttId": row.ntt_id})] = _failure_record(
                    row.ntt_id, exc, filename=None
                )
                flush()
            continue
        post = parse_view(html, row.ntt_id, kind=row.kind or None)
        if post is None:
            summary["empty"] += 1
            continue
        summary["posts"] += 1
        summary["attachments"] += len(post.attachments)
        if dry_run:
            continue
        error = _download_attachments(post, dest, fetch_file, pause, pending)
        if error is not None:
            attachment, exc = error
            summary["failed"] += 1
            failed[_failure_key({"nttId": post.ntt_id})] = _failure_record(
                post.ntt_id, exc, filename=attachment.name
            )
            flush()
            continue
        manifest[post.ntt_id] = post.to_manifest()
        done.add(post.ntt_id)
        failed.pop(_failure_key({"nttId": post.ntt_id}), None)
        flush()
    return summary


def crawl_sweep(
    dest: Path,
    *,
    seed: list[SeedRow],
    fetch_html,
    fetch_file,
    range_spec: str = DEFAULT_RANGE,
    coarse_from: int = DEFAULT_COARSE_FROM,
    coarse_to: int = DEFAULT_COARSE_TO,
    coarse_stride: int = DEFAULT_COARSE_STRIDE,
    dry_run: bool = False,
    resume: bool = False,
    sweep_download: bool = False,
    delay: float = DEFAULT_DELAY,
    sleeper=time.sleep,
) -> dict:
    dest = Path(dest)
    seed_ids = {row.ntt_id: row for row in seed}
    done, probed = _load_state(dest / "_state.json")
    records = {
        (row["type"], row["nttId"]): row for row in _read_jsonl(dest / "_sweep.jsonl")
    }
    manifest = {row["nttId"]: row for row in _read_jsonl(dest / "manifest.jsonl")}
    pending = {
        (row["nttId"], row["name"]): row for row in _read_jsonl(dest / "_pending-conversion.jsonl")
    }
    summary = {"new": 0, "empty": 0, "failed": 0}
    requested = False

    def pause() -> None:
        nonlocal requested
        if requested and delay > 0:
            sleeper(delay)
        requested = True

    def flush() -> None:
        dest.mkdir(parents=True, exist_ok=True)
        _write_jsonl(
            dest / "_sweep.jsonl",
            sorted(records.values(), key=lambda row: (row["nttId"], row["type"])),
        )
        _write_text_if_changed(dest / "_state.json", _state_text(done, probed))
        if sweep_download:
            _write_jsonl(
                dest / "manifest.jsonl",
                sorted(manifest.values(), key=lambda row: row["nttId"]),
            )
            _write_jsonl(
                dest / "_pending-conversion.jsonl",
                sorted(pending.values(), key=lambda row: (row["nttId"], row["name"])),
            )

    def finish(ntt_id: int) -> None:
        if dry_run:
            return
        probed.add(ntt_id)
        flush()

    for ntt_id in sweep_ids(range_spec, coarse_from, coarse_to, coarse_stride):
        if resume and (ntt_id in probed or ntt_id in done):
            continue
        pause()
        try:
            html = fetch_html(ntt_id)
        except FetchError as exc:
            summary["failed"] += 1
            records.pop(("post", ntt_id), None)
            records[("failure", ntt_id)] = _sweep_failure(ntt_id, exc, filename=None)
            finish(ntt_id)
            continue
        seed_row = seed_ids.get(ntt_id)
        post = parse_view(html, ntt_id, kind=seed_row.kind if seed_row else None)
        if post is None:
            summary["empty"] += 1
            records.pop(("post", ntt_id), None)
            records.pop(("failure", ntt_id), None)
            finish(ntt_id)
            continue
        if ntt_id in seed_ids:
            records.pop(("post", ntt_id), None)
            records.pop(("failure", ntt_id), None)
            finish(ntt_id)
            continue
        summary["new"] += 1
        records[("post", ntt_id)] = {"type": "post", **post.to_manifest()}
        records.pop(("failure", ntt_id), None)
        if dry_run or not sweep_download:
            finish(ntt_id)
            continue
        error = _download_attachments(post, dest, fetch_file, pause, pending)
        if error is not None:
            attachment, exc = error
            summary["failed"] += 1
            records[("failure", ntt_id)] = _sweep_failure(
                ntt_id, exc, filename=attachment.name
            )
            finish(ntt_id)
            continue
        manifest[post.ntt_id] = post.to_manifest()
        done.add(post.ntt_id)
        finish(ntt_id)
    return summary


def _info_fields(soup: BeautifulSoup) -> dict[str, str]:
    board = soup.select_one("dl.bd-info")
    if board is None:
        return {}
    fields: dict[str, str] = {}
    for dt in board.find_all("dt"):
        label = dt.get_text(strip=True)
        dd = dt.find_next_sibling("dd")
        fields[label] = "" if dd is None else dd.get_text(strip=True)
    return fields


def _attachments(soup: BeautifulSoup) -> list[Attachment]:
    found: list[Attachment] = []
    seen: set[str] = set()
    for link in soup.select("a.btn-attach-download"):
        href = (link.get("href") or "").strip()
        name = " ".join(_SIZE_RE.sub("", link.get_text(" ", strip=True)).split())
        if not href or not name:
            continue
        url = urljoin(ORIGIN, href)
        if url in seen:
            continue
        seen.add(url)
        found.append(Attachment(name=name, url=url, ext=Path(name).suffix.lower()))
    return found


def _parse_range(spec: str) -> tuple[int, int]:
    left, right = spec.split("-", 1)
    start, end = int(left), int(right)
    if end < start:
        raise ValueError(f"range end is before start: {spec}")
    return start, end


def _retryable_transport(exc: BaseException) -> bool:
    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return True
    text = str(exc).upper()
    return "UNEXPECTED_EOF" in text or "SSLEOFERROR" in text


def _download_attachments(post: Post, dest: Path, fetch_file, pause, pending: dict):
    for attachment in post.attachments:
        leaf = _safe_leaf(attachment.name)
        if leaf is None:
            return attachment, FetchError(
                "unsafe attachment name",
                http_status=None,
                attempts=1,
                url=attachment.url,
            )
        pause()
        try:
            content = fetch_file(attachment.url)
        except FetchError as exc:
            return attachment, exc
        if not _store_attachment(dest, post.ntt_id, leaf, content):
            return attachment, FetchError(
                "unsafe attachment name",
                http_status=None,
                attempts=1,
                url=attachment.url,
            )
        if attachment.ext in _CONVERT_EXT:
            pending[(post.ntt_id, attachment.name)] = {
                "nttId": post.ntt_id,
                "name": attachment.name,
                "ext": attachment.ext,
                "path": f"{post.ntt_id}/{leaf}",
            }
    return None


def _safe_leaf(name: str) -> str | None:
    leaf = Path(name).name
    if leaf in {"", ".", ".."} or "/" in leaf or "\\" in leaf or "\x00" in leaf:
        return None
    return leaf


def _store_attachment(dest: Path, ntt_id: int, name: str, content: bytes) -> bool:
    leaf = _safe_leaf(name)
    if leaf is None:
        return False
    base = (dest / str(ntt_id)).resolve()
    path = base / leaf
    if path.resolve().parent != base:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(content).digest():
        return True
    path.write_bytes(content)
    return True


def _failure_record(ntt_id: int, exc: FetchError, *, filename: str | None) -> dict:
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nttId": ntt_id,
        "page_url": view_url(ntt_id),
        "url": exc.url,
        "filename": filename,
        "http_status": exc.http_status,
        "error": str(exc),
        "attempts": exc.attempts,
    }


def _sweep_failure(ntt_id: int, exc: FetchError, *, filename: str | None) -> dict:
    return {"type": "failure", **_failure_record(ntt_id, exc, filename=filename)}


def _failure_key(record: dict) -> str:
    if record.get("nttId") is not None:
        return f"ntt:{record['nttId']}"
    return f"url:{record.get('url')}"


def _load_state(path: Path) -> tuple[set[int], set[int]]:
    if not path.exists():
        return set(), set()
    data = json.loads(path.read_text(encoding="utf-8"))
    done = {int(item) for item in data.get("done", [])}
    probed = {int(item) for item in data.get("probed", [])}
    return done, probed


def _state_text(done: set[int], probed: set[int]) -> str:
    payload = {"done": sorted(done), "probed": sorted(probed)}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _load_keyed(path: Path, key_fn) -> dict:
    return {key_fn(row): row for row in _read_jsonl(path)}


def _jsonl_text(rows: list[dict]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def _write_text_if_changed(path: Path, text: str) -> None:
    content = text.encode("utf-8")
    if path.exists() and path.read_bytes() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    if not rows:
        if path.exists():
            path.unlink()
        return
    _write_text_if_changed(path, _jsonl_text(rows))


def _write_seed_ledger(
    dest: Path,
    manifest: dict,
    done: set[int],
    pending: dict,
    failed: dict,
    probed: set[int],
) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    _write_jsonl(
        dest / "manifest.jsonl",
        sorted(manifest.values(), key=lambda row: row["nttId"]),
    )
    _write_text_if_changed(dest / "_state.json", _state_text(done, probed))
    _write_jsonl(
        dest / "_pending-conversion.jsonl",
        sorted(pending.values(), key=lambda row: (row["nttId"], row["name"])),
    )
    _write_jsonl(
        dest / "_failed.jsonl",
        sorted(
            failed.values(),
            key=lambda row: (row.get("nttId") is None, row.get("nttId") or 0, row.get("url") or ""),
        ),
    )
