# -*- coding: utf-8 -*-
"""HTML sanitization + link rewriting for WEB preview.

Pipeline (deterministic, no network):
- Parse HTML
- Remove dangerous tags
- Remove dangerous attributes
- Rewrite <a href> to /api/source/preview?url=<encoded absolute url>
- Final allowlist sanitize with bleach
"""

from __future__ import annotations

import re
from urllib.parse import quote, urljoin, urlsplit

import bleach
from bs4 import BeautifulSoup


_DANGEROUS_TAGS = {"script", "style", "iframe", "object", "embed", "svg"}
_DANGEROUS_ATTRS_EXACT = {"srcdoc", "formaction"}
_URL_ATTRS = {"href", "src", "action", "xlink:href"}
_ALLOWED_URL_SCHEMES = {"http", "https", ""}  # "" == relative

_CTRL_WS_RE = re.compile(r"[\x00-\x20]+")


def _is_javascript_url(url: str) -> bool:
    # Robustly detect javascript: with whitespace/control-char obfuscation.
    u = _CTRL_WS_RE.sub("", (url or "").lower())
    return u.startswith("javascript:")


def _is_allowed_scheme(url: str) -> bool:
    u = (url or "").strip()
    scheme = urlsplit(u).scheme.lower()
    return scheme in _ALLOWED_URL_SCHEMES


def sanitize_html_for_web_preview(html: str, base_url: str) -> str:
    if not isinstance(html, str):
        raise TypeError("html must be a str")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("base_url must be a non-empty str")

    soup = BeautifulSoup(html, "html.parser")

    # (a) Remove dangerous tags early.
    for tag_name in list(_DANGEROUS_TAGS):
        for t in soup.find_all(tag_name):
            t.decompose()

    # (b) Remove dangerous attributes and rewrite <a href>.
    for el in soup.find_all(True):
        # Remove event handlers and other blocked attrs.
        if el.attrs:
            for attr in list(el.attrs.keys()):
                attr_lc = attr.lower()
                if attr_lc.startswith("on") or attr_lc in _DANGEROUS_ATTRS_EXACT:
                    del el.attrs[attr]
                    continue
                # Drop javascript: URLs in common URL-bearing attributes.
                if attr_lc in _URL_ATTRS:
                    val = el.attrs.get(attr)
                    if isinstance(val, str) and _is_javascript_url(val):
                        del el.attrs[attr]

        if el.name != "a":
            continue

        href = el.get("href")
        if not href:
            continue

        # Resolve and rewrite all non-javascript links (absolute or relative)
        # so navigation stays inside the safe preview surface.
        if not _is_allowed_scheme(href):
            del el.attrs["href"]
            continue
        abs_url = urljoin(base_url, href)
        if _is_javascript_url(abs_url):
            del el.attrs["href"]
            continue

        encoded = quote(abs_url, safe="")
        el.attrs["href"] = f"/api/source/preview?url={encoded}"
        el.attrs["rel"] = "noopener noreferrer"

    # (c) Final pass: bleach allowlist sanitization.
    allowed_tags = [
        "a",
        "p",
        "div",
        "span",
        "br",
        "ul",
        "ol",
        "li",
        "strong",
        "em",
        "b",
        "i",
        "blockquote",
        "pre",
        "code",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "hr",
    ]
    allowed_attrs = {
        "a": ["href", "title", "rel"],
    }
    cleaned = bleach.clean(
        str(soup),
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True,
    )
    return cleaned

