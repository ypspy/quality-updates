# 미보도 제재 의안 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보도와 연결되지 않은 감리 의안을 `#### 제재 의결` 끝의 `##### 미보도`에 남기고, 그 경로가 빠지면 검증이 실패하게 한다.

**Architecture:** `repair_quarterly_structure.py`가 날짜 링크를 다시 모으기 전에 `##### 미보도`를 떼었다가 `제재 의결` 끝에 붙인다. `validate_content.py`는 분기 문서가 가리키는 회차 `record.md`의 unmatched 경로가 본문에 있는지만 본다. 회사 일치 판단은 요약 스킬 규칙으로 남고, 스크립트는 의결서 본문을 읽지 않는다.

**Tech Stack:** Python 3, pytest, 기존 `scripts/repair_quarterly_structure.py`, `scripts/validate_content.py`, `scripts/attach_sanction_minutes.py`, markdownlint.

## Global Constraints

- 스펙: `docs/superpowers/specs/2026-11-06-unpublished-sanction-items-design.md`
- `attach_sanction_minutes.py`는 실명·의안번호만 연결한다. 가려진 이름(○, △, O, ◇, ■, `A사`, `㈜OO`)은 추정하지 않는다.
- 미보도 항목에는 조치 표, `!!! note`, `위원 논의`를 만들지 않는다.
- `record.md`의 연결 칸을 고치지 않는다. `data/quarterly-processed/`를 만들지 않는다. 볼트에 복사하지 않는다.
- 2026년 3분기와 그 이전 분기 본문은 고치지 않는다. 3분기 회차 기록에는 unmatched 행이 없다.
- 분기 마크다운은 파일에 이미 있는 줄바꿈(`\r\n` 또는 `\n`)을 유지한다. 파일 전체를 다른 줄바꿈으로 다시 쓰지 않는다.
- 커밋은 사용자가 요청할 때만 한다. 이 계획의 태스크는 git commit을 실행하지 않는다.
- `docs/` 마크다운을 고친 뒤에는 `npm run lint:md`가 통과해야 한다.

---

### Task 1: 구조 수리가 미보도 절을 유지

**Files:**

- Modify: `scripts/repair_quarterly_structure.py`
- Test: `scripts/tests/test_repair_quarterly_structure.py`

**Interfaces:**

- Consumes: `split_document`, `extract_blocks`, `dedupe_blocks`, `rebuild_main_body`, `repair_file`
- Produces: `split_unpublished(main_lines: list[str]) -> tuple[list[str], list[str]]`. 두 번째 값은 `##### 미보도`부터 다음 제목 앞까지의 줄이다. 없으면 빈 리스트.
- Produces: `append_unpublished(body: str, block: list[str]) -> str`. `block`이 비면 `body`를 그대로 반환한다.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_repair_quarterly_structure.py` 끝에 추가한다.

```python
from repair_quarterly_structure import repair_file


QUARTER = """---
title: t
---

### 금융위원회

#### 보도자료

- (26-01-02) [일반 보도](https://fsc.go.kr/no010101/9)

#### 제재 의결

- (26-03-11) [감사보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/1)

##### 미보도

- 제5차 증권선물위원회(2026.3.11.) 의결 66. 예시

    <!-- source: pdf|downloads/sanctions/2026-증선위-정기-5차/decision/staff.pdf -->

#### 고시/공고/훈령

- (26-03-12) [고시](https://fsc.go.kr/po040200/2)
"""


def test_repair_keeps_unpublished_after_resolution_items(tmp_path):
    path = tmp_path / "quarter.md"
    path.write_text(QUARTER, encoding="utf-8", newline="\n")
    repair_file(path)
    text = path.read_text(encoding="utf-8")
    assert text.index("#### 제재 의결") < text.index("##### 미보도")
    assert text.index("##### 미보도") < text.index("staff.pdf")
    assert text.index("staff.pdf") < text.index("#### 고시/공고/훈령")
    assert text.index("- (26-03-11)") < text.index("##### 미보도")


