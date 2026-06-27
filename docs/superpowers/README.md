# Superpowers — 설계 스펙·구현 계획 아카이브

`/brainstorming`으로 승인한 설계(spec)와 `writing-plans`로 작성한 구현 계획(plan)을 보관한다.  
**MkDocs 사이트 nav·검색에는 포함되지 않는다** (`mkdocs.yml` exclude).

새 spec 작성 규칙: `specs/YYYY-MM-DD-<topic>-design.md`  
Agent 진입·프롬프트: [AGENTS.md](../../AGENTS.md)

---

## Specs (설계)

| 날짜 | 파일 | 요약 |
|------|------|------|
| 2026-06-26 | [chronological-main-body-design.md](specs/2026-06-26-chronological-main-body-design.md) | 본문 과거→현재 정렬, Appendix 크롤 순 유지 |
| 2026-06-26 | [admonition-expand-notes-design.md](specs/2026-06-26-admonition-expand-notes-design.md) | 링크 요약 `??? note` → `!!! note` (Appendix `??? info` 유지) |
| 2026-06-27 | [audit-regulatory-lens-skill-design.md](specs/2026-06-27-audit-regulatory-lens-skill-design.md) | Planning/Execution/Reporting 감사 규제 렌즈 스킬 |
| 2026-06-27 | [mcp-corpus-design.md](specs/2026-06-27-mcp-corpus-design.md) | Corpus export + 로컬 stdio + Hosted MCP |
| 2026-06-26 | [remove-phase2-summaries-design.md](specs/2026-06-26-remove-phase2-summaries-design.md) | Phase 2(ES·기관별·시사점) 제거, MCP 코퍼스 정규화 |
| 2026-06-26 | [quarterly-update-list-spacing-design.md](specs/2026-06-26-quarterly-update-list-spacing-design.md) | 분기 동향 문서 리스트 항목 간격 (extra.css/js) |
| 2026-06-25 | [doc-organization-design.md](specs/2026-06-25-doc-organization-design.md) | 문서 IA, AGENTS.md, MkDocs exclude |
| 2026-06-25 | [platform-hardening-design.md](specs/2026-06-25-platform-hardening-design.md) | 크롤러 통합, CI, prepare_deploy, editor 분리 |
| 2026-06-25 | [crawler-integration-design.md](specs/2026-06-25-crawler-integration-design.md) | crawl.py, scripts/crawler (P1 상세) |
| 2026-06-25 | [kasb-schedule-crawler-design.md](specs/2026-06-25-kasb-schedule-crawler-design.md) | KASB 주요일정(calListA) 리스트 크롤 |
| 2026-03-27 | [quality-updates-writer-skill-redesign.md](specs/2026-03-27-quality-updates-writer-skill-redesign.md) | 스킬 Superpowers화 |
| 2026-03-25 | [editor-pdf-picker-design.md](specs/2026-03-25-editor-pdf-picker-design.md) | PDF 피커 |
| 2026-03-24 | [quality-updates-editor-design.md](specs/2026-03-24-quality-updates-editor-design.md) | 큐레이션 편집기 |
| 2026-03-24 | [doc-organization-design.md](specs/2026-03-24-doc-organization-design.md) | AGENT_* → 스킬 통합 (완료) |

---

## Plans (구현)

| 날짜 | 파일 | 요약 |
|------|------|------|
| 2026-06-27 | [mcp-corpus.md](plans/2026-06-27-mcp-corpus.md) | Corpus export + MCP stdio/HTTP |
| 2026-06-27 | [audit-regulatory-lens-skill.md](plans/2026-06-27-audit-regulatory-lens-skill.md) | 감사 규제 렌즈 ADVISORY 스킬 |
| 2026-06-26 | [admonition-expand-notes.md](plans/2026-06-26-admonition-expand-notes.md) | `??? note` → `!!! note` 백필 |
| 2026-06-26 | [remove-phase2-summaries.md](plans/2026-06-26-remove-phase2-summaries.md) | Phase 2(ES·기관별·시사점) 제거 |
| 2026-06-26 | [quarterly-update-list-spacing.md](plans/2026-06-26-quarterly-update-list-spacing.md) | 분기 문서 리스트 간격 CSS/JS |
| 2026-06-25 | [platform-hardening.md](plans/2026-06-25-platform-hardening.md) | P1~P4 구현 체크리스트 |
| 2026-03-27 | [quality-updates-writer-skill-redesign.md](plans/2026-03-27-quality-updates-writer-skill-redesign.md) | 스킬 재작성 |
| 2026-03-25 | [editor-source-implementation-plan.md](plans/2026-03-25-editor-source-implementation-plan.md) | SOURCE 탭·CLIP |
| 2026-03-24 | [quality-updates-editor.md](plans/2026-03-24-quality-updates-editor.md) | 편집기 초기 구현 |

---

## 워크플로

```
/brainstorming → spec (specs/) → 사용자 검토 → plan (plans/) → 구현 → pytest / validate / mkdocs
```
