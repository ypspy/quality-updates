# -*- coding: utf-8 -*-
"""Source preview, proxy, download, and web-to-clip routes."""
import re
import threading
import uuid
from time import perf_counter
from urllib.parse import quote

import requests
from flask import Blueprint, Response, jsonify, request

from .. import config, download_helpers, preview_helpers, source_fetch
from ..clip_store import create_clip
from ..html_sanitize import narrow_preview_html, sanitize_html_for_web_preview

bp = Blueprint("source", __name__)

_KASB_DOWNLOAD_POST_URL = "https://www.kasb.or.kr/commonFile/fileDownload.do"
_KASB_ATTACHMENT_MAX_BYTES = 30 * 1024 * 1024


@bp.route("/api/source/kasb_file")
def kasb_file_proxy():
    """한국회계기준원 첨부: POST로 받은 뒤 **설정된 downloads_folder**에 저장 (브라우저 기본 다운로드 경로 아님)."""
    file_no = (request.args.get("fileNo") or "").strip()
    file_seq = (request.args.get("fileSeq") or "").strip()
    if not file_no or not file_seq:
        return download_helpers.json_save_result(False, "Missing query params: fileNo, fileSeq", status=400)
    if not re.match(r"^-?[0-9]+$", file_no) or not re.match(r"^[0-9]+$", file_seq):
        return download_helpers.json_save_result(False, "Invalid fileNo/fileSeq.", status=400)
    try:
        source_fetch.validate_url(_KASB_DOWNLOAD_POST_URL)
    except ValueError:
        return download_helpers.json_save_result(False, "Download URL policy error.", status=500)

    try:
        r = requests.post(
            _KASB_DOWNLOAD_POST_URL,
            data={"fileNo": file_no, "fileSeq": file_seq},
            headers={
                "User-Agent": source_fetch._DEFAULT_BROWSER_UA,
                "Accept": "*/*",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
            timeout=(10, 120),
            stream=True,
        )
    except requests.RequestException as e:
        return download_helpers.json_save_result(False, preview_helpers.fetch_exception_user_message(e), status=502)

    try:
        if not (200 <= r.status_code < 300):
            return download_helpers.json_save_result(False, f"Upstream error: remote HTTP {r.status_code}", status=502)
        data = bytearray()
        for chunk in r.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            data.extend(chunk)
            if len(data) > _KASB_ATTACHMENT_MAX_BYTES:
                return download_helpers.json_save_result(False, "Attachment too large.", status=413)
    finally:
        r.close()

    if len(data) == 0:
        return download_helpers.json_save_result(False, "Empty file from server.", status=502)

    body = bytes(data)
    content_disp = r.headers.get("content-disposition")
    hint = download_helpers.parse_content_disposition_filename(content_disp)
    fname = download_helpers.safe_attachment_storage_name(hint, body, fallback_stem="kasb-attachment")

    root = config.repo_root()
    cfg = config.load_config()
    try:
        downloads_folder = config._normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        downloads_folder = config._normalize_downloads_folder(config.DEFAULT_CONFIG["downloads_folder"], root=root)

    folder = root / downloads_folder
    try:
        out_path = download_helpers.unique_file_path(folder, fname)
        out_path.write_bytes(body)
    except OSError as e:
        return download_helpers.json_save_result(False, f"Could not save file: {e}", status=500)

    rel = out_path.relative_to(root.resolve()).as_posix()
    return download_helpers.json_save_result(True, f"첨부 저장: {out_path.name}", rel_posix=rel)


@bp.route("/api/source/preview")
def source_preview():
    url = request.args.get("url")
    if not url:
        return preview_helpers.preview_html("Missing required query param: url", status=400)

    want_timing = (request.args.get("timing") or "").strip() == "1"
    timing: dict[str, float] | None = {} if want_timing else None
    t0 = perf_counter()

    try:
        final_url, body, content_type, _content_disp = source_fetch.fetch_url(url, timing=timing)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("remote HTTP") or msg == "empty response body":
            return preview_helpers.preview_html(f"Upstream error: {msg}", status=502)
        return preview_helpers.preview_html(f"Fetch blocked: {msg}", status=400)
    except Exception as e:
        return preview_helpers.preview_html(preview_helpers.fetch_exception_user_message(e), status=502)

    ct = download_helpers.primary_content_type(content_type)
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
            return preview_helpers.preview_html(f"Sanitization failed: {str(e)}", status=500)

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
        return preview_helpers.apply_preview_security_headers(resp)

    url_path = (final_url or "").split("?", 1)[0].lower()
    is_pdf = (
        ct == "application/pdf"
        or download_helpers.is_pdf_bytes(body)
        or (ct == "application/octet-stream" and (download_helpers.is_pdf_bytes(body) or url_path.endswith(".pdf")))
    )
    if is_pdf or download_helpers.should_auto_download_fetched(content_type, body):
        resp = preview_helpers.delegate_parent_fetch_download(url)
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

    return preview_helpers.preview_html("Unsupported content type for preview.", status=415)


@bp.route("/api/source/preview_fast")
def source_preview_fast():
    url = request.args.get("url")
    if not url:
        return preview_helpers.preview_html("Missing required query param: url", status=400)
    job_id = uuid.uuid4().hex
    preview_helpers.store_preview_job(job_id, {"ready": False, "stage": "접속 준비", "ts": perf_counter()})
    th = threading.Thread(target=preview_helpers.run_preview_job, args=(job_id, url), daemon=True)
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
    return preview_helpers.apply_preview_security_headers(resp, allow_inline_script=True, allow_connect_self=True)


@bp.route("/api/source/preview_fast_status/<job_id>")
def source_preview_fast_status(job_id: str):
    with preview_helpers._PREVIEW_JOBS_LOCK:
        job = preview_helpers._PREVIEW_JOBS.get(job_id)
    if not job:
        return jsonify({
            "ready": False,
            "stage": "미리보기 세션이 만료되었습니다. WEB 미리보기를 다시 여세요.",
            "error": "job not found",
        }), 404
    if not job.get("ready"):
        return jsonify({"ready": False, "stage": job.get("stage") or "처리 중"})
    url = request.args.get("url") or ""
    next_path = f"/api/source/preview_fast_result/{job_id}?url={quote(url, safe='')}"
    return jsonify({"ready": True, "next": next_path, "stage": job.get("stage") or "완료"})


@bp.route("/api/source/preview_fast_result/<job_id>")
def source_preview_fast_result(job_id: str):
    with preview_helpers._PREVIEW_JOBS_LOCK:
        job = preview_helpers._PREVIEW_JOBS.get(job_id)
    if not job:
        return preview_helpers.preview_html("Preview job not found.", status=404)
    if not job.get("ready"):
        return preview_helpers.preview_html("Preview still processing.", status=425)
    kind = job.get("kind")
    if kind == "html":
        resp = Response(job.get("html", ""), status=int(job.get("status", 200)), mimetype="text/html")
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        return preview_helpers.apply_preview_security_headers(resp)
    if kind == "delegate":
        url = request.args.get("url") or ""
        return preview_helpers.delegate_parent_fetch_download(url)
    return preview_helpers.preview_html(str(job.get("message") or "Preview failed."), status=int(job.get("status", 500)))


def _source_save_fetched_impl():
    """Fetch URL and write body to downloads_folder (PDF 또는 기타 바이너리)."""
    url = request.args.get("url")
    if not url:
        return download_helpers.json_save_result(False, "Missing required query param: url", status=400)

    try:
        final_url, body, content_type, content_disp = source_fetch.fetch_url(url)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("remote HTTP") or msg == "empty response body":
            return download_helpers.json_save_result(False, f"Upstream error: {msg}", status=502)
        return download_helpers.json_save_result(False, f"Fetch blocked: {msg}", status=400)
    except Exception as e:
        return download_helpers.json_save_result(False, preview_helpers.fetch_exception_user_message(e), status=502)

    if not download_helpers.save_fetched_allowed(content_type, body):
        return download_helpers.json_save_result(False, "Unsupported or unsafe content type for download save.", status=415)

    root = config.repo_root()
    cfg = config.load_config()
    try:
        downloads_folder = config._normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        downloads_folder = config._normalize_downloads_folder(config.DEFAULT_CONFIG["downloads_folder"], root=root)

    folder = root / downloads_folder
    hint = download_helpers.parse_content_disposition_filename(content_disp)
    try:
        if download_helpers.is_pdf_bytes(body):
            fname = download_helpers.safe_pdf_storage_name(hint, final_url)
            out_path = download_helpers.unique_pdf_path(folder, fname)
        else:
            fname = download_helpers.safe_attachment_storage_name(hint, body, fallback_stem="download")
            out_path = download_helpers.unique_file_path(folder, fname)
        out_path.write_bytes(body)
    except OSError as e:
        return download_helpers.json_save_result(False, f"Could not save file: {e}", status=500)

    rel = out_path.relative_to(root.resolve()).as_posix()
    label = "PDF 저장" if download_helpers.is_pdf_bytes(body) else "파일 저장"
    return download_helpers.json_save_result(True, f"{label}: {out_path.name}", rel_posix=rel)


@bp.route("/api/source/save_fetched")
def source_save_fetched():
    return _source_save_fetched_impl()


@bp.route("/api/source/save_pdf")
def source_save_pdf():
    """하위 호환: 예전 클라이언트 URL. 동작은 save_fetched와 동일."""
    return _source_save_fetched_impl()


@bp.route("/api/source/web_to_clip", methods=["POST"])
def web_to_clip():
    """Fetch+sanitize WEB preview and store *visible text* as CLIP for stable summarization."""
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        payload = preview_helpers.build_preview_payload(url)
    except ValueError as e:
        return jsonify({"error": f"Fetch blocked: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": preview_helpers.fetch_exception_user_message(e)}), 502

    if payload.get("kind") != "html" or not payload.get("html"):
        msg = payload.get("message") or "Preview is not HTML; cannot save to clip."
        return jsonify({"error": str(msg)}), 415

    text = preview_helpers.html_to_visible_text(str(payload["html"]))
    if not text.strip():
        return jsonify({"error": "미리보기에서 추출할 텍스트가 없습니다."}), 422

    try:
        clip_id = create_clip(text, content_type="text/plain")
    except (TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"id": clip_id})


