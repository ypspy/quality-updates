import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import editor.app as editor_app
from editor.clip_store import get_clip


def test_web_to_clip_requires_url(monkeypatch):
    client = editor_app.app.test_client()
    r = client.post("/api/source/web_to_clip", json={})
    assert r.status_code == 400


def test_web_to_clip_saves_html_payload(monkeypatch):
    def fake_build_preview_payload(url: str) -> dict:
        return {"kind": "html", "status": 200, "html": "<p>Hello</p>"}

    monkeypatch.setattr(editor_app, "_build_preview_payload", fake_build_preview_payload)
    client = editor_app.app.test_client()
    r = client.post("/api/source/web_to_clip", json={"url": "https://example.com"})
    assert r.status_code == 200
    data = r.get_json()
    assert data and data.get("id")
    rec = get_clip(data["id"])
    assert rec and rec.get("raw") == "Hello"


def test_web_capture_to_clip_happy_path(monkeypatch, tmp_path):
    # fake preview payload
    monkeypatch.setattr(editor_app, "_build_preview_payload", lambda url: {"kind": "html", "status": 200, "html": "<p>X</p>"})
    # fake capture + OCR
    monkeypatch.setattr(editor_app, "_capture_preview_png_bytes", lambda cleaned_html, base_url: b"PNG")
    monkeypatch.setattr(editor_app, "_ocr_png_to_text", lambda png: "OCR TEXT")
    # ensure downloads folder under tmp root
    monkeypatch.setattr(editor_app, "repo_root", lambda: tmp_path)
    (tmp_path / "downloads").mkdir(parents=True, exist_ok=True)

    client = editor_app.app.test_client()
    r = client.post("/api/source/web_capture_to_clip", json={"url": "https://example.com"})
    assert r.status_code == 200
    data = r.get_json()
    assert data and data.get("id") and data.get("path")
    rec = get_clip(data["id"])
    assert rec and "OCR TEXT" in rec.get("raw", "")

