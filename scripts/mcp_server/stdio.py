# -*- coding: utf-8
"""MCP stdio transport — Cursor / Claude Desktop."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from mcp_server.app import mcp  # noqa: E402


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
