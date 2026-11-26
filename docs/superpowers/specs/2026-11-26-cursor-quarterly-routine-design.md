# Cursor 정규 분기 루틴 — 설계 스펙

**날짜**: 2026-11-26  
**상태**: 설계 합의됨. 이 파일 검토 후 구현 계획.  
**범위**: [`docs/project/quarterly-operations-guide.md`](../../project/quarterly-operations-guide.md)를 **Cursor 유일 실행안**으로 다시 쓰고, Automation **적용 방법**은 문서만 남긴다(실등록은 중지 해제 후).

합의:

- Intent = 정규 분기 체크리스트를 Cursor 기준으로 재작성 (brainstorming B)
- 범위 = 분기 입수 **레인 A–E 전부**를 루틴 표에 둔다. **당일(5일 09:00 KST)** = A 본문 Phase 1–5 + B 금감원 질의회신 + C 회계기준원 질의회신 + **D 제재 안건·(당일까지 공개된) 의사록** + **E 회의록(당일까지 공개분)**. D의 **직전 분기 미공개분**(예: 늦게 올라온 의사록)은 **다음 분기 루틴에서 보완**한다.
- 과거분 = **누적 아카이브** (분기별 별도 DB 없음). 1b–1e는 기존 키는 skip하고 **해당 분기 신규(+ D 직전 미공개 보완)** 만 붙인다. 저장 위치·git 경계는 §5.4. **아카이브 스키마·보관·볼트 규격화는 후속 `/brainstorming`·별도 spec** (이번 Non-Goal)
- 협업 = **그록봇 실운영과 동일**: Agent가 수집·**큐레이션**·요약·nav 초안·배포 전처리까지 수행하고 draft PR을 연다. **전문가(사용자)는 최종 배포 전 PR 머지 결정만** 한다 (단계별 큐레이션·요약 검증을 필수로 두지 않음)
- 산출 = 가이드 본문을 Cursor 실행 중심으로 재구성 (과거 그록 운영 장문 삭제·축소)
- Automation = 적용 방법 절만 (등록·활성화는 Non-Goal)
- `HITL` → `전문가` 저장소 전면 개명 = **별도 spec** (이 가이드 새 본문에는 `전문가`만 사용)

참고: [AGENTS.md](../../../AGENTS.md) (그록 루틴 중지·V-249·머지 규칙), [pipeline-contract-sync](2026-11-26-pipeline-contract-sync-design.md), [HANDOVER.md](../../../HANDOVER.md) M3.

---

## 1. Intent & Why

그록봇(`qu` 등)으로 돌리던 분기 운영과, 인수인계 후 Cursor·AGENTS 중지 상태가 어긋나 있다. 운영 정본이 긴 과거 서술과 HITL/봇 전제를 들고 있어 **2027-01-05 정규 분기**를 그대로 따라가기 어렵다.

목표는 가이드를 위에서 아래로 읽으면 **Cursor Agent가 실행하고 전문가가 머지만 승인**하는 그록봇 시절 역할로 정규 분기를 끝낼 수 있게 하는 것이다. 스케줄 Automation은 “나중에 이렇게 건다”만 스펙·가이드에 고정하고, **지금은 켜지 않는다**.

성공 기준:

- 가이드 본문의 실행 경로가 Cursor뿐이며, 과거 운영안이 본문의 절반 이상을 차지하지 않는다.
- 역할: Agent = 큐레이션 포함 실행·draft PR, 전문가 = **최종 배포 전 머지 결정만**.
- 루틴 표에 레인 A–E가 있다. D·E는 **당일까지 공개분 입수**, D 미공개분은 **다음 분기 루틴에서 보완**한다.
- Automation 적용 방법 절이 있고, 실등록·활성화 지시/커밋이 없다.
- AGENTS에서 이 가이드 루틴 절로 가는 한 줄이 있다.

---

## 2. Non-Goals

