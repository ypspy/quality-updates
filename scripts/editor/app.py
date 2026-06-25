# -*- coding: utf-8 -*-
"""Flask routes for the quality-updates editor."""
import json
import os
import html
import re
import threading
import uuid
from pathlib import Path
from io import BytesIO
import tempfile
from urllib.parse import quote, unquote, unquote_to_bytes, urlsplit
from html.parser import HTMLParser

import requests
from flask import Flask, Response, jsonify, make_response, render_template, request
from time import perf_counter

from .clip_store import create_clip, get_clip
from .html_sanitize import narrow_preview_html, sanitize_html_for_web_preview
from .curation_store import (
    apply_sidecar_to_links,
    curation_payload_from_links,
    load_curation_map,
    save_curation_for_links,
)
from .parser import parse_links
from .saver import save_with_backup
from .source_fetch import _DEFAULT_BROWSER_UA, fetch_url, validate_url

app = Flask(__name__)
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" rx="6" fill="#1a1a2e"/>'
    '<path fill="#e3f2fd" d="M9 9h14v3H9zm0 6h10v3H9zm0 6h12v3H9z"/></svg>'
)
from .config import CONFIG_PATH, DEFAULT_CONFIG, load_config, save_config, repo_root, _normalize_downloads_folder
from .download_helpers import (
    _is_pdf_bytes,
    _primary_content_type,
    _should_auto_download_fetched,
    _save_fetched_allowed,
    _parse_content_disposition_filename,
    _safe_attachment_storage_name,
    _safe_pdf_storage_name,
    _unique_file_path,
    _unique_pdf_path,
    _json_save_result,
)
from .preview_helpers import (
    _PREVIEW_JOBS,
    _PREVIEW_JOBS_LOCK,
    _apply_preview_security_headers,
    _delegate_parent_fetch_download,
    _fetch_exception_user_message,
    _preview_html,
    _html_to_visible_text,
    _capture_preview_png_bytes,
    _ocr_png_to_text,
    _save_png_to_downloads,
    _safe_shot_name_from_url,
    _build_preview_payload,
    _store_preview_job,
    _run_preview_job,
)

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    resp = Response(_FAVICON_SVG, mimetype='image/svg+xml')
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


