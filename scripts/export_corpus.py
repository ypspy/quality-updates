# -*- coding: utf-8 -*-
"""Export quality-updates markdown to JSONL corpus + manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from corpus.parse import discover_quarter_files, infer_period_from_filename, parse_corpus_items  # noqa: E402
from corpus.schema import SCHEMA_VERSION  # noqa: E402

KST = timezone(timedelta(hours=9))


def repo_root() -> Path:
    return _SCRIPTS_DIR.parent


def git_sha(root: Path) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def load_site_url(root: Path) -> str:
    mkdocs = root / "mkdocs.yml"
    if not mkdocs.exists():
        return ""
    for line in mkdocs.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("site_url:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return ""


def load_public_pages(root: Path, site_url: str) -> dict[str, str]:
    """Map repo-relative doc path -> public MkDocs URL."""
    mkdocs = root / "mkdocs.yml"
    mapping: dict[str, str] = {}
    if not mkdocs.exists() or not site_url:
        return mapping
    base = site_url.rstrip("/") + "/"
    for line in mkdocs.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if ": quality-updates/" in stripped and stripped.endswith(".md"):
            path_part = stripped.split(": ", 1)[1].strip()
            doc_path = f"docs/{path_part}"
            mapping[doc_path.replace("\\", "/")] = base + path_part
    return mapping


def export_corpus(
    *,
    dry_run: bool = False,
    strict: bool = False,
    output_dir: Path | None = None,
) -> dict:
    root = repo_root()
    qu_dir = root / "docs" / "quality-updates"
    out_dir = output_dir or (root / "data" / "corpus")
    site_url = load_site_url(root)
    public_pages = load_public_pages(root, site_url)

    all_items = []
    periods: set[str] = set()

    for md_path in discover_quarter_files(qu_dir):
        rel = md_path.relative_to(root).as_posix()
        fb_label, fb_period = infer_period_from_filename(md_path.name)
        content = md_path.read_text(encoding="utf-8")
        meta, items = parse_corpus_items(
            content,
            source_doc=rel,
            public_page=public_pages.get(rel, ""),
            fallback_period_label=fb_label,
            fallback_period=fb_period,
        )
        pl = meta.get("period_label")
        if pl:
            periods.add(str(pl))
        all_items.extend(items)

    stats = {
        "item_count": len(all_items),
        "periods": sorted(periods, reverse=True),
        "done": sum(1 for i in all_items if i.summary_status == "done"),
        "no_summary": sum(1 for i in all_items if i.summary_status == "no_summary"),
        "undecided": sum(1 for i in all_items if i.summary_status == "undecided"),
    }

    if dry_run:
        return stats

    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "corpus.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for item in all_items:
            f.write(item.to_json() + "\n")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(KST).isoformat(),
        "item_count": stats["item_count"],
        "periods": stats["periods"],
        "source_commit": git_sha(root),
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if strict:
        _strict_checks(root, all_items, stats)

    return stats


def _strict_checks(root: Path, items, stats: dict) -> None:
    if stats["item_count"] < 10:
        raise SystemExit(f"strict: item_count too low ({stats['item_count']})")
    for item in items:
        if item.schema_version != SCHEMA_VERSION:
            raise SystemExit(f"strict: bad schema_version on {item.id}")
        if not item.id or not item.url or not item.period_label:
            raise SystemExit(f"strict: missing required fields on {item.id}")
    validate_script = root / "scripts" / "validate_content.py"
    if validate_script.exists():
        import subprocess

        rc = subprocess.call(
            [sys.executable, str(validate_script), "--strict"],
            cwd=root,
        )
        if rc != 0:
            raise SystemExit("strict: validate_content failed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export quality-updates corpus to JSONL")
    parser.add_argument("--dry-run", action="store_true", help="Print stats only")
    parser.add_argument("--strict", action="store_true", help="Schema + validate_content checks")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/corpus)",
    )
    args = parser.parse_args()
    stats = export_corpus(
        dry_run=args.dry_run,
        strict=args.strict,
        output_dir=args.output_dir,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
