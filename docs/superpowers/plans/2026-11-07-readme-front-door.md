# README Front Door Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub `README.md`를 소개·사이트·설치·짧은 운영 목록으로 줄이고, README에만 있던 절차 문장을 작업지시서·CONTRIBUTING·문서 지도에 남긴다.

**Architecture:** 정본을 먼저 채운 뒤 README를 갈아끼운다. 작업지시서에 이미 있는 문장은 복사하지 않는다. 검증은 문서 검색과 `npm run lint:md`다. 애플리케이션 테스트는 추가하지 않는다.

**Tech Stack:** Markdown, markdownlint-cli (`npm run lint:md`).

## Global Constraints

- 기준 브랜치는 `docs/readme-front-door` (`origin/main`). `docs/pipeline-owner-cabbage`와 합치지 않는다.
- 코드, 스크립트, 테스트, 분기 본문, `docs/fss-review/`, `docs/index.md`, 기존 스펙·플랜 본문은 고치지 않는다. 색인 한 줄은 이미 스펙에 있다.
- 새 Phase, 새 감리 절차, 품질관리감리 HWP 입수 절차를 만들지 않는다.
- export 스크립트를 누가 실행하는지는 정하지 않는다.
- `C:\dev\obsidian-valut\raw` 철자를 고치지 않는다.
- `raw/sanctions/` 문장은 아래 한 문장만 옮긴다. 경로를 새로 풀지 않는다.
- 작업지시서 Phase 3의 기존 웨일 문장(`그록 봇이 웨일에서 PDF로 저장`)은 고치지 않는다. 제재 안건 HWP 목록 문장과 한 문장으로 합치지 않는다.
- 배지, 스크린샷, 사람 이름을 넣지 않는다.
- 저장소 트리의 연도·파일 목록을 다시 세지 않는다.
- README는 `##` 여섯 절이고 150줄 안쪽이다.

**Spec:** `docs/superpowers/specs/2026-11-07-readme-front-door-design.md`

---

### Task 1: 작업지시서에 없는 조작 문장

**Files:**

- Modify: `docs/project/quarterly-operations-guide.md`
- Test: 검색. 새 테스트 파일 없음

**Interfaces:**

- Consumes: 없음
- Produces: 이후 README가 링크할 기존 파일. 새 앵커를 만들지 않는다. Phase 번호는 1~5를 유지한다.

- [ ] **Step 1: 문장이 아직 없는지 확인**

Run:

```powershell
rg -n "보도자료 등 기존 제목" docs/project/quarterly-operations-guide.md
rg -n "페이지 첨부 모두 연결" docs/project/quarterly-operations-guide.md
rg -n "의사록\(추가\)" docs/project/quarterly-operations-guide.md
rg -n "Whale 변환 필요 목록" docs/project/quarterly-operations-guide.md
rg -n "obsidian-valut" docs/project/quarterly-operations-guide.md
rg -n "crawl_kasb_replies.py" docs/project/quarterly-operations-guide.md
```

Expected: 각 명령이 일치 없음 (exit code 1).

- [ ] **Step 2: Phase 1 표 바로 아래, Agent 체크리스트 앞에 한 문장**

`docs/project/quarterly-operations-guide.md`의 Phase 1 표와 `**Agent 체크리스트**` 사이에 넣는다.

```markdown
`조사·감리결과 조치`가 없는 금융위 보도와 금감원·한공회·회계기준원 링크는 `보도자료` 등 기존 제목에 둔다.
```

`조사·감리결과 조치`를 `제재 의결`에 둔다는 문장과, 새 파일만 만든다는 표의 칸은 이미 있으므로 다시 쓰지 않는다.

- [ ] **Step 3: Phase 2 표 바로 아래, `**HITL 전용**` 앞에 첨부 불릿**

```markdown
**첨부**

- `fetch_attachments.py`는 skip(`<!-- skip -->`), 링크만(`<!-- no_summary -->`), 이미 요약이 있는 항목을 건너뛴다.
- 마커가 없는 링크는 `auto_curate.py`와 같은 규칙으로 고른다.
- 같은 문서가 HWP/HWPX와 PDF로 같이 있으면 PDF만 받는다.
- PDF가 없는 HWP/HWPX만 보고의 「수동 변환 필요」에 적는다.
- 보고 기본 경로는 설정된 다운로드 폴더의 `fetch-attachments-report.md`다. 받은 PDF, PDF가 아닌 기타 첨부, 웨일 변환이 필요한 HWP/HWPX, 다운로드 실패 항목이 나뉜다.
- 편집기 PDF 탭에서는 첨부를 여러 개 더하거나 뺄 수 있다. 「페이지 첨부 모두 연결」은 그 행의 원문 페이지에서 같은 규칙으로 첨부를 받아 항목에 붙인다.
```

