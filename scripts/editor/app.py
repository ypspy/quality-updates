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
_PREVIEW_JOBS: dict[str, dict] = {}
_PREVIEW_JOBS_LOCK = threading.Lock()

# Browsers request /favicon.ico by default; SVG payload is widely supported.
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" rx="6" fill="#1a1a2e"/>'
    '<path fill="#e3f2fd" d="M9 9h14v3H9zm0 6h10v3H9zm0 6h12v3H9z"/></svg>'
)

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


def _primary_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def _body_sniff_html(body: bytes) -> bool:
    """Heuristic: avoid saving HTML error pages as .zip etc."""
    if not body:
        return False
    s = bytes(body[:512]).lstrip(b"\xef\xbb\xbf \t\r\n")[:200].lower()
    return (
        s.startswith(b"<!doctype html")
        or s.startswith(b"<html")
        or s.startswith(b"<head")
        or s.startswith(b"<body")
    )


# MIME types we never persist via «원문 다운로드» (미리보기는 HTML 분기에서 처리).
_SAVE_BLOCKLIST_CT = frozenset(
    {
        "application/json",
        "application/ld+json",
        "application/javascript",
        "text/javascript",
        "text/css",
    }
)


def _should_auto_download_fetched(ct_raw: str, body: bytes) -> bool:
    """True → WEB 미리보기가 HTML이 아니면 부모 fetch로 downloads에 저장."""
    ct = _primary_content_type(ct_raw)
    if ct in {"text/html", "application/xhtml+xml"}:
        return False
    if ct.endswith("+xml") and "html" in ct:
        return False
    if ct in _SAVE_BLOCKLIST_CT:
        return False
    if ct.startswith("text/"):
        return False
    if _body_sniff_html(body):
        return False
    if ct == "application/pdf":
        return _is_pdf_bytes(body)
    if ct == "application/octet-stream":
        return True
    if ct.startswith(("image/", "audio/", "video/")):
        return True
    if ct.startswith("application/vnd."):
        return True
    if ct.startswith("application/"):
        return True
    return False


def _save_fetched_allowed(ct_raw: str, body: bytes) -> bool:
    """save_fetched/save_pdf 공통: 서버가 디스크에 쓸 수 있는 응답인지."""
    ct = _primary_content_type(ct_raw)
    if ct in {"text/html", "application/xhtml+xml"}:
        return False
    if ct.endswith("+xml") and "html" in ct:
        return False
    if ct in _SAVE_BLOCKLIST_CT:
        return False
    if ct.startswith("text/"):
        return False
    if _body_sniff_html(body):
        return False
    if ct == "application/pdf":
        return _is_pdf_bytes(body)
    if _is_pdf_bytes(body):
        return True
    return _should_auto_download_fetched(ct_raw, body)


# RFC 2231 / RFC 5987: filename*=charset'lang'percent-encoded-value
# (lang is often empty → two consecutive quotes: UTF-8''%EC%9E%85...)
_CD_FILENAME_STAR_RE = re.compile(
    r"filename\*\s*=\s*([A-Za-z0-9_.-]+)'([^']*)'([^;]+)",
    re.IGNORECASE,
)
# Shorthand seen in the wild: filename*=UTF-8''value (already covered by STAR_RE if we allow empty lang — yes '' is two quotes with empty between)
_CD_FILENAME_QUOTED_RE = re.compile(r'filename\s*=\s*"((?:\\.|[^"\\])*)"', re.IGNORECASE)
_CD_FILENAME_PLAIN_RE = re.compile(r"filename\s*=\s*([^;\s]+)", re.IGNORECASE)


