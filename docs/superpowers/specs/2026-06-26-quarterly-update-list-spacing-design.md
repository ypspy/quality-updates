# 분기 규제 동향 문서 리스트 간격 정규화 설계 스펙

**날짜**: 2026-06-26  
**상태**: 승인됨  
**범위**: MkDocs로 렌더링되는 **분기별 규제 업데이트 문서**(`docs/quality-updates/{year}/*.md`) 전체의 링크·요약 리스트 **항목 간 여백** 일관화

**브레인스토밍 결정 (개정)**: 초안의 `#### 보도자료` 한정 범위를 **동향 문서 전체 항목**으로 확대. 안 A 변형 — **페이지 스코프 CSS** + URL 기반 클래스 부여 (보도자료 제목 매칭 JS 불필요).

**대체 파일**: `2026-06-26-press-release-list-spacing-design.md` (보도자료 한정 초안, 본 스펙으로 대체)

---

## 배경

분기 규제 업데이트 문서는 섹션마다(`#### 보도자료`, `#### 회계감독 동향자료`, `#### 주요일정`, `#### 소통광장 - 보도자료` 등) 동일한 항목 패턴(`- (YY-MM-DD) [제목](url)` + 선택적 `!!! note`)을 쓰지만, 요약 유무에 따라 **렌더 DOM이 달라** 인접 불릿 사이 여백이 들쭉날쭉하다.

| 유형 | 마크다운 | 렌더 DOM (요약) | 여백 영향 |
|------|----------|-----------------|-----------|
| 요약 없음 | 링크 + `<!-- no_summary -->` | `<li>…<a>…</a></li>` | `li { margin-bottom: 0.5em }` |
| 요약 있음 | 링크 아래 들여쓴 `!!! note` / `??? note` | `<li><p>…</p><div class="admonition">…` | `li p { margin: 0.5em 0 }` + `.admonition { margin: 1.5625em 0 }` |

Material for MkDocs 기본값:

- `.md-typeset ul li { margin-bottom: .5em }`
- `.md-typeset ul li p { margin: .5em 0 }`
- `.md-typeset .admonition, .md-typeset details { margin: 1.5625em 0 }` (admonition 계열)

현재 `docs/assets/stylesheets/extra.css`에는 리스트·admonition 여백 규칙이 없다.

### 초안 대비 범위 변경

| 구분 | 초안 (보도자료 한정) | 본 스펙 |
|------|---------------------|---------|
| 적용 섹션 | `#### 보도자료` 직후 `ul`만 | 분기 문서 내 **모든** `ul > li` 항목 |
| 식별 방식 | h4 제목 텍스트 JS 매칭 | URL 경로로 페이지 스코프 |
| 포함 | FSS·FSC 보도자료 | 보도자료·동향자료·고시·주요일정·탭 요약 불릿·Appendix 등 |
| 제외 | 한공회 공지, ES 탭 등 | 홈·개요·fss-review |

---

## 목표

1. 분기 동향 문서에서 **인접 리스트 항목** 사이 시각적 여백을 일정하게 한다 (요약 note·details 유무와 무관).
2. **기존 분기 `.md` 파일을 수정하지 않는다** (백필 없음).
3. `quality-updates-writer` 스킬·`validate_content.py` **변경 없음**.

### 비목표

- 항목 **높이** 동일화 (콘텐츠량·표·접기 블록 차이는 유지).
- `docs/quality-updates/index.md`(개요), `docs/index.md`(홈), `docs/fss-review/**`.
- 편집기(`editor.css`) 미리보기 — MkDocs 사이트만.
- 마크다운 구조 통일(스킬·백필) — 표현 계층만 수정.

---

## 설계

### 아키텍처

```
마크다운 (변경 없음)
    → MkDocs/Material 렌더
    → extra.js: 분기 문서 URL이면 article에 .quarterly-update
    → extra.css: .quarterly-update .md-typeset ul > li 여백 정규화
```

### 1. 페이지 스코프 — `docs/assets/javascripts/extra.js`

**역할**: 분기별 규제 업데이트 페이지의 `article.md-content__inner`에 `quarterly-update` 클래스 부여.

**매칭 조건** (둘 중 하나):

```javascript
/\/quality-updates\/\d{4}\//.test(location.pathname)
```

예: `/quality-updates/2026/2026-01-01_to_2026-03-31/`

**제외**: `/quality-updates/` 개요만 있는 경로(연도 하위 없음), 홈, fss-review.

**로직**:

