# Expert Rename (Runtime Hub) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `HITL` from runtime hub docs and align role wording with the Cursor quarterly guide (Agent curates; expert merges only).

**Architecture:** Docs-only string/role updates in the files listed by the spec. No code, markers, or historical superpowers bulk rewrite.

**Tech Stack:** Markdown, markdownlint-cli, pytest (regression).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-26-expert-rename-design.md`
- Do not edit `docs/project/quarterly-operations-guide.md`
- Do not bulk-rename `docs/superpowers/specs|plans` history
- Do not change markers or `scripts/**`
- After docs edits: `npm run lint:md` must pass

---

### Task 1: Runtime hub prose

**Files:**

- Modify: `AGENTS.md`, `README.md`, `CONTRIBUTING.md`
- Modify: `docs/project/editor-curation-workflow.md`, `docs/project/curation-rules.md`, `docs/project/README.md`
- Modify: `.claude/skills/quality-updates-writer/reference/gold-excerpts-checklist.md`
- Modify: `docs/superpowers/README.md` (plans index row)

- [ ] **Step 1: Apply replacements**

`AGENTS.md`:

- Routing row 큐레이션·편집기: `HITL 주도; Agent는 마커 임의 변경 금지` → `정규 루틴은 Agent 큐레이션; 마커 무단 대량 변경 금지`
- §3: `**HITL 큐레이션**:` → `**큐레이션 마커**:` (same rule body)
- §7: `HITL 마커 대량 변경` → `큐레이션 마커 대량 변경`

`README.md`: `전문가(HITL)` → `전문가`

`CONTRIBUTING.md`: `Agent/HITL 역할` → `Agent/전문가 역할`

`editor-curation-workflow.md`: `Agent/HITL 역할` → `Agent/전문가 역할`

`curation-rules.md` line 6: replace with guide-aligned sentence:

`이 문서는 편집기를 대체하지 않는다. 스크립트는 파일을 수정하지 않는다. 정규 분기 루틴에서는 Agent가 스킵·출처 마커를 반영하고 draft PR을 열며, 전문가는 최종 머지 결정만 한다. 편집기 수동 경로에서도 같은 마커 규칙을 쓴다.`

`docs/project/README.md`: `HITL이 Render` → `전문가가 Render`

`gold-excerpts-checklist.md`: `HITL이 명시한 Minor` → `전문가가 명시한 Minor`

- [ ] **Step 2: Verify no HITL in scope files**

```bash
rg -n "HITL" AGENTS.md README.md CONTRIBUTING.md \
  docs/project/editor-curation-workflow.md docs/project/curation-rules.md \
  docs/project/README.md \
  .claude/skills/quality-updates-writer/reference/gold-excerpts-checklist.md \
  && exit 1 || true
```

- [ ] **Step 3: Index plan + lint + commit**

Add plans table row for this file. Then:

```bash
npm run lint:md
cd scripts && python -m pytest tests/ -q
```

Commit runtime + plan together or as two commits (spec already committed).

---

### Task 2: PR

- [ ] Push `cursor/expert-rename-afeb` and open PR via ManagePullRequest
- [ ] DoD: scope HITL-free, roles aligned, lint+pytest green
