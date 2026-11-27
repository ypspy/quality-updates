# 분기 운영 작업지시서

**대상**: Quality Updates 정규 분기 운영 (Cursor 유일 실행안)
**버전**: 2026-11
**관련 문서**: [README.md](../../README.md), [CONTRIBUTING.md](../../CONTRIBUTING.md),
[editor-curation-workflow.md](editor-curation-workflow.md),
[quality-updates-writer 스킬](../../.claude/skills/quality-updates-writer/SKILL.md),
[sanctions-format.md](../../docs-dev/sanctions-format.md),
[kasb-meetings-collector.md](kasb-meetings-collector.md),
스펙 [cursor-quarterly-routine-design](../superpowers/specs/2026-11-26-cursor-quarterly-routine-design.md)

---

## 1. 목적

금융당국(FSS, FSC, KICPA, KASB) 보도·공지·질의회신·제재·회의록 공개분을 분기 단위로 입수·선별·요약한 뒤 공개 사이트에 반영한다.

본 문서는 **Cursor Agent가 실행**하고 **전문가가 최종 머지만 승인**하는 정규 분기 루틴의 정본이다. 그록봇(`qu` 등) 자동 루틴은 중지되어 있다.

---

## 2. 역할

| 역할 | 담당 | 책임 |
|------|------|------|
| **Agent** | Cursor | 수집·**큐레이션**·요약·nav 초안·배포 전처리·**draft PR** |
| **전문가** | 사용자 | **최종 배포 전 `main` 머지 결정만** |
| **시스템** | 스크립트·CI | 게이트 (validate, lint_public_body, pytest, mkdocs, lint:md, corpus) |

**원칙**

- Agent는 원문에서 확인된 내용만 요약한다 (스킬 RIGID). 추정·보완 금지.
- 전문가에게 단계별 큐레이션·요약 사실 검증을 필수 칸으로 두지 않는다. 필수 칸은 **머지 결정**뿐이다.
- 파이프라인은 볼트에 직접 쓰지 않는다.
- 제재·요약·회의록·편집기 마커 **형식**은 이 가이드에 장문으로 두지 않는다. 위 관련 문서·스킬을 본다.

---

## 3. 정규 분기 루틴 — Cursor

시점: **분기 다음 달 5일 09:00 KST 이후**. 그 전 `crawl.py`는 해당 분기를 종료 코드 2로 거절한다. nav/index 최신 링크도 그 전 금지. 예외는 `data/qu-early-allow.txt` 표준 경로만.

### 3.1 당일 체크리스트

각 행: 단계 · 레인 · 담당 · 핵심 · 완료 신호.

| # | 단계 | 레인 | 담당 | 핵심 | 완료 신호 |
|---|------|------|------|------|-----------|
| 0 | 시점·대상 분기 | A | Agent | 달력으로 `--year`/`--quarter` 확정 | 대상 분기 확정 |
| 1 | 보도·공지 수집 | A | Agent | `crawl.py --dry-run` 권장 후 `--year/--quarter` | 표준 경로 md |
| 1b | 금감원 질의회신 | B | Agent | `crawl_fss_replies.py --limit 1` → 전량 | `data/fss-replies/` |
| 1c | 회계기준원 질의회신 | C | Agent | `crawl_kasb_replies.py` (증분·실패 재시도는 기존 CLI) | `data/kasb-replies/` |
| 1d | 제재 안건·의사록 (공개분) | D | Agent | 당일까지 공개된 금융위·증선위 안건·의결서·의사록 입수·연결 (`downloads/sanctions`, `attach_sanction_minutes` 등). **미공개 의사록은 당일 강제하지 않음** | 회차 폴더·분기 md 반영 |
| 1d′ | 직전 분기 D 미공개분 보완 | D | Agent | **이번 루틴에서** 직전 분기 문서의 미공개였던 의사록·안건을 재조회해 보완 | 직전 분기 md/첨부 갱신 |
| 1e | 회의록 (공개분) | E | Agent | 당일까지 공개된 회계기준위·자문위 등 회의록 입수 (`kasb_meetings` 등). 상세는 [kasb-meetings-collector.md](kasb-meetings-collector.md) | 수집물·draft PR |
| 2 | 큐레이션 | A | Agent | 스킵·출처. 전문가 필수 아님 | 마커 반영 |
| 3 | 요약 | A | Agent | `quality-updates-writer` SUMMARIZE (당일 반영된 D·E 공개분 포함) | note 블록 |
| 4 | nav/index | A | Agent | 갱신일 이후 초안, 자동 머지 없음 | draft PR에 포함 |
| 5 | 배포 전처리 | A | Agent | `prepare_deploy`, `export_corpus --strict`, 게이트 | CI + corpus · **draft PR** |
| 5b | 머지·배포 | — | 전문가 | **최종 배포 전 PR 머지 결정만** | Render |

