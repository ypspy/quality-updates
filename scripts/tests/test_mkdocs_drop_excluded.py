# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mkdocs_drop_excluded import on_files  # noqa: E402


class _Inclusion:
    def __init__(self, excluded):
        self._excluded = excluded

    def is_excluded(self):
        return self._excluded


class _File:
    def __init__(self, name, excluded):
        self.name = name
        self.inclusion = _Inclusion(excluded)


class _Files:
    def __init__(self, files):
        self._files = list(files)

    def __iter__(self):
        return iter(self._files)

    def remove(self, file):
        self._files.remove(file)


def test_on_files_drops_only_excluded_docs():
    keep = _File("index.md", False)
    drop = _File("project/README.md", True)
    files = _Files([keep, drop])

    result = on_files(files, config=None)

    assert result._files == [keep]
