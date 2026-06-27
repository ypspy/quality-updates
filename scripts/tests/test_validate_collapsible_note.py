from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate_content import validate_no_collapsible_note


def test_rejects_collapsible_note_in_quality_updates():
    lines = ['    ??? note "주요 내용"\n']
    path = Path("docs/quality-updates/2025/2025-10-01_to_2025-12-31.md")
    errors = validate_no_collapsible_note(lines, path)
    assert len(errors) == 1
    assert errors[0].code == "COLLAPSIBLE_NOTE"


def test_allows_collapsible_info():
    lines = ['    ??? info "금융감독원"\n']
    path = Path("docs/quality-updates/2025/2025-10-01_to_2025-12-31.md")
    errors = validate_no_collapsible_note(lines, path)
    assert errors == []


def test_skips_non_quality_updates():
    lines = ['??? note "quote"\n']
    path = Path("docs/fss-review/fr2022.md")
    errors = validate_no_collapsible_note(lines, path)
    assert errors == []
