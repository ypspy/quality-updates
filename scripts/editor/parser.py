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
PDF_RE = re.compile(r'^<!-- pdf: (.+?) -->')
SOURCE_RE = re.compile(r'^<!-- source:\s*([a-zA-Z0-9_-]+)\|(.+?)\s*-->')
NOTE_RE = re.compile(r'^\s+[!?]{3} note')

ALLOWED_SOURCE_TYPES = {'pdf', 'web', 'clip', 'url'}

AGENCY_KEYWORDS = {
    '금융감독원': '금융감독원',
    '금융위원회': '금융위원회',
    '한국공인회계사회': '한국공인회계사회',
    '한국회계기준원': '한국회계기준원',
}


def _detect_agency(header: str) -> Optional[str]:
    for key, name in AGENCY_KEYWORDS.items():
        if key in header:
            return name
    return None


def parse_links(content: str) -> list[dict]:
    """Parse .md content and return list of link dicts.

    Each dict: {date, title, url, state, pdf_path, source, agency, line_index}
    state: 'undecided' | 'skip' | 'needs_summary' | 'done'
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

            # Look ahead for state markers
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1

            if j < len(lines):
                next_line = lines[j]
                if SKIP_RE.match(next_line):
                    state = 'skip'
                elif SOURCE_RE.match(next_line):
                    src_type, src_ref = SOURCE_RE.match(next_line).groups()
                    src_type = src_type.strip()
                    src_ref = src_ref.strip()
                    if src_type not in ALLOWED_SOURCE_TYPES:
                        # Unknown marker type → treat as undecided to avoid
                        # silently persisting invalid state.
                        src_type = None
                    if src_type == 'url':
                        src_type = 'web'
                    if src_type:
                        state = 'needs_summary'
                        source = {'type': src_type, 'ref': src_ref}
                    # Backward compatibility: existing UI logic still uses pdf_path.
                    # If source type is pdf, populate pdf_path as well.
                    if source and source['type'] == 'pdf':
                        pdf_path = source['ref']
                elif PDF_RE.match(next_line):
                    state = 'needs_summary'
                    pdf_path = PDF_RE.match(next_line).group(1).strip()
                    source = {'type': 'pdf', 'ref': pdf_path}
                elif NOTE_RE.match(next_line):
                    state = 'done'

            links.append({
                'date': date,
                'title': title,
                'url': url,
                'state': state,
                'pdf_path': pdf_path,
                'source': source,
                'agency': current_agency,
                'line_index': i,
            })

        i += 1

    return links
