# -*- coding: utf-8 -*-
"""Flask routes for the quality-updates editor."""
import json
import os
import html
from pathlib import Path
from urllib.parse import quote

from flask import Flask, Response, jsonify, redirect, render_template, request

from .html_sanitize import sanitize_html_for_web_preview
from .parser import parse_links
from .saver import save_with_backup
from .source_fetch import fetch_url

app = Flask(__name__)

CONFIG_PATH = Path(__file__).parent.parent / 'editor_config.json'
DEFAULT_CONFIG = {
    'downloads_folder': 'downloads/',
    'last_file': '',
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding='utf-8') as f:
            cfg = json.load(f)
        merged = {**DEFAULT_CONFIG, **cfg}
    else:
        merged = dict(DEFAULT_CONFIG)

    # Defensive normalization so a stale/hand-edited config can't escape policy.
    try:
        merged["downloads_folder"] = _normalize_downloads_folder(merged.get("downloads_folder"), root=repo_root())
    except Exception:
        merged["downloads_folder"] = DEFAULT_CONFIG["downloads_folder"]
    return merged


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def repo_root() -> Path:
    """Return repository root (parent of scripts/)."""
    return Path(__file__).parent.parent.parent


def _normalize_downloads_folder(folder_value: object, *, root: Path) -> str:
    """Return normalized downloads folder as a repo-root-relative posix path ending with '/'.

    Policy:
    - must be a relative path (no absolute paths, no drive roots)
    - must not contain path traversal ("..")
    - resolved path must be under repo_root/downloads/
    """
    if not isinstance(folder_value, str) or not folder_value.strip():
        raise ValueError("downloads_folder must be a non-empty string")

    raw = folder_value.strip()
    p = Path(raw)

    if p.is_absolute():
        raise ValueError("downloads_folder must be relative")
    if any(part == ".." for part in p.parts):
        raise ValueError("downloads_folder must not contain '..'")

    root_resolved = root.resolve()
    base = (root_resolved / "downloads").resolve()
    full = (root_resolved / p).resolve()

    if not full.is_relative_to(base):
        raise ValueError("downloads_folder must be under downloads/")

    rel = full.relative_to(root_resolved).as_posix().rstrip("/") + "/"
    if not rel.startswith("downloads/"):
        # Defensive: should be guaranteed by is_relative_to(base) check.
        raise ValueError("downloads_folder must be under downloads/")
    return rel


def _is_pdf_bytes(data: bytes) -> bool:
    if not isinstance(data, (bytes, bytearray)):
        return False
    # PDF signature: "%PDF-" at file start (allow UTF-8 BOM/whitespace before it)
    head = bytes(data[:1024])
    stripped = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    return stripped.startswith(b"%PDF-")


def _apply_preview_security_headers(resp: Response) -> Response:
    # Allow embedding only by this editor (same-origin iframe).
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    # Block remote resource loading; preview should be self-contained.
    resp.headers["Content-Security-Policy"] = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _preview_html(message: str, *, status: int) -> Response:
    safe = html.escape(str(message), quote=False)
    resp = Response(f"<!doctype html><meta charset='utf-8'><p>{safe}</p>", status=status, mimetype="text/html")
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return _apply_preview_security_headers(resp)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/files')
def list_files():
    root = repo_root()
    updates_dir = root / 'docs' / 'quality-updates'
    files = sorted(updates_dir.rglob('*.md'))
    return jsonify([str(f.relative_to(root)) for f in files])


@app.route('/api/links')
def get_links():
    file_path = request.args.get('file')
    if not file_path:
        return jsonify({'error': 'file param required'}), 400
    root = repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({'error': 'invalid path'}), 400
    if not full_path.exists():
        return jsonify({'error': 'file not found'}), 404
    content = full_path.read_text(encoding='utf-8')
    links = parse_links(content)
    cfg = load_config()
    cfg['last_file'] = file_path
    save_config(cfg)
    return jsonify({'links': links, 'content': content})


