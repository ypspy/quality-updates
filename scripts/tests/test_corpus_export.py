# -*- coding: utf-8 -*-
"""Corpus export tests."""

import json
import sys
from pathlib import Path

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
