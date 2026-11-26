# HITL → 전문가 런타임 개명 — 설계 스펙

**날짜**: 2026-11-26  
**상태**: 설계 합의됨 (옵션 1 · 런타임 허브만).  
**선행**: [cursor-quarterly-routine-design](2026-11-26-cursor-quarterly-routine-design.md) — 분기 가이드는 이미 `전문가`만 사용; 전역 HITL 개명은 이 스펙.

합의:

- Intent = 런타임 허브 문서에서 `HITL` 용어를 제거하고, 역할 문구를 분기 가이드와 맞춘다.
- 범위 = **옵션 1** — `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `docs/project/editor-curation-workflow.md`, `docs/project/curation-rules.md`, `docs/project/README.md`, writer `gold-excerpts-checklist.md`(HITL 있을 때).
- 역할 SSOT = [quarterly-operations-guide.md](../../project/quarterly-operations-guide.md): Agent = 수집·**큐레이션**·요약·draft PR; **전문가 = 최종 머지 결정만**.
- Non-Goals = 역사 `docs/superpowers/specs|plans` 일괄 치환, 마커·스크립트·분기 콘텐츠, Automation, 아카이브 규격화, 「전문가적 판단」 관용구.

---

## 1. Intent & Why

`#193` 이후 분기 운영 정본은 Cursor Agent가 큐레이션까지 하고 전문가는 머지만 한다. 런타임 허브(`AGENTS.md` 등)는 아직 `HITL 주도`·`전문가(HITL)`를 써서 모순된다. HITL은 코드·pytest 식별자가 아니라 **문서 용어**뿐이므로, 허브 문구만 고치면 된다.

성공 기준:

- 범위 파일에 `HITL` 문자열이 없다.
- 역할 설명이 분기 가이드와 같다 (Agent 큐레이션 · 전문가 머지만).
- 마커 대량 무단 변경 금지는 유지하되 라벨에서 HITL을 뺀다.

---

## 2. Non-Goals

- `docs/superpowers/specs|plans` 역사 문서 일괄 `HITL`→`전문가` 치환
- `scripts/**`, CLI, env, 편집기 JS, `<!-- skip -->` / `<!-- source: … -->` 마커 동작
- `docs/quality-updates/**`, corpus, `mkdocs.yml` nav 콘텐츠
- `quarterly-operations-guide.md` 계약 문구·본문 재작성 (이미 HITL 없음)
- V-249 해제, Automation 등록, 아카이브 규격화
- 감사 관용구 「전문가적 판단」 등 비-HITL 용례 치환

---

## 3. Constraints

- 기획 → 구현: 이 스펙 승인 후 plan → 구현.
- `docs/` Markdown 변경 후 `npm run lint:md` 통과. 규칙 완화 금지.
- pytest는 HITL 문자열을 assert하지 않음. 회귀로 `cd scripts && python -m pytest tests/ -q` 실행.
- 분기 가이드·docs-contract 문구는 건드리지 않는다.

---

## 4. 파일별 변경

| 파일 | 변경 |
|------|------|
| `AGENTS.md` | 큐레이션 행: Agent 실행·마커 무단 대량 변경 금지(HITL 주도 삭제). §3·금지 목록: HITL 라벨 제거, 마커 규칙 유지 |
| `README.md` | `전문가(HITL)` → `전문가` |
| `CONTRIBUTING.md` | `Agent/HITL` → `Agent/전문가` |
| `docs/project/editor-curation-workflow.md` | `Agent/HITL` → `Agent/전문가` |
| `docs/project/curation-rules.md` | 최종 판단을 가이드와 맞춤: 정규 루틴은 Agent가 마커·draft PR, 전문가는 머지. HITL 괄호 삭제 |
| `docs/project/README.md` | Render 절 `HITL` → `전문가` |
| `.claude/skills/.../gold-excerpts-checklist.md` | Pass 조건의 HITL → 전문가(또는 동등 비-HITL 문구) |

색인: `docs/superpowers/README.md`에 이 스펙·후속 plan 행 추가.

---

## 5. Acceptance

### Happy path

1. 범위 파일에서 `rg HITL` → 매치 없음.
2. `AGENTS.md` 큐레이션 행·제약이 가이드 역할과 모순되지 않는다.
3. `npm run lint:md` exit 0; pytest 회귀 통과.

### Edge

- 역사 specs/plans에 HITL이 남아 있어도 이번 PR 실패 조건이 아니다.
- 분기 가이드 docs-contract 문자열이 깨지지 않는다.

---

## 6. Definition of Done

- [ ] 스펙·plan 색인 반영
- [ ] 범위 런타임 파일에 `HITL` 없음
- [ ] 역할 = Agent 큐레이션 · 전문가 머지만
- [ ] `npm run lint:md` · pytest 통과
- [ ] PR 오픈; 코드·마커·역사 일괄 개명 없음
