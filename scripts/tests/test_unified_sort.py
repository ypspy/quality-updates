# -*- coding: utf-8 -*-
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler import unified


def test_sort_fss_items_ascending():
    items = [
        {"date": "26-03-31", "title": "c", "link": "http://c"},
        {"date": "26-01-08", "title": "a", "link": "http://a"},
        {"date": "26-02-15", "title": "b", "link": "http://b"},
    ]
    ordered = unified.sort_fss_items(items)
    assert [i["date"] for i in ordered] == ["26-01-08", "26-02-15", "26-03-31"]


def test_sort_fss_items_stable_on_same_date():
    items = [
        {"date": "26-01-08", "title": "first", "link": "http://1"},
        {"date": "26-01-08", "title": "second", "link": "http://2"},
    ]
    ordered = unified.sort_fss_items(items)
    assert [i["title"] for i in ordered] == ["first", "second"]


def test_sort_kicpa_dict_items_ascending():
    items = [
        {"date": datetime(2026, 3, 1), "title": "c", "link": "http://c"},
        {"date": datetime(2026, 1, 1), "title": "a", "link": "http://a"},
    ]
    ordered = unified.sort_kicpa_dict_items(items)
    assert [i["title"] for i in ordered] == ["a", "c"]


def test_sort_dated_tuples_ascending():
    items = [
        ("26-03-01", "c", "http://c"),
        ("26-01-01", "a", "http://a"),
    ]
    ordered = unified.sort_dated_tuples(items)
    assert [t[1] for t in ordered] == ["a", "c"]


def test_sort_md_link_lines_ascending():
    lines = [
        "- (26-03-01) [c](http://c)",
        "- (26-01-01) [a](http://a)",
    ]
    ordered = unified.sort_md_link_lines(lines)
    assert ordered[0].startswith("- (26-01-01)")