def test_repair_keeps_unpublished_when_resolution_has_no_dated_link(tmp_path):
    source = QUARTER.replace(
        "- (26-03-11) [감사보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/1)\n\n",
        "",
    )
    path = tmp_path / "quarter.md"
    path.write_text(source, encoding="utf-8", newline="\n")
    repair_file(path)
    text = path.read_text(encoding="utf-8")
    assert "#### 제재 의결" in text
    assert text.index("#### 제재 의결") < text.index("##### 미보도")
    assert "staff.pdf" in text
    assert text.index("staff.pdf") < text.index("#### 고시/공고/훈령")
```

- [ ] **Step 2: Run test to verify it fails**

`scripts`에서 실행한다.

```bash
python -m pytest tests/test_repair_quarterly_structure.py::test_repair_keeps_unpublished_after_resolution_items tests/test_repair_quarterly_structure.py::test_repair_keeps_unpublished_when_resolution_has_no_dated_link -q
```

Expected: FAIL. `##### 미보도`가 수리 결과에 없다.

- [ ] **Step 3: Write minimal implementation**

`scripts/repair_quarterly_structure.py`의 `rebuild_main_body` 뒤에 추가한다.

```python
def split_unpublished(main_lines: list[str]) -> tuple[list[str], list[str]]:
    """Lift a ##### 미보도 block out of #### 제재 의결 before link extraction."""
    start = None
    end = None
    in_resolution = False
    for index, line in enumerate(main_lines):
        stripped = line.strip()
        if stripped == "#### 제재 의결":
            in_resolution = True
            continue
        if in_resolution and (stripped.startswith("#### ") or stripped.startswith("### ")):
            in_resolution = False
        if in_resolution and stripped == "##### 미보도" and start is None:
            start = index
            continue
        if start is not None and (
            stripped.startswith("#### ") or stripped.startswith("### ") or stripped.startswith("## ")
        ):
            end = index
            break
    if start is None:
        return main_lines, []
    if end is None:
        end = len(main_lines)
    while start > 0 and main_lines[start - 1].strip() == "":
        start -= 1
    block = main_lines[start:end]
    while block and block[0].strip() == "":
        block = block[1:]
    while block and block[-1].strip() == "":
        block = block[:-1]
    return main_lines[:start] + main_lines[end:], block


def append_unpublished(body: str, block: list[str]) -> str:
    """Put the lifted block at the end of #### 제재 의결, creating that section if needed."""
    if not block:
        return body
    lines = body.splitlines()
    section_at = next((i for i, line in enumerate(lines) if line.strip() == "#### 제재 의결"), None)
    if section_at is None:
        chunk = ["#### 제재 의결", "", *block]
        anchor = next((i for i, line in enumerate(lines) if line.strip() == "#### 고시/공고/훈령"), None)
        if anchor is None:
            anchor = next(
                (
                    i
                    for i, line in enumerate(lines)
                    if line.startswith("### ") and i > 0 and "금융위원회" in "\n".join(lines[:i])
                ),
                len(lines),
            )
        lines[anchor:anchor] = ["", *chunk, ""]
    else:
        insert_at = next(
            (
                i
                for i in range(section_at + 1, len(lines))
                if lines[i].startswith("#### ") or lines[i].startswith("### ")
            ),
            len(lines),
        )
        while insert_at > section_at + 1 and lines[insert_at - 1].strip() == "":
            insert_at -= 1
        lines[insert_at:insert_at] = ["", *block, ""]
    return "\n".join(lines).rstrip() + "\n"
```

`repair_file`의 본문 재구성 세 줄을 다음으로 바꾼다.

```python
    main_lines, unpublished = split_unpublished(main_lines)
    blocks = dedupe_blocks(extract_blocks(main_lines))
    new_main = append_unpublished(rebuild_main_body(blocks), unpublished)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_repair_quarterly_structure.py -q
```

Expected: PASS. 기존 수리 테스트도 통과한다.

---

### Task 2: unmatched 경로가 본문에 있는지 검사

**Files:**

