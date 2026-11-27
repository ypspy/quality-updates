# Summary Format DoD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `docs-dev/summary-formats/` family DoD docs (Q3 note types only), add Pass/Fail to `sanctions-format.md`, and align `gold-excerpts` + writer SKILL to 2026 Q3 without raising SUMMARIZE fixed cost above Excerpt-only.

**Architecture:** Family files under `docs-dev/summary-formats/` hold structure rules + Pass/Fail; `gold-excerpts.md` holds verbatim Q3 note blocks (session gold); SKILL/project README only link. Do not require reading the full Q3 md in SUMMARIZE sessions.

**Tech Stack:** Markdown docs; existing `quality-updates-writer` skill; `npm run lint:md` for `docs/**/*.md`.

**Spec:** [2026-11-27-summary-format-dod-design.md](../specs/2026-11-27-summary-format-dod-design.md)

## Global Constraints

- Gold form target = `docs/quality-updates/2026/2026-07-01_to_2026-09-30.md` (Q3 notes only; no `<!-- no_summary -->` DoD).
- **Economics ceiling:** SUMMARIZE stays Excerpt-only. Do **not** make Q3 full-file (or Q3 body-only) a mandatory session Read. Session fixed load ≈ SKILL + `gold-excerpts` (+ `sanctions-format` on-demand for 제재). Measured order: excerpts ~5k tok÷4 vs Q3 full ~57k tok÷4.
- Do not edit `docs/quality-updates/**` body, Appendix, or curation markers.
- Do not expand `lint_public_body.py` / `validate_content.py` in this plan.
- `sanctions-format.md` §1–§6 stay; append Pass/Fail only; do not move the file.
- Secrets: none. Commits on feature branch; user merges.
- AGENTS.md one-line cross-link: **ask user in PR/chat before editing** (spec §7.4).

## File map

| Path | Role |
|------|------|
| `docs-dev/summary-formats/README.md` | Agency×section → family map; review how-to; common 3 axes |
| `docs-dev/summary-formats/general-note.md` | style-A/B DoD |
| `docs-dev/summary-formats/legislative.md` | 세칙·입법예고 DoD |
| `docs-dev/summary-formats/trend-briefing.md` | 동향자료 multi-source DoD |
| `docs-dev/summary-formats/kasb-schedule.md` | □ 의결/보고 DoD |
| `docs-dev/sanctions-format.md` | Existing rules + new §7 Pass/Fail |
| `.claude/skills/quality-updates-writer/reference/gold-excerpts.md` | Q3 verbatim excerpts |
| `.../gold-excerpts-checklist.md` | covers + DoD pointer |
| `.claude/skills/quality-updates-writer/SKILL.md` | Q3-first optional gold path; DoD SSOT link |
| `docs/project/README.md` | SSOT table row |
| `docs/superpowers/README.md` | Spec/plan index rows |

---

### Task 1: summary-formats README + four family docs

**Files:**

- Create: `docs-dev/summary-formats/README.md`
- Create: `docs-dev/summary-formats/general-note.md`
- Create: `docs-dev/summary-formats/legislative.md`
- Create: `docs-dev/summary-formats/trend-briefing.md`
- Create: `docs-dev/summary-formats/kasb-schedule.md`

**Interfaces:**

- Consumes: Spec §4–§6; Q3 path `docs/quality-updates/2026/2026-07-01_to_2026-09-30.md`

- Produces: Family docs with sections 목적·범위 / 필수 구조 / 모범 앵커 / DoD Pass·Fail / 비범위; README mapping table

- [ ] **Step 1: Create `README.md`**

Include:

1. Purpose: writing + review DoD for Q3-shaped notes; MkDocs-unpublished (`docs-dev/`).
2. Economics note: agents use `gold-excerpts` in SUMMARIZE; these files are rules/review — not a substitute for loading the full Q3 md every session.
3. Mapping table (every Q3 section that has notes):

| 기관 | 절 | Family | DoD |
|------|-----|--------|-----|
| 금융감독원 | 보도자료 | general-note | [general-note.md](general-note.md) |
| 금융감독원 | 세칙제ㆍ개정예고 | legislative | [legislative.md](legislative.md) |
| 금융감독원 | 회계감독 동향자료 | trend-briefing | [trend-briefing.md](trend-briefing.md) |
| 금융위원회 | 보도자료 | general-note | [general-note.md](general-note.md) |
| 금융위원회 | 제재 의결 | sanctions | [../sanctions-format.md](../sanctions-format.md) |
| 금융위원회 | 고시/공고/훈령 | general-note | [general-note.md](general-note.md) |
| 금융위원회 | 입법예고/규정변경예고 | legislative | [legislative.md](legislative.md) |
| 한국공인회계사회 | 알림마당 - 공지사항 | general-note | [general-note.md](general-note.md) |
| 한국공인회계사회 | 회계감사 - 감사인증기준 | general-note | [general-note.md](general-note.md) |
| 한국회계기준원 | 소통광장 - 공지사항 | general-note | [general-note.md](general-note.md) |
| 한국회계기준원 | 주요일정 | kasb-schedule | [kasb-schedule.md](kasb-schedule.md) |

