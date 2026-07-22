# SUMMARIZE 비용 슬림 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SUMMARIZE 고정 컨텍스트를 줄이되 gold 수준을 유지한다 — `gold-excerpts` + md 윈도우 + REFERENCE 온디맨드 + 재주입 금지, Dual 게이트 Pass 후 Excerpt-only.

**Architecture:** 스킬 `reference/`에 발췌·체크리스트를 두고 `SKILL.md` SUMMARIZE 의식만 바꾼다. Dual로 먼저 배포한 뒤 2016 표본 2–3링크 대조 게이트를 스펙 §8에 기록하고, Pass 시에만 전문 gold 의무를 제거한다. 코퍼스 본문은 수정하지 않는다.

**Tech Stack:** Markdown skill (Cursor/Claude), gold 분기 md에서 블록 복사, 기존 `extract_pdf.py` (게이트 원문만)

**Spec:** `docs/superpowers/specs/2026-07-23-summarize-slim-design.md`

## Global Constraints

- 품질 하한 C: 포맷·사실·어조·상세도 gold 수준; 게이트 Fail 시 Excerpt-only 금지
- SUMMARIZE만 변경; BOILERPLATE/SKIP_REMOVAL 워크플로 문구는 깨지 말 것
- `docs/quality-updates/**` 본문 수정 금지 (게이트 스크래치는 `.superpowers/sdd/`만)
- OCR/#4 제재 sparse pdf·shot 파이프라인·로컬 LLM 비범위
- 재주입 금지: gold/발췌/SKILL 전문은 세션당 해당 자산 1회 Read
- 분기 md Phase 1: ±80줄 + 기관/소절 헤더만 (전문 Read 금지)
- 커밋은 사용자 요청 시 또는 이 플랜 실행 승인 시 브랜치에만

---

## File map

| File | Action | Responsibility |
|------|--------|----------------|
| `.claude/skills/quality-updates-writer/reference/gold-excerpts.md` | Create | 8–12 대표 note 블록 |
| `.claude/skills/quality-updates-writer/reference/gold-excerpts-checklist.md` | Create | 커버리지·게이트 축 체크리스트 |
| `.claude/skills/quality-updates-writer/SKILL.md` | Modify | Dual → (Task 5) Excerpt-only |
| `docs/superpowers/specs/2026-07-23-summarize-slim-design.md` | Modify | 상태·§8 게이트 결과 |
| `docs/superpowers/plans/2026-07-23-summarize-slim.md` | Create | 본 파일 |
| `docs/superpowers/README.md` | Modify | Plans 행 |
| `AGENTS.md` | Modify | SUMMARIZE 슬림 규칙 1줄 (선택·권장) |
| `docs/project/quarterly-operations-guide.md` | Modify | Phase 3에 윈도우/발췌 1줄 (선택·권장) |

---

### Task 1: `gold-excerpts.md` 큐레이션

**Files:**
- Create: `.claude/skills/quality-updates-writer/reference/gold-excerpts.md`
- Read: `docs/quality-updates/2023/2023-04-01_to_2023-06-30.md`
- Read: `docs/quality-updates/2025/2025-10-01_to_2025-12-31.md`

**Interfaces:**
- Produces: 파일 내 `### Excerpt N — …` 블록 8–12개, 각 블록에 `source:` 경로와 대략 줄 번호

- [ ] **Step 1: reference 디렉터리 생성**

```powershell
New-Item -ItemType Directory -Force -Path .claude/skills/quality-updates-writer/reference | Out-Null
```

- [ ] **Step 2: 발췌 목록 확정 (최소 구성 — 줄 번호는 Read로 재확인 후 조정)**

복사할 블록 (링크 줄 + `!!! note` 전체; Type B면 접기/`???` 포함):

| ID | 요구 | 권장 소스 |
|----|------|-----------|
| E1 | 스타일 A (괄호 접두) | 2023 Q2 초반 FSS note 1건 (예: L26 부근) |
| E2 | 스타일 A | 2025 Q4 FSS note 1건 (예: L29 부근) |
| E3 | 스타일 B (볼드-콜론) | 2025 L195–202 감사전 재무제표 등 |
| E4 | 스타일 B | 2025 L207–213 내부회계 과태료 등 |
| E5 | Type A 표 | 2025 L276–290 부근 `조사·감리결과 최종 과징금 부과` |
| E6 | Type B | 2025 L230–260 부근 증선위 조치(회사별·감사인 표) |
| E7 | 입법예고 (E형) | 2025 L366–375 부근 |
| E8 | 들여쓰기 모범 | E1 또는 E3와 중복 없이 짧은 note 1건 |
| E9–E12 | (선택) 중대부정 서술·KASB 주요일정·심사감리 중첩 info | 2025 L311 / KASB / L130 부근 — 총 블록 ≤12 |

