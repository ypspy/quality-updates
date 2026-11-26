# Pipeline Contract Sync + M0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cursor Cloud(Python 3.12)에서 HANDOVER M0 검증을 통과시키고, README·AGENTS·CONTRIBUTING·운영 가이드가 CI(3.11)·로컬(3.11–3.12)과 같은 계약을 말하게 한다.

**Architecture:** M0 게이트 우선. 실패 테스트는 네트워크/DNS에 의존하지 않도록 최소 수정한 뒤, 문서 SSOT만 정합한다. 새 CONTRACTS 파일·`.cursor/`·백필 콘텐츠는 만들지 않는다.

**Tech Stack:** Python 3.11–3.12, pytest, Flask editor routes, MkDocs, markdownlint-cli, GitHub Actions CI(3.11).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-26-pipeline-contract-sync-design.md`
- 지원 Python 문서: **3.11–3.12**. CI `python-version: "3.11"` 유지.
- Non-Goals: 연도 백필, HITL 마커 대량 변경, `#184`/`#185`, `.cursor/` 신설, Claude `.claude/` 삭제, 유료 API, Render 설정, `CONTRACTS.md` 신설, HANDOVER 대규모 재작성, `trailing_dot_host` 일괄 정리.
- HITL·분기 시점 가드·writer 스킬·MCP 소비 경계 동작 변경 금지.
- `docs/` Markdown 변경 후 `npm run lint:md` 통과. `.markdownlint.json` 완화·파일 제외 금지.
- TASKS `T6`는 원래 「조사만」이었으나, 이 스펙(깊이 2) 승인으로 **조사+수정**이 이 PR 범위에 포함된다. `T6` 상태를 완료로 갱신한다.
- AGENTS 「커밋은 사용자 요청 시」와 Cloud Agent 제출 규칙이 충돌하면, 이 브랜치의 합의된 작업 커밋·푸시는 Cloud 절차를 따른다.

---

### Task 1: M0 — kasb_file_proxy 테스트 격리

**Files:**

- Modify: `scripts/tests/test_preview_endpoint.py` (`test_kasb_file_proxy_saves_to_configured_downloads_folder`)
- Read-only diagnose: `scripts/editor/routes/source.py`, `scripts/editor/page_attachments.py` (`fetch_kasb_bytes`), `scripts/editor/source_fetch.py` (`validate_url`)
- Production code (`source.py` / `page_attachments.py`)는 **재현 결과가 구현 계약 위반일 때만** 수정. 기본 가설은 테스트가 라이브 DNS에 의존하는 구식 mock이다다.

**Interfaces:**

- Consumes: `kasb_file_proxy` → `page_attachments.fetch_kasb_bytes(file_no, file_seq) -> tuple[bytes, str | None]` → downloads_folder에 저장 → JSON `{ok, message}`
- Produces: 해당 테스트가 네트워크/DNS 없이 200·파일 저장을 검증. 전체 pytest 0 failed.

- [ ] **Step 1: 실패 재현**

Run (repo root, venv with deps):

```bash
cd /agent/repos/quality-updates
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cd scripts && python -m pytest tests/test_preview_endpoint.py::test_kasb_file_proxy_saves_to_configured_downloads_folder -v
```

Expected: FAIL. 기록할 것: `status_code`, JSON `message`(있으면), 트레이스 한 줄. 가설: `fetch_kasb_bytes`가 `source_fetch.validate_url(KASB_DOWNLOAD_POST_URL)`에서 DNS 해석을 하고, 실패 시 `AttachmentFetchError(..., 500)` → 응답 500.

- [ ] **Step 2: 원인 분기**

- 메시지가 `Download URL policy error` / hostname resolution이거나 status 500이면 → **테스트 수정**(Step 3). production 변경 없음.
- 저장 경로·파일명 계약이 깨진 것이 확인되면 → `scripts/editor/routes/source.py`의 `kasb_file_proxy`만 최소 수정 후 Step 3의 테스트도 계약에 맞게 유지.
- 다른 원인이면 메시지·트레이스를 PR 본문에 남기고, 같은 최소 원칙으로 고친다.

- [ ] **Step 3: 테스트를 네트워크 비의존으로 고친다 (기본 경로)**

`scripts/tests/test_preview_endpoint.py`의 `test_kasb_file_proxy_saves_to_configured_downloads_folder`를 다음으로 교체한다. `requests.post` fake와 라이브 `validate_url` DNS를 제거하고, `fetch_kasb_bytes`를 스텁한다.

