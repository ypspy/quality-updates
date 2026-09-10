# Consumption MCP Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 런타임에서 `audit-regulatory-lens`를 제거하고, 소비 정본을 공개 사이트 + 읽기 전용 MCP(인용 계약)로 문서·instructions에 고정한다.

**Architecture:** 생산 파이프라인과 MCP tool/스키마는 그대로 둔다. 렌즈 스킬 디렉터리를 삭제하고, 런타임 문서 4종에서 렌즈 진입점을 뺀다. README·FastMCP `instructions`에 다른 Agent 인용 계약 5줄을 넣는다. 분기 Phase 5에 `export_corpus --strict`를 한 줄로 추가한다. Hosted Render 서비스 생성은 HITL이며 이 계획이 대시보드를 조작하지 않는다.

**Tech Stack:** Python 3, pytest, FastMCP (`scripts/mcp_server/app.py`), MkDocs 문서, 기존 `export_corpus.py`

**Spec:** `docs/superpowers/specs/2026-09-10-consumption-mcp-product-design.md`

## Global Constraints

- 크롤러, 편집기, `quality-updates-writer`, 코퍼스 JSON 스키마, MCP tool 시그니처는 변경하지 않는다. `scripts/mcp_server/app.py`는 `instructions` 문자열(및 그 상수)만 변경한다.
- `.cursor/mcp.json`과 `render.yaml`은 만들지 않고 커밋하지 않는다. `data/corpus/` JSONL을 이 작업에서 재생성·커밋하지 않는다.
- `docs/superpowers/specs/2026-06-27-audit-regulatory-lens-skill-design.md`와 `docs/superpowers/plans/2026-06-27-audit-regulatory-lens-skill.md`와 `.superpowers/sdd/`는 삭제하지 않는다.
- 런타임 문서에서 렌즈 경로 `.claude/skills/audit-regulatory-lens`를 소비 진입점으로 안내하지 않는다. 대상 파일은 `AGENTS.md`, `README.md`, `docs/project/README.md`, `docs/project/quarterly-operations-guide.md`뿐이다.
- 사용자가 이 실행에서 커밋을 명시하지 않으면 모든 Commit 스텝을 건너뛴다.
- 검증: `cd scripts && python -m pytest tests/ -q` / `python scripts/validate_content.py --strict` / `python scripts/export_corpus.py --strict` / `mkdocs build --strict`

---

## File map

| File | Action |
|------|--------|
| `scripts/tests/test_consumption_contract.py` | Create — 렌즈 제거·인용 계약·Phase 5 export 회귀 |
| `.claude/skills/audit-regulatory-lens/` | Delete — SKILL.md, reference/keywords.md, reference/output-samples.md |
| `AGENTS.md` | Modify — 렌즈 라우팅·제약 삭제, MCP를 다른 Agent 소비로 명시 |
| `docs/project/README.md` | Modify — Agent 표·SSOT 렌즈 행 삭제, 소비 SSOT = 사이트+MCP |
| `README.md` | Modify — MCP 절을 사이트/Agent 분리 + 인용 계약 + Hosted 절차로 교체 |
| `docs/project/quarterly-operations-guide.md` | Modify — Phase 5·게이트·명령에 `export_corpus.py --strict` |
| `scripts/mcp_server/app.py` | Modify — `CITATION_INSTRUCTIONS` 상수, FastMCP에 전달 |
| `docs/superpowers/plans/2026-06-27-mcp-corpus.md` | Modify — 렌즈 follow-up 취소 |
| `docs/superpowers/README.md` | Modify — 이 plan 색인 (spec 행·렌즈 런타임 제거 표기는 이미 있음) |
| `docs/superpowers/specs/2026-09-10-consumption-mcp-product-design.md` | Modify — 상태를 승인됨 |

`scripts/mcp_server/core.py`, `stdio.py`, `http.py`, `scripts/corpus/`, `scripts/export_corpus.py`는 변경하지 않는다.

---

### Task 1: 소비 계약 회귀 테스트 (실패 확인)

**Files:**
- Create: `scripts/tests/test_consumption_contract.py`
- Test: `scripts/tests/test_consumption_contract.py`

**Interfaces:**
- Consumes: 없음
- Produces: `REPO_ROOT = Path(__file__).resolve().parents[2]`. 이후 태스크가 맞출 문자열: `CITATION_INSTRUCTIONS` in `scripts/mcp_server/app.py` (Task 3에서 생성). 본 태스크는 `app.py`를 수정하지 않는다.

- [ ] **Step 1: Write the failing tests**

Create `scripts/tests/test_consumption_contract.py` with this exact content:

