# 링크 요약 note 전면 펼침 (`??? note` → `!!! note`) — 설계 스펙

**날짜**: 2026-06-26  
**상태**: 구현 완료 (안 B)  
**범위**: 분기 규제 업데이트 문서·`quality-updates-writer` 스킬·관련 스크립트·운영 문서에서 **링크 요약 `??? note`를 `!!! note`로 일괄 전환**

**브레인스토밍 결정**

| 항목 | 결정 |
|------|------|
| 방안 | **안 B** — `??? note`만 `!!! note`로 전환 |
| Appendix A | **`??? info` 유지** — 전체 자료·기관별 접기 블록 |
| 중첩 info | **`??? info` 유지** — `!!! note` 내부 지적사례 목록·검색경로 등 |
| fss-review | **범위 외** — `??? quote` 1건 유지 |
| 코퍼스 | **재export** — `admonition` 필드 값 변경 반영 |

**선행·관련 spec**

- `2026-03-27-quality-updates-writer-skill-redesign.md` — REFERENCE A `!!!`/`???` note 규칙 (본 spec으로 **개정**)
- `2026-06-26-quarterly-update-list-spacing-design.md` — CSS/JS; 본 spec과 **호환** (`details` 규칙은 Appendix·중첩 info용으로 잔존)
- `2026-06-27-mcp-corpus-design.md` — `notes[].admonition` 필드; 백필 후 재export
- `2026-06-27-audit-regulatory-lens-skill-design.md` — note 읽기; `!!!`/`???` 모두 note로 취급 (동작 변화 없음)

---

## 배경

MkDocs Material에서 admonition 문법은 두 가지다.

| 문법 | 렌더 | 용도 (현재) |
|------|------|-------------|
| `!!!` | 항상 펼침 `<div class="admonition">` | 짧은 note, Type A |
| `???` | 접기 `<details>` | 긴 note, Type B, Appendix `info` |

현재 `docs/quality-updates/` 공개 콘텐츠 기준(2026-06-26 점검):

| 유형 | 건수 | 본 spec |
|------|------|---------|
| `??? note` | **84** | → `!!! note` |
| `??? info` | **73** | **유지** |
| `!!! note` | **347** | 유지 |

**문제**

| 문제 | 영향 |
|------|------|
| 요약이 접혀 있음 | 독자·HITL이 클릭 없이 핵심 사실을 읽기 어려움 |
| note 선택 규칙 복잡 | 스킬 REFERENCE A — 불릿 수·밀도·Type B별 `???`/`!!!` 분기 |
| 동일 분기 내 혼재 | gold standard(`2025-10-01_to_2025-12-31.md`)도 note 타입 혼용 |

**Appendix A를 `!!!`로 바꾸지 않는 이유**

분기 파일마다 Appendix에 **수백~수천** 필터 전 링크가 있다. 접기(`??? info`) 없이 펼치면 페이지 길이·스크롤·모바일 UX가 크게 악화된다.

---

## 목표

1. **모든 링크 요약**을 `!!! note`로 통일 — 길이·Type B 여부와 무관.
2. **Appendix A·중첩 `??? info`**는 기존 접기 UX 유지.
3. **작성 규칙 SSOT** 갱신 — writer 스킬, 분기 작업지시서, editor 완료 판정 문서.
4. **기존 16개 분기 `.md` 백필** — note 본문·들여쓰기·표 **내용 변경 없음**, 마커 줄만 치환.
5. **회귀 방지** — validate strict, pytest, mkdocs build strict, corpus `--strict` 재export.

### 비목표

- `??? info` → `!!! info` 전환 (Appendix·중첩)
- `docs/fss-review/fr2022.md`의 `??? quote` 변경
- Appendix A 구조·크롤러 수집 범위 변경
- list-spacing CSS/JS 재설계 (선택: `details` 규칙 유지 확인만)
- note 본문 재작성·요약 품질 개선
- Phase 2·nav/index 자동화

---

## 용어·범위 경계

### 전환 대상 (`??? note` → `!!! note`)

링크(`- (YY-MM-DD) […](url)`) 직후 들여쓴 **요약 note** 블록. 대표 title:

- `"주요 내용"`
- `"조사·감리결과 지적사항 및 조치내역"` (Type B)
- `"제N차 … 의결사항 요약"` (2022 레거시)
- `"뉴스 링크"` (2022 레거시)
- `"업무 관련항목"` (2022 레거시)