```python
def test_kasb_file_proxy_saves_to_configured_downloads_folder(monkeypatch, tmp_path):
    root = tmp_path
    dl = root / "downloads" / "kasb_test"
    dl.mkdir(parents=True)
    body = b"PK\x03\x04" + b"x" * 20
    calls = {}

    def fake_fetch_kasb_bytes(file_no: str, file_seq: str):
        calls["file_no"] = file_no
        calls["file_seq"] = file_seq
        return body, 'attachment; filename="a.zip"'

    monkeypatch.setattr(editor_config, "repo_root", lambda: root)
    monkeypatch.setattr(editor_config, "load_config", lambda: {"downloads_folder": "downloads/kasb_test/"})
    monkeypatch.setattr(page_attachments, "fetch_kasb_bytes", fake_fetch_kasb_bytes)

    client = editor_app.app.test_client()
    resp = client.get("/api/source/kasb_file?fileNo=-99&fileSeq=2")
    assert resp.status_code == 200
    assert resp.get_json().get("ok") is True
    assert "첨부 저장" in (resp.get_json().get("message") or "")
    assert calls == {"file_no": "-99", "file_seq": "2"}
    saved = list(dl.glob("*.zip"))
    assert len(saved) == 1
    assert saved[0].read_bytes().startswith(b"PK")
```

`editor_app._KASB_DOWNLOAD_POST_URL`·`FakeResp`·`page_attachments.requests.post` 주장은 이 테스트에서 제거한다. (URL 상수는 다른 테스트/모듈에서 유지.)

- [ ] **Step 4: 해당 테스트 + 파일 전체 통과**

```bash
cd /agent/repos/quality-updates/scripts
python -m pytest tests/test_preview_endpoint.py::test_kasb_file_proxy_saves_to_configured_downloads_folder -v
python -m pytest tests/test_preview_endpoint.py -q
```

Expected: PASS / 해당 파일 0 failed.

- [ ] **Step 5: 전체 pytest**

```bash
cd /agent/repos/quality-updates/scripts
python -m pytest tests/ -q
```

Expected: `0 failed` (passed 수는 환경에 따라 1300+).

- [ ] **Step 6: Commit**

```bash
cd /agent/repos/quality-updates
git add scripts/tests/test_preview_endpoint.py
# production을 고쳤다면 그 파일도 add
git commit -m "$(cat <<'EOF'
fix: isolate kasb_file_proxy test from live DNS

Stub fetch_kasb_bytes so M0 pytest passes without
resolving kasb.or.kr during URL policy checks.
EOF
)"
```

---

### Task 2: 문서 계약 정합 (Python 3.11–3.12 + 검증 목록)

**Files:**

- Modify: `README.md` (로컬에서 보기 — Python 줄)
- Modify: `AGENTS.md` (§5 최소 검증 블록에 `lint_public_body`; Python 지원 문구; T6/실패 테스트 참고 문장 갱신)
- Modify: `CONTRIBUTING.md` (환경에 Python 3.11–3.12가 없으면 한 줄 추가; 체크리스트에 이미 `lint_public_body` 있음)
- Modify: `docs/project/quarterly-operations-guide.md` (Phase 5 Agent 체크리스트·§7 게이트에 `lint_public_body` 교차 참조)
- Modify: `TASKS.md` (`T6` → done, 이 PR/스펙 근거)
- Modify: `HANDOVER.md` — **대규모 재작성 금지**. §7 항목 1 또는 §10 M0 행에 「테스트 격리로 M0 pytest 해소, 지원 3.11–3.12」한두 줄만 필요 시.
- Modify: `docs/superpowers/README.md` (plans 색인에 이 plan 한 줄)

**Interfaces:**

- Consumes: Task 1 완료(또는 이미 pytest 녹색)
- Produces: 문서가 동일 계약 문구를 가리킴

- [ ] **Step 1: README Python 줄**

`README.md`의 `- **Python**: 3.8 이상`을 다음으로 바꾼다.

```markdown
- **Python**: 3.11–3.12 (CI는 3.11)
```

- [ ] **Step 2: AGENTS.md §5**

긴 명령 목록에 이미 `lint_public_body.py`가 있다. **「구현·PR 후 최소 검증」** 펜스를 다음으로 맞춘다.

```bash
cd scripts && python -m pytest tests/ -q
python scripts/validate_content.py --strict
python scripts/lint_public_body.py
python scripts/export_corpus.py --strict
mkdocs build --strict
npm run lint:md
```

§5 도입부 또는 최소 검증 바로 위에 한 줄:

```markdown
지원 Python은 **3.11–3.12**다. CI는 3.11. 로컬 앞문은 [README.md](README.md).
```

`export_corpus.py --strict` 줄 주석/근처에 이미 「쓰기」가 있으면 유지. 없으면 최소 검증 아래 한 줄:

```markdown
`export_corpus.py --strict`는 `data/corpus/`를 갱신할 수 있다. 변경분이 있으면 PR에 포함하고 HITL이 검토한다.
```

실패 테스트 참고 문장(「박스 Python 3.13… TASKS」)은 Task 1 반영 후 삭제하거나 「해소됨 — 네트워크 비의존 mock, plan 2026-11-26」으로 짧게 바꾼다.

- [ ] **Step 3: CONTRIBUTING.md**

「재현 가능한 버그」/환경 안내에 Python 버전이 느슨하면 다음을 명시한다 (기존 문장 자리에 통합).

