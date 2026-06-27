# Admonition expand notes (`??? note` → `!!! note`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 분기 규제 업데이트 문서의 링크 요약 `??? note`를 `!!! note`로 일괄 전환하고, Appendix·중첩 `??? info`는 유지하며 작성 규칙 SSOT를 갱신한다.

**Architecture:** `expand_note_admonitions.py`로 `??? note` 줄만 idempotent 치환 → `validate_no_collapsible_note`로 회귀 방지 → writer 스킬·운영 문서 갱신 → corpus re-export.

**Tech Stack:** Python 3.8+, pytest, MkDocs Material, `quality-updates-writer` SKILL.md

**Spec:** `docs/superpowers/specs/2026-06-26-admonition-expand-notes-design.md`

---

## File map

| File | Action |
|------|--------|
| `scripts/expand_note_admonitions.py` | Create — 백필 CLI |
| `scripts/tests/test_expand_note_admonitions.py` | Create |
| `scripts/validate_content.py` | Modify — `validate_no_collapsible_note` |
| `scripts/tests/test_validate_collapsible_note.py` | Create |
| `docs/quality-updates/{year}/*.md` | Modify — 84건 `??? note` 치환 |
| `.claude/skills/quality-updates-writer/SKILL.md` | Modify — REFERENCE A |
| `docs/project/quarterly-operations-guide.md` | Modify |
| `docs/project/editor-curation-workflow.md` | Modify |
| `scripts/apply_q1_2026_summaries.py` | Modify — `folded` 제거 |
| `data/corpus/` | Regenerate — `export_corpus.py --strict` |

---

### Task 1: 백필 스크립트 + 테스트

- [x] `expand_note_admonitions.py` + `test_expand_note_admonitions.py`
- [x] `python scripts/expand_note_admonitions.py --verbose` → 84 replacements

### Task 2: validate 회귀 규칙

- [x] `validate_no_collapsible_note` + `test_validate_collapsible_note.py`

### Task 3: SSOT 문서

- [x] writer SKILL REFERENCE A·체크리스트
- [x] quarterly-operations-guide, editor-curation-workflow

### Task 4: 검증

- [x] `cd scripts && python -m pytest tests/ -q`
- [x] `python scripts/validate_content.py --strict`
- [x] `mkdocs build --strict`
- [x] `python scripts/export_corpus.py --strict`
- [x] `rg '^\s*\?\?\? note' docs/quality-updates/` → 0
