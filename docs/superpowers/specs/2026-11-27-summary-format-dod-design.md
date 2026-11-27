# 요약 형식 DoD (2026 Q3 골드셋) — 설계 스펙

**날짜**: 2026-11-27  
**상태**: 설계 합의됨. 이 파일 검토 후 구현 계획.  
**모범**: [`docs/quality-updates/2026/2026-07-01_to_2026-09-30.md`](../../quality-updates/2026/2026-07-01_to_2026-09-30.md)  
**관련**: [`docs-dev/sanctions-format.md`](../../../docs-dev/sanctions-format.md), [summarize-slim](2026-07-23-summarize-slim-design.md), AGENTS.md 장기 목표 1(백필 형태 = 2026 Q3 골드셋)

합의:

- Intent = 기관·요약 타입별 **작성 형식 + 리뷰 Pass/Fail**을 한 체계로 둔다. 향후 공시분 요약·과거 백필·PR 리뷰의 목표로 쓴다.
- 범위 = **Q3에 실제로 `!!! note`/`!!! info`가 있는 타입만**. `<!-- no_summary -->` 타입은 1차 제외.
- 접근 = **작성 가족(family)별 파일 + 색인** (`docs-dev/summary-formats/`). 제재는 기존 `sanctions-format.md` 유지하고 **Pass/Fail 절만 추가**.
- 정합 = DoD 문서 + `gold-excerpts` Q3 갱신 + `SKILL.md` REFERENCE 정합 (옵션 3).
- 비범위 = 기계 린트 확대, 분기 본문·백필 콘텐츠 재작성, 큐레이션 마커 대량 변경.

---

## 1. Intent & Why

AGENTS.md는 백필 형태를 2026 Q3 골드셋에 맞추라고 한다. 제재만 [`docs-dev/sanctions-format.md`](../../../docs-dev/sanctions-format.md)로 고정돼 있고, 일반 note·입법·동향·KASB 일정은 writer 스킬·`gold-excerpts`(발췌 소스는 아직 2023/2025)에 흩어져 있다. 작성·리뷰가 같은 체크리스트를 보게 하려면 **형식 규칙과 Pass/Fail이 family 단위 SSOT**로 있어야 한다.

---

## 2. Non-Goals

- `lint_public_body.py` / `validate_content.py`에 일반 note 구조 검사 신설 (후속)
- Q3 `<!-- no_summary -->` 타입 DoD
- `docs/quality-updates/**` 분기 본문·Appendix·백필 연도 콘텐츠 수정
- 큐레이션 마커(`<!-- skip -->`, `<!-- source -->`) 대량 변경
- `sanctions-format.md` 본문 규칙 재작성(Pass/Fail 절 추가만)
- nested-info(지적사례 접기)·serious-fraud 등 Q3 미출현 타입의 신규 DoD(기존 발췌는 유지·표시만)

---

## 3. Architecture

```text
2026 Q3 goldset md
        │
        ▼
docs-dev/summary-formats/README.md   ← 기관×절 → family 매핑 · 리뷰 사용법 · 공통 3축
        │
        ├── general-note.md
        ├── legislative.md
        ├── trend-briefing.md
        ├── kasb-schedule.md
        └── (link) ../sanctions-format.md   ← 이동 없음; Pass/Fail 절 추가
                │
                ▼
.claude/skills/.../gold-excerpts.md (+ checklist)  ← Q3 앵커
                │
                ▼
SKILL.md REFERENCE + docs/project/README.md SSOT 표
```

`docs-dev/`는 MkDocs 비공개(기존 제재 문서와 동일).

---

## 4. Family taxonomy (Q3 note 기준)

| Family | Q3 대상 (note 있는 절만) | 문서 |
|--------|--------------------------|------|
| general-note | FSS/FSC 보도, FSC 고시/공고/훈령, KICPA 알림마당·감사인증기준, KASB 소통광장 공지 — style-A(괄호) / style-B(볼드-콜론) | `general-note.md` |
| legislative | FSS 세칙제·개정예고, FSC 입법예고/규정변경예고 | `legislative.md` |
| trend-briefing | FSS 회계감독 동향자료(다중 `<!-- source -->` + 주제 불릿) | `trend-briefing.md` |
| kasb-schedule | KASB 주요일정 (`□ 의결` / `□ 보고`) | `kasb-schedule.md` |
| sanctions | FSC 제재 의결 (Type A/B 표, 안건 분석, 위원 논의) | [`docs-dev/sanctions-format.md`](../../../docs-dev/sanctions-format.md) |

매핑 SSOT는 README. 스킬·운영 문서는 장문 복사 없이 링크만 한다.

---

## 5. Family 문서 공통 목차

`general-note` · `legislative` · `trend-briefing` · `kasb-schedule` 각 파일:

1. **목적·범위** — 다루는 기관×절, Q3 밖 확장 금지
2. **필수 구조** — 링크 줄, `!!! note` 제목, 들여쓰기, 접두어/헤더, 불릿 수, 어미, 볼드
3. **모범 앵커** — Q3 경로 + 대표 링크 제목 1~2개(전문 복붙 최소화; 발췌 본문은 `gold-excerpts`)
4. **DoD Pass/Fail** — 공통 3축 + family 전용 행
5. **비범위** — `no_summary`, 타 family, 마커 대량 변경

### 5.1 공통 리뷰 3축

기존 `gold-excerpts-checklist`와 맞춤.

| 축 | Pass | Fail 예 |
|----|------|---------|
| Format | note 문법·들여쓰기·접두어 혼용 없음·family 스키마 준수 | style-A/B 혼용, 표 열 누락, □ 헤더 누락 |
| Facts | 수치·기한·대상·금액이 원문과 일치, 추정 없음 | 반올림·추정·원문에 없는 칸 채움 |
| Tone-detail | 불릿 밀도·증류 수준이 Q3 앵커와 동급 | 원문 재현, 과소·과다 |