```python
# -*- coding: utf-8 -*-
"""Runtime consumption contract: no lens skill; MCP citation rules."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LENS_DIR = REPO_ROOT / ".claude" / "skills" / "audit-regulatory-lens"
RUNTIME_DOCS = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "project" / "README.md",
    REPO_ROOT / "docs" / "project" / "quarterly-operations-guide.md",
)
LENS_PATH_NEEDLE = ".claude/skills/audit-regulatory-lens"


def test_lens_skill_directory_removed():
    assert not LENS_DIR.exists()


def test_runtime_docs_do_not_route_to_lens():
    for path in RUNTIME_DOCS:
        text = path.read_text(encoding="utf-8")
        assert LENS_PATH_NEEDLE not in text, path


def test_readme_has_citation_contract_and_hosted_attach():
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "no_summary" in text
    assert "MCP_API_KEY" in text
    assert "/health" in text
    assert "search_regulatory_updates" in text
    assert "get_regulatory_update" in text


def test_quarterly_ops_export_corpus_strict():
    text = (
        REPO_ROOT / "docs" / "project" / "quarterly-operations-guide.md"
    ).read_text(encoding="utf-8")
    assert "export_corpus.py --strict" in text


def test_fastmcp_citation_instructions():
    import sys

    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from mcp_server.app import CITATION_INSTRUCTIONS

    lower = CITATION_INSTRUCTIONS.lower()
    assert "read-only" in lower
    assert "no_summary" in CITATION_INSTRUCTIONS
    assert "do not invent" in lower
    assert "search_regulatory_updates" in CITATION_INSTRUCTIONS
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd scripts
python -m pytest tests/test_consumption_contract.py -v
```

Expected: FAIL. `test_lens_skill_directory_removed` because the directory exists. `test_runtime_docs_do_not_route_to_lens` because `AGENTS.md`, `README.md`, and `docs/project/README.md` still contain `.claude/skills/audit-regulatory-lens`. `test_readme_has_citation_contract_and_hosted_attach` because README has no `/health` and still points at the lens. `test_quarterly_ops_export_corpus_strict` because the ops guide has no `export_corpus.py --strict`. `test_fastmcp_citation_instructions` because `CITATION_INSTRUCTIONS` is not defined (`ImportError`).

- [ ] **Step 3: Commit (only if the user asked to commit)**

```bash
git add scripts/tests/test_consumption_contract.py
git commit -m "test: add consumption contract regression (lens off, MCP cite)"
```

---

### Task 2: 렌즈 삭제와 런타임 라우팅

**Files:**
- Delete: `.claude/skills/audit-regulatory-lens/SKILL.md`
- Delete: `.claude/skills/audit-regulatory-lens/reference/keywords.md`
- Delete: `.claude/skills/audit-regulatory-lens/reference/output-samples.md`
- Modify: `AGENTS.md`
- Modify: `docs/project/README.md`

**Interfaces:**
- Consumes: Task 1 needles `LENS_DIR`, `LENS_PATH_NEEDLE`
- Produces: 런타임 진입점에 렌즈 경로 없음. `AGENTS.md` MCP 행이 다른 Agent 읽기 전용 소비를 가리킴.

- [ ] **Step 1: Delete the lens skill tree**

Delete these three files (then remove empty directories `reference/` and `audit-regulatory-lens/` if they remain):

- `.claude/skills/audit-regulatory-lens/SKILL.md`
- `.claude/skills/audit-regulatory-lens/reference/keywords.md`
- `.claude/skills/audit-regulatory-lens/reference/output-samples.md`

Do not delete anything under `docs/superpowers/` or `.superpowers/sdd/`.

- [ ] **Step 2: Patch AGENTS.md routing and constraints**

In `AGENTS.md` section 1, replace the two rows

```markdown
| **감사 규제 렌즈 (Planning/Execution/Reporting)** | [.claude/skills/audit-regulatory-lens/SKILL.md](.claude/skills/audit-regulatory-lens/SKILL.md) | ADVISORY; writer와 **동시 사용 금지** |
| **MCP 코퍼스 export·서버** | [docs/superpowers/specs/2026-06-27-mcp-corpus-design.md](docs/superpowers/specs/2026-06-27-mcp-corpus-design.md) | `export_corpus.py` → stdio/HTTP MCP |
```

with this single row:

```markdown
| **다른 Agent 소비 (MCP, 읽기 전용)** | [README MCP 절](README.md) · [mcp-corpus spec](docs/superpowers/specs/2026-06-27-mcp-corpus-design.md) | `export_corpus.py` → stdio/HTTP. 인용 계약. 코퍼스 쓰기는 생산 레인만. |
```

