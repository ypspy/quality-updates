# Quality Updates 문서 정리·Agent 진입점 설계 스펙

**날짜**: 2026-06-25  
**상태**: 승인됨  
**범위**: 메타 문서 IA 정립, 중복 축소, `AGENTS.md` Agent 프롬프트 가이드, MkDocs exclude

**선행 스펙**: `docs/superpowers/specs/2026-03-24-doc-organization-design.md` (AGENT_* → 스킬 통합, 완료)

---

## 배경

플랫폼 통합(crawler, prepare_deploy, editor Blueprint) 및 `quarterly-operations-guide.md` 추가 이후 메타 문서가 다시 분산되었다.

| 문제 | 예시 |
|------|------|
| 워크플로 3중 서술 | README, CONTRIBUTING, 작업지시서 |
| Agent 진입점 없음 | 분기 요약 스킬만 존재, **프로젝트 보완·기획** 프롬프트 미문서화 |
| superpowers 미색인 | specs/plans 12파일, 발견 어려움 |
| MkDocs 오염 | 내부·설계 문서가 빌드·검색에 포함 |
| 유지보수 로그 구식 | `IMPLEMENTATION_LOG.md` (validate continue-on-error 등) |

---

## 목표

1. **계층 + Agent 허브** — 파일 대량 병합 없이 역할·진입점 정리  
2. **단일 정본(SSOT)** — 주제별 canonical 문서 지정, 나머지는 요약+링크  
3. **`AGENTS.md`** — Agent용 프로젝트 점검·보완 기획 프롬프트 템플릿  
4. **내부 문서 MkDocs 제외** — `project/`, `superpowers/` 검색·nav 비포함

**범위 외**

- `docs/quality-updates/` 분기 콘텐츠 백필·편집  
- superpowers 파일 물리 이동(경로 유지, README 색인만)  
- 1차에서 `quarterly-operations-guide.md` 경로 이동(과도기: `docs/project/README.md`가 허브)

---

## 정보 구조 (IA)

```
quality-updates/
├── AGENTS.md                         # [신규] Agent 진입·프롬프트 템플릿
├── README.md                         # 사람 온보딩 (워크플로 요약+링크)
├── CONTRIBUTING.md                   # PR·CI·스타일 (운영 상세는 링크)
│
├── docs/
│   ├── project/                      # [신규] 메타·운영 (MkDocs exclude)
│   │   └── README.md                 # 문서 지도
│   ├── quarterly-operations-guide.md # [유지] 운영 SSOT
│   ├── editor-curation-workflow.md   # [유지] 편집기 SSOT
│   ├── superpowers/                  # [유지] 설계 이력
│   │   ├── README.md                 # [신규] specs/plans 색인
│   │   ├── specs/
│   │   └── plans/
│   └── quality-updates/              # 공개 콘텐츠 (변경 없음)
│
├── .claude/skills/quality-updates-writer/  # 분기 요약 RIGID (유지)
└── IMPLEMENTATION_LOG.md             # [갱신] 또는 project/MAINTENANCE.md
```

---

## 단일 정본 (SSOT)

| 주제 | 정본 | 다른 문서 |
|------|------|-----------|
| 분기 운영·HITL/Agent | `docs/quarterly-operations-guide.md` | README·CONTRIBUTING = 요약+링크 |
| 편집기·마커 | `docs/editor-curation-workflow.md` | 작업지시서 Phase 2 = 링크 |
| 분기 요약 포맷 | `.claude/skills/quality-updates-writer/SKILL.md` | 작업지시서 Phase 3 = 링크 |
| 로컬 개발·스크립트 | `README.md` | — |
| PR·린트·CI | `CONTRIBUTING.md` | — |
| 기능 설계 | `docs/superpowers/specs/` | plans = 구현 체크리스트 |
| **Agent 프로젝트 기획** | **`AGENTS.md`** | brainstorming → spec → plan |

---

## AGENTS.md 설계

### 섹션

1. **Quick routing** — 작업 유형 → 읽을 문서·스킬  
2. **Document map** — `docs/project/README.md` 링크  
3. **Prompt templates** — 복사용 (아래)  
4. **Constraints** — 스킬 우회 금지, spec 없이 대규모 변경 금지 등

### 프롬프트 템플릿 (필수 3종)

**A. 프로젝트 점검 + 보완 기획**