def _repair_latin1_wrapped_utf8(name: str) -> str:
    """HTTP/1.1 headers are often ISO-8859-1; UTF-8 bytes misread as Latin-1 → mojibake.

    If ``name`` is all ASCII, return as-is. Otherwise try reversing Latin-1→bytes→UTF-8;
    keep the result when it contains Hangul (typical for .go.kr attachments).
    """
    if not name or not isinstance(name, str):
        return name
    if all(ord(c) < 128 for c in name):
        return name
    try:
        raw = name.encode("latin-1")
        fixed = raw.decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return name
    if re.search(r"[\uac00-\ud7a3]", fixed):
        return fixed
    if "\ufffd" in name and "\ufffd" not in fixed:
        return fixed
    return name


def _parse_content_disposition_filename(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    # Prefer filename* (UTF-8 percent-encoded) over legacy filename=
    m = _CD_FILENAME_STAR_RE.search(value)
    if m:
        charset = (m.group(1) or "UTF-8").strip()
        # ``unquote`` maps each %xx to U+00xx (wrong for UTF-8 multibyte). Use bytes → decode.
        pct = m.group(3).strip().strip('"').strip("'")
        try:
            raw_bytes = unquote_to_bytes(pct)
        except ValueError:
            raw_bytes = pct.encode("ascii", errors="ignore")
        cs = charset.lower().replace("_", "-")
        try:
            if cs in ("utf-8", "utf8"):
                return raw_bytes.decode("utf-8")
            return raw_bytes.decode(cs, errors="replace")
        except (LookupError, UnicodeDecodeError):
            return raw_bytes.decode("utf-8", errors="replace")

    m = _CD_FILENAME_QUOTED_RE.search(value)
    if m:
        inner = m.group(1).replace("\\\"", '"').replace("\\\\", "\\")
        inner = inner.strip()
        # Many sites send filename="%28%EB%B3%B4%EB%8F%84…%29.hwp" (ASCII-only quoted UTF-8 pct)
        if "%" in inner and re.search(r"%[0-9A-Fa-f]{2}", inner):
            try:
                inner = unquote_to_bytes(inner).decode("utf-8")
            except (UnicodeDecodeError, ValueError):
                pass
        inner = _repair_latin1_wrapped_utf8(inner)
        return inner

    m = _CD_FILENAME_PLAIN_RE.search(value)
    if m:
        token = m.group(1).strip().strip('"').strip("'")
        if "%" in token:
            try:
                decoded = unquote_to_bytes(token).decode("utf-8")
                return _repair_latin1_wrapped_utf8(decoded)
            except (UnicodeDecodeError, ValueError):
                pass
        return _repair_latin1_wrapped_utf8(unquote(token))
    return None


def _basename_from_final_url(final_url: str) -> str | None:
    path = urlsplit(final_url).path
    if not path or path.endswith("/"):
        return None
    seg = path.rsplit("/", 1)[-1].strip()
    if not seg or seg in (".", ".."):
        return None
    if "%" in seg:
        try:
            return unquote_to_bytes(seg).decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            pass
    return unquote(seg)


def _safe_pdf_storage_name(hint: str | None, final_url: str) -> str:
    raw = (hint or "").strip() or _basename_from_final_url(final_url) or "document.pdf"
    name = Path(raw.replace("\\", "/")).name
    if not name or name in (".", ".."):
        name = "document.pdf"
    name = name.replace("\x00", "")
    stem = Path(name).stem
    if not stem:
        stem = "document"
    stem = re.sub(r'[\x00-\x1f\\/:*?"<>|]', "_", stem).strip()[:150]
    if not stem:
        stem = "document"
    return stem + ".pdf"


def _safe_attachment_storage_name(hint: str | None, body: bytes, *, fallback_stem: str = "attachment") -> str:
    """Local filename for arbitrary downloads (KASB hwpx 등). Preserves extension from hint or sniffs magic."""
    raw = (hint or "").strip()
    name = Path(raw.replace("\\", "/")).name if raw else ""
    if not name or name in (".", ".."):
        name = ""
    name = name.replace("\x00", "")
    suf = Path(name).suffix.lower() if name else ""
    stem = Path(name).stem if name else ""
    if not stem:
        stem = fallback_stem
    stem = re.sub(r'[\x00-\x1f\\/:*?"<>|]', "_", stem).strip()[:150]
    if not stem:
        stem = fallback_stem
    if not suf:
        if body.startswith(b"%PDF"):
            suf = ".pdf"
        elif body[:2] == b"PK":
            suf = ".zip"
        else:
            suf = ".bin"
    return stem + suf


def _unique_file_path(folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    base = Path(filename)
    stem = base.stem or "file"
    suffix = (base.suffix or ".bin").lower()
    if not suffix.startswith("."):
        suffix = "." + suffix
    candidate = folder / f"{stem}{suffix}"
    n = 1
    while candidate.exists():
        candidate = folder / f"{stem} ({n}){suffix}"
        n += 1
    return candidate


def _unique_pdf_path(folder: Path, filename: str) -> Path:
    base = Path(filename)
    stem = base.stem
    return _unique_file_path(folder, f"{stem}.pdf")


def _apply_preview_security_headers(
    resp: Response,
    *,
    allow_inline_script: bool = False,
    allow_connect_self: bool = False,
) -> Response:
    # Allow embedding only by this editor (same-origin iframe).
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    if allow_inline_script:
        # 저장 완료 페이지만 parent.postMessage용 인라인 스크립트 허용
        csp = (
            "default-src 'none'; script-src 'unsafe-inline'; img-src data:; style-src 'unsafe-inline'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
        )
        if allow_connect_self:
            csp += "; connect-src 'self'"
        resp.headers["Content-Security-Policy"] = csp
    else:
        resp.headers["Content-Security-Policy"] = (
            "default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; "
            "form-action 'none'; frame-ancestors 'self'"
        )
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _json_save_result(
    ok: bool,
    message: str,
    *,
    status: int = 200,
    rel_posix: str | None = None,
):
    """save_pdf / kasb_file 전용 JSON (부모 fetch + UTF-8 메시지)."""
    data: dict = {"ok": ok, "message": message}
    if ok and rel_posix:
        data["path"] = rel_posix
        data["name"] = Path(rel_posix).name
    return jsonify(data), status


def _delegate_parent_fetch_download(original_url: str) -> Response:
    """바이너리(PDF·Zip·Office 등): 부모 창이 save_fetched를 fetch하고 토스트만 표시."""
    path = "/api/source/save_fetched?url=" + quote(original_url, safe="")
    msg = json.dumps({"type": "quality-updates-fetch-save", "path": path})
    page = (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'><title></title></head><body>"
        "<script>"
        "(function(){try{if(parent!==window){parent.postMessage("
        + msg
        + ",'*');}}catch(e){}})();"
        "</script></body></html>"
    )
    resp = Response(page, status=200, mimetype="text/html")
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return _apply_preview_security_headers(resp, allow_inline_script=True)


def _exception_search_blob(exc: BaseException) -> str:
    """Flatten str/repr/args/cause for substring checks (requests often nests OSError)."""
    parts: list[str] = []

    def walk(x: object, depth: int) -> None:
        if depth > 10:
            return
        if isinstance(x, BaseException):
            parts.append(str(x))
            parts.append(repr(x))
            if x.__cause__ is not None:
                walk(x.__cause__, depth + 1)
            ctx = x.__context__
            if ctx is not None and ctx is not x.__cause__:
                walk(ctx, depth + 1)
            walk(x.args, depth + 1)
        elif isinstance(x, tuple):
            for item in x:
                walk(item, depth + 1)
        elif x is not None:
            parts.append(repr(x))

    walk(exc, 0)
    return " ".join(parts)


def _fetch_exception_user_message(exc: BaseException) -> str:
    """Shorter iframe message for common transient TCP/TLS drops (e.g. WinError 10054)."""
    blob = _exception_search_blob(exc)
    low = blob.lower()
    if (
        "10054" in blob
        or "connectionreseterror" in low
        or "connection aborted" in low
        or "connection reset" in low
        or "broken pipe" in low
        or "forcibly closed" in low
        or "원격 호스트" in blob
        or ("ssl" in low and "eof" in low)
        or "protocolerror" in low
        or "remotedisconnected" in low
    ):
        return (
            "원문 서버와의 연결이 끊겼습니다. "
            "잠시 후 [미리보기/새로고침]을 다시 눌러 보거나, 표의 링크를 새 탭에서 여세요."
        )
    return f"Fetch failed: {str(exc)}"


def _preview_html(message: str, *, status: int) -> Response:
    safe = html.escape(str(message), quote=False)
    resp = Response(f"<!doctype html><meta charset='utf-8'><p>{safe}</p>", status=status, mimetype="text/html")
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return _apply_preview_security_headers(resp)


class _VisibleTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._chunks.append(data)

    def get_text(self) -> str:
        return "".join(self._chunks)


def _html_to_visible_text(html_content: str) -> str:
    """Best-effort conversion of preview HTML -> user-visible text."""
    if not isinstance(html_content, str):
        return ""
    # Add line breaks at common block boundaries before parsing.
    s = html_content
    s = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", s)
    s = re.sub(r"(?i)</\s*(p|div|li|h1|h2|h3|h4|h5|h6|tr)\s*>", "\n", s)
    s = re.sub(r"(?i)</\s*(td|th)\s*>", "\t", s)
    s = re.sub(r"(?i)<\s*li[^>]*>", "- ", s)
    s = re.sub(r"(?i)<\s*(script|style)[^>]*>.*?<\s*/\s*\\1\\s*>", "", s, flags=re.S)
    parser = _VisibleTextExtractor()
    try:
        parser.feed(s)
    except Exception:
        return ""
    text = html.unescape(parser.get_text())
    # Normalize whitespace while preserving newlines/tabs we inserted.
    text = re.sub(r"[ \\u00a0\\f\\v]+", " ", text)
    text = re.sub(r"\\n\\s*\\n\\s*\\n+", "\n\n", text)
    text = re.sub(r"[ \\t]+\\n", "\n", text)
    return text.strip()


def _build_preview_document(cleaned_html: str, *, base_url: str = "") -> str:
    # Keep it simple and deterministic; styles matter for screenshot readability.
    base = f"<base href='{html.escape(base_url, quote=True)}' />" if base_url else ""
    return (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        f"{base}"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<style>"
        "html,body{margin:0;padding:0;background:#fff;color:#111}"
        "body{font:14px/1.55 system-ui,-apple-system,Segoe UI,Roboto,Arial,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;padding:16px}"
        "table{border-collapse:collapse;max-width:100%}"
        "th,td{border:1px solid #ddd;padding:6px 8px;vertical-align:top}"
        "th{background:#f7f7f7}"
        "pre,code{white-space:pre-wrap;word-break:break-word}"
        "a{color:#0b57d0;text-decoration:none}"
        "</style></head><body>"
        f"{cleaned_html}"
        "</body></html>"
    )


def _capture_preview_png_bytes(cleaned_html: str, *, base_url: str) -> bytes:
    """Render cleaned preview HTML and screenshot to PNG bytes (full page)."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Playwright가 필요합니다. `pip install playwright` 후 `python -m playwright install chromium`을 실행하세요."
        ) from e

    doc = _build_preview_document(cleaned_html, base_url=base_url)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "preview.html"
        p.write_text(doc, encoding="utf-8")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.goto(p.as_uri(), wait_until="load")
                page.wait_for_timeout(200)  # allow layout settle
                png = page.screenshot(full_page=True, type="png")
                return bytes(png)
            finally:
                browser.close()


def _ocr_png_to_text(png_bytes: bytes) -> str:
    """OCR PNG screenshot to text. Requires pytesseract + system Tesseract."""
    try:
        import pytesseract  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("pytesseract가 필요합니다. `pip install pytesseract`를 설치하세요.") from e
    try:
        from PIL import Image
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Pillow가 필요합니다. `pip install pillow`를 설치하세요.") from e

    img = Image.open(BytesIO(png_bytes))
    # PSM 6: assume a uniform block of text; better for tables than default in many cases.
    text = pytesseract.image_to_string(img, lang="kor+eng", config="--psm 6")
    return (text or "").strip()


def _save_png_to_downloads(png_bytes: bytes, *, filename_hint: str) -> str:
    """Save screenshot into configured downloads folder. Returns repo-relative posix path."""
    root = repo_root()
    cfg = load_config()
    try:
        downloads_folder = _normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        downloads_folder = _normalize_downloads_folder(DEFAULT_CONFIG["downloads_folder"], root=root)
    folder = root / downloads_folder
    out_path = _unique_file_path(folder, filename_hint)
    out_path.write_bytes(png_bytes)
    return out_path.relative_to(root.resolve()).as_posix()


def _safe_shot_name_from_url(url: str) -> str:
    host = urlsplit(url).hostname or "web"
    host = re.sub(r"[^a-zA-Z0-9._-]+", "_", host).strip("._-")[:60] or "web"
    return f"{host}-preview.png"


def _build_preview_payload(url: str) -> dict:
    final_url, body, content_type, _content_disp = fetch_url(url)
    ct = _primary_content_type(content_type)
    is_html = ct in {"text/html", "application/xhtml+xml"} or ct.endswith("+xml") and "html" in ct
    url_path = (final_url or "").split("?", 1)[0].lower()
    is_pdf = (
        ct == "application/pdf"
        or _is_pdf_bytes(body)
        or (ct == "application/octet-stream" and (_is_pdf_bytes(body) or url_path.endswith(".pdf")))
    )
    if is_html:
        html_text = body.decode("utf-8", errors="replace")
        html_text = narrow_preview_html(html_text, final_url)
        cleaned = sanitize_html_for_web_preview(html_text, base_url=final_url)
        return {"kind": "html", "status": 200, "html": cleaned}
    if is_pdf or _should_auto_download_fetched(content_type, body):
        return {"kind": "delegate", "status": 200}
    return {"kind": "error", "status": 415, "message": "Unsupported content type for preview."}


def _store_preview_job(job_id: str, payload: dict) -> None:
    with _PREVIEW_JOBS_LOCK:
        _PREVIEW_JOBS[job_id] = payload
        # Keep in-memory store bounded.
        if len(_PREVIEW_JOBS) > 200:
            stale = sorted(_PREVIEW_JOBS.items(), key=lambda kv: kv[1].get("ts", 0.0))[:50]
            for k, _v in stale:
                _PREVIEW_JOBS.pop(k, None)


def _update_preview_job(job_id: str, **kwargs) -> None:
    with _PREVIEW_JOBS_LOCK:
        cur = _PREVIEW_JOBS.get(job_id, {})
        cur.update(kwargs)
        _PREVIEW_JOBS[job_id] = cur


def _run_preview_job(job_id: str, url: str) -> None:
    try:
        _update_preview_job(job_id, stage="원문 요청 중")
        payload = _build_preview_payload(url)
        if payload.get("kind") == "html":
            _update_preview_job(job_id, stage="전처리 중")
    except ValueError as e:
        msg = str(e)
        if msg.startswith("remote HTTP") or msg == "empty response body":
            payload = {"kind": "error", "status": 502, "message": f"Upstream error: {msg}"}
        else:
            payload = {"kind": "error", "status": 400, "message": f"Fetch blocked: {msg}"}
    except Exception as e:
        payload = {"kind": "error", "status": 502, "message": _fetch_exception_user_message(e)}
    payload["ready"] = True
    payload["stage"] = "완료"
    payload["ts"] = perf_counter()
    _store_preview_job(job_id, payload)


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
