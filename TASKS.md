# TASKS — Quality Updates 작업 큐

상태: `ready` · `blocked` · `paused` · `done` · `optional`
근거는 DECISIONS ID, 사용자 답, PR, HANDOVER를 적는다.
에이전트는 `blocked`/`paused`를 스스로 풀지 않는다.

장기 목표·V-249·머지 규칙은 [AGENTS.md](AGENTS.md)가 원본이다.

---

## 지금 진행 가능

| ID | 목표 | 완료 기준 | 상태 | 근거 |
|----|------|-----------|------|------|
| T1 | `.gitignore`·`.env.example` 점검 | summary_bench ignore, PUBLIC·값 금지 주석, 코드 env 이름과 일치 | ready → 이 PR | 사용자 답 9(c) |
| T2 | `AGENTS.md` 보강 | 장기 목표, V-249 해제 문안, 머지 4항목, 하지 말 것 | ready → 이 PR | 사용자 답 6·5 |
| T3 | `TASKS.md` 신설 | 이 파일 | ready → 이 PR | 사용자 답 9(b) |
| T4 | #190 HANDOVER 사실 정정 | #189 머지·COMMON 없음·열린 PR·결정 반영. `[추정]`은 그록봇 확인 전 유지 | ready | 사용자 답 3·4 |
| T5 | 린트·형식 잔여 (`trailing_dot_host` 등) | `lint_public_body` 개선 PR. **연도 본문 재작성 없음** | optional | V-249 허용 |
| T6 | pytest 1실패 원인 조사 | 3.11 vs 3.13 재현 기록. 수정은 별도 승인 | ready(조사만) | HANDOVER·그록봇 |

---

## blocked / paused

| ID | 목표 | 완료 기준 | 상태 | 근거 |
|----|------|-----------|------|------|
| T7 | `FSS Inspection_Grokbot_MINT/` 처분 | 용량·에이전트 읽기 필요성 보고 후 사용자 결정 → 유지/이전/gitignore | **blocked** | 사용자 답 1. 용량 112M·364파일. 일상(린트·형식·QU 분기) 경로에서 스크립트가 이 폴더를 읽지 않음. fss-review 원문 작업·스펙만 경로를 언급. 품질관리감리 자동 파이프라인은 「지금 하지 않는 것」 |
| T8 | V-249 해제(연도 백필·새 클라우드 에이전트) | AGENTS.md §0 파일럿 3회 + 표 보고 + 사용자 수치(X) + 명시 승인 | **blocked** | V-249. X·한도 단위 비움 |
| T9 | #184·#185 처리 | 사용자 방침 후 | **blocked**(보류) | 사용자 답 2(d) |
| T10 | 백필 재개(2012·2013 재작성 → 2009~2000) | T8 해제 후 | **blocked** | V-249, 장기 목표 1 |
| T11 | 정규 분기 루틴 검증 | 2027-01-05 09:00 KST 이후. `crawl.py --year 2027 --quarter 1` → 종료 코드 2 | **blocked**(일자) | V-031, V-222 |
| T12 | 장기 목표 1 완료 | 무인 파이프라인 4회 + 2025→2000 백필 + 2026Q3 골드셋 형태 | **blocked**(장기) | V-205 |
| T13 | Grok 루틴 | 재개 지시 | **paused** | 사용자 답 7(c) |
| T14 | 품질관리감리 자동 파이프라인·백필 | — | **blocked**(비대상) | 장기 목표 「지금 하지 않는 것」 |

---

## 참고 (비큐)

- 랩탑 `C:\dev\quality-updates`: `fix/sanction-kale-handoff-format` @ `4cfc3561`. untracked `summary_bench/` HTML 4개(각 ~660–680KB). 저장소 테스트는 `fixtures/fss_reply_*.html`만 사용.
- 제재 969 정본: 박스 `/workspace/qu-collect/downloads/sanctions/` (저장소 밖).
- `summary_bench/`: 이 clone에는 없음. 테스트 의존 없음 → `.gitignore`에 추가(실수 커밋 방지).
