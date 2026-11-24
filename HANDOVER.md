# HANDOVER — ypspy/quality-updates

- 작성: 2026-11-24 CET(UTC+1), 조율 담당(Mr. Vegetable) executor. 기준 브랜치 `handover` @ `c8826001` (base `main` `150cdca5`).
- 갱신: 2026-11-25 KST(UTC+9), 조율 담당(Mr. Vegetable) executor. 갱신 브랜치 `handover-update-20261125`(base `main` `67fc396a`). LAPTOP-YS가 응답해 2.2절을 읽기 전용 점검 결과로 바꾸고, 11/24 이후 바뀐 PR·봇 상태를 반영했다. 이번 갱신에서 새로 확인한 것은 [확인됨 11/25]로 적었다. 그 밖의 [확인됨]은 11/24 작성 때 확인한 값이다.
- 11/24 초안은 quality-updates #187, dart-wrapper #21, disclosure-extractor #14로 각 기본 브랜치에 squash 머지됐다(2026-11-24 12:35~12:36 KST). 이 갱신본은 별도 PR이며 머지는 윤석님 검토·승인 후.
- 표기: [확인됨] 이번 작성에서 직접 확인 / [추정] 기록·봇 보고에 있으나 이번에 재확인 안 함 / [확인 불가] 근거를 찾지 못함 / [접근 불가] 접근 경로 없음(11/24 작성 당시 LAPTOP-YS 오프라인 등).
- 비밀값(토큰·키·비밀번호·환경변수 값)은 적지 않았다. 이름만 적었다.
- 자매 문서: `ypspy/dart-wrapper` `HANDOVER.md`, `ypspy/disclosure-extractor` `HANDOVER.md` (2·4·9절은 세 문서 공통).

## 1. 프로젝트 목적과 현재 상태

Quality Updates는 금융위·금감원·회계기준원 등의 회계·감사 규제 자료를 분기별로 정리해 https://quality-updates.onrender.com 에 공개하는 MkDocs 사이트(팀 조직상 Product A)이다 [확인됨: `README.md`, `mkdocs.yml` `site_url`, HTTP 200]. 팀 목표 문서에는 "Quality Updates 생산 파이프라인을 완성하고 안정화한다"가 첫 목표로 적혀 있다 [추정: `/workspace/reports/team-diagnosis-20261122.md` §1]. `150cdca5`(#186 공개 본문 린트·2026 제재 의결 형식 기준, 2026-11-22 머지) 이후 `main`에는 #187(`HANDOVER.md`, `06608116`)과 #188(`DECISIONS.md`, `67fc396a`)만 더해졌고, 현재 `main` `67fc396a`의 CI는 성공이다 [확인됨 11/25: `git log origin/main`, `gh run list`]. `docs/quality-updates/`에 2012~2026 연도 폴더가 있고 2013(#177)·2012(#183)는 머지, 2011(#184)·2010(#185)은 draft로 열려 있다 [확인됨]. 2026-11-21 윤석님 지시 「린트·형식 기준 PR만 하고 나머지 연도 작업과 새 클라우드 에이전트는 멈춰」로 연도 백필은 정지 상태다 [추정: `Cabbage.md` §4, `Mint.md` §2]. 다음 정규 분기 루틴 첫 실행은 2027-01-05 09:00 KST이다 [추정: `Cabbage.md` §2].

## 2. 자료 위치 지도

표기: [확인됨] 이번 작성에서 파일·명령·API로 직접 확인 / [추정] 기록에 있으나 이번에 재확인하지 않음 / [확인 불가] 찾아봤으나 근거 없음 / [접근 불가] 접근 경로가 없음(랩탑 오프라인 등).

### 2.1 GitHub 저장소 (소유자 `ypspy`)

