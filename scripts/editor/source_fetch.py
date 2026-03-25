# -*- coding: utf-8 -*-
"""SSRF-safe URL validation and fetching for WEB preview.

MVP policy:
- allow only http/https
- deny localhost/loopback/private/link-local/unspecified/reserved (IPv4/IPv6)
- deny 0.0.0.0
- deny userinfo in URL
- validate every redirect hop (<=3)
- enforce connect/read timeouts and max bytes cutoff

Limitations:
- DNS rebinding: `validate_url()` resolves DNS to reject private IPs, but the actual
  TCP connection performed by `requests` may resolve again at connect time. This
  is a best-effort mitigation for the editor's local workflow, not a hardened
  production-grade SSRF firewall.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests


_ALLOWED_SCHEMES = {"http", "https"}
_ALLOWED_PORTS = {80, 443}
_MAX_REDIRECTS_DEFAULT = 3
_MAX_BYTES_DEFAULT = 5 * 1024 * 1024  # 5MB
_TIMEOUT_DEFAULT = (3.0, 8.0)  # (connect, read)


@dataclass(frozen=True)
class NormalizedUrl:
    url: str
    scheme: str
    hostname: str
    port: int | None


IpAddr = ipaddress.IPv4Address | ipaddress.IPv6Address


def _is_ip_denied(ip: IpAddr) -> bool:
    # Handle IPv4-mapped IPv6 addresses (e.g., ::ffff:127.0.0.1) explicitly.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    # Block all special ranges relevant to SSRF.
    if ip.is_loopback:
        return True
    if ip.is_private:
        return True
    if ip.is_link_local:
        return True
    if ip.is_multicast:
        return True
    if ip.is_unspecified:
        return True
    if ip.is_reserved:
        return True
    return False


def _parse_ip_literal(hostname: str) -> IpAddr | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None


def _resolve_host_addrs(hostname: str, port: int | None) -> list[IpAddr]:
    # Use getaddrinfo to resolve A/AAAA; validate every resolved address.
    # If resolution fails, treat as invalid to avoid bypass via NXDOMAIN tricks.
    try:
        infos = socket.getaddrinfo(
            hostname,
            port or 0,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
    except OSError as e:
        raise ValueError(f"hostname resolution failed: {hostname}") from e

    addrs: list[IpAddr] = []
    for _family, _socktype, _proto, _canonname, sockaddr in infos:
        ip_str = sockaddr[0]
        ip_obj = ipaddress.ip_address(ip_str)
        addrs.append(ip_obj)
    return addrs


def validate_url(url: str) -> NormalizedUrl:
    """Validate a URL under SSRF policy and return a normalized representation.

    Raises ValueError on any policy violation.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")

    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError("scheme not allowed")

    # Disallow userinfo tricks (username/password in authority).
    if parts.username is not None or parts.password is not None:
        raise ValueError("userinfo not allowed")

    hostname = parts.hostname
    if not hostname:
        raise ValueError("hostname required")
    hostname_lc = hostname.lower().strip(".")
    if hostname_lc in {"localhost"}:
        raise ValueError("localhost not allowed")

    port = parts.port
    if port is not None and port not in _ALLOWED_PORTS:
        raise ValueError("port not allowed")

    # Normalize: drop fragment, ensure path is at least "/".
    path = parts.path or "/"
    normalized = urlunsplit((scheme, parts.netloc, path, parts.query, ""))

    ip_lit = _parse_ip_literal(hostname)
    if ip_lit is not None:
        if _is_ip_denied(ip_lit):
            raise ValueError("ip not allowed")
        return NormalizedUrl(url=normalized, scheme=scheme, hostname=hostname, port=port)

    # DNS resolution check: deny if any resolved IP is denied.
    for ip_obj in _resolve_host_addrs(hostname, port):
        if _is_ip_denied(ip_obj):
            raise ValueError("resolved ip not allowed")

    return NormalizedUrl(url=normalized, scheme=scheme, hostname=hostname, port=port)


def validate_redirect_chain(urls: Iterable[str]) -> list[NormalizedUrl]:
    """Validate each URL in a redirect chain (no network)."""
    normalized: list[NormalizedUrl] = []
    for u in urls:
        normalized.append(validate_url(u))
    return normalized


def fetch_url(
    url: str,
    *,
    max_redirects: int = _MAX_REDIRECTS_DEFAULT,
    timeout: tuple[float, float] = _TIMEOUT_DEFAULT,
    max_bytes: int = _MAX_BYTES_DEFAULT,
    user_agent: str = "quality-updates-editor/1.0",
) -> tuple[str, bytes, str | None]:
    """Fetch a URL safely (manual redirects), returning (final_url, body_bytes, content_type)."""
    current = validate_url(url).url

    # No cookies/auth forwarding: use a fresh session and minimal headers.
    session = requests.Session()
    # Don't inherit proxy/auth/certs from environment (HTTP_PROXY, ~/.netrc, etc).
    session.trust_env = False
    session.cookies.clear()

    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

    for _hop in range(max_redirects + 1):
        resp = session.get(
            current,
            headers=headers,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
        )

        try:
            if 300 <= resp.status_code < 400 and "location" in resp.headers:
                loc = resp.headers["location"]
                next_url = urljoin(current, loc)
                current = validate_url(next_url).url
                continue

            # Read with cutoff.
            data = bytearray()
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                data.extend(chunk)
                if len(data) > max_bytes:
                    raise ValueError("response too large")

            content_type = resp.headers.get("content-type")
            return current, bytes(data), content_type
        finally:
            resp.close()

    raise ValueError("too many redirects")

