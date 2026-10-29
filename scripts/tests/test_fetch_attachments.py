# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import auto_curate
import editor.source_fetch as source_fetch
import fetch_attachments
from fetch_attachments import needs_attachment_fetch


HTML = """\
<div class="content">
  <a href="https://www.fsc.go.kr/files/notice.pdf">notice.pdf</a>
  <a href="https://www.fsc.go.kr/files/notice.hwp">notice.hwp</a>
  <a href="https://www.fsc.go.kr/files/extra.hwpx">extra.hwpx</a>
</div>
"""

QUARTER = """\
### 금융위원회

#### 보도자료

- (26-03-01) [보도](https://www.fsc.go.kr/no010101/1)
<!-- source: pdf|pending -->

- (26-03-02) [건너뜀](https://www.fsc.go.kr/no010101/2)
<!-- skip -->

- (26-03-03) [링크만](https://www.fsc.go.kr/no010101/3)
<!-- no_summary -->

- (26-03-04) [외부감사 제도 개정](https://www.fsc.go.kr/no010101/4)
"""


def _fake_fetch(calls):
    def fake_fetch(url, **kwargs):
        calls.append(url)
        if url.endswith(".hwp"):
            raise AssertionError("duplicate hwp should not be downloaded: " + url)
        if url.endswith(".pdf"):
            return url, b"%PDF-1.4\n", "application/pdf", 'attachment; filename="notice.pdf"'
        if url.endswith(".hwpx"):
            return url, b"HWPX-BYTES", "application/octet-stream", 'attachment; filename="extra.hwpx"'
        return url, HTML.encode("utf-8"), "text/html; charset=utf-8", None

    return fake_fetch


def test_needs_attachment_fetch_respects_skip_and_link_only():
    decision = auto_curate.Decision(
        state="needs_summary",
        rule_id="t",
        reason="",
        confidence=1,
        source_type="pdf",
        source_ref="pending",
    )
    assert needs_attachment_fetch({"state": "skip"}, decision) is False
    assert needs_attachment_fetch({"state": "no_summary"}, decision) is False
    assert needs_attachment_fetch({"state": "done"}, decision) is False
    assert needs_attachment_fetch({"state": "needs_summary"}, None) is True
    assert needs_attachment_fetch({"state": "undecided"}, decision) is True
    assert needs_attachment_fetch({"state": "undecided"}, None) is False


def test_run_writes_markers_report_and_skips_duplicate_hwp(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(source_fetch, "fetch_url", _fake_fetch(calls))
    md_path = tmp_path / "quarter.md"
    md_path.write_text(QUARTER, encoding="utf-8")
    root = tmp_path
    folder = root / "downloads"
    report_path = folder / "fetch-attachments-report.md"

    summary = fetch_attachments.run(md_path, report_path=report_path, root=root, folder=folder)
    body = md_path.read_text(encoding="utf-8")
    assert "<!-- source: pdf|pending -->" not in body
    assert "<!-- source: pdf|downloads/notice.pdf -->" in body
    assert "<!-- source: hwp|downloads/extra.hwpx -->" in body
    assert "<!-- source: hwp|downloads/notice.hwp -->" not in body
    assert "<!-- skip -->" in body
    assert "<!-- no_summary -->" in body
    assert "https://www.fsc.go.kr/no010101/2" not in "\n".join(calls)
    assert "https://www.fsc.go.kr/no010101/3" not in "\n".join(calls)
    assert not any(url.endswith(".hwp") for url in calls)

    report = report_path.read_text(encoding="utf-8")
    assert "downloads/notice.pdf" in report
    assert "downloads/extra.hwpx" in report
    assert "notice.hwp" in report.split("## PDF와 같아 건너뛴 HWP")[1].split("## 다운로드 실패")[0]
    whale = report.split("## 수동 변환 필요 (네이버 웨일)")[1].split("## PDF와 같아 건너뛴 HWP")[0]
    assert "extra.hwpx" in whale
    assert "notice.hwp" not in whale
    assert summary.updated == 2

    calls.clear()
    again = fetch_attachments.run(md_path, report_path=report_path, root=root, folder=folder)
    assert again.updated == 0
    assert list(folder.glob("notice*.pdf")) == [folder / "notice.pdf"]
    assert not any(url.endswith(".hwp") for url in calls)


def test_page_failure_is_reported_and_does_not_invent_markers(monkeypatch, tmp_path):
    def fake_fetch(url, **kwargs):
        raise ValueError("remote HTTP 500")

    monkeypatch.setattr(source_fetch, "fetch_url", fake_fetch)
    md_path = tmp_path / "quarter.md"
    original = "- (26-03-01) [보도](https://www.fsc.go.kr/no010101/1)\n<!-- source: pdf|pending -->\n"
    md_path.write_text(original, encoding="utf-8")
    report_path = tmp_path / "downloads" / "report.md"
    summary = fetch_attachments.run(
        md_path,
        report_path=report_path,
        root=tmp_path,
        folder=tmp_path / "downloads",
    )
    assert md_path.read_text(encoding="utf-8") == original
    assert summary.updated == 0
    text = report_path.read_text(encoding="utf-8")
    assert "remote HTTP 500" in text
    assert "## 다운로드 실패" in text