`### Phase`를 새로 만들지 않는다. `그록 봇`이 있는 문장은 수정하지 않는다.

- [ ] **Step 4: Phase 3의 `validate_content.py --strict`는 `record.md`가 있는 회의만 본다` 문단 다음, Agent 체크리스트 앞에 넣는다**

이미 있는 안건 분석·위원 논의·미보도·validate 설명은 다시 쓰지 않는다. 아래만 넣는다.

```markdown
제목에 `의사록(추가)`인 글은 회차 키가 같으면 같은 회의로 합치고, 합친 의사록 PDF마다 마커를 붙인다. 추가가 아닌 의사록 PDF가 같은 회의에 둘이면 마커를 붙이지 않는다.

같은 글의 안건 ZIP(첨부 2번)은 받아서 조사·감리·위탁감리·회계법인·감사인 의안의 공개용 안건과 의결서 PDF만 `downloads/sanctions/{연도}-{위원회}-{정기|임시|서면}-{N}차/`에 둔다. `조사`만 있는 파일은 남기지 않고, `조사·감리` 또는 `조사결과`일 때만 본다. `불공정거래`, `시세조종`, `미공개정보`가 들어간 파일과 규정·개정 안건은 남기지 않는다. ZIP 원본은 남기지 않고 주소만 기록한다. 회차 폴더에는 의사록 PDF를 복사하고 `record.md`에 회의일을 적는다. 보도자료에 의안번호가 있으면 그 번호로 잇고, 없으면 같은 회차에서 실명 회사명이 정확히 하나일 때만 잇는다.

제재 안건 HWP는 변환하지 않고 Whale 변환 필요 목록으로만 보고한다.

요약 스킬은 확인한 사실을 `write_quarterly_record.py`로 `data/quarterly-processed/{분기 stem}/`에 남긴다. 파일명은 `{YY-MM-DD}-{제목 앞 40자}.md`다. 같은 경로가 있으면 바이트를 유지한다. 기록 파일은 직접 고치지 않는다. `skip`, `no_summary`, Appendix 항목은 만들지 않는다. 2026년 3분기 항목은 이 명령으로 만들지 않고, 내보내기가 기존 노트에서 만든다. 같은 제목이 둘이면 `--date YY-MM-DD`를 붙인다.

`export_quarterly_raw.py`는 분기 마크다운, 처리 기록, PDF·캡처를 `C:\dev\obsidian-valut\raw`로 복사한다. 저장소 파일은 수정하지 않는다. `--dest`로 목적지를 바꿀 수 있다.

볼트로 보낼 때의 경로는 `raw/sanctions/`이고, 그 복사는 `export_quarterly_raw.py`에 들어가기 전까지 미룬다.
```

- [ ] **Step 5: 6절 코드 펜스 안, `npm run lint:md` 줄 다음에 명령을 추가**

기존 `crawl.py`, `editor.py`, `prepare_deploy.py`, `validate_content.py`, `export_corpus.py`, pytest, `mkdocs build --strict`, `npm run lint:md` 줄은 그대로 둔다. 펜스를 닫기 전에 다음을 붙인다.

```bash
# 첨부
python scripts/fetch_attachments.py docs/quality-updates/2026/2026-07-01_to_2026-09-30.md
python scripts/fetch_attachments.py <분기.md> --report downloads/fetch-attachments-report.md

# 제재 의결 의사록·처리 기록·raw 복사
python scripts/attach_sanction_minutes.py <분기.md>
python scripts/write_quarterly_record.py <분기.md> --title "<링크 제목>"
python scripts/export_quarterly_raw.py <분기.md>

# 질의회신. 분기 크롤러와 별도다. 원문은 사이트, 분기 문서, MCP 코퍼스에 넣지 않는다.
python scripts/crawl_kasb_replies.py
python scripts/crawl_kasb_replies.py --limit 20
python scripts/crawl_kasb_replies.py --retry-failed
python scripts/export_kasb_replies_raw.py

