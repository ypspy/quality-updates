import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import editor.app as editor_app


def test_proxy_rejects_non_pdf_content_type(monkeypatch):
    def fake_fetch_url(url: str, **kwargs):
        return ("https://example.com/page", b"<html>no</html>", "text/html; charset=utf-8")

    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)

    client = editor_app.app.test_client()
    resp = client.get("/api/source/proxy?url=" + "https%3A%2F%2Fexample.com%2Fpage")
    assert resp.status_code == 415
    assert (resp.headers.get("Content-Type") or "").startswith("text/html")


@pytest.mark.parametrize(
    "content_type",
    ["application/pdf", "application/octet-stream"],
)
def test_proxy_serves_pdf_bytes(monkeypatch, content_type):
    pdf_bytes = b"%PDF-1.7\n%....\n1 0 obj\n<<>>\nendobj\n"

    def fake_fetch_url(url: str, **kwargs):
        return ("https://example.com/doc.pdf", pdf_bytes, content_type)

    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)

    client = editor_app.app.test_client()
    resp = client.get("/api/source/proxy?url=" + "https%3A%2F%2Fexample.com%2Fdoc.pdf")
    assert resp.status_code == 200
    assert resp.data == pdf_bytes
    assert (resp.headers.get("Content-Type") or "").startswith("application/pdf")
    cd = resp.headers.get("Content-Disposition") or ""
    assert cd.startswith("inline")


def test_proxy_rejects_octet_stream_non_pdf_magic(monkeypatch):
    def fake_fetch_url(url: str, **kwargs):
        return ("https://example.com/file", b"NOTPDF", "application/octet-stream")

    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)

    client = editor_app.app.test_client()
    resp = client.get("/api/source/proxy?url=" + "https%3A%2F%2Fexample.com%2Ffile")
    assert resp.status_code == 415


def test_proxy_rejects_pdf_content_type_without_pdf_magic(monkeypatch):
    def fake_fetch_url(url: str, **kwargs):
        return ("https://example.com/doc.pdf", b"NOTPDF", "application/pdf")

    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)

    client = editor_app.app.test_client()
    resp = client.get("/api/source/proxy?url=" + "https%3A%2F%2Fexample.com%2Fdoc.pdf")
    assert resp.status_code == 415

