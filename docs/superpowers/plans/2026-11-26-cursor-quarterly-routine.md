# Cursor Quarterly Routine Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `docs/project/quarterly-operations-guide.md` as the Cursor-only quarterly routine (lanes A–E, Agent executes including curation, expert merges only) and add Automation apply-notes without enabling Automation.

**Architecture:** Replace the long Grok/HITL-centric guide body with a short Cursor execution SSOT: roles → routine checklist → timing → gates → commands → Automation (docs only) → archive As-Is table → links. Cross-link format details; do not copy sanction/writer prose. Touch AGENTS/project README only for routing lines required by the spec.

**Tech Stack:** Markdown, markdownlint-cli (`npm run lint:md`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-26-cursor-quarterly-routine-design.md`
- SSOT file remains `docs/project/quarterly-operations-guide.md` (no new checklist file).
- New guide body uses **전문가** (not HITL). Do **not** globally rename HITL across the repo (separate spec).
- Agent = collect, curate, summarize, nav draft, prepare_deploy, draft PR. Expert = merge decision only before deploy.
- Lanes A–E on routine day for **public-by-then** intake; D prior-quarter unpublished backfill on next routine (`1d′`).
- Cumulative archive + key skip (§5.4 As-Is only). Archive formalization = follow-up brainstorming.
- Do **not** register/enable Cursor Automation; document apply method only.
- Do **not** change crawlers, editor code, CI, paid APIs, Render, backfill content, or enable `kasb_meetings --live` without existing approval rules.
- After `docs/` edits: `npm run lint:md` must pass. Do not weaken `.markdownlint.json`.

---

### Task 1: Rewrite quarterly-operations-guide.md

**Files:**

- Modify: `docs/project/quarterly-operations-guide.md` (full rewrite of body; keep filename)
- Test: search + `npm run lint:md` (no pytest)

**Interfaces:**

- Consumes: Spec §§4–6 checklist tables and §5.4 archive table
- Produces: Cursor-only ops SSOT linked from AGENTS / project README

- [ ] **Step 1: Confirm baseline**

```bash
cd /agent/repos/quality-updates
git checkout cursor/cursor-quarterly-routine-afeb
wc -l docs/project/quarterly-operations-guide.md
rg -n "^## " docs/project/quarterly-operations-guide.md
```

Expected: long legacy file (~400+ lines) with Phase 1–5 / HITL-heavy sections.

- [ ] **Step 2: Overwrite the guide with the complete body below**

Write the **entire** file `docs/project/quarterly-operations-guide.md` as exactly this content (preserve trailing newline; do not add HITL):

````markdown
# 분기 운영 작업지시서

**대상**: Quality Updates 정규 분기 운영 (Cursor 유일 실행안)
**버전**: 2026-11
**관련 문서**: [README.md](../../README.md), [CONTRIBUTING.md](../../CONTRIBUTING.md),
[editor-curation-workflow.md](editor-curation-workflow.md),
[quality-updates-writer 스킬](../../.claude/skills/quality-updates-writer/SKILL.md),
[sanctions-format.md](../../docs-dev/sanctions-format.md),
[kasb-meetings-collector.md](kasb-meetings-collector.md),
스펙 [cursor-quarterly-routine-design](../superpowers/specs/2026-11-26-cursor-quarterly-routine-design.md)

---

## 1. 목적

금융당국(FSS, FSC, KICPA, KASB) 보도·공지·질의회신·제재·회의록 공개분을 분기 단위로 입수·선별·요약한 뒤 공개 사이트에 반영한다.

본 문서는 **Cursor Agent가 실행**하고 **전문가가 최종 머지만 승인**하는 정규 분기 루틴의 정본이다. 그록봇(`qu` 등) 자동 루틴은 중지되어 있다.

---

## 2. 역할

| 역할 | 담당 | 책임 |
|------|------|------|
| **Agent** | Cursor | 수집·**큐레이션**·요약·nav 초안·배포 전처리·**draft PR** |
| **전문가** | 사용자 | **최종 배포 전 `main` 머지 결정만** |
| **시스템** | 스크립트·CI | 게이트 (validate, lint_public_body, pytest, mkdocs, lint:md, corpus) |

**원칙**

- Agent는 원문에서 확인된 내용만 요약한다 (스킬 RIGID). 추정·보완 금지.
- 전문가에게 단계별 큐레이션·요약 사실 검증을 필수 칸으로 두지 않는다. 필수 칸은 **머지 결정**뿐이다.
- 파이프라인은 볼트에 직접 쓰지 않는다.
- 제재·요약·회의록·편집기 마커 **형식**은 이 가이드에 장문으로 두지 않는다. 위 관련 문서·스킬을 본다.

---

## 3. 정규 분기 루틴 — Cursor

시점: **분기 다음 달 5일 09:00 KST 이후**. 그 전 `crawl.py`는 해당 분기를 종료 코드 2로 거절한다. nav/index 최신 링크도 그 전 금지. 예외는 `data/qu-early-allow.txt` 표준 경로만.

### 3.1 당일 체크리스트

각 행: 단계 · 레인 · 담당 · 핵심 · 완료 신호.

| # | 단계 | 레인 | 담당 | 핵심 | 완료 신호 |
|---|------|------|------|------|-----------|
| 0 | 시점·대상 분기 | A | Agent | 달력으로 `--year`/`--quarter` 확정 | 대상 분기 확정 |
| 1 | 보도·공지 수집 | A | Agent | `crawl.py --dry-run` 권장 후 `--year/--quarter` | 표준 경로 md |
| 1b | 금감원 질의회신 | B | Agent | `crawl_fss_replies.py --limit 1` → 전량 | `data/fss-replies/` |
| 1c | 회계기준원 질의회신 | C | Agent | `crawl_kasb_replies.py` (증분·실패 재시도는 기존 CLI) | `data/kasb-replies/` |
| 1d | 제재 안건·의사록 (공개분) | D | Agent | 당일까지 공개된 금융위·증선위 안건·의결서·의사록 입수·연결 (`downloads/sanctions`, `attach_sanction_minutes` 등). **미공개 의사록은 당일 강제하지 않음** | 회차 폴더·분기 md 반영 |
| 1d′ | 직전 분기 D 미공개분 보완 | D | Agent | **이번 루틴에서** 직전 분기 문서의 미공개였던 의사록·안건을 재조회해 보완 | 직전 분기 md/첨부 갱신 |
| 1e | 회의록 (공개분) | E | Agent | 당일까지 공개된 회계기준위·자문위 등 회의록 입수 (`kasb_meetings` 등). 상세는 [kasb-meetings-collector.md](kasb-meetings-collector.md) | 수집물·draft PR |
| 2 | 큐레이션 | A | Agent | 스킵·출처. 전문가 필수 아님 | 마커 반영 |
| 3 | 요약 | A | Agent | `quality-updates-writer` SUMMARIZE (당일 반영된 D·E 공개분 포함) | note 블록 |
| 4 | nav/index | A | Agent | 갱신일 이후 초안, 자동 머지 없음 | draft PR에 포함 |
| 5 | 배포 전처리 | A | Agent | `prepare_deploy`, `export_corpus --strict`, 게이트 | CI + corpus · **draft PR** |
| 5b | 머지·배포 | — | 전문가 | **최종 배포 전 PR 머지 결정만** | Render |

루틴 표 밖(한 줄·링크만): Whale, 볼트 raw export, B0000291 **주간**.

### 3.2 D·E 타이밍

- **D:** 당일 = 그 시점까지 공개된 제재 자료 입수. 늦게 공개되는 의사록 등은 **다음 분기 루틴의 1d′**에서 직전 분기를 보완한다.
- **E:** 당일까지 **공개분**만 입수. 미공개분은 이후 루틴에서 같은 방식으로 이어서 받는다.
- E 실수집(`kasb_meetings --live`)은 기존 승인 원칙을 따른다. 가이드는 칸·명령·링크로만 둔다.

### 3.3 과거분·누적 아카이브

분기마다 “그 분기 DB”를 새로 만들지 않는다. 1b–1e는 **누적 저장소에 키가 있으면 skip**, 없으면(또는 실패 재시도면) 추가한다.

| 레인 | 누적 위치 | git | skip/증분 |
|------|-----------|-----|-----------|
| B | `data/fss-replies/{board}/{nttId}/` + `manifest.jsonl` | `item.md`·manifest만. 첨부 HWP 등은 ignore | 완료 건 skipped |
| C | `data/kasb-replies/{seq}/` | item·첨부 커밋 | 있으면 재수집 안 함 |
| D | `downloads/sanctions/{회차}/` | `downloads/` ignore. 사이트는 `docs/quality-updates/` | 회차 폴더·연결 상태 누적; 미공개→다음 분기 보완 |
| E | `downloads/kasb-meetings/…` + `_state.json` | `downloads/` ignore | 끝난 seq 재수집 안 함 |

공개 노출은 아카이브 전체가 아니라 분기 md·corpus 쪽이다. 볼트 `export_*_raw`는 복사본이다.

**후속 (별도 brainstorming):** 레인 간 스키마·보관·gitignore·볼트·`downloads` 이관 규칙을 하나의 아카이브 규격으로 고정하는 작업. 이번 가이드 재작성은 위 As-Is를 **한 표로 적는 것**까지다.

---

## 4. 시점·경로 규칙

- 표준 경로: `docs/quality-updates/YYYY/YYYY-MM-DD_to_YYYY-MM-DD.md`
- `crawl.py`는 `--year`와 `--quarter`를 명시한다. 갱신일 전 해당 분기는 exit 2.
- 조기 예외: `data/qu-early-allow.txt`에 표준 경로를 적은 경우만 (윤석님 명시 승인).
- 본문 dated list는 과거→현재. Appendix A는 크롤 수집 순(최신→과거) 유지.
- 기존 큐레이션본이 있으면 crawl이 덮지 않는다.

---

## 5. 품질 게이트

| # | 게이트 | 비고 |
|---|--------|------|
| G1 | draft PR (Agent) | 자동 머지 없음 |
| G2 | `python scripts/validate_content.py --strict` | |
| G3 | `python scripts/lint_public_body.py` | |
| G4 | `cd scripts && python -m pytest tests/ -q` | |
| G5 | `mkdocs build --strict` | |
| G6 | `npm run lint:md` | `docs/` 변경 시 |
| G7 | `python scripts/export_corpus.py --strict` | corpus diff를 PR에 포함 |
| G8 | 전문가 머지 승인 → Render | 필수 칸 = 머지 결정만 |

Python 문서·로컬: 3.11–3.12. CI: 3.11.

---

## 6. 명령 빠른 참조

```bash
# A — 보도·공지
python scripts/crawl.py --year YYYY --quarter N
python scripts/editor.py
# 또는 제안만: python scripts/auto_curate.py …
# 요약: quality-updates-writer 스킬 SUMMARIZE
python scripts/prepare_deploy.py
python scripts/export_corpus.py --strict

# B — 금감원 질의회신
python scripts/crawl_fss_replies.py --limit 1
python scripts/crawl_fss_replies.py

# C — 회계기준원 질의회신
python scripts/crawl_kasb_replies.py

# D — 제재 안건·의사록 (공개분)
python scripts/attach_sanction_minutes.py <분기.md>
# 형식: docs-dev/sanctions-format.md

# E — 회의록 (공개분; 실수집은 기존 승인)
cd scripts && python -m crawler.kasb_meetings --dry-run --limit 3
# 승인 후: --live --limit N
```

형식·마커 상세: [quality-updates-writer](../../.claude/skills/quality-updates-writer/SKILL.md),
[editor-curation-workflow.md](editor-curation-workflow.md),
[sanctions-format.md](../../docs-dev/sanctions-format.md),
[kasb-meetings-collector.md](kasb-meetings-collector.md).

---

## 7. Automation 적용 방법 (미등록)

이 절은 **적용 방법만** 적는다. 이 작업(또는 구현 PR)에서 Automation을 **생성·활성화하지 않는다**.

| 항목 | 내용 |
|------|------|
| 수단 | Cursor Automation (또는 동등 예약 Cloud Agent) |
| 트리거 | 분기 다음 달 5일 09:00 KST **이후** (첫 대상 예: 2027-01-05) |
| 프롬프트 정본 | 이 가이드의 「정규 분기 루틴 — Cursor」 체크리스트 (A–E 당일 공개분 + D 직전 미공개 보완) |
| 산출 | **draft PR만** (당일 공개분·큐레이션·요약·nav·게이트; D 1d′ 보완 포함 가능). 커밋·PR 본문에 레인·단계·검증 결과 |
| 금지 | 머지, force-push, 비밀값, 볼트 직접 쓰기, early-allow 없는 조기 nav |
| 전문가 | Automation이 연 draft PR에 대해 **머지 여부만** 결정 |
| 활성화 조건 | V-249 및 「새 클라우드 에이전트 중지」해제 + 사용자 명시 승인 후 |

---

## 8. 관련 문서·개정 이력

| 문서·경로 | 용도 |
|-----------|------|
| [AGENTS.md](../../AGENTS.md) | Agent 허브·분기 라우팅 |
| [editor-curation-workflow.md](editor-curation-workflow.md) | 마커·skip·prepare_deploy |
| [curation-rules.md](curation-rules.md) | 큐레이션 규칙 제안 |
| `scripts/crawl.py` 등 | 레인 A–E 수집 CLI |
| [pipeline-contract-sync](../superpowers/specs/2026-11-26-pipeline-contract-sync-design.md) | 게이트·exit·Python 계약 |

| 날짜 | 변경 |
|------|------|
| 2026-11-26 | Cursor 유일 실행안으로 재작성 (스펙 cursor-quarterly-routine). 과거 그록 운영·Phase 장문 삭제. Automation은 적용 방법만 |
````

- [ ] **Step 3: Strip banned content**

```bash
rg -n "HITL|그록봇 실행|캐비지|케일|Vegetable|Mr\." docs/project/quarterly-operations-guide.md && exit 1 || true
rg -n "정규 분기 루틴 — Cursor|1d′|누적 아카이브|Automation 적용" docs/project/quarterly-operations-guide.md
```

Expected: no `HITL` in the new guide; required headings/phrases present. Brief “그록봇 … 중지” is OK.

- [ ] **Step 4: Lint**

```bash
npm run lint:md
```

Expected: exit 0. Fix reported lines without disabling rules. Do not bulk-strip trailing spaces that are Markdown hard breaks.

- [ ] **Step 5: Commit**

```bash
git add docs/project/quarterly-operations-guide.md
git commit -m "$(cat <<'EOF'
docs: rewrite quarterly ops guide as Cursor-only routine

Replace Grok/HITL-era Phase essays with A–E checklist,
Agent curation, expert merge-only, and Automation notes.
EOF
)"
```

---

### Task 2: Cross-links (AGENTS + project README + superpowers index)

**Files:**

- Modify: `AGENTS.md` (routing row + template D quarterly block only — not global HITL purge)
- Modify: `docs/project/README.md` (SSOT blurb for the guide)
- Modify: `docs/superpowers/README.md` (plans index row)

**Interfaces:**

- Consumes: Task 1 guide heading `## 3. 정규 분기 루틴 — Cursor`
- Produces: discoverable links; quarterly prompt matches Agent-curate / expert-merge

