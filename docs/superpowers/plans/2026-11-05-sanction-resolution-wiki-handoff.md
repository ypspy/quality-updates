# 제재 의결·위키 원본 전달 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 조사·감리 조치를 `제재 의결`로 유지하고, 의사록 PDF만 연결하며, 요약이 끝난 분기 본문의 처리 기록과 PDF를 옵시디안 `raw/`로 복사한다.

**Architecture:** 섹션 분류는 `repair_quarterly_structure.py`가 링크 제목으로 한다. 의사록 연결은 네트워크를 주입받는 순수 함수와 얇은 CLI다. 처리 기록은 분기 본문에서 만들고, 복사 CLI는 볼트에 이미 있는 파일을 덮어쓰지 않는다. 웨일 변환과 위키 페이지 작성은 이 계획에 없다.

**Tech Stack:** Python 3, pytest, pathlib. 새 의존성 없음.

**Spec:** `docs/superpowers/specs/2026-11-05-sanction-resolution-wiki-handoff-design.md`

## Global Constraints

- 금융위원회 하위 순서는 `보도자료`, `제재 의결`, `고시/공고/훈령`, `입법예고/규정변경예고`.
- `제재 의결` 제목 조건은 링크 텍스트에 `조사·감리결과 조치`가 있는 금융위 보도다. `불공정거래` 제목은 이 섹션으로 가지 않는다.
- 회차 키는 연도, 금융위 또는 증선위, 정기·임시·서면, 제N차다. 의안 키는 회차 키와 의안번호다. 안건 ZIP을 받아 감리 의안의 공개용 안건·의결서 PDF만 남기고, ZIP 원본은 요청 결과로 보관하지 않는다. `의사록(추가)`는 같은 회차로 합친다.
- 표의 회사명, 위반내용, 금액은 고치지 않는다. 회사명이 가려진 안건을 표 행에 추정으로 붙이지 않는다.
- 처리 기록 경로는 `data/quarterly-processed/{분기 파일 stem}/{YY-MM-DD}-{슬러그}.md`. gitignore하지 않는다. MkDocs에 포함되지 않는다.
- 복사 기본 목적지는 `C:\dev\obsidian-valut\raw`. 같은 상대 경로가 있으면 덮어쓰지 않는다. 바이트가 같으면 건너뛰고, 다르면 이름에 `--YYYY-MM-DD`를 붙인 새 파일을 만든다.
- 복사 대상은 분기 본문의 `pdf`, `shot`, `clip`이다. Appendix, `<!-- skip -->`, `<!-- no_summary -->`, PDF가 없는 HWP/HWPX는 복사하지 않는다.
- PDF가 없는 HWP/HWPX는 그록 봇 변환 대기로 보고만 한다. 이 저장소는 웨일을 실행하지 않고 LibreOffice를 호출하지 않는다.
- `docs/quality-updates/2026/2026-07-01_to_2026-09-30.md`에는 이 계획의 어떤 단계에서도 `repair_quarterly_structure.py`를 실행하지 않는다. 검증은 fixture만 쓴다.
- 위키 `wiki/` 작성과 과거 분기 소급은 하지 않는다.

---

### Task 1: 제재 의결 분류

**Files:**

- Modify: `scripts/repair_quarterly_structure.py`
- Test: `scripts/tests/test_repair_quarterly_structure.py`

**Interfaces:**

- Consumes: 기존 `classify_url(url)`, `rebuild_main_body(blocks)`, `LINK_RE`
- Produces: `classify_url(url: str, title: str = "") -> tuple[str, str]`, `classify_block(url: str, block: str) -> tuple[str, str]`. `rebuild_main_body`는 `classify_block`을 쓴다.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_repair_quarterly_structure.py`에 다음을 추가한다.

```python
def test_sanction_title_goes_to_resolution_section():
    url = "https://fsc.go.kr/no010101/87293"
    title = "사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회"
    assert classify_url(url, title) == ("금융위원회", "제재 의결")


