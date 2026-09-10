# -*- coding: utf-8 -*-
"""Hosted Streamable HTTP transport: Bearer + public Render Host."""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.testclient import TestClient

MCP_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}


def _reload_http_app():
    import mcp_server.app as app_mod
    import mcp_server.http as http_mod

    app_mod.mcp._session_manager = None
    return importlib.reload(http_mod)


def test_mcp_http_accepts_render_public_host(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", "test-key")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "quality-updates-mcp.onrender.com")
    http_mod = _reload_http_app()

    with TestClient(
        http_mod.app,
        base_url="https://quality-updates-mcp.onrender.com",
    ) as client:
        response = client.post(
            "/mcp",
            headers={
                "Authorization": "Bearer test-key",
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json=MCP_INITIALIZE,
        )

    assert response.status_code != 421, response.text
    assert "Invalid Host header" not in response.text
