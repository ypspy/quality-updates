# 분기 Automation 문서 정본 — 설계 스펙

**날짜**: 2026-11-27  
**상태**: 설계 합의됨 (사용자: V-249 **B 전체 해제 목표** + 산출 **1** 문서·프롬프트).  
**선행**: [cursor-quarterly-routine-design](2026-11-26-cursor-quarterly-routine-design.md), [quarterly-operations-guide.md](../../project/quarterly-operations-guide.md) §7.

합의:

- Intent = Cursor Automation용 **실행 프롬프트 정본**과 UI 등록 체크리스트를 저장소에 둔다. 에이전트는 Automation을 **생성·활성화하지 않는다** (UI/API create 없음).
- V-249 = **전체 해제(B)** 를 목표로 한다. 해제는 AGENTS §0 파일럿 3회 + 사용량 보고 + 한도 X + **사용자 명시 승인** 후에만. 이 PR에서 중지를 풀지 않는다.
- 산출 1 = 프롬프트 md + 가이드 §7·AGENTS·문서 지도 갱신. Terraform·지금 수동 파일럿 Cloud Agent 실행은 Non-Goal.
- 스케줄 초안: cron `0 0 5 1,4,7,10 *` (UTC) ≈ 1/5·4/5·7/5·10/5 09:00 KST. 첫 대상 2027-01-05. **enable은 V-249 해제 후 사용자**.

---

## 1. Intent & Why

분기 루틴 가이드는 Automation **적용 방법**만 있고 붙여 넣을 프롬프트가 없다. Cursor Automation은 UI에서 만들고, 에이전트 MCP는 조회만 가능하다. 정본 프롬프트·등록 절차를 저장소에 두면 V-249 해제 직후 사용자가 바로 등록할 수 있다.

---

## 2. Non-Goals

- Cursor UI에서 Automation 생성·enable (에이전트 불가 / 이번 PR 범위 밖)
- Terraform `cursor_platform_workflow`
- V-249 즉시 해제, 파일럿 3회 실행, 한도 X 확정
- 연도 백필·`#184`/`#185` 재개 (해제는 승인 후 별도)
- Grok `qu` 재가동
- 유료 API·비밀값 커밋

---

## 3. Deliverables

| 산출 | 경로 |
|------|------|
| 실행 프롬프트 정본 | `docs/project/quarterly-automation-prompt.md` |
| 가이드 §7 | UI 등록 체크리스트 + 프롬프트 링크. 상태: 문서 준비 / **미등록·미활성** |
| AGENTS.md | Automation 문서 링크; V-249에 「전체 해제 목표(B), 파일럿 전」 한 줄 |
| 문서 지도 | `docs/project/README.md` 표에 프롬프트 행 |
| 스펙·plan 색인 | `docs/superpowers/README.md` |

프롬프트 필수 내용: 가이드 「정규 분기 루틴 — Cursor」 A–E + 1d′; **draft PR만**; 머지·force-push·비밀값·볼트 직접 쓰기·early-allow 없는 조기 nav 금지; 전문가는 머지 결정만.

---

## 4. Acceptance

1. 프롬프트만 복사해도 Automation 본문으로 쓸 수 있다.
2. 가이드 §7이 UI 등록 단계와 V-249 전제·미등록 상태를 분명히 한다.
3. V-249 중지 문구는 유지된다 (해제 아님).
4. `npm run lint:md` exit 0.

---

## 5. Definition of Done

- [ ] 위 Deliverables 반영
- [ ] Automation enable / V-249 해제 커밋 없음
- [ ] lint:md 통과, PR 오픈
