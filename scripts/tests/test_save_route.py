import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import editor.app as editor_app


def test_save_accepts_null_curation(tmp_path, monkeypatch):
    """JSON null curation must not crash the server (was TypeError in apply_curation)."""
    root = tmp_path
    md = root / "docs" / "x.md"
    md.parent.mkdir(parents=True)
    md.write_text("- (25-01-01) [T](https://example.com/a)\n", encoding="utf-8")

    monkeypatch.setattr(editor_app, "repo_root", lambda: root)

    client = editor_app.app.test_client()
    resp = client.post(
        "/api/save",
        json={"file": "docs/x.md", "curation": None},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_save_rejects_bad_line_index_entries(tmp_path, monkeypatch):
    root = tmp_path
    md = root / "docs" / "x.md"
    md.parent.mkdir(parents=True)
    md.write_text("- (25-01-01) [T](https://example.com/a)\n", encoding="utf-8")
    monkeypatch.setattr(editor_app, "repo_root", lambda: root)

    client = editor_app.app.test_client()
    resp = client.post(
        "/api/save",
        json={
            "file": "docs/x.md",
            "curation": [{"line_index": "not-a-number", "state": "undecided"}],
        },
    )
    assert resp.status_code == 200
    body = md.read_text(encoding="utf-8")
    assert "example.com" in body


def test_save_persists_to_sidecar_without_mutating_markdown(tmp_path, monkeypatch):
    root = tmp_path
    md = root / "docs" / "x.md"
    md.parent.mkdir(parents=True)
    original = "- (25-01-01) [T](https://example.com/a)\n"
    md.write_text(original, encoding="utf-8")
    monkeypatch.setattr(editor_app, "repo_root", lambda: root)

    client = editor_app.app.test_client()
    resp = client.post(
        "/api/save",
        json={
            "file": "docs/x.md",
            "curation": [
                {
                    "line_index": 0,
                    "state": "skip",
                    "source": None,
                    "pdf_path": None,
                }
            ],
        },
    )
    assert resp.status_code == 200

    assert md.read_text(encoding="utf-8") == original
    sidecar = root / ".editor-curation" / "docs" / "x.md.json"
    assert sidecar.exists()


def test_links_overlay_uses_sidecar_state(tmp_path, monkeypatch):
    root = tmp_path
    md = root / "docs" / "x.md"
    md.parent.mkdir(parents=True)
    md.write_text("- (25-01-01) [T](https://example.com/a)\n", encoding="utf-8")
    monkeypatch.setattr(editor_app, "repo_root", lambda: root)
    client = editor_app.app.test_client()

    save_resp = client.post(
        "/api/save",
        json={
            "file": "docs/x.md",
            "curation": [
                {
                    "line_index": 0,
                    "state": "needs_summary",
                    "source": {"type": "pdf", "ref": "downloads/a.pdf"},
                    "pdf_path": "downloads/a.pdf",
                }
            ],
        },
    )
    assert save_resp.status_code == 200

    links_resp = client.get("/api/links?file=docs/x.md")
    assert links_resp.status_code == 200
    payload = links_resp.get_json()
    assert payload and isinstance(payload.get("links"), list)
    row = payload["links"][0]
    assert row["state"] == "needs_summary"
    assert row["source"] == {"type": "pdf", "ref": "downloads/a.pdf"}


def test_export_to_md_writes_markers_from_sidecar(tmp_path, monkeypatch):
    root = tmp_path
    md = root / "docs" / "x.md"
    md.parent.mkdir(parents=True)
    md.write_text("- (25-01-01) [T](https://example.com/a)\n", encoding="utf-8")
    monkeypatch.setattr(editor_app, "repo_root", lambda: root)
    client = editor_app.app.test_client()

    save_resp = client.post(
        "/api/save",
        json={"file": "docs/x.md", "curation": [{"line_index": 0, "state": "skip"}]},
    )
    assert save_resp.status_code == 200

    export_resp = client.post("/api/sync/export_to_md", json={"file": "docs/x.md"})
    assert export_resp.status_code == 200
    body = md.read_text(encoding="utf-8")
    assert "<!-- skip -->" in body


def test_import_from_md_writes_sidecar(tmp_path, monkeypatch):
    root = tmp_path
    md = root / "docs" / "x.md"
    md.parent.mkdir(parents=True)
    md.write_text(
        "- (25-01-01) [T](https://example.com/a)\n<!-- source: pdf|downloads/a.pdf -->\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(editor_app, "repo_root", lambda: root)
    client = editor_app.app.test_client()

    import_resp = client.post("/api/sync/import_from_md", json={"file": "docs/x.md"})
    assert import_resp.status_code == 200
    sidecar = root / ".editor-curation" / "docs" / "x.md.json"
    assert sidecar.exists()
    text = sidecar.read_text(encoding="utf-8")
    assert '"state": "needs_summary"' in text
    assert '"type": "pdf"' in text


def test_no_summary_roundtrip_export_import(tmp_path, monkeypatch):
    root = tmp_path
    md = root / "docs" / "x.md"
    md.parent.mkdir(parents=True)
    md.write_text("- (25-01-01) [T](https://example.com/a)\n", encoding="utf-8")
    monkeypatch.setattr(editor_app, "repo_root", lambda: root)
    client = editor_app.app.test_client()

    save_resp = client.post(
        "/api/save",
        json={"file": "docs/x.md", "curation": [{"line_index": 0, "state": "no_summary"}]},
    )
    assert save_resp.status_code == 200

    export_resp = client.post("/api/sync/export_to_md", json={"file": "docs/x.md"})
    assert export_resp.status_code == 200
    body = md.read_text(encoding="utf-8")
    assert "<!-- no_summary -->" in body

    # Now import back from md into sidecar
    import_resp = client.post("/api/sync/import_from_md", json={"file": "docs/x.md"})
    assert import_resp.status_code == 200

    links_resp = client.get("/api/links?file=docs/x.md")
    row = links_resp.get_json()["links"][0]
    assert row["state"] == "no_summary"
