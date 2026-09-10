# -*- coding: utf-8 -*-
"""FastMCP registration and invocation smoke tests."""

import asyncio

from mcp_server.app import mcp


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
