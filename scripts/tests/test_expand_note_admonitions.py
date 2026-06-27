from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from expand_note_admonitions import expand_notes_in_text


def test_expands_note_only():
    text = """- (25-01-01) [제목](https://example.com)

    ??? note "주요 내용"

        - bullet

    ??? info "2025년 상반기 회계심사·감리 주요 지적사례 공개 목록"

        1. item
"""
    updated, count = expand_notes_in_text(text)
    assert count == 1
    assert '!!! note "주요 내용"' in updated
    assert '??? info "2025년 상반기' in updated
    assert "??? note" not in updated


def test_idempotent():
    text = '    ??? note "조사·감리결과 지적사항 및 조치내역"\n'
    once, n1 = expand_notes_in_text(text)
    twice, n2 = expand_notes_in_text(once)
    assert n1 == 1
    assert n2 == 0
    assert once == twice


def test_preserves_indent():
    text = '        ??? note "주요 내용"\n'
    updated, count = expand_notes_in_text(text)
    assert count == 1
    assert updated == '        !!! note "주요 내용"\n'