**치환 규칙**: 선행 공백·title 문자열 **보존**, `???` → `!!!`만 변경.

```markdown
# Before
    ??? note "조사·감리결과 지적사항 및 조치내역"

# After
    !!! note "조사·감리결과 지적사항 및 조치내역"
```

### 유지 대상 (`??? info`)

| 위치 | 예 |
|------|-----|
| Appendix A 루트 | `??? info "전체 자료 (전문가 가공 전)"` |
| Appendix A 기관 | `??? info "금융감독원"` 등 |
| `!!! note` 내부 중첩 | `??? info "2025년 상반기 … 지적사례 공개 목록"` |
| 레거시 중첩 | `??? info "참고 심사·감리 지적사례(요지)"`, `??? info "붙임 안내(검색 경로)"` |

### 적용 파일

| 경로 | 조치 |
|------|------|
| `docs/quality-updates/{year}/*.md` | `??? note` → `!!! note` (index.md 제외) |
| `.claude/skills/quality-updates-writer/SKILL.md` | REFERENCE A·체크리스트 개정 |
| `docs/project/quarterly-operations-guide.md` | Phase 1 문구 동기화 |
| `docs/project/editor-curation-workflow.md` | 완료 판정 문구 (필요 시) |
| `scripts/corpus/` | 파서·스키마 주석 (동작 유지; `admonition` 값만 백필 후 갱신) |
| `data/corpus/` | `export_corpus.py --strict` 재생성 |

### 변경 없음 (동작 확인만)

| 경로 | 이유 |
|------|------|
| `scripts/crawler/unified.py` | Appendix `??? info` 생성 — 유지 |
| `scripts/validate_content.py` | `!!!`/`???` 공통 들여쓰기 규칙 — 유지 |
| `scripts/source_marker_layout.py` | note 렌더 경고 — `!!! note`로 문구만 선택적 정리 |
| `docs/assets/stylesheets/extra.css` | `.admonition`·`details` 모두 처리 — 유지 |
| `scripts/editor/*` | 완료 판정이 `!!! note`/`??? note` 병기 — note는 `!!!`만 신규 생성 |

---

## 설계

### 1. 콘텐츠 백필

**대상**: `docs/quality-updates/**/*.md` (16개 분기 파일, `index.md` 제외)

**구현**

- `scripts/expand_note_admonitions.py` (신규, idempotent)
  - 정규식: 줄 시작 `(indent)(??? note "…")` → `\1!!! note "…"`
  - **`??? info`는 매칭 제외** (`note` 토큰만)
  - `--dry-run`, `--file`, `--verbose` (파일별 치환 건수)
  - exit 0 후 `docs/quality-updates/`에 `^\s*\?\?\? note` **0건** 확인

**주의**

- 블록 **내용·들여쓰기·표·중첩 `??? info` 변경 금지**
- `<!-- skip -->`, `<!-- source: … -->`, `<!-- no_summary -->` **변경 금지**
- 백필 후 gold standard 2파일 HITL 육안 확인:
  - `2023-04-01_to_2023-06-30.md`
  - `2025-10-01_to_2025-12-31.md` (Type B·중첩 info·Appendix 혼재)

### 2. `quality-updates-writer` 스킬

**파일**: `.claude/skills/quality-updates-writer/SKILL.md`

| 변경 | 내용 |
|------|------|
| REFERENCE A 표 | `??? note` 행 **삭제**; 모든 note → `!!! note` |
| Type B | `??? note "조사·…"` → **`!!! note "조사·…"`** |
| 길이 규칙 인용 | “과도하게 길면 `???`” 문단 **삭제** |
| REFERENCE E | `!!! note` + 중첩 `??? info` — **유지** (변경 없음) |
| REFERENCE G | Appendix `??? info` — **유지** |
| 품질 체크리스트 | “`!!!`/`???` 선택 적합” → “**모든 note는 `!!! note`**” |
| Phase 0 완료 표 | `!!! note` / `??? note` → **`!!! note`** |

**신규 REFERENCE A (적용 후)**

| 상황 | 문법 |
|------|------|
| 일반·긴 요약·Type B·Type A | **`!!! note "…"`** (title만 유형별 상이) |
| Appendix·부가 목록 | **`??? info "…"`** (REFERENCE G·E) |

### 3. 운영·편집 문서

