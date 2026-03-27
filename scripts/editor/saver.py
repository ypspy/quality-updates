# -*- coding: utf-8 -*-
"""Apply curation results to .md file content."""
import re
import shutil

SKIP_RE = re.compile(r'^<!-- skip -->$')
NO_SUMMARY_RE = re.compile(r'^<!-- no_summary -->$')
PDF_RE = re.compile(r'^<!-- pdf: .+ -->$')
SOURCE_RE = re.compile(r'^<!-- source:\s*[a-zA-Z0-9_-]+\|.+ -->$')
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
            preserved_marker_line = None
            while i < len(lines):
                next_core = _line_core(lines[i])
                if next_core == '':
                    consumed_blank = True
                    i += 1
                elif _is_comment(lines[i]):
                    # Preserve an existing marker if the incoming curation doesn't
                    # provide enough info to re-write it. This prevents losing
                    # source markers until the frontend sends `source`.
                    if preserved_marker_line is None and (
                        SOURCE_RE.match(next_core) or PDF_RE.match(next_core)
                    ):
                        preserved_marker_line = lines[i]
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
                src = entry.get('source')
                if isinstance(src, dict) and src.get('type') and src.get('ref'):
                    result.append(f"<!-- source: {src['type']}|{src['ref']} -->\n")
                elif entry.get('pdf_path'):
                    # Migration/normalization: even if the UI only sends `pdf_path`,
                    # write the unified source marker.
                    result.append(f"<!-- source: pdf|{entry['pdf_path']} -->\n")
                elif preserved_marker_line is not None:
                    result.append(preserved_marker_line)
            # undecided → no comment

            # Restore blank line separator between items
            if consumed_blank:
                result.append('\n')

            continue

        result.append(line)
        i += 1

    return ''.join(result)


def save_with_backup(file_path: str, original_content: str, curation: list[dict]) -> None:
    """Create .bak then write curated content to file_path."""
    shutil.copy2(file_path, file_path + '.bak')
    new_content = apply_curation(original_content, curation)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