- Modify: `scripts/validate_content.py`
- Create: `scripts/tests/test_unpublished_sanctions.py`

**Interfaces:**

- Consumes: `ValidationError`
- Produces: `meeting_folders(text: str) -> set[str]`. 원소는 `2026-증선위-정기-5차` 형식이다.
- Produces: `unmatched_source_paths(record_text: str, folder: str) -> list[str]`. 원소는 `downloads/sanctions/{folder}/{agenda|decision}/{제목}`이다.
- Produces: `validate_unpublished_sanctions(lines: list[str], path: Path, sanctions_root: Path) -> list[ValidationError]`

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_unpublished_sanctions.py`를 만든다.

```python
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validate_content import meeting_folders, unmatched_source_paths, validate_unpublished_sanctions

RECORD = """# 2026-증선위-정기-5차

| 번호 | 구분 | 제목 | 마스킹 | 연결 |
| --- | --- | --- | --- | --- |
| 66 | agenda | staff-agenda.pdf | 아니오 | unmatched |
| 66 | decision | staff-decision.pdf | 아니오 | unmatched |
| 72 | decision | named.pdf | 예 | 이화전기공업㈜ |
"""

QUARTER = """#### 제재 의결

- (26-03-11) [조사·감리결과 조치](https://fsc.go.kr/no010101/1)

    <!-- source: pdf|downloads/minutes-2026-증선위-정기-5.pdf -->
"""


def _root(tmp_path: Path) -> Path:
    folder = tmp_path / "2026-증선위-정기-5차"
    folder.mkdir()
    (folder / "record.md").write_text(RECORD, encoding="utf-8")
    return tmp_path


def test_meeting_folder_comes_from_minutes_or_sanction_path():
    text = QUARTER + "<!-- source: pdf|downloads/sanctions/2026-금융위-정기-5차/decision/a.pdf -->"
    assert meeting_folders(text) == {"2026-증선위-정기-5차", "2026-금융위-정기-5차"}


def test_unmatched_paths_skip_linked_rows():
    assert unmatched_source_paths(RECORD, "2026-증선위-정기-5차") == [
        "downloads/sanctions/2026-증선위-정기-5차/agenda/staff-agenda.pdf",
        "downloads/sanctions/2026-증선위-정기-5차/decision/staff-decision.pdf",
    ]


def test_missing_source_fails_and_press_or_unpublished_source_passes(tmp_path):
    root = _root(tmp_path)
    doc = tmp_path / "2026-01-01_to_2026-03-31.md"
    missing = validate_unpublished_sanctions(QUARTER.splitlines(), doc, root)
    assert [error.code for error in missing] == ["UNPUBLISHED_SOURCE", "UNPUBLISHED_SOURCE"]

    on_press = QUARTER.replace(
        "downloads/minutes-2026-증선위-정기-5.pdf -->",
        "downloads/minutes-2026-증선위-정기-5.pdf -->\n"
        "    <!-- source: pdf|downloads/sanctions/2026-증선위-정기-5차/agenda/staff-agenda.pdf -->\n"
        "    <!-- source: pdf|downloads/sanctions/2026-증선위-정기-5차/decision/staff-decision.pdf -->",
    )
    assert validate_unpublished_sanctions(on_press.splitlines(), doc, root) == []

    unpublished = QUARTER + (
        "\n##### 미보도\n\n"
        "- 예시\n\n"
        "    <!-- source: pdf|downloads/sanctions/2026-증선위-정기-5차/agenda/staff-agenda.pdf -->\n"
        "    <!-- source: pdf|downloads/sanctions/2026-증선위-정기-5차/decision/staff-decision.pdf -->\n"
    )
    assert validate_unpublished_sanctions(unpublished.splitlines(), doc, root) == []


def test_quarter_without_a_meeting_skips_the_check(tmp_path):
    doc = tmp_path / "note.md"
    assert validate_unpublished_sanctions(["일반 문장"], doc, tmp_path) == []