4. Common 3 axes (Format / Facts / Tone-detail) from spec §5.1.
5. Review usage: map link → open family DoD only; independent review sessions do not push/comment (AGENTS §6.3).

- [ ] **Step 2: Write `general-note.md`**

- 목적: FSS/FSC 보도·고시, KICPA 알림·감사인증기준, KASB 공지.
- 필수 구조: `!!! note "주요 내용"`; indent 4+4; style-A `(접두)` XOR style-B `**주제**:`; bullets 3–7 (short 2–3 / long 8–9 OK); 명사형 어미; bold on key terms only; no A/B mix in one note.
- A vs B: 점검·유의사항 나열 → B; 서사·개정 흐름 → A.
- 모범 앵커: `(26-09-03)` 감사전 재무제표 (B); `(26-09-23)` 토지 공시지가 (A). Point to `gold-excerpts` for verbatim.
- DoD table: common 3 axes + A/B consistency row.
- 비범위: legislative, trend-briefing, sanctions, kasb-schedule, `no_summary`.

- [ ] **Step 3: Write `legislative.md`**

- 목적: FSS 세칙예고, FSC 입법예고/규정변경예고.
- 필수: style-A parentheses; must include 취지/배경, 주요 내용, 시행(or 일정), **의견 제출 기한 bold**; 법령·규정명.
- 앵커: `(26-09-18)` 시행세칙; note FSC 규정변경예고 as same family.
- DoD: common 3 + deadline bold + statute name rows.

- [ ] **Step 4: Write `trend-briefing.md`**

- 목적: FSS 회계감독 동향자료.
- 필수: multiple consecutive `<!-- source: pdf|… -->`; note with `(개요)` then one bullet per major attachment theme; sources ↔ topics correspondence.
- 앵커: `(26-07-20)` 감사인 설명회 설명자료 (5 sources).
- DoD: common 3 + source/topic correspondence + overview bullet.

- [ ] **Step 5: Write `kasb-schedule.md`**

- 필수: `!!! note "주요 내용"`; `□ 의결 안건` / `□ 보고 안건`; blank line rules per SKILL REFERENCE E; no bold on agenda instrument names; `해당사항 없음` if empty.
- 앵커: `(26-07-10)` 제8회; `(26-09-04)` 제9회 auxiliary.
- DoD: common 3 + □ headers + no-bold row.

- [ ] **Step 6: Sanity-check mapping completeness**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import re
text = Path('docs/quality-updates/2026/2026-07-01_to_2026-09-30.md').read_text().split('## Appendix')[0]
agency=section=None
noted=set()
for line in text.splitlines():
    if line.startswith('### '): agency=line[4:].strip()
    elif line.startswith('#### '): section=line[5:].strip()
    elif '!!! note' in line or '!!! info' in line:
        noted.add((agency, section))
print(sorted(noted))
PY
```

Expected: the 11 (agency, section) pairs in the README table (제재 counts as one section). Every pair must appear in README.

- [ ] **Step 7: Commit**

```bash
git add docs-dev/summary-formats/
git commit -m "docs: add summary-formats family DoD index and rules"
```

---

### Task 2: sanctions-format Pass/Fail section

**Files:**

- Modify: `docs-dev/sanctions-format.md` (append after §6; do not rewrite §1–§6)

**Interfaces:**

- Consumes: Spec §5.2 sanctions; existing lint rules in §5

- Produces: `## 7. 리뷰 Pass/Fail (DoD)`

- [ ] **Step 1: Append §7**

Add (Korean, match existing voice):

```markdown
---

## 7. 리뷰 Pass/Fail (DoD)

작성·백필·독립 리뷰 때 이 절만으로 Pass/Fail을 기록한다. 규칙 본문은 §1–§6이다. 색인: `summary-formats/README.md`.

| 축 | Pass | Fail 예 |
| --- | --- | --- |
| Format | 회차 제목 하나, Type A/B 표 스키마, `안건 분석`/`위원 논의` 분리, 출처 역할 분리 | 호마다 제목 반복, 표·논의 합침, 감사인 표 허위 삽입 |
| Facts | 회사명·금액·조치가 공개 원문과 일치; 없는 칸만 `미입수` | 추정·반올림; 의결서 부재를 `미입수`로 적음 |
| Tone-detail | 안건·논의가 요약(질의·수정 의결 포함); 빈 기계 문장 없음 | 의사록 줄 단위 덤프, §5 금지 문구 |

Family 전용:

- 보도 붙임에 감사인 조치 없으면 감사인 소제목·표 생략 (제16차 해태 패턴)
- 의사록 없으면 위원 논의는 `미공개` 한 줄
- `lint_public_body.py` 공개 본문 금지 목록 위반 = Format Fail
```

