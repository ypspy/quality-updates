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
    result = export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5), repo_root=root)
    copied_pdf = dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "ifrs.pdf"
    record = dest / "quality-updates-processed" / "2026-07-01_to_2026-09-30"
    repo_record = root / "data" / "quarterly-processed" / "2026-07-01_to_2026-09-30"
    assert copied_pdf.read_bytes() == b"%PDF-1"
    assert not (dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "ifrs.hwpx").exists()
    assert not (dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "exam.pdf").exists()
    assert not (dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "appendix.pdf").exists()
    assert "매년 제출" in next(record.glob("*.md")).read_text(encoding="utf-8")
    assert next(repo_record.glob("*.md")).read_bytes() == next(record.glob("*.md")).read_bytes()
    assert result.exit_code == 0
    again = export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5), repo_root=root)
    assert again.copied == []
    assert next(repo_record.glob("*.md")).read_bytes() == next(record.glob("*.md")).read_bytes()


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
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5), repo_root=root)
    (downloads / "ifrs.pdf").write_bytes(b"%PDF-2")
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 6), repo_root=root)
    folder = dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30"
    assert (folder / "ifrs.pdf").read_bytes() == b"%PDF-1"
    assert (folder / "ifrs--2026-11-06.pdf").read_bytes() == b"%PDF-2"


HEADING_QUARTER = """---
title: q
---

### 금융감독원

#### 회계감독 동향자료

- (26-09-11) [계리가정](https://fss.or.kr/1)

    !!! note "주요 내용"

        - (보고서) 매년 제출

    !!! note "위원 논의"

        - 미공개

### 금융위원회

#### 보도자료

- (26-09-12) [다음 고시](https://fsc.go.kr/2)

    !!! note "다음 노트"

        - 다른 사실
"""


def test_record_is_stored_in_repo_root_then_copied(tmp_path: Path):
    root = tmp_path / "repo"
    md, downloads = _write_quarter(root)
    explicit = tmp_path / "explicit-root"
    dest = tmp_path / "raw"
    dest.mkdir()
    export_quarter(
        md,
        downloads,
        root / "clips",
        dest,
        date(2026, 11, 5),
        repo_root=explicit,
    )
    name = "26-09-11-계리가정.md"
    stem = "2026-07-01_to_2026-09-30"
    repo_file = explicit / "data" / "quarterly-processed" / stem / name
    vault_file = dest / "quality-updates-processed" / stem / name
    assert repo_file.read_bytes() == vault_file.read_bytes()
    assert "매년 제출" in repo_file.read_text(encoding="utf-8")
    assert not (root / "data").exists()


def test_changed_site_note_does_not_rebuild_existing_record(tmp_path: Path):
    root = tmp_path / "repo"
    md, downloads = _write_quarter(root)
    dest = tmp_path / "raw"
    dest.mkdir()
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5), repo_root=root)
    md.write_text(QUARTER.replace("매년 제출", "매년 개정"), encoding="utf-8")
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 6), repo_root=root)
    name = "26-09-11-계리가정.md"
    stem = "2026-07-01_to_2026-09-30"
    repo_file = root / "data" / "quarterly-processed" / stem / name
    vault_file = dest / "quality-updates-processed" / stem / name
    assert "매년 제출" in repo_file.read_text(encoding="utf-8")
    assert "매년 개정" not in repo_file.read_text(encoding="utf-8")
    assert vault_file.read_bytes() == repo_file.read_bytes()
    assert not (vault_file.parent / "26-09-11-계리가정--2026-11-06.md").exists()


def test_existing_record_with_extra_line_is_copied_unchanged(tmp_path: Path):
    root = tmp_path / "repo"
    md, downloads = _write_quarter(root)
    stem = "2026-07-01_to_2026-09-30"
    name = "26-09-11-계리가정.md"
    repo_file = root / "data" / "quarterly-processed" / stem / name
    repo_file.parent.mkdir(parents=True)
    original = (
        "- (26-09-11) [계리가정](https://fsc.go.kr/no010101/1)\n"
        "preserved extra line\n"
    ).encode("utf-8")
    repo_file.write_bytes(original)
    dest = tmp_path / "raw"
    dest.mkdir()
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5), repo_root=root)
    vault_file = dest / "quality-updates-processed" / stem / name
    assert repo_file.read_bytes() == original
    assert vault_file.read_bytes() == original


