# Task 4 Report: 처리 기록과 raw 복사

## Summary

`export_quarter` copies a finished quarter into a vault raw directory without reading PDFs. It keeps the body before `## Appendix`, skips `<!-- skip -->` and `<!-- no_summary -->`, and copies only `source: pdf` files from that body. HWP/HWPX in a block that already has a pdf marker is not copied. HWP/HWPX with no pdf marker is listed on `waiting`. `shot` PNGs and `clip|clips/{id}` files are copied beside the PDFs. The processed record keeps the link line, source lines, and `!!! note` body. The record name is the link date plus the first 40 characters of the title with `\ / : * ? " < > |` removed, for example `26-09-11-계리가정.md`.

The quarter markdown is copied to `raw/quality-updates-{stem}.md` with the same byte rule: write when absent, skip when the bytes match, and write `stem--YYYY-MM-DD` before the extension only when the bytes differ and that snapshot is absent. If the destination's parent directory does not exist, the function returns exit code 2 and does not create the destination. A selected pdf, shot, or clip that is missing returns exit code 1 after the other copies continue. Files the exporter does not select do not affect the exit code.

`export_quarterly_raw.py` calls `export_quarter` and returns `exit_code`. The default `--dest` is `C:\dev\obsidian-valut\raw`. Neither module imports a PDF extract function.

## TDD

### Step 2 — RED

Command (from `scripts`):

```
python -m pytest tests/test_export_quarterly_raw.py -q
```

Exit code: 2

Output:

```
=================================== ERRORS ====================================
_____________ ERROR collecting tests/test_export_quarterly_raw.py _____________
ImportError while importing test module 'C:\dev\quality-updates\.worktrees\sanction-resolution-wiki-handoff\scripts\tests\test_export_quarterly_raw.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Users\yoont\AppData\Local\Programs\Python\Python312\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\test_export_quarterly_raw.py:8: in <module>
    from quarterly_handoff import export_quarter
E   ModuleNotFoundError: No module named 'quarterly_handoff'
=========================== short test summary info ===========================
ERROR tests/test_export_quarterly_raw.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.27s
```

Expected: FAIL with `ModuleNotFoundError` — confirmed. This was before `scripts/quarterly_handoff.py` existed.

### Step 4 — GREEN

Command (from `scripts`):

```
python -m pytest tests/test_export_quarterly_raw.py -q
```

Exit code: 0

Output:

```
...                                                                      [100%]
3 passed in 0.16s
```

Four-module command (from `scripts`):

```
python -m pytest tests/test_repair_quarterly_structure.py tests/test_fsc_section_order.py tests/test_attach_sanction_minutes.py tests/test_export_quarterly_raw.py -q
```

Exit code: 0

Output:

```
.............                                                            [100%]
13 passed in 0.43s
```

From the worktree root:

```
python scripts/validate_content.py --strict
```

Exit code: 0. No stdout.

```
mkdocs build --strict
```

Exit code: 0

Output:

```
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: C:\dev\quality-updates\.worktrees\sanction-resolution-wiki-handoff\site
INFO    -  DeprecationWarning: A plugin has set File.page to an instance of Page and it got overwritten. The behavior of this will change in MkDocs 1.6.
  File "C:\Users\yoont\AppData\Local\Programs\Python\Python312\Lib\site-packages\mkdocs\structure\nav.py", line 183, in _data_to_navigation
    _data_to_navigation((key, value), files, config)
  File "C:\Users\yoont\AppData\Local\Programs\Python\Python312\Lib\site-packages\mkdocs\structure\nav.py", line 209, in _data_to_navigation
    warnings.warn(

INFO    -  The following pages exist in the docs directory, but are not included in the "nav" configuration:
  - fss-review\fr2022.md
INFO    -  Doc file 'quality-updates/2020/2020-07-01_to_2020-09-30.md' contains an unrecognized relative link '임대주택건설사업자의 임대후분양주택 회계처리', it was left as is.
INFO    -  Documentation built in 23.59 seconds
```

The MkDocs warning and the unlisted page were already present. The build still exited 0.

## Changes

