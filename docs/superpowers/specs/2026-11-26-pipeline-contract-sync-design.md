# 분기 파이프라인 계약 동기화 + M0 안정화 — 설계 스펙

**날짜**: 2026-11-26  
**상태**: 설계 합의됨. 이 파일 검토 후 구현 계획.  
**범위**: HANDOVER M0 검증이 Cursor Cloud(Python 3.12)에서 통과하고, Agent·사람 진입 문서가 CI(3.11)·로컬(3.11–3.12)과 같은 계약을 말하게 한다.

합의: Intent = C(파이프라인 안정화·계약 동기화), 깊이 = 문서 + 계약 강제 최소 코드, Python = 3.11–3.12, 접근 = M0 게이트 우선(안 2).

참고: [HANDOVER.md](../../../HANDOVER.md) §3.3·§7·§10(M0), [AGENTS.md](../../../AGENTS.md), [docs/project/quarterly-operations-guide.md](../../project/quarterly-operations-guide.md), [readme-front-door](2026-11-07-readme-front-door-design.md).

---

## 1. Intent & Why

인수인계 후 Cursor에서 이어받을 때, 문서·CI·로컬이 서로 다른 Python 버전과 검증 목록을 말해 M0을 재현하기 어렵다. 목표는 **측정 가능한 안정화**(M0 exit 0)와 **계약 문구 정합**이다. 기능 추가가 아니다.

성공 기준:

- 이 환경(Python 3.12)에서 M0 검증 명령이 모두 성공한다.
- README·AGENTS·CONTRIBUTING·운영 가이드가 지원 Python **3.11–3.12**와 동일 검증 목록을 가리킨다.
- CI는 기존처럼 Python **3.11 단일**을 유지한다.

---

## 2. Non-Goals

- 연도 백필(2013→2000)·draft PR #184·#185 재개
- 공개 분기 본문·HITL 마커(`<!-- skip -->`, `<!-- source: … -->`) 대량 변경
- 원격 브랜치 정리·저장소 public/private 전환
- `.cursor/` 규칙 신설, Claude `.claude/` 삭제
- 크롤러·편집기 UX·MCP 프로토콜 변경
- 유료 클라우드/API 호출, Render 대시보드·환경변수 변경
- `CONTRACTS.md` 등 새 SSOT 파일 신설(안 3 배제)
- HANDOVER.md 대규모 재작성

---

## 3. Constraints

- 기존 SSOT 유지: 분기 운영 = `docs/project/quarterly-operations-guide.md`, Agent 허브 = `AGENTS.md`, PR/CI = `CONTRIBUTING.md`, 로컬 앞문 = `README.md`.
- HITL 큐레이션·분기 시점 가드(다음 달 5일 09:00 KST)·`quality-updates-writer` 요약 포맷·MCP 소비 경계는 **동작 변경 없음**. 교차 참조만 점검한다.
- `docs/` Markdown을 바꾸면 `npm run lint:md` 통과. `.markdownlint.json`을 끄거나 파일을 검사에서 빼지 않는다.
- 커밋·PR은 이 브랜치의 합의된 범위만. 사용자가 요청한 제출 절차를 따른다.
- 유료 API·비밀값은 사용하지 않는다.

---

## 4. Contracts & Interfaces

| 계약 | 조치 |
|------|------|
| 지원 Python | 문서에 **3.11–3.12**로 명시. CI workflow `python-version: "3.11"` 유지 |
| Agent 검증 목록 (`AGENTS.md` §5) | CI·CONTRIBUTING과 맞추어 `python scripts/lint_public_body.py` 추가 |
| 기존 §5 명령 | `pytest`, `validate_content.py --strict`, `export_corpus.py --strict`, `mkdocs build --strict`, `npm run lint:md` 유지 |
| `export_corpus.py --strict` | 쓰기 검증이다. 산출물(`data/corpus/`)이 바뀌면 PR에 포함하고 HITL 검토 대상임을 문서에 한 줄로 명시 |
| HITL·시점·writer·MCP | 문구 모순만 고치고 스키마·마커·스킬 RIGID 규칙은 그대로 |

