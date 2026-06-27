from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_content import validate_no_phase2


def test_rejects_executive_summary_header():
    lines = ["---", "title: x", "---", "", "## Executive Summary", "text"]
    errs = validate_no_phase2(lines, Path("docs/quality-updates/2025/x.md"))
    assert any(e.code == "PHASE2_ES" for e in errs)


def test_allows_note_sisajeom_prefix():
    lines = ["---", "title: x", "---", "", "        - (시사점) 원문 사실"]
    errs = validate_no_phase2(lines, Path("docs/quality-updates/2025/x.md"))
    assert not any(e.code == "PHASE2_IMPL" for e in errs)


def test_skips_index_md():
    lines = ["## Executive Summary"]
    errs = validate_no_phase2(lines, Path("docs/quality-updates/index.md"))
    assert errs == []