- [ ] **Step 3: 파일 헤더 + 블록 기록**

`gold-excerpts.md` 상단:

```markdown
# Gold excerpts for SUMMARIZE (quality-updates-writer)

**Mode:** Dual / Excerpt-only (SKILL.md가 정본)
**Rule:** 세션당 이 파일을 **1회만** Read. 링크 루프에서 재Read 금지.
**Full gold (Dual only, 판단 어려울 때):**
- `docs/quality-updates/2023/2023-04-01_to_2023-06-30.md`
- `docs/quality-updates/2025/2025-10-01_to_2025-12-31.md`

각 Excerpt는 원문을 **편집 없이** 복사한다. 출처만 메타로 적는다.
```

각 Excerpt:

```markdown
### Excerpt N — <짧은 라벨>

- source: `<path>` ~Lstart–Lend
- covers: style-A | style-B | type-A | type-B | legislative | indent-demo | …

```markdown
<원문 그대로>
```
```

(내부 펜스 충돌 시 Excerpt 본문은 4-backtick fence 사용.)

- [ ] **Step 4: 커버리지 검증**

```powershell
$t = Get-Content .claude/skills/quality-updates-writer/reference/gold-excerpts.md -Raw -Encoding utf8
$n = ([regex]::Matches($t, '(?m)^### Excerpt ')).Count
"excerpts=$n"
# Expect: 8 <= n <= 12
# Manually confirm covers tags include style-A×2, style-B×2, type-A, type-B, legislative, indent-demo
```

Expected: `excerpts` 8–12; 스펙 §4.1 최소 구성 충족.

- [ ] **Step 5: Commit (플랜 실행 승인 시)**

```bash
git add .claude/skills/quality-updates-writer/reference/gold-excerpts.md
git commit -m "$(cat <<'EOF'
docs(skill): add SUMMARIZE gold-excerpts reference pack

EOF
)"
```

---

### Task 2: 체크리스트 파일

**Files:**
- Create: `.claude/skills/quality-updates-writer/reference/gold-excerpts-checklist.md`

**Interfaces:**
- Consumes: Task 1 Excerpt IDs
- Produces: 커버리지 표 + 게이트 3축 표 (빈 결과열)

- [ ] **Step 1: 파일 작성**

필수 섹션:

1. **Coverage** — Excerpt ID ↔ covers 태그 표 (Task 1과 일치)
2. **Gate axes** — Format / Facts / Tone-detail — Pass 정의 (스펙 §5.2 문구 그대로)
3. **Gate runs** — 표본 `#1 #2 #5` (경제성 스펙 §9.2), 결과 열 공란
4. **Sign-off** — Dual / Excerpt-only / Fail·보강

- [ ] **Step 2: 검증** — Coverage 행 수 = Excerpt 수; Gate axes 3행 존재

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/quality-updates-writer/reference/gold-excerpts-checklist.md
git commit -m "$(cat <<'EOF'
docs(skill): add gold-excerpts quality gate checklist

EOF
)"
```

---

### Task 3: SKILL.md Dual 모드

**Files:**
- Modify: `.claude/skills/quality-updates-writer/SKILL.md`
- Modify: `docs/superpowers/specs/2026-07-23-summarize-slim-design.md` (상태 → Dual 구현)

**Interfaces:**
- Consumes: `reference/gold-excerpts.md` 경로
- Produces: SUMMARIZE가 Dual 규칙으로 동작

- [ ] **Step 1: 상단 gold 배지 문구 교체**

기존 (L8 근처):

```markdown
> **기준 파일(gold standard)**: `docs/quality-updates/2023/...`, `docs/quality-updates/2025/...`
```

교체:

```markdown
> **SUMMARIZE 기준 (Dual):** 기본 `.claude/skills/quality-updates-writer/reference/gold-excerpts.md` (세션 1회). 판단 어려울 때만 전문 gold 2파일 추가 1회. **재주입 금지.**
> **전문 gold (선택):** `docs/quality-updates/2023/2023-04-01_to_2023-06-30.md`, `docs/quality-updates/2025/2025-10-01_to_2025-12-31.md`
```

- [ ] **Step 2: Announce 템플릿 갱신**

```markdown
> `quality-updates-writer 스킬로 [작업 유형]을 시작합니다. SUMMARIZE 기준: gold-excerpts.md (Dual; 전문 gold는 판단 어려울 때만)`
```

- [ ] **Step 3: §4 Gold Standard 확인 → Dual 절차로 교체**

```markdown
### 4. Gold / excerpts 확인 (SUMMARIZE만)

