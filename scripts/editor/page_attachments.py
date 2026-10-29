# -*- coding: utf-8 -*-
"""Discover and download every attachment on a press-release page.

HWP/HWPX/HML is saved only when the same document is not also offered as PDF.
Matching uses the base filename or the link title (format words such as
``hwp`` / ``pdf`` / ``한글`` removed). The owner converts leftover HWP files
to PDF in Naver Whale; this module does not convert them.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from . import config, download_helpers, source_fetch
from .html_sanitize import narrow_preview_html

KASB_DOWNLOAD_POST_URL = "https://www.kasb.or.kr/commonFile/fileDownload.do"
ATTACHMENT_MAX_BYTES = 30 * 1024 * 1024
ATTACHMENT_TIMEOUT = (10.0, 120.0)

_KASB_FILEDOWN_RE = re.compile(
    r"fileDownload\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)",
    re.IGNORECASE,
)
_DOWNLOAD_ENDPOINT_RE = re.compile(
    r"(?:getfile|filedown(?:load)?(?:\.do)?|download\.do|atchfile|atchmnfl|cmm/fms)",
    re.IGNORECASE,
)
_DOC_SUFFIX_RE = re.compile(
    r"(\.(?:pdf|hwp|hwpx|hml|zip|7z|rar|docx?|xlsx?|pptx?))(?:$|[\s)\]】])",
    re.IGNORECASE,
)
_FORMAT_PAREN_RE = re.compile(
    r"[\(\[（【]\s*(?:hwp|hwpx|hml|pdf|한글파일|아래아한글|한글)\s*[\)\]）】]",
    re.IGNORECASE,
)
_NAME_QUERY_KEYS = (
    "fileorginlnm",
    "orginlfilenm",
    "orginlfilename",
    "orignlfilename",
    "originalfilename",
    "filename",
    "filenm",
    "srvrfilenm",
    "serverfilename",
)
_SERVER_NAME_KEYS = {"srvrfilenm", "serverfilename"}
_HWP_SUFFIXES = {".hwp", ".hwpx", ".hml"}
_GENERIC_TITLE_KEYS = {
    "첨부",
    "첨부파일",
    "다운로드",
    "내려받기",
    "download",
    "file",
    "파일",
    "보기",
    "바로보기",
    "본문",
}


class AttachmentFetchError(Exception):
    def __init__(self, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class DiscoveredAttachment:
    kind: str  # "http" | "kasb"
    url: str = ""
    file_no: str = ""
    file_seq: str = ""
    filename_hint: str = ""
    title: str = ""

    def suffixes(self) -> set[str]:
        found: set[str] = set()
        for value in (self.filename_hint, self.title, self.url):
            suf = _doc_suffix(value)
            if suf:
                found.add(suf)
        return found

    def is_pdf(self) -> bool:
        return ".pdf" in self.suffixes()

    def is_hwp_family(self) -> bool:
        return bool(self.suffixes() & _HWP_SUFFIXES) and not self.is_pdf()


@dataclass
class SavedAttachment:
    source_type: str
    ref: str
    name: str
    path: Path


@dataclass
class PageFetchResult:
    ok: bool
    message: str
    attached: list[SavedAttachment] = field(default_factory=list)
    skipped_hwp: list[str] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "ok": self.ok,
            "message": self.message,
            "attached": [
                {"type": item.source_type, "ref": item.ref, "name": item.name}
                for item in self.attached
            ],
            "skipped_hwp": [{"name": name} for name in self.skipped_hwp],
            "failed": list(self.failed),
        }


def source_type_for_filename(name: str) -> str:
    suf = Path(name).suffix.lower()
    if suf == ".pdf":
        return "pdf"
    if suf in _HWP_SUFFIXES:
        return "hwp"
    if suf in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff"}:
        return "shot"
    return "file"


def attachment_match_key(name: str) -> str:
    """Stem used to treat ``보고서.pdf`` and ``보고서.hwp`` as one document."""
    text = unquote(name or "").strip()
    if not text:
        return ""
    if "://" in text or text.startswith("/"):
        hinted = _filename_from_url(text)
        text = hinted or Path(urlsplit(text).path).name
    stem = Path(text.replace("\\", "/")).stem
    stem = unicodedata.normalize("NFKC", stem).casefold()
    stem = _FORMAT_PAREN_RE.sub("", stem)
    stem = re.sub(r"[\s_\-]+", "", stem)
    stem = re.sub(r"(?:hwp|hwpx|hml|pdf|한글파일|아래아한글|한글)$", "", stem)
    stem = re.sub(r"[^0-9a-z가-힣]", "", stem)
    return stem


def prefer_pdf_over_hwp(
    items: list[DiscoveredAttachment],
) -> tuple[list[DiscoveredAttachment], list[DiscoveredAttachment]]:
    """Drop HWP/HWPX when a PDF of the same document is also offered.

    Filename stems always match. Link titles match only when they are not a
    generic label such as ``첨부파일`` (those labels are shared by unrelated files).
    """
    pdf_file_keys: set[str] = set()
    pdf_title_keys: set[str] = set()
    for item in items:
        if not item.is_pdf():
            continue
        if item.filename_hint:
            key = attachment_match_key(item.filename_hint)
            if key:
                pdf_file_keys.add(key)
        if item.title:
            key = attachment_match_key(item.title)
            if key and len(key) >= 2 and key not in _GENERIC_TITLE_KEYS:
                pdf_title_keys.add(key)

    kept: list[DiscoveredAttachment] = []
    skipped: list[DiscoveredAttachment] = []
    for item in items:
        if item.is_hwp_family():
            file_key = attachment_match_key(item.filename_hint) if item.filename_hint else ""
            title_key = attachment_match_key(item.title) if item.title else ""
            file_hit = bool(file_key) and file_key in pdf_file_keys
            title_hit = (
                bool(title_key)
                and len(title_key) >= 2
                and title_key not in _GENERIC_TITLE_KEYS
                and title_key in pdf_title_keys
            )
            if file_hit or title_hit:
                skipped.append(item)
                continue
        kept.append(item)
    return kept, skipped


def discover_attachments(html: str, page_url: str) -> list[DiscoveredAttachment]:
    """Return document links in the article body (then the full page if the body has none)."""
    if not isinstance(html, str) or not html.strip():
        return []
    narrowed = narrow_preview_html(html, page_url)
    found = _discover_in_html(narrowed, page_url)
    if not found and narrowed != html:
        found = _discover_in_html(html, page_url)
    return found


def fetch_kasb_bytes(file_no: str, file_seq: str) -> tuple[bytes, str | None]:
    """POST the KASB fileDownload endpoint and return ``(body, content-disposition)``."""
    if not re.match(r"^-?[0-9]+$", file_no or "") or not re.match(r"^[0-9]+$", file_seq or ""):
        raise AttachmentFetchError("Invalid fileNo/fileSeq.", 400)
    try:
        source_fetch.validate_url(KASB_DOWNLOAD_POST_URL)
    except ValueError as exc:
        raise AttachmentFetchError("Download URL policy error.", 500) from exc

    response = requests.post(
        KASB_DOWNLOAD_POST_URL,
        data={"fileNo": file_no, "fileSeq": file_seq},
        headers={
            "User-Agent": source_fetch._DEFAULT_BROWSER_UA,
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Connection": "close",
        },
        timeout=ATTACHMENT_TIMEOUT,
        stream=True,
        proxies={},
    )
    try:
        if not (200 <= response.status_code < 300):
            raise AttachmentFetchError(
                f"Upstream error: remote HTTP {response.status_code}",
                502,
            )
        body = _read_limited(response, ATTACHMENT_MAX_BYTES)
    finally:
        response.close()
    return body, response.headers.get("content-disposition")


def fetch_page_attachments(page_url: str, *, root: Path, folder: Path) -> PageFetchResult:
    """Download every attachment on ``page_url`` into ``folder`` (under the repo)."""
    try:
        final_url, body, content_type, content_disp = source_fetch.fetch_url(page_url)
    except (OSError, ValueError, requests.RequestException) as exc:
        return PageFetchResult(ok=False, message=f"원문 페이지를 받지 못했습니다: {exc}")

    if not _is_html(content_type, body):
        try:
            saved = _save_download(
                final_url,
                body,
                content_type,
                content_disp,
                root=root,
                folder=folder,
                filename_hint="",
            )
        except (AttachmentFetchError, OSError, ValueError) as exc:
            return PageFetchResult(ok=False, message=str(exc), failed=[{"name": page_url, "error": str(exc)}])
        return PageFetchResult(ok=True, message="첨부 1건 저장", attached=[saved])

    html = _decode_html(body, content_type)
    discovered = discover_attachments(html, final_url)
    kept, skipped = prefer_pdf_over_hwp(discovered)
    attached: list[SavedAttachment] = []
    failed: list[dict] = []
    for item in kept:
        try:
            attached.append(_download_discovered(item, root=root, folder=folder))
        except (AttachmentFetchError, OSError, ValueError, requests.RequestException) as exc:
            failed.append({"name": _display_name(item), "error": str(exc)})

    attached, dropped_names = _drop_saved_hwp_matching_pdf(attached)
    skipped_names = [_display_name(item) for item in skipped] + dropped_names

    if attached:
        message = f"첨부 {len(attached)}건 저장"
    elif not kept and not skipped:
        message = "첨부 파일을 찾지 못했습니다."
    else:
        message = "저장한 첨부가 없습니다."
    return PageFetchResult(
        ok=True,
        message=message,
        attached=attached,
        skipped_hwp=skipped_names,
        failed=failed,
    )


def downloads_dir(root: Path | None = None) -> Path:
    """Configured downloads folder, always under ``<root>/downloads``."""
    root = (root or config.repo_root()).resolve()
    cfg = config.load_config()
    try:
        rel = config._normalize_downloads_folder(cfg.get("downloads_folder"), root=root)
    except ValueError:
        rel = config._normalize_downloads_folder(config.DEFAULT_CONFIG["downloads_folder"], root=root)
    folder = root / rel
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _display_name(item: DiscoveredAttachment) -> str:
    return item.filename_hint or item.title or item.url or f"kasb:{item.file_no}:{item.file_seq}"


def _doc_suffix_token(name: str) -> str:
    text = unquote(name or "").strip()
    if not text:
        return ""
    base = Path(text.replace("\\", "/")).name
    match = _DOC_SUFFIX_RE.search(base)
    if match and base.lower().endswith(match.group(1).lower()):
        return match.group(1).lower()
    match = _DOC_SUFFIX_RE.search(text)
    return match.group(1).lower() if match else ""


def _doc_suffix(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if "://" in text or text.startswith("/"):
        hinted = _filename_from_url(text)
        if hinted:
            return _doc_suffix_token(hinted)
        return _doc_suffix_token(Path(urlsplit(text).path).name)
    return _doc_suffix_token(text)


def _filename_from_url(url: str) -> str:
    parts = urlsplit(url)
    query = parse_qs(parts.query, keep_blank_values=False)
    ranked: list[tuple[int, str]] = []
    for key, values in query.items():
        lowered = key.lower()
        if lowered not in _NAME_QUERY_KEYS or not values:
            continue
        name = Path(unquote(values[0]).replace("\\", "/")).name
        if not name:
            continue
        rank = 0 if lowered in _SERVER_NAME_KEYS else 1
        ranked.append((rank, name))
    ranked.sort(key=lambda item: item[0], reverse=True)
    for _rank, name in ranked:
        if _doc_suffix_token(name):
            return name
    base = Path(unquote(parts.path)).name
    if base and _doc_suffix_token(base):
        return base
    if ranked:
        return ranked[0][1]
    return ""


def _discover_in_html(html: str, page_url: str) -> list[DiscoveredAttachment]:
    soup = BeautifulSoup(html or "", "html.parser")
    found: list[DiscoveredAttachment] = []
    seen: set[tuple[str, ...]] = set()

    def add(item: DiscoveredAttachment) -> None:
        if item.kind == "kasb":
            key: tuple[str, ...] = ("kasb", item.file_no, item.file_seq)
        else:
            if not item.url:
                return
            key = ("http", item.url)
        if key in seen:
            return
        seen.add(key)
        found.append(item)

    page_parts = urlsplit(page_url or "")
    page_key = urlunsplit((page_parts.scheme, page_parts.netloc, page_parts.path, page_parts.query, ""))

    for anchor in soup.find_all("a"):
        title = anchor.get_text(" ", strip=True)
        onclick = anchor.get("onclick") if isinstance(anchor.get("onclick"), str) else ""
        kasb = _KASB_FILEDOWN_RE.search(onclick or "")
        if kasb:
            add(
                DiscoveredAttachment(
                    kind="kasb",
                    file_no=kasb.group(1),
                    file_seq=kasb.group(2),
                    filename_hint=_hint_from_title(title),
                    title=title,
                )
            )
            continue

        href = anchor.get("href") if isinstance(anchor.get("href"), str) else ""
        if not href or href.startswith("#"):
            continue
        kasb_href = _kasb_from_editor_href(href)
        if kasb_href is not None:
            file_no, file_seq = kasb_href
            add(
                DiscoveredAttachment(
                    kind="kasb",
                    file_no=file_no,
                    file_seq=file_seq,
                    filename_hint=_hint_from_title(title),
                    title=title,
                )
            )
            continue

        nested = _nested_editor_url(href)
        if nested:
            href = nested
        if href.lower().startswith(("javascript:", "mailto:", "data:")):
            continue
        absolute = urljoin(page_url, href)
        parts = urlsplit(absolute)
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            continue
        absolute = urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))
        if absolute == page_key:
            continue
        if not _looks_like_attachment_url(absolute, title):
            continue
        hint = _filename_from_url(absolute) or _hint_from_title(title)
        add(DiscoveredAttachment(kind="http", url=absolute, filename_hint=hint, title=title))
    return found


def _hint_from_title(title: str) -> str:
    if _doc_suffix_token(title):
        return Path(title.replace("\\", "/")).name
    return ""


def _looks_like_attachment_url(url: str, title: str) -> bool:
    hinted = _filename_from_url(url)
    if hinted and _doc_suffix_token(hinted):
        return True
    if _doc_suffix_token(title):
        return True
    if _DOWNLOAD_ENDPOINT_RE.search(urlsplit(url).path) or _DOWNLOAD_ENDPOINT_RE.search(url):
        return True
    return False


def _kasb_from_editor_href(href: str) -> tuple[str, str] | None:
    if not href.startswith("/api/source/kasb_file"):
        return None
    query = parse_qs(urlsplit(href).query)
    file_no = (query.get("fileNo") or [""])[0]
    file_seq = (query.get("fileSeq") or [""])[0]
    if not file_no or not file_seq:
        return None
    return file_no, file_seq


def _nested_editor_url(href: str) -> str:
    if not href.startswith("/api/source/"):
        return ""
    query = parse_qs(urlsplit(href).query)
    nested = (query.get("url") or [""])[0]
    return nested.strip()


def _decode_html(body: bytes, content_type: str | None) -> str:
    charset = ""
    if content_type and "charset=" in content_type.lower():
        charset = content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip().strip("\"'")
    if not charset:
        head = body[:2500]
        match = re.search(br"charset\s*=\s*['\"]?\s*([\w.-]+)", head, re.IGNORECASE)
        if match:
            charset = match.group(1).decode("ascii", errors="ignore")
    for candidate in (charset, "utf-8", "euc-kr", "cp949"):
        if not candidate:
            continue
        try:
            return body.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def _is_html(content_type: str | None, body: bytes) -> bool:
    ct = download_helpers.primary_content_type(content_type)
    if ct in {"text/html", "application/xhtml+xml"}:
        return True
    if "html" in ct and ct.endswith("+xml"):
        return True
    if download_helpers.body_sniff_html(body) and (not ct or ct.startswith("text/") or ct == "application/octet-stream"):
        return True
    return False


def _read_limited(response: requests.Response, max_bytes: int) -> bytes:
    data = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        data.extend(chunk)
        if len(data) > max_bytes:
            raise AttachmentFetchError("Attachment too large.", 413)
    if not data:
        raise AttachmentFetchError("Empty file from server.", 502)
    return bytes(data)


def _download_discovered(item: DiscoveredAttachment, *, root: Path, folder: Path) -> SavedAttachment:
    if item.kind == "kasb":
        body, content_disp = fetch_kasb_bytes(item.file_no, item.file_seq)
        return _save_download(
            KASB_DOWNLOAD_POST_URL,
            body,
            "application/octet-stream",
            content_disp,
            root=root,
            folder=folder,
            filename_hint=item.filename_hint or item.title,
        )
    final_url, body, content_type, content_disp = source_fetch.fetch_url(
        item.url,
        max_bytes=ATTACHMENT_MAX_BYTES,
        timeout=ATTACHMENT_TIMEOUT,
    )
    return _save_download(
        final_url,
        body,
        content_type,
        content_disp,
        root=root,
        folder=folder,
        filename_hint=item.filename_hint or item.title,
    )


def _save_download(
    final_url: str,
    body: bytes,
    content_type: str | None,
    content_disp: str | None,
    *,
    root: Path,
    folder: Path,
    filename_hint: str,
) -> SavedAttachment:
    if not download_helpers.save_fetched_allowed(content_type or "", body):
        raise AttachmentFetchError("저장할 수 없는 형식", 415)
    hint = download_helpers.parse_content_disposition_filename(content_disp) or filename_hint
    if download_helpers.is_pdf_bytes(body):
        fname = download_helpers.safe_pdf_storage_name(hint, final_url)
    else:
        fname = download_helpers.safe_attachment_storage_name(hint, body, fallback_stem="attachment")
    path = _store_body(folder, fname, body)
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    if not rel.startswith("downloads/"):
        raise AttachmentFetchError("downloads 폴더 밖에 저장할 수 없습니다.", 500)
    return SavedAttachment(
        source_type=source_type_for_filename(path.name),
        ref=rel,
        name=path.name,
        path=path,
    )


def _store_body(folder: Path, filename: str, body: bytes) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    direct = folder / filename
    if direct.is_file():
        try:
            if direct.read_bytes() == body:
                return direct
        except OSError:
            pass
    out = download_helpers.unique_file_path(folder, filename)
    out.write_bytes(body)
    return out


def _drop_saved_hwp_matching_pdf(saved: list[SavedAttachment]) -> tuple[list[SavedAttachment], list[str]]:
    pdf_keys = {attachment_match_key(item.name) for item in saved if item.source_type == "pdf"}
    pdf_keys.discard("")
    kept: list[SavedAttachment] = []
    dropped: list[str] = []
    for item in saved:
        key = attachment_match_key(item.name)
        if item.source_type == "hwp" and key and key in pdf_keys:
            try:
                item.path.unlink()
            except OSError:
                pass
            dropped.append(item.name)
            continue
        kept.append(item)
    return kept, dropped
