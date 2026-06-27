# Phase 2 집계 요약 제거 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 분기 규제 업데이트 문서·파이프라인·운영 문서에서 Executive Summary / 기관별 요약 / 시사점(Phase 2)을 제거하고, 링크별 Phase 1 note + YAML + Appendix A만 남긴 MCP 친화 코퍼스로 정규화한다.

**Architecture:** `strip_phase2_summaries.py`로 front matter 직후~첫 `금융감독원` 헤더 직전 구간 일괄 삭제 → `validate_content.validate_no_phase2`로 회귀 방지 → `quality-updates-writer` 스킬에서 Phase 2·REFERENCE F 제거 → 운영 문서 SSOT 갱신.

**Tech Stack:** Python 3.8+, pytest, MkDocs Material, `.claude/skills/quality-updates-writer/SKILL.md`

**Spec:** `docs/superpowers/specs/2026-06-26-remove-phase2-summaries-design.md`

---

## File map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/strip_phase2_summaries.py` | Create | Phase 2 구간 삭제 CLI |
| `scripts/validate_content.py` | Modify | `validate_no_phase2` + `validate_file` 등록 |
| `scripts/tests/test_validate_phase2.py` | Create | Phase 2 금지 규칙 단위 테스트 |
| `scripts/tests/test_strip_phase2_summaries.py` | Create | strip 스크립트 단위 테스트 |
| `docs/quality-updates/{year}/*.md` | Modify | 12개 분기 백필 (2023 Q2 제외) |
| `.claude/skills/quality-updates-writer/SKILL.md` | Modify | Phase 2 제거, gold standard 갱신 |
| `.claude/skills/quality-updates-writer/boilerplate.md` | Modify | DEPRECATED 주석 1줄 |
| `scripts/apply_q1_2026_summaries.py` | Modify | DEPRECATED 또는 Phase 2 코드 삭제 |
| `scripts/patch_2023_q1_md.py` | Modify | DEPRECATED 주석 |
| `README.md`, `AGENTS.md`, `docs/project/*.md`, `docs/quality-updates/index.md` | Modify | SSOT 문구 |
| `docs/superpowers/README.md` | Modify | plan 행 추가 |

---

### Task 1: Phase 2 strip 스크립트

**Files:**
- Create: `scripts/strip_phase2_summaries.py`
- Create: `scripts/tests/test_strip_phase2_summaries.py`

- [ ] **Step 1: Write failing tests**

```python
# scripts/tests/test_strip_phase2_summaries.py
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from strip_phase2_summaries import strip_phase2_from_text

SAMPLE_WITH_ES = """---
title: test
---

## Executive Summary

분기 테마 문장.

#### 기관별 요약

!!! success ""

    === "금융감독원"
        - bullet

---

#### 시사점

!!! success ""

    === "기업"
        - bullet

### 금융감독원

#### 보도자료

- (25-01-01) [제목](https://example.com)
"""

SAMPLE_LEGACY = """---
title: test
---

### 요약

- 기간 : 2022년 …
- 주요 사항

### 금융감독원

#### 보도자료
"""

def test_strip_removes_executive_summary_block():
    out = strip_phase2_from_text(SAMPLE_WITH_ES)
    assert "Executive Summary" not in out
    assert "기관별 요약" not in out
    assert "#### 시사점" not in out
    assert "### 금융감독원" in out
    assert "https://example.com" in out

def test_strip_removes_legacy_summary():
    out = strip_phase2_from_text(SAMPLE_LEGACY)
    assert "### 요약" not in out.split("---")[-1]  # after front matter
    assert "### 금융감독원" in out

def test_strip_idempotent():
    once = strip_phase2_from_text(SAMPLE_WITH_ES)
    twice = strip_phase2_from_text(once)
    assert once == twice
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd scripts && python -m pytest tests/test_strip_phase2_summaries.py -v
```

Expected: `ImportError` or `AttributeError`

- [ ] **Step 3: Implement `strip_phase2_from_text`**

```python
# scripts/strip_phase2_summaries.py (core logic)
import re
from pathlib import Path

AGENCY_ANCHOR = re.compile(r"^#{2,3}\s+금융감독원\s*$", re.MULTILINE)

def strip_phase2_from_text(text: str) -> str:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text
    end_fm = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_fm = i
            break
    if end_fm is None:
        return text
    rest = "\n".join(lines[end_fm + 1 :])
    m = AGENCY_ANCHOR.search(rest)
    if not m:
        return text
    head = "\n".join(lines[: end_fm + 1])
    tail = rest[m.start() :].lstrip("\n")
    return f"{head}\n\n{tail}\n"
```

