# -*- coding: utf-8 -*-
"""Preview HTML generation, async jobs, OCR, and security headers."""
import html
import json
import re
import tempfile
import threading
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from time import perf_counter
from urllib.parse import quote, urlsplit

from flask import Response

from . import config, download_helpers, source_fetch
from .html_sanitize import narrow_preview_html, sanitize_html_for_web_preview

_PREVIEW_JOBS: dict[str, dict] = {}
_PREVIEW_JOBS_LOCK = threading.Lock()


def apply_preview_security_headers(
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


def delegate_parent_fetch_download(original_url: str) -> Response:
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
    return apply_preview_security_headers(resp, allow_inline_script=True)


def exception_search_blob(exc: BaseException) -> str:
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


def fetch_exception_user_message(exc: BaseException) -> str:
    """Shorter iframe message for common transient TCP/TLS drops (e.g. WinError  #10054)."""
    blob = exception_search_blob(exc)
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


def preview_html(message: str, *, status: int) -> Response:
    safe = html.escape(str(message), quote=False)
    resp = Response(f"<!doctype html><meta charset='utf-8'><p>{safe}</p>", status=status, mimetype="text/html")
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return apply_preview_security_headers(resp)


class VisibleTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._chunks.append(data)

    def get_text(self) -> str:
        return "".join(self._chunks)


def html_to_visible_text(html_content: str) -> str:
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
    parser = VisibleTextExtractor()
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


def build_preview_document(cleaned_html: str, *, base_url: str = "") -> str:
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


def capture_preview_png_bytes(cleaned_html: str, *, base_url: str) -> bytes:
    """Render cleaned preview HTML and screenshot to PNG bytes (full page)."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Playwright가 필요합니다. `pip install playwright` 후 `python -m playwright install chromium`을 실행하세요."
        ) from e

    doc = build_preview_document(cleaned_html, base_url=base_url)
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


def ocr_png_to_text(png_bytes: bytes) -> str:
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


def save_png_to_downloads(png_bytes: bytes, *, filename_hint: str) -> str:
    """Save screenshot into configured downloads folder. Returns repo-relative posix path."""
    root = config.repo_root()
    cfg = config.load_config()
    try:
        downloads_folder = config._normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        downloads_folder = config._normalize_downloads_folder(config.DEFAULT_CONFIG["downloads_folder"], root=root)
    folder = root / downloads_folder
    out_path = download_helpers.unique_file_path(folder, filename_hint)
    out_path.write_bytes(png_bytes)
    return out_path.relative_to(root.resolve()).as_posix()


def safe_shot_name_from_url(url: str) -> str:
    host = urlsplit(url).hostname or "web"
    host = re.sub(r"[^a-zA-Z0-9._-]+", "_", host).strip("._-")[:60] or "web"
    return f"{host}-preview.png"


def build_preview_payload(url: str) -> dict:
    final_url, body, content_type, _content_disp = source_fetch.fetch_url(url)
    ct = download_helpers.primary_content_type(content_type)
    is_html = ct in {"text/html", "application/xhtml+xml"} or ct.endswith("+xml") and "html" in ct
    url_path = (final_url or "").split("?", 1)[0].lower()
    is_pdf = (
        ct == "application/pdf"
        or download_helpers.is_pdf_bytes(body)
        or (ct == "application/octet-stream" and (download_helpers.is_pdf_bytes(body) or url_path.endswith(".pdf")))
    )
    if is_html:
        html_text = body.decode("utf-8", errors="replace")
        html_text = narrow_preview_html(html_text, final_url)
        cleaned = sanitize_html_for_web_preview(html_text, base_url=final_url)
        return {"kind": "html", "status": 200, "html": cleaned}
    if is_pdf or download_helpers.should_auto_download_fetched(content_type, body):
        return {"kind": "delegate", "status": 200}
    return {"kind": "error", "status": 415, "message": "Unsupported content type for preview."}


def store_preview_job(job_id: str, payload: dict) -> None:
    with _PREVIEW_JOBS_LOCK:
        _PREVIEW_JOBS[job_id] = payload
        # Keep in-memory store bounded.
        if len(_PREVIEW_JOBS) > 200:
            stale = sorted(_PREVIEW_JOBS.items(), key=lambda kv: kv[1].get("ts", 0.0))[:50]
            for k, _v in stale:
                _PREVIEW_JOBS.pop(k, None)


def update_preview_job(job_id: str, **kwargs) -> None:
    with _PREVIEW_JOBS_LOCK:
        cur = _PREVIEW_JOBS.get(job_id, {})
        cur.update(kwargs)
        _PREVIEW_JOBS[job_id] = cur


def run_preview_job(job_id: str, url: str) -> None:
    try:
        update_preview_job(job_id, stage="원문 요청 중")
        payload = build_preview_payload(url)
        if payload.get("kind") == "html":
            update_preview_job(job_id, stage="전처리 중")
    except ValueError as e:
        msg = str(e)
        if msg.startswith("remote HTTP") or msg == "empty response body":
            payload = {"kind": "error", "status": 502, "message": f"Upstream error: {msg}"}
        else:
            payload = {"kind": "error", "status": 400, "message": f"Fetch blocked: {msg}"}
    except Exception as e:
        payload = {"kind": "error", "status": 502, "message": fetch_exception_user_message(e)}
    payload["ready"] = True
    payload["stage"] = "완료"
    payload["ts"] = perf_counter()
    store_preview_job(job_id, payload)


# Backward-compatible aliases for tests and legacy imports.
_apply_preview_security_headers = apply_preview_security_headers
_delegate_parent_fetch_download = delegate_parent_fetch_download
_fetch_exception_user_message = fetch_exception_user_message
_preview_html = preview_html
_html_to_visible_text = html_to_visible_text
_build_preview_payload = build_preview_payload
_capture_preview_png_bytes = capture_preview_png_bytes
_ocr_png_to_text = ocr_png_to_text
_save_png_to_downloads = save_png_to_downloads
_safe_shot_name_from_url = safe_shot_name_from_url
_run_preview_job = run_preview_job
_store_preview_job = store_preview_job
