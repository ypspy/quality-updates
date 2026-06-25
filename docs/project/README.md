# 프로젝트 메타 문서 지도

Quality Updates **저장소 운영·개발·Agent**용 문서 목록입니다.  
공개 사이트 콘텐츠(`docs/quality-updates/`)와 설계 아카이브(`docs/superpowers/`)를 구분한다.

> `docs/project/`와 `docs/superpowers/`는 MkDocs **exclude** 대상 — `mkdocs serve` 사이드바에 나오지 않는 것이 정상이다.

---

## Agent

| 문서 | 용도 |
|------|------|
| [AGENTS.md](../../AGENTS.md) | **Agent 진입점** — 라우팅, 보완 기획 프롬프트 템플릿 |
| [.claude/skills/quality-updates-writer/SKILL.md](../../.claude/skills/quality-updates-writer/SKILL.md) | 분기 요약·스킵 제거 (RIGID) |

---

## 사람 — 온보딩·기여

| 문서 | 용도 |
|------|------|
| [README.md](../../README.md) | 클론, 의존성, 스크립트, 프로젝트 구조 |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | PR, 커밋 규칙, CI 체크리스트 |

---

## 분기 운영 (SSOT) — `docs/project/`

| 문서 | 용도 |
|------|------|
| [quarterly-operations-guide.md](quarterly-operations-guide.md) | **분기 파이프라인** — Agent/HITL, Phase 1~5, 품질 게이트 |
| [editor-curation-workflow.md](editor-curation-workflow.md) | **편집기** — 마커, skip, prepare_deploy |

README·CONTRIBUTING·AGENTS.md의 운영·큐레이션 요약은 위 문서를 정본으로 한다.

---

## 설계·구현 이력

| 문서 | 용도 |
|------|------|
| [superpowers/README.md](../superpowers/README.md) | specs/plans 색인 |
| [IMPLEMENTATION_LOG.md](../../IMPLEMENTATION_LOG.md) | 과거 개선 작업 로그 (2026-06 이후는 superpowers spec 우선) |

---

## 공개 사이트 콘텐츠

| 경로 | 용도 |
|------|------|
| `docs/quality-updates/` | 분기별 규제 업데이트 (MkDocs nav 등록) |
| `docs/fss-review/` | 품질관리감리 |
| `docs/index.md` | 홈 |

---

## 주제별 단일 정본 (SSOT)

| 주제 | 정본 |
|------|------|
| 분기 운영 | `docs/project/quarterly-operations-guide.md` |
| 편집기 | `docs/project/editor-curation-workflow.md` |
| 요약 포맷 | `quality-updates-writer/SKILL.md` |
| Agent 기획 | `AGENTS.md` |
| 로컬 개발 | `README.md` |
| PR/CI | `CONTRIBUTING.md` |