def test_unfair_trade_title_stays_in_press():
    url = "https://fsc.go.kr/no010101/9"
    assert classify_url(url, "불공정거래 조치")[1] == "보도자료"


def test_rebuild_keeps_discussion_note_under_resolution():
    block = "\n".join([
        "- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/87293)",
        "",
        "    !!! note \"위원 논의\"",
        "",
        "        - (의결) 수정의결함",
    ])
    body = rebuild_main_body([((2026, 7, 9), "https://fsc.go.kr/no010101/87293", block)])
    assert body.index("#### 제재 의결") < body.index("수정의결함")
    assert "#### 보도자료" not in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_repair_quarterly_structure.py::test_sanction_title_goes_to_resolution_section tests/test_repair_quarterly_structure.py::test_rebuild_keeps_discussion_note_under_resolution -q`

Expected: FAIL. `classify_url`가 title을 받지 않거나 `제재 의결`이 `SECTIONS`에 없어 `ValueError`가 난다.

- [ ] **Step 3: Write minimal implementation**

`SECTIONS`의 금융위원회 목록을 다음으로 바꾼다.

```python
("금융위원회", ["보도자료", "제재 의결", "고시/공고/훈령", "입법예고/규정변경예고"]),
```

`classify_url` 서명을 `def classify_url(url: str, title: str = "") -> tuple[str, str]:`로 바꾸고, `fsc.go.kr` 분기에서 고시·입법예고 판정 다음에 넣는다.

```python
if "조사·감리결과 조치" in title:
    return "금융위원회", "제재 의결"
return "금융위원회", "보도자료"
```

`classify_block`을 추가한다.

```python
def classify_block(url: str, block: str) -> tuple[str, str]:
    title = ""
    first = block.splitlines()[0] if block else ""
    matched = LINK_RE.match(first)
    if matched:
        title = matched.group(4)
    return classify_url(url, title)
```

`rebuild_main_body`의 분류 호출을 `classify_block(item[1], item[2])`로 바꾼다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts && python -m pytest tests/test_repair_quarterly_structure.py -q`

Expected: PASS. 기존 `test_classify_fsc_subsections`는 title 기본값이 빈 문자열이라 보도자료로 남는다.

- [ ] **Step 5: Commit**

```bash
git add scripts/repair_quarterly_structure.py scripts/tests/test_repair_quarterly_structure.py
git commit -m "fix: keep investigation sanctions in the resolution section"
```

### Task 2: 골격과 요약 규칙

**Files:**

- Modify: `scripts/crawler/unified.py` (`collect_fsc`)
- Modify: `.claude/skills/quality-updates-writer/SKILL.md`
- Modify: `docs/project/quarterly-operations-guide.md`
- Test: `scripts/tests/test_fsc_section_order.py`

**Interfaces:**

- Consumes: Task 1의 금융위원회 하위 순서
- Produces: `unified.FSC_MAIN_HEADINGS`. `collect_fsc`가 보도자료 다음에 빈 `#### 제재 의결`을 쓴다.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_fsc_section_order.py`를 만든다. 크롤 함수는 호출하지 않는다.

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler.unified import FSC_MAIN_HEADINGS
from repair_quarterly_structure import SECTIONS


def test_fsc_headings_match_repair_sections():
    repair = dict(SECTIONS)["금융위원회"]
    assert FSC_MAIN_HEADINGS == repair
    assert FSC_MAIN_HEADINGS.index("보도자료") < FSC_MAIN_HEADINGS.index("제재 의결")
    assert FSC_MAIN_HEADINGS.index("제재 의결") < FSC_MAIN_HEADINGS.index("고시/공고/훈령")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_fsc_section_order.py -q`

Expected: FAIL with `ImportError` for `FSC_MAIN_HEADINGS`.

- [ ] **Step 3: Write minimal implementation**