### 5.2 Family 전용 행

- **general-note**: A vs B 선택 일관성(점검·유의사항 나열 → B, 서사·개정 흐름 → A)
- **legislative**: 의견 제출 기한 볼드, 시행일·개정 대상 법령명 필수
- **trend-briefing**: source 마커와 주제 불릿 대응, 개요 불릿 1개
- **kasb-schedule**: `□ 의결`/`□ 보고`·빈 줄 규칙·제도명 볼드 금지
- **sanctions**: 기존 규칙 본문 + **문서 끝에 Pass/Fail 절 추가**(본문 재서술 없음). 색인은 이 파일을 sanctions family 기준으로 지정

### 5.3 리뷰 사용법 (README)

- 작성/백필 PR: 변경 링크 → 매핑으로 family 확정 → 해당 파일 §DoD만 체크
- 독립 리뷰 세션: 코드 수정·푸시·PR 댓글 없이 3축+전용 행만 Pass/Fail 기록 (AGENTS.md §6.3)

---

## 6. Q3 모범 앵커 (대표)

| Family | 대표 앵커 (제목 키) |
|--------|-------------------|
| general-note style-B | FSS `(26-09-03)` 감사전 재무제표 점검결과 |
| general-note style-A | FSS `(26-09-23)` 토지 공시지가 주석 공시 |
| legislative | FSS `(26-09-18)` 외부감사 규정 시행세칙 (FSC 규정변경예고는 동일 family 보조 예) |
| trend-briefing | FSS `(26-07-20)` 주권상장법인 감사인 설명회 설명자료 |
| sanctions Type B | FSC 제13차 증선위(만호제강) — `sanctions-format` 기존 예 |
| sanctions Type A | FSC `(26-07-15)` 제13차 금융위 `최종 과징금 부과` |
| kasb-schedule | KASB `(26-07-10)` 제8회 회계기준위원회 (`(26-09-04)` 제9회는 보조) |

KICPA·KASB 일반 공지는 general-note style-A로 커버. 별도 covers 태그는 필수가 아니다.

---

## 7. gold-excerpts · checklist · SKILL

### 7.1 `gold-excerpts.md`

- Full-gold **1순위**: `docs/quality-updates/2026/2026-07-01_to_2026-09-30.md`. 2023 Q2·2025 Q4는 보조 참고로 강등.
- Q3 note가 있는 family의 발췌를 Q3 앵커로 교체·추가 (style-A/B, legislative, trend-briefing, type-A/B·위원 논의 샘플, kasb-schedule).
- Q3 미출현 타입(`nested-info`, `serious-fraud` 등): **삭제하지 않고** “Q3 미출현 · 기존 발췌 유지” 표시.

### 7.2 `gold-excerpts-checklist.md`

- Excerpt ID ↔ covers 표를 위 발췌에 맞게 갱신.
- 리뷰 시 DoD family 파일과 함께 쓰도록 한 줄 안내.

### 7.3 `SKILL.md`

- 세션 고지·Full gold 경로를 Q3 우선으로.
- REFERENCE B/D/E 모범 경로·스키마가 DoD/`sanctions-format`과 어긋나면 DoD 쪽으로 맞춤.
- 제재 장문은 스킬에 두지 않고 `sanctions-format` + 분기 운영 가이드 링크 유지.
- 요약 형식 상세 SSOT: `docs-dev/summary-formats/`.

### 7.4 교차 링크

- [`docs/project/README.md`](../../project/README.md) SSOT 표: 요약 포맷 → `docs-dev/summary-formats/README.md` (스킬은 워크플로).
- AGENTS.md “2026 Q3 골드셋”에 summary-formats 경로를 넣을지는 **구현 PR에서 사용자 한 줄 확인** 후 반영(방향·규칙 교차 참조; 본 스펙은 권고만).

---

## 8. Acceptance

1. `docs-dev/summary-formats/README.md`가 기관×절→family 매핑·리뷰 사용법·공통 3축을 가진다.
2. Q3에 note 있는 모든 기관×절이 매핑에 있고, 해당 family 문서(`sanctions`는 `sanctions-format.md`)에 연결된다.
3. `general-note` · `legislative` · `trend-briefing` · `kasb-schedule` 각 파일이 §5 목차(필수 구조·Q3 앵커·Pass/Fail)를 채운다.
4. `sanctions-format.md`에 리뷰용 Pass/Fail 절이 추가되고, 기존 §1–§6 규칙 본문은 유지된다.
5. `gold-excerpts.md`가 Q3 우선이며 checklist covers가 일치한다.
6. `SKILL.md`와 `docs/project/README.md`가 summary-formats를 가리킨다.
7. 분기 본문·큐레이션 마커·비밀값 변경 없음.
8. 수정한 `docs/**/*.md`에 대해 `npm run lint:md` exit 0. (`docs-dev/`는 MkDocs·markdownlint `docs/**` 밖이면 해당 없음으로 PR에 명시.)

---

## 9. Implementation order

1. 본 스펙 커밋 → 사용자 스펙 리뷰
2. (승인 후 plan) README + family 4파일 + sanctions Pass/Fail
3. gold-excerpts · checklist · SKILL · project README (+ AGENTS 한 줄은 확인 후)
4. lint · PR

---

## 10. Definition of Done

- [ ] 스펙·summary-formats 색인·family 4문서·sanctions Pass/Fail
- [ ] gold-excerpts·checklist·SKILL·project README 정합
- [ ] Acceptance §8 전항
- [ ] 후속(린트 확대·no_summary DoD)은 Non-Goals로 명시
- [ ] PR (증거·범위·비밀값 없음)