# 텍스트 추출·정렬
python scripts/extract_pdf.py
python scripts/extract_hwp.py
python scripts/extract_hwp.py --path "경로/파일.hwp"
python scripts/reorder_chronological.py docs/quality-updates/2025/2025-01-01_to_2025-03-31.md
```

펜스 바로 아래에 이 문단을 둔다. `npm:` 줄은 유지한다.

```markdown
`crawl_kasb_replies.py`는 `data/kasb-replies/{seq}/item.md`와 원본 첨부를 저장한다. 이 경로는 gitignore하지 않는다. `item.md`와 첨부가 이미 있으면 다시 받지 않는다. `--retry-failed`는 `failed`, `partial`, `empty`를 디스크의 원본으로 다시 추출하고, 없는 파일만 받는다.

`export_kasb_replies_raw.py`는 `item.md`만 복사한다. 기본 목적지는 `C:\dev\obsidian-vault\raw\kasb-replies`이고, `--dest`로 바꿀 수 있다. 같은 `{seq}.md`가 있으면 덮어쓰지 않는다. 첨부 파일은 복사하지 않는다.
```

- [ ] **Step 6: 10절 개정 이력 표의 맨 위에 한 줄**

```markdown
| 2026-11-07 | README에만 있던 첨부·제재 의결·질의회신·추출 명령을 해당 Phase와 6절로 옮김 |
```

- [ ] **Step 7: 들어간 문장 확인**

Run:

```powershell
rg -n "보도자료 등 기존 제목|페이지 첨부 모두 연결|의사록\(추가\)|Whale 변환 필요 목록|obsidian-valut|crawl_kasb_replies.py" docs/project/quarterly-operations-guide.md
```

Expected: 여섯 패턴이 모두 한 번 이상 일치. `그록 봇` 문장은 원래 문장 그대로다.

Run: `npm run lint:md`

Expected: exit code 0.

- [ ] **Step 8: Commit**

```powershell
git add -- docs/project/quarterly-operations-guide.md
git commit -m @"
docs: README에만 있던 조작 문장을 작업지시서에 둔다

"@
```

---

### Task 2: 프론트매터 템플릿

**Files:**

- Modify: `CONTRIBUTING.md` (「수동으로 파일을 만들 때」 목록, 현재 README 앵커 줄)
- Test: 검색. 새 테스트 파일 없음

**Interfaces:**

- Consumes: 없음
- Produces: `CONTRIBUTING.md` 안의 프론트매터 코드 펜스. README는 이 파일을 링크만 한다.

- [ ] **Step 1: 앵커가 아직 README를 가리키는지 확인**

Run:

```powershell
rg -n "README.md#콘텐츠-업데이트-가이드" CONTRIBUTING.md
```

Expected: 한 줄 일치.

- [ ] **Step 2: 그 목록을 아래로 바꾼다**

````markdown
수동으로 파일을 만들 때는 아래를 참고합니다.

- **파일 경로**: `docs/quality-updates/YYYY/YYYY-MM-DD_to_YYYY-MM-DD.md`
- **파일명**: `YYYY-MM-DD_to_YYYY-MM-DD.md` (예: `2025-01-01_to_2025-03-31.md`)

**프론트매터 템플릿**

```yaml
---
title: YYYY-MM-DD ~ YYYY-MM-DD 규제 업데이트
description: [기간] 회계·감사 분야 규제 변화 및 주요 이슈 정리
jurisdiction: KR
year: YYYY
frequency: quarterly
period_label: YYYY-QX
period:
  start: YYYY-MM-DD
  end: YYYY-MM-DD
category: Quality Updates
agencies: [FSS, FSC, KICPA, KASB]
tags: [규제 업데이트, 회계기준, 감사감리, 금융감독]
---
```

- **title**: 페이지 제목 (탐색·검색에 사용)
- **description**: 요약 설명 (SEO·검색 결과용)
- **jurisdiction**: 관할 (한국: KR)
- **year**, **period_label**, **period**: 기간 정보
- **agencies**: 언급 기관 (FSS, FSC, KICPA, KASB 등)
- **tags**: 검색·필터용 태그

문서 본문은 기존 분기별 파일과 같은 형식(금융감독원, 보도자료 등 섹션)을 따른다. 추가 후 `mkdocs.yml`의 `nav`에 등록해야 사이드바에 나온다. 운영 절차는 [분기 운영 작업지시서](docs/project/quarterly-operations-guide.md)다.
````

품질관리감리 절의 최소 프론트매터·`nav` 문장은 이미 있으므로 고치지 않는다.

- [ ] **Step 3: 확인**

Run:

```powershell
rg -n "README.md#콘텐츠-업데이트-가이드" CONTRIBUTING.md
rg -n "period_label: YYYY-QX" CONTRIBUTING.md
```

Expected: 첫 명령은 일치 없음. 둘째는 한 줄 일치.

Run: `npm run lint:md`

Expected: exit code 0.

- [ ] **Step 4: Commit**

```powershell
git add -- CONTRIBUTING.md
git commit -m @"
docs: 분기 프론트매터 템플릿을 CONTRIBUTING에 둔다