```markdown
- 지원 Python: 3.11–3.12 (CI는 3.11)
```

테스트 체크리스트의 `lint_public_body` 항목은 이미 있으면 유지.

- [ ] **Step 4: quarterly-operations-guide.md**

Phase 5 **Agent 체크리스트**에 다음을 validate 줄 근처에 추가한다.

```markdown
- [ ] `python scripts/lint_public_body.py` 통과 (형식: `docs-dev/sanctions-format.md`)
```

§7 품질 게이트 표에 CI validate job과 맞추어 한 행을 추가한다 (번호는 기존 체계 유지).

```markdown
| G5b | `lint_public_body.py` 통과 | 시스템 |
```

G5와 G6 사이에 둔다. Phase·역할 표·mermaid는 바꾸지 않는다.

§6 검증 펜스에 `lint_public_body`가 없으면 `validate_content.py --strict` 다음 줄에 추가한다.

```bash
python scripts/lint_public_body.py
```

- [ ] **Step 5: TASKS.md T6**

`T6` 행을 완료로 바꾼다.

```markdown
| T6 | pytest 1실패 원인 조사·수정 | 네트워크 비의존 mock으로 M0 pytest 0 failed | done | 스펙 2026-11-26-pipeline-contract-sync |
```

- [ ] **Step 6: HANDOVER (선택·최소)**

§7.1 또는 §10 M0 행에만, 사실이 바뀐 한 줄을 고친다. 봇 표·랩탑 경로·추정 표기는 건드리지 않는다.

- [ ] **Step 7: superpowers README plans 색인**

`docs/superpowers/README.md`의 Plans 표 맨 위에:

```markdown
| 2026-11-26 | [pipeline-contract-sync.md](plans/2026-11-26-pipeline-contract-sync.md) | M0 게이트·Python 3.11–3.12 문서 정합 |
```

- [ ] **Step 8: lint md**

```bash
cd /agent/repos/quality-updates
npm run lint:md
```

Expected: exit 0.

- [ ] **Step 9: Commit**

```bash
git add README.md AGENTS.md CONTRIBUTING.md docs/project/quarterly-operations-guide.md TASKS.md docs/superpowers/README.md docs/superpowers/plans/2026-11-26-pipeline-contract-sync.md
# HANDOVER.md를 고쳤으면 포함
git commit -m "$(cat <<'EOF'
docs: align pipeline contracts for Python 3.11–3.12

Sync README/AGENTS/ops guide verification lists with CI
and record T6 done under the M0 contract-sync spec.
EOF
)"
```

---

### Task 3: M0 전체 게이트 + PR 갱신

**Files:**

- No intentional code edits. May include `data/corpus/` only if `export_corpus.py --strict` rewrites it.

**Interfaces:**

- Consumes: Task 1–2
- Produces: DoD 증거(로그), 갱신된 PR 본문

- [ ] **Step 1: M0 + CI 정합 명령**

```bash
cd /agent/repos/quality-updates
source .venv/bin/activate
cd scripts && python -m pytest tests/ -q
cd ..
python scripts/validate_content.py --strict
python scripts/lint_public_body.py
mkdocs build --strict
npm run lint:md
```

Expected: 모두 exit 0. (`lint_public_body`의 trailing_dot_host **경고**는 기존 정책 유지; exit 0이면 통과.)

- [ ] **Step 2: export_corpus (쓰기 검증)**

```bash
python scripts/export_corpus.py --strict
git status --short data/corpus/
```

Expected: exit 0. `data/corpus/`가 바뀌면 커밋에 포함하고 PR에 「corpus 쓰기 검증」을 명시. 안 바뀌면 추가 커밋 없음.

- [ ] **Step 3: Push + PR body 갱신**

```bash
git push -u origin cursor/pipeline-contract-sync-afeb
```

PR 본문에 넣을 증거:

- Python 버전 (`python3 --version`)
- pytest 요약 줄
- validate / lint_public_body / mkdocs / lint:md exit 0
- Non-Goals 준수 (백필·`.cursor/` 없음)

- [ ] **Step 4: DoD 체크**

- [ ] Spec Intent·Non-Goals 충족
- [ ] 3.12에서 pytest 0 failed
- [ ] validate / mkdocs / lint:md exit 0
- [ ] lint_public_body 문서·실행 정합
- [ ] README Python 3.11–3.12, CI 3.11 유지
- [ ] 백필·HITL 마커·유료 API 변경 없음

---

## Spec coverage (self-review)

| Spec 요구 | Task |
|-----------|------|
| M0 pytest 0 failed | Task 1, 3 |
| validate / mkdocs / lint:md | Task 3 |
| lint_public_body 문서 정합 | Task 2, 3 |
| Python 3.11–3.12 문서, CI 3.11 유지 | Task 2 |
| export_corpus 쓰기 명시 | Task 2, 3 |
| Non-Goals | Global Constraints + Task 2/3 범위 |
| HANDOVER 최소 | Task 2 Step 6 |
| T6 | Task 2 Step 5 |
