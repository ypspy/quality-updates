# Superpowers — 설계 스펙·구현 계획 아카이브

`/brainstorming`으로 승인한 설계(spec)와 `writing-plans`로 작성한 구현 계획(plan)을 보관한다.  
**MkDocs 사이트 nav·검색에는 포함되지 않는다** (`mkdocs.yml` exclude).

새 spec 작성 규칙: `specs/YYYY-MM-DD-<topic>-design.md`  
Agent 진입·프롬프트: [AGENTS.md](../../AGENTS.md)

---

## Specs (설계)

| 날짜 | 파일 | 요약 |
|------|------|------|
| 2026-06-25 | [doc-organization-design.md](specs/2026-06-25-doc-organization-design.md) | 문서 IA, AGENTS.md, MkDocs exclude |
| 2026-06-25 | [platform-hardening-design.md](specs/2026-06-25-platform-hardening-design.md) | 크롤러 통합, CI, prepare_deploy, editor 분리 |
| 2026-06-25 | [crawler-integration-design.md](specs/2026-06-25-crawler-integration-design.md) | crawl.py, scripts/crawler (P1 상세) |
| 2026-03-27 | [quality-updates-writer-skill-redesign.md](specs/2026-03-27-quality-updates-writer-skill-redesign.md) | 스킬 Superpowers화 |
| 2026-03-25 | [editor-pdf-picker-design.md](specs/2026-03-25-editor-pdf-picker-design.md) | PDF 피커 |
| 2026-03-24 | [quality-updates-editor-design.md](specs/2026-03-24-quality-updates-editor-design.md) | 큐레이션 편집기 |
| 2026-03-24 | [doc-organization-design.md](specs/2026-03-24-doc-organization-design.md) | AGENT_* → 스킬 통합 (완료) |

---

## Plans (구현)

| 날짜 | 파일 | 요약 |
|------|------|------|
| 2026-06-25 | [platform-hardening.md](plans/2026-06-25-platform-hardening.md) | P1~P4 구현 체크리스트 |
| 2026-03-27 | [quality-updates-writer-skill-redesign.md](plans/2026-03-27-quality-updates-writer-skill-redesign.md) | 스킬 재작성 |
| 2026-03-25 | [editor-source-implementation-plan.md](plans/2026-03-25-editor-source-implementation-plan.md) | SOURCE 탭·CLIP |
| 2026-03-24 | [quality-updates-editor.md](plans/2026-03-24-quality-updates-editor.md) | 편집기 초기 구현 |

---

## 워크플로

```
/brainstorming → spec (specs/) → 사용자 검토 → plan (plans/) → 구현 → pytest / validate / mkdocs
```
