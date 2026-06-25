# -*- coding: utf-8 -*-
"""Curation save, sync, and config routes."""
from flask import Blueprint, jsonify, request

from .. import config as cfg
from ..curation_store import (
    apply_sidecar_to_links,
    curation_payload_from_links,
    load_curation_map,
    save_curation_for_links,
)
from ..parser import parse_links
from ..saver import save_with_backup

bp = Blueprint("curation", __name__)

ALLOWED_CONFIG_KEYS = {"downloads_folder", "last_file"}


@bp.route("/api/save", methods=["POST"])
def save():
    data = request.get_json(silent=True) or {}
    file_path = data.get("file")
    curation = data.get("curation")
    if not isinstance(curation, list):
        curation = []
    if not file_path:
        return jsonify({"error": "file required"}), 400
    root = cfg.repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({"error": "invalid path"}), 400
    if not full_path.exists():
        return jsonify({"error": "file not found"}), 404
    original = full_path.read_text(encoding="utf-8")
    links = parse_links(original)
    try:
        save_curation_for_links(root, file_path, links, curation)
    except OSError as e:
        return jsonify({"error": f"Could not write curation data: {e}"}), 500
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid curation payload: {e}"}), 400
    return jsonify({"ok": True})


@bp.route("/api/sync/export_to_md", methods=["POST"])
def sync_export_to_md():
    """Write sidecar curation markers into markdown body."""
    data = request.get_json(silent=True) or {}
    file_path = data.get("file")
    if not file_path:
        return jsonify({"error": "file required"}), 400
    root = cfg.repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({"error": "invalid path"}), 400
    if not full_path.exists():
        return jsonify({"error": "file not found"}), 404

    original = full_path.read_text(encoding="utf-8")
    links = parse_links(original)
    curation_map = load_curation_map(root, file_path)
    merged_links = apply_sidecar_to_links(links, curation_map)
    curation_payload = curation_payload_from_links(merged_links)
    try:
        save_with_backup(str(full_path), original, curation_payload)
    except OSError as e:
        return jsonify({"error": f"Could not write markdown: {e}"}), 500
    return jsonify({"ok": True, "written": len(curation_payload)})


@bp.route("/api/sync/import_from_md", methods=["POST"])
def sync_import_from_md():
    """Read markdown markers and store them into sidecar curation file."""
    data = request.get_json(silent=True) or {}
    file_path = data.get("file")
    if not file_path:
        return jsonify({"error": "file required"}), 400
    root = cfg.repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({"error": "invalid path"}), 400
    if not full_path.exists():
        return jsonify({"error": "file not found"}), 404

    content = full_path.read_text(encoding="utf-8")
    links = parse_links(content)
    curation_payload = curation_payload_from_links(links)
    try:
        save_curation_for_links(root, file_path, links, curation_payload)
    except OSError as e:
        return jsonify({"error": f"Could not write curation data: {e}"}), 500
    return jsonify({"ok": True, "imported": len(curation_payload)})


@bp.route("/api/config", methods=["GET", "POST"])
def config():
    if request.method == "GET":
        return jsonify(cfg.load_config())
    cfg_data = cfg.load_config()
    payload = request.get_json(silent=True) or {}
    incoming = {k: v for k, v in payload.items() if k in ALLOWED_CONFIG_KEYS}
    if "downloads_folder" in incoming:
        try:
            incoming["downloads_folder"] = cfg._normalize_downloads_folder(incoming["downloads_folder"], root=cfg.repo_root())
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    cfg_data.update(incoming)
    cfg.save_config(cfg_data)
    return jsonify(cfg_data)
