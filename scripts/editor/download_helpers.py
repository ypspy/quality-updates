# -*- coding: utf-8 -*-
"""Content-Disposition parsing, safe filenames, and download content sniffing."""
import re
from pathlib import Path
from urllib.parse import unquote, unquote_to_bytes, urlsplit

from flask import jsonify


def is_pdf_bytes(data: bytes) -> bool:
    if not isinstance(data, (bytes, bytearray)):
        return False
    # PDF signature: "%PDF-" at file start (allow UTF-8 BOM/whitespace before it)
    head = bytes(data[:1024])
    stripped = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    return stripped.startswith(b"%PDF-")


def primary_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def body_sniff_html(body: bytes) -> bool:
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


def should_auto_download_fetched(ct_raw: str, body: bytes) -> bool:
    """True → WEB 미리보기가 HTML이 아니면 부모 fetch로 downloads에 저장."""
    ct = primary_content_type(ct_raw)
    if ct in {"text/html", "application/xhtml+xml"}:
        return False
    if ct.endswith("+xml") and "html" in ct:
        return False
    if ct in _SAVE_BLOCKLIST_CT:
        return False
    if ct.startswith("text/"):
        return False
    if body_sniff_html(body):
        return False
    if ct == "application/pdf":
        return is_pdf_bytes(body)
    if ct == "application/octet-stream":
        return True
    if ct.startswith(("image/", "audio/", "video/")):
        return True
    if ct.startswith("application/vnd."):
        return True
    if ct.startswith("application/"):
        return True
    return False


def save_fetched_allowed(ct_raw: str, body: bytes) -> bool:
    """save_fetched/save_pdf 공통: 서버가 디스크에 쓸 수 있는 응답인지."""
    ct = primary_content_type(ct_raw)
    if ct in {"text/html", "application/xhtml+xml"}:
        return False
    if ct.endswith("+xml") and "html" in ct:
        return False
    if ct in _SAVE_BLOCKLIST_CT:
        return False
    if ct.startswith("text/"):
        return False
    if body_sniff_html(body):
        return False
    if ct == "application/pdf":
        return is_pdf_bytes(body)
    if is_pdf_bytes(body):
        return True
    return should_auto_download_fetched(ct_raw, body)


# RFC 2231 / RFC 5987: filename*=charset'lang'percent-encoded-value
# (lang is often empty → two consecutive quotes: UTF-8''%EC%9E%85...)
_CD_FILENAME_STAR_RE = re.compile(
    r"filename\*\s*=\s*([A-Za-z0-9_.-]+)'([^']*)'([^;]+)",
    re.IGNORECASE,
)
# Shorthand seen in the wild: filename*=UTF-8''value (already covered by STAR_RE if we allow empty lang — yes '' is two quotes with empty between)
_CD_FILENAME_QUOTED_RE = re.compile(r'filename\s*=\s*"((?:\\.|[^"\\])*)"', re.IGNORECASE)
_CD_FILENAME_PLAIN_RE = re.compile(r"filename\s*=\s*([^;\s]+)", re.IGNORECASE)


def repair_latin1_wrapped_utf8(name: str) -> str:
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


def parse_content_disposition_filename(value: str | None) -> str | None:
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
        inner = repair_latin1_wrapped_utf8(inner)
        return inner

    m = _CD_FILENAME_PLAIN_RE.search(value)
    if m:
        token = m.group(1).strip().strip('"').strip("'")
        if "%" in token:
            try:
                decoded = unquote_to_bytes(token).decode("utf-8")
                return repair_latin1_wrapped_utf8(decoded)
            except (UnicodeDecodeError, ValueError):
                pass
        return repair_latin1_wrapped_utf8(unquote(token))
    return None


def basename_from_final_url(final_url: str) -> str | None:
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


def safe_pdf_storage_name(hint: str | None, final_url: str) -> str:
    raw = (hint or "").strip() or basename_from_final_url(final_url) or "document.pdf"
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


def safe_attachment_storage_name(hint: str | None, body: bytes, *, fallback_stem: str = "attachment") -> str:
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


def unique_file_path(folder: Path, filename: str) -> Path:
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


def unique_pdf_path(folder: Path, filename: str) -> Path:
    base = Path(filename)
    stem = base.stem
    return unique_file_path(folder, f"{stem}.pdf")


def json_save_result(
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


# Backward-compatible aliases for tests and legacy imports.
_is_pdf_bytes = is_pdf_bytes
_primary_content_type = primary_content_type
_body_sniff_html = body_sniff_html
_should_auto_download_fetched = should_auto_download_fetched
_save_fetched_allowed = save_fetched_allowed
_parse_content_disposition_filename = parse_content_disposition_filename
_safe_pdf_storage_name = safe_pdf_storage_name
_safe_attachment_storage_name = safe_attachment_storage_name
_unique_file_path = unique_file_path
_unique_pdf_path = unique_pdf_path
_json_save_result = json_save_result