Phase 1 시작 전 **세션당 1회**:
1. `reference/gold-excerpts.md`를 Read한다.
2. 포맷·어조가 발췌만으로 불충분할 때만 전문 gold 2파일 중 필요 분량을 Read한다 (가능하면 해당 Excerpt 출처 구간만).
3. 이후 링크 루프에서 gold-excerpts·전문 gold·이 SKILL.md 전문을 **다시 Read하지 않는다**.

### 4b. 분기 md 윈도우 (SUMMARIZE Phase 1)

대상 분기 파일 **전문 Read 금지**. 허용: 링크 줄 ±80줄, 소속 `##`/`####` 헤더, 삽입 후 해당 `!!! note`만 재확인. Appendix·타 기관 전체 로드 금지.

### 4c. REFERENCE 온디맨드

| 링크 유형 | 로드 |
|-----------|------|
| 일반 보도/공지 | A + B (세션 내 기로드 시 재Read 금지) |
| 제재·증선위 | + D |
| 입법예고·특수 | + E |
| Appendix | + G |
| 선별 판단 | + C |

매 링크 A–G 전체 재독 **금지**.
```

- [ ] **Step 4: Phase 1 본문에 “→ REFERENCE A,B,C,D,E 참조”를 온디맨드 표 인용으로 완화** (전 항목 강제 재독처럼 읽히지 않게)

- [ ] **Step 5: 스펙 상태줄**

`상태: Dual 구현 — 게이트 대기`

- [ ] **Step 6: 검증**

```powershell
Select-String -Path .claude/skills/quality-updates-writer/SKILL.md -Pattern 'gold-excerpts|재주입|±80|온디맨드|Dual'
# Expect: multiple hits; old "반드시 읽어" full-gold-only wording for SUMMARIZE should be gone
```

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/quality-updates-writer/SKILL.md docs/superpowers/specs/2026-07-23-summarize-slim-design.md
git commit -m "$(cat <<'EOF'
feat(skill): Dual SUMMARIZE slim — excerpts, window, on-demand REFERENCE

EOF
)"
```

---

### Task 4: 품질 게이트 대조 (스크래치)

**Files:**
- Read: 경제성 스펙 §9.2 표본 `#1 #2 #5` 및 해당 `downloads/` pdf
- Write (untracked OK): `.superpowers/sdd/slim-gate-drafts.md`
- Modify: `reference/gold-excerpts-checklist.md` Gate runs
- Modify: `docs/superpowers/specs/2026-07-23-summarize-slim-design.md` §8

**Interfaces:**
- Consumes: Dual SKILL rules
- Produces: §8 채워진 표; Pass/Fail 판정

- [ ] **Step 1: 고지**

> `품질 게이트: SUMMARIZE Dual vs legacy, 표본 3/3, 본문 미반영`

- [ ] **Step 2: 각 표본에 대해 (a)(b) 초안**

| # | 링크 (경제성 §9.2) | source |
|---|-------------------|--------|
| 1 | 16-03-01 외부감사제도 순회 설명회 | `downloads/160302_조간_2016년 외부감사제도 전국 순회 설명회 개최.pdf` |
| 2 | 16-02-01 감사전 재무제표 제출 | `downloads/160201_조간_자산총액 1천억원 이상인 비상장법인은 올해부터 감사전 재무제표를 금융감독원에 제출해야 합니다_f.pdf` |
| 5 | 16-02-16 수주산업 설명회 | `downloads/160216_석간_수주산업 회계투명성 제고방안 설명회 개최.pdf` |

(a) legacy: 발췌 대신 전문 gold 규칙을 **가정**한 초안 (실제 전문 2파일 전부 읽지 말고, “구규칙 의도”로 동일 원문·동일 REFERENCE로 초안 — **공정 비교를 위해 원문·윈도우는 (b)와 동일**하게 맞출 것; 차이는 스타일 앵커만 excerpts vs 기억/발췌).

