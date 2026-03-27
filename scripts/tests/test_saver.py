import sys, os, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from editor.saver import apply_curation

ORIGINAL = """\
### 금융감독원

- (25-01-10) [제목A](https://fss.or.kr/a)

- (25-01-15) [제목B](https://fss.or.kr/b)
<!-- skip -->

- (25-01-20) [제목C](https://fss.or.kr/c)
<!-- pdf: downloads/old.pdf -->

- (25-01-25) [제목D](https://fss.or.kr/d)

    !!! note "주요 내용"

        - 내용

## Appendix A. Complete List

- (25-02-01) [AppendixLink](https://fss.or.kr/x)
"""

# Curation: A→skip, B→needs_summary+pdf, C→undecided, D(done)→unchanged
CURATION = [
    {'title': '제목A', 'line_index': 2, 'state': 'skip', 'pdf_path': None},
    {'title': '제목B', 'line_index': 4, 'state': 'needs_summary', 'pdf_path': 'downloads/250115.pdf'},
    {'title': '제목C', 'line_index': 7, 'state': 'undecided', 'pdf_path': None},
    {'title': '제목D', 'line_index': 10, 'state': 'done', 'pdf_path': None},
]


def test_skip_writes_marker_after_link():
    result = apply_curation(ORIGINAL, CURATION)
    lines = result.splitlines()
    idx = next(i for i, l in enumerate(lines) if '제목A' in l)
    assert lines[idx + 1] == '<!-- skip -->'


def test_pdf_updated():
    result = apply_curation(ORIGINAL, CURATION)
    lines = result.splitlines()
    idx = next(i for i, l in enumerate(lines) if '제목B' in l)
    assert lines[idx + 1] == '<!-- source: pdf|downloads/250115.pdf -->'


def test_old_skip_removed():
    result = apply_curation(ORIGINAL, CURATION)
    # B had <!-- skip -->, now <!-- source: ... -->; A still has <!-- skip -->
    assert result.count('<!-- skip -->') == 1


def test_no_summary_writes_marker_after_link():
    content = "- (25-01-10) [A](https://a.com)\n\n"
    curation = [{"line_index": 0, "state": "no_summary", "pdf_path": None}]
    result = apply_curation(content, curation)
    assert "<!-- no_summary -->" in result


def test_old_pdf_removed_for_undecided():
    result = apply_curation(ORIGINAL, CURATION)
    assert 'downloads/old.pdf' not in result


def test_done_unchanged():
    result = apply_curation(ORIGINAL, CURATION)
    assert '!!! note "주요 내용"' in result


def test_appendix_preserved():
    result = apply_curation(ORIGINAL, CURATION)
    assert '## Appendix A. Complete List' in result
    assert 'AppendixLink' in result


def test_bak_created(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text(ORIGINAL, encoding='utf-8')
    from editor.saver import save_with_backup
    save_with_backup(str(md_file), ORIGINAL, CURATION)
    assert (tmp_path / "test.md.bak").exists()


def test_blank_line_preserved_between_items():
    content = "- (25-01-10) [A](https://a.com)\n<!-- skip -->\n\n- (25-01-11) [B](https://b.com)\n"
    curation = [{'line_index': 0, 'state': 'undecided', 'pdf_path': None}]
    result = apply_curation(content, curation)
    lines = result.splitlines()
    idx_a = next(i for i, l in enumerate(lines) if '[A]' in l)
    idx_b = next(i for i, l in enumerate(lines) if '[B]' in l)
    assert idx_b - idx_a == 2, f"expected blank line between items, got idx_a={idx_a}, idx_b={idx_b}"


def test_needs_summary_no_pdf_saves_as_undecided():
    content = "- (25-01-10) [A](https://a.com)\n\n"
    curation = [{'line_index': 0, 'state': 'needs_summary', 'pdf_path': None}]
    result = apply_curation(content, curation)
    assert '<!-- pdf:' not in result
    assert '<!-- source:' not in result
    assert '<!-- skip -->' not in result


def test_needs_summary_web_writes_source_marker():
    # WEB 출처 ref는 행의 원문 링크 URL과 동일하게 저장한다.
    content = "- (25-01-10) [A](https://a.com)\n\n"
    curation = [
        {
            'line_index': 0,
            'state': 'needs_summary',
            'pdf_path': None,
            'source': {'type': 'web', 'ref': 'https://a.com'},
        }
    ]
    result = apply_curation(content, curation)
    assert '<!-- source: web|https://a.com -->' in result


def test_crlf_second_link_undecided_removes_skip():
    """CRLF: ``<!-- skip -->\\r`` must be recognized so markers apply to the correct link."""
    content = (
        "- (23-06-28) [A](https://a.example)\r\n"
        "- (23-06-27) [B](https://b.example)\r\n"
        "<!-- skip -->\r\n"
    )
    curation = [
        {"line_index": 0, "state": "skip", "pdf_path": None, "title": "A"},
        {"line_index": 1, "state": "undecided", "pdf_path": None, "title": "B"},
    ]
    result = apply_curation(content, curation)
    assert result.count("<!-- skip -->") == 1
    lines = result.splitlines()
    idx_a = next(i for i, l in enumerate(lines) if "[A]" in l)
    idx_b = next(i for i, l in enumerate(lines) if "[B]" in l)
    assert lines[idx_a + 1] == "<!-- skip -->"
    assert idx_b + 1 >= len(lines) or lines[idx_b + 1] != "<!-- skip -->"


def test_line_index_string_coerced():
    content = "- (25-01-10) [A](https://a.com)\n<!-- skip -->\n"
    curation = [{"line_index": "0", "state": "undecided", "pdf_path": None}]
    result = apply_curation(content, curation)
    assert "<!-- skip -->" not in result


def test_needs_summary_clip_writes_source_marker():
    content = "- (25-01-10) [A](https://a.com)\n\n"
    curation = [
        {
            'line_index': 0,
            'state': 'needs_summary',
            'pdf_path': None,
            'source': {'type': 'clip', 'ref': 'clip_1700000000_a1b2c3d4'},
        }
    ]
    result = apply_curation(content, curation)
    assert '<!-- source: clip|clip_1700000000_a1b2c3d4 -->' in result