def test_missing_record_fails(tmp_path):
    doc = tmp_path / "2026-01-01_to_2026-03-31.md"
    errors = validate_unpublished_sanctions(QUARTER.splitlines(), doc, tmp_path)
    assert [error.code for error in errors] == ["UNPUBLISHED_RECORD"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_unpublished_sanctions.py -q
```

Expected: FAIL. `meeting_folders`가 없다.

- [ ] **Step 3: Write minimal implementation**

`scripts/validate_content.py`의 `validate_file` 앞에 추가한다.

```python
_MINUTES_FOLDER = re.compile(
    r"downloads/minutes-(?P<year>\d{4})-(?P<committee>증선위|금융위)-(?P<kind>정기|임시|서면)-(?P<number>\d+)\.pdf"
)
_BUNDLE_FOLDER = re.compile(
    r"downloads/sanctions/(?P<year>\d{4})-(?P<committee>증선위|금융위)-(?P<kind>정기|임시|서면)-(?P<number>\d+)차/"
)


def meeting_folders(text: str) -> set[str]:
    found: set[str] = set()
    for pattern in (_MINUTES_FOLDER, _BUNDLE_FOLDER):
        for match in pattern.finditer(text):
            found.add(
                f"{match.group('year')}-{match.group('committee')}-{match.group('kind')}-{match.group('number')}차"
            )
    return found


def unmatched_source_paths(record_text: str, folder: str) -> list[str]:
    paths: list[str] = []
    for line in record_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 5 or cells[1] not in {"agenda", "decision"} or cells[4] != "unmatched":
            continue
        paths.append(f"downloads/sanctions/{folder}/{cells[1]}/{cells[2]}")
    return paths


def validate_unpublished_sanctions(
    lines: list[str], path: Path, sanctions_root: Path
) -> list[ValidationError]:
    del path
    text = "\n".join(lines)
    errors: list[ValidationError] = []
    for folder in sorted(meeting_folders(text)):
        record = sanctions_root / folder / "record.md"
        if not record.is_file():
            errors.append(ValidationError(1, "UNPUBLISHED_RECORD", f"회차 기록 없음: {folder}", "error"))
            continue
        for source in unmatched_source_paths(record.read_text(encoding="utf-8"), folder):
            if source not in text:
                errors.append(
                    ValidationError(1, "UNPUBLISHED_SOURCE", f"미연결 의안이 분기 문서에 없음: {source}", "error")
                )
    return errors
```

대상 회의가 없으면 함수는 빈 목록을 반환한다. 임시 테스트 경로에 `quality-updates`가 없어도 검사를 건너뛰지 않는다.

`validate_file`의 검사 함수 리스트 끝에 `validate_unpublished_sanctions`를 직접 넣지 않는다. 그 함수는 `sanctions_root`가 필요하다. 리스트 뒤에 다음을 추가한다.

```python
    sanctions_root = Path(__file__).resolve().parent.parent / "downloads" / "sanctions"
    all_errors.extend(validate_unpublished_sanctions(lines, filepath, sanctions_root))
```

이 태스크 직후 `python scripts/validate_content.py --strict`는 1·2분기 unmatched 경로가 아직 본문에 없으므로 실패한다. 그것은 Task 4가 고친다. 이 태스크의 완료는 `tests/test_unpublished_sanctions.py` 통과다.

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_unpublished_sanctions.py -q
```

Expected: PASS.

---

### Task 3: 연결 스크립트가 미보도 절을 보도 항목에 넣지 않음

**Files:**

- Test: `scripts/tests/test_attach_sanction_minutes.py`
- Modify: `scripts/attach_sanction_minutes.py` only if Step 2 fails

**Interfaces:**

- Consumes: `DecisionPost`, `attach_minutes`
- Produces: 없음. 동작이 이미 맞으면 프로덕션 코드를 고치지 않는다.

- [ ] **Step 1: Write the test**

`scripts/tests/test_attach_sanction_minutes.py` 끝에 추가한다.

```python
def test_unpublished_section_stays_outside_the_press_item():
    text = """### 금융위원회

#### 제재 의결

- (26-03-11) [감사보고서 등에 대한 조사·감리결과 조치 - 제5차 증권선물위원회('26.3.11.)](https://fsc.go.kr/no010101/1)

    !!! note "위원 논의"

        - 미공개

##### 미보도

- 제5차 증권선물위원회(2026.3.11.) 의결 66. 예시

    <!-- source: pdf|downloads/sanctions/2026-증선위-정기-5차/decision/staff.pdf -->

#### 고시/공고/훈령
"""
    posts = [DecisionPost(2026, "증선위", "정기", 5, "https://fsc.go.kr/files/minutes-5.pdf", [])]
    updated, _report = attach_minutes(text, posts)
    assert "##### 미보도" in updated
    assert updated.index("minutes-5.pdf") < updated.index("##### 미보도")
    assert updated.index("##### 미보도") < updated.index("staff.pdf")
    assert updated.index("staff.pdf") < updated.index("#### 고시/공고/훈령")
```

- [ ] **Step 2: Run the test**

```bash
python -m pytest tests/test_attach_sanction_minutes.py::test_unpublished_section_stays_outside_the_press_item -q
```

Expected: PASS. 보도 항목 블록이 `#####`에서 끊기고, 의사록 마커는 그 앞에 들어간다.

- [ ] **Step 3: Change production code only on failure**

PASS이면 `attach_sanction_minutes.py`를 고치지 않는다. FAIL이면 보도 항목의 끝 조건을 `#####`에서 끊기도록 고친 뒤 같은 테스트를 다시 실행해 PASS를 확인한다.

---

### Task 4: 1·2분기 미보도 절 추가

**Files:**

- Modify: `docs/quality-updates/2026/2026-01-01_to_2026-03-31.md`
- Modify: `docs/quality-updates/2026/2026-04-01_to_2026-06-30.md`

**Interfaces:**

- Consumes: Task 2의 `UNPUBLISHED_SOURCE` 검사
- Produces: 두 분기 파일의 `#### 제재 의결`과 `#### 고시/공고/훈령` 사이에 있는 `##### 미보도`

이미 보도 항목에 있는 출처는 옮기지 않는다. PDF를 열지 않는다. `record.md`를 고치지 않는다.

- [ ] **Step 1: Insert the blocks with the file's existing newline**

저장소 루트에서 한 번 실행한다. `##### 미보도`가 이미 있으면 그 파일은 건너뛴다.

```python
from pathlib import Path

ROOT = Path("downloads/sanctions")
Q1 = Path("docs/quality-updates/2026/2026-01-01_to_2026-03-31.md")
Q2 = Path("docs/quality-updates/2026/2026-04-01_to_2026-06-30.md")


def item(title: str, paths: list[str]) -> str:
    sources = "\n".join(f"    <!-- source: pdf|{path} -->" for path in paths)
    return f"- {title}\n\n{sources}"


def pair(folder: str, number: int, firm: str) -> str:
    agenda = f"(공개용) 의결 {number}. {firm}에 대한 감사인 감리결과 조치안_공개용.pdf"
    decision = f"(의결서) 의결 {number}. {firm}에 대한 감사인 감리결과 조치안.pdf"
    base = f"downloads/sanctions/{folder}"
    title = f"제9차 증권선물위원회(2026.5.6.) 의결 {number}. {firm}에 대한 감사인 감리결과 조치안"
    return item(title, [f"{base}/agenda/{agenda}", f"{base}/decision/{decision}"])


q1_block = "\n".join([
    "##### 미보도",
    "",
    item(
        "제5차 증권선물위원회(2026.3.11.) 의결 66. 금융감독원 소속 직원에 대한 자체조사 결과 조치안",
        [
            "downloads/sanctions/2026-증선위-정기-5차/agenda/(공개용) 의결 66. 금융감독원 소속 직원에 대한 자체조사 결과 조치안.pdf",
            "downloads/sanctions/2026-증선위-정기-5차/decision/(의결서) 의결 66. 금융감독원 소속 직원에 대한 자체조사 결과 조치안.pdf",
        ],
    ),
    "",
    item(
        "제5차 금융위원회(2026.3.18.) 의결 128. 금융감독원 소속 직원에 대한 자체조사 결과 조치안",
        [
            "downloads/sanctions/2026-금융위-정기-5차/agenda/의결128 금융감독원 소속 직원에 대한 자체조사 결과 조치안(공개용).pdf",
            "downloads/sanctions/2026-금융위-정기-5차/decision/금융위 의결서(제2026-128호)_금융감독원 소속 직원에 대한 자체조사 결과 조치안.pdf",
        ],
    ),
])

firms = ["삼일", "대주", "신한", "태성", "태일", "동성", "예일", "안경", "예지", "선일"]
q2_items = [
    item(
        "제9차 증권선물위원회(2026.5.6.) 보고 12. 한국공인회계사회의 2025년도 회계법인에 대한 감사인 감리 처리결과 보고",
        ["downloads/sanctions/2026-증선위-정기-9차/agenda/(공개용) 보고 12. 한국공인회계사회의 2025년도 회계법인에 대한 감사인 감리 처리결과 보고.pdf"],
    ),
    item(
        "제9차 증권선물위원회(2026.5.6.) 보고 13 한국공인회계사회의 2025년도 감사반에 대한 감사인 감리 처리결과 보고",
        ["downloads/sanctions/2026-증선위-정기-9차/agenda/(공개용) 보고 13 한국공인회계사회의 2025년도 감사반에 대한 감사인 감리 처리결과 보고.pdf"],
    ),
]
q2_items.extend(pair("2026-증선위-정기-9차", number, firm) for number, firm in enumerate(firms, start=125))
q2_block = "##### 미보도\n\n" + "\n\n".join(q2_items)


def insert(path: Path, block: str) -> None:
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")
    if "##### 미보도" in text:
        return
    marker = "#### 제재 의결"
    start = text.index(marker)
    heading = "#### 고시/공고/훈령"
    at = text.index(heading, start)
    text = text[:at] + block + newline + newline + text[at:]
    path.write_bytes(text.replace("\r\n", "\n").replace("\n", newline).encode("utf-8"))


insert(Q1, q1_block)
insert(Q2, q2_block)
```

`보고 13` 제목에는 번호 뒤 마침표가 없다. 파일명이 그렇다. `의결 125` 표시 제목에서는 `_공개용`을 뺀다. 출처 경로에는 `_공개용`을 남긴다.

- [ ] **Step 2: Confirm placement and run the strict check**

각 파일에서 `##### 미보도`는 `#### 제재 의결`보다 뒤이고 `#### 고시/공고/훈령`보다 앞이다. 기존 보도 링크와 `위원 논의` 문장은 그대로다.

저장소 루트에서 실행한다.

```bash
python scripts/validate_content.py --strict
```

Expected: exit 0. `UNPUBLISHED_SOURCE`가 없다.

```bash
npm run lint:md
```

Expected: exit 0.

---

### Task 5: 요약 스킬과 운영 문서

**Files:**

- Modify: `.claude/skills/quality-updates-writer/SKILL.md`
- Modify: `docs/project/quarterly-operations-guide.md`
- Modify: `README.md`

**Interfaces:**

- Consumes: 스펙의 파이프라인 두 단계와 `##### 미보도` 형식
- Produces: 없음

- [ ] **Step 1: Add the writer rule**

`.claude/skills/quality-updates-writer/SKILL.md`에서 `제재 의결` 항목의 `위원 논의` 문단 바로 뒤에 다음 문단을 넣는다.

```markdown
의사록이 공개된 분기에서는 `attach_sanction_minutes.py`를 먼저 실행한다. 그 명령은 실명과 의안번호만 붙인다. 이어서 그 분기 파일에 의사록 마커가 있는 회의의 `downloads/sanctions/.../record.md`에서 연결이 `unmatched`인 PDF만 연다. 같은 회의의 보도 한 건과 지적사항·금액이 맞으면 그 의안의 unmatched 출처를 그 보도 항목으로 옮긴다. 기호가 비슷하다는 이유로는 옮기지 않는다. 실명인데 회사명 칸에 없어 스크립트가 놓친 파일도 여기서 읽는다. 맞는 보도가 없거나 둘 이상이면 `#### 제재 의결` 맨 끝의 `##### 미보도`에 둔다. 항목은 날짜 링크가 아니다. 회의·의안 제목과 PDF 출처만 적고, 조치 표와 `위원 논의`는 만들지 않는다. 같은 의안번호의 안건과 의결서는 한 항목에 둔다. 번호가 없는 보고는 파일마다 한 항목이다. 표시 제목은 `제N차 증권선물위원회(YYYY.M.D.)` 또는 `제N차 금융위원회(YYYY.M.D.)` 뒤에 의안 이름을 붙인다. 월·일의 앞쪽 0은 뺀다. 의안 이름은 공개용 안건 파일명을 우선하고, 없으면 의결서 파일명을 쓴다. 확장자, 앞쪽 `(공개용)`과 그 뒤 공백, 앞쪽 `(의결서)`와 그 뒤 공백, 앞쪽 `금융위 의결서(제YYYY-N호)_`, 끝의 `_공개용`을 뺀다. `의결128`은 `의결 128.`으로 맞춘다. 순서는 회의일, 그다음 의안번호다. 다시 요약할 때 `##### 미보도`와 보도 항목의 `위원 논의`는 지우지 않는다. `record.md`는 고치지 않는다. PDF를 읽을 수 없으면 제목만 쓰고 출처 마커는 쓰지 않는다.
```

- [ ] **Step 2: Add the operations step**

`docs/project/quarterly-operations-guide.md`의 Phase 3에서 `조사·감리결과 조치는 금융위원회 제재 의결에 두고, 의사록 PDF가 공개되면 같은 분기 파일의 위원 논의에 보강한다.` 문장 뒤를 다음으로 바꾼다.

```markdown
조사·감리결과 조치는 금융위원회 `제재 의결`에 둔다. 의사록 PDF가 공개되면, 그 회의가 들어 있는 분기 파일에서 두 단계를 실행한다. `python scripts/attach_sanction_minutes.py <분기.md>`는 의사록과 실명·의안번호가 맞는 의안만 붙인다. 이어서 요약 스킬이 unmatched PDF를 읽어, 같은 회의 보도 한 건과만 맞으면 보도 항목으로 옮기고 나머지는 `##### 미보도`에 회의·의안 제목·출처만 적는다. 크롤 당일에는 이 두 단계를 실행하지 않는다.
```

Agent 체크리스트에 다음 두 줄을 추가한다.

```markdown
- [ ] 의사록이 공개된 회의는 `attach_sanction_minutes.py` 뒤 unmatched를 보도 항목 또는 `##### 미보도`에 둠
- [ ] `##### 미보도`에는 조치 표와 `위원 논의`를 쓰지 않음
```

- [ ] **Step 3: Replace the README sentence**

`README.md`의 제재 연결 문단에서 다음 문장을 바꾼다.

기존:

```markdown
대응이 없거나 둘 이상이면 unmatched로 보고하고, 그 PDF는 분기 문서에 마커로 넣지 않는다.
```

변경:

```markdown
대응이 없거나 둘 이상이면 unmatched로 보고한다. 요약 단계가 그 PDF를 읽어 같은 회의 보도 한 건과만 맞으면 보도 항목에 붙이고, 나머지는 `##### 미보도`에 회의·의안 제목·출처만 적는다. `validate_content.py --strict`는 unmatched 경로가 분기 문서에 있는지만 본다.
```

- [ ] **Step 4: Lint**

```bash
npm run lint:md
```

Expected: exit 0.

---

## 완료 확인

`scripts`에서:

```bash
python -m pytest tests/test_repair_quarterly_structure.py tests/test_attach_sanction_minutes.py tests/test_unpublished_sanctions.py -q
```

저장소 루트에서:

```bash
python scripts/validate_content.py --strict
npm run lint:md
```

Expected: 세 명령 모두 exit 0.
