# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from editor import clip_store


def test_create_and_get_clip_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(clip_store, "clips_dir", lambda: tmp_path)

    cid = clip_store.create_clip("hello\nworld", content_type="text/plain")
    assert cid.startswith("clip_")
    rec = clip_store.get_clip(cid)
    assert rec is not None
    assert rec["id"] == cid
    assert rec["raw"] == "hello\nworld"
    assert rec["content_type"] == "text/plain"
    assert rec["byte_length"] == len("hello\nworld".encode("utf-8"))
    assert len(rec["sha256"]) == 64

    path = tmp_path / f"{cid}.json"
    assert path.is_file()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["raw"] == "hello\nworld"


def test_get_clip_invalid_id():
    assert clip_store.get_clip("../evil") is None
    assert clip_store.get_clip("nope") is None


def test_create_clip_rejects_oversize(monkeypatch):
    monkeypatch.setattr(clip_store, "clips_dir", lambda: Path(tempfile.mkdtemp()))
    big = "x" * (2 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="too large"):
        clip_store.create_clip(big)


def test_get_clip_bad_json(tmp_path, monkeypatch):
    monkeypatch.setattr(clip_store, "clips_dir", lambda: tmp_path)
    p = tmp_path / "clip_1700000000_abcd1234.json"
    p.write_text("{not json", encoding="utf-8")
    assert clip_store.get_clip("clip_1700000000_abcd1234") is None