`scripts/crawler/unified.py`의 `collect_fsc` 위에 상수를 둔다.

```python
FSC_MAIN_HEADINGS = ["보도자료", "제재 의결", "고시/공고/훈령", "입법예고/규정변경예고"]
```

`collect_fsc`에서 보도자료 블록 다음, 소관규정 블록 전에 넣는다.

```python
lines += ["\n#### 제재 의결\n"]
```

스킬 보일러플레이트 `## 금융위원회`의 `#### 보도자료` / `해당사항 없음` 다음에 넣는다.

```markdown
#### 제재 의결

해당사항 없음
```

`REFERENCE D`의 Type B 절 끝에 다음 문단을 넣는다.

```markdown
`제재 의결` 항목은 Type A 또는 Type B 표 아래에 `!!! note "위원 논의"`를 둔다. 의사록을 읽지 않았으면 `미공개` 한 줄만 둔다. 다시 요약할 때 이 노트를 지우지 않는다. 표의 회사명과 금액은 고치지 않는다. 문체는 명사형, `~함`, `~임`, `~예정`이다.
```

`docs/project/quarterly-operations-guide.md`의 요약 단계 설명 근처에 다음 세 문장을 넣는다.

```markdown
PDF가 없는 HWP/HWPX는 `fetch_attachments.py` 보고의 변환 목록이다. 그록 봇이 웨일에서 PDF로 저장하고 `pdf` 마커로 연결한다. 저장소 스크립트는 웨일을 실행하지 않는다. 조사·감리결과 조치는 금융위원회 `제재 의결`에 두고, 의사록 PDF가 공개되면 같은 분기 파일의 `위원 논의`에 보강한다.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts && python -m pytest tests/test_fsc_section_order.py tests/test_repair_quarterly_structure.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/crawler/unified.py scripts/tests/test_fsc_section_order.py .claude/skills/quality-updates-writer/SKILL.md docs/project/quarterly-operations-guide.md
git commit -m "docs: add the sanction resolution heading to the quarter skeleton"
```

### Task 3: 의사록 PDF 연결

**Files:**

- Create: `scripts/attach_sanction_minutes.py`
- Test: `scripts/tests/test_attach_sanction_minutes.py`

**Interfaces:**

- Consumes: 분기 마크다운 텍스트. 테스트가 넣는 `DecisionPost`.
- Produces: `DecisionPost`, `meeting_key(text: str) -> tuple[int, str, str, int] | None`, `select_minutes_pdf(key, posts: list[DecisionPost]) -> str | None`, `attach_minutes(text: str, posts: list[DecisionPost]) -> tuple[str, list[str]]`. CLI `main(argv) -> int`는 이 계획에서 네트워크 구현을 비워 두고, 테스트는 `attach_minutes`만 호출한다. ZIP URL은 `select_minutes_pdf`의 반환값이 될 수 없다. 이후 안건 작업은 ZIP을 받아 `parse_agenda_number`와 `link_agendas`로 감리 의안만 연결한다.

- [ ] **Step 1: Write the failing test**