def test_heading_after_note_is_not_stored_in_the_record(tmp_path: Path):
    root = tmp_path / "repo"
    downloads = root / "downloads"
    downloads.mkdir(parents=True)
    explicit = tmp_path / "explicit-root"
    md = root / "2026-07-01_to_2026-09-30.md"
    md.write_text(HEADING_QUARTER, encoding="utf-8")
    dest = tmp_path / "raw"
    dest.mkdir()
    export_quarter(
        md,
        downloads,
        root / "clips",
        dest,
        date(2026, 11, 5),
        repo_root=explicit,
    )
    stem = "2026-07-01_to_2026-09-30"
    repo_file = explicit / "data" / "quarterly-processed" / stem / "26-09-11-계리가정.md"
    vault_file = dest / "quality-updates-processed" / stem / "26-09-11-계리가정.md"
    text = repo_file.read_text(encoding="utf-8")
    assert text == vault_file.read_text(encoding="utf-8")
    assert '!!! note "주요 내용"' in text
    assert '!!! note "위원 논의"' in text
    assert "미공개" in text
    assert "### 금융위원회" not in text
    assert "#### 보도자료" not in text
    nxt = (explicit / "data" / "quarterly-processed" / stem / "26-09-12-다음 고시.md").read_text(
        encoding="utf-8"
    )
    assert "다음 노트" in nxt
    assert "위원 논의" not in nxt


def test_existing_snapshot_skips_only_when_bytes_match(tmp_path: Path):
    root = tmp_path / "repo"
    md, downloads = _write_quarter(root)
    dest = tmp_path / "raw"
    dest.mkdir()
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5), repo_root=root)
    folder = dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30"
    (downloads / "ifrs.pdf").write_bytes(b"%PDF-2")
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 6), repo_root=root)
    snapshot = folder / "ifrs--2026-11-06.pdf"
    assert snapshot.read_bytes() == b"%PDF-2"

    (downloads / "ifrs.pdf").write_bytes(b"%PDF-3")
    blocked = export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 6), repo_root=root)
    assert blocked.exit_code == 1
    assert str(snapshot) in blocked.conflicts
    assert str(snapshot) not in blocked.skipped
    assert snapshot.read_bytes() == b"%PDF-2"

    (downloads / "ifrs.pdf").write_bytes(b"%PDF-2")
    same = export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 6), repo_root=root)
    assert same.exit_code == 0
    assert str(snapshot) in same.skipped
    assert str(snapshot) not in same.conflicts


def test_default_repo_root_is_parent_of_scripts():
    from quarterly_handoff import _default_repo_root

    root = _default_repo_root()
    assert root == Path(__file__).resolve().parents[2]
    assert (root / "scripts" / "quarterly_handoff.py").is_file()


def test_omitted_repo_root_is_not_the_markdown_parent(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    md, downloads = _write_quarter(root)
    sentinel = tmp_path / "script-location-root"
    monkeypatch.setattr("quarterly_handoff._default_repo_root", lambda: sentinel)
    dest = tmp_path / "raw"
    dest.mkdir()
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5))
    stem = "2026-07-01_to_2026-09-30"
    saved = sentinel / "data" / "quarterly-processed" / stem / "26-09-11-계리가정.md"
    assert saved.is_file()
    assert not (root / "data").exists()


def test_missing_vault_root_copies_nothing(tmp_path: Path):
    root = tmp_path / "repo"
    md, downloads = _write_quarter(root)
    missing = tmp_path / "no-such-vault" / "raw"
    result = export_quarter(md, downloads, root / "clips", missing, date(2026, 11, 5), repo_root=root)
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
    result = export_quarter(md, downloads, clips, dest, date(2026, 11, 5), repo_root=root)
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
    missing = export_quarter(missing_md, downloads, clips, missing_dest, date(2026, 11, 5), repo_root=root)
    assert missing.exit_code == 1
    assert not (
        missing_dest / "quality-updates-sources" / "missing-clip" / "clip_1700000077_11111111.txt"
    ).exists()
