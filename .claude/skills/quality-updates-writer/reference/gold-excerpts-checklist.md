# Gold excerpts quality gate checklist

**Spec:** `docs/superpowers/specs/2026-07-23-summarize-slim-design.md` §5.2  
**Excerpts:** `reference/gold-excerpts.md` (E1–E10; E11 생략 — E1 style-A로 대체)  
**Sample links:** `docs/superpowers/specs/2026-07-23-summarize-economics-design.md` §9.2  
**DoD (family):** 리뷰 시 `docs-dev/summary-formats/` family DoD와 함께 쓴다.

---

## Coverage

Excerpt ID ↔ `covers` tags (Task 1 큐레이션과 일치).  
**type-B** = 증선위·금융위 조치 표(E6). **nested-info** = `??? info` 접기(E10) — 별도 태그.

| ID | Title (short) | covers |
|----|---------------|--------|
| E1 | FSS style A (토지 공시지가, 2026 Q3) | style-A |
| E2 | FSS style B (감사전 재무제표, 2026 Q3) | style-B |
| E3 | 입법예고·시행세칙 (2026 Q3) | legislative |
| E4 | 회계감독 동향 (설명회 설명자료, 2026 Q3) | trend-briefing |
| E5 | Type A (제13차 금융위 과징금 표) | type-A |
| E6 | Type B (제13차 증선위 표 + 위원 논의) | type-B |
| E7 | KASB 주요일정 (제8회, 2026 Q3) | kasb-schedule |
| E8 | 들여쓰기 모범 (중첩 불릿) | indent-demo |
| E9 | 중대부정 서술 (장문 style-A) | style-A, serious-fraud |
| E10 | 심사·감리 지적사례 (`??? info` 접기) | nested-info |

E8·E9·E10은 **Q3 미출현 · 기존 발췌 유지** (2025 Q4 원문).

**Minimum composition (§4.1):** style-A ≥2 (E1·E9) · style-B ≥1 (E2) · type-A 1 · type-B 1 · legislative ≥1 · trend-briefing ≥1 · indent-demo ≥1 · kasb-schedule ≥1 — satisfied.

---

## Gate axes

대조: (a) 구규칙(전문 gold) 초안 vs (b) 신규칙(발췌+윈도우+온디맨드) 초안.

| Axis | Pass |
|------|------|
| Format | `!!! note`, 들여쓰기, 스타일 A/B 일관 |
| Facts | 수치·기한·대상 누락·왜곡 없음 |
| Tone-detail | gold 수준 (과소/과다 아님) |

**Pass 조건:** 대조 대상 링크 **전 건** 3축 Pass (전문가가 명시한 Minor만 허용).  
**Fail:** 발췌 보강 후 재대조. Excerpt-only 금지.

---

## Gate runs

표본 `#1` `#2` `#5` (경제성 §9.2; `#4` OCR sparse는 게이트 제외).  
결과 열은 Task 4 대조 후 기입.

| # | Link (date · title) | source | Format | Facts | Tone-detail | Overall |
|---|---------------------|--------|--------|-------|-------------|---------|
| 1 | 16-03-01 · 2016년 외부감사제도 전국 순회 설명회 개최 | `pdf\|downloads/160302_조간_2016년 외부감사제도 전국 순회 설명회 개최.pdf` | Pass | Pass | Pass | Pass |
| 2 | 16-02-01 · 자산총액 1천억+ 비상장법인 감사前 재무제표 제출 | `pdf\|downloads/160201_조간_자산총액 1천억원 이상인 비상장법인은 올해부터 감사전 재무제표를 금융감독원에 제출해야 합니다_f.pdf` | Pass | Pass | Pass | Pass |
| 5 | 16-02-16 · 수주산업 회계투명성 제고방안 설명회 개최 | `pdf\|downloads/160216_석간_수주산업 회계투명성 제고방안 설명회 개최.pdf` | Pass | Pass | Pass | Pass |

**대조 상세:** `.superpowers/sdd/slim-gate-drafts.md` — (a) legacy(전문 gold 유사 note 1–2개 추가 참조) vs (b) Dual(`gold-excerpts.md` E1–E4만) 초안이 3링크 모두 **문자 그대로 동일**. Format(들여쓰기·style-A/B 구조), Facts(수치·기한·대상 — PDF 원문 직접 대조), Tone-detail(불릿 4–6개, gold 수준) 전 축 Pass. 근거: 표본이 모두 일반 note(style-A/B)이고 발췌 최소구성(E1·E2 style-A/B, E3·E4 style-B)이 정확히 해당 유형을 커버하여 전문 gold 추가 참조가 새 정보를 제공하지 않음.

---

## Sign-off

| Stage | Date | Result | Notes |
|-------|------|--------|-------|
| Dual | 2026-07-23 | Pass | 표본 #1·#2·#5 3링크×3축 전건 Pass (Minor 없음). SKILL Dual 규칙 유지, Excerpt-only 전환 승인 대기(별도 Task) |
| Excerpt-only | 2026-07-23 | Pass/적용 | Task 5 SKILL Excerpt-only 전환 완료 |
| Q3 excerpt refresh | 2026-11-27 | Docs alignment | `gold-excerpts.md` Q3 앵커(E1–E7) 갱신; **2016 표본 게이트 재실행 없음**(이번 PR) |
| Fail · 보강 | — | N/A | 이번 게이트는 Fail 없음 |