- Cursor Automation / 예약 Cloud Agent **실등록·활성화·파일럿 실행**
- V-249 해제, 그록 `qu`/`qu-2`/`fss-b0000291` 재가동
- 저장소 전역 `HITL` → `전문가` 치환 (별도 spec)
- 연도 백필·#184·#185·공개 분기 본문·HITL 마커 대량 변경
- D를 “의사록이 전부 공개될 때까지 당일 입수를 미루는” 모델로 두는 것 (당일 공개분만 받고, 미공개는 다음 분기에 보완)
- E를 당일 루틴 밖으로만 두는 것 (당일까지 **공개분**은 당일 입수)
- E 실수집 코드/네트워크를 이번 PR에서 새로 승인·활성화하는 것; 가이드는 칸·명령·링크로 두고, `kasb_meetings` 실수집 승인은 기존 원칙
- Whale·볼트 raw·B0000291 **주간**을 정규 분기 당일 필수로 승격 (루틴 표 밖·한 줄·링크)
- **입수 아카이브 규격화** (스키마 통일, 보관 정책, 볼트 SSOT, D/E `downloads/` 백업·이관 규칙 등) — 후속 brainstorming
- 크롤러·편집기·CI 코드 변경, 유료 API, Render 설정
- 별도 `quarterly-routine-checklist.md` 신설 (가이드 SSOT 유지)
- 제재·요약·회의록 **형식 규칙**을 가이드에 장문으로 재서술 (스킬·`docs-dev/sanctions-format.md`·`kasb-meetings-collector.md`·editor 문서로 링크)

---

## 3. Constraints

- 분기 운영 SSOT 파일은 계속 `docs/project/quarterly-operations-guide.md`다.
- 시점: 분기 다음 달 5일 09:00 KST. `crawl.py` 거부(exit 2), nav/index 최신 링크, `data/qu-early-allow.txt` 예외 규칙은 **유지**.
- **역할 (그록봇 실운영 반영):** Agent가 수집·큐레이션(스킵·출처)·요약·nav/index 초안·`prepare_deploy`/corpus·게이트까지 수행하고 **draft PR**을 연다. 전문가(사용자)는 **최종 배포 전 `main` 머지 승인만** 한다. 전문가에게 단계별 큐레이션·요약 사실 검증을 필수 칸으로 두지 않는다.
- 검증 게이트는 계약 동기화 이후 목록을 따른다: pytest, validate `--strict`, `lint_public_body`, export_corpus `--strict`, mkdocs `--strict`, `lint:md`. Python 문서 3.11–3.12, CI 3.11.
- `docs/` Markdown 변경 후 `npm run lint:md` 통과. 규칙 완화·파일 제외 금지.
- 파이프라인은 볼트에 직접 쓰지 않는다 (현행 원칙 유지).

---

## 4. 가이드 재구성

### 4.1 본문 골격 (유일 실행안)

대략 다음 순서로 **다시 쓴다**. 기존 장문 Phase·그록 전제 문단은 삭제하거나 한 줄·링크로 줄인다.

1. **목적** — 분기 수집·선별·요약·공개 (짧게)
2. **역할** — Agent = Cursor (수집·큐레이션·요약·nav 초안·배포 전처리·draft PR). 전문가 = 최종 배포 전 머지 결정만. 시스템 = CI/스크립트 게이트
3. **정규 분기 루틴 — Cursor** — §5 체크리스트 (실행 정본)
4. **시점·경로 규칙** — 5일 09:00 KST, 표준 경로, early-allow (현행 문장 압축)
5. **품질 게이트** — 표로 유지·갱신 (`lint_public_body` 포함)
6. **명령 빠른 참조** — 레인 A–E에 쓰는 명령만. 형식·수집기 장문은 링크
7. **Automation 적용 방법** — §6 (문서만)
8. **관련 문서·개정 이력**

제재 형식·요약 슬림·editor 마커 세부는 각각 스킬·`docs-dev/sanctions-format.md`·`editor-curation-workflow.md`로 보낸다. 가이드에 의사록 fileNo 장문 등을 **복사해 두지 않는다**.

### 4.2 삭제·축소 대상 (예시)

