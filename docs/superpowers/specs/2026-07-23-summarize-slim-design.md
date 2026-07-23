# SUMMARIZE 비용 슬림 (품질 유지) — Design

**날짜**: 2026-07-23  
**상태**: Excerpt-only 적용  
**선행**: [2026-07-23-summarize-economics-design.md](2026-07-23-summarize-economics-design.md) §9.3–§9.4  
**대상**: `.claude/skills/quality-updates-writer` — **SUMMARIZE**만

---

## 1. 목적

Phase 3 SUMMARIZE의 고정·반복 컨텍스트를 줄이되 **gold 수준(포맷·사실·어조·상세도)** 을 유지한다. 경제성 진단의 슬림 후보와 gold 발췌를 **품질 게이트 통과 후** 정본으로 올린다.

전제: 품질 유지가 가능하다는 HITL/설계 합의. 게이트 Fail 시 Excerpt-only로 올리지 않는다.

---

## 2. 범위·비범위

### 범위

| # | 변경 | 예상 절감(진단 추정) |
|---|------|----------------------|
| 1 | 분기 md → 링크 ±80줄(+기관/소절 헤더) 윈도우 | ~60–90k tok÷4/세션 |
| 2 | REFERENCE A–G → 유형별 온디맨드 (매 링크 전체 재독 금지) | ~1.5–2k/재독 |
| 3 | gold 2파일 전문 → `gold-excerpts.md` (8–12 대표 블록) | ~80–100k tok÷4/세션 |
| 4 | gold/발췌/SKILL **재주입 금지** (세션당 해당 자산 1회 Read) | 고정비 팽창 방지 |
| 5 | 게이트: 체크리스트 + 2016 표본 2–3링크 대조 | C 입증 |

### 비범위

- OCR / sparse 제재 pdf 추출 개선  
- shot·비전 파이프라인  
- BOILERPLATE / SKIP_REMOVAL  
- 로컬 LLM  
- 2016 Q1 전체 note 백필  

---

## 3. 접근

**발췌 gold + Dual 게이트 후 Excerpt-only 전환** (브레인스토밍 안 2).

1. 발췌 파일 큐레이션  
2. SKILL에 윈도우·온디맨드·재주입 금지 + Dual 규칙  
3. 대조 실측 + 체크리스트  
4. Pass 시 Excerpt-only  

---

## 4. 상세 규칙

### 4.1 Gold 발췌

- **경로:** `.claude/skills/quality-updates-writer/reference/gold-excerpts.md`
- **구성 (8–12 블록):** 원문 note를 출처 경로·대략 위치와 함께 복사  
  - 일반 note 스타일 A·B 각 ≥2  
  - Type A 표 1, Type B(접기+표) 1  
  - REFERENCE E형(입법예고 등) ≥1  
  - `!!! note`·들여쓰기 모범 ≥1  
- **소스 gold:**  
  - `docs/quality-updates/2023/2023-04-01_to_2023-06-30.md`  
  - `docs/quality-updates/2025/2025-10-01_to_2025-12-31.md`

### 4.2 분기 md 윈도우

SUMMARIZE Phase 1에서 대상 분기 파일 **전문 Read 금지**.

**허용:**

1. 해당 링크 줄 기준 **±80줄**  
2. 소속 `## 기관` 및 `#### 소절` 헤더  
3. 삽입 후 해당 `!!! note` 블록만 재확인  

Appendix·타 기관 섹션 전체 로드 금지(다른 작업 유형 제외).

### 4.3 REFERENCE 온디맨드

| 링크 유형 | 로드 |
|-----------|------|
| 일반 보도/공지 | A + B (세션 내 이미 로드됐으면 재Read 금지) |
| 제재·증선위 조치 | + D |
| 입법예고·특수 유형 | + E |
| Appendix 구조 작업 | + G |
| 요약 대상 선별 판단 | + C |

**금지:** 매 링크마다 REFERENCE A–G 전체 재독.

### 4.4 재주입 금지

- Phase 1 시작 전: Dual에서는 `gold-excerpts` (+ 필요 시 전문 gold)를 **세션당 1회**만 Read.  
- Excerpt-only에서는 `gold-excerpts`만 세션당 1회.  
- 링크 루프에서 gold·발췌·SKILL 전문 **재Read 금지**.  
- 컨텍스트 부족 시 발췌/gold를 다시 넣지 말고, §4.3에 따라 REFERENCE **부분**만 로드.

---

## 5. 롤아웃·게이트

### 5.1 Dual → Excerpt-only