In `AGENTS.md` section 3, replace

```markdown
- **감사 규제 렌즈**: `audit-regulatory-lens` 스킬은 코퍼스 **읽기 전용** — `docs/quality-updates/` 및 파이프라인 `.md` **수정 금지**
```

with:

```markdown
- **코퍼스 소비**: 다른 Agent는 MCP만 읽는다. 소비 경로로 `docs/quality-updates/`를 grep하지 않는다. 큐레이션·요약·nav 쓰기는 생산 레인만.
```

In `AGENTS.md` section 5, replace the verification block with:

```markdown
```bash
cd scripts && python -m pytest tests/ -q
python scripts/validate_content.py --strict
python scripts/export_corpus.py --strict
mkdocs build --strict
```
```

Leave templates A–D and the writer routing row unchanged.

- [ ] **Step 3: Patch docs/project/README.md**

In the Agent table, delete this row only:

```markdown
| [.claude/skills/audit-regulatory-lens/SKILL.md](../../.claude/skills/audit-regulatory-lens/SKILL.md) | 감사 Planning/Execution/Reporting 규제 렌즈 (ADVISORY) |
```

In the SSOT table, replace

```markdown
| 감사 규제 렌즈 | `.claude/skills/audit-regulatory-lens/SKILL.md` |
| MCP 코퍼스 export | `scripts/export_corpus.py` → `data/corpus/` |
| MCP 서버 | `scripts/mcp_server/` (stdio + HTTP) |
```

with:

```markdown
| 소비 (사람) | 공개 MkDocs 사이트 |
| 소비 (다른 Agent) | `scripts/mcp_server/` (stdio + HTTP), `data/corpus/` |
| MCP 코퍼스 export | `scripts/export_corpus.py` → `data/corpus/` |
```

- [ ] **Step 4: Run lens tests (expect remaining README/ops/instructions failures)**

Run:

```bash
cd scripts
python -m pytest tests/test_consumption_contract.py::test_lens_skill_directory_removed tests/test_consumption_contract.py::test_runtime_docs_do_not_route_to_lens -v
```

Expected: `test_lens_skill_directory_removed` PASS. `test_runtime_docs_do_not_route_to_lens` FAIL until Task 3 rewrites `README.md` (it still contains `.claude/skills/audit-regulatory-lens`). That remaining failure is expected.

- [ ] **Step 5: Commit (only if the user asked to commit)**

```bash
git add AGENTS.md docs/project/README.md
git add -u .claude/skills/audit-regulatory-lens
git commit -m "remove audit-regulatory-lens skill from runtime routing"
```

---

### Task 3: README 인용 계약, Phase 5 export, FastMCP instructions

**Files:**
- Modify: `README.md` (MCP 절, lines around 300–320)
- Modify: `docs/project/quarterly-operations-guide.md`
- Modify: `scripts/mcp_server/app.py`

**Interfaces:**
- Consumes: Task 1 tests `test_readme_has_citation_contract_and_hosted_attach`, `test_quarterly_ops_export_corpus_strict`, `test_fastmcp_citation_instructions`, `test_runtime_docs_do_not_route_to_lens`
- Produces: `mcp_server.app.CITATION_INSTRUCTIONS: str` — FastMCP `instructions=` 인자로 전달되는 모듈 상수

- [ ] **Step 1: Replace the README MCP section**

In `README.md`, replace the entire section starting at `## MCP 코퍼스 (에이전트·Cursor)` through the sentence `설계: [docs/superpowers/specs/2026-06-27-mcp-corpus-design.md](...)` (stop before `## 배포`) with:

```markdown
## MCP 코퍼스 (다른 Agent)

사람은 [공개 사이트](https://quality-updates.onrender.com)에서 조회한다. 다른 Agent는 같은 공개 경계의 **읽기 전용 MCP**에 붙는다. 문헌 검색 MCP와 역할이 다르다: 이 코퍼스는 한국 감독·기준(FSS, FSC, KICPA, KASB) **큐레이션 사실**만 제공한다.

Tool: `list_quarterly_periods`, `search_regulatory_updates`, `get_regulatory_update`.

**인용 계약**

1. 주장마다 `agency`, `date`, `title`, `url` (가능하면 `id`)를 붙인다.
2. note bullets·표에 있는 내용만 쓴다. 없는 숫자·해석은 창작이다.
3. `summary_status=no_summary`면 제목·URL만 힌트이고, 본문 사실로 쓰지 않는다.
4. skip 항목은 코퍼스에 없다. 사이트 원문 md에서 되살리지 않는다.
5. 코퍼스는 읽기 전용이다. 큐레이션·요약·nav는 생산 레인만 한다.

```bash
# 코퍼스 생성 (skip 제외, Appendix A 이전만)
python scripts/export_corpus.py --strict