```markdown
프로젝트를 점검해줘. /brainstorming

범위: [크롤러 / CI / 문서 / 편집기 / 전체]
목표: [한 문장]
제외: [명시]
참고: README, docs/project/README.md, docs/superpowers/specs/ 최신
산출: 현황 평가 + 2~3안 + 승인 후 spec (docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md)
```

**B. 승인된 스펙 기반 구현**

```markdown
@docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md 기준으로
구현 계획 작성 후 Subagent-Driven(또는 executing-plans)으로 실행.
범위 외 변경 금지. 완료 시 pytest, validate --strict, mkdocs build --strict.
```

**C. 문서 정리·IA**

```markdown
문서 중복·진입점을 점검하고 IA 정리안을 /brainstorming 해줘.
SSOT 원칙, AGENTS.md 허브, MkDocs exclude 반영. 구현 전 spec 승인.
```

### 작업 유형 라우팅

| 유형 | 트리거 예 | 1차 문서 | 워크플로 |
|------|-----------|----------|----------|
| 분기 요약 | "Q2 요약" | `quality-updates-writer` SKILL | SUMMARIZE |
| 분기 운영 | "이번 분기 올리기" | `quarterly-operations-guide.md` | crawl→editor→skill |
| 프로젝트 기획 | "통합 방안", "점검" | `AGENTS.md` + `/brainstorming` | spec → plan → 구현 |
| 버그/CI | "테스트 실패" | `CONTRIBUTING.md` 테스트 절 | 직접 수정 |

---

## docs/project/README.md

메타 문서 지도 표:

| 문서 | 독자 | 용도 |
|------|------|------|
| `AGENTS.md` | Agent | 기획·라우팅·프롬프트 |
| `README.md` | 개발자 | 온보딩 |
| `CONTRIBUTING.md` | 기여자 | PR |
| `quarterly-operations-guide.md` | 운영자·HITL | 분기 파이프라인 |
| `editor-curation-workflow.md` | 운영자 | 편집기 |
| `superpowers/README.md` | 개발·Agent | 설계 이력 |
| `IMPLEMENTATION_LOG.md` | 유지보수 | 변경 로그 |

---

## docs/superpowers/README.md

- specs: 날짜순 표 (파일명, 제목 한 줄, 상태)  
- plans: 동일  
- “새 spec 작성 규칙”: `YYYY-MM-DD-<topic>-design.md`, brainstorming 승인 후 커밋

---

## MkDocs exclude

`mkdocs.yml` `exclude_docs`에 추가:

```yaml
exclude_docs: |
  **/*.bak
  project/**
  superpowers/**
```

공개 사이트 검색·nav에서 내부·설계 문서 제외.  
`quarterly-operations-guide.md`, `editor-curation-workflow.md`는 1차 **exclude하지 않음** (선택적 공개 유지). 2차에서 `docs/project/`로 이동 시 함께 exclude.

---

## README·CONTRIBUTING 변경 원칙

- **README** `분기 운영 워크플로`: 표·mermaid 유지, 상세는 작업지시서 링크  
- **CONTRIBUTING** `콘텐츠 추가 절차`: 단계 번호 유지, Agent/HITL 표는 작업지시서로 위임  
- 중복 체크리스트·Phase 설명 **삭제하지 말고** “→ [작업지시서](...)” 한 줄로 대체

---

## IMPLEMENTATION_LOG 갱신

- validate `continue-on-error` 제거, pytest job, platform hardening 반영  
- 또는 상단에 “2026-06 이후는 `docs/superpowers/specs/` 참조” 안내 후 최신 섹션만 유지

---

## 구현 체크리스트

- [ ] `AGENTS.md` (루트)
- [ ] `docs/project/README.md`
- [ ] `docs/superpowers/README.md`
- [ ] README·CONTRIBUTING 링크화·중복 축소
- [ ] `mkdocs.yml` exclude_docs
- [ ] `IMPLEMENTATION_LOG.md` 갱신
- [ ] `README.md` 프로젝트 트리에 `AGENTS.md`, `docs/project/` 반영

---

## 리스크

| 리스크 | 완화 |
|--------|------|
| 깨진 상대 링크 | `docs/project/README.md`에서 canonical URL만 사용 |
| Agent가 AGENTS.md 미참조 | README 상단·CONTRIBUTING에 “Agent는 AGENTS.md” 한 줄 |
| exclude 후 로컬 미리보기 혼란 | project/superpowers는 `mkdocs serve`에 안 나옴이 정상 — README에 명시 |

---

## 개정 이력

| 날짜 | 내용 |
|------|------|
| 2026-06-25 | 초판 — brainstorming 승인 |