루틴 표 밖(한 줄·링크만): Whale, 볼트 raw export, B0000291 **주간**.

### 3.2 D·E 타이밍

- **D:** 당일 = 그 시점까지 공개된 제재 자료 입수. 늦게 공개되는 의사록 등은 **다음 분기 루틴의 1d′**에서 직전 분기를 보완한다.
- **E:** 당일까지 **공개분**만 입수. 미공개분은 이후 루틴에서 같은 방식으로 이어서 받는다.
- E: `scripts/crawler/kasb_meetings.py`는 인자가 없으면 안내 후 끝난다. 실수집은 승인 전이다. 연속 HTTP 간격은 `--delay`(기본 0.3초)이고 `--dry-run`에는 적용하지 않는다. 상세: [kasb-meetings-collector.md](kasb-meetings-collector.md).

### 3.3 과거분·누적 아카이브

분기마다 “그 분기 DB”를 새로 만들지 않는다. 1b–1e는 **누적 저장소에 키가 있으면 skip**, 없으면(또는 실패 재시도면) 추가한다.

**정본:** [intake-archive.md](intake-archive.md) (레인 B–E 경로·키·git·볼트·상세 링크).

| 레인 | 누적 위치 | git | skip/증분 |
|------|-----------|-----|-----------|
| B | `data/fss-replies/{board}/{nttId}/` + `manifest.jsonl` | `item.md`·manifest만. 첨부 HWP 등은 ignore | 완료 건 skipped |
| C | `data/kasb-replies/{seq}/` | item·첨부 커밋 | 있으면 재수집 안 함 |
| D | `downloads/sanctions/{회차}/` | `downloads/` ignore. 사이트는 `docs/quality-updates/` | 회차 폴더·연결 상태 누적; 미공개→다음 분기 보완 |
| E | `downloads/kasb-meetings/…` + `_state.json` | `downloads/` ignore | 끝난 seq 재수집 안 함 |

공개 노출은 아카이브 전체가 아니라 분기 md·corpus 쪽이다. 볼트 `export_*_raw`는 복사본이다.

**후속:** gitignore 정합(옵션 2), 볼트·박스 이관 계약(옵션 3) — [intake-archive.md](intake-archive.md) §4.

---

## 4. 시점·경로 규칙

- 표준 경로: `docs/quality-updates/YYYY/YYYY-MM-DD_to_YYYY-MM-DD.md`
- 분기 문서와 nav·「최신」 링크는 그 분기 다음 달 5일 09:00 KST 이후에만 만든다.
- `crawl.py`는 `--year`와 `--quarter`를 명시한다. 인자 없는 `crawl.py`는 갱신일이 지난 마지막 분기를 고른다. 명시 기간이 갱신일 전인 달력 분기면 종료 코드 2로 거부한다.
- 조기 예외는 윤석님 본인의 명시 승인만 인정한다. 승인은 `data/qu-early-allow.txt`의 정확한 표준 경로로만 기록한다.
- 본문 dated list는 과거→현재. Appendix A는 크롤 수집 순(최신→과거) 유지.
- 기존 큐레이션본이 있으면 crawl이 덮지 않는다.

---

## 5. 품질 게이트

| # | 게이트 | 비고 |
|---|--------|------|
| G1 | draft PR (Agent) | 자동 머지 없음 |
| G2 | `python scripts/validate_content.py --strict` | |
| G3 | `python scripts/lint_public_body.py` | |
| G4 | `cd scripts && python -m pytest tests/ -q` | |
| G5 | `mkdocs build --strict` | |
| G6 | `npm run lint:md` | `docs/` 변경 시 |
| G7 | `python scripts/export_corpus.py --strict` | corpus diff를 PR에 포함 |
| G8 | 전문가 머지 승인 → Render | 필수 칸 = 머지 결정만 |

Python 문서·로컬: 3.11–3.12. CI: 3.11.

---

## 6. 명령 빠른 참조

```bash
# A — 보도·공지
python scripts/crawl.py --year YYYY --quarter N
python scripts/editor.py
# 또는 제안만: python scripts/auto_curate.py …
# 요약: quality-updates-writer 스킬 SUMMARIZE
python scripts/prepare_deploy.py
python scripts/export_corpus.py --strict

# B — 금감원 질의회신
python scripts/crawl_fss_replies.py --limit 1
python scripts/crawl_fss_replies.py

# C — 회계기준원 질의회신
python scripts/crawl_kasb_replies.py

# D — 제재 안건·의사록 (공개분)
python scripts/attach_sanction_minutes.py <분기.md>
# 형식: docs-dev/sanctions-format.md

# E — 회의록 (공개분; 실수집은 기존 승인)
cd scripts && python -m crawler.kasb_meetings --dry-run --limit 3
# 승인 후: --live --limit N
```