```python
from attach_sanction_minutes import DecisionPost, attach_minutes, select_minutes_pdf

PRESS = """### 금융위원회

#### 제재 의결

- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회(’26.7.8.)](https://fsc.go.kr/no010101/87293)

    !!! note "위원 논의"

        - 미공개임

#### 보도자료

- (26-07-24) [외부감사 규정 예고](https://fsc.go.kr/no010101/1)
"""

POSTS = [
    DecisionPost(2026, "증선위", "정기", 13, "https://fsc.go.kr/comm/getFile?fileNo=1", ["https://fsc.go.kr/comm/getFile?fileNo=2"]),  # 의사록 URL만 마커에 쓴다. ZIP은 감리 의안 추출 대상이다.
    DecisionPost(2026, "증선위", "정기", 13, "https://fsc.go.kr/comm/getFile?other=1", []),
]


def test_ambiguous_key_does_not_attach_and_ignores_zip():
    updated, report = attach_minutes(PRESS, POSTS)
    assert updated == PRESS
    assert "fileNo=2" not in " ".join(report)
    assert select_minutes_pdf((2026, "증선위", "정기", 13), POSTS) is None


def test_single_minutes_pdf_is_attached_without_rewriting_the_table():
    posts = [POSTS[0]]
    updated, report = attach_minutes(PRESS, posts)
    assert "source: pdf|downloads/" in updated
    assert "외부감사 규정" in updated
    assert updated.index("외부감사 규정") > updated.index("제재 의결")
    assert "fileNo=2" not in updated
    assert report == ["attached 2026 증선위 정기 13"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_attach_sanction_minutes.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`scripts/attach_sanction_minutes.py`에 다음을 둔다. HTTP 클라이언트는 만들지 않는다.

```python
from __future__ import annotations

import re
from dataclasses import dataclass

LINK_RE = re.compile(r"^- \((\d{2})-(\d{2})-(\d{2})\) \[(.+?)\]\((https?://[^\)]+)\)")
KEY_RE = re.compile(
    r"(20\d{2}|'\d{2}|’\d{2}).{0,40}?(제\s*(\d+)\s*차)\s*(증권선물위원회|금융위원회)"
)
KIND_RE = re.compile(r"임시|서면")


@dataclass(frozen=True)
class DecisionPost:
    year: int
    committee: str
    kind: str
    number: int
    pdf_url: str
    zip_urls: list[str]  # 안건 ZIP URL. 의사록 마커에는 넣지 않고, 감리 의안 추출에 쓴다.


def meeting_key(text: str) -> tuple[int, str, str, int] | None:
    matched = KEY_RE.search(text.replace(" ", ""))
    if not matched:
        return None
    raw_year, _nth, number, committee = matched.groups()
    year = int(raw_year.replace("'", "20").replace("’", "20"))
    if year < 100:
        year += 2000
    kind = "임시" if "임시" in text else "서면" if "서면" in text else "정기"
    name = "증선위" if committee == "증권선물위원회" else "금융위"
    return year, name, kind, int(number)


def select_minutes_pdf(key, posts: list[DecisionPost]) -> str | None:
    found = [post.pdf_url for post in posts if (post.year, post.committee, post.kind, post.number) == key and post.pdf_url]
    if len(found) != 1:
        return None
    return found[0]


def attach_minutes(text: str, posts: list[DecisionPost]) -> tuple[str, list[str]]:
    lines = text.splitlines()
    report: list[str] = []
    in_resolution = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#### "):
            in_resolution = stripped == "#### 제재 의결"
        if in_resolution and (matched := LINK_RE.match(lines[i])):
            block_end = i + 1
            while block_end < len(lines) and not LINK_RE.match(lines[block_end]) and not lines[block_end].startswith("####"):
                block_end += 1
            block = "\n".join(lines[i:block_end])
            key = meeting_key(matched.group(4) + "\n" + block)
            pdf = select_minutes_pdf(key, posts) if key else None
            name = pdf.rsplit("/", 1)[-1] if pdf else ""
            if name and f"downloads/{name}" not in block:
                lines.insert(i + 1, "")
                lines.insert(i + 2, f"    <!-- source: pdf|downloads/{name} -->")
                report.append(f"attached {key[0]} {key[1]} {key[2]} {key[3]}")
                i = block_end + 2
                continue
        i += 1
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), report
```

파일명에 URL 쿼리가 들어가면 테스트의 `downloads/` 포함 조건은 통과하지만 경로는 지저분하다. 테스트 PDF URL을 경로만 쓰도록 위 테스트의 `pdf_url`을 `https://fsc.go.kr/files/minutes-13.pdf`로 두고, 구현의 마커는 `downloads/` 뒤에 URL의 마지막 경로 조각을 쓴다. ZIP 원본 URL은 마커에 넣지 않는다. ZIP 안에서는 감리 의안의 공개용 안건·의결서 PDF만 꺼내 `downloads/sanctions/`에 둔다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts && python -m pytest tests/test_attach_sanction_minutes.py -q`

