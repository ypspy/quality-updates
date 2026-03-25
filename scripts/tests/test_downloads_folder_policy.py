import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import editor.app as editor_app


@pytest.mark.parametrize("bad_value", ["../", "..", "/etc", r"C:\\", "C:/", r"downloads\..\evil"])
def test_config_rejects_invalid_downloads_folder(monkeypatch, tmp_path, bad_value):
    monkeypatch.setattr(editor_app, "CONFIG_PATH", tmp_path / "editor_config.json")
    monkeypatch.setattr(editor_app, "repo_root", lambda: tmp_path)

    client = editor_app.app.test_client()
    resp = client.post("/api/config", json={"downloads_folder": bad_value})
    assert resp.status_code == 400
    data = resp.get_json() or {}
    assert "error" in data


def test_downloads_list_default_folder(monkeypatch, tmp_path):
    # Isolate config + repo root for test
    monkeypatch.setattr(editor_app, "CONFIG_PATH", tmp_path / "editor_config.json")
    monkeypatch.setattr(editor_app, "repo_root", lambda: tmp_path)

    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "a.pdf").write_bytes(b"%PDF-1.7\n%...")
    (downloads / "b.pdf").write_bytes(b"%PDF-1.7\n%...")
    (downloads / "c.txt").write_text("nope", encoding="utf-8")

    client = editor_app.app.test_client()
    resp = client.get("/api/downloads")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == ["downloads/a.pdf", "downloads/b.pdf"]