CLI: `--dry-run`, `--file PATH`, default `docs/quality-updates/{year}/*.md` (`index.md` 제외).

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd scripts && python -m pytest tests/test_strip_phase2_summaries.py -v
```

- [ ] **Step 5: Dry-run on 2026 Q1**

```bash
python scripts/strip_phase2_summaries.py --dry-run --file docs/quality-updates/2026/2026-01-01_to_2026-03-31.md
```

Expected: 삭제 줄 수 출력, `Executive Summary` 구간만

---

### Task 2: 분기 콘텐츠 백필

**Files:**
- Modify: 12× `docs/quality-updates/{year}/*.md` (2023 Q2 제외)

- [ ] **Step 1: Apply strip to all quarter files**

```bash
python scripts/strip_phase2_summaries.py
```

- [ ] **Step 2: Spot-check diffs**

```bash
git diff --stat docs/quality-updates/
git diff docs/quality-updates/2025/2025-10-01_to_2025-12-31.md | head -80
git diff docs/quality-updates/2022/2022-12-15_to_2023-04-03.md | head -40
```

Confirm: 첫 본문 헤더가 `금융감독원`; 링크 note `- (시사점)` 잔존

- [ ] **Step 3: Grep — no Phase 2 headers**

```bash
rg "^#{2,4}\s+(Executive Summary|기관별 요약|시사점)\s*$" docs/quality-updates/
rg "^#{2,3}\s+요약\s*$" docs/quality-updates/
```

Expected: no matches (index.md 제외)

---

### Task 3: validate_content Phase 2 금지

**Files:**
- Modify: `scripts/validate_content.py`
- Create: `scripts/tests/test_validate_phase2.py`

- [ ] **Step 1: Write failing tests**

```python
# scripts/tests/test_validate_phase2.py
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_content import validate_no_phase2

def test_rejects_executive_summary_header():
    lines = ["---", "title: x", "---", "", "## Executive Summary", "text"]
    errs = validate_no_phase2(lines, Path("docs/quality-updates/2025/x.md"))
    assert any(e.code == "PHASE2_ES" for e in errs)

def test_allows_note_sisajeom_prefix():
    lines = ["---", "title: x", "---", "", "        - (시사점) 원문 사실"]
    errs = validate_no_phase2(lines, Path("docs/quality-updates/2025/x.md"))
    assert not any(e.code == "PHASE2_IMPL" for e in errs)

def test_skips_index_md():
    lines = ["## Executive Summary"]
    errs = validate_no_phase2(lines, Path("docs/quality-updates/index.md"))
    assert errs == []
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd scripts && python -m pytest tests/test_validate_phase2.py -v
```

- [ ] **Step 3: Implement `validate_no_phase2`**

```python
PHASE2_PATTERNS = [
    ("PHASE2_ES", re.compile(r"^#{2,3}\s+Executive Summary\s*$"), "error"),
    ("PHASE2_AGENCY", re.compile(r"^#{2,4}\s+기관별 요약\s*$"), "error"),
    ("PHASE2_IMPL", re.compile(r"^#{2,4}\s+시사점\s*$"), "error"),
    ("PHASE2_LEGACY", re.compile(r"^#{2,3}\s+요약\s*$"), "error"),
]

def validate_no_phase2(lines: list[str], path: Path) -> list[ValidationError]:
    if path.name == "index.md":
        return []
    if "quality-updates" not in path.as_posix():
        return []
    errors = []
    for i, line in enumerate(lines):
        for code, pat, sev in PHASE2_PATTERNS:
            if pat.match(line.rstrip()):
                errors.append(ValidationError(i + 1, code, f"Phase 2 헤더 금지: {line.strip()}", sev))
    return errors
```

`validate_file`의 `for fn in [...]` 목록에 추가.

- [ ] **Step 4: Run tests + validate strict**

```bash
cd scripts && python -m pytest tests/test_validate_phase2.py -v
python scripts/validate_content.py --strict
```

Expected: exit 0

---

### Task 4: quality-updates-writer 스킬 개정

**Files:**
- Modify: `.claude/skills/quality-updates-writer/SKILL.md`
- Modify: `.claude/skills/quality-updates-writer/boilerplate.md`

- [ ] **Step 1: Remove Phase 2 from SUMMARIZE workflow**

삭제 대상:
- TaskCreate 항목 `"Phase 2: 분기 요약 생성"`
- dot 그래프의 `Phase 2: 분기 요약` 노드·엣지
- `### Phase 2: 분기 요약 생성` 섹션 전체
- `## REFERENCE F. Phase 2 구조 규칙` 전체
- BOILERPLATE 템플릿 내 ES·기관별·시사점 블록 (front matter → `## 금융감독원` 직결)
- 품질 체크리스트: ES 어미, 시사점 탭, 증선위→금융위 탭(Phase 2 한정) 항목

유지: REFERENCE A–E, Appendix G, Phase 0·1, SKIP_REMOVAL, BOILERPLATE 크롤러 우선.

- [ ] **Step 2: Update gold standard references**

- Announce / Gold standard: `2023-04-01_to_2023-06-30.md`, `2025-10-01_to_2025-12-31.md`
- SUMMARIZE 완료 정의: Phase 1 note + Appendix A

- [ ] **Step 3: boilerplate.md DEPRECATED 주석**

```markdown
<!-- Phase 2(Executive Summary·기관별 요약·시사점)는 2026-06-26 spec으로 제거됨. SKILL.md BOILERPLATE 참조. -->
```

- [ ] **Step 4: Grep skill — no Phase 2 remnants**

```bash
rg "Phase 2|REFERENCE F|Executive Summary|기관별 요약" .claude/skills/quality-updates-writer/SKILL.md
```

Expected: BOILERPLATE 설명·이력 맥락 외 불필요 매치 없음

---

### Task 5: 운영·메타 문서

**Files:**
- Modify: `README.md` (line ~70 workflow table)
- Modify: `docs/project/quarterly-operations-guide.md` (Phase 3)
- Modify: `docs/project/README.md` (SSOT table)
- Modify: `docs/quality-updates/index.md` (line ~23)
- Modify: `AGENTS.md` (constraints §3)

- [ ] **Step 1: README.md** — Phase 3 산출물: `링크별 note` (Executive Summary·기관별 요약 삭제)

- [ ] **Step 2: quarterly-operations-guide.md**
  - Phase 3 표: Phase 2 행 삭제; Agent = Phase 0·1 only
  - HITL: “분기 테마(Executive Summary)” 체크 삭제
  - Phase 1 HITL “ES 없음 = 정상” 유지

- [ ] **Step 3: docs/project/README.md** — “요약 포맷” → Phase 1 링크 note

- [ ] **Step 4: docs/quality-updates/index.md** — “기관별 보도자료·링크별 note”

- [ ] **Step 5: AGENTS.md** — `Executive Summary·note` → `note 블록`; gold standard 경로 갱신

---

### Task 6: Legacy scripts

**Files:**
- Modify: `scripts/apply_q1_2026_summaries.py`
- Modify: `scripts/patch_2023_q1_md.py`

- [ ] **Step 1:** 각 파일 상단에 DEPRECATED docstring 추가 (Phase 2 제거 spec 이후 사용 금지)

- [ ] **Step 2:** `apply_q1_2026_summaries.py`에서 `PHASE2_*` 상수·`build_phase2_*` 함수·main의 Phase 2 삽입 호출 **삭제** (Phase 1-only 남기거나 전체 DEPRECATED if unused)

- [ ] **Step 3:** `patch_2023_q1_md.py` — Phase 2 삽입 문자열·로직 제거 또는 파일 전체 `if __name__` guard with sys.exit message

---

### Task 7: Final verification

- [ ] **Step 1: pytest**

```bash
cd scripts && python -m pytest tests/ -q
```

Expected: all passed

- [ ] **Step 2: validate strict**

```bash
python scripts/validate_content.py --strict
```

Expected: exit 0

- [ ] **Step 3: mkdocs strict**

```bash
mkdocs build --strict
```

Expected: exit 0

- [ ] **Step 4: Manual spot-check `(시사점)` in notes**

```bash
rg "\- \(시사점\)" docs/quality-updates/2023/2023-07-01_to_2023-09-30.md | head -3
```

Expected: matches present

- [ ] **Step 5: Update docs/superpowers/README.md plans table**

Add row: `2026-06-26 | remove-phase2-summaries.md | Phase 2 제거 구현`

---

## Acceptance checklist (from spec)

- [ ] 12개 분기 파일 Phase 2 헤더 없음
- [ ] 2022 `### 요약` 없음
- [ ] 링크 note `(시사점)` 잔존
- [ ] SKILL.md Phase 2·REFERENCE F 없음
- [ ] validate / pytest / mkdocs strict 통과
- [ ] quarterly-operations-guide Phase 3 = Phase 1-only