- 그록봇·캐비지/케일 인계를 전제로 한 서술
- 웨일/볼트 경로를 “당일 필수”처럼 읽히는 장문 (필요 시 “별도·중지” 한 줄)
- Phase마다 중복된 긴 체크리스트 (루틴 표로 통합)
- “상세 규칙으로 구 Phase 전체를 보존”하는 이중 구조

---

## 5. 실행 체크리스트 (루틴 정본)

각 행: **단계 | 레인 | 타이밍 | 담당 | 핵심 | 완료 신호**

### 5.1 당일 — 분기 다음 달 5일 09:00 KST 이후

| # | 단계 | 레인 | 담당 | 핵심 | 완료 신호 |
|---|------|------|------|------|-----------|
| 0 | 시점·대상 분기 | A | Agent | 달력으로 `--year`/`--quarter` 확정 | 대상 분기 확정 |
| 1 | 보도·공지 수집 | A | Agent | `crawl.py --dry-run` 권장 후 `--year/--quarter` | 표준 경로 md |
| 1b | 금감원 질의회신 | B | Agent | `crawl_fss_replies.py --limit 1` → 전량 | `data/fss-replies/` |
| 1c | 회계기준원 질의회신 | C | Agent | `crawl_kasb_replies.py` (증분·실패 재시도는 기존 CLI) | `data/kasb-replies/` |
| 1d | 제재 안건·의사록 (공개분) | D | Agent | 당일까지 공개된 금융위·증선위 안건·의결서·의사록 입수·연결 (`downloads/sanctions`, `attach_sanction_minutes` 등). **미공개 의사록은 당일 강제하지 않음** | 회차 폴더·분기 md 반영 |
| 1d′ | 직전 분기 D 미공개분 보완 | D | Agent | **이번 루틴에서** 직전 분기 문서의 미공개였던 의사록·안건을 재조회해 보완 | 직전 분기 md/첨부 갱신 |
| 1e | 회의록 (공개분) | E | Agent | 당일까지 공개된 회계기준위·자문위 등 회의록 입수 (`kasb_meetings` 등). 상세는 `kasb-meetings-collector.md` | 수집물·draft PR |
| 2 | 큐레이션 | A | Agent | 스킵·출처. 전문가 필수 아님 | 마커 반영 |
| 3 | 요약 | A | Agent | `quality-updates-writer` SUMMARIZE (당일 반영된 D·E 공개분 포함) | note 블록 |
| 4 | nav/index | A | Agent | 갱신일 이후 초안, 자동 머지 없음 | draft PR에 포함 |
| 5 | 배포 전처리 | A | Agent | `prepare_deploy`, `export_corpus --strict`, 게이트 | CI + corpus · **draft PR** |
| 5b | 머지·배포 | — | 전문가 | **최종 배포 전 PR 머지 결정만** | Render |

**D 타이밍 요약:** 당일 = 그 시점까지 공개된 제재 자료 입수. 늦게 공개되는 의사록 등은 **다음 분기 루틴의 1d′**에서 직전 분기를 보완한다 (구 “8주 후 별도 창만” 모델이 아님).

**E 타이밍 요약:** 당일까지 **공개분**만 입수. 미공개분은 이후 루틴에서 같은 방식으로 이어서 받는다.

루틴 표 밖(한 줄·링크만): Whale, 볼트 raw export, B0000291 **주간**. 전문가 필수 칸은 **머지 결정뿐**이다.

### 5.4 과거분·누적 아카이브 (현행 As-Is, 가이드에 짧게)

분기마다 “그 분기 DB”를 새로 만들지 않는다. 1b–1e는 **누적 저장소에 키가 있으면 skip**, 없으면(또는 실패 재시도면) 추가한다.

