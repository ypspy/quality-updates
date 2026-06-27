# MCP Corpus Implementation Plan

> **Status**: Implemented 2026-06-27 (tests pass: pytest 172, validate --strict, mkdocs --strict, export_corpus --strict)

**Goal:** Export-first JSONL corpus + local stdio MCP + Hosted HTTP MCP (shared core).

**Spec:** [2026-06-27-mcp-corpus-design.md](../specs/2026-06-27-mcp-corpus-design.md)

## Completed

- [x] P1 `scripts/corpus/` + `export_corpus.py` + `data/corpus/`
- [x] P2 `scripts/mcp_server/core.py` + `app.py` + `stdio.py` + tests
- [x] P3 `scripts/mcp_server/http.py` (Bearer `MCP_API_KEY`)
- [x] P4 CI validate job + README/AGENTS/docs/project SSOT

## HITL (optional)

- [ ] Cursor `.cursor/mcp.json` smoke
- [ ] Render 2nd Web Service + Hosted smoke

## Follow-up (v1.1)

- [ ] `audit-regulatory-lens` SKILL — MCP 우선 retrieve 활성화
