# -*- coding: utf-8 -*-
"""File listing, links, and downloads routes."""
from pathlib import Path

from flask import Blueprint, jsonify, request

from .. import config
from ..curation_store import apply_sidecar_to_links, load_curation_map
from ..parser import parse_links

bp = Blueprint("files", __name__)


@bp.route("/api/files")
def list_files():
    root = config.repo_root()
    updates_dir = root / "docs" / "quality-updates"
    files = list(updates_dir.rglob("*.md"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return jsonify([str(f.relative_to(root)) for f in files])


@bp.route("/api/links")
def get_links():
    file_path = request.args.get("file")
    if not file_path:
        return jsonify({"error": "file param required"}), 400
    root = config.repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({"error": "invalid path"}), 400
    if not full_path.exists():
        return jsonify({"error": "file not found"}), 404
    content = full_path.read_text(encoding="utf-8")
    links = parse_links(content)
    curation_map = load_curation_map(root, file_path)
    links = apply_sidecar_to_links(links, curation_map)
    cfg = config.load_config()
    cfg["last_file"] = file_path
    config.save_config(cfg)
    return jsonify({"links": links, "content": content})


@bp.route("/api/downloads")
def list_downloads():
    cfg = config.load_config()
    root = config.repo_root()
    try:
        downloads_folder = config._normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        downloads_folder = config._normalize_downloads_folder(config.DEFAULT_CONFIG["downloads_folder"], root=root)

    folder = root / downloads_folder
    if not folder.exists() or not folder.is_dir():
        return jsonify({"files": [], "folder_exists": False})

    files = [f for f in folder.rglob("*") if f.is_file()]
    files.sort(key=lambda p: p.as_posix().lower())
    rel = [f.relative_to(root).as_posix() for f in files]
    return jsonify({"files": rel, "folder_exists": True})


def _clear_folder_files(folder: Path) -> int:
    """Delete all files under folder (recursive), keep directories."""
    deleted = 0
    if not folder.exists() or not folder.is_dir():
        return 0
    for p in sorted(folder.rglob("*")):
        try:
            if p.is_file() or p.is_symlink():
                p.unlink()
                deleted += 1
        except FileNotFoundError:
            # Race / concurrent cleanup: ignore.
            continue
    return deleted


@bp.route("/api/downloads/clear", methods=["POST"])
def clear_downloads():
    """Delete all files in the configured downloads folder (under downloads/ only)."""
    payload = request.get_json(silent=True) or {}
    if (payload.get("confirm") or "") != "DELETE":
        return jsonify({"error": "confirmation required"}), 400

    cfg = config.load_config()
    root = config.repo_root()
    try:
        downloads_folder = config._normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        downloads_folder = config._normalize_downloads_folder(config.DEFAULT_CONFIG["downloads_folder"], root=root)

    folder = root / downloads_folder
    try:
        deleted = _clear_folder_files(folder)
    except OSError as e:
        return jsonify({"error": f"could not clear downloads: {e}"}), 500
    folder_exists = folder.exists() and folder.is_dir()
    return jsonify({
        "ok": True,
        "deleted": deleted,
        "folder": downloads_folder,
        "folder_exists": folder_exists,
    })