- [ ] **Step 2: Confirm §1–§6 unchanged**

```bash
git diff -- docs-dev/sanctions-format.md | head -80
```

Expected: only additions at end (and maybe a trailing newline). No deletions of existing rule paragraphs.

- [ ] **Step 3: Commit**

```bash
git add docs-dev/sanctions-format.md
git commit -m "docs: add Pass/Fail DoD section to sanctions-format"
```

---

### Task 3: gold-excerpts + checklist → Q3

**Files:**

- Modify: `.claude/skills/quality-updates-writer/reference/gold-excerpts.md`
- Modify: `.claude/skills/quality-updates-writer/reference/gold-excerpts-checklist.md`

**Interfaces:**

- Consumes: Q3 note blocks (verbatim copy, edit nothing); Task 1 family IDs

- Produces: Excerpt-only session gold with Q3-first full-gold pointer; checklist covers aligned

- [ ] **Step 1: Rewrite excerpts header**

Set:

```markdown
**Mode:** Excerpt-only (SKILL.md가 정본)
**Rule:** 세션당 이 파일을 **1회만** Read. 링크 루프에서 재Read 금지.
**Full gold (선택 참고, 판단 어려울 때만 — 전문 의무 아님):**
- `docs/quality-updates/2026/2026-07-01_to_2026-09-30.md` (1순위 · 형태 골드셋)
- `docs/quality-updates/2025/2025-10-01_to_2025-12-31.md` (보조)
- `docs/quality-updates/2023/2023-04-01_to_2023-06-30.md` (보조)
**DoD:** `docs-dev/summary-formats/`
```

- [ ] **Step 2: Replace/add Q3 excerpts (verbatim from Q3)**

Copy **without editing** from Q3 into new/replaced Excerpt sections. Keep IDs stable where possible:

| ID | covers | Q3 source |
|----|--------|-----------|
| E1 | style-A | `(26-09-23)` 토지 공시지가 note block |
| E2 | style-B | `(26-09-03)` 감사전 재무제표 note block |
| E3 | legislative | `(26-09-18)` 시행세칙 note block |
| E4 | trend-briefing | `(26-07-20)` 설명회 (include source markers + note) |
| E5 | type-A | `(26-07-15)` 제13차 금융위 최종 과징금 note (+ tables) |
| E6 | type-B | `(26-07-09)` 제13차 증선위 지적사항 표 note |
| E7 | kasb-schedule | `(26-07-10)` 제8회 주요일정 note |
| E8 | indent-demo | Keep prior indent-demo **or** pick a Q3 nested-bullet note if present; if none, keep 2025 indent-demo with label `Q3 미출현 · 기존 발췌 유지` |
| E9 | style-A, serious-fraud | Keep 2025 serious-fraud with `Q3 미출현 · 기존 발췌 유지` |
| E10 | nested-info | Keep 2025 nested-info with `Q3 미출현 · 기존 발췌 유지` |
| E11 | (optional) style-A KICPA/KASB | One short Q3 KICPA or KASB 공지 note if space; else omit and rely on E1 |

Also add one short **위원 논의** sample under E6 or as E6b if needed for sanctions review — prefer attaching under E6 after the Type B tables from the same 제13차 item (verbatim `!!! note "위원 논의"` block).

Each Excerpt meta must set `source: docs/quality-updates/2026/2026-07-01_to_2026-09-30.md` (or prior path for 미출현).

- [ ] **Step 3: Size check (economics)**

```bash
python3 - <<'PY'
from pathlib import Path
b = Path('.claude/skills/quality-updates-writer/reference/gold-excerpts.md').read_bytes()
print(len(b), 'bytes', len(b)//4, 'tok÷4')
assert len(b) < 80_000, 'excerpts too large — trim; do not paste whole Q3'
assert len(b) > 8_000, 'excerpts too small — missing Q3 anchors'
PY
```

Expected: roughly 15–60KB (well under Q3 full 227KB). Fail if whole Q3 was pasted.

- [ ] **Step 4: Update checklist**

- Refresh Excerpt ID ↔ covers table to match Step 2.
- Add line: 리뷰 시 `docs-dev/summary-formats/` family DoD와 함께 쓴다.
- Keep gate axes Format/Facts/Tone-detail.
- Note Dual historical gate rows can remain as archive; add a row that Q3 excerpt refresh is docs alignment (no new 2016 gate required this PR).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/quality-updates-writer/reference/gold-excerpts.md \
  .claude/skills/quality-updates-writer/reference/gold-excerpts-checklist.md
