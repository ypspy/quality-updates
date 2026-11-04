# -*- coding: utf-8 -*-
"""Copy one quarter markdown, its notes, and source files into the vault raw folder."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from quarterly_handoff import export_quarter

DEFAULT_DEST = Path(r"C:\dev\obsidian-valut\raw")
_HERE = Path(__file__).resolve().parent
_DEFAULT_DOWNLOADS = _HERE.parent / "downloads"
_DEFAULT_CLIPS = _HERE / "editor" / "clips"


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--downloads", type=Path, default=_DEFAULT_DOWNLOADS)
    parser.add_argument("--clips", type=Path, default=_DEFAULT_CLIPS)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    result = export_quarter(
        args.markdown,
        args.downloads,
        args.clips,
        args.dest,
        date.today(),
    )
    for path in result.copied:
        print(f"copied {path}")
    for path in result.skipped:
        print(f"skipped {path}")
    for name in result.waiting:
        print(f"waiting {name}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
