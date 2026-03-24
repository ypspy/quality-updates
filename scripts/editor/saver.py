# -*- coding: utf-8 -*-
"""Apply curation results to .md file content."""
import re
import shutil

SKIP_RE = re.compile(r'^<!-- skip -->$')
PDF_RE = re.compile(r'^<!-- pdf: .+ -->$')
APPENDIX_RE = re.compile(r'^## Appendix')
NOTE_RE = re.compile(r'^\s+[!?]{3} note')


def _is_comment(line: str) -> bool:
    return bool(SKIP_RE.match(line) or PDF_RE.match(line))


def apply_curation(content: str, curation: list[dict]) -> str:
    """Return new .md content with curation comments applied."""
    lines = content.splitlines(keepends=True)
    # Build lookup: line_index → curation entry
    curation_map = {entry['line_index']: entry for entry in curation}

    result = []
    i = 0
    in_appendix = False

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip('\n')

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
            while i < len(lines):
                next_stripped = lines[i].rstrip('\n')
                if next_stripped == '':
                    consumed_blank = True
                    i += 1
                elif _is_comment(next_stripped):
                    i += 1
                else:
                    break

            # Insert new comment based on state
            state = entry['state']
            if state == 'skip':
                result.append('<!-- skip -->\n')
            elif state == 'needs_summary' and entry.get('pdf_path'):
                result.append(f"<!-- pdf: {entry['pdf_path']} -->\n")
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