코드 최소 변경 대상: `scripts/tests/test_preview_endpoint.py::test_kasb_file_proxy_saves_to_configured_downloads_folder` (및 필요 시 `scripts/editor/routes/source.py`의 `kasb_file_proxy`).

절차:

1. Python 3.12에서 재현하고 응답 본문·트레이스로 원인 확정.
2. 구현이 계약을 어기면 `kasb_file_proxy`를 고친다.
3. 테스트가 구식이면 테스트만 고친다.
4. 해당 테스트와 전체 `cd scripts && python -m pytest tests/ -q`가 0 failed.

---

## 5. 문서 변경 대상

| 파일 | 변경 |
|------|------|
| `README.md` | "Python 3.8 이상" → **3.11–3.12** |
| `AGENTS.md` | §5에 `lint_public_body.py` 추가. 지원 버전은 README와 모순 없게 한 줄 또는 링크 |
| `CONTRIBUTING.md` | 환경·체크리스트가 CI·AGENTS와 모순이면 맞춤. 없으면 유지 |
| `docs/project/quarterly-operations-guide.md` | Phase 5/품질 게이트에 공개본문 린트 교차 참조가 빠졌으면 보강. Phase·역할 구조는 변경하지 않음 |
| `HANDOVER.md` | 대규모 재작성 금지. M0 관련(지원 버전·실패 테스트 해소) 한두 줄만 필요 시 갱신 |
| `docs/superpowers/README.md` | 이 스펙·후속 plan 색인 한 줄 |

---

## 6. Acceptance Scenarios

### Happy path

1. venv에서 `pip install -r requirements.txt -r requirements-dev.txt` 후 Python 3.12.
2. `cd scripts && python -m pytest tests/ -q` → 0 failed.
3. `python scripts/validate_content.py --strict` → exit 0.
4. `python scripts/lint_public_body.py` → exit 0 (기존 allowlist·경고 정책 유지; 이번 범위에서 trailing_dot_host 일괄 정리는 하지 않음).
5. `mkdocs build --strict` → exit 0.
6. `npm run lint:md` → exit 0.
7. README·AGENTS가 3.11–3.12와 동일 검증 목록을 가리킨다.

### Edge & failure

- 실패 테스트가 환경 의존이면 원인과 수정 근거를 PR·스펙 이행 기록에 남긴다.
- `export_corpus.py --strict`가 `data/corpus/`를 바꾸면 커밋에 포함하고, 문서에 쓰기 검증임을 명시한다. 임의로 corpus만 손대지 않는다.
- 문서만 바꾸고 코드가 필요 없으면 코드 단계는 “재현 후 통과 확인”으로 끝낸다.

---

## 7. 구현 순서 (개요)

1. M0 재현: 실패 테스트 원인 확정 → 최소 수정 → pytest 전체 통과.
2. 문서 정합: README → AGENTS §5 → CONTRIBUTING → 운영 가이드 교차 참조 → 필요 시 HANDOVER 한 줄.
3. 게이트 재실행 + `npm run lint:md`.
4. `docs/superpowers/README.md` 색인 갱신.

세부 체크리스트는 승인 후 `docs/superpowers/plans/2026-11-26-pipeline-contract-sync.md`에 둔다.

---

## 8. Definition of Done

- [ ] 이 스펙의 Intent·계약·Non-Goals가 충족된다.
- [ ] Python 3.12에서 `pytest` 0 failed, `validate_content.py --strict`, `mkdocs build --strict`, `npm run lint:md` 통과.
- [ ] `lint_public_body.py`가 AGENTS 검증 목록과 CI validate job에 문서상 정합한다.
- [ ] 지원 Python이 README·관련 온보딩에서 3.11–3.12로 일치한다. CI는 3.11 유지.
- [ ] 백필·공개 분기 md·HITL 마커·`.cursor/`·유료 API·Render 설정 변경이 없다.
- [ ] 문서·주석과 실제 검증 명령 사이 모순이 해소된다.