- [ ] **Step 1: AGENTS routing table**

In `AGENTS.md`, change the **분기 파이프라인 전체** row workflow cell to:

`가이드 「정규 분기 루틴 — Cursor」 — Agent 실행(큐레이션 포함)·draft PR → 전문가 머지`

Keep the **큐레이션·편집기** row as-is (global HITL rename is out of scope).

- [ ] **Step 2: AGENTS template D**

In `### D. 분기 운영`, replace Agent/HITL responsibility lines with:

```markdown
Agent 담당: crawl·질의회신·제재/회의록 공개분 입수·큐레이션·요약·nav 초안·prepare_deploy·draft PR
전문가 담당: 최종 배포 전 main 머지 승인만
```

Do not rewrite unrelated HITL bullets in §3 constraints.

- [ ] **Step 3: docs/project/README.md**

Update the quarterly-operations-guide row summary to:

`**분기 파이프라인** — Cursor 유일 루틴(A–E), Agent 실행·전문가 머지, 품질 게이트`

- [ ] **Step 4: superpowers README plans**

Insert at the top of the Plans table (after header):

`| 2026-11-26 | [cursor-quarterly-routine.md](plans/2026-11-26-cursor-quarterly-routine.md) | Cursor 유일 분기 루틴으로 운영 가이드 재작성 |`

