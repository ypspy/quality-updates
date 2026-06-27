# -*- coding: utf-8 -*-
"""MCP core search/get tests (no transport)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from export_corpus import export_corpus
from mcp_server.core import (
    get_regulatory_update,
    list_quarterly_periods,
    load_corpus,
    search_regulatory_updates,
)


def test_mcp_core_search(tmp_path):
    out = tmp_path / "corpus"
    export_corpus(dry_run=False, output_dir=out)
    store = load_corpus(out)

    periods = list_quarterly_periods(store)
    assert periods["item_count"] >= 10
    assert periods["periods"]

    hits = search_regulatory_updates(store, query="내부회계", limit=5)
    assert hits
    assert all("id" in h and "url" in h for h in hits)

    item = get_regulatory_update(store, id=hits[0]["id"])
    assert item is not None
    assert item["url"] == hits[0]["url"]

    by_url = get_regulatory_update(store, url=item["url"])
    assert by_url["id"] == item["id"]

    done_only = search_regulatory_updates(store, has_summary=True, limit=3)
    assert all(h["summary_status"] == "done" for h in done_only)
