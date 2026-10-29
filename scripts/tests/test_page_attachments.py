# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import editor.config as editor_config
import editor.page_attachments as page_attachments
import editor.source_fetch as source_fetch
from editor.page_attachments import DiscoveredAttachment, prefer_pdf_over_hwp


def _item(name: str, title: str | None = None, url: str | None = None) -> DiscoveredAttachment:
    return DiscoveredAttachment(
        kind="http",
        url=url or f"https://www.fsc.go.kr/files/{name}",
        filename_hint=name,
        title=title if title is not None else name,
    )


def test_skip_hwp_when_pdf_has_the_same_stem():
    kept, skipped = prefer_pdf_over_hwp([
        _item("보도자료.pdf"),
        _item("보도자료.hwp"),
        _item("보도자료.hwpx"),
    ])
    assert [item.filename_hint for item in kept] == ["보도자료.pdf"]
    assert [item.filename_hint for item in skipped] == ["보도자료.hwp", "보도자료.hwpx"]


def test_keep_hwp_when_no_pdf_equivalent():
    kept, skipped = prefer_pdf_over_hwp([_item("별첨.hwp"), _item("별첨.hwpx")])
    assert [item.filename_hint for item in kept] == ["별첨.hwp", "별첨.hwpx"]
    assert skipped == []


def test_match_hwp_to_pdf_by_title_when_filenames_differ():
    kept, skipped = prefer_pdf_over_hwp([
        _item("uuid-1.pdf", title="붙임_개정안.pdf"),
        _item("uuid-2.hwp", title="붙임_개정안.hwp"),
    ])
    assert [item.filename_hint for item in kept] == ["uuid-1.pdf"]
    assert [item.filename_hint for item in skipped] == ["uuid-2.hwp"]


def test_generic_title_does_not_collapse_different_files():
    kept, skipped = prefer_pdf_over_hwp([
        _item("공고.pdf", title="첨부파일"),
        _item("별첨.hwp", title="첨부파일"),
    ])
    assert len(kept) == 2
    assert skipped == []


def test_format_word_in_parentheses_still_matches():
    kept, skipped = prefer_pdf_over_hwp([
        _item("보도자료.pdf", title="보도자료.pdf"),
        _item("보도자료(한글).hwp", title="보도자료(한글).hwp"),
    ])
    assert [item.filename_hint for item in kept] == ["보도자료.pdf"]
    assert len(skipped) == 1


def test_fetch_does_not_download_hwp_when_pdf_equivalent_exists(monkeypatch, tmp_path):
    html = """\
<div class="content">
  <a href="https://www.fsc.go.kr/files/notice.pdf">notice.pdf</a>
  <a href="https://www.fsc.go.kr/files/notice.hwp">notice.hwp</a>
  <a href="https://www.fsc.go.kr/files/extra.hwpx">extra.hwpx</a>
</div>
"""
    calls = []

    def fake_fetch(url, **kwargs):
        calls.append(url)
        if url.endswith(".pdf"):
            return url, b"%PDF-1.4\n", "application/pdf", 'attachment; filename="notice.pdf"'
        if url.endswith(".hwpx"):
            return url, b"HWPX-BYTES", "application/octet-stream", 'attachment; filename="extra.hwpx"'
        if url.endswith(".hwp"):
            raise AssertionError("duplicate hwp should not be downloaded: " + url)
        return url, html.encode("utf-8"), "text/html; charset=utf-8", None

    monkeypatch.setattr(source_fetch, "fetch_url", fake_fetch)
    root = tmp_path
    folder = root / "downloads"
    result = page_attachments.fetch_page_attachments(
        "https://www.fsc.go.kr/no010101/1",
        root=root,
        folder=folder,
    )
    assert result.ok is True
    names = [item.name for item in result.attached]
    assert names == ["notice.pdf", "extra.hwpx"]
    assert result.attached[0].source_type == "pdf"
    assert result.attached[1].source_type == "hwp"
    assert any("notice.hwp" in name for name in result.skipped_hwp)
    assert not any(call.endswith(".hwp") for call in calls)
    assert (folder / "notice.pdf").is_file()
    assert (folder / "extra.hwpx").is_file()
    assert not (folder / "notice.hwp").exists()


def test_content_disposition_names_drop_hwp_after_download(monkeypatch, tmp_path):
    html = """\
<div class="bd-view">
  <a href="https://www.fss.or.kr/fss/bbs/download.do?fileSn=1">첨부</a>
  <a href="https://www.fss.or.kr/fss/bbs/download.do?fileSn=2">첨부</a>
</div>
"""

    def fake_fetch(url, **kwargs):
        if "fileSn=1" in url:
            return url, b"%PDF-1.4\n", "application/pdf", 'attachment; filename="같은문서.pdf"'
        if "fileSn=2" in url:
            return url, b"HWP-BYTES", "application/octet-stream", 'attachment; filename="같은문서.hwp"'
        return url, html.encode("utf-8"), "text/html", None

    monkeypatch.setattr(source_fetch, "fetch_url", fake_fetch)
    root = tmp_path
    folder = root / "downloads"
    result = page_attachments.fetch_page_attachments(
        "https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=9",
        root=root,
        folder=folder,
    )
    assert [item.name for item in result.attached] == ["같은문서.pdf"]
    assert "같은문서.hwp" in result.skipped_hwp
    assert (folder / "같은문서.pdf").is_file()
    assert not (folder / "같은문서.hwp").exists()


def test_download_page_attachments_route(monkeypatch, tmp_path):
    import editor.app as editor_app

    html = '<div class="content"><a href="https://www.fsc.go.kr/files/a.pdf">a.pdf</a><a href="https://www.fsc.go.kr/files/a.hwp">a.hwp</a></div>'

    def fake_fetch(url, **kwargs):
        if url.endswith(".hwp"):
            raise AssertionError(url)
        if url.endswith(".pdf"):
            return url, b"%PDF-1.4\n", "application/pdf", 'attachment; filename="a.pdf"'
        return url, html.encode("utf-8"), "text/html", None

    monkeypatch.setattr(editor_config, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(editor_config, "load_config", lambda: {"downloads_folder": "downloads/"})
    monkeypatch.setattr(source_fetch, "fetch_url", fake_fetch)
    client = editor_app.app.test_client()
    resp = client.post("/api/source/download_page_attachments", json={"url": "https://www.fsc.go.kr/no010101/8"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["attached"] == [{"type": "pdf", "ref": "downloads/a.pdf", "name": "a.pdf"}]
    assert data["skipped_hwp"]
    assert (tmp_path / "downloads" / "a.pdf").is_file()
    assert not (tmp_path / "downloads" / "a.hwp").exists()
