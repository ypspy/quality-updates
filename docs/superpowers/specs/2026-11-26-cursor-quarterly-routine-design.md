# Cursor 정규 분기 루틴 — 설계 스펙

**날짜**: 2026-11-26  
**상태**: 설계 합의됨. 이 파일 검토 후 구현 계획.  
**범위**: [`docs/project/quarterly-operations-guide.md`](../../project/quarterly-operations-guide.md)를 **Cursor 유일 실행안**으로 다시 쓰고, Automation **적용 방법**은 문서만 남긴다(실등록은 중지 해제 후).

합의:

- Intent = 정규 분기 체크리스트를 Cursor 기준으로 재작성 (brainstorming B)
- 범위 = Phase 1–5 + 같은 날 금감원 질의회신 증분
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
- 필수 칸에 Phase 1–5와 `crawl_fss_replies` 증분만 있다.
- Automation 적용 방법 절이 있고, 실등록·활성화 지시/커밋이 없다.
- AGENTS에서 이 가이드 루틴 절로 가는 한 줄이 있다.

---

## 2. Non-Goals

- Cursor Automation / 예약 Cloud Agent **실등록·활성화·파일럿 실행**
- V-249 해제, 그록 `qu`/`qu-2`/`fss-b0000291` 재가동
- 저장소 전역 `HITL` → `전문가` 치환 (별도 spec)
- 연도 백필·#184·#185·공개 분기 본문·HITL 마커 대량 변경
- 제재 의사록·Whale·볼트 raw·B0000291 주간을 **당일 필수**로 승격
- 크롤러·편집기·CI 코드 변경, 유료 API, Render 설정
- 별도 `quarterly-routine-checklist.md` 신설 (가이드 SSOT 유지)
- 제재·요약 **형식 규칙**을 가이드에 장문으로 재서술 (기존 스킬·`docs-dev/sanctions-format.md`·editor 문서로 링크)

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
6. **명령 빠른 참조** — 루틴에 필요한 명령만 (질의회신 증분 포함). 곁가지 장문은 링크
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

각 행: **단계 | 담당 | 핵심 명령·행동 | 완료 신호**

| # | 단계 | 담당 | 핵심 | 완료 신호 |
|---|------|------|------|-----------|
| 0 | 시점·대상 분기 | Agent | 갱신일 이후 달력으로 `--year`/`--quarter` 확정 (예: 2026 Q4 → 2027-01-05 이후) | 대상 분기 확정 |
| 1 | 수집 | Agent | `crawl.py --dry-run` 권장 후 `crawl.py --year/--quarter` | 표준 경로 md |
| 1b | 질의회신 증분 | Agent | `crawl_fss_replies.py --limit 1` 시범 → 전량 | `data/fss-replies/` |
| 2 | 큐레이션 | Agent | 스킵·출처 (`editor`/`auto_curate` 등 기존 수단). **전문가가 필수로 돌리지 않음** | 마커 반영 |
| 3 | 요약 | Agent | `quality-updates-writer` SUMMARIZE | note 블록 |
| 4 | nav/index | Agent | `mkdocs.yml`, index 초안 (갱신일 이후). 자동 머지 없음 | draft PR에 포함 |
| 5 | 배포 전처리 | Agent | `prepare_deploy`, `export_corpus --strict`, 게이트 | CI 초록 + corpus diff · **draft PR** |
| 5b | 머지·배포 | 전문가 | **최종 배포 전 PR 머지 결정만** | Render |

당일 필수 아님: `attach_sanction_minutes`, Whale, 볼트 export, B0000291 주간. 의사록 공개 후 창은 관련 문서로만 링크. 전문가가 임의로 본문을 더 보는 것은 막지 않으나, **루틴 필수 칸은 머지 결정뿐이다**.

---

## 6. Automation 적용 방법 (문서만)

가이드에 짧은 절을 둔다. **구현 PR은 Automation을 생성·활성화하지 않는다.**

| 항목 | 내용 |
|------|------|
| 수단 | Cursor Automation (또는 동등 예약 Cloud Agent) |
| 트리거 | 분기 다음 달 5일 09:00 KST **이후** (첫 대상 예: 2027-01-05) |
| 프롬프트 정본 | 이 가이드의 「정규 분기 루틴 — Cursor」 체크리스트 |
| 산출 | **draft PR만** (수집·큐레이션·요약·nav·게이트 포함). 커밋·PR 본문에 단계·검증 결과 |
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
- [ ] 체크리스트 범위 = Phase 1–5 + `crawl_fss_replies` 증분.
- [ ] Automation 적용 방법 절 존재. 실등록·활성화 없음.
- [ ] AGENTS 한 줄 링크. HITL 전역 개명 없음.
- [ ] `npm run lint:md` 통과.
- [ ] 코드·백필·유료 API·Render 변경 없음.
