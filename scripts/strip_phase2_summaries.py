#!/usr/bin/env python3
"""Remove Phase 2 blocks (Executive Summary, agency tabs, implications) from quarter docs."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

AGENCY_ANCHOR = re.compile(r"^#{2,3}\s+금융감독원\s*$", re.MULTILINE)


def strip_phase2_from_text(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return text

    if lines[0].strip() == "---":
        end_fm = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_fm = i
                break
        if end_fm is None:
            return text
        rest = "\n".join(lines[end_fm + 1 :])
        match = AGENCY_ANCHOR.search(rest)
        if not match:
            return text
        head = "\n".join(lines[: end_fm + 1])
        tail = rest[match.start() :].lstrip("\n")
        if not tail.endswith("\n"):
            tail += "\n"
        return f"{head}\n\n{tail}"

    full = "\n".join(lines)
    match = AGENCY_ANCHOR.search(full)
    if not match:
        return text
    tail = full[match.start() :].lstrip("\n")
    if not tail.endswith("\n"):
        tail += "\n"
    return tail


def _default_paths(repo_root: Path) -> list[Path]:
    docs_dir = repo_root / "docs" / "quality-updates"
    paths = sorted(docs_dir.rglob("*.md"))
    return [p for p in paths if p.name != "index.md" and p.parent.name.isdigit()]


def strip_file(path: Path, *, dry_run: bool) -> tuple[bool, int]:
    original = path.read_text(encoding="utf-8")
    updated = strip_phase2_from_text(original)
    if updated == original:
        return False, 0
    removed = len(original.splitlines()) - len(updated.splitlines())
    if not dry_run:
        path.write_text(updated, encoding="utf-8")
    return True, removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Strip Phase 2 summary blocks from quarter markdown files")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files")
    parser.add_argument("--file", action="append", dest="files", help="Specific file path (repeatable)")
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

    changed = 0
    for path in paths:
        did_change, removed_lines = strip_file(path, dry_run=args.dry_run)
        if did_change:
            changed += 1
            rel = path.relative_to(repo_root)
            mode = "would strip" if args.dry_run else "stripped"
            print(f"{rel}: {mode} (~{removed_lines} lines)")

    print(f"Done: {changed} file(s) {'would change' if args.dry_run else 'updated'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
