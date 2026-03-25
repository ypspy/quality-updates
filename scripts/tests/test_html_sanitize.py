import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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

