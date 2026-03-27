import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_strips_empty_and_whitespace_only_wrappers():
    import editor.html_sanitize as hs

    html = (
        '<div><p></p><span> \t\n</span><span>&nbsp;</span></div>'
        '<p><span></span><strong>  </strong></p>'
        '<div><p>real</p></div>'
    )
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a")
    assert "real" in out
    assert out.count("<p>") == 1
    assert "strong" not in out.lower()


def test_strips_br_only_wrappers_keeps_br_between_text_and_empty_link():
    import editor.html_sanitize as hs

    html = (
        '<p><span><br></span></p><p><hr></p>'
        '<p>a<br>b</p><a href="/x"></a><p>z</p>'
    )
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/base/")
    assert "a" in out and "b" in out
    assert "<br" in out.lower()
    assert "<hr" not in out.lower()
    assert "/api/source/preview?url=" in out
    assert "z" in out


def test_removes_script_tags():
    import editor.html_sanitize as hs

    html = "<div>ok</div><script>alert(1)</script>"
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a")
    assert "<script" not in out.lower()
    assert "alert(1)" not in out


@pytest.mark.parametrize("tag", ["style", "iframe", "object", "embed", "svg"])
def test_removes_other_dangerous_tags(tag: str):
    import editor.html_sanitize as hs

    # Some tags like <embed> are void elements; text may end up outside the tag
    # in the parser. We assert tag removal only.
    html = f"<div>ok</div><{tag}>bad</{tag}>"
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a")
    assert f"<{tag}" not in out.lower()


def test_removes_inline_event_handlers():
    import editor.html_sanitize as hs

    html = '<a href="https://example.com" onclick="alert(1)">x</a>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a")
    assert "onclick" not in out.lower()
    assert "alert(1)" not in out


def test_removes_srcdoc_and_formaction_attrs():
    import editor.html_sanitize as hs

    html = '<iframe srcdoc="<p>bad</p>"></iframe><form><button formaction="https://evil">x</button></form>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a")
    assert "srcdoc" not in out.lower()
    assert "formaction" not in out.lower()


def test_drops_javascript_href():
    import editor.html_sanitize as hs

    html = '<a href="javascript:alert(1)">x</a>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a")
    # href should be removed/neutralized; x should remain.
    assert "javascript:" not in out.lower()
    assert "href=" not in out.lower()
    assert ">x<" in out


@pytest.mark.parametrize("href", ["java\nscript:alert(1)", "java\tscript:alert(1)", " jAvAsCrIpT:alert(1)"])
def test_drops_obfuscated_javascript_href(href: str):
    import editor.html_sanitize as hs

    html = f'<a href="{href}">x</a>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a")
    assert "javascript:" not in out.lower()
    assert "href=" not in out.lower()


def test_drops_data_scheme_href():
    import editor.html_sanitize as hs

    html = '<a href="data:text/html,<script>alert(1)</script>">x</a>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a")
    assert "href=" not in out.lower()


def test_drops_javascript_src():
    import editor.html_sanitize as hs

    html = '<img src="javascript:alert(1)"><div>ok</div>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a")
    assert "javascript:" not in out.lower()
    assert "alert(1)" not in out


def test_rewrites_relative_link_with_base_url():
    import editor.html_sanitize as hs

    html = '<a href="../b?q=1#frag">go</a>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a/c/")
    assert "/api/source/preview?url=" in out
    assert "https%3A%2F%2Fexample.com%2Fa%2Fb%3Fq%3D1%23frag" in out


def test_rewrites_absolute_link_too():
    import editor.html_sanitize as hs

    html = '<a href="https://other.example/x">go</a>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/a/")
    assert "/api/source/preview?url=" in out
    assert "https%3A%2F%2Fother.example%2Fx" in out


def test_rewritten_link_contains_urlencoded_absolute_url():
    import editor.html_sanitize as hs

    html = '<a href="/path with spaces?q=hello world">go</a>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/base/")
    # Must contain encoded absolute URL in query param.
    assert "/api/source/preview?url=" in out
    assert "https%3A%2F%2Fexample.com%2Fpath%20with%20spaces%3Fq%3Dhello%20world" in out


def test_bleach_allowlist_strips_unapproved_tags_and_attrs():
    import editor.html_sanitize as hs

    html = '<div><img src="https://example.com/x.png"><a href="/x" style="color:red" data-x="1">go</a></div>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/base/")
    assert "<img" not in out.lower()  # not in allowlist
    assert "style=" not in out.lower()  # not allowed attr
    assert "data-x" not in out.lower()  # not allowed attr


def test_rewritten_links_have_noopener_rel():
    import editor.html_sanitize as hs

    html = '<a href="/x">go</a>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/base/")
    assert "rel=" in out.lower()
    assert "noopener" in out.lower()


