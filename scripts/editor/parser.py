# -*- coding: utf-8 -*-
"""Parse quality-updates .md files to extract link items."""
import re
from typing import Optional

LINK_RE = re.compile(
    r'^\s*- \((\d{2}-\d{2}-\d{2})\) \[(.+?)\]\((https?://[^\)]+)\)'
)
SECTION_RE = re.compile(r'^#{1,4}\s+(.+)')
APPENDIX_RE = re.compile(r'^## Appendix')
SKIP_RE = re.compile(r'^<!-- skip -->')
NO_SUMMARY_RE = re.compile(r'^<!-- no_summary -->')
PDF_RE = re.compile(r'^\s*<!-- pdf: (.+?) -->')
SOURCE_RE = re.compile(r'^\s*<!-- source:\s*([a-zA-Z0-9_-]+)\|(.+?)\s*-->')
NOTE_RE = re.compile(r'^\s+[!?]{3} note')

ALLOWED_SOURCE_TYPES = {'pdf', 'web', 'clip', 'url', 'shot', 'hwp', 'file'}
_SOURCE_TYPE_ALIASES = {'url': 'web', 'hwpx': 'hwp', 'hml': 'hwp'}

AGENCY_KEYWORDS = {
    '금융감독원': '금융감독원',
    '금융위원회': '금융위원회',
    '한국공인회계사회': '한국공인회계사회',
    '한국회계기준원': '한국회계기준원',
}


def coerce_source(src: object) -> Optional[dict]:
    """Return ``{type, ref}`` or None. ``url``/``hwpx``/``hml`` aliases fold into ``web``/``hwp``."""
    if not isinstance(src, dict):
        return None
    src_type = src.get('type')
    src_ref = src.get('ref')
    if not isinstance(src_type, str) or not isinstance(src_ref, str):
        return None
    src_type = _SOURCE_TYPE_ALIASES.get(src_type.strip(), src_type.strip())
    src_ref = src_ref.strip()
    if src_type not in ALLOWED_SOURCE_TYPES or not src_ref:
        return None
    if '-->' in src_ref or '\n' in src_ref or '\r' in src_ref:
        return None
    return {'type': src_type, 'ref': src_ref}


def coerce_sources(sources=None, *, source=None, pdf_path=None) -> list[dict]:
    """Normalize a source list. A non-empty ``sources`` list wins over ``source``/``pdf_path``."""
    raw: list = []
    if isinstance(sources, list) and sources:
        raw.extend(sources)
    else:
        if isinstance(source, dict):
            raw.append(source)
        if isinstance(pdf_path, str) and pdf_path.strip():
            raw.append({'type': 'pdf', 'ref': pdf_path.strip()})
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in raw:
        one = coerce_source(item)
        if not one:
            continue
        key = (one['type'], one['ref'])
        if key in seen:
            continue
        seen.add(key)
        out.append(one)
    return out


def _first_pdf_ref(sources: list[dict]) -> Optional[str]:
    for src in sources:
        if src.get('type') == 'pdf':
            return src.get('ref')
    return None


def _marker_from_groups(src_type: str, src_ref: str) -> Optional[dict]:
    return coerce_source({'type': src_type, 'ref': src_ref})


def _collect_source_markers(lines: list[str], start: int) -> tuple[list[dict], int]:
    """Read consecutive ``source`` / legacy ``pdf`` markers. Invalid types are skipped."""
    sources: list[dict] = []
    seen: set[tuple[str, str]] = set()
    index = start
    while index < len(lines):
        src_match = SOURCE_RE.match(lines[index])
        if src_match:
            one = _marker_from_groups(src_match.group(1), src_match.group(2))
            index += 1
            if one:
                key = (one['type'], one['ref'])
                if key not in seen:
                    seen.add(key)
                    sources.append(one)
            continue
        pdf_match = PDF_RE.match(lines[index])
        if pdf_match:
            one = {'type': 'pdf', 'ref': pdf_match.group(1).strip()}
            index += 1
            key = (one['type'], one['ref'])
            if one['ref'] and key not in seen:
                seen.add(key)
                sources.append(one)
            continue
        break
    return sources, index


def _detect_agency(header: str) -> Optional[str]:
    for key, name in AGENCY_KEYWORDS.items():
        if key in header:
            return name
    return None


def parse_links(content: str) -> list[dict]:
    """Parse .md content and return list of link dicts.

    Each dict: {date, title, url, state, pdf_path, source, agency, line_index}
    state: 'undecided' | 'skip' | 'no_summary' | 'needs_summary' | 'done'
    """
    lines = content.splitlines()
    links = []
    current_agency = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # Stop at Appendix boundary
        if APPENDIX_RE.match(line):
            break

        # Track agency section headers
        section_match = SECTION_RE.match(line)
        if section_match:
            agency = _detect_agency(section_match.group(1))
            if agency:
                current_agency = agency

        # Match link line
        link_match = LINK_RE.match(line)
        if link_match:
            date, title, url = link_match.groups()
            state = 'undecided'
            pdf_path = None
            source = None
            sources: list[dict] = []

            # Look ahead for state markers. Several source lines = several attachments.
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1

            if j < len(lines):
                next_line = lines[j]
                if SKIP_RE.match(next_line):
                    state = 'skip'
                elif NO_SUMMARY_RE.match(next_line):
                    state = 'no_summary'
                elif SOURCE_RE.match(next_line) or PDF_RE.match(next_line):
                    sources, after = _collect_source_markers(lines, j)
                    if sources:
                        state = 'needs_summary'
                        source = sources[0]
                        pdf_path = _first_pdf_ref(sources)
                    # Summarized item: source marker(s) then note block (MkDocs-safe layout).
                    k = after
                    while k < len(lines) and lines[k].strip() == '':
                        k += 1
                    if k < len(lines) and NOTE_RE.match(lines[k]):
                        state = 'done'
                elif NOTE_RE.match(next_line):
                    state = 'done'

            links.append({
                'date': date,
                'title': title,
                'url': url,
                'state': state,
                'pdf_path': pdf_path,
                'source': source,
                'sources': sources,
                'agency': current_agency,
                'line_index': i,
            })

        i += 1

    return links
