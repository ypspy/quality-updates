# -*- coding: utf-8 -*-
"""Shared corpus load, search, get for MCP transports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CorpusStore:
    manifest: dict[str, Any]
    items: list[dict[str, Any]]
    by_id: dict[str, dict[str, Any]]
    by_url: dict[str, dict[str, Any]]


def default_corpus_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "corpus"


def load_corpus(corpus_dir: Path | None = None) -> CorpusStore:
    base = corpus_dir or default_corpus_dir()
    manifest_path = base / "manifest.json"
    jsonl_path = base / "corpus.jsonl"
    if not manifest_path.exists() or not jsonl_path.exists():
        raise FileNotFoundError(
            f"Corpus not found in {base}. Run: python scripts/export_corpus.py"
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    by_url: dict[str, dict[str, Any]] = {}

    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        items.append(item)
        by_id[item["id"]] = item
        by_url[item["url"]] = item

    return CorpusStore(manifest=manifest, items=items, by_id=by_id, by_url=by_url)


def list_quarterly_periods(store: CorpusStore) -> dict[str, Any]:
    return {
        "schema_version": store.manifest.get("schema_version"),
        "periods": store.manifest.get("periods", []),
        "item_count": store.manifest.get("item_count"),
        "generated_at": store.manifest.get("generated_at"),
    }


def _item_text(item: dict[str, Any]) -> str:
    parts = [item.get("title", "")]
    for note in item.get("notes") or []:
        parts.extend(note.get("bullets") or [])
        for table in note.get("tables") or []:
            parts.extend(table)
    return "\n".join(parts).lower()


def search_regulatory_updates(
    store: CorpusStore,
    *,
    query: str | None = None,
    agency: str | None = None,
    period_label: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    has_summary: bool | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    q = (query or "").lower().strip()
    results: list[dict[str, Any]] = []

    for item in store.items:
        if agency and item.get("agency") != agency:
            continue
        if period_label and item.get("period_label") != period_label:
            continue
        if has_summary is True and item.get("summary_status") != "done":
            continue
        if has_summary is False and item.get("summary_status") == "done":
            continue
        if date_from and item.get("date", "") < date_from:
            continue
        if date_to and item.get("date", "") > date_to:
            continue
        if q and q not in _item_text(item):
            continue

        snippet = item.get("title", "")
        notes = item.get("notes") or []
        if notes and notes[0].get("bullets"):
            snippet = notes[0]["bullets"][0][:120]

        results.append(
            {
                "id": item["id"],
                "date": item.get("date"),
                "title": item.get("title"),
                "agency": item.get("agency"),
                "period_label": item.get("period_label"),
                "summary_status": item.get("summary_status"),
                "url": item.get("url"),
                "snippet": snippet,
            }
        )
        if len(results) >= limit:
            break

    return results


def get_regulatory_update(
    store: CorpusStore,
    *,
    id: str | None = None,
    url: str | None = None,
) -> dict[str, Any] | None:
    if id:
        return store.by_id.get(id)
    if url:
        return store.by_url.get(url)
    return None


def period_item_ids(store: CorpusStore, period_label: str) -> list[str]:
    return [i["id"] for i in store.items if i.get("period_label") == period_label]
