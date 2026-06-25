# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skip_removal import remove_skip_pairs

SAMPLE = (
    "- (25-01-10) [A](https://a.com)\n"
    "<!-- skip -->\n"
    "\n"
    "- (25-01-11) [B](https://b.com)\n"
)


def test_removes_skip_pair():
    out = remove_skip_pairs(SAMPLE)
    assert "<!-- skip -->" not in out
    assert "[A]" not in out
    assert "[B]" in out


def test_preserves_non_skip_link():
    content = "- (25-01-10) [A](https://a.com)\n\n- (25-01-11) [B](https://b.com)\n"
    assert remove_skip_pairs(content) == content


def test_crlf_skip_marker():
    content = "- (25-01-10) [A](https://a.com)\r\n<!-- skip -->\r\n"
    out = remove_skip_pairs(content)
    assert "<!-- skip -->" not in out
    assert "[A]" not in out


def test_appendix_preserved():
    content = (
        "- (25-01-10) [A](https://a.com)\n"
        "<!-- skip -->\n"
        "\n"
        "## Appendix A. Complete List\n"
        "- (25-01-09) [Z](https://z.com)\n"
        "<!-- skip -->\n"
    )
    out = remove_skip_pairs(content)
    assert "[A]" not in out.split("## Appendix")[0]
    assert "[Z]" in out
    assert "<!-- skip -->" in out
