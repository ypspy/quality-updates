# -*- coding: utf-8 -*-
"""Parse quality-updates markdown into corpus items (extended beyond editor.parser)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from corpus.schema import (
    SCHEMA_VERSION,
    CorpusItem,
    NoteBlock,
    make_id,
    state_to_summary_status,
)
from skip_removal import remove_skip_pairs

LINK_RE = re.compile(
    r"^\s*- \((\d{2}-\d{2}-\d{2})\) \[(.+?)\]\((https?://[^\)]+)\)"
)
SECTION_RE = re.compile(r"^(#{1,4})\s+(.+)")
APPENDIX_RE = re.compile(r"^## Appendix")
SKIP_RE = re.compile(r"^<!-- skip -->")
NO_SUMMARY_RE = re.compile(r"^<!-- no_summary -->")
PDF_RE = re.compile(r"^\s*<!-- pdf: (.+?) -->")
SOURCE_RE = re.compile(r"^\s*<!-- source:\s*([a-zA-Z0-9_-]+)\|(.+?)\s*-->")
NOTE_START_RE = re.compile(r"^(\s+)([!?]{3})\s+note(?:\s+\"(.+?)\")?\s*$")
TABLE_ROW_RE = re.compile(r"^\s+\|(.+)\|\s*$")

ALLOWED_SOURCE_TYPES = {"pdf", "web", "clip", "url", "shot"}

AGENCY_KEYWORDS = {
    "금융감독원": "금융감독원",
    "금융위원회": "금융위원회",
    "한국공인회계사회": "한국공인회계사회",
    "한국회계기준원": "한국회계기준원",
}


def _detect_agency(header: str) -> str | None:
    for key, name in AGENCY_KEYWORDS.items():
        if key in header:
            return name
    return None


def split_front_matter(content: str) -> tuple[dict[str, Any], str]:
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return meta, body


def _parse_note_block(lines: list[str], start: int, base_indent: int) -> tuple[NoteBlock | None, int]:
    m = NOTE_START_RE.match(lines[start])
    if not m:
        return None, start
    admonition = m.group(2)
    title = m.group(3) or "주요 내용"
    bullets: list[str] = []
    tables: list[list[str]] = []
    i = start + 1
    current_table: list[str] | None = None

    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if indent < base_indent and stripped:
            break
        if LINK_RE.match(line) or SECTION_RE.match(line):
            break

        if TABLE_ROW_RE.match(line):
            row = "|" + TABLE_ROW_RE.match(line).group(1) + "|"
            if current_table is None:
                current_table = []
            current_table.append(row.strip())
            i += 1
            continue

        if current_table:
            tables.append(current_table)
            current_table = None

        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
            i += 1
            continue

        if indent >= base_indent and stripped:
            i += 1
            continue
        break

    if current_table:
        tables.append(current_table)

    note = NoteBlock(
        admonition=admonition,
        title=title,
        bullets=bullets,
        tables=tables,
    )
    return note, i


def _parse_link_state(lines: list[str], i: int) -> tuple[str, dict | None, list[NoteBlock], int]:
    """Return (state, source, notes, next_index)."""
    state = "undecided"
    source: dict | None = None
    notes: list[NoteBlock] = []
    j = i + 1

    while j < len(lines) and lines[j].strip() == "":
        j += 1

    if j >= len(lines):
        return state, source, notes, j

    next_line = lines[j]
    if SKIP_RE.match(next_line.strip()):
        return "skip", None, notes, j + 1
    if NO_SUMMARY_RE.match(next_line.strip()):
        return "no_summary", None, notes, j + 1

    if SOURCE_RE.match(next_line):
        src_type, src_ref = SOURCE_RE.match(next_line).groups()
        src_type = src_type.strip()
        src_ref = src_ref.strip()
        if src_type == "url":
            src_type = "web"
        if src_type in ALLOWED_SOURCE_TYPES:
            source = {"type": src_type, "ref": src_ref}
            state = "needs_summary"
        k = j + 1
        while k < len(lines) and lines[k].strip() == "":
            k += 1
        if k < len(lines):
            note_m = NOTE_START_RE.match(lines[k])
            if note_m:
                note, k = _parse_note_block(lines, k, len(note_m.group(1)) + 4)
                if note:
                    notes.append(note)
                    state = "done"
                return state, source, notes, k
        return state, source, notes, j + 1

    if PDF_RE.match(next_line):
        ref = PDF_RE.match(next_line).group(1).strip()
        source = {"type": "pdf", "ref": ref}
        return "needs_summary", source, notes, j + 1

    note_m = NOTE_START_RE.match(next_line)
    if note_m:
        note, k = _parse_note_block(lines, j, len(note_m.group(1)) + 4)
        if note:
            notes.append(note)
        return "done", source, notes, k

    return state, source, notes, j


def infer_period_from_filename(filename: str) -> tuple[str, dict[str, str]]:
    """Derive period_label and period from ``YYYY-MM-DD_to_YYYY-MM-DD.md``."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})\.md", filename)
    if not m:
        return "", {}
    start, end = m.group(1), m.group(2)
    end_month = int(end[5:7])
    quarter = (end_month - 1) // 3 + 1
    period_label = f"{end[:4]}-Q{quarter}"
    return period_label, {"start": start, "end": end}


def parse_corpus_items(
    content: str,
    source_doc: str,
    public_page: str = "",
    *,
    fallback_period_label: str = "",
    fallback_period: dict[str, str] | None = None,
) -> tuple[dict[str, Any], list[CorpusItem]]:
    meta, body = split_front_matter(content)
    filtered = remove_skip_pairs(body)
    lines = filtered.splitlines()

    period_label = str(meta.get("period_label") or fallback_period_label or "")
    period = meta.get("period") or fallback_period or {}
    if not isinstance(period, dict):
        period = {}
    if not period and fallback_period:
        period = dict(fallback_period)

    items: list[CorpusItem] = []
    current_agency = ""
    current_subsection = ""

    i = 0
    while i < len(lines):
        line = lines[i]
        if APPENDIX_RE.match(line):
            break

        section_match = SECTION_RE.match(line)
        if section_match:
            level = len(section_match.group(1))
            header = section_match.group(2).strip()
            agency = _detect_agency(header)
            if agency and level <= 3:
                current_agency = agency
            if level == 4:
                current_subsection = header
            i += 1
            continue

        link_match = LINK_RE.match(line)
        if not link_match:
            i += 1
            continue

        date, title, url = link_match.groups()
        state, source, notes, next_i = _parse_link_state(lines, i)
        i = next_i

        if state == "skip":
            continue

        summary_status = state_to_summary_status(state)
        agency = current_agency or "unknown"
        item_id = make_id(period_label, agency, date, url)

        note_dicts = [
            {
                "admonition": n.admonition,
                "title": n.title,
                "bullets": n.bullets,
                **({"tables": n.tables} if n.tables else {}),
            }
            for n in notes
        ]

        items.append(
            CorpusItem(
                id=item_id,
                schema_version=SCHEMA_VERSION,
                period_label=period_label,
                period={"start": str(period.get("start", "")), "end": str(period.get("end", ""))},
                agency=agency,
                subsection=current_subsection,
                date=date,
                title=title,
                url=url,
                summary_status=summary_status,
                source=source,
                notes=note_dicts,
                source_doc=source_doc,
                public_page=public_page,
            )
        )

    return meta, items


def discover_quarter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for year_dir in sorted(root.glob("*")):
        if not year_dir.is_dir():
            continue
        for md in sorted(year_dir.glob("*.md")):
            files.append(md)
    return files