"@
```

---

### Task 3: 저장소 트리와 MCP

**Files:**

- Modify: `docs/project/README.md` (파일 끝)
- Modify: `AGENTS.md` (라우팅 표의 MCP 행)
- Test: 검색. 새 테스트 파일 없음

**Interfaces:**

- Consumes: 없음
- Produces: `docs/project/README.md`의 `## 저장소 트리`, `## MCP 코퍼스`. `AGENTS.md`는 `[문서 지도 MCP 절](docs/project/README.md#mcp-코퍼스)`를 쓴다.

- [ ] **Step 1: 문서 지도에 절이 없는지 확인**

Run:

```powershell
rg -n "^## 저장소 트리|^## MCP 코퍼스" docs/project/README.md
```

Expected: 일치 없음.

- [ ] **Step 2: `docs/project/README.md` 맨 끝에 두 절을 추가**

트리 코드블록은 현재 `README.md`의 `## 프로젝트 구조` 펜스와 그 아래 두 불릿을 글자 그대로 옮긴다. 연도 폴더를 추가하거나 빼지 않는다.

````markdown
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
````

SSOT 표의 「로컬 개발 | README.md」 행은 그대로 둔다.

- [ ] **Step 3: `AGENTS.md` MCP 행의 첫 링크만 바꾼다**

현재:

```markdown
| **다른 Agent 소비 (MCP, 읽기 전용)** | [README MCP 절](README.md) · [mcp-corpus spec](docs/superpowers/specs/2026-06-27-mcp-corpus-design.md) | `export_corpus.py` → stdio/HTTP. 인용 계약. 코퍼스 쓰기는 생산 레인만. |
```

변경:

```markdown
| **다른 Agent 소비 (MCP, 읽기 전용)** | [문서 지도 MCP 절](docs/project/README.md#mcp-코퍼스) · [mcp-corpus spec](docs/superpowers/specs/2026-06-27-mcp-corpus-design.md) | `export_corpus.py` → stdio/HTTP. 인용 계약. 코퍼스 쓰기는 생산 레인만. |
```

- [ ] **Step 4: 확인**

Run:

```powershell
rg -n "^## MCP 코퍼스" docs/project/README.md
rg -n "문서 지도 MCP 절" AGENTS.md
rg -n "README MCP 절" AGENTS.md
```

Expected: 첫 둘은 일치. 셋째는 일치 없음.

Run: `npm run lint:md`

Expected: exit code 0.

- [ ] **Step 5: Commit**

```powershell
git add -- docs/project/README.md AGENTS.md
git commit -m @"
docs: 저장소 트리와 MCP 설명을 문서 지도로 옮긴다

"@
```

---

### Task 4: README를 여섯 절로 교체

**Files:**

- Modify: `README.md` (파일 전체)
- Test: 줄 수와 검색. 새 테스트 파일 없음

**Interfaces:**

- Consumes: Task 1의 작업지시서, Task 2의 `CONTRIBUTING.md`, Task 3의 `docs/project/README.md`
- Produces: 150줄 안쪽의 앞문 README

- [ ] **Step 1: 긴 절이 아직 README에 있는지 확인**

Run:

```powershell
rg -n "^## 프로젝트 구조|^## MCP 코퍼스|^## 회계기준원" README.md
```

Expected: 세 제목이 일치.

- [ ] **Step 2: `README.md`를 아래 내용으로 교체**

````markdown
# Quality Updates

회계·감사 분야 규제 모니터링을 위한 정적 문서 사이트입니다.  
금융위원회·금융감독원·회계기준원 등 주요 기관의 보도자료, 제도 개정, 감리 결과를 시기별로 정리하여 제공합니다.

