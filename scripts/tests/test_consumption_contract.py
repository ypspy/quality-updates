# -*- coding: utf-8 -*-
"""Runtime consumption contract: no lens skill; MCP citation rules."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LENS_DIR = REPO_ROOT / ".claude" / "skills" / "audit-regulatory-lens"
RUNTIME_DOCS = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "project" / "README.md",
    REPO_ROOT / "docs" / "project" / "quarterly-operations-guide.md",
)
LENS_PATH_NEEDLE = ".claude/skills/audit-regulatory-lens"


def test_lens_skill_directory_removed():
    assert not LENS_DIR.exists()


def test_runtime_docs_do_not_route_to_lens():
    for path in RUNTIME_DOCS:
        text = path.read_text(encoding="utf-8")
        assert LENS_PATH_NEEDLE not in text, path


def test_readme_has_citation_contract_and_hosted_attach():
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "no_summary" in text
    assert "MCP_API_KEY" in text
    assert "/health" in text
    assert "search_regulatory_updates" in text
    assert "get_regulatory_update" in text


def test_quarterly_ops_export_corpus_strict():
    text = (
        REPO_ROOT / "docs" / "project" / "quarterly-operations-guide.md"
    ).read_text(encoding="utf-8")
    assert "export_corpus.py --strict" in text


def test_fastmcp_citation_instructions():
    import sys

    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from mcp_server.app import CITATION_INSTRUCTIONS

    lower = CITATION_INSTRUCTIONS.lower()
    assert "read-only" in lower
    assert "no_summary" in CITATION_INSTRUCTIONS
    assert "do not invent" in lower
    assert "search_regulatory_updates" in CITATION_INSTRUCTIONS