Expected: PASS. 구현 도중 키 정규식이 공백 제거 문자열과 맞지 않으면 `meeting_key`가 원문과 공백 제거 문자열을 둘 다 보게 고친다. 표 행은 이 함수가 받지 않으므로 테스트 본문에 표가 없어도 된다.

- [ ] **Step 5: Commit**

```bash
git add scripts/attach_sanction_minutes.py scripts/tests/test_attach_sanction_minutes.py
git commit -m "feat: attach one minutes PDF to a sanction item"
```

### Task 4: 처리 기록과 raw 복사

**Files:**

- Create: `scripts/quarterly_handoff.py`
- Create: `scripts/export_quarterly_raw.py`
- Test: `scripts/tests/test_export_quarterly_raw.py`

**Interfaces:**

- Consumes: 분기 마크다운, `downloads/` 파일, `scripts/editor/clips/{id}` 텍스트, 목적지 디렉터리, `today` 날짜
- Produces: `record_from_item(link: str, body: str) -> str`, `export_quarter(md_path: Path, downloads: Path, clips: Path, dest: Path, today: date) -> ExportResult`. `ExportResult.exit_code`는 파일 누락이 있으면 `1`, 목적지 루트가 없으면 `2`, 아니면 `0`.

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
from pathlib import Path

from quarterly_handoff import export_quarter

QUARTER = """---
title: q
---

### 금융위원회

#### 보도자료

- (26-09-11) [계리가정](https://fsc.go.kr/no010101/1)

    <!-- source: pdf|downloads/ifrs.pdf -->
    <!-- source: hwp|downloads/ifrs.hwpx -->

    !!! note "주요 내용"

        - (보고서) 매년 제출

- (26-09-01) [시험 공고](https://fsc.go.kr/no010101/2)
    <!-- no_summary -->
    <!-- source: pdf|downloads/exam.pdf -->

## Appendix A. Complete List

- (26-09-02) [미선별](https://fsc.go.kr/no010101/3)
    <!-- source: pdf|downloads/appendix.pdf -->
"""


def test_export_copies_body_pdf_and_note_without_rereading(tmp_path: Path):
    root = tmp_path / "repo"
    downloads = root / "downloads"
    downloads.mkdir(parents=True)
    (downloads / "ifrs.pdf").write_bytes(b"%PDF-1")
    (downloads / "ifrs.hwpx").write_bytes(b"HWPX")
    (downloads / "exam.pdf").write_bytes(b"%PDF-EXAM")
    (downloads / "appendix.pdf").write_bytes(b"%PDF-APP")
    md = root / "2026-07-01_to_2026-09-30.md"
    md.write_text(QUARTER, encoding="utf-8")
    dest = tmp_path / "raw"
    dest.mkdir()
    result = export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5))
    copied_pdf = dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "ifrs.pdf"
    record = dest / "quality-updates-processed" / "2026-07-01_to_2026-09-30"
    assert copied_pdf.read_bytes() == b"%PDF-1"
    assert not (dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "ifrs.hwpx").exists()
    assert not (dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "exam.pdf").exists()
    assert not (dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30" / "appendix.pdf").exists()
    assert "매년 제출" in next(record.glob("*.md")).read_text(encoding="utf-8")
    assert result.exit_code == 0
    again = export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5))
    assert again.copied == []


def _write_quarter(root: Path) -> tuple[Path, Path]:
    downloads = root / "downloads"
    downloads.mkdir(parents=True)
    (downloads / "ifrs.pdf").write_bytes(b"%PDF-1")
    (downloads / "ifrs.hwpx").write_bytes(b"HWPX")
    md = root / "2026-07-01_to_2026-09-30.md"
    md.write_text(QUARTER, encoding="utf-8")
    return md, downloads


