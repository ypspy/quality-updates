import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from editor.parser import parse_links
from source_marker_layout import fix_mkdocs_source_layout, find_unsafe_source_layout, normalize_quarterly_spacing


def test_unsafe_layout_detected():
    md = """\
- (26-03-29) [title](https://example.com/a)
<!-- source: pdf|downloads/a.pdf -->

    !!! note "주요 내용"

        - bullet
"""
    issues = find_unsafe_source_layout(md.splitlines())
    assert len(issues) == 1


def test_fix_layout_renders_admonition():
    md = """\
- (26-03-29) [title](https://example.com/a)
<!-- source: pdf|downloads/a.pdf -->

    !!! note "주요 내용"

        - bullet
"""
    fixed, n = fix_mkdocs_source_layout(md)
    assert n == 1
    assert "<!-- source: pdf|downloads/a.pdf -->" in fixed
    assert fixed.index("<!-- source:") > fixed.index("](https://")
    assert "    !!! note" in fixed
    assert find_unsafe_source_layout(fixed.splitlines()) == []


def test_normalize_spacing_collapses_source_note_gap():
    md = """\
- (26-03-29) [title](https://example.com/a)

    <!-- source: pdf|downloads/a.pdf -->


    !!! note "주요 내용"

        - bullet
"""
    fixed, n = normalize_quarterly_spacing(md)
    assert n >= 1
    assert "pdf -->\n\n\n    !!!" not in fixed
    assert "pdf -->\n\n    !!!" in fixed


def test_normalize_spacing_uniform_no_summary_gap():
    md = """\
#### 보도자료

- (26-03-31) [A](https://example.com/a)
<!-- no_summary -->
- (26-03-29) [B](https://example.com/b)

    !!! note "주요 내용"

        - bullet
"""
    fixed, _ = normalize_quarterly_spacing(md)
    assert "no_summary -->\n\n- (26-03-29)" in fixed


def test_normalize_spacing_preserves_note_title_gap():
    md = """\
- (26-03-29) [title](https://example.com/a)

    !!! note "주요 내용"

        - bullet
"""
    fixed, n = normalize_quarterly_spacing(md)
    assert n == 0
    assert '!!! note "주요 내용"\n\n        - bullet' in fixed


def test_parser_done_with_indented_source():
    md = """\
### 금융감독원

- (26-03-29) [title](https://example.com/a)

    <!-- source: pdf|downloads/a.pdf -->

    !!! note "주요 내용"

        - bullet
"""
    links = parse_links(md)
    assert len(links) == 1
    link = links[0]
    assert link["state"] == "done"
    assert link["source"] == {"type": "pdf", "ref": "downloads/a.pdf"}