@app.route('/')
def index():
    resp = make_response(render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp


@app.route('/api/files')
def list_files():
    root = repo_root()
    updates_dir = root / 'docs' / 'quality-updates'
    files = list(updates_dir.rglob('*.md'))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
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
    curation_map = load_curation_map(root, file_path)
    links = apply_sidecar_to_links(links, curation_map)
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

    files = [f for f in folder.rglob("*") if f.is_file()]
    files.sort(key=lambda p: p.as_posix().lower())
    rel = [f.relative_to(root).as_posix() for f in files]
    return jsonify(rel)


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


@app.route("/api/downloads/clear", methods=["POST"])
def clear_downloads():
    """Delete all files in the configured downloads folder (under downloads/ only)."""
    payload = request.get_json(silent=True) or {}
    if (payload.get("confirm") or "") != "DELETE":
        return jsonify({"error": "confirmation required"}), 400

    cfg = load_config()
    root = repo_root()
    try:
        downloads_folder = _normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        downloads_folder = _normalize_downloads_folder(DEFAULT_CONFIG["downloads_folder"], root=root)

    folder = (root / downloads_folder)
    try:
        deleted = _clear_folder_files(folder)
    except OSError as e:
        return jsonify({"error": f"could not clear downloads: {e}"}), 500
    return jsonify({"ok": True, "deleted": deleted, "folder": downloads_folder})


@app.route('/api/save', methods=['POST'])
def save():
    data = request.get_json(silent=True) or {}
    file_path = data.get('file')
    curation = data.get('curation')
    if not isinstance(curation, list):
        curation = []
    if not file_path:
        return jsonify({'error': 'file required'}), 400
    root = repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({'error': 'invalid path'}), 400
    if not full_path.exists():
        return jsonify({'error': 'file not found'}), 404
    original = full_path.read_text(encoding='utf-8')
    links = parse_links(original)
    try:
        save_curation_for_links(root, file_path, links, curation)
    except OSError as e:
        return jsonify({'error': f'Could not write curation data: {e}'}), 500
    except (TypeError, ValueError) as e:
        return jsonify({'error': f'Invalid curation payload: {e}'}), 400
    return jsonify({'ok': True})


@app.route('/api/sync/export_to_md', methods=['POST'])
def sync_export_to_md():
    """Write sidecar curation markers into markdown body."""
    data = request.get_json(silent=True) or {}
    file_path = data.get('file')
    if not file_path:
        return jsonify({'error': 'file required'}), 400
    root = repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({'error': 'invalid path'}), 400
    if not full_path.exists():
        return jsonify({'error': 'file not found'}), 404

    original = full_path.read_text(encoding='utf-8')
    links = parse_links(original)
    curation_map = load_curation_map(root, file_path)
    merged_links = apply_sidecar_to_links(links, curation_map)
    curation_payload = curation_payload_from_links(merged_links)
    try:
        save_with_backup(str(full_path), original, curation_payload)
    except OSError as e:
        return jsonify({'error': f'Could not write markdown: {e}'}), 500
    return jsonify({'ok': True, 'written': len(curation_payload)})


@app.route('/api/sync/import_from_md', methods=['POST'])
def sync_import_from_md():
    """Read markdown markers and store them into sidecar curation file."""
    data = request.get_json(silent=True) or {}
    file_path = data.get('file')
    if not file_path:
        return jsonify({'error': 'file required'}), 400
    root = repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({'error': 'invalid path'}), 400
    if not full_path.exists():
        return jsonify({'error': 'file not found'}), 404

    content = full_path.read_text(encoding='utf-8')
    links = parse_links(content)
    curation_payload = curation_payload_from_links(links)
    try:
        save_curation_for_links(root, file_path, links, curation_payload)
    except OSError as e:
        return jsonify({'error': f'Could not write curation data: {e}'}), 500
    return jsonify({'ok': True, 'imported': len(curation_payload)})


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


@app.route("/api/clips", methods=["POST"])
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


@app.route("/api/clips/<clip_id>")
def clips_get(clip_id: str):
    rec = get_clip(clip_id)
    if not rec:
        return _preview_html("Clip not found.", status=404)
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
    return _apply_preview_security_headers(resp)


_KASB_DOWNLOAD_POST_URL = "https://www.kasb.or.kr/commonFile/fileDownload.do"
_KASB_ATTACHMENT_MAX_BYTES = 30 * 1024 * 1024


@app.route("/api/source/kasb_file")
def kasb_file_proxy():
    """한국회계기준원 첨부: POST로 받은 뒤 **설정된 downloads_folder**에 저장 (브라우저 기본 다운로드 경로 아님)."""
    file_no = (request.args.get("fileNo") or "").strip()
    file_seq = (request.args.get("fileSeq") or "").strip()
    if not file_no or not file_seq:
        return _json_save_result(False, "Missing query params: fileNo, fileSeq", status=400)
    if not re.match(r"^-?[0-9]+$", file_no) or not re.match(r"^[0-9]+$", file_seq):
        return _json_save_result(False, "Invalid fileNo/fileSeq.", status=400)
    try:
        validate_url(_KASB_DOWNLOAD_POST_URL)
    except ValueError:
        return _json_save_result(False, "Download URL policy error.", status=500)

    try:
        r = requests.post(
            _KASB_DOWNLOAD_POST_URL,
            data={"fileNo": file_no, "fileSeq": file_seq},
            headers={
                "User-Agent": _DEFAULT_BROWSER_UA,
                "Accept": "*/*",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
            timeout=(10, 120),
            stream=True,
        )
    except requests.RequestException as e:
        return _json_save_result(False, _fetch_exception_user_message(e), status=502)

    try:
        if not (200 <= r.status_code < 300):
            return _json_save_result(False, f"Upstream error: remote HTTP {r.status_code}", status=502)
        data = bytearray()
        for chunk in r.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            data.extend(chunk)
            if len(data) > _KASB_ATTACHMENT_MAX_BYTES:
                return _json_save_result(False, "Attachment too large.", status=413)
    finally:
        r.close()

    if len(data) == 0:
        return _json_save_result(False, "Empty file from server.", status=502)

    body = bytes(data)
    content_disp = r.headers.get("content-disposition")
    hint = _parse_content_disposition_filename(content_disp)
    fname = _safe_attachment_storage_name(hint, body, fallback_stem="kasb-attachment")

    root = repo_root()
    cfg = load_config()
    try:
        downloads_folder = _normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        downloads_folder = _normalize_downloads_folder(DEFAULT_CONFIG["downloads_folder"], root=root)

    folder = root / downloads_folder
    try:
        out_path = _unique_file_path(folder, fname)
        out_path.write_bytes(body)
    except OSError as e:
        return _json_save_result(False, f"Could not save file: {e}", status=500)

    rel = out_path.relative_to(root.resolve()).as_posix()
    return _json_save_result(True, f"첨부 저장: {out_path.name}", rel_posix=rel)


@app.route("/api/source/preview")
def source_preview():
    url = request.args.get("url")
    if not url:
        return _preview_html("Missing required query param: url", status=400)

    want_timing = (request.args.get("timing") or "").strip() == "1"
    timing: dict[str, float] | None = {} if want_timing else None
    t0 = perf_counter()

    try:
        final_url, body, content_type, _content_disp = fetch_url(url, timing=timing)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("remote HTTP") or msg == "empty response body":
            return _preview_html(f"Upstream error: {msg}", status=502)
        return _preview_html(f"Fetch blocked: {msg}", status=400)
    except Exception as e:
        return _preview_html(_fetch_exception_user_message(e), status=502)

    ct = _primary_content_type(content_type)
    is_html = ct in {"text/html", "application/xhtml+xml"} or ct.endswith("+xml") and "html" in ct
    if is_html:
        t_decode = perf_counter()
        html_text = body.decode("utf-8", errors="replace")
        decode_ms = (perf_counter() - t_decode) * 1000.0
        t_narrow = perf_counter()
        html_text = narrow_preview_html(html_text, final_url)
        narrow_ms = (perf_counter() - t_narrow) * 1000.0
        try:
            t_san = perf_counter()
            cleaned = sanitize_html_for_web_preview(html_text, base_url=final_url)
            sanitize_ms = (perf_counter() - t_san) * 1000.0
        except Exception as e:
            return _preview_html(f"Sanitization failed: {str(e)}", status=500)

        resp = Response(cleaned, status=200, mimetype="text/html")
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        if want_timing:
            total_ms = (perf_counter() - t0) * 1000.0
            resp.headers["Server-Timing"] = ", ".join(
                [
                    f"fetch;dur={timing.get('attempt_total_ms', 0.0):.1f}",
                    f"dns;dur={timing.get('validate_url_ms', 0.0):.1f}",
                    f"connect;dur={timing.get('request_ms', 0.0):.1f}",
                    f"download;dur={timing.get('download_ms', 0.0):.1f}",
                    f"decode;dur={decode_ms:.1f}",
                    f"narrow;dur={narrow_ms:.1f}",
                    f"sanitize;dur={sanitize_ms:.1f}",
                    f"total;dur={total_ms:.1f}",
                ]
            )
        return _apply_preview_security_headers(resp)

    url_path = (final_url or "").split("?", 1)[0].lower()
    is_pdf = (
        ct == "application/pdf"
        or _is_pdf_bytes(body)
        or (ct == "application/octet-stream" and (_is_pdf_bytes(body) or url_path.endswith(".pdf")))
    )
    if is_pdf or _should_auto_download_fetched(content_type, body):
        resp = _delegate_parent_fetch_download(url)
        if want_timing:
            total_ms = (perf_counter() - t0) * 1000.0
            resp.headers["Server-Timing"] = ", ".join(
                [
                    f"fetch;dur={timing.get('attempt_total_ms', 0.0):.1f}",
                    f"dns;dur={timing.get('validate_url_ms', 0.0):.1f}",
                    f"connect;dur={timing.get('request_ms', 0.0):.1f}",
                    f"download;dur={timing.get('download_ms', 0.0):.1f}",
                    f"total;dur={total_ms:.1f}",
                ]
            )
        return resp

    return _preview_html("Unsupported content type for preview.", status=415)


@app.route("/api/source/preview_fast")
def source_preview_fast():
    url = request.args.get("url")
    if not url:
        return _preview_html("Missing required query param: url", status=400)
    job_id = uuid.uuid4().hex
    _store_preview_job(job_id, {"ready": False, "stage": "접속 준비", "ts": perf_counter()})
    th = threading.Thread(target=_run_preview_job, args=(job_id, url), daemon=True)
    th.start()
    status_path = f"/api/source/preview_fast_status/{job_id}?url={quote(url, safe='')}"
    page = (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>Loading preview</title>"
        "<style>body{font:14px/1.45 sans-serif;color:#222;padding:12px}</style></head><body>"
        "<p>미리보기 로딩 중...</p><p id='preview-stage' style='color:#555'>단계: 접속 준비</p>"
        "<script>(function poll(){fetch('"
        + status_path
        + "',{cache:'no-store'}).then(function(r){return r.json();}).then(function(d){"
          "var el=document.getElementById('preview-stage');"
          "if(el && d && d.stage){el.textContent='단계: '+d.stage;}"
          "if(d && d.ready && d.next){location.replace(d.next);return;}"
          "setTimeout(poll,250);"
        "}).catch(function(){setTimeout(poll,600);});})();</script></body></html>"
    )
    resp = Response(page, status=200, mimetype="text/html")
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return _apply_preview_security_headers(resp, allow_inline_script=True, allow_connect_self=True)


@app.route("/api/source/preview_fast_status/<job_id>")
def source_preview_fast_status(job_id: str):
    with _PREVIEW_JOBS_LOCK:
        job = _PREVIEW_JOBS.get(job_id)
    if not job:
        return jsonify({"ready": True, "next": None, "error": "job not found"}), 404
    if not job.get("ready"):
        return jsonify({"ready": False, "stage": job.get("stage") or "처리 중"})
    url = request.args.get("url") or ""
    next_path = f"/api/source/preview_fast_result/{job_id}?url={quote(url, safe='')}"
    return jsonify({"ready": True, "next": next_path, "stage": job.get("stage") or "완료"})


@app.route("/api/source/preview_fast_result/<job_id>")
def source_preview_fast_result(job_id: str):
    with _PREVIEW_JOBS_LOCK:
        job = _PREVIEW_JOBS.get(job_id)
    if not job:
        return _preview_html("Preview job not found.", status=404)
    if not job.get("ready"):
        return _preview_html("Preview still processing.", status=425)
    kind = job.get("kind")
    if kind == "html":
        resp = Response(job.get("html", ""), status=int(job.get("status", 200)), mimetype="text/html")
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        return _apply_preview_security_headers(resp)
    if kind == "delegate":
        url = request.args.get("url") or ""
        return _delegate_parent_fetch_download(url)
    return _preview_html(str(job.get("message") or "Preview failed."), status=int(job.get("status", 500)))


def _source_save_fetched_impl():
    """Fetch URL and write body to downloads_folder (PDF 또는 기타 바이너리)."""
    url = request.args.get("url")
    if not url:
        return _json_save_result(False, "Missing required query param: url", status=400)

    try:
        final_url, body, content_type, content_disp = fetch_url(url)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("remote HTTP") or msg == "empty response body":
            return _json_save_result(False, f"Upstream error: {msg}", status=502)
        return _json_save_result(False, f"Fetch blocked: {msg}", status=400)
    except Exception as e:
        return _json_save_result(False, _fetch_exception_user_message(e), status=502)

    if not _save_fetched_allowed(content_type, body):
        return _json_save_result(False, "Unsupported or unsafe content type for download save.", status=415)

    root = repo_root()
    cfg = load_config()
    try:
        downloads_folder = _normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        downloads_folder = _normalize_downloads_folder(DEFAULT_CONFIG["downloads_folder"], root=root)

    folder = root / downloads_folder
    hint = _parse_content_disposition_filename(content_disp)
    try:
        if _is_pdf_bytes(body):
            fname = _safe_pdf_storage_name(hint, final_url)
            out_path = _unique_pdf_path(folder, fname)
        else:
            fname = _safe_attachment_storage_name(hint, body, fallback_stem="download")
            out_path = _unique_file_path(folder, fname)
        out_path.write_bytes(body)
    except OSError as e:
        return _json_save_result(False, f"Could not save file: {e}", status=500)

    rel = out_path.relative_to(root.resolve()).as_posix()
    label = "PDF 저장" if _is_pdf_bytes(body) else "파일 저장"
    return _json_save_result(True, f"{label}: {out_path.name}", rel_posix=rel)


@app.route("/api/source/save_fetched")
def source_save_fetched():
    return _source_save_fetched_impl()


@app.route("/api/source/save_pdf")
def source_save_pdf():
    """하위 호환: 예전 클라이언트 URL. 동작은 save_fetched와 동일."""
    return _source_save_fetched_impl()


@app.route("/api/source/web_to_clip", methods=["POST"])
def web_to_clip():
    """Fetch+sanitize WEB preview and store *visible text* as CLIP for stable summarization."""
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        payload = _build_preview_payload(url)
    except ValueError as e:
        return jsonify({"error": f"Fetch blocked: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": _fetch_exception_user_message(e)}), 502

    if payload.get("kind") != "html" or not payload.get("html"):
        msg = payload.get("message") or "Preview is not HTML; cannot save to clip."
        return jsonify({"error": str(msg)}), 415

    text = _html_to_visible_text(str(payload["html"]))
    if not text.strip():
        return jsonify({"error": "미리보기에서 추출할 텍스트가 없습니다."}), 422

    try:
        clip_id = create_clip(text, content_type="text/plain")
    except (TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"id": clip_id})


@app.route("/api/source/web_capture_to_clip", methods=["POST"])
def web_capture_to_clip():
    """Capture WEB preview as screenshot + OCR -> CLIP, and store PNG in downloads."""
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400

    try:
        payload = _build_preview_payload(url)
    except ValueError as e:
        return jsonify({"error": f"Fetch blocked: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": _fetch_exception_user_message(e)}), 502

    if payload.get("kind") != "html" or not payload.get("html"):
        msg = payload.get("message") or "Preview is not HTML; cannot capture."
        return jsonify({"error": str(msg)}), 415

    cleaned_html = str(payload["html"])
    try:
        png = _capture_preview_png_bytes(cleaned_html, base_url=url)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 501

    rel_png = _save_png_to_downloads(png, filename_hint=_safe_shot_name_from_url(url))

    try:
        ocr_text = _ocr_png_to_text(png)
    except RuntimeError as e:
        # Still return screenshot path so user has evidence, but no clip.
        return jsonify({"error": str(e), "path": rel_png}), 501

    if not ocr_text.strip():
        return jsonify({"error": "OCR 결과가 비어 있습니다.", "path": rel_png}), 422

    clip_body = f"[WEB 미리보기 캡쳐 OCR]\n- url: {url}\n- screenshot: {rel_png}\n\n{ocr_text}\n"
    try:
        clip_id = create_clip(clip_body, content_type="text/plain")
    except (TypeError, ValueError) as e:
        return jsonify({"error": str(e), "path": rel_png}), 400

    return jsonify({"id": clip_id, "path": rel_png})


@app.route("/api/source/proxy")
def source_proxy():
    url = request.args.get("url")
    if not url:
        return _preview_html("Missing required query param: url", status=400)

    try:
        final_url, body, content_type, _content_disp = fetch_url(url)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("remote HTTP") or msg == "empty response body":
            return _preview_html(f"Upstream error: {msg}", status=502)
        return _preview_html(f"Fetch blocked: {msg}", status=400)
    except Exception as e:
        return _preview_html(_fetch_exception_user_message(e), status=502)

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
