#!/usr/bin/env python3
"""Expand collapsible link-summary admonitions: ??? note → !!! note (Appendix ??? info unchanged)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NOTE_LINE = re.compile(r"^(\s*)\?\?\? note(\s+.*)$", re.MULTILINE)


def expand_notes_in_text(text: str) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f"{match.group(1)}!!! note{match.group(2)}"

    updated = NOTE_LINE.sub(repl, text)
    return updated, count


def _default_paths(repo_root: Path) -> list[Path]:
    docs_dir = repo_root / "docs" / "quality-updates"
    paths = sorted(docs_dir.rglob("*.md"))
    return [p for p in paths if p.name != "index.md" and p.parent.name.isdigit()]


def expand_file(path: Path, *, dry_run: bool) -> tuple[bool, int]:
    original = path.read_text(encoding="utf-8")
    updated, count = expand_notes_in_text(original)
    if updated == original:
        return False, 0
    if not dry_run:
        path.write_text(updated, encoding="utf-8")
    return True, count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replace ??? note with !!! note in quarter markdown files"
    )
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files")
    parser.add_argument("--file", action="append", dest="files", help="Specific file path (repeatable)")
    parser.add_argument("--verbose", action="store_true", help="Print per-file replacement counts")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    if args.files:
        paths = []
        for f in args.files:
            p = Path(f)
            if not p.is_absolute():
                p = repo_root / p
            if p.exists():
                paths.append(p.resolve())
            else:
                print(f"Warning: file not found {f}", file=sys.stderr)
    else:
        paths = _default_paths(repo_root)

    total = 0
    changed_files = 0
    for path in paths:
        changed, count = expand_file(path, dry_run=args.dry_run)
        if changed:
            changed_files += 1
            total += count
            if args.verbose:
                rel = path.relative_to(repo_root)
                print(f"{rel}: {count} replacement(s)")

    mode = "would replace" if args.dry_run else "replaced"
    print(f"{mode} {total} ??? note line(s) in {changed_files} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
