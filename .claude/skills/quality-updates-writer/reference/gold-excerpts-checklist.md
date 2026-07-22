# Gold excerpts quality gate checklist

**Spec:** `docs/superpowers/specs/2026-07-23-summarize-slim-design.md` §5.2  
**Excerpts:** `reference/gold-excerpts.md` (E1–E11)  
**Sample links:** `docs/superpowers/specs/2026-07-23-summarize-economics-design.md` §9.2

---

## Coverage

Excerpt ID ↔ `covers` tags (Task 1 큐레이션과 일치).  
**type-B** = 증선위·금융위 조치 표(E6). **nested-info** = `??? info` 접기(E10) — 별도 태그.

| ID | Title (short) | covers |
|----|---------------|--------|
| E1 | FSS style A (2023 Q2 설명회) | style-A |
| E2 | FSS style A (2025 Q4 CEO 간담회) | style-A |
| E3 | FSS style B (결산·감사 유의) | style-B |
| E4 | FSS style B (내부회계 과태료) | style-B |
| E5 | Type A (과징금 부과 표) | type-A |
| E6 | Type B (증선위 조치, 회사별·감사인 표) | type-B |
| E7 | 입법예고 (E형) | legislative |
| E8 | 들여쓰기 모범 (중첩 불릿) | indent-demo |
| E9 | 중대부정 서술 (장문 style-A) | style-A, serious-fraud |
| E10 | 심사·감리 지적사례 (`??? info` 접기) | nested-info |
| E11 | KASB 주요일정 (의결·보고 안건) | kasb-schedule |

**Minimum composition (§4.1):** style-A ≥2 · style-B ≥2 · type-A 1 · type-B 1 · legislative ≥1 · indent-demo ≥1 — satisfied.

---

## Gate axes

대조: (a) 구규칙(전문 gold) 초안 vs (b) 신규칙(발췌+윈도우+온디맨드) 초안.

| Axis | Pass |
|------|------|
| Format | `!!! note`, 들여쓰기, 스타일 A/B 일관 |
| Facts | 수치·기한·대상 누락·왜곡 없음 |
| Tone-detail | gold 수준 (과소/과다 아님) |

**Pass 조건:** 대조 대상 링크 **전 건** 3축 Pass (HITL이 명시한 Minor만 허용).  
**Fail:** 발췌 보강 후 재대조. Excerpt-only 금지.

---

## Gate runs

표본 `#1` `#2` `#5` (경제성 §9.2; `#4` OCR sparse는 게이트 제외).  
결과 열은 Task 4 대조 후 기입.

| # | Link (date · title) | source | Format | Facts | Tone-detail | Overall |
|---|---------------------|--------|--------|-------|-------------|---------|
| 1 | 16-03-01 · 2016년 외부감사제도 전국 순회 설명회 개최 | `pdf\|downloads/160302_조간_2016년 외부감사제도 전국 순회 설명회 개최.pdf` | | | | |
| 2 | 16-02-01 · 자산총액 1천억+ 비상장법인 감사前 재무제표 제출 | `pdf\|downloads/160201_조간_자산총액 1천억원 이상인 비상장법인은 올해부터 감사전 재무제표를 금융감독원에 제출해야 합니다_f.pdf` | | | | |
| 5 | 16-02-16 · 수주산업 회계투명성 제고방안 설명회 개최 | `pdf\|downloads/160216_석간_수주산업 회계투명성 제고방안 설명회 개최.pdf` | | | | |

---

## Sign-off

| Stage | Date | Result | Notes |
|-------|------|--------|-------|
| Dual | | | SKILL Dual 규칙 적용; 게이트 대조 전 |
| Excerpt-only | | | Task 4 Pass 후에만 전환 |
| Fail · 보강 | | | 발췌 재큐레이션·재대조 필요 시 |