| 파일 | 변경 |
|------|------|
| `docs/project/quarterly-operations-guide.md` | Phase 1 “`??? note` 요약” → “**`!!! note` 요약**” |
| `docs/project/editor-curation-workflow.md` | 완료: “`!!! note` / `??? note`” → “**`!!! note`** (레거시 `??? note`는 백필 후 없음)” |

`README.md`·`AGENTS.md`: admonition 선택 언급 없으면 **변경 생략**.

### 4. 검증·코퍼스

| 단계 | 명령 |
|------|------|
| 치환 잔존 검사 | `rg '^\s*\?\?\? note' docs/quality-updates/` → 0 |
| info 유지 검사 | Appendix 파일 1건 이상 `??? info` 존재 확인 |
| 콘텐츠 | `python scripts/validate_content.py --strict` |
| 테스트 | `cd scripts && python -m pytest tests/ -q` |
| 사이트 | `mkdocs build --strict` |
| 코퍼스 | `python scripts/export_corpus.py --strict` |

**선택 (권장)**: `validate_content.py`에 `--strict` 시 `docs/quality-updates/`에서 `??? note` 발견 → **error** 규칙 추가 (회귀 방지). `??? info`는 허용.

**코퍼스 영향**: `notes[].admonition`이 `"???"` → `"!!!"`로 바뀐 레코드만 갱신. MCP tool·audit-regulatory-lens는 note **내용** 기준이므로 동작 동일.

### 5. CSS·렌더링

`2026-06-26-quarterly-update-list-spacing-design.md` 규칙:

```css
.md-content__inner.quarterly-update ul > li > :is(.admonition, details)
```

- note 전환 후: 더 많은 항목이 `.admonition`으로 렌더 → **기존 CSS로 처리됨**
- Appendix·중첩: `details` 규칙 **계속 필요**
- **CSS 변경 필수 아님**; 백필 후 `mkdocs serve`로 2025 Q4·2026 Q1 샘플 간격 육안 확인

### 6. 레거시·일회성 스크립트

| 파일 | 조치 |
|------|------|
| `scripts/apply_q1_2026_summaries.py` | DEPRECATED — `_block()`의 `folded`/`???` 분기 제거 또는 주석 “spec 후 `!!!` only” |
| `scripts/patch_2023_q1_md.py` | 일회성; **수정 생략** (아카이브) |

---

## 완료 조건 (Definition of Done)

- [ ] `docs/quality-updates/`에 `??? note` **0건**
- [ ] Appendix·중첩 `??? info` **73건± 유지** (분기당 ~5 info 블록)
- [ ] `quality-updates-writer` REFERENCE A·체크리스트 반영
- [ ] `quarterly-operations-guide.md` Phase 1 문구 반영
- [ ] (선택) `validate_content.py` `??? note` 금지 규칙
- [ ] `cd scripts && python -m pytest tests/ -q` 통과
- [ ] `python scripts/validate_content.py --strict` 통과
- [ ] `mkdocs build --strict` 통과
- [ ] `python scripts/export_corpus.py --strict` 통과
- [ ] HITL: gold standard 2파일 + Appendix 1파일 브라우저 확인

---

## 리스크·완화

| 리스크 | 완화 |
|--------|------|
| 긴 Type B note로 페이지 스크롤 증가 | note만 대상; Appendix 접기 유지. list-spacing CSS 이미 적용 |
| Agent가 구 규칙으로 `??? note` 생성 | 스킬 + validate 금지 규칙 |
| 중첩 `??? info` 오치환 | 스크립트는 `??? note` 토큰만 매칭 |
| 코퍼스·MCP stale | 백필 직후 `export_corpus.py --strict` CI/로컬 실행 |

---

## 구현 순서 (plan 작성용)

1. `scripts/expand_note_admonitions.py` + 단위 테스트 (`test_expand_note_admonitions.py`)
2. `--dry-run` → HITL diff 확인 → 일괄 백필
3. writer 스킬·운영 문서 갱신
4. (선택) `validate_content.py` 회귀 규칙
5. corpus re-export
6. pytest / validate / mkdocs strict
7. `docs/superpowers/plans/2026-06-26-admonition-expand-notes.md` 체크리스트

---

## 참고: 현재 note 혼용 예 (gold standard)

`2025-10-01_to_2025-12-31.md` — 동일 섹션에서 `??? note`(37행)와 `!!! note`(50행) 혼재.  
백필 후 해당 분기 note는 **전부 `!!!`**; 67행 중첩 `??? info`는 **유지**.