def test_changed_bytes_get_a_dated_snapshot(tmp_path: Path):
    root = tmp_path / "repo"
    md, downloads = _write_quarter(root)
    dest = tmp_path / "raw"
    dest.mkdir()
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 5))
    (downloads / "ifrs.pdf").write_bytes(b"%PDF-2")
    export_quarter(md, downloads, root / "clips", dest, date(2026, 11, 6))
    folder = dest / "quality-updates-sources" / "2026-07-01_to_2026-09-30"
    assert (folder / "ifrs.pdf").read_bytes() == b"%PDF-1"
    assert (folder / "ifrs--2026-11-06.pdf").read_bytes() == b"%PDF-2"


def test_missing_vault_root_copies_nothing(tmp_path: Path):
    root = tmp_path / "repo"
    md, downloads = _write_quarter(root)
    missing = tmp_path / "no-such-vault" / "raw"
    result = export_quarter(md, downloads, root / "clips", missing, date(2026, 11, 5))
    assert result.exit_code == 2
    assert not missing.exists()
```

`test_export_copies_body_pdf_and_note_without_rereading`도 `_write_quarter`를 쓰고, `exam.pdf`와 `appendix.pdf`는 그 테스트 안에서만 추가로 쓴다. 구현은 `exam.pdf`가 디스크에 없어도 `no_summary` 항목이라 누락으로 세지 않는다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_export_quarterly_raw.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`scripts/quarterly_handoff.py`에 본문 구간을 `## Appendix` 전으로 자르고, 항목 블록을 링크 행 단위로 나눈다. 블록에 `<!-- skip -->` 또는 `<!-- no_summary -->`가 있으면 건너뛴다. `<!-- source: pdf|downloads/이름 -->`만 복사한다. 같은 블록의 `hwp`는 복사하지 않고, `pdf` 마커가 없으면 `waiting` 목록에 파일명을 넣는다. `shot`은 png를, `clip|clips/{id}`는 `scripts/editor/clips/{id}`가 있으면 `{id}.txt`로 복사한다.

처리 기록은 링크 행, source 행, `!!! note` 본문을 그대로 담는다. 파일명은 `26-09-11-계리가정.md`처럼 날짜와 링크 제목의 앞 40자에서 `\/:*?"<>|`를 뺀 이름이다. PDF 추출 함수는 import하지 않는다.

복사는 목적지에 파일이 없으면 쓴다. 있고 바이트가 같으면 `skipped`에 넣는다. 있고 바이트가 다르면 `stem--YYYY-MM-DD` 접미 파일이 없을 때만 쓴다. 분기 마크다운도 같은 규칙으로 `raw/quality-updates-{stem}.md`에 쓴다.

`scripts/export_quarterly_raw.py`는 `--dest` 기본값 `Path(r"C:\dev\obsidian-valut\raw")`로 `export_quarter`를 호출하고 `exit_code`를 반환한다. 목적지 루트 디렉터리가 없으면 만들기 전에 `2`를 반환한다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts && python -m pytest tests/test_repair_quarterly_structure.py tests/test_fsc_section_order.py tests/test_attach_sanction_minutes.py tests/test_export_quarterly_raw.py -q`

Expected: PASS

그다음 저장소 루트에서 실행한다.

```bash
python scripts/validate_content.py --strict
mkdocs build --strict
```

Expected: 둘 다 exit 0. 라이브 분기 파일은 수정하지 않았어야 한다.

- [ ] **Step 5: Commit**

```bash
git add scripts/quarterly_handoff.py scripts/export_quarterly_raw.py scripts/tests/test_export_quarterly_raw.py
git commit -m "feat: copy quarter notes and source PDFs into the vault raw folder"
```