| File | Change |
|------|--------|
| `scripts/tests/test_export_quarterly_raw.py` | Three tests from the brief, written in full. The first test builds `exam.pdf` and `appendix.pdf` itself. `_write_quarter` is used only by the dated-snapshot and missing-vault tests. |
| `scripts/quarterly_handoff.py` | `record_from_item`, `export_quarter`, and `ExportResult` (`exit_code`, `copied`, `skipped`, `waiting`). |
| `scripts/export_quarterly_raw.py` | CLI. Default destination `Path(r"C:\dev\obsidian-valut\raw")`. Prints copied, skipped, and waiting paths and returns `exit_code`. |

The test module also inserts `scripts/` on `sys.path`, matching the other handoff tests. `python -m pytest` from `scripts` already puts that directory on the path; the insert keeps the import working if pytest is started elsewhere.

## Self-review

- Body is cut at `^## Appendix`. `<!-- skip -->` and `<!-- no_summary -->` items are not copied and are not counted as missing. The first test leaves `exam.pdf` and `appendix.pdf` on disk and asserts they are not copied, with `exit_code == 0`.
- A second export of unchanged bytes returns `copied == []`. Same bytes go to `skipped`. Different bytes write `{stem}--YYYY-MM-DD{suffix}` only when that snapshot is absent. The original `ifrs.pdf` stays `%PDF-1` and `ifrs--2026-11-06.pdf` is `%PDF-2`.
- If `dest.parent` is not a directory, return exit code 2 and do not create `dest`. Checked again with a parent named `no-vault`: exit 2, destination absent.
- A selected pdf that is not on disk sets exit code 1 and does not stop the shot, clip, record, or quarter-markdown copies. An hwp marker in that same block is not added to `waiting`. An hwp-only block adds the filename to `waiting` and still writes its record.
- Record filename check: title `bad:name?` becomes `26-09-11-badname.md`. Quarter file lands at `quality-updates-{stem}.md`. Shot bytes and clip text copy through.
- `record_from_item` keeps the link line, both source lines, and the note text. It does not call a PDF reader. `quarterly_handoff.py` and `export_quarterly_raw.py` do not import `extract_pdf` or another PDF library.
- Copies use `write_bytes`, so Windows newline translation does not make an unchanged record look new on the second run.
- Did not edit `docs/quality-updates/2026/2026-07-01_to_2026-09-30.md`. Did not run `repair_quarterly_structure.py`. Did not launch Whale. Did not call the CLI against `C:\dev\obsidian-valut\raw`.
- Commit `dd16bab` contains only the three Step 5 files (330 insertions). It was not pushed.

## Concern

The editor stores clip text at `scripts/editor/clips/{id}.json` and writes markers as `<!-- source: clip|{id} -->`. This exporter follows the brief: `clip|clips/{id}` is copied only when `scripts/editor/clips/{id}` exists, and the destination name is `{id}.txt`. A bare `{id}` marker is also looked up as `{id}` inside the clips directory. Existing `.json` clips are not read, so a quarter that points at them will skip the clip and return exit code 1. PDF, shot, note, and quarter-markdown copies are unaffected.

## Commit

During `git commit`, Git printed `failed to delete 'C:/dev/quality-updates/.git/worktrees/feat-consumption-mcp-product': Permission denied` and then created the commit. Exit code was 0. The commit is `dd16bab` on `feat/sanction-resolution-wiki-handoff`.

```
dd16bab feat: copy quarter notes and source PDFs into the vault raw folder
```

## Clip JSON lookup

Command (from `scripts`):

```
cd scripts; python -m pytest tests/test_export_quarterly_raw.py -q
```

Exit code: 0

Output:

```
....                                                                     [100%]
4 passed in 0.17s
```

## Fix: repo records and heading bounds

Command (from `scripts`):

```
cd scripts; python -m pytest tests/test_export_quarterly_raw.py tests/test_repair_quarterly_structure.py tests/test_fsc_section_order.py tests/test_attach_sanction_minutes.py -q
```

Exit code: 0

Output:

```
.................                                                        [100%]
17 passed in 0.40s
```
