# -*- coding: utf-8 -*-
"""Pre-deploy: remove skip pairs, validate strict, print nav/index diff hints."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from deploy_hints import all_hints
from skip_removal import remove_skip_pairs


def repo_root() -> Path:
    return _SCRIPTS.parent


def default_targets() -> list[Path]:
    base = repo_root() / "docs" / "quality-updates"
    return sorted(p for p in base.glob("*/*.md") if p.name != "index.md")


def process_file(path: Path, *, dry_run: bool) -> tuple[str, bool]:
    """Return (new_content, changed)."""
    original = path.read_text(encoding="utf-8")
    updated = remove_skip_pairs(original)
    changed = updated != original
    if changed and not dry_run:
        path.write_text(updated, encoding="utf-8")
    return updated, changed


def run_validate() -> int:
    cmd = [sys.executable, str(_SCRIPTS / "validate_content.py"), "--strict"]
    if default_targets():
        cmd.extend(str(p) for p in default_targets())
    result = subprocess.run(cmd, cwd=repo_root())
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare quality-updates docs for deploy")
    parser.add_argument("files", nargs="*", help="Markdown files (default: all quarterly docs)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files")
    args = parser.parse_args(argv)

    targets = [Path(f) for f in args.files] if args.files else default_targets()
    if not targets:
        print("[WARN] No target files found", file=sys.stderr)

    total_removed = 0
    for path in targets:
        if not path.is_file():
            print(f"[ERROR] Not found: {path}", file=sys.stderr)
            return 2
        _, changed = process_file(path, dry_run=args.dry_run)
        if changed:
            total_removed += 1
            action = "would update" if args.dry_run else "updated"
            print(f"[SKIP] {action}: {path}")

    if total_removed == 0:
        print("[INFO] No skip pairs to remove")

    if args.dry_run:
        print("[DRY-RUN] Skipping validate and file writes")
        hints = all_hints(repo_root())
        if hints.strip():
            print("\n--- Deploy hints (nav / index) ---\n")
            print(hints)
        return 0

    code = run_validate()
    if code != 0:
        print("[ERROR] validate_content --strict failed", file=sys.stderr)
        return 1

    hints = all_hints(repo_root())
    if hints.strip():
        print("\n--- Deploy hints (nav / index) ---\n")
        print(hints)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
