"""Persist editor curation states outside markdown files."""
from __future__ import annotations

import json
from pathlib import Path

from .parser import coerce_sources

ALLOWED_STATES = {"skip", "no_summary", "needs_summary"}


def _item_key(item: dict) -> tuple[str, str, str]:
    return (
        str(item.get("date") or ""),
        str(item.get("title") or ""),
        str(item.get("url") or ""),
    )


def curation_sidecar_path(root: Path, rel_md_path: str) -> Path:
    rel = Path(rel_md_path)
    return (root / ".editor-curation" / rel).with_suffix(rel.suffix + ".json")


def load_curation_map(root: Path, rel_md_path: str) -> dict[tuple[str, str, str], dict]:
    path = curation_sidecar_path(root, rel_md_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    items = data.get("items")
    if not isinstance(items, list):
        return {}
    out: dict[tuple[str, str, str], dict] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = _item_key(item)
        out[key] = item
    return out


def apply_sidecar_to_links(links: list[dict], curation_map: dict[tuple[str, str, str], dict]) -> list[dict]:
    out: list[dict] = []
    for link in links:
        row = dict(link)
        if row.get("state") == "done":
            out.append(row)
            continue
        key = _item_key(row)
        saved = curation_map.get(key)
        if not saved:
            out.append(row)
            continue
        state = saved.get("state")
        if state in ALLOWED_STATES:
            row["state"] = state
        sources = coerce_sources(saved.get("sources"), source=saved.get("source"))
        if sources:
            row["sources"] = sources
            row["source"] = sources[0]
            row["pdf_path"] = next((item["ref"] for item in sources if item["type"] == "pdf"), None)
        out.append(row)
    return out


def save_curation_for_links(root: Path, rel_md_path: str, links: list[dict], curation: list[dict]) -> None:
    by_index = {
        int(link.get("line_index")): link
        for link in links
        if isinstance(link, dict) and isinstance(link.get("line_index"), int)
    }
    items: list[dict] = []
    for entry in curation:
        if not isinstance(entry, dict):
            continue
        try:
            idx = int(entry.get("line_index"))
        except (TypeError, ValueError):
            continue
        link = by_index.get(idx)
        if not link:
            continue
        state = entry.get("state")
        if state not in ALLOWED_STATES:
            continue

        item = {
            "date": link.get("date") or "",
            "title": link.get("title") or "",
            "url": link.get("url") or "",
            "state": state,
        }

        if state == "needs_summary":
            sources = coerce_sources(
                entry.get("sources"),
                source=entry.get("source"),
                pdf_path=entry.get("pdf_path"),
            )
            if sources:
                item["sources"] = sources
                item["source"] = sources[0]

        items.append(item)

    sidecar = curation_sidecar_path(root, rel_md_path)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "items": items}
    sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def curation_payload_from_links(links: list[dict]) -> list[dict]:
    """Build saver/apply payload from parsed links.

    Includes only unresolved states that saver can materialize in markdown.
    """
    out: list[dict] = []
    for link in links:
        if not isinstance(link, dict):
            continue
        state = link.get("state")
        if state not in ALLOWED_STATES:
            continue
        line_index = link.get("line_index")
        if not isinstance(line_index, int):
            continue
        row = {
            "line_index": line_index,
            "state": state,
            "pdf_path": link.get("pdf_path"),
            "title": link.get("title") or "",
        }
        sources = coerce_sources(link.get("sources"), source=link.get("source"), pdf_path=link.get("pdf_path"))
        if sources:
            row["sources"] = sources
            row["source"] = sources[0]
            row["pdf_path"] = next((item["ref"] for item in sources if item["type"] == "pdf"), None)
        out.append(row)
    return out
