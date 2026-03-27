import os
import sys
from urllib.parse import quote

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import editor.app as editor_app


def test_fetch_exception_user_message_detects_windows_reset():
    inner = ConnectionResetError(
        10054,
        "현재 연결은 원격 호스트에 의해 강제로 끊겼습니다",
        None,
        10054,
    )
    exc = requests.exceptions.ConnectionError(("Connection aborted.", inner))
    msg = editor_app._fetch_exception_user_message(exc)
    assert "원문 서버" in msg
    assert "Fetch failed" not in msg


def test_preview_missing_url_param():
    client = editor_app.app.test_client()
    resp = client.get("/api/source/preview")
    assert resp.status_code == 400


def test_preview_html_sanitizes_and_sets_headers(monkeypatch):
    def fake_fetch_url(url: str, **kwargs):
        return (
            "https://example.com/page",
            b"<html><body><h1>Hi</h1><script>alert(1)</script></body></html>",
            "text/html; charset=utf-8",
            None,
        )

    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)
    client = editor_app.app.test_client()
    resp = client.get("/api/source/preview?url=" + "https%3A%2F%2Fexample.com%2Fpage")
    assert resp.status_code == 200
    assert b"<script" not in resp.data.lower()
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "frame-ancestors 'self'" in (resp.headers.get("Content-Security-Policy") or "")


def test_preview_timing_param_sets_server_timing_header(monkeypatch):
    def fake_fetch_url(url: str, **kwargs):
        return (
            "https://example.com/page",
            b"<html><body><h1>Hi</h1></body></html>",
            "text/html; charset=utf-8",
            None,
        )

    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)
    client = editor_app.app.test_client()
    resp = client.get(
        "/api/source/preview?timing=1&url=" + "https%3A%2F%2Fexample.com%2Fpage"
    )
    assert resp.status_code == 200
    st = resp.headers.get("Server-Timing") or ""
    assert "total" in st


def test_preview_fast_flow_auto_result_html(monkeypatch):
    class ImmediateThread:
        def __init__(self, target=None, args=(), daemon=None):
            self._target = target
            self._args = args

        def start(self):
            if self._target:
                self._target(*self._args)

    def fake_fetch_url(url: str, **kwargs):
        return ("https://example.com/page", b"<html><body><h1>Hi</h1></body></html>", "text/html", None)

    monkeypatch.setattr(editor_app.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)
    client = editor_app.app.test_client()

    first = client.get("/api/source/preview_fast?url=https%3A%2F%2Fexample.com%2Fpage")
    assert first.status_code == 200
    assert "미리보기 로딩 중" in first.get_data(as_text=True)
    csp = first.headers.get("Content-Security-Policy") or ""
    assert "connect-src 'self'" in csp

    jobs = list(editor_app._PREVIEW_JOBS.keys())
    assert len(jobs) >= 1
    job_id = jobs[-1]

    st = client.get(f"/api/source/preview_fast_status/{job_id}?url=https%3A%2F%2Fexample.com%2Fpage")
    assert st.status_code == 200
    data = st.get_json()
    assert data.get("ready") is True
    assert data.get("stage") == "완료"
    assert f"/api/source/preview_fast_result/{job_id}" in (data.get("next") or "")

    out = client.get(f"/api/source/preview_fast_result/{job_id}?url=https%3A%2F%2Fexample.com%2Fpage")
    assert out.status_code == 200
    assert b"<h1>Hi</h1>" in out.data


def test_preview_fast_status_includes_stage_while_pending(monkeypatch):
    class NoopThread:
        def __init__(self, target=None, args=(), daemon=None):
            self._target = target
            self._args = args

        def start(self):
            # keep pending on purpose
            return None

    monkeypatch.setattr(editor_app.threading, "Thread", NoopThread)
    client = editor_app.app.test_client()
    first = client.get("/api/source/preview_fast?url=https%3A%2F%2Fexample.com%2Fpage")
    assert first.status_code == 200
    jobs = list(editor_app._PREVIEW_JOBS.keys())
    job_id = jobs[-1]
    st = client.get(f"/api/source/preview_fast_status/{job_id}?url=https%3A%2F%2Fexample.com%2Fpage")
    assert st.status_code == 200
    data = st.get_json()
    assert data.get("ready") is False
    assert data.get("stage")