def test_narrow_fss_bbs_view_extracts_bd_view_only():
    import editor.html_sanitize as hs

    html = """
    <html><body>
    <div class="bd-view-nav"><a>이전글</a></div>
    <div class="bd-view"><h2 class="subject">TITLE</h2><div class="dbdata">BODY</div></div>
    <div class="btn-set"><a class="b-list">목록</a></div>
    </body></html>
    """
    u = "https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=1&menuNo=200218"
    out = hs.narrow_preview_html(html, u)
    assert "TITLE" in out and "BODY" in out
    assert "이전글" not in out
    assert "목록" not in out


def test_narrow_preview_noop_for_non_fss_host():
    import editor.html_sanitize as hs

    html = '<div class="bd-view"><p>x</p></div>'
    assert hs.narrow_preview_html(html, "https://example.com/fss/bbs/x/view.do") == html


def test_narrow_preview_noop_for_fss_non_bbs_view():
    import editor.html_sanitize as hs

    html = '<div id="content"><div class="bd-view"><p>z</p></div></div>'
    u = "https://www.fss.or.kr/fss/main/main.do"
    assert hs.narrow_preview_html(html, u) == html


def test_narrow_fsc_extracts_content_and_strips_breadcrumb_and_survey():
    import editor.html_sanitize as hs

    html = """
    <html><body>
    <header>SITE</header>
    <div class="content">
      <div class="location-wrap"><span>breadcrumb</span></div>
      <div class="content-header"><h3>보도자료</h3></div>
      <div class="content-body"><div class="subject">TITLE</div><p>BODY</p></div>
      <div class="content-foot"><span>만족도</span></div>
    </div>
    <footer>FOOTER</footer>
    </body></html>
    """
    u = "https://www.fsc.go.kr/no010101/85878"
    out = hs.narrow_preview_html(html, u)
    assert "TITLE" in out and "BODY" in out
    assert "breadcrumb" not in out
    assert "만족도" not in out
    assert "SITE" not in out
    assert "FOOTER" not in out


def test_narrow_preview_noop_for_fsc_without_content_div():
    import editor.html_sanitize as hs

    html = "<html><body><main><p>x</p></main></body></html>"
    assert hs.narrow_preview_html(html, "https://fsc.go.kr/") == html


def test_narrow_kasb_keeps_h3_and_following_siblings_only():
    import editor.html_sanitize as hs

    html = """
    <html><body>
    <header><h3>Nav</h3></header>
    <div id="contents">
      <p>Before</p>
      <h3>제목</h3>
      <p>본문1</p>
      <div class="files">첨부</div>
    </div>
    <footer>FOOTER</footer>
    </body></html>
    """
    u = "https://www.kasb.or.kr/front/board/comm020View.do?seq=1"
    out = hs.narrow_preview_html(html, u)
    assert "제목" in out and "본문1" in out and "첨부" in out
    assert "Before" not in out
    assert "FOOTER" not in out
    assert "Nav" not in out


def test_narrow_kasb_unwraps_table_and_rewires_filedownload():
    import editor.html_sanitize as hs

    html = """
    <html><body><div id="contents">
      <h3>제목</h3>
      <table><tr><td>등록일</td><td>첨부</td></tr></table>
      <a onclick="javascript:fileDownload('-12','3'); return false;"><span>첨부.hwp</span></a>
    </div></body></html>
    """
    u = "https://www.kasb.or.kr/front/board/comm020View.do?seq=1"
    out = hs.narrow_preview_html(html, u)
    assert "<table" not in out.lower()
    assert "preview-unwrapped-table" in out
    assert "/api/source/kasb_file?" in out
    assert "fileNo=-12" in out
    assert "fileSeq=3" in out


def test_sanitize_preserves_kasb_file_proxy_href():
    import editor.html_sanitize as hs

    html = '<div><a href="/api/source/kasb_file?fileNo=-1&fileSeq=2">다운</a></div>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://www.kasb.or.kr/front/x")
    assert "/api/source/kasb_file?" in out
    assert "fileNo=-1" in out
    assert "fileSeq=2" in out
    assert "/api/source/preview?url=" not in out


def test_narrow_kicpa_unwraps_tables_to_divs():
    import editor.html_sanitize as hs

    html = """
    <html><body>
    <div id="contents">
      <table><tr><td><p>셀A</p></td><th>셀B</th></tr></table>
    </div>
    </body></html>
    """
    u = "https://www.kicpa.or.kr/board/read.brd?boardId=noti"
    out = hs.narrow_preview_html(html, u)
    assert "<table" not in out.lower()
    assert "preview-unwrapped-table" in out
    assert "preview-tr" in out
    assert "preview-td" in out
    assert "셀A" in out and "셀B" in out