1. 조건 충족 시 `document.querySelector('.md-content__inner')?.classList.add('quarterly-update')`.
2. idempotent (이미 있으면 스킵).
3. MkDocs Material **navigation.instant**: `document$` 구독 시 재실행.

JS는 **페이지 판별만** 담당. 섹션·제목별 분기 없음.

### 2. CSS — `docs/assets/stylesheets/extra.css`

**스코프**: `.md-content__inner.quarterly-update .md-typeset`

**대상**: 문서 내 모든 `ul > li` (보도자료·동향자료·주요일정·Executive Summary 탭 불릿·note 내부 불릿·Appendix 리스트 포함).

**규칙 (초안 값 — 구현 시 `mkdocs serve`로 튜닝)**:

| 선택자 | 속성 | 목적 |
|--------|------|------|
| `… ul > li` | `margin-bottom: 0.75em` | 인접 항목 간 고정 간격 |
| `… ul > li:last-child` | `margin-bottom: 0` | 리스트 말미 |
| `… ul > li > p` | `margin: 0` | 요약 있을 때 `<p>` 래퍼 여백 제거 |
| `… ul > li > :is(.admonition, details)` | `margin: 0.5em 0 0` | note·접기 블록 상단 과다 여백 축소 |
| `… ul > li > :is(.admonition, details):last-child` | `margin-bottom: 0` | 항목 하단 여백을 `li margin-bottom`에 일원화 |

**중첩 리스트**: note·탭 **내부** `ul > li`도 동일 규칙 적용 → 문서 전반 불릿 리듬 통일 (의도적).

**의도적으로 건드리지 않음**:

- `ol > li` (분기 문서에서 거의 미사용; 필요 시 추후 추가).
- `H3 { margin-top: 40px; }` 등 기존 `extra.css` 규칙.
- 홈·개요·fss-review 페이지.

### 3. 인쇄·다크 모드

- 여백만 조정; 별도 `@media print` 규칙 불필요.
- 테마 변수 미사용 → 라이트/다크 동일.

---

## 검증

### 자동

```bash
mkdocs build --strict
cd scripts && python -m pytest tests/ -q
python scripts/validate_content.py --strict
```

### 수동 (HITL)

`mkdocs serve` 후 분기 문서에서 **서로 다른 섹션 유형**을 확인:

| 페이지 | 확인 섹션 |
|--------|-----------|
| `2026-01-01_to_2026-03-31` | FSS 보도자료(요약 혼재), FSC 동향자료, KASB 주요일정 |
| `2025-10-01_to_2025-12-31` | gold standard — ES 탭, FSS·FSC 보도자료, Type B `??? note` |
| `2024-10-01_to_2024-12-31` | gold standard — 회귀 |

**체크리스트**:

- [ ] 요약 없는 링크 ↔ 요약 있는 링크 사이 간격이 **섹션 종류와 무관하게** 균일해 보임
- [ ] `!!!` / `???` note·표 포함 항목 전후 간격 유지
- [ ] Executive Summary 탭 내 불릿 간격이 본문과 어울림
- [ ] Appendix A( details 내부) 리스트가 과도하게 붙거나 벌어지지 않음
- [ ] **홈·규제 업데이트 개요** 페이지 리스트는 변경 없음
- [ ] 라이트/다크, 모바일(≤44.9375em), `navigation.instant` 페이지 전환

---

## 구현 체크리스트

- [x] `extra.js` — URL 기반 `.quarterly-update` + `document$` 훅
- [x] `extra.css` — 스코프 규칙 추가 (기존 주석·섹션 스타일 유지)
- [ ] 수동 검증 3페이지
- [x] `docs/superpowers/README.md` specs 테이블에 본 스펙 행 추가
- [x] 초안 `2026-06-26-press-release-list-spacing-design.md` 삭제 또는 README에서 superseded 표기

---

## 리스크·완화

| 리스크 | 완화 |
|--------|------|
| note **내부** 불릿까지 간격 변경 | 전체 통일이 목표; 과밀/과소 시 `em` 값만 튜닝 |
| Appendix·중첩 `details` 레이아웃 | gold standard 3페이지에서 Appendix 확인 |
| Material 업그레이드 | 배포 전 검증 체크리스트 재실행 |
| `navigation.instant` | `document$` 구독 필수 |
| FOUC | 여백 차이가 작아 실무상 허용 |

---

## 승인 후 다음 단계

1. 사용자 spec 검토·승인  
2. `writing-plans` → `docs/superpowers/plans/2026-06-26-quarterly-update-list-spacing.md`  
3. 구현 → 검증 명령 실행
