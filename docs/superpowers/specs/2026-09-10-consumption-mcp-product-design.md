# 소비 제품: 사이트 + Agent MCP, 렌즈 제거

**날짜**: 2026-09-10  
**상태**: 승인됨  
**범위**: 소비 정본을 공개 사이트와 읽기 전용 MCP로 고정하고 `audit-regulatory-lens`를 제거한다.  
**선행**: [2026-06-27-mcp-corpus-design.md](2026-06-27-mcp-corpus-design.md) (스키마·tool·stdio/HTTP — **재설계하지 않음**)

---

## 개요

Quality Updates **생산** 파이프라인은 유지한다. **소비**는 이 레포 안의 감사 워크플로가 아니라 두 산출물이다.

| 산출물 | 소비자 | 역할 |
|--------|--------|------|
| MkDocs 사이트 | 사람 | 분기 문서 조회 |
| 코퍼스 MCP (읽기 전용) | 다른 Agent | 최신 규제 항목 검색·인용 |

`audit-regulatory-lens`(Planning/Execution/Reporting 코멘트)는 소비 정본이 아니므로 **삭제**한다. 대체 스킬은 만들지 않는다.

---

## 브레인스토밍 합의

| 항목 | 결정 |
|------|------|
| 소비 정본 | 사이트(사람) + MCP(다른 Agent) |
| 부착면 | Hosted HTTP가 정본, 로컬 stdio는 동일 `core.py` 편의 통로 |
| 렌즈 | 내리지 않고 **삭제** |
| 생산 | crawl → editor HITL → writer → prepare_deploy **변경 없음** |
| MCP tool/스키마 | v1 유지 (`list_quarterly_periods`, `search_regulatory_updates`, `get_regulatory_update`) |
| 문헌 MCP | `accounting-lit`과 역할 분리 — 이 코퍼스는 한국 감독·기준 **사실**만 |

---

## 범위 외

- 임베딩·의미 검색, 새 MCP tool, 코퍼스 스키마 변경
- 크롤러·편집기·writer·요약 포맷
- 과거 spec/plan 파일 삭제 (아카이브 유지)
- Render 대시보드에서 서비스·시크릿을 만드는 HITL 클릭 (문서로만 안내)
- 이 PR에서 `data/corpus/` 전량 재생성 (신선도 **절차**만 문서화; JSONL 커밋은 분기 배포 HITL)

---

## 1. 제품 경계

```text
생산 (이 레포)  →  docs/quality-updates/*.md
                →  MkDocs 사이트 (사람)
                →  export_corpus → data/corpus/ → MCP (다른 Agent)
```

다른 Agent가 **해도 되는 일**: search → get → 기관·날짜·원문 URL·note만 근거로 쓰기.

다른 Agent가 **해서는 안 되는 일**: skip 판단, 요약 작성, `docs/quality-updates/` 수정, skip된 항목을 사이트 원문 md에서 되살리기.

이 레포 Agent 세션도 소비 시 MCP만 쓴다. repo `grep`으로 코퍼스를 우회하지 않는 것을 권장하나, 강제 게이트는 MCP 계약·문서이다.

---

## 2. 다른 Agent 인용 계약

Tool 입출력은 [mcp-corpus spec §2.2](2026-06-27-mcp-corpus-design.md)와 같다.

다른 Agent가 이 코퍼스를 근거로 쓸 때 **필수**:

1. 주장마다 `agency`, `date`, `title`, `url` (가능하면 `id`)를 붙인다.
2. note bullets·표에 **있는 내용만** 쓴다. 없는 숫자·해석은 창작이다.
3. `summary_status=no_summary`면 제목·URL만 힌트이고, 본문 사실로 쓰지 않는다.
4. skip 항목은 JSONL에 없다. 원문 md를 뒤져 되살리지 않는다.
5. 코퍼스는 읽기 전용이다. 큐레이션·요약·nav는 생산 레인만 한다.

이 다섯 줄을 README MCP 절과 FastMCP `instructions`에 넣는다. 별도 consumer 스킬 파일은 두지 않는다.

문헌 검색(`accounting-lit` 등)과 같이 쓸 수 있다. 역할은 겹치지 않는다: 논문 vs 한국 감독·기준 큐레이션 사실.

---

## 3. 렌즈 삭제

### 지움

| 경로 | 내용 |
|------|------|
| `.claude/skills/audit-regulatory-lens/` | SKILL.md, reference/keywords.md, output-samples.md |
| `AGENTS.md` | 렌즈 라우팅 행, 렌즈 제약 문단 |
| `README.md` | MCP 절의 렌즈 “우선 사용” 문장 |
| `docs/project/README.md` | Agent 표·SSOT의 렌즈 행 |

### 남김

| 경로 | 이유 |
|------|------|
| `docs/superpowers/specs/2026-06-27-audit-regulatory-lens-skill-design.md` | 설계 이력 |
| `docs/superpowers/plans/2026-06-27-audit-regulatory-lens-skill.md` | 구현 이력 |
| `.superpowers/sdd/*` 스냅샷 | 생성 아카이브, 이 spec 범위 외 |

`docs/superpowers/README.md` 렌즈 spec/plan 행은 **삭제하지 않는다**. 요약에 “런타임 제거(2026-09-10)”를 붙인다.

