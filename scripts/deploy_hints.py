# -*- coding: utf-8 -*-
"""Suggest mkdocs nav and docs/index.md updates before deploy (diff hints only)."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

import yaml

_NAV_MD_RE = re.compile(r"quality-updates/\d{4}/[^\s:]+\.md")
_PERIOD_FILE_RE = re.compile(
    r"docs/quality-updates/(\d{4})/(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})\.md$"
)


def _parse_front_matter_period(md_path: Path) -> tuple[str, str] | None:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    fm = yaml.safe_load(text[3:end]) or {}
    period = fm.get("period") or {}
    start = period.get("start")
    end_date = period.get("end")
    if start and end_date:
        return str(start), str(end_date)
    return None


def collect_period_files(docs_root: Path) -> list[dict]:
    rows = []
    base = docs_root / "quality-updates"
    for path in sorted(base.glob("*/*.md")):
        if path.name == "index.md":
            continue
        period = _parse_front_matter_period(path)
        if not period:
            continue
        start, end = period
        rel = path.as_posix().replace("\\", "/")
        if rel.startswith("./"):
            rel = rel[2:]
        rows.append({"path": rel, "start": start, "end": end})
    return rows


def nav_paths_from_mkdocs(mkdocs_path: Path) -> set[str]:
    data = yaml.safe_load(mkdocs_path.read_text(encoding="utf-8")) or {}
    found: set[str] = set()

    def walk(node):
        if isinstance(node, str):
            m = _NAV_MD_RE.search(node.replace("\\", "/"))
            if m:
                found.add(m.group(0))
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data.get("nav", []))
    return found


def _quarter_label(start: str, end: str) -> str:
    sm = int(start[5:7])
    q = (sm - 1) // 3 + 1
    em = int(end[5:7])
    return f"{q}분기 ({start[5:7]}–{end[5:7]}월)"


def suggest_nav_entries(missing_paths: list[dict]) -> list[str]:
  """Return suggested nav lines (not applied automatically)."""
  lines = []
  for row in sorted(missing_paths, key=lambda r: r["start"], reverse=True):
    rel = row["path"].replace("docs/", "")
    label = _quarter_label(row["start"], row["end"])
    year = row["start"][:4]
    lines.append(f'          - {label}: {rel}')
  return lines


def hint_missing_nav(repo_root: Path) -> str:
    docs = repo_root / "docs"
    mkdocs = repo_root / "mkdocs.yml"
    period_files = collect_period_files(docs)
    nav_paths = nav_paths_from_mkdocs(mkdocs)

    missing = []
    for row in period_files:
        rel_short = row["path"].replace("docs/", "")
        if rel_short not in nav_paths:
            missing.append(row)

    if not missing:
        return ""

    suggestions = suggest_nav_entries(missing)
    original = mkdocs.read_text(encoding="utf-8").splitlines(keepends=True)
    hint_block = ["# Suggested nav entries (manual review):\n"] + [ln + "\n" for ln in suggestions]
    return "".join(
        difflib.unified_diff(
            original,
            original + ["\n"] + hint_block,
            fromfile="mkdocs.yml",
            tofile="mkdocs.yml (suggested)",
        )
    )


def _latest_period_file(period_files: list[dict]) -> dict | None:
    if not period_files:
        return None
    return max(period_files, key=lambda r: r["end"])


def hint_index_latest(repo_root: Path) -> str:
    index_path = repo_root / "docs" / "index.md"
    period_files = collect_period_files(repo_root / "docs")
    latest = _latest_period_file(period_files)
    if not latest:
        return ""

    expected_suffix = latest["path"].replace("docs/quality-updates/", "quality-updates/")
    text = index_path.read_text(encoding="utf-8")
    if expected_suffix in text:
        return ""

    suggested = text
    link_pat = re.compile(r"\(quality-updates/\d{4}/[^\)]+\.md\)")
    if link_pat.search(suggested):
        suggested = link_pat.sub(f"({expected_suffix})", suggested, count=1)

    return "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            suggested.splitlines(keepends=True),
            fromfile="docs/index.md",
            tofile="docs/index.md (suggested)",
        )
    )


def all_hints(repo_root: Path) -> str:
    parts = [hint_missing_nav(repo_root), hint_index_latest(repo_root)]
    return "\n".join(p for p in parts if p.strip())
