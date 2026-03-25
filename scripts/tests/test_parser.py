import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from editor.parser import parse_links

SAMPLE_MD = """
### 금융감독원

#### 보도자료

- (25-01-10) [제목A](https://fss.or.kr/a)
<!-- skip -->

- (25-01-15) [제목B](https://fss.or.kr/b)
<!-- pdf: downloads/250115.pdf -->

- (25-01-20) [제목C](https://fss.or.kr/c)

    !!! note "주요 내용"

        - 내용

- (25-01-25) [제목D](https://fss.or.kr/d)

### 금융위원회

- (25-02-01) [제목E](https://fsc.go.kr/e)

## Appendix A. Complete List

- (25-02-05) [Appendix링크](https://fss.or.kr/x)
"""


def test_parse_count():
    links = parse_links(SAMPLE_MD)
    assert len(links) == 5, f"expected 5 links (not Appendix), got {len(links)}"


def test_skip_state():
    links = parse_links(SAMPLE_MD)
    a = next(l for l in links if l['title'] == '제목A')
    assert a['state'] == 'skip'


def test_pdf_state():
    links = parse_links(SAMPLE_MD)
    b = next(l for l in links if l['title'] == '제목B')
    assert b['state'] == 'needs_summary'
    assert b['pdf_path'] == 'downloads/250115.pdf'
    assert b['source'] == {'type': 'pdf', 'ref': 'downloads/250115.pdf'}


def test_clip_source_marker_parsed():
    md = """
### 금융감독원

- (25-01-10) [클립항목](https://kasb.or.kr/x)
<!-- source: clip|clip_1700000000_a1b2c3d4 -->
"""
    links = parse_links(md)
    assert len(links) == 1
    x = links[0]
    assert x['state'] == 'needs_summary'
    assert x['source'] == {'type': 'clip', 'ref': 'clip_1700000000_a1b2c3d4'}
    assert x.get('pdf_path') in (None, '')


def test_done_state():
    links = parse_links(SAMPLE_MD)
    c = next(l for l in links if l['title'] == '제목C')
    assert c['state'] == 'done'


def test_undecided_state():
    links = parse_links(SAMPLE_MD)
    d = next(l for l in links if l['title'] == '제목D')
    assert d['state'] == 'undecided'


def test_agency_tagging():
    links = parse_links(SAMPLE_MD)
    a = next(l for l in links if l['title'] == '제목A')
    assert a['agency'] == '금융감독원'
    e = next(l for l in links if l['title'] == '제목E')
    assert e['agency'] == '금융위원회'


def test_appendix_excluded():
    links = parse_links(SAMPLE_MD)
    titles = [l['title'] for l in links]
    assert 'Appendix링크' not in titles


def test_line_index():
    # SAMPLE_MD starts with \n → line 0 is blank
    # line 5: 제목A, line 8: 제목B, line 11: 제목C, line 17: 제목D, line 21: 제목E
    links = parse_links(SAMPLE_MD)
    by_title = {l['title']: l for l in links}
    assert by_title['제목A']['line_index'] == 5
    assert by_title['제목B']['line_index'] == 8
    assert by_title['제목C']['line_index'] == 11
    assert by_title['제목D']['line_index'] == 17
    assert by_title['제목E']['line_index'] == 21