| 레인 | 누적 위치 | git | skip/증분 |
|------|-----------|-----|-----------|
| B | `data/fss-replies/{board}/{nttId}/` + `manifest.jsonl` | `item.md`·manifest만. 첨부 HWP 등은 ignore | 완료 건 skipped |
| C | `data/kasb-replies/{seq}/` | item·첨부 커밋 | 있으면 재수집 안 함 |
| D | `downloads/sanctions/{회차}/` | `downloads/` ignore. 사이트는 `docs/quality-updates/` | 회차 폴더·연결 상태 누적; 미공개→다음 분기 보완 |
| E | `downloads/kasb-meetings/…` + `_state.json` | `downloads/` ignore | 끝난 seq 재수집 안 함 |

공개 노출은 아카이브 전체가 아니라 분기 md·corpus 쪽이다. 볼트 `export_*_raw`는 복사본이다.

**후속 (별도 brainstorming):** 레인 간 스키마·보관·gitignore·볼트·박스/`downloads` 이관 규칙을 하나의 아카이브 규격으로 고정하는 작업. 이번 가이드 재작성은 위 As-Is를 **한 표로 적는 것**까지다.

---

## 6. Automation 적용 방법 (문서만)

가이드에 짧은 절을 둔다. **구현 PR은 Automation을 생성·활성화하지 않는다.**

| 항목 | 내용 |
|------|------|
| 수단 | Cursor Automation (또는 동등 예약 Cloud Agent) |
| 트리거 | 분기 다음 달 5일 09:00 KST **이후** (첫 대상 예: 2027-01-05) |
| 프롬프트 정본 | 이 가이드의 「정규 분기 루틴 — Cursor」 체크리스트 (§5.1: A–E 당일 공개분 + D 직전 미공개 보완) |
| 산출 | **draft PR만** (A–E 당일 공개분·큐레이션·요약·nav·게이트; D 1d′ 보완 포함 가능). 커밋·PR 본문에 레인·단계·검증 결과 |
| 금지 | 머지, force-push, 비밀값, 볼트 직접 쓰기, early-allow 없는 조기 nav |
| 전문가 | Automation이 연 draft PR에 대해 **머지 여부만** 결정 |
| 활성화 조건 | V-249 및 「새 클라우드 에이전트 중지」해제 + 사용자 명시 승인 후 |

---

## 7. 교차 문서

| 파일 | 변경 |
|------|------|
| `docs/project/quarterly-operations-guide.md` | §4–6에 따라 재구성 |
| `AGENTS.md` | 분기 운영 행/절에 가이드 루틴 절 한 줄 링크. 전면 HITL 개명 없음 |
| `docs/project/README.md` | SSOT 표는 가이드 정본 유지. 한 줄 요약만 필요 시 |
| `docs/superpowers/README.md` | 이 스펙·후속 plan 색인 |

---

## 8. Acceptance

### Happy path

1. 가이드를 연다 → Agent가 큐레이션까지 돌리고 전문가는 머지만 하는 시나리오를 말로 재현할 수 있다.
2. Automation 절을 읽고 “미등록·승인 후”, 산출은 draft PR임을 확인한다.
3. `npm run lint:md` exit 0.
4. AGENTS에서 가이드 루틴으로 점프한다.

### Edge

- 갱신일 전 crawl → 계속 exit 2 / nav 금지 (문구 유지).
- 제재·질의회신 **형식** 질문이 가이드에 없으면 링크된 정본으로 보낸다.

---

## 9. Definition of Done

- [ ] 가이드 본문이 Cursor 유일 실행안이다. 과거 그록 운영 장문이 본문을 지배하지 않는다.
- [ ] 역할: Agent가 큐레이션 포함 실행·draft PR, 전문가 필수 칸 = 최종 머지 결정만.
- [ ] 체크리스트에 레인 A–E가 있다. D·E 당일 공개분 입수, D 직전 미공개분 다음 분기 보완이 명시된다.
- [ ] 누적 아카이브·키 단위 skip(§5.4)이 가이드에 짧게 있고, 아카이브 규격화는 후속으로 명시된다.
- [ ] Automation 적용 방법 절 존재. 실등록·활성화 없음.
- [ ] AGENTS 한 줄 링크. HITL 전역 개명 없음.
- [ ] `npm run lint:md` 통과.
- [ ] 코드·백필·유료 API·Render 변경 없음.