- [ ] **Step 5: Lint + commit**

```bash
npm run lint:md
git add AGENTS.md docs/project/README.md docs/superpowers/README.md docs/superpowers/plans/2026-11-26-cursor-quarterly-routine.md
git commit -m "$(cat <<'EOF'
docs: link Cursor quarterly routine from AGENTS and indexes

Point quarterly routing at the rewritten guide checklist;
add plan index entry.
EOF
)"
```

If the plan file was already committed earlier, omit it from this `git add` or include only if still dirty.

---

### Task 3: DoD verification + PR update

**Files:**

- None required unless lint fixes

**Interfaces:**

- Consumes: Tasks 1–2
- Produces: PR evidence for #193

- [ ] **Step 1: Content DoD searches**

```bash
rg -n "정규 분기 루틴 — Cursor|1d′|누적 아카이브|Automation 적용" docs/project/quarterly-operations-guide.md
rg -n "HITL" docs/project/quarterly-operations-guide.md && exit 1 || true
rg -n "전문가|머지 결정만" docs/project/quarterly-operations-guide.md
test ! -f docs/project/quarterly-routine-checklist.md
```

Expected: routine heading + 1d′ + archive + Automation present; **no HITL** in the guide; no separate checklist file.

- [ ] **Step 2: Full md lint**

```bash
npm run lint:md
```

Expected: exit 0.

- [ ] **Step 3: Push and refresh PR #193**

```bash
git push -u origin cursor/cursor-quarterly-routine-afeb
```

Update PR body via ManagePullRequest: preserve any human edits; note guide rewritten per spec; Automation not registered; archive formalization deferred; HITL global rename deferred.

- [ ] **Step 4: Checklist**

- [ ] Spec Intent/Non-Goals met
- [ ] Guide is Cursor-only; legacy Grok essays gone
- [ ] A–E + D backfill + §5.4 archive table present
- [ ] Expert = merge only; Agent curates
- [ ] Automation docs only
- [ ] `npm run lint:md` green

---

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| Rewrite guide Cursor-only | Task 1 |
| Checklist A–E, 1d′, roles | Task 1 |
| Archive As-Is §5.4 | Task 1 |
| Automation apply docs only | Task 1 |
| AGENTS one-line / quarterly prompt | Task 2 |
| project README / plans index | Task 2 |
| lint:md + DoD | Task 3 |
| No Automation enable, no archive formalization, no global HITL rename | Global Constraints |