@app.route('/api/downloads')
def list_downloads():
    cfg = load_config()
    root = repo_root()
    try:
        downloads_folder = _normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        downloads_folder = _normalize_downloads_folder(DEFAULT_CONFIG["downloads_folder"], root=root)

    folder = (root / downloads_folder)
    if not folder.exists() or not folder.is_dir():
        return jsonify([])

    files = sorted(folder.glob("*.pdf"))
    rel = [f.relative_to(root).as_posix() for f in files]
    return jsonify(rel)


@app.route('/api/save', methods=['POST'])
def save():
    data = request.get_json(silent=True) or {}
    file_path = data.get('file')
    curation = data.get('curation', [])
    if not file_path:
        return jsonify({'error': 'file required'}), 400
    root = repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({'error': 'invalid path'}), 400
    if not full_path.exists():
        return jsonify({'error': 'file not found'}), 404
    original = full_path.read_text(encoding='utf-8')
    save_with_backup(str(full_path), original, curation)
    return jsonify({'ok': True})


ALLOWED_CONFIG_KEYS = {'downloads_folder', 'last_file'}

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        return jsonify(load_config())
    cfg = load_config()
    payload = request.get_json(silent=True) or {}
    incoming = {k: v for k, v in payload.items() if k in ALLOWED_CONFIG_KEYS}
    if "downloads_folder" in incoming:
        try:
            incoming["downloads_folder"] = _normalize_downloads_folder(incoming["downloads_folder"], root=repo_root())
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    cfg.update(incoming)
    save_config(cfg)
    return jsonify(cfg)


@app.route("/api/source/preview")
def source_preview():
    url = request.args.get("url")
    if not url:
        return _preview_html("Missing required query param: url", status=400)

    try:
        final_url, body, content_type = fetch_url(url)
    except ValueError as e:
        return _preview_html(f"Fetch blocked: {str(e)}", status=400)
    except Exception as e:
        return _preview_html(f"Fetch failed: {str(e)}", status=502)

    ct = (content_type or "").split(";", 1)[0].strip().lower()

    is_html = ct in {"text/html", "application/xhtml+xml"} or ct.endswith("+xml") and "html" in ct
    url_path = (final_url or "").split("?", 1)[0].lower()
    is_pdf = (
        ct == "application/pdf"
        or _is_pdf_bytes(body)
        or (ct == "application/octet-stream" and (_is_pdf_bytes(body) or url_path.endswith(".pdf")))
    )

    if is_pdf:
        # Contract: PDF is served via proxy (Task 3D). Redirect now so the client flow is stable.
        resp = redirect(f"/api/source/proxy?url={quote(url, safe='')}", code=302)
        return _apply_preview_security_headers(resp)

    if not is_html:
        return _preview_html("Unsupported content type for preview.", status=415)

    html_text = body.decode("utf-8", errors="replace")
    try:
        cleaned = sanitize_html_for_web_preview(html_text, base_url=final_url)
    except Exception as e:
        return _preview_html(f"Sanitization failed: {str(e)}", status=500)

    resp = Response(cleaned, status=200, mimetype="text/html")
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return _apply_preview_security_headers(resp)


@app.route("/api/source/proxy")
def source_proxy():
    url = request.args.get("url")
    if not url:
        return _preview_html("Missing required query param: url", status=400)

    try:
        final_url, body, content_type = fetch_url(url)
    except ValueError as e:
        return _preview_html(f"Fetch blocked: {str(e)}", status=400)
    except Exception as e:
        return _preview_html(f"Fetch failed: {str(e)}", status=502)

    ct = (content_type or "").split(";", 1)[0].strip().lower()
    allowed_ct = ct in {"application/pdf", "application/octet-stream"}
    if not allowed_ct or not _is_pdf_bytes(body):
        return _preview_html("Unsupported content type.", status=415)

    resp = Response(body, status=200, mimetype="application/pdf")
    # Minimal safe header set: do not forward hop-by-hop / arbitrary upstream headers.
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Length"] = str(len(body))
    resp.headers["Content-Disposition"] = 'inline; filename="document.pdf"'
    return _apply_preview_security_headers(resp)
