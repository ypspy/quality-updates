"""Copy a finished quarter's notes and source files into a vault raw folder."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

LINK_RE = re.compile(
    r"^\s*- \((\d{2}-\d{2}-\d{2})\) \[(.+?)\]\((https?://[^\)]+)\)\s*$"
)
SOURCE_RE = re.compile(r"<!--\s*source:\s*([A-Za-z0-9_-]+)\|(.+?)\s*-->")
APPENDIX_RE = re.compile(r"(?m)^## Appendix\b")
SKIP_RE = re.compile(r"<!--\s*(?:skip|no_summary)\s*-->")
NOTE_RE = re.compile(r"!!!\s*note")
INVALID_FILENAME = re.compile(r'[\\/:*?"<>|]')
HWP_TYPES = {"hwp", "hwpx", "hml"}


@dataclass
class ExportResult:
    exit_code: int
    copied: list[str]
    skipped: list[str]
    waiting: list[str]


def record_from_item(link: str, body: str) -> str:
    """Keep the link line, source markers, and note body as written."""
    lines = [link.rstrip()]
    in_note = False
    for line in body.splitlines():
        if in_note:
            lines.append(line)
            continue
        if SOURCE_RE.search(line):
            lines.append(line)
            continue
        if NOTE_RE.search(line):
            in_note = True
            lines.append(line)
    return "\n".join(lines).rstrip() + "\n"


def _record_filename(date_text: str, title: str) -> str:
    slug = INVALID_FILENAME.sub("", title[:40])
    return f"{date_text}-{slug}.md"


def _items(text: str) -> list[tuple[str, str, str, str]]:
    body = APPENDIX_RE.split(text, maxsplit=1)[0]
    lines = body.splitlines()
    starts = [index for index, line in enumerate(lines) if LINK_RE.match(line)]
    items: list[tuple[str, str, str, str]] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        link_line = lines[start]
        matched = LINK_RE.match(link_line)
        if matched is None:
            continue
        date_text, title, _url = matched.groups()
        item_body = "\n".join(lines[start + 1 : end])
        items.append((link_line, item_body, date_text, title))
    return items


def _download_file(downloads: Path, ref: str) -> Path:
    relative = ref.strip().replace("\\", "/")
    if relative.startswith("downloads/"):
        relative = relative[len("downloads/") :]
    return downloads / relative


def _clip_bytes(clips: Path, ref: str) -> tuple[str, bytes | None]:
    """Read editor clip JSON and return vault `{id}.txt` bytes.

    Markers may use `clip|{id}`, `clip|clips/{id}`, or the same paths with
    `.json`. The file on disk is always `{id}.json`; its `raw` string is the
    text copied into the vault. A missing file returns no bytes.
    """
    relative = ref.strip().replace("\\", "/")
    if relative.startswith("clips/"):
        relative = relative[len("clips/") :]
    clip_id = Path(relative).name
    if clip_id.endswith(".json"):
        clip_id = clip_id[: -len(".json")]
    dest_name = f"{clip_id}.txt"
    source = clips / f"{clip_id}.json"
    if not source.is_file():
        return dest_name, None
    try:
        record = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return dest_name, None
    if not isinstance(record, dict):
        return dest_name, None
    raw = record.get("raw")
    if not isinstance(raw, str):
        return dest_name, None
    return dest_name, raw.encode("utf-8")


def _copy_bytes(
    data: bytes,
    target: Path,
    today: date,
    copied: list[str],
    skipped: list[str],
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(data)
        copied.append(str(target))
        return
    if target.read_bytes() == data:
        skipped.append(str(target))
        return
    snapshot = target.with_name(f"{target.stem}--{today.isoformat()}{target.suffix}")
    if snapshot.exists():
        skipped.append(str(snapshot))
        return
    snapshot.write_bytes(data)
    copied.append(str(snapshot))


def _source_markers(body: str) -> list[tuple[str, str]]:
    return [(kind.lower(), ref.strip()) for kind, ref in SOURCE_RE.findall(body)]


def _copy_item_files(
    body: str,
    downloads: Path,
    clips: Path,
    sources_dir: Path,
    today: date,
    copied: list[str],
    skipped: list[str],
    waiting: list[str],
) -> bool:
    markers = _source_markers(body)
    has_pdf = any(kind == "pdf" for kind, _ref in markers)
    missing = False
    for kind, ref in markers:
        if kind in HWP_TYPES:
            if not has_pdf:
                waiting.append(Path(ref).name)
            continue
        if kind in {"pdf", "shot"}:
            source = _download_file(downloads, ref)
            if not source.is_file():
                missing = True
                continue
            _copy_bytes(source.read_bytes(), sources_dir / source.name, today, copied, skipped)
            continue
        if kind == "clip":
            dest_name, data = _clip_bytes(clips, ref)
            if data is None:
                missing = True
                continue
            _copy_bytes(data, sources_dir / dest_name, today, copied, skipped)
    return missing


def export_quarter(
    md_path: Path,
    downloads: Path,
    clips: Path,
    dest: Path,
    today: date,
) -> ExportResult:
    if not dest.parent.is_dir():
        return ExportResult(exit_code=2, copied=[], skipped=[], waiting=[])

    dest.mkdir(exist_ok=True)
    copied: list[str] = []
    skipped: list[str] = []
    waiting: list[str] = []
    missing = False

    quarter_bytes = Path(md_path).read_bytes()
    quarter_target = dest / f"quality-updates-{Path(md_path).stem}.md"
    _copy_bytes(quarter_bytes, quarter_target, today, copied, skipped)

    text = quarter_bytes.decode("utf-8")
    stem = Path(md_path).stem
    sources_dir = dest / "quality-updates-sources" / stem
    records_dir = dest / "quality-updates-processed" / stem

    for link_line, body, date_text, title in _items(text):
        if SKIP_RE.search(link_line + "\n" + body):
            continue
        if _copy_item_files(
            body, downloads, clips, sources_dir, today, copied, skipped, waiting
        ):
            missing = True
        record = record_from_item(link_line, body)
        record_path = records_dir / _record_filename(date_text, title)
        _copy_bytes(record.encode("utf-8"), record_path, today, copied, skipped)

    return ExportResult(
        exit_code=1 if missing else 0,
        copied=copied,
        skipped=skipped,
        waiting=waiting,
    )
