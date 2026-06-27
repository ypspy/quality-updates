# Phase 2 집계 요약 제거 — 설계 스펙

**날짜**: 2026-06-26  
**상태**: 승인됨  
**범위**: 분기 규제 업데이트 문서·`quality-updates-writer` 스킬·운영 문서·검증에서 **Executive Summary · 기관별 요약 · 시사점(Phase 2)** 제거

**브레인스토밍 결정**

| 항목 | 결정 |
|------|------|
| 방안 | **안 A** — Phase 2 완전 제거 + 단일 포맷 정규화 |
| 링크 note `(시사점)` | **유지** — 원문 기반 사실 bullet 접두어 (Phase 2와 구분) |
| MCP 레이어 | **범위 외** — 후속 spec (`sidecar`·MCP 서버 등) |

**선행·관/port spec**

- `2026-03-27-quality-updates-writer-skill-redesign.md` — Phase 2 정의 (본 spec으로 **대체·폐기**)
- `2026-06-25-doc-organization-design.md` — SSOT; 요약 포맷 정본 경로는 본 spec 적용 후 갱신
- `2026-06-26-quarterly-update-list-spacing-design.md` — CSS/JS만; 본 spec과 **독립** (Phase 2 탭 제거 후에도 분기 문서 `ul > li` 규칙 유효)

---

## 배경

Quality Updates는 분기별 규제 보도자료를 **크롤 → 큐레이션 → 링크별 note 요약 → MkDocs 공개** 파이프라인으로 운영한다. 2026-03 스킬 재설계 이후 **Phase 2**(Executive Summary, 기관별 요약 탭, 시사점 탭)가 SUMMARIZE 필수 산출물이 되었으나:

| 문제 | 영향 |
|------|------|
| **중복** | Phase 2는 Phase 1 링크 note의 편집적 재집계 |
| **MCP/RAG 부적합** | 해석·테마가 섞인 상단 블록 vs 원자적 링크+note 정본 모호 |
| **운영 비용** | HITL이 “분기 테마” 등 주관 검토에 시간 소모 |
| **크롤러와 불일치** | `crawl.py`는 Phase 2 없음 → 수집 후 Agent가 별도 생성 |

**목적 확장**: 공개 정보 아카이브뿐 아니라 **MCP로 활용**할 코퍼스를 링크 단위 사실·YAML·기관 계층 중심으로 정리한다.

---

## 목표

1. **공개 산출물**에서 Phase 2 섹션 전부 제거 (기존·신규 분기 포함).
2. **파이프라인**에서 Phase 2 생성·검증·HITL 항목 제거 — SUMMARIZE = Phase 0 + Phase 1만.
3. **문서 SSOT** 갱신 — README, 분기 작업지시서, AGENTS, `docs/quality-updates/index.md`.
4. **회귀 방지** — `validate_content.py`에 Phase 2 금지 규칙 추가.
5. **Gold standard** 교체 — Phase 2 없는 분기 파일 기준.

### 비목표

- 링크 note 내 `(시사점)`·`(유의사항)` 등 **Phase 1 접두어** 변경
- Appendix A 구조·역할 변경
- MCP 서버·JSON sidecar·색인 API (후속 spec)
- `docs/fss-review/` 포맷 변경
- mkdocs nav/index 자동화

---

## 용어·범위 경계

### 제거 대상 (Phase 2)

문서 **상단**에 위치하는 다음 블록 전체:

```markdown
## Executive Summary          (또는 ### Executive Summary)
…
#### 기관별 요약
!!! success ""
    === "금융감독원" …
    === "금융위원회" …
    …
#### 시사점
!!! success ""
    === "기업" …
    === "감사인" …
---
```

**레거시 동등 블록** (2022):

```markdown
### 요약
- 기간 : …
- 주요 사항 …
```

### 유지 대상

| 항목 | 예 |
|------|-----|
| YAML front matter | `title`, `period`, `agencies` … |
| 4기관 본문 섹션 | `## 금융감독원` → `#### 보도자료` → 링크 |
| Phase 1 note | `!!! note`, Type A/B 표, `(시사점)` bullet |
| Appendix A | 크롤러 전체 목록 |
| 큐레이션 마커 | `<!-- skip -->`, `<!-- source: … -->` (배포 전 제거) |

### `(시사점)` 구분

