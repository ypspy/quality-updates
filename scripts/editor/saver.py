# -*- coding: utf-8 -*-
"""Apply curation results to .md file content."""
import re
import shutil

from .parser import coerce_sources

SKIP_RE = re.compile(r'^<!-- skip -->$')
NO_SUMMARY_RE = re.compile(r'^<!-- no_summary -->$')
PDF_RE = re.compile(r'^<!-- pdf: .+ -->$')
SOURCE_RE = re.compile(r'^\s*<!-- source:\s*[a-zA-Z0-9_-]+\|.+ -->$')
APPENDIX_RE = re.compile(r'^## Appendix')


def _line_core(line: str) -> str:
    """Strip line endings for comparisons. CRLF files must not leave ``\\r`` or markers won't match."""
    return line.rstrip('\r\n')


def _is_comment(line: str) -> bool:
    core = _line_core(line)
    return bool(
        SKIP_RE.match(core)
        or NO_SUMMARY_RE.match(core)
        or PDF_RE.match(core)
        or SOURCE_RE.match(core)
    )


def _build_curation_map(curation: list[dict]) -> dict[int, dict]:
    """line_index must be int (JSON may send str in edge cases)."""
    out: dict[int, dict] = {}
    for entry in curation:
        if not isinstance(entry, dict):
            continue
        li = entry.get('line_index')
        if li is None:
            continue
        try:
            idx = int(li)
        except (TypeError, ValueError):
            continue
        out[idx] = entry
    return out


def apply_curation(content: str, curation: list[dict]) -> str:
    """Return new .md content with curation comments applied."""
    lines = content.splitlines(keepends=True)
    curation_map = _build_curation_map(curation)

    result = []
    i = 0
    in_appendix = False

    while i < len(lines):
        line = lines[i]
        stripped = _line_core(line)

        if APPENDIX_RE.match(stripped):
            in_appendix = True

        if in_appendix:
            result.append(line)
            i += 1
            continue

        if i in curation_map:
            entry = curation_map[i]

            # done entries: leave everything after the link untouched
            # (blank line + !!! note block must stay intact for MkDocs)
            if entry['state'] == 'done':
                result.append(line)
                i += 1
                continue

            result.append(line)  # keep link line as-is
            i += 1

            # Skip blank lines + old comments immediately after link
            # Track whether we consumed a blank line (to restore it after)
            consumed_blank = False
            preserved_marker_lines: list[str] = []
            while i < len(lines):
                next_core = _line_core(lines[i])
                if next_core == '':
                    consumed_blank = True
                    i += 1
                elif _is_comment(lines[i]):
                    # Preserve existing markers when the payload has no source.
                    # Several consecutive markers belong to the same item.
                    if SOURCE_RE.match(next_core) or PDF_RE.match(next_core):
                        preserved_marker_lines.append(_ensure_newline(lines[i]))
                    i += 1
                else:
                    break

            # Insert new comment based on state.
            state = entry['state']
            if state == 'skip':
                result.append('<!-- skip -->\n')
            elif state == 'no_summary':
                result.append('<!-- no_summary -->\n')
            elif state == 'needs_summary':
                sources = _sources_from_entry(entry)
                if sources:
                    for src in sources:
                        result.append(f"<!-- source: {src['type']}|{src['ref']} -->\n")
                elif preserved_marker_lines:
                    result.extend(preserved_marker_lines)
            # undecided → no comment

            # Restore blank line separator between items
            if consumed_blank:
                result.append('\n')

            continue

        result.append(line)
        i += 1

    return ''.join(result)


def _ensure_newline(line: str) -> str:
    return line if line.endswith('\n') else line + '\n'


def _sources_from_entry(entry: dict) -> list[dict] | None:
    """Sources to write, or None when the payload should keep the markers already on disk."""
    if isinstance(entry.get('sources'), list) and entry['sources']:
        normalized = coerce_sources(entry['sources'])
        return normalized or None
    if entry.get('source') or entry.get('pdf_path'):
        normalized = coerce_sources(None, source=entry.get('source'), pdf_path=entry.get('pdf_path'))
        return normalized or None
    return None


def save_with_backup(file_path: str, original_content: str, curation: list[dict]) -> None:
    """Create .bak then write curated content to file_path."""
    shutil.copy2(file_path, file_path + '.bak')
    new_content = apply_curation(original_content, curation)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
