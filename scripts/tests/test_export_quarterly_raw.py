# -*- coding: utf-8 -*-
import hashlib
import json
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


def _write_editor_clip(clips: Path, clip_id: str, raw: str) -> None:
    """Write the same JSON record shape as clip_store.create_clip."""
    body = raw.encode("utf-8")
    now = 1700000000.0
    record = {
        "id": clip_id,
        "created_at": now,
        "updated_at": now,
        "content_type": "text/plain",
        "raw": raw,
        "byte_length": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    (clips / f"{clip_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_selected_editor_clip_json_copies_raw_text(tmp_path: Path):
    root = tmp_path / "repo"
    downloads = root / "downloads"
    downloads.mkdir(parents=True)
    clips = root / "clips"
    clips.mkdir()
    selected = [
        ("clip_1700000000_a1b2c3d4", "clip_1700000000_a1b2c3d4", "제재 의결 원문\n둘째 단락"),
        ("clip_1700000001_b2c3d4e5", "clips/clip_1700000001_b2c3d4e5", "접두만 있는 원문"),
        ("clip_1700000002_c3d4e5f6", "clip_1700000002_c3d4e5f6.json", "json 접미 원문"),
        ("clip_1700000003_d4e5f6a7", "clips/clip_1700000003_d4e5f6a7.json", "접두와 json 원문"),
    ]
    for clip_id, _ref, raw in selected:
        _write_editor_clip(clips, clip_id, raw)
    _write_editor_clip(clips, "clip_1700000004_aabbccdd", "선택되지 않은 파일")

    items = []
    for index, (clip_id, ref, _raw) in enumerate(selected, start=11):
        items.append(
            f"- (26-09-{index:02d}) [클립 {index}](https://fsc.go.kr/no010101/{index})\n"
            f"    <!-- source: clip|{ref} -->\n"
        )
    quarter = (
        "---\ntitle: q\n---\n\n### 금융위원회\n\n#### 보도자료\n\n"
        + "\n".join(items)
        + """
- (26-09-01) [시험 공고](https://fsc.go.kr/no010101/2)
    <!-- no_summary -->
    <!-- source: clip|clip_1700000099_ffffffff -->

## Appendix A. Complete List

- (26-09-02) [미선별](https://fsc.go.kr/no010101/3)
    <!-- source: clip|clips/clip_1700000088_eeeeeeee.json -->
"""
    )
    md = root / "2026-07-01_to_2026-09-30.md"
    md.write_text(quarter, encoding="utf-8")
    dest = tmp_path / "raw"
    dest.mkdir()
    result = export_quarter(md, downloads, clips, dest, date(2026, 11, 5))
    folder = dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30"
    for clip_id, _ref, raw in selected:
        assert (folder / f"{clip_id}.txt").read_text(encoding="utf-8") == raw
    assert not (folder / "clip_1700000004_aabbccdd.txt").exists()
    assert not (folder / "clip_1700000099_ffffffff.txt").exists()
    assert not (folder / "clip_1700000088_eeeeeeee.txt").exists()
    assert result.exit_code == 0

    missing_md = root / "missing-clip.md"
    missing_md.write_text(
        "- (26-09-11) [없는 클립](https://fsc.go.kr/no010101/9)\n"
        "    <!-- source: clip|clip_1700000077_11111111 -->\n",
        encoding="utf-8",
    )
    missing_dest = tmp_path / "raw-missing"
    missing_dest.mkdir()
    missing = export_quarter(missing_md, downloads, clips, missing_dest, date(2026, 11, 5))
    assert missing.exit_code == 1
    assert not (
        missing_dest / "quality-updates-sources" / "missing-clip" / "clip_1700000077_11111111.txt"
    ).exists()