- **제거**: `#### 시사점` 탭 아래 기업·감사인 **전향적 해석** 불릿
- **유지**: 개별 링크 note의 `- (시사점) …` — 금감원 등 원문 “분석 및 시사점”에서 추출한 **사실 요약**

---

## 목표 문서 구조 (정규 포맷)

크롤러 산출물과 동일 — front matter 직후 **첫 `##` = 기관명**:

```markdown
---
title: …
period_label: YYYY-QN
…
---

## 금융감독원

#### 보도자료

- (YY-MM-DD) [제목](URL)

    ??? note "주요 내용"
        - (개요) …
        - (시사점) …   ← 유지 가능

---

## 금융위원회
…

## Appendix A. Complete List of Retrieved Items (Unfiltered)
…
```

**Gold standard (적용 후)**

- `docs/quality-updates/2023/2023-04-01_to_2023-06-30.md` (이미 Phase 2 없음)
- `docs/quality-updates/2025/2025-10-01_to_2025-12-31.md` (Phase 2 제거 후, note 품질 기준)

---

## 설계

### 1. 콘텐츠 백필

**대상**: `docs/quality-updates/{year}/*.md` (index.md 제외)

| 파일 | Phase 2 | 조치 |
|------|:-------:|------|
| 2022/2022-12-15_to_2023-04-03.md | `### 요약` | 요약 블록 삭제 |
| 2023/2023-01-01_to_2023-03-31.md | ES | 삭제 |
| 2023/2023-04-01_to_2023-06-30.md | 없음 | 변경 없음 |
| 2023/2023-07-01_to_2023-09-30.md | ES | 삭제 |
| 2023/2023-10-01_to_2023-12-31.md | ES | 삭제 |
| 2024/*.md (4분기) | ES | 삭제 |
| 2025/*.md (4분기) | ES | 삭제 |
| 2026/2026-01-01_to_2026-03-31.md | ES | 삭제 |

**구현 방식**

- `scripts/strip_phase2_summaries.py` (신규, 일회성·재실행 가능)
  - front matter 종료(`---`) 이후 ~ 첫 `## 금융감독원`(또는 `### 금융감독원`) 직전까지 Phase 2 패턴 제거
  - `Executive Summary` / `기관별 요약` / `시사점` / `### 요약` 헤더 및 연결 admonition·구분선 정리
  - `--dry-run`, `--file` 지원
- HITL: 2025 Q4·2026 Q1 샘플 diff 육안 확인 후 일괄 적용

**주의**

- 본문·Appendix 내용·링크 note **수정 금지** (Phase 2 구간만 삭제)
- 헤더 레벨 불일치(`##` vs `###` 기관)는 **별도 정규화 범위 외** (기존 spec platform-hardening “백필 범위 외” 유지)

### 2. `quality-updates-writer` 스킬

**파일**: `.claude/skills/quality-updates-writer/SKILL.md`

| 변경 | 내용 |
|------|------|
| SUMMARIZE TaskCreate | “Phase 2: 분기 요약 생성” **삭제** |
| 프로세스 흐름도 | Phase 2 노드·엣지 제거; Phase 1 → 품질 검증 |
| `Phase 2: 분기 요약 생성` 섹션 | **전체 삭제** |
| REFERENCE F | **전체 삭제** |
| BOILERPLATE 템플릿 | ES·기관별·시사점 블록 **삭제**; 크롤러 우선 문구 유지 |
| Gold standard | `2023-04-01_to_2023-06-30.md`, `2025-10-01_to_2025-12-31.md` (제거 후) |
| 품질 체크리스트 | Phase 2·시사점 탭·ES 어미 항목 **삭제** |
| Announce 문구 | gold standard 경로 갱신 |

**SUMMARIZE 완료 정의**: 큐레이션 대상 링크에 Phase 1 note 반영 + Appendix A 보존.

**`.claude/skills/quality-updates-writer/boilerplate.md`**: DEPRECATED 주석에 “Phase 2 제거됨, SKILL.md BOILERPLATE 참조” 한 줄 추가 (본문 대규모 수정 불필요).

### 3. 일회성 스크립트 정리

| 파일 | 조치 |
|------|------|
| `scripts/apply_q1_2026_summaries.py` | Phase 2 생성 함수·상수 **삭제** 또는 파일 상단 `DEPRECATED` + README 안내 (Phase 1-only 잔존 시) |
| `scripts/patch_2023_q1_md.py` | `DEPRECATED` 주석; Phase 2 삽입 로직 제거 또는 archive |

### 4. `validate_content.py`

**신규**: `validate_no_phase2(lines, path)`

대상: `docs/quality-updates/{year}/*.md` ( `index.md` 제외 )

| 코드 | severity | 조건 |
|------|----------|------|
| `PHASE2_ES` | error | `^#{2,3}\s+Executive Summary` |
| `PHASE2_AGENCY` | error | `^#{2,4}\s+기관별 요약` |
| `PHASE2_IMPL` | error | `^#{2,4}\s+시사점` (단, 링크 제목 URL 내 “시사점”은 무관) |
| `PHASE2_LEGACY` | error | `^#{2,3}\s+요약\s*$` (2022 레거시; `index.md`·note 접두어 제외) |

**헤더 줄만** 검사 — note bullet `- (시사점)` 은 **검사하지 않음**.

**테스트**: `scripts/tests/test_validate_phase2.py` — 위반/정상 fixture.

### 5. 운영·메타 문서

| 파일 | 변경 요약 |
|------|-----------|
| `README.md` | 분기 워크플로 표 “Executive Summary, 기관별 요약, 링크별 note” → **“링크별 note”** |
| `docs/project/quarterly-operations-guide.md` | Phase 3: Phase 2 행·HITL “분기 테마” 삭제; Phase 1-only; Phase 1 체크 “ES 없음 = 정상” 유지 |
| `docs/project/README.md` | SSOT “요약 포맷” 설명: Phase 1 note |
| `docs/quality-updates/index.md` | “규제 변화 요약, 기관별 …” → “기관별 보도자료·링크별 note” |
| `AGENTS.md` | gold standard·“Executive Summary·note” 제약 → **“note 블록 형식”** |
| `docs/superpowers/README.md` | 본 spec 색인 추가 |

**CONTRIBUTING.md**: Phase 2 언급 없음 — 변경 불필요.

### 6. MCP 연계 (후속)

본 spec 적용 후 코퍼스 특성:

- **원자 단위**: `(agency, subsection, date, title, url, note_blocks[])`
- **메타**: YAML `period`, `agencies`, `tags`
- **완전성**: Appendix A

후속 spec 후보: `2026-XX-XX-mcp-corpus-design.md` — Markdown→구조화 export, MCP `resources/list`·`search_regulatory_updates` 도구.

---

## 구현 순서

```
P1  strip_phase2_summaries.py + 12개 분기 백필
P2  validate_content Phase 2 금지 + pytest
P3  quality-updates-writer SKILL.md 개정
P4  운영 문서·AGENTS·index.md
P5  legacy scripts 정리
P6  검증: pytest, validate --strict, mkdocs build --strict
```

P1→P2 순서 필수 (백필 후 validate 통과 확인).

---

## 완료 조건 (Acceptance)

- [ ] 12개 분기 파일에 `Executive Summary` / `기관별 요약` / `#### 시사점` 헤더 **없음**
- [ ] 2022 `### 요약` 블록 **없음**
- [ ] 링크 note `(시사점)` bullet **잔존** (2023 Q3 등 기존 사례 spot-check)
- [ ] `quality-updates-writer` SUMMARIZE에 Phase 2·REFERENCE F **없음**
- [ ] `python scripts/validate_content.py --strict` exit 0
- [ ] `cd scripts && python -m pytest tests/ -q` exit 0
- [ ] `mkdocs build --strict` exit 0
- [ ] `docs/project/quarterly-operations-guide.md` Phase 3가 Phase 1-only 서술

---

## 리스크·완화

| 리스크 | 완화 |
|--------|------|
| strip 스크립트가 본문 오삭제 | `--dry-run`, 첫 `## 금융감독원` 앵커; PR diff HITL |
| 외부 북마크(ES 앵커) 깨짐 | Phase 2는 nav 앵커로 쓰이지 않음; 영향 낮음 |
| 구 spec/plan과 모순 | superpowers 이력 유지; 본 spec이 **새 SSOT** |
| list-spacing spec “스킬 변경 없음” | 해당 spec은 CSS-only 완료 전제; 본 spec은 별도 track |

---

## 개정 이력

| 날짜 | 내용 |
|------|------|
| 2026-06-26 | 초안 — 브레인스토밍 안 A, 링크 note `(시사점)` 유지 |