@bp.route("/api/source/web_capture_to_clip", methods=["POST"])
def web_capture_to_clip():
    """Capture WEB preview as screenshot + OCR -> CLIP, and store PNG in downloads."""
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400

    try:
        payload = preview_helpers.build_preview_payload(url)
    except ValueError as e:
        return jsonify({"error": f"Fetch blocked: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": preview_helpers.fetch_exception_user_message(e)}), 502

    if payload.get("kind") != "html" or not payload.get("html"):
        msg = payload.get("message") or "Preview is not HTML; cannot capture."
        return jsonify({"error": str(msg)}), 415

    cleaned_html = str(payload["html"])
    try:
        png = preview_helpers.capture_preview_png_bytes(cleaned_html, base_url=url)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 501

    rel_png = preview_helpers.save_png_to_downloads(png, filename_hint=preview_helpers.safe_shot_name_from_url(url))

    try:
        ocr_text = preview_helpers.ocr_png_to_text(png)
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


@bp.route("/api/source/proxy")
def source_proxy():
    url = request.args.get("url")
    if not url:
        return preview_helpers.preview_html("Missing required query param: url", status=400)

    try:
        final_url, body, content_type, _content_disp = source_fetch.fetch_url(url)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("remote HTTP") or msg == "empty response body":
            return preview_helpers.preview_html(f"Upstream error: {msg}", status=502)
        return preview_helpers.preview_html(f"Fetch blocked: {msg}", status=400)
    except Exception as e:
        return preview_helpers.preview_html(preview_helpers.fetch_exception_user_message(e), status=502)

    ct = (content_type or "").split(";", 1)[0].strip().lower()
    allowed_ct = ct in {"application/pdf", "application/octet-stream"}
    if not allowed_ct or not download_helpers.is_pdf_bytes(body):
        return preview_helpers.preview_html("Unsupported content type.", status=415)

    resp = Response(body, status=200, mimetype="application/pdf")
    # Minimal safe header set: do not forward hop-by-hop / arbitrary upstream headers.
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Length"] = str(len(body))
    resp.headers["Content-Disposition"] = 'inline; filename="document.pdf"'
    return preview_helpers.apply_preview_security_headers(resp)
