# TASKS — Quality Updates 작업 큐

상태: `ready` · `blocked` · `paused` · `done` · `optional`
근거는 DECISIONS ID, 사용자 답, PR, HANDOVER를 적는다.
에이전트는 `blocked`/`paused`를 스스로 풀지 않는다.

장기 목표·V-249·머지 규칙은 [AGENTS.md](AGENTS.md)가 원본이다.

---

## 지금 진행 가능

| ID | 목표 | 완료 기준 | 상태 | 근거 |
|----|------|-----------|------|------|
| T10 | 백필 재개(2012·2013 재작성 → 2009~2000) | 연도 **한 건씩** draft PR. 작성 Agent가 [summary-formats](docs-dev/summary-formats/) Format·[완결성](docs-dev/summary-formats/completeness.md) Fail을 **자체 수정한 뒤** draft. 1파 한도 X=2M Tokens 안 | **ready** | T8 해제. DoD SSOT #201–#204. #184·#185는 T9 |
| T5 | 린트·형식 잔여 (`trailing_dot_host` 등) | 추가 경고 정리. 연도 본문 대량 재작성은 별도 연도 PR(T10) | optional | #197 도구 개선 완료 |

---

## done (최근)

| ID | 목표 | 상태 | 근거 |
|----|------|------|------|
| T1–T4 | gitignore·AGENTS·TASKS·HANDOVER 이관 | done | #191·#190 등 |
| T5 도구 | `lint_public_body` trailing_dot 요약 | done | #197 |
| T6 | pytest 1실패 mock 격리 | done | 스펙 pipeline-contract-sync |
| T15 | 분기 Automation 프롬프트·§7 문서 | done | #195. 정본 [quarterly-automation-prompt.md](docs/project/quarterly-automation-prompt.md) |
| T16 | Automation UI 등록·enable | **done** | 파일럿 **전** Enable. 사용자 확인 2026-11-27. UI: [Quality Updates - Quarterly Routine](https://cursor.com/automations/a821548c-e9f8-11f1-a83f-1254d1a6b4db) |
| T17 | V-249 파일럿 1 (문서 정합) | done | #196 |
| T18 | 입수 아카이브 문서 SSOT (범위 1) | done | #198 |
| T8 | V-249 **전체** 해제 | **done** | 파일럿 #196–#198 + X=2M Tokens + 사용자 `ok` 2026-11-27 |
| T19 | 2026 Q3 요약 형식·완결성 DoD | **done** | #201 스펙 · #202 family DoD·excerpts · #203 Format Fail 반영 · #204 완결성 DoD. **본문 재작성은 T10** (감사만 함) |
| T20 | QU 분기 Automation Slack 알림 | **done** | 사용자 붙임 2026-11-27 (에이전트 bc-01a20b0b). Automation `a821548c-e9f8-11f1-a83f-1254d1a6b4db` Enable 유지. 에이전트는 Automation 재설정하지 않음(AGENTS §0) |
| T13 | Grok 루틴 → Cursor Automation 이관 | **done** | 사용자 확인 2026-11-27. 후속은 T15·T16·T20(QU Quarterly Routine). `qu`/`qu-2`/`fss-b0000291` **재가동 안 함**(AGENTS §0·§7) |

---

## blocked / paused

| ID | 목표 | 완료 기준 | 상태 | 근거 |
|----|------|-----------|------|------|
| T7 | `FSS Inspection_Grokbot_MINT/` 처분 | 용량·에이전트 읽기 필요성 보고 후 사용자 결정 → 유지/이전/gitignore | **blocked** | 사용자 답 1. 용량 112M·364파일. 일상 경로 스크립트는 이 폴더를 읽지 않음 |
| T9 | #184·#185 처리 | 사용자 방침 후 | **blocked**(보류) | 사용자 답 2(d). V-249와 별개 |
| T11 | 정규 분기 루틴 **첫 실행 검증** | 2027-01-05 09:00 KST 이후. Automation 기동 또는 동등 실행 → `crawl.py --year 2027 --quarter 1` 등 가이드 §3 · draft PR. (이관·프롬프트·Enable·Slack은 T13·T15·T16·T20으로 **이미 준비**) | **blocked**(일자) | V-031, V-222 |
| T12 | 장기 목표 1 완료 | 무인 파이프라인 4회 + 2025→2000 백필 + 2026Q3 골드셋 **형태 적용** | **blocked**(장기) | V-205. 형태 **기준**(DoD)은 T19 done. 적용·백필·무인 4회는 미완 |
| T14 | 품질관리감리 자동 파이프라인·백필 | — | **blocked**(비대상) | 장기 목표 「지금 하지 않는 것」 |

---

## 참고 (비큐)

- 랩탑 `C:\dev\quality-updates`: `fix/sanction-kale-handoff-format` @ `4cfc3561`. untracked `summary_bench/` HTML 4개(각 ~660–680KB). 저장소 테스트는 `fixtures/fss_reply_*.html`만 사용.
- 제재 969 정본: 박스 `/workspace/qu-collect/downloads/sanctions/` (저장소 밖).
- `summary_bench/`: 이 clone에는 없음. 테스트 의존 없음 → `.gitignore`에 추가(실수 커밋 방지).
- V-249 1파 한도: **X = 2,000,000 비캐시 Tokens** (AGENTS.md §0).
- DoD 감사(콘텐츠 미수정): Format Fail ~269 / 완결성 Fail ~1354 (2012–2026 Q3). 해소는 T10 연도 PR.
- 작성 Fail → 머지 검토 전 Agent 자체 수정. 독립 리뷰는 Pass/Fail 기록만(AGENTS §6.3).
