# Audit Regulatory Lens Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Planning·Execution·Reporting(Quality review) 3단계에서 Quality Updates 코퍼스를 근거로 감사 보조 출력을 생성하는 `audit-regulatory-lens` ADVISORY 스킬을 추가한다 (MCP 없이 repo fallback v1).

**Architecture:** `.claude/skills/audit-regulatory-lens/SKILL.md`에 모드 감지·engagement brief·retrieve fallback·3모드 출력 스키마·RIGID-lite guardrail을 집약. reference/는 keywords·gold output 예시. AGENTS.md 라우팅. MCP 연동은 v1.1 절만 SKILL에 placeholder.

**Tech Stack:** Markdown skill (Cursor/Claude), repo `docs/quality-updates/`, `rg`/Read tool

**Spec:** `docs/superpowers/specs/2026-06-27-audit-regulatory-lens-skill-design.md`

---

## File map

| File | Action | Responsibility |
|------|--------|----------------|
| `.claude/skills/audit-regulatory-lens/SKILL.md` | Create | 메인 RIGID-lite 스킬 |
| `.claude/skills/audit-regulatory-lens/reference/keywords.md` | Create | assertion→검색 키워드 |
| `.claude/skills/audit-regulatory-lens/reference/output-samples.md` | Create | 3모드 출력 예시 |
| `AGENTS.md` | Modify | 라우팅 행 + writer와 분리 제약 |
| `docs/project/README.md` | Modify | SSOT 표에 감사 스킬 |
| `docs/superpowers/README.md` | Modify | plan 행 (완료 시) |

---

### Task 1: SKILL.md 골격

**Files:**
- Create: `.claude/skills/audit-regulatory-lens/SKILL.md`

- [ ] **Step 1:** Front matter

```yaml
---
name: audit-regulatory-lens
description: 감사 Planning·Execution·Reporting(품질검토 포함) 단계에서 Quality Updates 코퍼스(링크+note)를 근거로 규제 렌즈 코멘트·체크리스트를 생성. 코퍼스 읽기 전용.
---
```

- [ ] **Step 2:** ADVISORY 선언 + writer **동시 사용 금지**

- [ ] **Step 3:** Announce 템플릿 (spec §1.3)

- [ ] **Step 4:** 모드 감지 표 (PLANNING / EXECUTION / REPORTING + QR 서브)

- [ ] **Step 5:** 공통 워크플로 dot 또는 numbered list (brief → retrieve → draft → gate → footer)

- [ ] **Step 6:** Engagement brief 표 (spec §2.1)

- [ ] **Step 7:** Retrieve — MCP v1.1 절(placeholder) + repo fallback 절차 (spec §5)

- [ ] **Step 8:** Quality gate 체크리스트 (spec §2.3)

- [ ] **Step 9:** Footer 블록 (spec §2.4)

---

### Task 2: 3모드 출력 스키마 (SKILL.md 본문)

**Files:**
- Modify: `.claude/skills/audit-regulatory-lens/SKILL.md`

- [ ] **Step 1:** PLANNING — 출력 스키마 + 추가 brief + retrieve 초점 + 체크list 최소 5항 가이드 (spec §3.1)

- [ ] **Step 2:** EXECUTION — 출력 스키마 + 조서 brief **필수** 규칙 (spec §3.2)

- [ ] **Step 3:** REPORTING Part A + Part B Quality review — 각 스키마·체크list (spec §3.3)

- [ ] **Step 4:** 복수 모드 요청 시 섹션 순서: Planning → Execution → Reporting

---

### Task 3: reference/keywords.md

**Files:**
- Create: `.claude/skills/audit-regulatory-lens/reference/keywords.md`

- [ ] **Step 1:** 표 작성 (최소 12행)

| focus_area | 검색 키워드 (ko) | 기관 힌트 |
|------------|------------------|-----------|
| ICFR / 내부회계 | 내부회계, 운영실태, 자금 부정 | FSS |
| 수익인식 | 수익인식, 매출, 중점심사 | FSS |
| 전환사채 | 전환사채, CB | FSS |
| … | … | … |

- [ ] **Step 2:** SKILL.md에서 `reference/keywords.md` 링크

---

### Task 4: reference/output-samples.md

**Files:**
- Create: `.claude/skills/audit-regulatory-lens/reference/output-samples.md`

- [ ] **Step 1:** PLANNING 예시 1블록 — `2026-01-01_to_2026-03-31.md` 운영계획 note 인용 (실 URL)

- [ ] **Step 2:** EXECUTION 예시 1블록 — 가상 조서 맥락 + note 인용

- [ ] **Step 3:** REPORTING + QR 예시 각 1블록

- [ ] **Step 4:** SKILL.md gold reference로 명시

---

### Task 5: AGENTS.md · docs/project/README.md

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/project/README.md`

- [ ] **Step 1:** AGENTS.md §1 라우팅 표 추가

```markdown
| **감사 규제 렌즈 (Planning/Execution/Reporting)** | [.claude/skills/audit-regulatory-lens/SKILL.md](...) | ADVISORY; writer와 동시 사용 금지 |
```

- [ ] **Step 2:** AGENTS.md §3 제약 1줄 — audit 스킬은 `.md` 수정 금지

- [ ] **Step 3:** docs/project/README.md SSOT — 감사 규제 렌즈 스킬 경로

---

### Task 6: 검증 (HITL smoke)

- [ ] **Step 1:** Cursor 새 �ats — `@audit-regulatory-lens` 또는 스킬 트리거

**PLANNING prompt (예):**
> 2025-12-31 결산 상장 제조업. 중점 ICFR·전환사채. 감사계획 규제 렌즈.

**EXECUTION prompt (예):**
> 전환사채 TOE 조서 요약: … (1문장). execution 규제 렌즈.

**REPORTING+QR prompt (예):**
> KAM 내부회계·결론 초안 요약. reporting + quality review 규제 렌즈.

- [ ] **Step 2:** 각 출력에 **실제 note URL** 포함 여부 확인

- [ ] **Step 3:** `cd scripts && python -m pytest tests/ -q` — 기존 CI 회귀 없음 (스킬만 변경 시 통과)

- [ ] **Step 4:** `mkdocs build --strict` (선택)

---

### Task 7: superpowers README

- [x] **Step 1:** plans 테이블에 본 plan 행 추가

---

## Acceptance (from spec)

- [x] SKILL.md — 3모드 + QR + gate + fallback + MCP v1.1 placeholder
- [x] reference/ 2파일
- [x] AGENTS.md 라우팅
- [ ] HITL 3모드 smoke (Cursor 수동)

## Out of scope (v1.1 follow-up)

- ~~MCP tool 구현 (corpus spec)~~ → [2026-06-27-mcp-corpus.md](2026-06-27-mcp-corpus.md) 완료
- SKILL.md MCP 우선 retrieve 절 **활성화** (corpus 연결 후)
