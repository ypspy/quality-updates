# -*- coding: utf-8 -*-
"""FastMCP app — shared tools and resources for stdio / HTTP transports."""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from mcp_server.core import (  # noqa: E402
    get_regulatory_update,
    list_quarterly_periods,
    load_corpus,
    period_item_ids,
    search_regulatory_updates,
)

mcp = FastMCP(
    "quality-updates",
    instructions=(
        "Read-only access to Korean financial regulatory updates corpus "
        "(FSS, FSC, KICPA, KASB). Use search_regulatory_updates then "
        "get_regulatory_update for note text and URLs."
    ),
)


@lru_cache(maxsize=1)
def _store():
    return load_corpus()


@mcp.tool()
def list_quarterly_periods_tool() -> dict:
    """List indexed quarterly periods and corpus metadata."""
    return list_quarterly_periods(_store())


@mcp.tool()
def search_regulatory_updates(
    query: str | None = None,
    agency: str | None = None,
    period_label: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    has_summary: bool | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search regulatory update items by keyword and filters."""
    return search_regulatory_updates(
        _store(),
        query=query,
        agency=agency,
        period_label=period_label,
        date_from=date_from,
        date_to=date_to,
        has_summary=has_summary,
        limit=limit,
    )


@mcp.tool()
def get_regulatory_update(id: str | None = None, url: str | None = None) -> dict | None:
    """Fetch one regulatory update by id or url (notes included)."""
    return get_regulatory_update(_store(), id=id, url=url)


@mcp.resource("quality-updates://corpus/manifest")
def corpus_manifest() -> str:
    """Corpus manifest JSON."""
    return json.dumps(_store().manifest, ensure_ascii=False, indent=2)


@mcp.resource("quality-updates://period/{period_label}")
def period_ids(period_label: str) -> str:
    """Item ids for a quarterly period."""
    ids = period_item_ids(_store(), period_label)
    return json.dumps({"period_label": period_label, "ids": ids}, ensure_ascii=False)
