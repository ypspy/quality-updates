# Task 4 Report: item.md, 완료 판정, manifest

## Status

DONE_WITH_CONCERNS

## TDD Evidence

### RED (Step 2)

Command (cwd: `scripts`):

```text
python -m pytest tests/test_kasb_replies.py::test_compose_item_uses_detail_category_and_registered_date -q
```

Result:

```text
FAILED tests/test_kasb_replies.py::test_compose_item_uses_detail_category_and_registered_date
AttributeError: module 'crawler.kasb_replies' has no attribute 'compose_item'
1 failed in 0.41s
```

### GREEN (Step 4)

Command (cwd: `scripts`):

```text
python -m pytest tests/test_kasb_replies.py -q
```

Result:

```text
21 passed in 0.86s
```

Intermediate failure before fix (full suite after verbatim brief implementation):

```text
FAILED tests/test_kasb_replies.py::test_compose_item_writes_failed_attachment_line
assert 'failed: PrvText missing' in text
(body showed `failed: missing extract` because section key was `note.hwp` while composed attachment name was `note.hwpx`)
20 passed, 1 failed
```

## Files Changed

| File | Change |
|------|--------|
| `scripts/crawler/kasb_replies.py` | Added `json`/`yaml` imports; `attachment_filename`, `compose_item`, `read_meta`, `should_attempt`, `append_manifest` |
| `scripts/tests/test_kasb_replies.py` | Appended Task 4 tests and helpers (`_sample_row`, `_sample_detail`) |

## Implementation Summary

- **`attachment_filename`**: Strips path segments, dedupes via `used` set with `-{file_seq}` suffix pattern.
- **`compose_item`**: YAML front matter + markdown body (`## 상세 안내`, per-attachment `## 첨부:` sections); merges list/detail fields; `standards` as `list(detail.standards)`; overall `extract_status` from `aggregate_status`.
- **`read_meta`**: Parses `item.md` front matter; returns `None` on missing/invalid input.
- **`should_attempt`**: Skip when `extract_status == ok` and all attachment files exist; retry rules for missing files and `retry_failed` on non-ok statuses.
- **`append_manifest`**: Appends one JSON line per record, UTF-8, `ensure_ascii=False`.

## Self-Review

- Parsers and extractors left untouched per brief.
- `Path` not re-imported.
- Commit scoped to the two Task 4 files only (other dirty workspace files unstaged).

## Concerns

1. **`compose_item` section matching**: Brief used filename-only lookup in `by_saved`. `test_compose_item_writes_failed_attachment_line` passes `("note.hwp", ...)` while `_sample_detail` attachment is `note.hwpx`, so strict lookup fails. Added positional fallback when `len(sections) == len(names)` and filename is absent from `by_saved`. Production crawl always uses matching `attachment_filename` keys, so behavior is unchanged for the intended path; fallback only affects mismatched test (or manual) inputs.

2. **Test imports**: `json` and `yaml` were appended mid-file per brief; could be consolidated at top in a later cleanup (out of scope).

## Commit

- `feat: write KASB reply item markdown and manifest lines` (see git log for SHA)

## Fix: filename-only extract matching

Removed positional fallback in `compose_item`; sections pair only via `by_saved.get(filename, ...)`. Test `test_compose_item_writes_failed_attachment_line` uses `note.hwpx` to match `_sample_detail`.

Command (cwd: `scripts`):

```text
python -m pytest tests/test_kasb_replies.py -q
```

Result:

```text
.....................                                                    [100%]
21 passed in 0.73s
```

Commit: `12a48edef5cb6f12eda2e17c93f6bb8df8eb9bb3` — fix: match KASB reply extracts by attachment filename