git commit -m "docs: refresh gold-excerpts to 2026 Q3 family anchors"
```

---

### Task 4: SKILL + project README + superpowers index

**Files:**

- Modify: `.claude/skills/quality-updates-writer/SKILL.md`
- Modify: `docs/project/README.md`
- Modify: `docs/superpowers/README.md`
- Do **not** modify `AGENTS.md` unless user explicitly OK’d the one-line link in this PR conversation.

**Interfaces:**

- Consumes: Task 1–3 paths

- Produces: Cross-links; Q3-first optional full gold; no full-Q3 mandatory Read

- [ ] **Step 1: Patch SKILL.md header / gold paths**

Update lines that list full gold so **2026 Q3 is first**, 2025/2023 auxiliary. Keep Excerpt-only + 재주입 금지.

Add near SUMMARIZE criteria or REFERENCE B:

```markdown
> **형식 DoD (작성·리뷰):** `docs-dev/summary-formats/` (제재는 `docs-dev/sanctions-format.md`)
```

Update REFERENCE E kasb example path to Q3 when mentioning schedule gold.

Update trailing “패턴 예시” line to list Q3 first.

Do **not** change §4b window (±80) or §4c on-demand rules.

- [ ] **Step 2: Patch `docs/project/README.md` SSOT table**

Change 요약 포맷 row to:

| 요약 포맷 | `docs-dev/summary-formats/README.md` (형식·DoD); 워크플로는 `.claude/skills/quality-updates-writer/SKILL.md` |

- [ ] **Step 3: Index in `docs/superpowers/README.md`**

Add Specs row for `2026-11-27-summary-format-dod-design.md` and Plans row for this file.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/quality-updates-writer/SKILL.md \
  docs/project/README.md docs/superpowers/README.md
git commit -m "docs: point writer skill and SSOT map at summary-formats DoD"
```

---

### Task 5: Verify + PR

**Files:**

- Test: lint/commands below; no pytest required (docs-only)
- PR body: scope, economics note, secrets none

- [ ] **Step 1: Confirm no quality-updates body churn**

```bash
git diff origin/main --stat -- docs/quality-updates/
```

Expected: empty (no files).

- [ ] **Step 2: Lint docs under `docs/`**

```bash
npm run lint:md
```

Expected: exit 0. (`docs-dev/` is outside `docs/**/*.md` glob — state that in PR.)

- [ ] **Step 3: Economics regression check**

```bash
python3 - <<'PY'
from pathlib import Path
ex = len(Path('.claude/skills/quality-updates-writer/reference/gold-excerpts.md').read_bytes())
q3 = len(Path('docs/quality-updates/2026/2026-07-01_to_2026-09-30.md').read_bytes())
print('excerpts', ex, 'q3', q3, 'ratio', round(ex/q3, 3))
assert ex < q3 * 0.4, 'excerpts must stay far below full Q3'
skill = Path('.claude/skills/quality-updates-writer/SKILL.md').read_text()
assert '2026-07-01_to_2026-09-30' in skill
assert '전문 gold 읽기 의무 없음' in skill or 'Excerpt-only' in skill
assert 'summary-formats' in skill
PY
```

Expected: asserts pass.

- [ ] **Step 4: Mapping smoke vs README**

Re-run Task 1 Step 6 script; visually confirm README table covers all pairs.

- [ ] **Step 5: Push and open PR**

```bash
git push -u origin HEAD
```

PR title: `docs: 2026 Q3 summary-format DoD + gold-excerpts align`

PR body must include:

- Scope: `docs-dev/summary-formats/*`, sanctions Pass/Fail, gold-excerpts/checklist, SKILL, project/superpowers README
- Non-scope: no `docs/quality-updates` edits; no lint expansion; AGENTS.md unchanged unless approved
- Economics: Excerpt-only retained; full Q3 not mandatory session gold
- Verify commands + results
- Secrets: none

- [ ] **Step 6: Ask user about AGENTS.md one-liner**

In the PR or chat: whether to add `docs-dev/summary-formats/` next to the V-205 Q3 goldset bullet. Do not edit until they say yes.

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| README mapping + review how-to | Task 1 |
| general-note / legislative / trend / kasb | Task 1 |
| sanctions Pass/Fail only | Task 2 |
| gold-excerpts Q3 + keep 미출현 | Task 3 |
| checklist | Task 3 |
| SKILL + project README | Task 4 |
| Acceptance §8 / economics ceiling | Task 5 |
| AGENTS optional | Task 5 Step 6 |

## Self-review notes

- No TBD placeholders in steps.
- No full-Q3 mandatory Read (economics).
- Family file templates are specified enough to write without re-opening the brainstorm thread; verbatim blocks come from Q3 at implementation time via Read, not invented.
