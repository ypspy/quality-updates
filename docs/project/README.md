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
| [curation-rules.md](curation-rules.md) | **큐레이션 규칙** — 스킵·링크만·요약·출처 제안. 편집기를 대체하지 않음 |
| [curation-backtest.md](curation-backtest.md) | 위 규칙의 과거 분기 일치도 |

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
| 요약 포맷 | `.claude/skills/quality-updates-writer/SKILL.md` (Phase 1 링크 note) |
| 소비 (사람) | 공개 MkDocs 사이트 |
| 소비 (다른 Agent) | `scripts/mcp_server/` (stdio + HTTP), `data/corpus/` |
| MCP 코퍼스 export | `scripts/export_corpus.py` → `data/corpus/` |
| Agent 기획 | `AGENTS.md` |
| 로컬 개발 | `README.md` |
| PR/CI | `CONTRIBUTING.md` |

## 저장소 트리

```text
quality-updates/
├── docs/                          # 문서 소스 (MkDocs 소스 루트)
│   ├── project/                   # 메타·운영 문서 (MkDocs exclude)
│   │   ├── README.md              # 문서 지도
│   │   ├── quarterly-operations-guide.md
│   │   └── editor-curation-workflow.md
│   ├── superpowers/               # 설계 spec·plan 아카이브 (MkDocs exclude)
│   ├── index.md                   # 홈페이지
│   ├── assets/
│   │   ├── images/                # 이미지 (로고 등)
│   │   ├── icons/
│   │   ├── stylesheets/extra.css  # 추가 CSS
│   │   └── javascripts/extra.js   # 추가 JS
│   ├── quality-updates/           # 규제 업데이트
│   │   ├── index.md               # 규제 업데이트 개요
│   │   ├── 2022/
│   │   ├── 2023/
│   │   ├── 2024/
│   │   └── 2025/
│   └── fss-review/                # 품질관리감리
│       ├── index.md
│       └── fr2022.md
├── overrides/
│   └── partials/                  # Material 테마 오버라이드
│       ├── header.html
│       └── footer.html
├── mkdocs.yml                     # MkDocs 설정
├── requirements.txt               # Python 의존성 (버전 고정)
├── package.json                   # npm 스크립트 및 devDependencies
├── .editorconfig                  # 에디터 포맷 규칙
├── .markdownlint.json             # Markdown 린트 설정
├── .github/
│   ├── workflows/ci.yml           # CI (lint, build, validate)
│   └── dependabot.yml             # 의존성 자동 업데이트
├── data/
│   ├── kasb-replies/              # 질의회신 원문 아카이브 (사이트 비게시)
│   └── quarterly-processed/       # 요약 처리 기록 (사이트 빌드 제외)
├── scripts/                       # 유틸리티 스크립트
│   ├── crawl.py                   # 규제 업데이트 크롤러 CLI
│   ├── crawl_kasb_replies.py      # 질의회신 수집 CLI
│   ├── export_kasb_replies_raw.py # item.md만 옵시디안 raw로 복사
│   ├── crawler/                   # FSS·FSC·KICPA·KASB 수집 모듈
│   ├── editor.py                  # 큐레이션 편집기 진입점 (Flask)
│   ├── editor/                    # 편집기 앱·정적 파일
│   ├── fetch_attachments.py       # 요약 대상 원문 첨부 일괄 다운로드
│   ├── attach_sanction_minutes.py # 제재 의결에 의사록 PDF 마커
│   ├── write_quarterly_record.py  # 처리 기록 생성·추가
│   ├── export_quarterly_raw.py    # 분기 원문을 옵시디안 raw로 복사
│   ├── extract_pdf.py             # PDF 텍스트 추출
│   ├── extract_hwp.py             # HWP 텍스트 추출
│   ├── reorder_chronological.py   # 콘텐츠 시계열 정렬
│   ├── validate_content.py        # 콘텐츠 스키마 검증
│   ├── prepare_deploy.py          # 배포 전처리 (skip·validate·힌트)
│   └── tests/                     # 스크립트 단위 테스트
├── .claude/skills/quality-updates-writer/  # 분기 요약·배포 정리 스킬
├── AGENTS.md                        # Agent 진입·보완 기획 프롬프트
├── README.md                      # 이 파일
├── CONTRIBUTING.md                # 기여 가이드
└── IMPLEMENTATION_LOG.md          # 개선 작업 실행 로그
```

- **탐색 구조**: `mkdocs.yml`의 `nav`에서 메뉴·레이블·파일 매핑을 정의합니다.
- **스타일/스크립트**: `docs/assets/` 아래 파일은 `mkdocs.yml`의 `extra_css`, `extra_javascript`로 로드됩니다.

## MCP 코퍼스

사람은 [공개 사이트](https://quality-updates.onrender.com)에서 조회한다. 다른 Agent는 같은 공개 경계의 **읽기 전용 MCP**에 붙는다. 문헌 검색 MCP와 역할이 다르다: 이 코퍼스는 한국 감독·기준(FSS, FSC, KICPA, KASB) **큐레이션 사실**만 제공한다.

Tool: `list_quarterly_periods`, `search_regulatory_updates`, `get_regulatory_update`.

**인용 계약**

1. 주장마다 `agency`, `date`, `title`, `url` (가능하면 `id`)를 붙인다.
2. note bullets·표에 있는 내용만 쓴다. 없는 숫자·해석은 창작이다.
3. `summary_status=no_summary`면 제목·URL만 힌트이고, 본문 사실로 쓰지 않는다.
4. skip 항목은 코퍼스에 없다. 사이트 원문 md에서 되살리지 않는다.
5. 코퍼스는 읽기 전용이다. 큐레이션·요약·nav는 생산 레인만 한다.

```bash
# 코퍼스 생성 (skip 제외, Appendix A 이전만)
python scripts/export_corpus.py --strict

# 로컬 stdio MCP (Cursor). 워크스페이스 절대경로가 든 .cursor/mcp.json은 커밋하지 않는다.
# .cursor/mcp.json 예시:
# { "mcpServers": { "quality-updates": {
#     "command": "python", "args": ["scripts/mcp_server/stdio.py"],
#     "cwd": "/path/to/quality-updates" } } }
python scripts/mcp_server/stdio.py

# Hosted HTTP (Render 2번째 Web Service — 사이트와 별도)
# cwd=scripts, PYTHONPATH=scripts, env MCP_API_KEY 필수
# Start: uvicorn mcp_server.http:app --host 0.0.0.0 --port $PORT
# Health: GET /health
# MCP: POST /mcp  Authorization: Bearer <MCP_API_KEY>
# Host 허용: RENDER_EXTERNAL_HOSTNAME(Render 주입) + 선택 MCP_ALLOWED_HOSTS
# 실제 호스트 URL은 HITL이 Render에서 만든 뒤 이 절에 적는다.
```

설계: [mcp-corpus spec](../superpowers/specs/2026-06-27-mcp-corpus-design.md) · [소비 제품 spec](../superpowers/specs/2026-09-10-consumption-mcp-product-design.md)
