# Agent 가이드 (Quality Updates)

Cursor·Claude 등 **AI 에이전트**가 이 저장소에서 작업할 때의 진입점입니다.
사람용 온보딩은 [README.md](README.md), 분기 운영은 [docs/project/quarterly-operations-guide.md](docs/project/quarterly-operations-guide.md)를 본다.
분기 규제 업데이트·제재 의결·질의회신 파이프라인은 **Agent**와 **전문가**가 협업한다.

이 파일이 에이전트 규칙의 **원본(SSOT)** 이다. `.claude/` 스킬은 병행하되, 충돌하면 이 파일을 따른다.
작업 큐는 [TASKS.md](TASKS.md), 이 프로젝트 결정은 [DECISIONS.md](DECISIONS.md)다.
공통·미분류 결정은 이 저장소 `DECISIONS.md`에 없으며, 필요할 때만 원문·대화를 인용한다. 없다고 해서 결정이 없었던 것은 아니다.

저장소는 PUBLIC이다. 토큰·키·비밀번호·환경변수 **값**은 커밋·PR·이슈·채팅 어디에도 쓰지 않는다.

---

## 0. 장기 목표와 중지 상태

### 유효한 장기 목표

1. Quality Updates — 규제 업데이트 항목의 **자동 파이프라인과 백필을 마무리**한다.
   - 상태: 유효 (V-205, 2026-11-18)
   - 완료 기준: ① 자동 파이프라인이 사람 개입 없이 4회 연속 완료 ② 백필 대상 연도 2025년부터 2000년까지 완료 ③ 백필 형태는 2026년 3분기 골드셋을 따른다

이 저장소 작업 대상이 **아닌** 것(폐기·타 저장소): 추출기 완성(disclosure-extractor), 학술 연구 후 업무·공개 확장(dart-wrapper).

### 지금 하지 않는 것

- 나머지 연도 백필·연도 본문 재작성·#184·#185 재개 (V-249, 사용자 보류)
- 새 클라우드 에이전트 기동 (V-249)
- 품질관리감리 항목의 자동 파이프라인과 백필
- Grok Bot 루틴(`qu`, `qu-2`, `fss-b0000291` 등) 재가동 — 당분간 중지

### 지금 해도 되는 것

- **린트·형식 기준 PR** (V-249 허용)
- 이관 문서·에이전트 규칙·TASKS·검증·원인 조사(쓰기 없는 범위)
- 사용자가 명시한 그 밖의 작업

### V-249 해제 조건 (blocked: 파일럿 후 결정)

V-249(린트·형식 기준 PR 외 연도 작업 및 새 클라우드 에이전트 중지)는
아래 절차와 조건을 모두 충족한 뒤에만 해제를 검토한다.
해제 여부는 사용자만 결정하며, 에이전트는 스스로 해제하지 않는다.

[파일럿: 3회]

- 사용량 측정을 위해 작업 3건을 돌린다. 가능하면 작은 작업 2건과
  중간 규모 1건으로 유형을 섞는다.
- 파일럿 중에는 다른 루틴·에이전트를 돌리지 않는다.
- 사용자가 각 작업 전후의 사용량 수치를 알려 주면, 에이전트는
  작업 유형, 소요 시간, 사용량 증가분을 한 줄씩 PR 설명에 기록한다.
  에이전트는 사용량을 직접 확인할 수 없으므로 수치를 추정해 적지 않는다.

[파일럿 후 결정]

- 3건 기록이 모이면 에이전트는 유형별 사용량(평균과 최대)을 표로
  보고하고, 해제 시 예상 소모를 아래 식으로 계산해 제시한다.
  예상 소모 = 해제 후 작업 건수 × 파일럿 최대 사용량 × 1.5
- 해제 조건의 수치([한도 단위] 기준 X 이하)는 이 보고를 보고
  사용자가 정한다. 그 전까지 X는 비워 둔다.
- 사용자의 명시적 승인이 있어야 해제된다.

[해제 전까지]

린트·형식 기준 PR만 진행하고 나머지 연도 작업과 새 클라우드
에이전트는 중지 상태를 유지한다.