# 로컬 stdio MCP (Cursor). 워크스페이스 절대경로가 든 .cursor/mcp.json은 커밋하지 않는다.
# .cursor/mcp.json 예시:
# { "mcpServers": { "quality-updates": {
#     "command": "python", "args": ["scripts/mcp_server/stdio.py"],
#     "cwd": "/path/to/quality-updates" } } }
python scripts/mcp_server/stdio.py

# Hosted HTTP (Render 2번째 Web Service — 사이트와 별도)
# cwd=scripts, PYTHONPATH=scripts, env MCP_API_KEY 필수
# Start: uvicorn mcp_server.http:app --host 0.0.0.0 --port $PORT
# Health: GET /health
# MCP: POST /mcp  Authorization: Bearer <MCP_API_KEY>
# 실제 호스트 URL은 HITL이 Render에서 만든 뒤 이 절에 적는다.
```

설계: [docs/superpowers/specs/2026-06-27-mcp-corpus-design.md](docs/superpowers/specs/2026-06-27-mcp-corpus-design.md) · [소비 제품 spec](docs/superpowers/specs/2026-09-10-consumption-mcp-product-design.md)
```

Do not mention `audit-regulatory-lens` in `README.md`.

- [ ] **Step 2: Add export to quarterly operations Phase 5**

In `docs/project/quarterly-operations-guide.md`:

1. Change the version line `**버전**: 2026-06` to `**버전**: 2026-09`.

2. In the Phase 5 mermaid subgraph, replace

```text
        P5A[Agent: prepare_deploy.py]
        P5H[HITL: 힌트·최종 diff 승인]
        P5B[시스템: mkdocs build --strict, CI, Render]
```

with:

```text
        P5A[Agent: prepare_deploy.py]
        P5C[Agent: export_corpus.py --strict]
        P5H[HITL: 힌트·corpus diff 승인]
        P5B[시스템: mkdocs build --strict, CI, Render]
```

and replace `P1A --> P1H --> P2H --> P3A --> P3H --> P4H --> P5A --> P5H --> P5B` with `P1A --> P1H --> P2H --> P3A --> P3H --> P4H --> P5A --> P5C --> P5H --> P5B`.

3. In the Phase 5 table, add this row after the 실행 row:

```markdown
| **코퍼스** | `python scripts/export_corpus.py --strict` | `data/corpus/` JSONL·manifest 커밋 여부 검토 | skip in-memory 제외 |
```

4. In Agent 체크리스트 under Phase 5, add:

```markdown
- [ ] `python scripts/export_corpus.py --strict` 통과
```

5. In HITL 체크리스트 under Phase 5, add:

```markdown
- [ ] corpus JSONL을 사이트와 같이 커밋할지 결정 (MCP Hosted는 커밋된 JSONL을 읽음)
```

6. In section 6 명령어, under `# 검증`, add:

```bash
python scripts/export_corpus.py --strict
```

7. In section 7 품질 게이트, add after G7:

```markdown
| G7b | `export_corpus.py --strict` 통과 | 시스템 |
```

Keep G8 as `main` push 승인. Do not renumber G1–G8.

8. In section 9 관련 파일, add:

```markdown
| `scripts/export_corpus.py` | MCP 코퍼스 JSONL (skip 제외) |
| `scripts/mcp_server/` | 읽기 전용 MCP (stdio + HTTP) |
```

9. In section 10 개정 이력, add:

```markdown
| 2026-09-10 | Phase 5에 corpus export. 소비는 사이트+MCP. 렌즈 스킬 제거 |
```

Do not add `.claude/skills/audit-regulatory-lens` anywhere in this file.

- [ ] **Step 3: Add CITATION_INSTRUCTIONS in app.py**

In `scripts/mcp_server/app.py`, replace the `mcp = FastMCP(...)` block (keep imports and tools unchanged) with:

```python
CITATION_INSTRUCTIONS = (
    "Read-only Korean financial regulatory corpus (FSS, FSC, KICPA, KASB). "
    "Use search_regulatory_updates then get_regulatory_update. "
    "Citation contract: (1) Every claim must include agency, date, title, url "
    "(and id when available). (2) Use only facts in note bullets/tables; "
    "do not invent numbers or interpretations. (3) If summary_status is "
    "no_summary, treat title and url as hints only, not body facts. "
    "(4) Skipped items are absent from the corpus; do not recover them "
    "from source markdown. (5) Corpus is read-only; curation, summaries, "
    "and nav belong to the production pipeline."
)

mcp = FastMCP(
    "quality-updates",
    instructions=CITATION_INSTRUCTIONS,
)
```

