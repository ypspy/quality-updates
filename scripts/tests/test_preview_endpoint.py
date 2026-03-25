import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import editor.app as editor_app


def test_preview_missing_url_param():
    client = editor_app.app.test_client()
    resp = client.get("/api/source/preview")
    assert resp.status_code == 400


def test_preview_html_sanitizes_and_sets_headers(monkeypatch):
    def fake_fetch_url(url: str, **kwargs):
        return (
            "https://example.com/page",
            b"<html><body><h1>Hi</h1><script>alert(1)</script></body></html>",
            "text/html; charset=utf-8",
        )

    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)
    client = editor_app.app.test_client()
    resp = client.get("/api/source/preview?url=" + "https%3A%2F%2Fexample.com%2Fpage")
    assert resp.status_code == 200
    assert b"<script" not in resp.data.lower()
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "frame-ancestors 'self'" in (resp.headers.get("Content-Security-Policy") or "")


@pytest.mark.parametrize(
    "content_type, body",
    [
        ("application/pdf", b"%PDF-1.7\n%...."),
        ("application/octet-stream", b"%PDF-1.4\n%...."),
    ],
)
def test_preview_pdf_redirects_to_proxy(monkeypatch, content_type, body):
    def fake_fetch_url(url: str, **kwargs):
        return ("https://example.com/doc", body, content_type)

    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)
    client = editor_app.app.test_client()
    resp = client.get("/api/source/preview?url=" + "https%3A%2F%2Fexample.com%2Fdoc", follow_redirects=False)
    assert resp.status_code in (301, 302, 307, 308)
    loc = resp.headers.get("Location") or ""
    assert loc.startswith("/api/source/proxy?url=")

