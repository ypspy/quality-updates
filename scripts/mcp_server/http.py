# -*- coding: utf-8
"""MCP Streamable HTTP transport — Render Web Service."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from mcp_server.app import mcp

API_KEY_ENV = "MCP_API_KEY"


def _http_transport_security() -> TransportSecuritySettings:
    hosts = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*", "[::1]:*"]
    extras = [os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()]
    extras.extend(
        part.strip()
        for part in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",")
        if part.strip()
    )
    for host in extras:
        if not host:
            continue
        hosts.append(host)
        if ":*" not in host:
            hosts.append(f"{host}:*")
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
    )


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ("/health",):
            return await call_next(request)
        expected = os.environ.get(API_KEY_ENV, "").strip()
        if not expected:
            return JSONResponse(
                {"error": f"{API_KEY_ENV} not configured"},
                status_code=503,
            )
        auth = request.headers.get("authorization", "")
        if auth != f"Bearer {expected}":
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


mcp.settings.transport_security = _http_transport_security()
mcp._session_manager = None
app = mcp.streamable_http_app()
app.add_middleware(BearerAuthMiddleware)


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "mcp_server.http:app",
        host="0.0.0.0",
        port=port,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