@pytest.mark.parametrize(
    "content_type, body",
    [
        ("application/pdf", b"%PDF-1.7\n%...."),
        ("application/octet-stream", b"%PDF-1.4\n%...."),
    ],
)
def test_preview_pdf_returns_delegate_page_for_parent_fetch(monkeypatch, content_type, body):
    def fake_fetch_url(url: str, **kwargs):
        return ("https://example.com/doc", body, content_type, None)

    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)
    client = editor_app.app.test_client()
    resp = client.get("/api/source/preview?url=" + "https%3A%2F%2Fexample.com%2Fdoc", follow_redirects=False)
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "quality-updates-fetch-save" in text
    assert "/api/source/save_fetched" in text
    assert "unsafe-inline" in (resp.headers.get("Content-Security-Policy") or "")


def test_preview_zip_returns_delegate_for_parent_fetch(monkeypatch):
    zip_body = b"PK\x03\x04" + b"x" * 30

    def fake_fetch_url(url: str, **kwargs):
        return ("https://example.com/a.zip", zip_body, "application/zip", None)

    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)
    client = editor_app.app.test_client()
    resp = client.get("/api/source/preview?url=" + "https%3A%2F%2Fexample.com%2Fa.zip", follow_redirects=False)
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "quality-updates-fetch-save" in text
    assert "/api/source/save_fetched" in text