**사이트:** [https://quality-updates.onrender.com](https://quality-updates.onrender.com)

## 기능

- **규제 업데이트**: 분기별 보도자료·제도 변경 정리 (2022년~현재)
- **품질관리감리**: 금융감독원 회계법인 품질관리감리 관련 문서 요약
- **한국어**: 검색·탐색·테마(라이트/다크)
- **질의회신 아카이브**: 원문은 사이트에 게시하지 않는다

## 로컬에서 보기

- **Python**: 3.8 이상
- **Node.js** (선택): `dev`, `build:strict`, `test`

```bash
git clone https://github.com/ypspy/quality-updates.git
cd quality-updates
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
mkdocs serve
```

`mkdocs`를 찾지 못하면 `python -m mkdocs serve`를 쓴다. 브라우저 주소는 [http://127.0.0.1:8000](http://127.0.0.1:8000)이다.

```bash
npm install
npm run dev
npm run build:strict
npm test
```

## 분기 운영

**Agent**와 **전문가(HITL)** 가 협업한다.

수집 → 큐레이션 → 요약 → 사이트 반영 → 배포.

절차·역할·명령은 [분기 운영 작업지시서](docs/project/quarterly-operations-guide.md)에 있다.  
문서 지도는 [docs/project/README.md](docs/project/README.md)에 있다.

## 배포

- **플랫폼**: [Render](https://render.com)
- **동작**: `main` 브랜치 푸시 시 자동 빌드·배포
- **빌드 명령**: `pip install -r requirements.txt && mkdocs build`
- **출력 디렉터리**: `site/`
- **사이트 URL**: [https://quality-updates.onrender.com](https://quality-updates.onrender.com)

## 기여

버그 제보, 문서 수정, 개선 제안은 이슈와 Pull Request로 한다.  
절차는 [CONTRIBUTING.md](CONTRIBUTING.md)에 있다.

## 라이선스·저작권

© 2026 Quality Updates.  
사이트 내 저작권 문구는 `mkdocs.yml`의 `copyright` 및 푸터 오버라이드에 정의되어 있습니다.
````

목차 목록, 배지, 스크린샷, glightbox, minify, CI 항목, `~/.bashrc` alias, mermaid, 8행 단계 표는 넣지 않는다.

- [ ] **Step 3: 확인**

Run:

```powershell
(Get-Content README.md).Count
rg -n "^## " README.md
rg -n "glightbox|bashrc|fetch_attachments|프로젝트 구조" README.md
```

Expected: 줄 수는 150 이하. `##` 제목은 기능, 로컬에서 보기, 분기 운영, 배포, 기여, 라이선스·저작권 여섯 개. 셋째 검색은 일치 없음.

- [ ] **Step 4: Commit**

```powershell
git add -- README.md
git commit -m @"
docs: README를 소개와 설치 앞문으로 줄인다

"@
```

---

### Task 5: 스펙 확인

**Files:**

- Modify: Task 1~4에서 빠진 링크가 있을 때만 해당 파일
- Test: 아래 검색과 `npm run lint:md`

**Interfaces:**

- Consumes: Task 1~4의 문장
- Produces: 스펙의 확인 목록을 만족하는 문서

- [ ] **Step 1: 검색**

Run:

```powershell
rg -n "README.md#콘텐츠-업데이트-가이드|README MCP 절" AGENTS.md CONTRIBUTING.md
rg -n "페이지 첨부 모두 연결" README.md
rg -n "페이지 첨부 모두 연결" docs/project/quarterly-operations-guide.md
rg -n "period_label: YYYY-QX" CONTRIBUTING.md
rg -n "^## MCP 코퍼스" docs/project/README.md
npm run lint:md
```

Expected:

- 첫 검색은 일치 없음.
- README에는 `페이지 첨부 모두 연결`이 없고, 작업지시서에는 있다.
- `period_label`과 `## MCP 코퍼스`는 각각 한 번 이상.
- `npm run lint:md` exit code 0.

- [ ] **Step 2: 실패한 검색만 고치고, 고친 경우에만 커밋**

실패가 없으면 커밋하지 않는다. 고쳤으면:

```powershell
git add -- README.md AGENTS.md CONTRIBUTING.md docs/project/README.md docs/project/quarterly-operations-guide.md
git commit -m @"
docs: README 앞문 확인에서 빠진 링크를 고친다

"@
```

커밋에는 실제로 고친 파일만 넣는다.