| 저장소 | 공개 여부 | 기본 브랜치 | 용도 | 근거 |
|---|---|---|---|---|
| `ypspy/quality-updates` | PUBLIC | `main` | MkDocs 공개 사이트 Quality Updates(Product A). 분기 규제 업데이트·제재 의결·품질관리감리·질의회신 수집 스크립트 | [확인됨] `gh repo view ypspy/quality-updates --json visibility,defaultBranchRef` |
| `ypspy/dart-wrapper` | PUBLIC | `master` | DART 공시 카탈로그 수집(1층)·Viewer API·감사 추출 연구 패키지 모노레포 | [확인됨] 같은 명령 |
| `ypspy/disclosure-extractor` | PUBLIC | `feat/standard-extractors` | DART 공시 하이브리드 파서(`dart_parser`)와 골드 검수 도구(Gold Desk) | [확인됨] 같은 명령 |
| `ypspy/obsidian-vault` | PRIVATE | `main` | LLM 위키(Second-Brain). `wiki/` 435개 파일, `raw/` 원문. 쓰기는 Mr. Kale만 | [확인됨] `gh repo list ypspy`, 박스 사본 `/workspace/vault` (HEAD `e54d2aa9`, PR #20 머지) / 역할은 `wiki/bot-operations.md` |
| `ypspy/review-kit` | PRIVATE | `main` | 독립 리뷰어(클라우드 에이전트) 규칙·스킬. 9절 참고 | [확인됨] `git ls-remote` main = `e124cd3893c4fb7cd56b20252ef37f9c4dbb509b` |
| `ypspy/my-obsidian-vault` | PRIVATE | — | 리타이어한 이전 볼트. 삭제·아카이브는 윤석님 확인 필요 | [확인됨] 목록 / [추정] 상태는 `wiki/bot-operations.md` 2026-11-05 기록 |

세 대상 저장소의 `handover` 브랜치(2026-11-25 KST): quality-updates `d269d795`(PR #189 열림, base `main`), dart-wrapper `48762aa6`(PR #22 열림, base `master`), disclosure-extractor `f700c39e`(PR #15 열림, base `feat/standard-extractors`). 셋 다 기본 브랜치를 일반 merge 커밋으로 받은 뒤(QU `399885b9`, DW `f7f4499`, DE `fd1561b`) DECISIONS.md 정리 커밋을 얹은 상태로, 기본 브랜치보다 뒤처진 커밋은 없다(앞선 커밋 QU 5, DW 4, DE 4). 11/24 초안의 `.gitignore`·`.env.example`·`HANDOVER.md`는 #187/#21/#14로 기본 브랜치에 들어갔다. 이 갱신본은 열린 PR과 섞이지 않게 `handover-update-20261125` 브랜치에서 올린다. [확인됨 11/25] `git rev-list --left-right --count`, `gh pr list`, `gh pr view`

### 2.2 로컬 폴더 — LAPTOP-YS (Windows, 윤석님 노트북)

**[확인됨 11/25]** 2026-11-25 05:27 KST에 LAPTOP-YS가 응답해 읽기 전용 명령으로 확인했다(`git status -sb`·`rev-parse`·`worktree list`, 파일 목록·크기, `Get-ScheduledTask`, SQLite `immutable=1` 읽기, `Get-FileHash`, 프로세스·포트 목록). 랩탑에는 아무것도 쓰거나 바꾸지 않았고 `git fetch`도 하지 않았다. 랩탑의 origin 추적 ref는 마지막 fetch(2026-11-23 00:22 KST) 기준이라, 아래 "원격 대비"는 박스에서 받은 현재 원격과 비교한 값이다. 시각은 모두 KST.

**작업 트리**

| 경로 | 브랜치 @ HEAD | 원격 대비 | untracked |
|---|---|---|---|
| `C:\dev\quality-updates` | `fix/sanction-kale-handoff-format` @ `4cfc3561` | 원격 같은 브랜치와 같음. 현재 `origin/main` `67fc396a`보다 1 앞서고 80 뒤처짐 | `scripts/tests/fixtures/summary_bench/` |
| `C:\dev\dart-wrapper` | `feat/gold-review` @ `2f0bf964`(고정, checkout·pull 금지 [추정: `Seaweed.md` §1]) | 원격 `feat/gold-review`와 같음. 현재 `origin/master` `1f199e0a`보다 42 뒤처짐 | `data/`, `packages/web-api/dart_sections.db-shm`, `packages/web-api/dart_sections.db-wal` |
| `C:\dev\disclosure-extractor` | `feat/standard-extractors` @ `d4e7bae9` | 현재 원격 `374cad91`(#14 HANDOVER 머지)보다 1 뒤처짐 | 없음 |
| `C:\dev\dw-arf-d8e92e1`, `C:\dev\dw-f004-d8e92e1` | dart-wrapper worktree 2개, 둘 다 detached `d8e92e1` | — | — |

**로컬 DB** (건수는 SQLite `immutable=1` 읽기)

| 경로 | 크기·수정 시각 | 내용 |
|---|---|---|
| `C:\dev\dart-wrapper\packages\web-api\dart_catalog.db` | 10,336,010,240 B, 2026-11-21 21:10 | 1층 카탈로그. `disclosures` 488,539건, `slice_progress` complete 19,504·pending 75, `catalog_jobs`·`extraction_jobs`의 running/pending 0 |
| `C:\dev\dart-wrapper\packages\web-api\dart_sections.db` | 6,328,320 B, 2026-11-07 00:51 | F004 본문 |
| `C:\dev\dart-wrapper\packages\web-api\f004_research.db` | 15,585,280 B, 2026-11-16 11:02 | F004 연구 DB(백업 대상 아님) |
| `C:\dev\dart-wrapper\data\gold\gold.db` | 13,529,088 B, 2026-11-12 13:49 | DW 골드 DB(읽기 전용, 새 라벨 금지 [추정: `Zucchini.md` §6.1]). samples 446, captures 7, capture_history 10, labels 0, runs 1. SHA-256 앞 16자리 `A0CAC855C1DB2D25` |
| `C:\dev\disclosure-extractor\data\gold.db` | 13,529,088 B, 2026-11-20 00:14 | DE 골드 DB. samples 446, extractor_snapshots 446, captures 0, labels 0, runs 1. SHA-256 앞 16자리 `1E603DA5093EAE41`(11/20 기록 `1e603da5…`와 앞자리 같음) |
| `C:\dev\dart-wrapper\.worktrees\admin-viewer-skeleton\packages\web-api\dart_catalog.db` | 53,248 B, 2026-07-25 | `git worktree list`에 없는 남은 폴더 안의 작은 DB |
| `C:\dev\dart-wrapper\data\gold_cache` | — | 골드 원문 캐시. 존재만 확인(크기 미측정) |

**실행 스크립트·예약 작업** (작업 스케줄러, 프로젝트 관련 3개. 나머지는 OneDrive·Google·Apple·Lenovo·Realtek 등 무관한 작업)

| 작업 이름 | 실행 | 트리거 | 마지막 실행·결과 | 다음 실행 |
|---|---|---|---|---|
| `DartNightlyCatalog` | `powershell.exe -File C:\dev\dart-nightly\run.ps1` | 매일 14:00, 15:00 | 2026-11-21 15:00, 결과 0. 요약 로그: 15:00~21:10, added 4,829, total 488,539, 잡 `376d2c25…` partial(예산 정지), 미완료 슬라이스 75 | 2026-11-25 14:00 |
| `DartF004Weekly` | `powershell.exe -File C:\dev\dart-f004\run.ps1` | 토 21:00, 22:00 | 2026-11-21 22:00, **결과 1**. 로그: `loader not found at C:\dev\dw-f004\packages\web-api\scripts\load_section_bodies.py`(`reason=loader_missing`). 스크립트(L13)는 `C:\dev\dw-f004`를 쓰지만 그 폴더는 없고 worktree는 `C:\dev\dw-f004-d8e92e1`이다 | 2026-11-28 21:00 |
| `DartDbBackup` | `powershell.exe -File C:\backups\dart\run-backup.ps1` → `C:\backups\dart\backup.py` | 수 21:30 | 2026-11-20 21:17 시작, 21:44 `backup.py exit=0`(1,627.8초), 결과 0 | 2026-11-25 21:30 |

- `C:\dev\dart-nightly\run-sections.ps1`도 있다(연결된 예약 작업 없음).
- `C:\dev\dart-nightly\run.ps1`은 회차마다 `origin/master`를 `C:\dev\dw-nightly`로 detach해 쓰고 끝나면 지운다(L4, L127–L128, L140). 지금 `C:\dev\dw-nightly`는 없다.
- 로그: `C:\dev\dart-nightly\logs\`(최신 `20261121*.log`, `*-summary.txt`), `C:\backups\dart\logs\`(최신 `backup-20261120-211706.log`).
- 실행 중 프로세스: python·uvicorn 0개, 8000–8999 포트 LISTEN 0개 → Gold Desk(:8765)와 uvicorn :8010 모두 꺼져 있다.

**백업** (`C:\backups` 전체 20,986,674,922 B)

| 경로 | 내용 |
|---|---|
| `C:\backups\dart\` (19,463,795,045 B) | `dart-db-slot3.zip`(1,198,994,722 B, 2026-11-20 21:44), `run-backup.ps1`, `backup.py`, `logs\`, `tmp\`, `pre-arf-20261116\`, `pre-f004-02-20261116\` 등. `backup.py` 대상은 `dart_catalog.db`, `dart_sections.db`, DW `data\gold\gold.db` 3개(L18–L20) — DE `gold.db`, `f004_research.db`는 없다 |
| `C:\backups\qu-sanctions-20261116-postd28`, `-20261116-r2`, `-20261117-prec20-5`, `-20261118-pre-c16` | QU 제재 폴더 스냅샷 4개(하위 폴더 595 / 688 / 608 / 610) |

**기타**

| 경로 | 내용 |
|---|---|
| `C:\Users\yoont\arf-resume-20261115\` | ARF 추출 도구·Gold Desk 로그 [추정: `Zucchini.md` §6.1]. 존재만 확인 |
| QU 제재 원본 `qu-sanctions`(969폴더 [추정: `Cabbage.md` §1]) | `C:\dev\quality-updates` 아래(깊이 2)와 `C:\Users\yoont` 아래(깊이 3)에서 찾지 못함 — 위치 [확인 불가] |
| `C:\dev`의 다른 폴더: `accounting-lit-mcp`, `audit-engagement-template`, `ax-learning`, `cost-analysis`, `firmFlow`, `obsidian-vault`, `spelling-bee`, `_archive`, `dart-f004`, `dart-nightly` | 세 저장소와 별개(앞의 둘은 스크립트 폴더). 내용은 열지 않음 |

- `.env` 파일은 비밀값이 있어 열지 않았다.

### 2.3 봇 박스 (Grok Bot 공용 Linux 박스, `/workspace`)

| 경로 | 용도 | 근거 |
|---|---|---|
| `/workspace/handover-repos/<repo>` | 이 HANDOVER.md를 고친 clone(`handover`, `handover-update-20261125` 브랜치) | [확인됨 11/25] |
| `/workspace/handover-repos/quality-updates/COMMON_DECISIONS.md` (`handover` 브랜치, PR #189) | 공통 결정 모음 156항목(1. 공통 92, 2. 세 저장소 밖 30, 3. 여러 프로젝트 섞임 11, 4. 프로젝트 불명 23). 위치는 임시이며 최종 위치는 윤석님 결정 대기 | [확인됨 11/25] 항목 수 직접 셈 |
| `/workspace/quality-updates`, `/workspace/repos/dart-wrapper`, `/workspace/disclosure-extractor-pr11`, `/workspace/qu-*`, `/workspace/wt*` 등 | 봇 작업용 clone·worktree(여러 개, 일부 detached) | [확인됨] `find / -name .git` |
| `/workspace/decision-inbox/queue.md` | 결정 대기열(추가만, 봇 보고 한 줄씩). 554줄 | [확인됨 11/25] |
| `/workspace/proposals/` | 계획서·실행안(`economy/team-rules-v1.md`, `cloud-migration/`, `gold-ingest/`, `qu-bf2000/`, `team-ops-5-actions-20261122.md`) | [확인됨] |
| `/workspace/plans/` | 수집·백필 계획(2026-11-11~11-20) | [확인됨] |
| `/workspace/prompts/` | 봇·클라우드 에이전트 지시서 85개 | [확인됨] `ls \| wc -l` |
| `/workspace/reviews/`, `/workspace/reviews/state/<repo>-<pr>.json` | 독립 검토 보고서와 라운드 상태 | [확인됨] |
| `/workspace/handoff/` | Mint 분류표(`qu-bf-2000`~`qu-bf-2013`), Kale 반입 묶음(zip) | [확인됨] |
| `/workspace/qu-collect/downloads/`, `/workspace/qu-collect-logs/` | QU 백필 원문 입수본·수집 로그 | [추정] `Mint.md` §5 |
| `/workspace/quality-updates/data-handoff/` | `F004`, `fss-replies`, `kasb-replies`, `sanctions` 전달 묶음(untracked) | [확인됨] |
| `/workspace/f004/`, `/workspace/fss-review/` | F004 추출 검토·FSS 감리 주간 기준선(`baseline_2026-11-23.json`) | [확인됨] |
| `/workspace/arf-resume/`, `/workspace/proposals/gold-ingest/` | ARF C2·W1 Gold Desk 점검 기록 사본 | [확인됨] |
| `/workspace/vault` | `ypspy/obsidian-vault` 공유 clone | [확인됨] |
| `/workspace/full_scan/`, `/workspace/drive_*.csv`, `/workspace/step3_rename_candidates/` | Rice의 Drive 전수 목록·정리 기록 | [확인됨] 파일 존재 |
| `/workspace/reports/team-diagnosis-20261122.md` | 팀 운영 진단(봇 구성·루틴·GitHub 수치) | [확인됨] |
| `/workspace/handover/bot-reports/<봇>.md` | 이번 이관용 봇 보고서 | [확인됨] |
| `/workspace/exports/` | 대화 기록 내보내기. **저장소에 넣지 않음, 내용 인용 안 함** | [확인됨] 존재만 |

### 2.4 클라우드

| 위치 | 용도 | 근거 |
|---|---|---|
| https://quality-updates.onrender.com | QU 공개 사이트(Render). `main` 푸시 시 자동 빌드·배포 | [확인됨] HTTP 200(2026-11-24 CET), `README.md` 배포 절 / Render 대시보드·서비스 설정은 [접근 불가] |
| Google Drive `Second-Brain` 폴더 (`1nW461q4t4aSTHOqaqT1myAznMdxnFAvp`) | `Bot-Operations`, `Home`, `README (지식체계 인덱스)`, `지식체계 요약본` 4개 Docs. 요약본은 2026-11-05부터 갱신 안 함 | [확인됨] Drive 목록 / [추정] 갱신 중단은 `wiki/bot-operations.md` |
| Google Drive `80_개발_AI/DART_DB_백업` | DART DB 주간 백업 zip(슬롯 2개) | [확인됨] 폴더 존재 / 슬롯 파일 현황은 [확인 불가] |
| Google Drive `80_개발_AI/quality-updates`, `accounting-lit-mcp`, `ax-learning`, `cost-analysis` | 코드 사본 폴더(2026-10-29) | [확인됨] 폴더 존재 / 내용·용도 [확인 불가] |
| Cursor 캔버스 「결정 대기함」, 「정보원 정기 입수 개선안 (2026-11-12)」 | 결정 카드·정보원 로드맵(P0~P3) | [추정] `/workspace/reports/team-diagnosis-20261122.md` §1 (URL 기재) |
| GoatCounter `yoonseokseong.goatcounter.com` | QU 접속 통계 | [추정] `Cabbage.md` §2 |
| GitHub Actions | QU `CI`(lint/build/validate/test), DW `ci`(web-api·research pytest). DE는 워크플로 없음 | [확인됨] `.github/workflows/` |

## 3. 구조

### 3.1 주요 폴더·파일 [확인됨: `ls`, `git ls-files`(4,390개, `.git` 제외 199M)]

| 경로 | 내용 |
|---|---|
| `mkdocs.yml` | 사이트 설정·nav. `exclude_docs`로 `project/**`, `superpowers/**` 제외. 훅 `scripts/mkdocs_drop_excluded.py`, `scripts/mkdocs_fss_review_year.py` |
| `docs/quality-updates/<YYYY>/<YYYY-MM-DD>_to_<YYYY-MM-DD>.md` | 분기 페이지(2012~2026) |
| `docs/fss-review/` | 품질관리감리 페이지 |
| `docs/project/` | 운영 정본: `quarterly-operations-guide.md`, `editor-curation-workflow.md`, `curation-rules.md`, `fss-b0000291-collector.md`, `kasb-meetings-collector.md` |
| `docs/superpowers/specs/`(30), `plans/`(22) | 설계·구현 계획 |
| `docs-dev/sanctions-format.md` | 2026 제재 의결 형식 기준(#186) |
| `scripts/` | `crawl.py`, `crawler/`(FSC·FSS·KASB·KICPA 등), `editor.py`·`editor/`(Flask 편집기), `mcp_server/`(`stdio.py`, `http.py`), `validate_content.py`, `lint_public_body.py`, `export_corpus.py`, `prepare_deploy.py`, `attach_sanction_minutes.py`, `quarter_timing.py`, `tests/`(57개 파일) |
| `data/` | `corpus/`(`corpus.jsonl`, `manifest.json`), `fss-replies/`, `fss-review/`, `kasb-replies/`, `qu-early-allow.txt` |
| `FSS Inspection_Grokbot_MINT/` | Mint 품질관리감리 원문 PDF·정리(364파일, 112M, 폴더명에 공백) |
| `AGENTS.md`, `.claude/skills/quality-updates-writer/SKILL.md`, `.claude/settings.local.json` | 기존 에이전트 진입점(Claude 기준). 이번 작업에서 수정하지 않음 |
| `.github/workflows/ci.yml`, `.github/dependabot.yml` | CI, 의존성 갱신(pip·npm 월간, `mcp` 메이저 무시) |
| `.markdownlint.json`, `.editorconfig`, `CONTRIBUTING.md`, `IMPLEMENTATION_LOG.md` | 스타일·기여 규칙 |

### 3.2 브랜치 전략
- 기본 브랜치 `main`, 보호 규칙 없음 [확인됨]. PR은 squash 머지(커밋 제목 끝 `(#번호)`) [확인됨: `git log`].
- 원격 브랜치 141개: `cursor/` 50, `content/` 28, `fix/` 20, `feat/` 17, `data/` 8, `docs/` 4, `chore/` 3, 기타 [확인됨: `git branch -r`]. 머지 후에도 브랜치가 남아 있다.
- `cursor/*`는 클라우드 에이전트, 봇 PR은 draft로만 열고 ready·머지·force-push 금지 [추정: `Cabbage.md` §5].
- `handover`: 이관용(`.gitignore`·`.env.example`만 추가) [확인됨].

### 3.3 실행·테스트·배포 명령 [확인됨: `package.json`, `README.md`, `AGENTS.md` §5, CI]

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
mkdocs serve                                   # http://127.0.0.1:8000
cd scripts && python -m pytest tests/ -q       # = npm test
python scripts/validate_content.py --strict
python scripts/lint_public_body.py             # = npm run lint:public-body
python scripts/export_corpus.py --strict       # data/corpus 갱신(쓰기 발생)
mkdocs build --strict                          # = npm run build:strict
npm ci && npm run lint:md                      # markdownlint "docs/**/*.md"
python scripts/crawl.py --year YYYY --quarter N   # --year/--quarter 필수, 갱신일 전 분기는 종료 코드 2
python scripts/editor.py                       # 로컬 큐레이션 편집기(Flask)
python scripts/prepare_deploy.py
```
- 배포: Render, `main` 푸시 시 자동. 빌드 `pip install -r requirements.txt && mkdocs build`, 출력 `site/` [확인됨: `README.md`] / Render 서비스 설정·MCP HTTP 서버 배포 여부는 [접근 불가].
- 이번 박스 실측(Python 3.13.5, 2026-11-24 CET, `/tmp` venv): pytest **1307 passed, 1 failed**(`tests/test_preview_endpoint.py::test_kasb_file_proxy_saves_to_configured_downloads_folder`, 500≠200), `validate_content.py --strict` rc 0, `lint_public_body.py` rc 0(경고 2026: `trailing_dot_host` 66), `mkdocs build --strict -d /tmp/qu-site` rc 0 [확인됨]. `npm run lint:md`·`export_corpus.py`는 실행하지 않음(쓰기·설치 회피). CI(Python 3.11)는 `150cdca5`에서 성공 [확인됨].

## 4. 봇별 역할 분담

조직 근거: `ypspy/obsidian-vault` `wiki/bot-operations.md`(2026-11-11 확정 조직, 마지막 갱신 2026-11-16), `/workspace/reports/team-diagnosis-20261122.md` §2. 2026-11-16에 Mr. Strawberry(홍보·세일즈)는 조직에서 빠졌다. [확인됨: 두 파일]
봇 보고서: `/workspace/handover/bot-reports/<봇>.md` — 6개 모두 수신(Cabbage, Mint, Seaweed, Zucchini, Rice, Kale; 2026-11-24 02:36~02:42 CET). 보고서 안의 [확인됨]은 그 봇이 작성 시점에 확인했다는 뜻이며, 이 문서에서 다시 확인한 것은 따로 적었다.

| 봇 | 역할 | 담당 파일·모듈 | 지금까지 한 일 (근거) | 보고 |
|---|---|---|---|---|
| Mr. Vegetable · 조율 담당 | 조율만. 결정 대기함, 브리핑, 봇 지시, 독립 검토 띄우기, 머지 실행(윤석님 결정 후) | `/workspace/decision-inbox/queue.md`, `/workspace/proposals/`, `/workspace/prompts/`, `/workspace/reviews/state/` | 세 저장소 `handover` 브랜치 생성·커밋(`c8826001`, `ab74bad6`, `cf9afbfa`) [확인됨: git log]. 11/24 HANDOVER(#187·#21·#14)와 QU DECISIONS(#188) squash 머지, DECISIONS 3절 구조 PR #189·#22·#15 열림 [확인됨 11/25: `gh pr view`]. 머지 실행 예: dart-wrapper #20 `ef02eb7e`, quality-updates #153 `85b66aa4` [추정: queue.md 2026-11-20 줄] | 요청자(해당 없음) |
| Mr. Cabbage · Quality Update 담당 | `quality-updates` 구현·수집·draft PR. 비DART 원천(FSC·FSS·KASB 등) 수집·가공 | `scripts/crawl.py`, `scripts/crawler/`, `scripts/attach_sanction_minutes.py`, `scripts/lint_public_body.py`, `docs/quality-updates/`, `data/` | 최근 머지 #173~#186 [확인됨: `gh pr list --state merged`]. 2013→2000 연도 백필 중 #177(2013)·#183(2012) 머지, #184(2011)·#185(2010) draft. 루틴 `qu`, `qu-2`, `fss-b0000291` [추정: 보고서] | 수신 `Cabbage.md` |
| Mr. Mint · 품질관리감리 담당 | 품질관리감리·제재 의결 분류와 원문 대조. **코드 구현 안 함** | `/workspace/handoff/qu-bf-<연도>/`, `/workspace/fss-review/`, `/workspace/f004/review-pr*` | 2013→2000 분류 r2 완료, F004 관련 #145~#150 머지, 주간 감리 점검(2026-11-23 신규 0) [추정: `Mint.md` §2~3] | 수신 `Mint.md` |
| Mr. Seaweed · 데이터 추출 담당 | DART 1층 원천 수집(`dart_catalog.db` `disclosures`/`entries`/`corps`/`slice_progress`, `dart_sections.db`), DB 파일·백업 실행 | DW `packages/web-api`(수집), 랩탑 `run.ps1`·`backup.py` | D3-2015(F002 2015 365/365 complete), 공시 누계 483,710(11/20)→488,539(11/21), 여행 전 수동 백업 [추정: `Seaweed.md` §3] | 수신 `Seaweed.md` |
| Mr. Zucchini · DART 파서 담당 | DART 2층 파싱·추출(`audit_report_facts`, `extraction_*`), DE `gold.db` 품질 검증(Gold Desk), DW·DE PR 오너 수용 검토. 1층은 읽기만 | DW `packages/research/`, DE `src/dart_parser/gold/` | DW #14~#20, DE #13 지시·수용 검토, W1 Gold Desk 기동(446 샘플), ARF C2 14,288/17,455 처리 후 보류 [추정: `Zucchini.md` §1~3] | 수신 `Zucchini.md` |
| Mr. Kale · Second-Brain 담당 | `ypspy/obsidian-vault`에만 쓰기. raw 반입·위키 합성 | 볼트 `raw/`, `wiki/`, `.cursorrules` | 볼트 PR #16~#20 머지: #18 회계기준위 566회(`b247e2bf`), #19 금융위·증선위 969회차(`67752242`), #20 허브 날짜(`e54d2aa9`) [확인됨: `gh pr list -R ypspy/obsidian-vault --state merged`]. 루틴 D12(`/workspace/synth-runner/run_weekly.py`, 잔액 하한 가드로 11/23 skip) [추정: `Kale.md` §6] | 수신 `Kale.md` |
| Mr. Rice · 드라이브 문서 담당 | Google Drive 개인 문서 정리(Second-Brain 제외). DART DB는 다루지 않고 백업 위치만 | `/workspace/full_scan/`, `/workspace/drive_cleanup_*`, `/workspace/step3_rename_candidates/` | Drive 전수 목록 r79–r84 누계 63,340항목·쓰기 0 [확인됨: `/workspace/full_scan/report_r79-r84.md`], Step 3 이름 변경 1,823행, 중복 정리 Step 1 이동 7,119·잔여 1,768, `DART_DB_백업` 폴더 생성 [추정: `Rice.md` §2~3]. 루틴: 전수 조사(`automation-1794885772459`), 중복 정리 야간(`automation-1793420638471`), Inbox 분류(`drive-inbox`) | 수신 `Rice.md` |

**11/25 갱신 메모(봇 상태)**
- Zucchini: ARF C2 마지막 잡 `925d62064e424e5b925850f4aea2e4e7`을 랩탑 `dart_catalog.db` `extraction_jobs`에서 읽기 전용으로 확인 — 상태 `partial`, extractor `audit_opinion`, mode `resume`, `finished_at` 2026-11-19 04:35:22(DB 기록값, 시간대 표기 없음). running/pending 잡 0, :8010 LISTEN 없음 [확인됨 11/25]. 11/18 밤 이후 미점검으로 남아 있던 '잡 925d6206·uvicorn :8010' 확인은 이것으로 끝났다. C2와 uvicorn :8010은 W1 캡처가 끝날 때까지 시작하지 않는다 [추정: queue.md 2026-11-24 8:09 AM CT 줄, `Zucchini.md` §3]. ARF 루틴 3개(`arf-07-50-ct`, `arf-09-22-ct`, `arf-23-00-ct`) 일시정지 여부는 윤석님 답 대기 [추정: queue.md 2026-11-23 7:36 PM CT 줄].
- Seaweed: 예약 작업 3개가 Ready 상태이고 랩탑이 켜져 있어 다음 실행이 잡혀 있다(`DartNightlyCatalog` 2026-11-25 14:00, `DartDbBackup` 11-25 21:30, `DartF004Weekly` 11-28 21:00 KST). `DartF004Weekly`는 11/21에 `loader_missing`으로 실패했다 [확인됨 11/25: 2.2절]. 여행 중 catch-up 금지 방침 [추정: `Seaweed.md` §1]에 비춰 이 실행을 둘지는 이번에 바꾸지 않았다.
- Rice: Drive 전수 조사 r91–r96 누계 65,140항목·쓰기 0, 대기열 1,466 [추정: queue.md 2026-11-24 3:15 AM CT 줄].
- Gold Desk(:8765)는 꺼져 있다. 다시 켜는 것은 윤석님 결정 사항 [확인됨 11/25: 프로세스·포트 목록].

PR·커밋 봇 식별 규칙(앞방향만): 라벨 `bot:<봇이름>`(클라우드 에이전트면 `bot:cloud-agent` 추가), 커밋 끝 `Bot: <봇이름>` + `Made-with: cursor-agent`. [추정] `/workspace/proposals/team-ops-5-actions-20261122.md` §1 (실행안, 라벨 저장소 생성은 별도 승인), `Cabbage.md` §5. 2026-10-25~11-22 PR 216건 중 213건 작성자가 `ypspy`라 과거 PR은 봇을 구분할 수 없다. [추정: 같은 문서 배경]

## 5. 결정 기록

- `DECISIONS.md`: 인수인계 결정 기록이 #188(`67fc396a`, 2026-11-24 13:12 KST squash 머지)로 `main`에 들어왔다 [확인됨 11/25].
- 이를 3절 구조(1. 이 프로젝트 결정 134, 2. 공통 결정 92, 3. 미분류 64)로 고친 판과 `COMMON_DECISIONS.md`(156항목)는 PR #189(head `handover` `d269d795`)에 있고 열린 상태다. 머지와 `COMMON_DECISIONS.md`의 최종 위치는 윤석님 결정 대기 [확인됨 11/25: `gh pr list`, 항목 수 직접 셈].
- 3절 미분류는 파일 첫 줄대로 확정 전에는 규칙으로 쓰지 않는다. `COMMON_DECISIONS.md` 4절(프로젝트 불명 23항목)은 윤석님이 항목별로 분류하는 중이다 [추정: 2026-11-24 윤석님 지시, 조율 기록].

## 6. 진행 중 작업

### 6.1 열린 PR·이슈 [확인됨 11/25: `gh pr list --state open`]
| PR | 브랜치 | 상태 |
|---|---|---|
| #185 2010년 분기 페이지 신설(Mint 분류 반영) | `cursor/qu-bf2000-2010-quarters` head `885b5972` | draft. #186 이전 base `48e235fe`, 형식 기준에 맞춘 재작성 필요 [추정: `Cabbage.md` §4] |
| #184 2011년 분기 페이지 신설 | `cursor/qu-bf2000-2011-quarters` head `93e994e5` | draft. 같은 사유 |
| #189 프로젝트별 DECISIONS.md 3절 구조와 COMMON_DECISIONS.md(임시) | `handover` head `d269d795` | ready(draft 아님), 머지 금지·윤석님 검토 대기 |
- 열린 이슈 0건(이슈 기능은 켜져 있음) [확인됨, 11/24].

### 6.2 미완료 작업
- 2013→2000 연도 백필: 정지. 재개 시 2단계 2012·2013 재작성, 3단계 #184·#185 수정, 2009~2000 PR 미착수 [추정: `Cabbage.md` §4]. Mint 분류표는 `/workspace/handoff/qu-bf-<연도>/`에 있음(2013~2000 r2) [추정: `Mint.md` §3.1].
- 2012 배포본 제재 절에 작성 지시·공정 문구가 공개 본문에 남아 있음 [추정: `/workspace/reviews/qu-2012-deployed-diagnosis.md`].
- 2012 Q1 견본(커밋 안 함) `/workspace/reviews/qu-format-lint/sample-2012q1/` [추정: `Cabbage.md` §4].
- FSS 질의회신 본문 `pending_whale` 1,179건 재전달 대기(Whale 변환 → Kale `--update-pending`, 별도 승인) [추정: `Kale.md` §5-6].
- `record.md` 날짜 오류 6건(Cabbage 쪽 원자료): `2009-금융위-15차`, `2010-증선위-10차`, `2010-증선위-15차`, `2012-증선위-7차`, `2012-증선위-임시-2차`, `2012-증선위-8차` [추정: `Kale.md` §5-10].
- 회계기준자문위원회 50건 위키 미반입, 품질관리감리 위키 미작성 [추정: `Kale.md` §5-4, §5-7].

### 6.3 막힌 지점
- 연도 백필 재개는 윤석님 재개 지시 대기 [추정: `Cabbage.md` §4].
- 미보도 항목 (가)/(나) 처리, record.md 날짜에 대한 윤석님 답 대기 [추정: `Cabbage.md` §4].
- F004 주간 확인은 LAPTOP-YS 오프라인으로 미확인(마지막 접수번호 `20261008000709`) [추정: `Mint.md` §2, queue.md 2026-11-23 줄]. 랩탑은 11/25 응답했으나 Mint의 F004 주간 확인은 이번 갱신에서 다시 돌리지 않았다. 랩탑 예약 작업 `DartF004Weekly`는 11/21 `loader_missing`으로 실패 [확인됨 11/25: 랩탑 로그, dart-wrapper HANDOVER 7절].

## 7. 알려진 문제와 기술 부채
1. 로컬 pytest 1건 실패 `test_kasb_file_proxy_saves_to_configured_downloads_folder` — 박스 Python 3.13에서 재현 [확인됨]. CI(3.11)는 통과 [확인됨]. 원인 미조사 [확인 불가].
2. 린트 임시 허용 `scripts/lint-public-body-allow.txt`에 2012·2013 분기 파일이 경고로만 집계됨(2단계·3단계 후 삭제 예정) [확인됨: 파일 주석].
3. `lint_public_body.py` 경고 `trailing_dot_host` 2026: 66건 [확인됨]. 2014–2026 `fsc.go.kr./` 1,099건 경고 [추정: `Cabbage.md` §4].
4. 원격 브랜치 141개 중 다수가 머지 후 남은 브랜치. 정리는 삭제라서 승인 필요 [확인됨: 개수].
5. 에이전트 규칙이 Claude 기준(`AGENTS.md` "Cursor·Claude", `.claude/skills/quality-updates-writer`, `.claude/settings.local.json`의 Windows 경로 allow-list). Cursor 규칙 파일은 다른 곳에서 만든다고 했으므로 여기서는 만들지 않음 [확인됨: 파일].
6. 저장소 루트에 공백 포함 폴더 `FSS Inspection_Grokbot_MINT/`(112M PDF) — 저장소 크기·경로 처리 부담 [확인됨].
7. `README.md`는 "Python 3.8 이상", CI는 3.11 — 지원 버전 불일치 [확인됨].
8. `IMPLEMENTATION_LOG.md` "분기 콘텐츠 백필 (2023 Q2, 2024 Q1·Q2 gold standard)" 미체크 [확인됨]. 현재 유효 여부는 [확인 불가].
9. 저장소가 PUBLIC. private 전환은 윤석님 승인 사항 [확인됨: visibility].
10. 과거 PR 작성자가 모두 `ypspy`라 봇별 이력 구분 불가 [추정: `team-ops-5-actions-20261122.md`].

## 8. 환경변수(이름만)·외부 서비스·의존성
- 환경변수(`.env.example`, `handover` 커밋) [확인됨]: `MCP_API_KEY`, `MCP_ALLOWED_HOSTS`, `RENDER_EXTERNAL_HOSTNAME`, `PORT`, `LOG_LEVEL` (`scripts/mcp_server/http.py`), `FLASK_DEBUG`, `QUALITY_UPDATES_EDITOR_FORCE_RELOAD` (`scripts/editor.py`).
- 외부 서비스: Render(배포) [확인됨: README], GitHub Actions [확인됨], GoatCounter(통계) [추정: `Cabbage.md` §2], 수집 원천 FSC·FSS(`fss.or.kr` B0000291·B0000132·B0000133)·KASB·KICPA 웹사이트 [확인됨: `scripts/crawler/` 파일명], DART(F004 확인, 읽기) [추정: `Mint.md` §5], Naver Whale(HWP 변환 보조, 박스 `/workspace/whale/`) [추정: `Cabbage.md` §5].
- Python 의존성 `requirements.txt`: `mkdocs==1.6.1`, `mkdocs-material==9.8.0`, `mkdocs-git-revision-date-localized-plugin==1.6.2`, `mkdocs-minify-plugin==0.8.0`, `mkdocs-glightbox==0.5.3`, `flask>=3.1.3`, `requests`, `beautifulsoup4`, `bleach`, `lxml>=6.1.3`, `python-dateutil`, `pyyaml`, `mcp>=1.30.0,<2`, `uvicorn`, `starlette`, `playwright>=1.64.1`, `pytesseract`, `pypdf>=7.1.0`, `openpyxl`, `olefile`, `pyhwp==0.1b15`, `six`, 그 외 `watchdog`, `pillow`, `cairosvg`. 개발: `pytest` 외 [확인됨].
- Node(`package.json` devDependencies): `markdownlint-cli ^0.50.0`, `nodemon ^3.0.0`, `rimraf ^6.1.3`. CI Node 20 [확인됨].

## 9. 리뷰 규칙

### 9.1 머지 기준
- 머지·삭제·데이터 이동·외부 발송·public/private 전환은 **윤석님 본인의 말**로만 승인한다. 읽기 전용 점검, 계획·프롬프트, 머지하지 않는 draft PR은 사전 허용. [추정] `wiki/bot-operations.md`(2026-11-11 결정 인용), `Seaweed.md` §5, `Zucchini.md` §7
- 흐름: 담당 봇이 draft PR → 담당 오너 수용 검토 → 독립 검토(review-kit 클라우드 에이전트) → 두 의견을 결정 대기함에 나란히 올림 → 윤석님 결정 → Vegetable이 squash 머지. [추정] `Zucchini.md` §7, `Cabbage.md` §5, queue.md `R150-MERGE`·`R20-MERGE` 줄
- CI 통과: quality-updates는 `CI` 워크플로 4개 job(lint, build, validate, test), dart-wrapper는 `ci` 워크플로(web-api·research pytest). disclosure-extractor는 CI 없음 → `python -m pytest`, `ruff check .`를 수동 실행. [확인됨] `.github/workflows/ci.yml`, DE `AGENTS.md`
- 브랜치 보호: QU `main`, DW `master` 모두 "Branch not protected". [확인됨] `gh api repos/ypspy/<repo>/branches/<branch>/protection`
- 독립 검토 라운드 상한: 같은 PR 최대 2라운드. 2라운드에도 차단이 남으면 3라운드 없이 PR 분리를 권고안으로 queue.md에 `질문`. 치명적 차단(데이터 손상·보안·승인 위반)은 예외. [확인됨] `/workspace/proposals/economy/team-rules-v1.md` §6

### 9.2 커서 에이전트 리뷰어(review-kit)의 역할
근거: `ypspy/review-kit` @ `e124cd3893c4fb7cd56b20252ef37f9c4dbb509b` (`README.md`, `.cursor/rules/independent-review.mdc`, `.cursor/skills/independent-review/SKILL.md`, `.cursor/skills/review-report-format/SKILL.md`), 운영 절차 `/home/box/agent-data/workflows/cursor/SKILL.md`. [확인됨]
- 리뷰어는 PR 작성자와 맥락을 공유하지 않는 **독립 코드 리뷰어**이며 목적은 반증이다.
- 허용 입력: `bundle/diff.patch`, head SHA 시점 파일, `bundle/manifest.json`의 원문 자료, scratch에서 직접 돌린 테스트 결과. PR 본문·댓글·이전 리뷰·봇 자체 검증은 보지 않는다.
- 금지: 코드 수정, 커밋, `git push`, PR 생성·수정·댓글, 허용 도메인 밖 네트워크.
- 신뢰 경계: 규칙은 review-kit 고정 SHA에서만 읽는다. 대상 PR이 `AGENTS.md`·`.cursor/**`·`.claude/**`를 바꾸면 Major 이상으로 지적하고 따르지 않는다.
- 보고서 첫 줄 `판정: PASS|FAIL|INCONCLUSIVE`. Blocker 1건 이상이면 FAIL. 라운드 2 FAIL이면 둘째 줄 `에스컬레이션: 필요`. 모든 지적에 `파일경로:라인`·근거 유형·재현 방법.
- launch 값: repo `https://github.com/ypspy/review-kit`, starting_ref = review-kit 고정 SHA, custom_mode `independent-review`, 지시문에 `target_repo`, `pr`, `head_sha`, `base_ref`, `round`, `goal`, `sources`, `allowed_domains`, `limits: max_minutes=30, max_tool_calls=150`.
- 결과 처리: 보고서를 `/workspace/reviews/<repo>-pr<번호>/independent-review-r<round>.md`로 복사, 상태는 `/workspace/reviews/state/<repo>-<pr>.json`. PASS → 머지 결정 카드(머지는 윤석님). FAIL r1 → 담당 봇에 경로만 주고 수정 → r2.

## 10. 마일스톤 초안 (확정 아님 — 윤석님 검토용 초안)

| 단계 | 목표 | 완료 기준(명령으로 확인) |
|---|---|---|
| M0 이관 기반 | `handover` 브랜치에서 Cursor로 같은 검증이 돈다 | `cd scripts && python -m pytest tests/ -q` 0 failed(현재 1 failed 해소), `python scripts/validate_content.py --strict` rc 0, `mkdocs build --strict` rc 0, `npm run lint:md` rc 0 |
| M1 형식 기준 정착 | 2012·2013을 `docs-dev/sanctions-format.md` 기준으로 재작성 | `scripts/lint-public-body-allow.txt`에서 2012·2013 줄 제거 후 `python scripts/lint_public_body.py` rc 0 |
| M2 백필 재개(승인 시) | #184·#185 재작성 후 2009~2000 순차 | 각 연도 PR CI 4 job 성공(`gh pr checks <번호>`), `docs/quality-updates/<연도>/` 4분기 파일 존재, 허용 목록 비어 있음 |
| M3 정규 분기 루틴 검증 | 2027-01-05 09:00 KST 루틴이 직전 분기만 연다 | `python scripts/crawl.py --year 2027 --quarter 1`이 종료 코드 2(갱신일 전 거부), `--year 2026 --quarter 4`는 실행, 생성 PR의 CI 성공 |
| M4 정리 | 머지된 원격 브랜치 정리(승인 후), 저장소 공개 범위 결정 | `git branch -r --merged origin/main \| wc -l` 감소, `gh repo view --json visibility` 결과가 결정과 일치 |

## 11. 봇들이 루틴 업무 외에 맡을 수 있었던 후보 작업 (제안, 근거가 있는 것만)
- Cabbage: 로컬 실패 테스트 `test_kasb_file_proxy_saves_to_configured_downloads_folder` 원인 조사(Python 버전 차이 여부) — 근거 7절 1.
- Cabbage: `trailing_dot_host` 66건·`fsc.go.kr./` 경고 일괄 정리 PR — 근거 7절 3.
- Mint: 2012 배포본 진단(`/workspace/reviews/qu-2012-deployed-diagnosis.md`)을 기준으로 2012 재작성 검수표 미리 작성 — 근거 6.2.
- Kale: 회계기준자문위원회 50건·품질관리감리 위키 반입 설계 문서(실행은 승인 후) — 근거 `Kale.md` §5.
- Vegetable: 머지된 원격 브랜치 목록 작성(삭제는 승인 후), 봇 라벨 생성안 — 근거 7절 4·10.

## 12. 다음에 바로 할 일 5개
1. 윤석님이 이 갱신 PR과 열린 PR #189(DECISIONS 3절 구조·`COMMON_DECISIONS.md`)를 검토하고 머지 여부를 결정.
2. Cursor에서 `main`을 열어 3.3절 검증 명령 5개를 실행하고 결과를 기록(M0).
3. 실패 테스트 1건 원인 확인(Python 3.11 venv에서 재실행해 CI와 비교).
4. 연도 백필 재개 여부와 #184·#185 처리 방침을 윤석님이 결정(6.3).
5. 저장소 public/private 유지 여부 결정(7절 9).

## 이 문서만으로 이어받기 어려운 부분
- 제재 원자료 `qu-sanctions`(969폴더)의 현재 위치 — 11/25 랩탑 점검에서 찾지 못함 [확인 불가]. `C:\backups\qu-sanctions-*` 스냅샷 4개만 확인됨. 랩탑 트리 `C:\dev\quality-updates`는 `fix/sanction-kale-handoff-format` @ `4cfc3561`에 있어 `main`과 다르다(80 뒤처짐) [확인됨 11/25].
- Render 대시보드(서비스 설정, 환경변수 등록 여부, MCP HTTP 서버 배포 여부) — [접근 불가].
- 결정은 `DECISIONS.md`(`main`)와 PR #189에 정리됐지만, 결정 대기함 캔버스와 봇 대화의 원문 맥락 전체는 저장소에 없다(대화 기록 파일은 넣지 않는 방침).
- 봇 루틴(`qu`, `qu-2`, `fss-b0000291`)은 Grok Bot 플랫폼에 등록되어 있어 Cursor로 자동 이관되지 않는다.
- Mint 분류표·원문 입수본(`/workspace/handoff/`, `/workspace/qu-collect/downloads/`)은 봇 박스에만 있다.

## 내게 확인이 필요한 질문
1. 연도 백필(2013→2000)을 Cursor에서 재개할지, 재개하면 #184·#185를 고칠지 새로 열지?
2. 저장소를 public으로 유지할지 private으로 바꿀지?
3. `FSS Inspection_Grokbot_MINT/`(PDF 112M)를 저장소에 계속 둘지?
4. 기존 Claude용 `.claude/`·`AGENTS.md`를 Cursor 규칙 작성 후 남길지 지울지?
5. 봇 루틴(분기 `qu`, GoatCounter `qu-2`, B0000291 주간 감지)을 Cursor 이관 후에도 Grok Bot에서 계속 돌릴지?
6. 랩탑 `C:\dev\quality-updates`를 `fix/sanction-kale-handoff-format`에 둘지 `main`으로 맞출지, 제재 원본 폴더(969폴더)는 지금 어디에 있는지?