def test_save_fetched_writes_zip(monkeypatch, tmp_path):
    root = tmp_path
    dl = root / "downloads" / "z"
    dl.mkdir(parents=True)
    zip_body = b"PK\x03\x04" + b"y" * 20

    def fake_fetch_url(url: str, **kwargs):
        return (
            "https://example.com/pack.zip",
            zip_body,
            "application/zip",
            'attachment; filename="pack.zip"',
        )

    monkeypatch.setattr(editor_app, "repo_root", lambda: root)
    monkeypatch.setattr(editor_app, "load_config", lambda: {"downloads_folder": "downloads/z/"})
    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)

    client = editor_app.app.test_client()
    resp = client.get("/api/source/save_fetched?url=" + "https%3A%2F%2Fexample.com%2Fpack.zip")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("ok") is True
    assert data.get("name") == "pack.zip"
    assert "파일 저장" in (data.get("message") or "")
    saved = list(dl.glob("*.zip"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == zip_body


def test_save_pdf_writes_under_configured_folder(monkeypatch, tmp_path):
    root = tmp_path
    dl = root / "downloads" / "editor_pdfs"
    dl.mkdir(parents=True)

    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

    def fake_fetch_url(url: str, **kwargs):
        return (
            "https://example.com/pub/file.pdf",
            pdf,
            "application/pdf",
            'attachment; filename="My Report.pdf"',
        )

    monkeypatch.setattr(editor_app, "repo_root", lambda: root)
    monkeypatch.setattr(editor_app, "load_config", lambda: {"downloads_folder": "downloads/editor_pdfs/"})
    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)

    client = editor_app.app.test_client()
    resp = client.get("/api/source/save_pdf?url=" + "https%3A%2F%2Fexample.com%2Fpub%2Ffile.pdf")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("ok") is True
    assert data.get("name") == "My Report.pdf"
    assert "PDF 저장" in (data.get("message") or "")
    saved = list(dl.glob("*.pdf"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == pdf
    assert saved[0].name == "My Report.pdf"


def test_save_pdf_duplicate_name_adds_suffix(monkeypatch, tmp_path):
    root = tmp_path
    dl = root / "downloads" / "d"
    dl.mkdir(parents=True)
    (dl / "doc.pdf").write_bytes(b"%PDF-old\n")

    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

    def fake_fetch_url(url: str, **kwargs):
        return ("https://example.com/doc.pdf", pdf, "application/pdf", 'attachment; filename="doc.pdf"')

    monkeypatch.setattr(editor_app, "repo_root", lambda: root)
    monkeypatch.setattr(editor_app, "load_config", lambda: {"downloads_folder": "downloads/d/"})
    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)

    client = editor_app.app.test_client()
    resp = client.get("/api/source/save_pdf?url=" + "https%3A%2F%2Fexample.com%2Fdoc.pdf")
    assert resp.status_code == 200
    assert (dl / "doc (1).pdf").exists()
    assert (dl / "doc (1).pdf").read_bytes() == pdf


def test_kasb_file_proxy_rejects_invalid_file_no():
    client = editor_app.app.test_client()
    resp = client.get("/api/source/kasb_file?fileNo=abc&fileSeq=1")
    assert resp.status_code == 400


def test_kasb_file_proxy_saves_to_configured_downloads_folder(monkeypatch, tmp_path):
    class FakeResp:
        status_code = 200
        headers = {"content-disposition": 'attachment; filename="a.zip"'}

        def iter_content(self, chunk_size=8192):
            yield b"PK\x03\x04" + b"x" * 20

        def close(self):
            pass

    calls = {}

    def fake_post(url, **kwargs):
        calls["url"] = url
        calls["data"] = kwargs.get("data")
        return FakeResp()

    root = tmp_path
    dl = root / "downloads" / "kasb_test"
    dl.mkdir(parents=True)

    monkeypatch.setattr(editor_app, "repo_root", lambda: root)
    monkeypatch.setattr(editor_app, "load_config", lambda: {"downloads_folder": "downloads/kasb_test/"})
    monkeypatch.setattr(editor_app.requests, "post", fake_post)

    client = editor_app.app.test_client()
    resp = client.get("/api/source/kasb_file?fileNo=-99&fileSeq=2")
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True
    assert "첨부 저장" in (resp.get_json().get("message") or "")
    assert calls["url"] == editor_app._KASB_DOWNLOAD_POST_URL
    assert calls["data"] == {"fileNo": "-99", "fileSeq": "2"}
    saved = list(dl.glob("*.zip"))
    assert len(saved) == 1
    assert saved[0].read_bytes().startswith(b"PK")


def test_parse_content_disposition_filename_star_utf8_korean():
    enc = quote("보도자료.pdf", safe="")
    cd = 'attachment; filename="bad.pdf"; filename*=UTF-8\'\'' + enc
    out = editor_app._parse_content_disposition_filename(cd)
    assert out == "보도자료.pdf"


def test_parse_content_disposition_quoted_latin1_wrapped_utf8():
    inner = "보도자료.pdf".encode("utf-8").decode("latin-1")
    cd = 'attachment; filename="' + inner + '"'
    out = editor_app._parse_content_disposition_filename(cd)
    assert out == "보도자료.pdf"


def test_parse_content_disposition_quoted_percent_encoded_utf8():
    enc = quote("(보도자료).hwpx", safe="")
    cd = 'attachment; filename="' + enc + '"'
    out = editor_app._parse_content_disposition_filename(cd)
    assert out == "(보도자료).hwpx"


def test_save_pdf_korean_filename_from_rfc5987(monkeypatch, tmp_path):
    root = tmp_path
    dl = root / "downloads" / "d"
    dl.mkdir(parents=True)
    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    enc = quote("시행문.pdf", safe="")
    cd = 'attachment; filename="broken.pdf"; filename*=UTF-8\'\'' + enc

    def fake_fetch_url(url: str, **kwargs):
        return ("https://example.com/x", pdf, "application/pdf", cd)

    monkeypatch.setattr(editor_app, "repo_root", lambda: root)
    monkeypatch.setattr(editor_app, "load_config", lambda: {"downloads_folder": "downloads/d/"})
    monkeypatch.setattr(editor_app, "fetch_url", fake_fetch_url)

    client = editor_app.app.test_client()
    resp = client.get("/api/source/save_pdf?url=https%3A%2F%2Fexample.com%2Fx")
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True
    assert "시행문" in (resp.get_json().get("message") or "")
    saved = list(dl.glob("*.pdf"))
    assert len(saved) == 1
    assert saved[0].name == "시행문.pdf"

