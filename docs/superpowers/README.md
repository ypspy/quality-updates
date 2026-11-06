# Superpowers — 설계 스펙·구현 계획 아카이브

`/brainstorming`으로 승인한 설계(spec)와 `writing-plans`로 작성한 구현 계획(plan)을 보관한다.  
**MkDocs 사이트 nav·검색에는 포함되지 않는다** (`mkdocs.yml` exclude).

새 spec 작성 규칙: `specs/YYYY-MM-DD-<topic>-design.md`  
Agent 진입·프롬프트: [AGENTS.md](../../AGENTS.md)

---

## Specs (설계)

| 날짜 | 파일 | 요약 |
|------|------|------|
| 2026-11-07 | [readme-front-door-design.md](specs/2026-11-07-readme-front-door-design.md) | README를 앞문으로 줄이고, 절차 문장은 작업지시서·CONTRIBUTING·문서 지도로 옮김 |
| 2026-11-06 | [unpublished-sanction-items-design.md](specs/2026-11-06-unpublished-sanction-items-design.md) | 미연결 감리 의안을 제재 의결의 미보도 절에 두고, 요약 단계가 내용으로 연결 |
| 2026-11-05 | [quarterly-execution-design.md](specs/2026-11-05-quarterly-execution-design.md) | 크롤 때 제재 제목 분리, 의사록 PDF 수신, 요약 시 처리 기록 작성 |
| 2026-11-05 | [sanction-resolution-wiki-handoff-design.md](specs/2026-11-05-sanction-resolution-wiki-handoff-design.md) | 제재 의결·의사록, 처리 기록 공유, 분기 PDF를 옵시디안 raw로 복사 |
| 2026-11-04 | [kasb-reply-archive-design.md](specs/2026-11-04-kasb-reply-archive-design.md) | KASB 질의회신 항목 아카이브. 사이트 비게시, item.md만 옵시디안 raw |
| 2026-11-02 | [cursor-summary-pr-design.md](specs/2026-11-02-cursor-summary-pr-design.md) | 지식체계 요약을 베지 리뷰 PR로 전달 |
| 2026-11-01 | [fss-review-filter-rails-design.md](specs/2026-11-01-fss-review-filter-rails-design.md) | 품질관리감리 왼쪽 법인 목록과 오른쪽 연도 필터 |
| 2026-09-11 | [editor-keyboard-curation-design.md](specs/2026-09-11-editor-keyboard-curation-design.md) | 편집기 행 단위 키보드, 첨부 토스트, PDF 최신순 |
| 2026-09-10 | [consumption-mcp-product-design.md](specs/2026-09-10-consumption-mcp-product-design.md) | 소비 정본=사이트+MCP, audit-regulatory-lens 삭제 |
| 2026-09-09 | [fss-press-crawler-design.md](specs/2026-09-09-fss-press-crawler-design.md) | FSS 보도자료 목록 파서 KRDS 셀렉터 수정 |
| 2026-07-23 | [summarize-slim-design.md](specs/2026-07-23-summarize-slim-design.md) | SUMMARIZE 비용 슬림 (발췌 gold·윈도우·온디맨드, 품질 게이트) |
| 2026-07-23 | [summarize-economics-design.md](specs/2026-07-23-summarize-economics-design.md) | SUMMARIZE 비용 분해·슬림 후보 진단 (2016 Q1 표본) |
| 2026-06-26 | [chronological-main-body-design.md](specs/2026-06-26-chronological-main-body-design.md) | 본문 과거→현재 정렬, Appendix 크롤 순 유지 |
| 2026-06-26 | [admonition-expand-notes-design.md](specs/2026-06-26-admonition-expand-notes-design.md) | 링크 요약 `??? note` → `!!! note` (Appendix `??? info` 유지) |
| 2026-06-27 | [audit-regulatory-lens-skill-design.md](specs/2026-06-27-audit-regulatory-lens-skill-design.md) | 감사 규제 렌즈 스킬 (런타임 제거 2026-09-10) |
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
| 2026-11-07 | [readme-front-door.md](plans/2026-11-07-readme-front-door.md) | README를 앞문으로 줄이고 절차 문장을 정본으로 옮기는 구현 |
| 2026-11-06 | [unpublished-sanction-items.md](plans/2026-11-06-unpublished-sanction-items.md) | 미연결 감리 의안을 미보도 절에 두고 검증으로 빠짐을 막음 |
| 2026-11-05 | [quarterly-execution.md](plans/2026-11-05-quarterly-execution.md) | 크롤 때 제재 제목 분리, 의사록 PDF 수신, 요약 시 처리 기록 작성 |
| 2026-11-05 | [sanction-resolution-wiki-handoff.md](plans/2026-11-05-sanction-resolution-wiki-handoff.md) | 제재 의결 분류, 의사록 연결, 처리 기록과 raw 복사 |
| 2026-11-04 | [kasb-reply-archive.md](plans/2026-11-04-kasb-reply-archive.md) | KASB 질의회신 항목 아카이브 |
| 2026-11-02 | [cursor-summary-pr.md](plans/2026-11-02-cursor-summary-pr.md) | 지식체계 요약을 베지 리뷰 PR로 전달 |
| 2026-11-01 | [fss-review-filter-rails.md](plans/2026-11-01-fss-review-filter-rails.md) | 품질관리감리 왼쪽 법인 목록과 오른쪽 연도 필터 |
| 2026-09-11 | [editor-keyboard-curation.md](plans/2026-09-11-editor-keyboard-curation.md) | 편집기 행 키보드, 첨부 토스트, PDF 최신순 |
| 2026-09-10 | [consumption-mcp-product.md](plans/2026-09-10-consumption-mcp-product.md) | 소비 정본=사이트+MCP, 렌즈 런타임 삭제 |
| 2026-09-09 | [fss-press-crawler.md](plans/2026-09-09-fss-press-crawler.md) | FSS 보도자료 목록 파서 KRDS 셀렉터 수정 |
| 2026-07-23 | [summarize-slim.md](plans/2026-07-23-summarize-slim.md) | SUMMARIZE 비용 슬림 (발췌·윈도우·게이트) |
| 2026-07-23 | [summarize-economics.md](plans/2026-07-23-summarize-economics.md) | SUMMARIZE 비용 분해·슬림 후보 진단 |
| 2026-06-27 | [mcp-corpus.md](plans/2026-06-27-mcp-corpus.md) | Corpus export + MCP stdio/HTTP |
| 2026-06-27 | [audit-regulatory-lens-skill.md](plans/2026-06-27-audit-regulatory-lens-skill.md) | 감사 규제 렌즈 ADVISORY 스킬 (런타임 제거 2026-09-10) |
| 2026-06-26 | [admonition-expand-notes.md](plans/2026-06-26-admonition-expand-notes.md) | `??? note` → `!!! note` 백필 |
| 2026-06-26 | [remove-phase2-summaries.md](plans/2026-06-26-remove-phase2-summaries.md) | Phase 2(ES·기관별·시사점) 제거 |
| 2026-06-26 | [quarterly-update-list-spacing.md](plans/2026-06-26-quarterly-update-list-spacing.md) | 분기 문서 리스트 간격 CSS/JS |
| 2026-06-25 | [platform-hardening.md](plans/2026-06-25-platform-hardening.md) | P1~P4 구현 체크리스트 |
| 2026-03-27 | [quality-updates-writer-skill-redesign.md](plans/2026-03-27-quality-updates-writer-skill-redesign.md) | 스킬 재작성 |
| 2026-03-25 | [editor-source-implementation-plan.md](plans/2026-03-25-editor-source-implementation-plan.md) | SOURCE 탭·CLIP |
| 2026-03-24 | [quality-updates-editor.md](plans/2026-03-24-quality-updates-editor.md) | 편집기 초기 구현 |

---

## 워크플로

```text
/brainstorming → spec (specs/) → 사용자 검토 → plan (plans/) → 구현 → pytest / validate / mkdocs
```
