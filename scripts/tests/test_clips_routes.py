# -*- coding: utf-8 -*-
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import editor.app as editor_app
import editor.clip_store as clip_store_mod


def test_post_clip_requires_non_empty_raw():
    client = editor_app.app.test_client()
    assert client.post("/api/clips", json={}).status_code == 400
    assert client.post("/api/clips", json={"raw": "  "}).status_code == 400


def test_post_clip_and_get_escapes_html(tmp_path, monkeypatch):
    monkeypatch.setattr(clip_store_mod, "clips_dir", lambda: tmp_path)

    client = editor_app.app.test_client()
    resp = client.post("/api/clips", json={"raw": "<script>alert(1)</script>"})
    assert resp.status_code == 200
    cid = resp.get_json()["id"]

    page = client.get(f"/api/clips/{cid}")
    assert page.status_code == 200
    assert b"<script" not in page.data
    assert b"&lt;script&gt;" in page.data
    assert page.headers.get("X-Frame-Options") == "SAMEORIGIN"


def test_get_clip_not_found():
    client = editor_app.app.test_client()
    r = client.get("/api/clips/clip_1700000000_deadbeef")
    assert r.status_code == 404
