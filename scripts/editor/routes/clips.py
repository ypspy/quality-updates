# -*- coding: utf-8 -*-
"""CLIP create and retrieve routes."""
import html

from flask import Blueprint, Response, jsonify, request

from ..clip_store import create_clip, get_clip
from ..preview_helpers import apply_preview_security_headers, preview_html

bp = Blueprint("clips", __name__)


@bp.route("/api/clips", methods=["POST"])
def clips_create():
    data = request.get_json(silent=True) or {}
    raw = data.get("raw")
    if not isinstance(raw, str):
        return jsonify({"error": "raw (string) required"}), 400
    if not raw.strip():
        return jsonify({"error": "raw must be non-empty"}), 400
    ct = data.get("content_type")
    if ct is not None and not isinstance(ct, str):
        return jsonify({"error": "content_type must be a string"}), 400
    try:
        clip_id = create_clip(raw, content_type=(ct or "text/plain"))
    except (TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"id": clip_id})


@bp.route("/api/clips/<clip_id>")
def clips_get(clip_id: str):
    rec = get_clip(clip_id)
    if not rec:
        return preview_html("Clip not found.", status=404)
    raw = rec.get("raw", "")
    if not isinstance(raw, str):
        raw = str(raw)
    safe = html.escape(raw, quote=False)
    page = (
        "<!doctype html><meta charset='utf-8'>"
        "<style>pre{margin:0;padding:12px;font:13px/1.45 ui-monospace,Consolas,monospace;"
        "white-space:pre-wrap;word-break:break-word;background:#fafafa;color:#111}</style>"
        f"<pre>{safe}</pre>"
    )
    resp = Response(page, status=200, mimetype="text/html")
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return apply_preview_security_headers(resp)