실용적 공정 비교 (컨트롤러 해석):
- **공통:** 동일 pdf extract, 동일 ±80줄 md 윈도우, 동일 REFERENCE 온디맨드
- **차이:** (a)는 Excerpt 대신 gold 파일에서 **해당 유형 유사 note 1–2개만** 추가 참조; (b)는 `gold-excerpts`만

초안은 `.superpowers/sdd/slim-gate-drafts.md`에만. **2016 md 편집 금지.**

- [ ] **Step 3: 3축 판정 → 체크리스트·스펙 §8 기입**

Pass 조건: 3링크 × 3축 모두 Pass (Minor만 HITL 명시 시 허용).

- [ ] **Step 4: Fail이면** Excerpt 보강(Task 1 재오픈) 후 재대조. **Excerpt-only Task 5 진행 금지.**

- [ ] **Step 5: Pass면 Commit**

```bash
git add .claude/skills/quality-updates-writer/reference/gold-excerpts-checklist.md docs/superpowers/specs/2026-07-23-summarize-slim-design.md
git commit -m "$(cat <<'EOF'
docs: record SUMMARIZE slim Dual quality gate results

EOF
)"
```

---

### Task 5: Excerpt-only 전환 + 문서 1줄

**Files:**
- Modify: `.claude/skills/quality-updates-writer/SKILL.md`
- Modify: `docs/superpowers/specs/2026-07-23-summarize-slim-design.md`
- Modify: `AGENTS.md` (권장)
- Modify: `docs/project/quarterly-operations-guide.md` Phase 3 (권장)
- Modify: `docs/superpowers/README.md` Plans 행

**Precondition:** Task 4 Pass. Fail이면 이 태스크 스킵·BLOCKED.

- [ ] **Step 1: SKILL Excerpt-only**

- Dual 배지 → `기본 gold-excerpts만 (세션 1회). 전문 gold 읽기 의무 없음(선택 참고). 재주입 금지.`
- §4에서 전문 gold 의무 문단 삭제; “판단 어려울 때” 분량도 **선택**으로만 남기거나 삭제(스펙: 의무 삭제, 경로는 선택 링크).
- Announce를 Excerpt-only로 갱신.

- [ ] **Step 2: AGENTS.md**

분기 보도자료 요약 행 참고에 한 줄:

`SUMMARIZE: gold-excerpts + md ±80줄 윈도우 + REFERENCE 온디맨드; 재주입 금지. 상세: docs/superpowers/specs/2026-07-23-summarize-slim-design.md`

- [ ] **Step 3: quarterly-operations-guide.md Phase 3**

Writer 스킬 행에 동일 취지 1문장.

- [ ] **Step 4: 스펙 상태** `Excerpt-only 적용` + §8 단계 열 갱신; README Plans:

```markdown
| 2026-07-23 | [summarize-slim.md](plans/2026-07-23-summarize-slim.md) | SUMMARIZE 비용 슬림 (발췌·윈도우·게이트) |
```

- [ ] **Step 5: 회귀 검증**

```powershell
git diff --name-only -- docs/quality-updates/
# Expect: empty (or only unrelated pre-existing untracked 2016 — do not add)
Select-String -Path .claude/skills/quality-updates-writer/SKILL.md -Pattern '반드시 읽어' 
# Expect: no SUMMARIZE full-gold mandate; boilerplate refs to gold templates OK if unrelated
```

가능하면:

```bash
cd scripts && python -m pytest tests/ -q
python scripts/validate_content.py --strict
```

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/quality-updates-writer/SKILL.md AGENTS.md docs/project/quarterly-operations-guide.md docs/superpowers/specs/2026-07-23-summarize-slim-design.md docs/superpowers/README.md docs/superpowers/plans/2026-07-23-summarize-slim.md
git commit -m "$(cat <<'EOF'
feat(skill): Excerpt-only SUMMARIZE after quality gate pass

EOF
)"
```

---

## Plan self-review

| Spec § | Task |
|--------|------|
| §4.1 발췌 | Task 1 |
| §4.2–4.4 윈도우·온디맨드·재주입 | Task 3 |
| §5 Dual→게이트→Excerpt-only | Task 3–5 |
| §5.2 게이트 / §8 | Task 4 |
| §6 산출물 | Task 1–5 |
| 비범위 OCR 등 | Global — 미포함 |

Placeholder scan: 없음. Task 4의 (a)(b) 공정 비교는 컨트롤러 해석 블록으로 고정.
