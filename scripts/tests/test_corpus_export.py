# -*- coding: utf-8 -*-
"""Corpus export tests."""

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

SEOUL = ZoneInfo("Asia/Seoul")
NOV_20 = datetime(2026, 11, 20, 12, 0, tzinfo=SEOUL)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corpus.parse import parse_corpus_items
from export_corpus import export_corpus

SAMPLE_MD = """---
title: Test Q
period_label: 2025-Q4
period:
  start: 2025-10-01
  end: 2025-12-31
---

### 금융감독원

#### 보도자료

- (25-12-24) [내부회계 유의](https://fss.or.kr/icfr)
<!-- skip -->

- (25-12-22) [결산 유의](https://fss.or.kr/closing)

    !!! note "주요 내용"

        - (시사점) 외부감사인 유의사항
        | 회사 | 위반 |
        |------|------|
        | A社 | test |

- (25-12-20) [제목만](https://fss.or.kr/nosum)
<!-- no_summary -->

## Appendix A

- (25-12-01) [Appendix](https://fss.or.kr/x)
"""


def test_parse_skips_and_notes():
    _, items = parse_corpus_items(SAMPLE_MD, "docs/quality-updates/2025/test.md")
    assert len(items) == 2
    titles = {i.title for i in items}
    assert "내부회계 유의" not in titles
    assert "Appendix" not in titles
    done = next(i for i in items if i.title == "결산 유의")
    assert done.summary_status == "done"
    assert done.notes[0]["bullets"][0].startswith("(시사점)")
    assert done.notes[0]["tables"]
    nosum = next(i for i in items if i.title == "제목만")
    assert nosum.summary_status == "no_summary"


def test_export_dry_run(tmp_path):
    root = Path(__file__).resolve().parent.parent.parent
    stats = export_corpus(dry_run=True)
    assert stats["item_count"] >= 100
    assert stats["done"] >= 1