`docs/superpowers/plans/2026-06-27-mcp-corpus.md`의 follow-up “렌즈 MCP retrieve 활성화”는 **취소**로 표시한다.

---

## 4. 배포·신선도

사이트와 MCP는 **같은 git 커밋의 공개 경계**를 본다. skip은 export 시 in-memory로 빠지고, 사이트는 `prepare_deploy` 후 빌드된다.

| 단계 | 담당 | 동작 |
|------|------|------|
| Phase 5 배포 전 | Agent 실행, HITL 승인 | 기존 `prepare_deploy` + `python scripts/export_corpus.py --strict` |
| JSONL 커밋 | HITL | `data/corpus/corpus.jsonl`, `manifest.json`이 소스와 맞으면 커밋 |
| CI | 시스템 | 기존 `export_corpus.py --strict` 유지 (스키마·strict; drift fail로 바꾸지 않음) |
| 사이트 | Render 기존 서비스 | `mkdocs build` |
| MCP | Render **두 번째** Web Service | `scripts/mcp_server/http.py`, env `MCP_API_KEY` 필수 |

Hosted 정본 URL 형태: `https://<mcp-service>/mcp` (실제 호스트는 HITL이 Render에서 정하고 README에 적는다). 인증: `Authorization: Bearer <MCP_API_KEY>`. 로컬 stdio는 인증 없음.

로컬 개밥: README의 Cursor `mcp.json` 예시만 유지한다. 워크스페이스 절대경로가 든 `.cursor/mcp.json`은 **커밋하지 않는다**.

`render.yaml` Blueprint는 기존 정적 사이트 설정을 덮을 위험이 있어 **이번 범위에 넣지 않는다**. Hosted 생성은 README 수동 절차(명령, cwd/`PYTHONPATH`, 헬스 `/health`, Bearer).

분기 운영 가이드 Phase 5·품질 게이트·명령 참조에 `export_corpus --strict`를 한 줄로 추가한다. 생산 단계 순서(수집→큐레이션→요약→nav)는 바꾸지 않는다.

---

## 5. 문서 라우팅 (구현 시)

| 파일 | 변경 |
|------|------|
| `AGENTS.md` | 렌즈 행 삭제. MCP 행을 “다른 Agent 소비(읽기 전용)”로 명시. 제약: 코퍼스 쓰기는 생산 레인만. |
| `README.md` | MCP 절: 사람=사이트, Agent=MCP. 인용 계약 5줄. 렌즈 문구 제거. Hosted 부착 절차. |
| `docs/project/README.md` | 렌즈 SSOT 삭제. 소비 SSOT = 사이트 + MCP. |
| `docs/project/quarterly-operations-guide.md` | Phase 5에 corpus export. |
| `docs/superpowers/README.md` | 본 spec 색인 + 렌즈 행에 런타임 제거 표기. |
| `scripts/mcp_server/app.py` | FastMCP `instructions`에 인용 계약(영문 요약 + 읽기 전용). |

AGENTS.md 보완 기획 템플릿(A–D)과 writer 스킬은 유지한다.

---

## 6. 구현 순서 (plan 작성용)

```
P1  audit-regulatory-lens 디렉터리 삭제 + AGENTS/README/docs/project 렌즈 참조 제거
P2  소비 정본·인용 계약·Hosted 부착을 README/AGENTS/quarterly-operations에 반영
P3  FastMCP instructions 갱신 + mcp-corpus plan follow-up 취소 + superpowers 색인
P4  pytest / validate --strict / mkdocs --strict / export_corpus --strict (기존 게이트)
```

P1과 P2는 같은 PR에 넣는다. Hosted 서비스 생성·키 설정은 HITL이며 P4 완료 조건이 **아니다**.

---

## 7. 완료 조건

- [ ] `.claude/skills/audit-regulatory-lens/` 없음
- [ ] 런타임 문서(`AGENTS.md`, `README.md`, `docs/project/`)에 렌즈를 소비 진입점으로 안내하지 않음
- [ ] README에 인용 계약 5줄 + 로컬 stdio 예시 + Hosted Bearer 절차
- [ ] 분기 운영 Phase 5에 `export_corpus --strict` 명시
- [ ] FastMCP instructions가 읽기 전용·note 밖 창작 금지를 말함
- [ ] `cd scripts && python -m pytest tests/ -q`
- [ ] `python scripts/validate_content.py --strict`
- [ ] `python scripts/export_corpus.py --strict`
- [ ] `mkdocs build --strict`
- [ ] 생산 스크립트·writer 스킬·코퍼스 스키마 무변경 (instructions 문자열 제외)

---

## 8. 리스크

| 리스크 | 완화 |
|--------|------|
| 렌즈를 쓰던 로컬 세션 | AGENTS 라우팅 삭제; 이력 spec만 남김 |
| Hosted 미개통 | 코드·문서는 준비, 서비스는 HITL. 로컬 stdio로 개밥 가능 |
| 코퍼스 stale | Phase 5 export를 운영 정본으로 명시. 이번 PR에서 JSONL 강제 재생성 없음 |
| 다른 Agent가 md를 grep | 계약·instructions로 금지. MCP write API는 원래 없음 |

---

## 개정 이력

| 날짜 | 내용 |
|------|------|
| 2026-09-10 | 초안 — 사이트+MCP 소비 정본, 렌즈 삭제, 인용 계약, Phase 5 export |
