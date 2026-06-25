# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deploy_hints import collect_period_files, nav_paths_from_mkdocs


def test_collect_period_files(tmp_path):
    md = tmp_path / "docs" / "quality-updates" / "2026"
    md.mkdir(parents=True)
    f = md / "2026-01-01_to_2026-03-31.md"
    f.write_text(
        "---\nperiod:\n  start: 2026-01-01\n  end: 2026-03-31\n---\n",
        encoding="utf-8",
    )
    rows = collect_period_files(tmp_path / "docs")
    assert len(rows) == 1
    assert rows[0]["end"] == "2026-03-31"


def test_missing_nav_entry(tmp_path):
    md = tmp_path / "docs" / "quality-updates" / "2099"
    md.mkdir(parents=True)
    (md / "2099-01-01_to_2099-03-31.md").write_text(
        "---\nperiod:\n  start: 2099-01-01\n  end: 2099-03-31\n---\n",
        encoding="utf-8",
    )
    mk = tmp_path / "mkdocs.yml"
    mk.write_text("nav:\n  - home: index.md\n", encoding="utf-8")
    period = collect_period_files(tmp_path / "docs")
    nav = nav_paths_from_mkdocs(mk)
    rel = period[0]["path"].replace("docs/", "")
    assert rel not in nav