def test_export_rejects_nonstandard_quarter_markdown(tmp_path):
    qu = tmp_path / "docs" / "quality-updates"
    year = qu / "2026"
    year.mkdir(parents=True)
    (qu / "index.md").write_text("# 개요\n", encoding="utf-8")
    (year / "2026Q4.md").write_text("# 4분기\n", encoding="utf-8")
    nested = year / "q4"
    nested.mkdir()
    (nested / "2026-10-01_to_2026-12-31.md").write_text("# nested\n", encoding="utf-8")
    (qu / "2026-10-01_to_2026-12-31.md").write_text("# bare\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        export_corpus(dry_run=True, root=tmp_path)
    message = str(exc.value)
    assert "2026/2026Q4.md" in message
    assert "2026/q4/2026-10-01_to_2026-12-31.md" in message
    assert "docs/quality-updates/2026-10-01_to_2026-12-31.md" in message
    assert "index.md" not in message


def _sentinel_corpus(out: Path) -> tuple[bytes, bytes]:
    out.mkdir()
    jsonl = out / "corpus.jsonl"
    manifest = out / "manifest.json"
    jsonl.write_bytes(b"KEEP-JSONL\n")
    manifest.write_bytes(b"KEEP-MANIFEST\n")
    return jsonl.read_bytes(), manifest.read_bytes()


@pytest.mark.parametrize("dry_run", [False, True])
def test_export_refuses_early_standard_file_without_rewriting_corpus(tmp_path, dry_run):
    root = tmp_path / "repo"
    quarter = root / "docs" / "quality-updates" / "2026"
    quarter.mkdir(parents=True)
    (quarter / "2026-07-01_to_2026-09-30.md").write_text(
        "---\nperiod:\n  start: 2026-10-01\n  end: 2026-12-31\n---\n",
        encoding="utf-8",
    )
    out = tmp_path / "corpus"
    before_jsonl, before_manifest = _sentinel_corpus(out)

    with pytest.raises(SystemExit, match="2026-07-01_to_2026-09-30"):
        export_corpus(dry_run=dry_run, strict=False, output_dir=out, root=root, now=NOV_20)

    assert (out / "corpus.jsonl").read_bytes() == before_jsonl
    assert (out / "manifest.json").read_bytes() == before_manifest


@pytest.mark.parametrize("dry_run", [False, True])
def test_export_refuses_reversed_period_without_rewriting_corpus(tmp_path, dry_run):
    root = tmp_path / "repo"
    quarter = root / "docs" / "quality-updates" / "2026"
    quarter.mkdir(parents=True)
    (quarter / "2026-03-31_to_2026-01-01.md").write_text(
        "---\nperiod:\n  start: 2026-03-31\n  end: 2026-01-01\n---\n",
        encoding="utf-8",
    )
    out = tmp_path / "corpus"
    before_jsonl, before_manifest = _sentinel_corpus(out)

    with pytest.raises(SystemExit, match="2026-03-31_to_2026-01-01"):
        export_corpus(dry_run=dry_run, strict=False, output_dir=out, root=root, now=NOV_20)

    assert (out / "corpus.jsonl").read_bytes() == before_jsonl
    assert (out / "manifest.json").read_bytes() == before_manifest


def _early_quarter_repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    quarter = root / "docs" / "quality-updates" / "2026"
    quarter.mkdir(parents=True)
    (quarter / "2026-10-01_to_2026-12-31.md").write_text(
        "---\nperiod:\n  start: 2026-10-01\n  end: 2026-12-31\n---\n",
        encoding="utf-8",
    )
    return root, quarter


def test_export_allows_exact_allow_list_path(tmp_path):
    root, _quarter = _early_quarter_repo(tmp_path)
    data = root / "data"
    data.mkdir()
    (data / "qu-early-allow.txt").write_text(
        "# 윤석님 본인의 명시 승인\n"
        "docs/quality-updates/2026/2026-10-01_to_2026-12-31.md\n",
        encoding="utf-8",
    )
    stats = export_corpus(dry_run=True, strict=False, root=root, now=NOV_20)
    assert stats["item_count"] == 0


def test_export_refuses_early_file_when_allow_list_is_absent(tmp_path):
    root, _quarter = _early_quarter_repo(tmp_path)
    out = tmp_path / "corpus"
    before_jsonl, before_manifest = _sentinel_corpus(out)
    with pytest.raises(SystemExit, match="2026-10-01_to_2026-12-31"):
        export_corpus(dry_run=False, strict=False, output_dir=out, root=root, now=NOV_20)
    assert (out / "corpus.jsonl").read_bytes() == before_jsonl
    assert (out / "manifest.json").read_bytes() == before_manifest


def test_export_refuses_allow_list_path_variants(tmp_path):
    root, _quarter = _early_quarter_repo(tmp_path)
    data = root / "data"
    data.mkdir()
    (data / "qu-early-allow.txt").write_text(
        "docs/quality-updates/2026/q4/2026-10-01_to_2026-12-31.md\n"
        "docs/quality-updates/2026/2026-10-01_to_2026-12-31.md.bak\n"
        "docs/quality-updates/2026/2026-10-01–to–2026-12-31.md\n",
        encoding="utf-8",
    )
    out = tmp_path / "corpus"
    before_jsonl, before_manifest = _sentinel_corpus(out)
    with pytest.raises(SystemExit, match="2026-10-01_to_2026-12-31"):
        export_corpus(dry_run=False, strict=False, output_dir=out, root=root, now=NOV_20)
    assert (out / "corpus.jsonl").read_bytes() == before_jsonl
    assert (out / "manifest.json").read_bytes() == before_manifest


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize(
    "body",
    [
        pytest.param("---\nperiod: '2026-10-01 to 2026-12-31'\n---\n", id="string-period"),
        pytest.param(
            "---\nperiod:\n  start: 2026-07-01\n  end: 2026-02-31\n---\n",
            id="invalid-date-token",
        ),
        pytest.param(
            "---\nperiod:\n  from: 2026-10-01\n  to: 2026-12-31\n---\n",
            id="from-to-keys",
        ),
        pytest.param(
            "---\nperiod.start: 2026-10-01\nperiod.end: 2026-12-31\n---\n",
            id="toplevel-period-keys",
        ),
        pytest.param(
            "\ufeff---\nperiod:\n  start: 2026-10-01\n  end: 2026-12-31\n---\n",
            id="bom-early-period",
        ),
    ],
)
def test_export_refuses_bad_period_before_writing_jsonl(tmp_path, dry_run, body):
    root = tmp_path / "repo"
    quarter = root / "docs" / "quality-updates" / "2026"
    quarter.mkdir(parents=True)
    (quarter / "2026-07-01_to_2026-09-30.md").write_text(body, encoding="utf-8")
    out = tmp_path / "corpus"
    before_jsonl, before_manifest = _sentinel_corpus(out)

    with pytest.raises(SystemExit, match="2026-07-01_to_2026-09-30"):
        export_corpus(dry_run=dry_run, strict=False, output_dir=out, root=root, now=NOV_20)

    assert (out / "corpus.jsonl").read_bytes() == before_jsonl
    assert (out / "manifest.json").read_bytes() == before_manifest


@pytest.mark.parametrize("dry_run", [False, True])
def test_export_allow_list_does_not_hide_invalid_period(tmp_path, dry_run):
    root = tmp_path / "repo"
    quarter = root / "docs" / "quality-updates" / "2026"
    quarter.mkdir(parents=True)
    name = "2026-10-01_to_2026-12-31.md"
    (quarter / name).write_text("---\nperiod: 'not-a-mapping'\n---\n", encoding="utf-8")
    data = root / "data"
    data.mkdir()
    (data / "qu-early-allow.txt").write_text(
        "# 윤석님 본인의 명시 승인\n"
        f"docs/quality-updates/2026/{name}\n",
        encoding="utf-8",
    )
    out = tmp_path / "corpus"
    before_jsonl, before_manifest = _sentinel_corpus(out)

    with pytest.raises(SystemExit, match=name):
        export_corpus(dry_run=dry_run, strict=False, output_dir=out, root=root, now=NOV_20)

    assert (out / "corpus.jsonl").read_bytes() == before_jsonl
    assert (out / "manifest.json").read_bytes() == before_manifest


def test_export_writes_jsonl(tmp_path):
    out = tmp_path / "corpus"
    stats = export_corpus(dry_run=False, output_dir=out)
    assert (out / "corpus.jsonl").exists()
    assert (out / "manifest.json").exists()
    lines = (out / "corpus.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == stats["item_count"]
    first = json.loads(lines[0])
    assert first["schema_version"] == "1.0.0"
    assert "id" in first
    skip_ids = [json.loads(l) for l in lines if "skip" in l]
    assert not skip_ids