---

## 1. 작업 유형별 라우팅

| 하고 싶은 일 | 먼저 읽을 것 | 워크플로 |
|--------------|--------------|----------|
| **분기 보도자료 요약** | [.claude/skills/quality-updates-writer/SKILL.md](.claude/skills/quality-updates-writer/SKILL.md) | SUMMARIZE / SKIP_REMOVAL — SUMMARIZE: gold-excerpts + md ±80줄 윈도우 + REFERENCE 온디맨드; 재주입 금지. [상세](docs/superpowers/specs/2026-07-23-summarize-slim-design.md) |
| **다른 Agent 소비 (MCP, 읽기 전용)** | [문서 지도 MCP 절](docs/project/README.md#mcp-코퍼스) · [mcp-corpus spec](docs/superpowers/specs/2026-06-27-mcp-corpus-design.md) | `export_corpus.py` → stdio/HTTP. 인용 계약. 코퍼스 쓰기는 생산 레인만. |
| **분기 파이프라인 전체** | [docs/project/quarterly-operations-guide.md](docs/project/quarterly-operations-guide.md) | 가이드 「정규 분기 루틴 — Cursor」 — Agent 실행(큐레이션 포함)·draft PR → 전문가 머지 |
| **큐레이션·편집기** | [docs/project/editor-curation-workflow.md](docs/project/editor-curation-workflow.md) | HITL 주도; Agent는 마커 임의 변경 금지 |
| **큐레이션 사전 제안** | [docs/project/curation-rules.md](docs/project/curation-rules.md) | `scripts/auto_curate.py`는 마커를 출력만 한다. 본문에 대량으로 쓰지 않음 |
| **프로젝트 점검·보완 기획** | 이 파일 + `/brainstorming` | 평가 → 2~3안 → **spec 승인** → plan → 구현 |
| **승인된 기능 구현** | `docs/superpowers/specs/YYYY-MM-DD-*-design.md` | [plan](docs/superpowers/plans/) + Subagent-Driven |
| **PR·CI·린트** | [CONTRIBUTING.md](CONTRIBUTING.md) · 아래 §6 | pytest, validate `--strict`, mkdocs `--strict`, `npm run lint:md` |
| **작업 큐** | [TASKS.md](TASKS.md) | 상태·완료 기준을 보고 진행 |
| **문서 지도** | [docs/project/README.md](docs/project/README.md) | — |

---

## 2. 프로젝트 보완 기획 — 프롬프트 템플릿

복사 후 `[...]`만 채워서 사용한다. **대규모 변경은 spec 승인 전 구현하지 않는다.**

### A. 프로젝트 점검 + 보완 기획

```markdown
프로젝트를 점검해줘. /brainstorming

범위: [크롤러 / CI / 문서 / 편집기 / 콘텐츠 / 전체]
목표: [한 문장, 예: 단일 repo 파이프라인 완성]
제외: [명시, 예: 분기 콘텐츠 백필]
참고: README, docs/project/README.md, docs/superpowers/specs/ 최신 항목
산출:
  - 현황 평가 (강점·부채)
  - 2~3안 비교 + 추천
  - 승인 후 spec → docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md
```

### B. 승인된 스펙 기반 구현

```markdown
@docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md 를 기준으로
구현 계획을 작성하고 Subagent-Driven으로 실행해줘.

제약:
- spec 범위 외 파일 변경 금지
- 완료 조건: cd scripts && python -m pytest tests/ -q
- python scripts/validate_content.py --strict
- mkdocs build --strict
```

### C. 문서·IA 정리

```markdown
문서 중복과 진입점을 점검하고 IA 정리안을 /brainstorming 해줘.

원칙: SSOT(단일 정본), AGENTS.md 허브, MkDocs exclude
참고: docs/superpowers/specs/2026-06-25-doc-organization-design.md
구현 전 spec 승인 필요.
```

### D. 분기 운영 (요약 아님)

```markdown
@docs/project/quarterly-operations-guide.md 기준으로 [YYYY QN] 분기 운영을 진행해줘.

분기 규제·제재 의결·질의회신 파이프라인은 Agent와 전문가가 협업한다.
Agent 담당: crawl·질의회신·제재/회의록 공개분 입수·큐레이션·요약·nav 초안·prepare_deploy·draft PR
전문가 담당: 최종 배포 전 main 머지 승인만
분기 문서와 nav·index 최신 링크는 그 분기 다음 달 5일 09:00 KST 이후에만 만든다.
```

---

## 3. 제약 (반드시 준수)

- **V-249**: 린트·형식 기준 PR만. 나머지 연도 작업·새 클라우드 에이전트 중지. 해제 조건은 §0.
- **분기 요약 포맷**: `quality-updates-writer` 스킬 없이 링크별 note 블록 형식을 임의로 바꾸지 않는다.
- **HITL 큐레이션**: `<!-- skip -->`, `<!-- source: … -->`를 사용자 지시 없이 대량 변경하지 않는다.
- **분기 시점**: 분기 문서(`docs/quality-updates/YYYY/YYYY-MM-DD_to_YYYY-MM-DD.md`)와 `mkdocs.yml` nav·`docs/quality-updates/index.md`·`docs/index.md` 최신 링크는 그 분기 다음 달 5일 09:00 KST(1/5·4/5·7/5·10/5) 이후에만 만든다. 그 전에 걸린 백필 항목은 다음 정규 분기 루틴으로 넘긴다. 예외는 윤석님 명시 승인만이며, 허용 경로는 `data/qu-early-allow.txt`에 적는다. `crawl.py`는 `--year`와 `--quarter`를 명시한다. (V-222: 갱신일 전 분기 수행 금지)
- **기획 → 구현**: `/brainstorming`으로 spec이 승인되기 전 코드·대규모 리팩터를 시작하지 않는다.
- **커밋**: 사용자가 요청할 때만. `quality-updates-writer`는 RIGID 스킬이다.
- **SUMMARIZE 슬림** (요약 시): `gold-excerpts` + 분기 md ±80줄 윈도우 + REFERENCE 온디맨드; 재주입 금지 — [spec](docs/superpowers/specs/2026-07-23-summarize-slim-design.md)
- **코퍼스 소비**: 다른 Agent는 MCP만 읽는다. 소비 경로로 `docs/quality-updates/`를 grep하지 않는다. 큐레이션·요약·nav 쓰기는 생산 레인만.
- **첨부**: 여러 건이면 모두 붙인다. hwp와 pdf가 함께 있으면 pdf만 받는다 (C-011).
- **날짜·요약**: 게시판 날짜와 원문 날짜가 다르면 원문 날짜. 출처 없는 요약은 점검한다 (C-022). 큐레이션 세부 규칙은 [docs/project/curation-rules.md](docs/project/curation-rules.md).
- **비밀값**: 토큰·키·비밀번호·환경변수 값을 기록·커밋·PR·이슈에 넣지 않는다. 이름은 `.env.example`만.
- **Markdown lint**: `docs/` 아래 `.md`를 작성하거나 수정한 뒤 `npm run lint:md`를 실행한다. 실패하면 보고된 오류를 모두 고치고, 통과할 때까지 다시 실행한다. `.markdownlint.json` 규칙을 끄거나 오류 파일을 검사에서 빼지 않는다. 줄 끝 공백은 일괄로 지우지 않는다. 공백 2칸은 Markdown 하드 줄바꿈일 수 있으니 그 줄과 앞뒤를 보고 고친다.

---

## 4. 폴더 구조

| 경로 | 내용 |
|------|------|
| `docs/quality-updates/<YYYY>/` | 분기 페이지 (현재 main: 2012~2026) |
| `docs/fss-review/` | 품질관리감리 공개 페이지 |
| `docs/project/` | 운영 정본 (분기 가이드, 큐레이션, 수집기) |
| `docs/superpowers/` | 승인 스펙·계획 |
| `docs-dev/` | 개발용 형식 기준 (예: `sanctions-format.md`) |
| `scripts/` | crawl·crawler·editor·mcp·validate·lint·tests |
| `data/` | corpus·replies·`qu-early-allow.txt` |
| `.claude/skills/` | 병행 스킬 (`quality-updates-writer` 등) |
| `FSS Inspection_Grokbot_MINT/` | Mint 원문 PDF·매핑 (처분 **blocked**; 일상 작업에서 읽지 않음 — TASKS 참고) |

제재 원본 969폴더·Mint 분류표 정본은 저장소 밖(봇 박스)에 있다. 저장소 `downloads/`는 gitignore다.

---

## 5. 실행·테스트·빌드

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
mkdocs serve                                   # http://127.0.0.1:8000
cd scripts && python -m pytest tests/ -q       # = npm test
python scripts/validate_content.py --strict
python scripts/lint_public_body.py             # = npm run lint:public-body
python scripts/export_corpus.py --strict       # data/corpus 갱신(쓰기)
mkdocs build --strict                          # = npm run build:strict
npm ci && npm run lint:md                      # markdownlint "docs/**/*.md"
python scripts/crawl.py --year YYYY --quarter N
python scripts/editor.py
python scripts/prepare_deploy.py
```

지원 Python은 **3.11–3.12**다. CI는 3.11. 로컬 앞문은 [README.md](README.md).

구현·PR 후 최소 검증:

```bash
cd scripts && python -m pytest tests/ -q
python scripts/validate_content.py --strict
python scripts/lint_public_body.py
python scripts/export_corpus.py --strict
mkdocs build --strict
npm run lint:md
```

참고: `test_kasb_file_proxy_saves_to_configured_downloads_folder` 1건 실패는 해소됨 — 네트워크 비의존 mock, plan 2026-11-26.

---

## 6. 머지·리뷰 절차

`CONTRIBUTING.md`와 충돌하면 **이 절을 우선**한다. (HANDOVER §9를 네 항목으로 압축)

1. **머지는 사용자만** — 머지·삭제·데이터 이동·외부 발송·공개 범위 변경은 사용자 본인 말로만 승인한다. 에이전트는 스스로 머지하지 않는다. 읽기 전용 점검, 계획, 머지하지 않는 draft PR은 사전 허용.
2. **PR에 증거·범위·비밀값 검사** — 변경 범위, 검증 명령·결과, 비밀값(토큰·키·비밀번호·환경변수 값)이 없음을 PR 본문에 적는다. CI(lint·build·validate·test) 통과를 목표로 한다.
3. **리뷰 세션 분리** — 작성 세션과 독립 검토 세션을 섞지 않는다. 독립 검토는 반증이 목적이고 코드 수정·푸시·PR 댓글을 하지 않는다. (세부 launch·라운드 상한은 HANDOVER §9.2·review-kit 참고)
4. **방향·규칙 변경은 사전 질문** — `AGENTS.md`·분기 시점·백필 범위·V-249 해제·공개 범위 등 방향·규칙을 바꾸기 전에 사용자에게 묻는다.

---

## 7. 하지 말 것

- V-249 해제 없이 연도 백필·#184·#185 재개·새 클라우드 에이전트
- 품질관리감리 자동 파이프라인·백필 (장기 목표 「지금 하지 않는 것」)
- HITL 마커 대량 변경, 요약 포맷 임의 변경
- 비밀값 기록·커밋
- 사용자 승인 전 커밋·머지·force-push
- Grok 루틴 재가동 (당분간 중지)
- `FSS Inspection_Grokbot_MINT/` 처분(삭제·gitignore·이전) — 사용자 결정 전 blocked
- 사용량 수치를 추정해 적기

---

## 8. 설계 이력

| 경로 | 용도 |
|------|------|
| [docs/superpowers/specs/](docs/superpowers/specs/) | 승인된 설계 스펙 |
| [docs/superpowers/plans/](docs/superpowers/plans/) | 구현 계획 (체크리스트) |
| [docs/superpowers/README.md](docs/superpowers/README.md) | 색인 |

새 spec 파일명: `YYYY-MM-DD-<topic>-design.md`