Do not change tool functions, resources, or `_store()`.

- [ ] **Step 4: Run consumption contract tests**

Run:

```bash
cd scripts
python -m pytest tests/test_consumption_contract.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit (only if the user asked to commit)**

```bash
git add README.md docs/project/quarterly-operations-guide.md scripts/mcp_server/app.py
git commit -m "docs: MCP citation contract and Phase 5 corpus export"
```

---

### Task 4: 이력 표기, spec 상태, 전체 게이트

**Files:**
- Modify: `docs/superpowers/plans/2026-06-27-mcp-corpus.md`
- Modify: `docs/superpowers/README.md`
- Modify: `docs/superpowers/specs/2026-09-10-consumption-mcp-product-design.md`

**Interfaces:**
- Consumes: Task 1–3 완료 상태
- Produces: 렌즈 MCP follow-up 취소, plan 색인, spec `상태: 승인됨`

- [ ] **Step 1: Cancel the lens follow-up on the MCP plan**

In `docs/superpowers/plans/2026-06-27-mcp-corpus.md`, replace

```markdown
## Follow-up (v1.1)

- [ ] `audit-regulatory-lens` SKILL — MCP 우선 retrieve 활성화
```

with:

```markdown
## Follow-up (v1.1)

- [x] `audit-regulatory-lens` SKILL — MCP 우선 retrieve 활성화 — **취소** (스킬 런타임 제거, 2026-09-10)
```

- [ ] **Step 2: Index this plan and mark the spec approved**

In `docs/superpowers/README.md` Plans table, insert this row immediately under the `## Plans` header row (before the 2026-09-09 fss-press-crawler plan):

```markdown
| 2026-09-10 | [consumption-mcp-product.md](plans/2026-09-10-consumption-mcp-product.md) | 소비 정본=사이트+MCP, 렌즈 런타임 삭제 |
```

Leave the 2026-09-10 spec row and the lens spec/plan “런타임 제거” wording as they already are.

In `docs/superpowers/specs/2026-09-10-consumption-mcp-product-design.md`, replace `**상태**: 초안 (사용자 검토 대기)` with `**상태**: 승인됨`.

- [ ] **Step 3: Grep runtime docs for leftover lens paths**

Run from repo root:

```bash
python -c "from pathlib import Path; roots=[Path('AGENTS.md'),Path('README.md'),Path('docs/project')];
hits=[]
for p in roots:
    files=[p] if p.is_file() else list(p.rglob('*.md'))
    for f in files:
        t=f.read_text(encoding='utf-8')
        if '.claude/skills/audit-regulatory-lens' in t: hits.append(str(f))
print('HITS', hits or 'none')"
```

Expected: `HITS none`.

- [ ] **Step 4: Run full verification gates**

Run from repo root (venv with project deps):

```bash
cd scripts
python -m pytest tests/ -q
cd ..
python scripts/validate_content.py --strict
python scripts/export_corpus.py --strict
mkdocs build --strict
```

Expected: pytest quiet pass (all existing tests plus 5 new). validate exit 0. export_corpus exit 0 **without** committing any JSONL diff. mkdocs strict build succeeds.

If `export_corpus.py --strict` rewrites `data/corpus/` on disk, **do not** `git add` those files. This plan does not refresh the committed corpus.

- [ ] **Step 5: Commit (only if the user asked to commit)**

```bash
git add docs/superpowers/plans/2026-06-27-mcp-corpus.md docs/superpowers/README.md docs/superpowers/specs/2026-09-10-consumption-mcp-product-design.md docs/superpowers/plans/2026-09-10-consumption-mcp-product.md
git commit -m "docs: approve consumption MCP spec and cancel lens follow-up"
```

---

## Self-review (spec coverage)

| Spec 요구 | Task |
|-----------|------|
| 렌즈 디렉터리 삭제 | Task 2 |
| AGENTS/README/docs/project 렌즈 진입점 제거 | Task 2–3 |
| 인용 계약 5줄 README + FastMCP instructions | Task 3 |
| Phase 5 `export_corpus --strict` | Task 3 |
| superpowers 색인 + 렌즈 이력 유지 + MCP follow-up 취소 | Task 4 (색인 렌즈 행은 이미 표기됨) |
| pytest / validate / export / mkdocs | Task 4 |
| 생산 파이프라인·스키마·tool 무변경, JSONL 재생성 없음, render.yaml 없음 | Global Constraints |
| Hosted 서비스 생성은 HITL, 완료 조건 아님 | Task 3 README 절차만 |
