# -*- coding: utf-8 -*-
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quarterly_handoff import export_quarter

QUARTER = """---
title: q
---

### 금융위원회

#### 보도자료

- (26-09-11) [계리가정](https://fsc.go.kr/no010101/1)

    <!-- source: pdf|downloads/ifrs.pdf -->
    <!-- source: hwp|downloads/ifrs.hwpx -->

    !!! note "주요 내용"

        - (보고서) 매년 제출

- (26-09-01) [시험 공고](https://fsc.go.kr/no010101/2)
    <!-- no_summary -->
    <!-- source: pdf|downloads/exam.pdf -->

## Appendix A. Complete List

- (26-09-02) [미선별](https://fsc.go.kr/no010101/3)
    <!-- source: pdf|downloads/appendix.pdf -->
"""


def test_export_copies_body_pdf_and_note_without_rereading(tmp_path: Path):
    root = tmp_path / "repo"
    downloads = root / "downloads"
    downloads.mkdir(parents=True)
    (downloads / "ifrs.pdf").write_bytes(b"%PDF-1")
    (downloads / "ifrs.hwpx").write_bytes(b"HWPX")
    (downloads / "exam.pdf").write_bytes(b"%PDF-EXAM")
    (downloads / "appendix.pdf").write_bytes(b"%PDF-APP")
    md = root / "2026-07-01_to_2026-09-30.md"
    md.write_text(QUARTER, encoding="utf-8")
    dest = tmp_path / "raw"
    dest.mkdir()
    result = export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5))
    copied_pdf = dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "ifrs.pdf"
    record = dest / "quality-updates-processed" / "2026-07-01_to_2026-09-30"
    assert copied_pdf.read_bytes() == b"%PDF-1"
    assert not (dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "ifrs.hwpx").exists()
    assert not (dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "exam.pdf").exists()
    assert not (dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "appendix.pdf").exists()
    assert "매년 제출" in next(record.glob("*.md")).read_text(encoding="utf-8")
    assert result.exit_code == 0
    again = export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5))
    assert again.copied == []


def _write_quarter(root: Path) -> tuple[Path, Path]:
    downloads = root / "downloads"
    downloads.mkdir(parents=True)
    (downloads / "ifrs.pdf").write_bytes(b"%PDF-1")
    (downloads / "ifrs.hwpx").write_bytes(b"HWPX")
    md = root / "2026-07-01_to_2026-09-30.md"
    md.write_text(QUARTER, encoding="utf-8")
    return md, downloads


def test_changed_bytes_get_a_dated_snapshot(tmp_path: Path):
    root = tmp_path / "repo"
    md, downloads = _write_quarter(root)
    dest = tmp_path / "raw"
    dest.mkdir()
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5))
    (downloads / "ifrs.pdf").write_bytes(b"%PDF-2")
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 6))
    folder = dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30"
    assert (folder / "ifrs.pdf").read_bytes() == b"%PDF-1"
    assert (folder / "ifrs--2026-11-06.pdf").read_bytes() == b"%PDF-2"


def test_missing_vault_root_copies_nothing(tmp_path: Path):
    root = tmp_path / "repo"
    md, downloads = _write_quarter(root)
    missing = tmp_path / "no-such-vault" / "raw"
    result = export_quarter(md, downloads, root / "clips", missing, date(2026, 11, 5))
    assert result.exit_code == 2
    assert not missing.exists()