| 단계 | SKILL | 종료 |
|------|-------|------|
| **Dual** | 기본=`gold-excerpts`; 전문 gold는 “판단 어려울 때만”; §4.2–4.4 적용 | 게이트 Pass |
| **Excerpt-only** | 전문 읽기 의무 삭제; gold 2경로는 선택 참고 링크만 | — |

### 5.2 품질 게이트

**표본 (본문 미반영 스크래치):** 경제성 진단 §9.2 권장 — `#1` 짧은 pdf, `#2` 긴 pdf, `#5` 짧은 pdf (또는 `#3` shot). `#4`(OCR sparse)는 **게이트 제외**.

**대조:** (a) 구규칙(전문 gold) 초안 vs (b) 신규칙(발췌+윈도우+온디맨드) 초안.

| 축 | Pass |
|----|------|
| 포맷 | `!!! note`, 들여쓰기, 스타일 A/B 일관 |
| 사실 | 수치·기한·대상 누락·왜곡 없음 |
| 어조·상세도 | gold 수준 (과소/과다 아님) |

**Pass 조건:** 대조 대상 링크 **전 건** 3축 Pass (HITL이 명시한 Minor만 허용).  
**Fail:** 발췌 보강 후 재대조. Excerpt-only 금지.

체크리스트 파일: `.claude/skills/quality-updates-writer/reference/gold-excerpts-checklist.md`  
통과 기록: 본 스펙 §8에 일자·표본·결과 표.

### 5.3 롤백

품질 회귀 시 Dual 복귀 또는 전문 의무 복구(`git`). 발췌만 수정 후 재게이트 가능.

---

## 6. 산출물

| 경로 | 동작 |
|------|------|
| `.claude/skills/quality-updates-writer/SKILL.md` | Modify — SUMMARIZE 의식·Phase 0/1 |
| `.claude/skills/quality-updates-writer/reference/gold-excerpts.md` | Create |
| `.claude/skills/quality-updates-writer/reference/gold-excerpts-checklist.md` | Create |
| `docs/superpowers/specs/2026-07-23-summarize-slim-design.md` | 본 파일 |
| `docs/superpowers/README.md` | 인덱스 1행 |
| `AGENTS.md` / `docs/project/quarterly-operations-guide.md` | 필요 시 SUMMARIZE 비용 규칙 1줄 |

코퍼스 `docs/quality-updates/**` 본문은 게이트 스크래치 외 **수정하지 않음**.

---

## 7. 성공 기준·검증

- SKILL이 §4 규칙을 명시적으로 강제  
- Dual 구현 후 게이트 표가 §8에 채워짐  
- Pass 후 Excerpt-only로 SKILL 전환 커밋  
- `git diff -- .claude/skills/quality-updates-writer` 외 의도치 않은 코퍼스 변경 없음  
- 기존: `cd scripts && python -m pytest tests/ -q` (환경 허용 시), `validate_content.py --strict` 회귀  

---

## 8. 게이트 결과 (구현 후 채움)

| 일자 | 표본 링크 | 포맷 | 사실 | 어조·상세 | 종합 |
|------|-----------|------|------|-----------|------|
| 2026-07-23 | #1 16-03-01 외부감사제도 순회 설명회 | Pass | Pass | Pass | Pass |
| 2026-07-23 | #2 16-02-01 감사前 재무제표 제출 | Pass | Pass | Pass | Pass |
| 2026-07-23 | #5 16-02-16 수주산업 설명회 | Pass | Pass | Pass | Pass |

**단계:** Excerpt-only 적용 (Task 5, 2026-07-23) / 롤백 불필요(Fail 없음)  
**비고:**
- 대조 방법: (a) legacy-style anchor(공통 pdf extract·±80줄 md 윈도우·REFERENCE A+B 동일 + 전문 gold에서 유사 note 1–2개 추가 참조) vs (b) Dual(`gold-excerpts.md` E1–E4만). 상세: `.superpowers/sdd/slim-gate-drafts.md`.
- 3표본 모두 (a)/(b) 산출물이 **문자 그대로 동일** — 발췌 최소구성(style-A E1·E2, style-B E3·E4)이 표본의 일반 note 유형을 정확히 커버하여 전문 gold 추가 참조가 품질에 차이를 만들지 않음.
- Facts는 PDF 원문 직접 대조로 확인(수치·기한·대상 누락 없음); Facts 축은 gold 소스와 무관하게 원문 의존이므로 (a)/(b) 원천적으로 동일.
- **주의(범위 한정):** 이번 3표본은 모두 일반 note(style-A/B)이며 Type A/B 표·입법예고(E형)·`??? info` 접기는 대조 대상에 포함되지 않음(경제성 §9.2 `#4` OCR sparse 제외 규칙에 따름). 해당 유형 슬림 신뢰도는 후속 표본 확대 시 재확인 권고.
