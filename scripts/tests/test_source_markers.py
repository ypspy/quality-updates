import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from editor.parser import parse_links
from editor.saver import apply_curation


def test_parse_source_marker_sets_source_and_needs_summary():
    md = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- source: pdf|downloads/a.pdf -->
"""
    links = parse_links(md)
    assert len(links) == 1
    a = links[0]
    assert a["state"] == "needs_summary"
    assert a["source"] == {"type": "pdf", "ref": "downloads/a.pdf"}
    assert a["pdf_path"] == "downloads/a.pdf"


def test_parse_source_url_alias_maps_to_web():
    md = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- source: url|https://example.com/page -->
"""
    links = parse_links(md)
    assert len(links) == 1
    a = links[0]
    assert a["state"] == "needs_summary"
    assert a["source"] == {"type": "web", "ref": "https://example.com/page"}


def test_parse_source_clip_marker_sets_source_and_needs_summary():
    md = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- source: clip|clip_20260325_abcdef -->
"""
    links = parse_links(md)
    assert len(links) == 1
    a = links[0]
    assert a["state"] == "needs_summary"
    assert a["source"] == {"type": "clip", "ref": "clip_20260325_abcdef"}


def test_parse_legacy_pdf_marker_sets_source_and_pdf_path():
    md = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- pdf: downloads/a.pdf -->
"""
    links = parse_links(md)
    assert len(links) == 1
    a = links[0]
    assert a["state"] == "needs_summary"
    assert a["source"] == {"type": "pdf", "ref": "downloads/a.pdf"}
    assert a["pdf_path"] == "downloads/a.pdf"


def test_apply_curation_writes_source_marker_and_removes_legacy_pdf():
    original = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- pdf: downloads/old.pdf -->

"""
    curation = [
        {
            "line_index": 2,
            "state": "needs_summary",
            "pdf_path": "downloads/old.pdf",
            "source": {"type": "pdf", "ref": "downloads/new.pdf"},
        }
    ]
    result = apply_curation(original, curation)
    assert "<!-- pdf:" not in result
    assert "<!-- source: pdf|downloads/new.pdf -->" in result


def test_apply_curation_with_only_pdf_path_normalizes_to_source_marker():
    original = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- pdf: downloads/old.pdf -->

"""
    curation = [{"line_index": 2, "state": "needs_summary", "pdf_path": "downloads/x.pdf", "source": None}]
    result = apply_curation(original, curation)
    assert "<!-- pdf:" not in result
    assert "<!-- source: pdf|downloads/x.pdf -->" in result


def test_apply_curation_removes_source_marker_when_undecided():
    original = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- source: pdf|downloads/a.pdf -->

"""
    curation = [{"line_index": 2, "state": "undecided", "pdf_path": None, "source": None}]
    result = apply_curation(original, curation)
    assert "<!-- source:" not in result


def test_apply_curation_preserves_existing_source_marker_when_needs_summary_but_payload_has_no_source_or_pdf():
    original = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- source: web|https://example.com/page -->

"""
    # Simulate current UI: state needs_summary but no source/pdf_path provided.
    curation = [{"line_index": 2, "state": "needs_summary", "pdf_path": None, "source": None}]
    result = apply_curation(original, curation)
    assert "<!-- source: web|https://example.com/page -->" in result


def test_parse_multiple_source_markers_keeps_single_marker_shape():
    md = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- source: pdf|downloads/a.pdf -->
<!-- source: pdf|downloads/b.pdf -->
<!-- source: hwp|downloads/c.hwp -->
"""
    links = parse_links(md)
    assert len(links) == 1
    item = links[0]
    assert item["state"] == "needs_summary"
    assert item["source"] == {"type": "pdf", "ref": "downloads/a.pdf"}
    assert item["pdf_path"] == "downloads/a.pdf"
    assert item["sources"] == [
        {"type": "pdf", "ref": "downloads/a.pdf"},
        {"type": "pdf", "ref": "downloads/b.pdf"},
        {"type": "hwp", "ref": "downloads/c.hwp"},
    ]


def test_parse_single_source_marker_still_one_entry():
    md = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- source: pdf|downloads/a.pdf -->
"""
    item = parse_links(md)[0]
    assert item["sources"] == [{"type": "pdf", "ref": "downloads/a.pdf"}]


def test_parse_hwpx_alias_is_hwp():
    md = """\
- (25-03-01) [A](https://a.com)
<!-- source: hwpx|downloads/a.hwpx -->
"""
    item = parse_links(md)[0]
    assert item["source"] == {"type": "hwp", "ref": "downloads/a.hwpx"}


def test_apply_curation_writes_every_source_marker():
    original = """\
### 금융감독원

- (25-03-01) [A](https://a.com)

"""
    curation = [
        {
            "line_index": 2,
            "state": "needs_summary",
            "sources": [
                {"type": "pdf", "ref": "downloads/a.pdf"},
                {"type": "pdf", "ref": "downloads/b.pdf"},
                {"type": "hwp", "ref": "downloads/c.hwp"},
            ],
        }
    ]
    result = apply_curation(original, curation)
    lines = result.splitlines()
    idx = next(i for i, line in enumerate(lines) if "[A]" in line)
    assert lines[idx + 1] == "<!-- source: pdf|downloads/a.pdf -->"
    assert lines[idx + 2] == "<!-- source: pdf|downloads/b.pdf -->"
    assert lines[idx + 3] == "<!-- source: hwp|downloads/c.hwp -->"


def test_apply_curation_preserves_every_existing_marker_when_payload_has_no_source():
    original = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- source: pdf|downloads/a.pdf -->
<!-- source: hwp|downloads/b.hwp -->

"""
    curation = [{"line_index": 2, "state": "needs_summary", "pdf_path": None, "source": None}]
    result = apply_curation(original, curation)
    assert "<!-- source: pdf|downloads/a.pdf -->" in result
    assert "<!-- source: hwp|downloads/b.hwp -->" in result


def test_apply_curation_removes_every_source_marker_when_undecided():
    original = """\
### 금융감독원

- (25-03-01) [A](https://a.com)
<!-- source: pdf|downloads/a.pdf -->
<!-- source: hwp|downloads/b.hwp -->

"""
    curation = [{"line_index": 2, "state": "undecided", "pdf_path": None, "source": None}]
    result = apply_curation(original, curation)
    assert "<!-- source:" not in result

