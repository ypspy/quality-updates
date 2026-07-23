# -*- coding: utf-8 -*-
"""MkDocs-safe placement for <!-- source --> markers next to admonition summaries."""
from __future__ import annotations

import re

LINK_RE = re.compile(r"^\s*- \(\d{2}-\d{2}-\d{2}\) \[(.+?)\]\((https?://[^\)]+)\)")
TOP_LINK_RE = re.compile(r"^- \(\d{2}-\d{2}-\d{2}\) ")
SECTION_HEADER_RE = re.compile(r"^#{2,4}\s")
NO_SUMMARY_RE = re.compile(r"^<!-- no_summary -->$")
APPENDIX_RE = re.compile(r"^## Appendix")
SOURCE_RE = re.compile(r"^(?P<indent>\s*)<!-- source:\s*(.+?)\s*-->\s*$")
NOTE_RE = re.compile(r"^\s+[!?]{3} note")


def _next_non_blank(lines: list[str], start: int) -> int | None:
    j = start
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    return j if j < len(lines) else None


def fix_mkdocs_source_layout(content: str) -> tuple[str, int]:
    """Move source markers under the link (4-space indent) when followed by a note block.

    MkDocs/Python-Markdown treats ``<!-- source -->`` at column 0 between a list item
    and an indented admonition as breaking list continuation; the admonition then renders
    as a literal ``<pre>`` block.

    Returns (new_content, number_of_fixes).
    """
    lines = content.splitlines(keepends=True)
    out: list[str] = []
    fixes = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        core = line.rstrip("\r\n")

        if LINK_RE.match(core):
            src_idx = _next_non_blank(lines, i + 1)
            if src_idx is not None:
                src_match = SOURCE_RE.match(lines[src_idx].rstrip("\r\n"))
                if src_match and src_match.group("indent") == "":
                    note_idx = _next_non_blank(lines, src_idx + 1)
                    if note_idx is not None and NOTE_RE.match(lines[note_idx].rstrip("\r\n")):
                        out.append(line if line.endswith("\n") else line + "\n")
                        if i + 1 < len(lines) and lines[i + 1].strip() == "":
                            i += 1
                        out.append("\n")
                        out.append(f"    <!-- source: {src_match.group(2).strip()} -->\n")
                        out.append("\n")
                        fixes += 1
                        i = src_idx + 1
                        while i < len(lines) and lines[i].strip() == "":
                            i += 1
                        continue

        out.append(line if line.endswith("\n") else line + "\n")
        i += 1

    return "".join(out), fixes


def find_unsafe_source_layout(lines: list[str]) -> list[tuple[int, str]]:
    """Return (1-based line no, message) for MkDocs-unsafe source+note layouts."""
    issues: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        core = lines[i].rstrip("\r\n")
        if not LINK_RE.match(core):
            i += 1
            continue
        src_idx = _next_non_blank(lines, i + 1)
        if src_idx is None:
            i += 1
            continue
        src_match = SOURCE_RE.match(lines[src_idx].rstrip("\r\n"))
        if not src_match or src_match.group("indent") != "":
            i += 1
            continue
        note_idx = _next_non_blank(lines, src_idx + 1)
        if note_idx is not None and NOTE_RE.match(lines[note_idx].rstrip("\r\n")):
            issues.append(
                (
                    src_idx + 1,
                    "source 마커가 링크 직후 열 0에 있으면 !!! note가 MkDocs에서 렌더되지 않음 "
                    "(링크 다음 빈 줄 → 4칸 들여쓰기 source → note)",
                )
            )
        i += 1
    return issues


def _trim_trailing_blanks(lines: list[str]) -> list[str]:
    out = list(lines)
    while out and out[-1].strip() == "":
        out.pop()
    return out


def _trim_leading_blanks(lines: list[str]) -> list[str]:
    out = list(lines)
    while out and out[0].strip() == "":
        out.pop(0)
    return out


def _format_link_entry(entry_lines: list[str]) -> list[str]:
    """Canonical spacing for one top-level curated link block."""
    if not entry_lines:
        return []
    link = entry_lines[0]
    rest = _trim_leading_blanks(_trim_trailing_blanks(entry_lines[1:]))

    no_summary: str | None = None
    if rest and NO_SUMMARY_RE.match(rest[0].strip()):
        no_summary = rest[0]
        rest = _trim_leading_blanks(rest[1:])

    note_idx = next((i for i, line in enumerate(rest) if NOTE_RE.match(line.rstrip("\r\n"))), None)
    source_line = next((line for line in rest if SOURCE_RE.match(line.rstrip("\r\n"))), None)

    if note_idx is None:
        out = [link]
        if no_summary:
            out.append(no_summary)
        return out

    note_block = rest[note_idx:]
    out = [link, ""]
    if source_line:
        out.append(source_line)
        out.append("")
    out.extend(note_block)
    return out


def normalize_quarterly_spacing(content: str) -> tuple[str, int]:
    """Normalize blank-line spacing across quarterly link entries (main body only).

    Rules (2025 Q4 deployed pattern + MkDocs-safe source markers):
    - Exactly one blank line between consecutive top-level ``- (YY-MM-DD)`` entries
    - ``<!-- no_summary -->`` immediately after link, then blank before next entry
    - Summarized entries: link → blank → source (optional) → blank → admonition block
    - Single blank between source and admonition; admonition title → body blank preserved
    - Appendix A and nested/indented lists are not modified
    """
    lines = content.splitlines()
    appendix_idx = next((i for i, line in enumerate(lines) if APPENDIX_RE.match(line)), len(lines))
    head, tail = lines[:appendix_idx], lines[appendix_idx:]

    segments: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(head):
        if TOP_LINK_RE.match(head[i]):
            entry = [head[i]]
            i += 1
            # Stop at next link OR section header — otherwise ###/#### after
            # <!-- no_summary --> is swallowed and dropped by _format_link_entry.
            while i < len(head) and not TOP_LINK_RE.match(head[i]):
                if SECTION_HEADER_RE.match(head[i]):
                    break
                entry.append(head[i])
                i += 1
            segments.append(("entry", _format_link_entry(entry)))
        else:
            static = [head[i]]
            i += 1
            while i < len(head) and not TOP_LINK_RE.match(head[i]):
                static.append(head[i])
                i += 1
            segments.append(("static", static))

    out: list[str] = []
    fixes = 0
    for kind, block in segments:
        block = _trim_trailing_blanks(block)
        if not block:
            continue
        if kind == "entry":
            if out:
                if out[-1].strip() != "":
                    out.append("")
                    fixes += 1
                # collapse duplicate separators
                while len(out) >= 2 and out[-1].strip() == "" and out[-2].strip() == "":
                    out.pop()
                    fixes += 1
            before = len(out)
            out.extend(block)
            if len(out) != before + len(block):
                fixes += 1
        else:
            if out and out[-1].strip() != "" and block[0].strip() != "":
                out.append("")
            out.extend(block)

    normalized_head = "\n".join(out)
    result = normalized_head
    if tail:
        if result and not result.endswith("\n"):
            result += "\n"
        result += "\n".join(tail)
    result = result + ("\n" if content.endswith("\n") else "")
    fixes = 0 if result == content else 1
    return result, fixes