형식·마커 상세: [quality-updates-writer](../../.claude/skills/quality-updates-writer/SKILL.md),
[editor-curation-workflow.md](editor-curation-workflow.md),
[sanctions-format.md](../../docs-dev/sanctions-format.md),
[kasb-meetings-collector.md](kasb-meetings-collector.md).

### 6.1 제재 출처 계약 (요약)

장문 형식은 [sanctions-format.md](../../docs-dev/sanctions-format.md)·writer 스킬을 본다. 가이드에 남기는 계약만:

- 안건 분석 첫 불릿은 `attach_sanction_minutes.decision_source_bullet` 의결서 출처다. fileNo는 2로 고정하지 않는다. 2026년 1분기부터 이 줄이 없으면 `validate_content.py --strict`가 오류다.
- 위원 논의 의사록 출처는 `attach_sanction_minutes.minutes_source_bullet`가 만든다. fileNo를 하드코딩하지 않는다. PDF가 없고 HWP·HWPX 의사록만 있으면 그 파일을 고른다. 첨부가 없으면 `미공개`. 2026년 1분기부터 출처 줄이 있으면 getFile 주소와 「의사록」 표시 이름이 필요하다.

---

## 7. Automation 적용 방법 (문서 정본 · UI 미등록)

**상태:** 저장소에 프롬프트 정본은 있다. Cursor UI에서 Automation은 **아직 만들지 않았고 enable하지 않는다.**  
에이전트는 Automation을 생성·활성화할 수 없다. 등록은 사용자가 [cursor.com/automations](https://cursor.com/automations)에서 한다.

| 항목 | 내용 |
|------|------|
| 수단 | Cursor Automation (또는 동등 예약 Cloud Agent) |
| 프롬프트 정본 | [quarterly-automation-prompt.md](quarterly-automation-prompt.md) (본문은 가이드 §3 체크리스트를 따른다) |
| 트리거 | cron `0 0 5 1,4,7,10 *` (UTC) ≈ 1/5·4/5·7/5·10/5 09:00 KST. 첫 대상 예: 2027-01-05 |
| 산출 | **draft PR만**. 커밋·PR 본문에 레인·단계·검증 결과 |
| 금지 | 머지, force-push, 비밀값, 볼트 직접 쓰기, early-allow 없는 조기 nav |
| 전문가 | Automation이 연 draft PR에 대해 **머지 여부만** 결정 |
| 활성화 조건 | **V-249 전체 해제**(파일럿 3회·한도 X·명시 승인) 후. 예외 해제(Automation만)가 아님 |

### 7.1 사용자 UI 등록 체크리스트 (해제 승인 후)

1. V-249가 AGENTS.md §0 기준으로 해제됐는지 확인한다.
2. [cursor.com/automations/new](https://cursor.com/automations/new) (또는 `/automate`)를 연다.
3. Trigger = Scheduled, cron `0 0 5 1,4,7,10 *` (UTC).
4. Repository = `ypspy/quality-updates`, base branch `main`.
5. Prompt = [quarterly-automation-prompt.md](quarterly-automation-prompt.md) 펜스 안 텍스트 전체.
6. Pull request 생성 유지. draft만. 머지 도구 사용 안 함.
7. Save 후 **Enable**은 해제 승인 직후에만. 등록 후 이 절 상태 문장을 「등록됨」으로 고친다.

---

## 8. 관련 문서·개정 이력

| 문서·경로 | 용도 |
|-----------|------|
| [AGENTS.md](../../AGENTS.md) | Agent 허브·분기 라우팅 |
| [editor-curation-workflow.md](editor-curation-workflow.md) | 마커·skip·prepare_deploy |
| [curation-rules.md](curation-rules.md) | 큐레이션 규칙 제안 |
| `scripts/crawl.py` 등 | 레인 A–E 수집 CLI |
| [pipeline-contract-sync](../superpowers/specs/2026-11-26-pipeline-contract-sync-design.md) | 게이트·exit·Python 계약 |
| [quarterly-automation-prompt.md](quarterly-automation-prompt.md) | Automation 실행 프롬프트 정본 |
| [intake-archive.md](intake-archive.md) | 입수 아카이브 B–E SSOT |
| [quarterly-automation-docs](../superpowers/specs/2026-11-27-quarterly-automation-docs-design.md) | Automation 문서·V-249 전체 해제 목표 |

| 날짜 | 변경 |
|------|------|
| 2026-11-27 | 입수 아카이브 SSOT(`intake-archive.md`) 링크. Automation 프롬프트·UI 체크리스트. enable은 V-249 전체 해제 후 |
| 2026-11-26 | Cursor 유일 실행안으로 재작성 (스펙 cursor-quarterly-routine). 과거 그록 운영·Phase 장문 삭제. Automation은 적용 방법만 |
