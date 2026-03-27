# -*- coding: utf-8 -*-
"""HTML sanitization + link rewriting for WEB preview.

Pipeline (deterministic, no network):
- Parse HTML
- Remove dangerous tags
- Drop whitespace-only / empty wrappers (parents that only contain ``br``/``hr`` go too; keep ``br`` between real text and ``a[href]``)
- Remove dangerous attributes
- Rewrite <a href> to /api/source/preview?url=<encoded absolute url>
- Final allowlist sanitize with bleach
"""

from __future__ import annotations

import re
from urllib.parse import quote, urljoin, urlsplit

import bleach
from bs4 import BeautifulSoup, Comment, NavigableString


_KASB_FILEDOWN_RE = re.compile(
    r"fileDownload\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)",
    re.IGNORECASE,
)

_DANGEROUS_TAGS = {"script", "style", "iframe", "object", "embed", "svg"}
_DANGEROUS_ATTRS_EXACT = {"srcdoc", "formaction"}
_URL_ATTRS = {"href", "src", "action", "xlink:href"}
_ALLOWED_URL_SCHEMES = {"http", "https", ""}  # "" == relative

_CTRL_WS_RE = re.compile(r"[\x00-\x20]+")
# NBSP, ZW*, BOM — treat as “no visible content” for empty-tag stripping.
_WS_ONLY_RE = re.compile(r"[\s\u00a0\u200b\u200c\u200d\ufeff]*\Z", re.UNICODE)


def _is_whitespace_only_string(s: str) -> bool:
    return _WS_ONLY_RE.match(s or "") is not None


def _element_keeps_preview_value(tag) -> bool:
    """True if this element should survive empty-tag stripping."""
    name = (tag.name or "").lower()
    if name in ("br", "hr"):
        return True
    if name == "a" and tag.get("href"):
        return True
    for d in tag.descendants:
        if isinstance(d, NavigableString):
            if isinstance(d, Comment):
                continue
            if not _is_whitespace_only_string(str(d)):
                return True
            continue
        child_name = (d.name or "").lower()
        if child_name == "a" and d.get("href"):
            return True
    return False


def _strip_empty_elements(soup: BeautifulSoup) -> None:
    """Remove tags with no visible text; ``br``/``hr`` do not count as content for parents."""
    while True:
        tags = [t for t in soup.find_all(True)]
        tags.sort(key=lambda t: len(list(t.descendants)), reverse=True)
        removed_any = False
        for tag in tags:
            if _element_keeps_preview_value(tag):
                continue
            tag.decompose()
            removed_any = True
        if not removed_any:
            break


def _narrow_kasb_from_h3(soup: BeautifulSoup) -> str | None:
    """KASB: keep the title ``h3`` and everything after it among its parent's children."""
    h3 = None
    for sel in (
        "#contents h3",
        "#content h3",
        "article h3",
        "main h3",
        "#container h3",
        ".contents h3",
    ):
        h3 = soup.select_one(sel)
        if h3:
            break
    if h3 is None:
        h3 = soup.find("h3")
    if h3 is None:
        return None

    dummy = BeautifulSoup("", "html.parser")
    container = dummy.new_tag("div")
    container["class"] = "preview-kasb-from-h3"
    node = h3
    while node is not None:
        nxt = node.next_sibling
        container.append(node.extract())
        node = nxt
    return str(container)


def _unwrap_tables_to_divs(root) -> None:
    """Replace ``table`` layouts with nested ``div``s (same reading order, easier to scan)."""
    dummy = BeautifulSoup("", "html.parser")
    tables = list(root.find_all("table"))
    tables.sort(key=lambda t: len(list(t.descendants)), reverse=True)
    for table in tables:
        wrapper = dummy.new_tag("div")
        wrapper["class"] = "preview-unwrapped-table"
        for tr in table.find_all("tr"):
            row = dummy.new_tag("div")
            row["class"] = "preview-tr"
            for cell in tr.find_all(["td", "th"], recursive=False):
                cell_div = dummy.new_tag("div")
                cell_div["class"] = "preview-td"
                for child in list(cell.children):
                    cell_div.append(child.extract())
                row.append(cell_div)
            if row.contents:
                wrapper.append(row)
        table.replace_with(wrapper)


def _kasb_rewire_file_download_links(soup: BeautifulSoup) -> None:
    """KASB 첨부는 ``onclick="fileDownload('fileNo','fileSeq')"`` 만 있고 ``href``가 없음 → 에디터 프록시 GET으로 연결."""
    for a in soup.find_all("a"):
        oc = a.get("onclick")
        if not isinstance(oc, str):
            continue
        m = _KASB_FILEDOWN_RE.search(oc)
        if not m:
            continue
        file_no, file_seq = m.group(1), m.group(2)
        qn = quote(file_no, safe="")
        qs = quote(file_seq, safe="")
        a["href"] = f"/api/source/kasb_file?fileNo={qn}&fileSeq={qs}"
        a["rel"] = "noopener noreferrer"


def narrow_preview_html(html: str, page_url: str) -> str:
    """If the page is a known layout, return only the main article fragment.

    - 금융감독원 보도자료 ``view.do``: ``div.bd-view`` (목록·이전/다음글 제외).
    - 금융위원회: ``div.content``; breadcrumb·만족도 설문(``location-wrap``, ``content-foot``)은 제거.
    - 한국회계기준원: 본문 ``h3`` 이하 + ``table``을 div로 풀기 + ``fileDownload`` 첨부를 ``/api/source/kasb_file`` 로 연결.
    - 한국공인회계사회: ``table``을 행/셀 ``div``로 풀어 표시.
    """
    if not isinstance(html, str) or not html.strip():
        return html
    if not isinstance(page_url, str) or not page_url.strip():
        return html

    parts = urlsplit(page_url.strip())
    host = (parts.netloc or "").lower()
    path = (parts.path or "").lower()

    soup = BeautifulSoup(html, "html.parser")

    if "fss.or.kr" in host and "/bbs/" in path and "view.do" in path:
        main = soup.select_one("div.bd-view")
        if main:
            return str(main)

    if "fsc.go.kr" in host:
        main = soup.select_one("div.content")
        if main:
            for noise in main.select(".location-wrap, .content-foot"):
                noise.decompose()
            return str(main)

    if "kasb.or.kr" in host:
        narrowed = _narrow_kasb_from_h3(soup)
        if narrowed:
            frag = BeautifulSoup(narrowed, "html.parser")
            root = frag.find(True)
            if root is None:
                return narrowed
            _unwrap_tables_to_divs(root)
            _kasb_rewire_file_download_links(root)
            return str(frag)

    if "kicpa.or.kr" in host:
        root = soup.select_one("#contents, #content, main, article") or soup.body or soup
        _unwrap_tables_to_divs(root)
        return str(root)

    return html


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

    _strip_empty_elements(soup)

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

        # Same-origin editor endpoints (KASB 첨부 프록시 등) — 그대로 둠.
        if isinstance(href, str) and href.startswith("/api/source/"):
            el.attrs.setdefault("rel", "noopener noreferrer")
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
        "dl",
        "dt",
        "dd",
    ]
    # class: FSS 보도자료 레이아웃(subject, inline, file-list, dbdata, ico-* 등)
    allowed_attrs = {
        "a": ["href", "title", "rel", "class"],
        "div": ["class"],
        "span": ["class"],
        "h2": ["class"],
        "dl": ["class"],
        "dt": ["class"],
        "dd": ["class"],
        "i": ["class"],
        "p": ["class"],
    }
    cleaned = bleach.clean(
        str(soup),
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True,
    )
    return cleaned

