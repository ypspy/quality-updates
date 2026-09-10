# -*- coding: utf-8 -*-
"""FastMCP registration and invocation smoke tests."""

import asyncio
from pathlib import Path

from mcp_server.app import mcp

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mcp_sdk_excludes_v2_breaking_rename():
    """Render pip-installs latest mcp; v2 removed FastMCP (mcp.server.fastmcp)."""
    req = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    mcp_lines = [
        line.strip()
        for line in req.splitlines()
        if line.strip().startswith("mcp") and not line.strip().startswith("mcp_")
    ]
    assert mcp_lines, "mcp must be listed in requirements.txt"
    spec = mcp_lines[0]
    assert "<2" in spec, spec


def test_documented_tools_are_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}

    assert {
        "list_quarterly_periods",
        "search_regulatory_updates",
        "get_regulatory_update",
    } <= names
    assert "list_quarterly_periods_tool" not in names


def test_search_regulatory_updates_round_trip():
    result = asyncio.run(
        mcp.call_tool("search_regulatory_updates", {"query": None, "limit": 1})
    )

    assert result
