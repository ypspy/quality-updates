# FSS Press-List KRDS Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `FSS.fetch_press_release()`가 KRDS 목록 HTML에서 보도자료 제목·날짜·링크를 다시 수집하게 한다.

**Architecture:** 행 파싱을 `parse_press_list_html(html)`로 분리하고, 셀렉터를 동향자료와 같게 `table tbody tr`로 맞춘다. `fetch_press_release()`는 기존 GET 파라미터를 유지한 채 헬퍼 결과만 페이지 루프에 넣는다. CI는 `fss.or.kr`을 호출하지 않고 픽스처 HTML만 검증한다.

**Tech Stack:** Python 3, pytest, BeautifulSoup4, requests (기존 `scripts/crawler/FSS.py`)

**Spec:** `docs/superpowers/specs/2026-09-09-fss-press-crawler-design.md`

## Global Constraints

- 보도자료 목록 파서만 변경한다. `fetch_accounting_trend`, `fetch_rules_revision`, `unified.py`, 편집기는 수정하지 않는다.
- 목록 URL은 `https://www.fss.or.kr/fss/bbs/B0000188/list.do` 그대로다. 쿼리는 `menuNo=200218`, `pageIndex`, `sdate`, `edate`, `searchCnd`, `searchWrd` 그대로다.
- 행 선택자는 `table tbody tr`이다. `td.title a`와 등록일 칸 `tds[3]`(`%Y-%m-%d`)은 유지한다.
- `parse_press_list_html(html)`은 `{"title": str, "href": str, "posted_on": datetime}` 리스트를 반환한다. href는 문서 그대로(상대경로). 유효 행이 없으면 `[]`.
- CI·단위 테스트는 `fss.or.kr`을 호출하지 않는다.
- 기존 분기 마크다운·HITL 마커는 수정하지 않는다.
- 픽스처는 전체 페이지가 아니라 목록 테이블 조각만 둔다.

---

## File map

| File | Action |
|------|--------|
| `scripts/tests/fixtures/fss_press_list_krds.html` | Create — `bd-list` 없는 KRDS 목록 2행 |
| `scripts/tests/test_fss_press_list.py` | Create — 헬퍼 + mocked `fetch_press_release` |
| `scripts/crawler/FSS.py` | Modify — `parse_press_list_html` 추가, `fetch_press_release`가 헬퍼 사용 |
| `docs/superpowers/README.md` | Modify — Plans 색인에 이 파일 추가 |
| `docs/superpowers/specs/2026-09-09-fss-press-crawler-design.md` | Modify — 상태를 승인됨으로 |

`scripts/crawler/unified.py`는 변경하지 않는다. `collect_fss()`는 이미 `FSS.fetch_press_release()`를 호출한다.

---

### Task 1: KRDS 픽스처와 실패하는 파서 테스트

**Files:**
- Create: `scripts/tests/fixtures/fss_press_list_krds.html`
- Create: `scripts/tests/test_fss_press_list.py`
- Test: `scripts/tests/test_fss_press_list.py`

**Interfaces:**
- Consumes: 없음
- Produces: 테스트가 import할 `crawler.FSS.parse_press_list_html(html: str) -> list[dict]` (`title: str`, `href: str`, `posted_on: datetime`). 이 태스크에서는 함수를 아직 만들지 않는다.

- [ ] **Step 1: Write the KRDS fixture**

Create `scripts/tests/fixtures/fss_press_list_krds.html` with this exact content (no `bd-list` class):

```html
<div class="krds-table-wrap">
<table class="tbl col list-data">
  <caption>보도자료</caption>
  <thead>
    <tr>
      <th>번호</th><th>제목</th><th>담당부서</th><th>등록일</th><th>첨부파일</th><th>영상</th><th>조회수</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="num">2</td>
      <td class="title"><a href="/fss/bbs/B0000188/view.do?nttId=227554&amp;menuNo=200218">공모 목표전환형 펀드 현황 및 투자자 유의사항 안내</a></td>
      <td>자산운용감독국</td>
      <td>2026-09-09</td>
      <td></td>
      <td></td>
      <td>12</td>
    </tr>
    <tr>
      <td class="num">1</td>
      <td class="title"><a href="/fss/bbs/B0000188/view.do?nttId=227555&amp;menuNo=200218">2026년 8월 가계대출 동향(잠정) 및 가계부채 점검회의 개최</a></td>
      <td>은행리스크감독국</td>
      <td>2026-09-08</td>
      <td></td>
      <td></td>
      <td>12</td>
    </tr>
  </tbody>
</table>
</div>
```

- [ ] **Step 2: Write the failing tests**

Create `scripts/tests/test_fss_press_list.py`:

```python
# -*- coding: utf-8 -*-
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler import FSS

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "fss_press_list_krds.html"


def test_parse_press_list_html_extracts_krds_rows():
    html = FIXTURE.read_text(encoding="utf-8")
    items = FSS.parse_press_list_html(html)
    assert len(items) == 2
    assert items[0]["title"] == "공모 목표전환형 펀드 현황 및 투자자 유의사항 안내"
    assert "B0000188/view.do" in items[0]["href"]
    assert "nttId=227554" in items[0]["href"]
    assert items[0]["posted_on"] == datetime(2026, 9, 9)
    assert items[1]["title"] == "2026년 8월 가계대출 동향(잠정) 및 가계부채 점검회의 개최"
    assert "nttId=227555" in items[1]["href"]
    assert items[1]["posted_on"] == datetime(2026, 9, 8)


def test_parse_press_list_html_empty_tbody():
    assert FSS.parse_press_list_html("<table><tbody></tbody></table>") == []
    assert FSS.parse_press_list_html("<div></div>") == []


def test_parse_press_list_html_finds_rows_without_bd_list():
    html = FIXTURE.read_text(encoding="utf-8")
    assert "bd-list" not in html
    items = FSS.parse_press_list_html(html)
    assert len(items) == 2


def test_parse_press_list_html_skips_invalid_rows():
    html = """
    <table><tbody>
      <tr><td class="num">1</td><td>제목없음</td><td>부서</td><td>2026-09-09</td></tr>
      <tr>
        <td class="num">2</td>
        <td class="title"><a href="/fss/bbs/B0000188/view.do?nttId=1">유효</a></td>
        <td>부서</td>
        <td>not-a-date</td>
      </tr>
      <tr>
        <td class="num">3</td>
        <td class="title"><a href="/fss/bbs/B0000188/view.do?nttId=2">정상</a></td>
        <td>부서</td>
        <td>2026-09-01</td>
      </tr>
    </tbody></table>
    """
    items = FSS.parse_press_list_html(html)
    assert len(items) == 1
    assert items[0]["title"] == "정상"
    assert items[0]["posted_on"] == datetime(2026, 9, 1)
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
cd scripts && python -m pytest tests/test_fss_press_list.py -v
```

Expected: FAIL with `ImportError` / `AttributeError` — `parse_press_list_html` is not defined on `crawler.FSS`.

- [ ] **Step 4: Commit**

```bash
git add scripts/tests/fixtures/fss_press_list_krds.html scripts/tests/test_fss_press_list.py
git commit -m "Add failing tests for FSS KRDS press-list parser."
```

---

### Task 2: `parse_press_list_html` 구현

**Files:**
- Modify: `scripts/crawler/FSS.py` (보도자료 함수 바로 위, `fetch_press_release` 앞)
- Test: `scripts/tests/test_fss_press_list.py`

**Interfaces:**
- Consumes: Task 1 픽스처 HTML과 테스트 시그니처
- Produces: `parse_press_list_html(html: str) -> list[dict]` where each dict is `{"title": str, "href": str, "posted_on": datetime}`

- [ ] **Step 1: Implement the helper**

In `scripts/crawler/FSS.py`, insert this function immediately before `def fetch_press_release(max_page=50):`. Do not change `fetch_press_release` yet.

```python
def parse_press_list_html(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for row in soup.select("table tbody tr"):
        a = row.select_one("td.title a")
        tds = row.find_all("td")
        if not a or len(tds) < 4:
            continue
        href = a.get("href") or ""
        if not href:
            continue
        try:
            posted_on = datetime.strptime(tds[3].get_text(strip=True), "%Y-%m-%d")
        except ValueError:
            continue
        results.append({
            "title": a.get_text(strip=True),
            "href": href,
            "posted_on": posted_on,
        })
    return results
```

- [ ] **Step 2: Run tests to verify they pass**

Run:

```bash
cd scripts && python -m pytest tests/test_fss_press_list.py -v
```

Expected: PASS (4 tests). `fetch_press_release` is still using `div.bd-list`; that is intentional until Task 3.

- [ ] **Step 3: Commit**

```bash
git add scripts/crawler/FSS.py
git commit -m "Parse FSS press-list rows from KRDS table markup."
```

---

### Task 3: `fetch_press_release`가 헬퍼를 쓰게 연결

**Files:**
- Modify: `scripts/crawler/FSS.py` (`fetch_press_release`, 기존 약 22–72행)
- Modify: `scripts/tests/test_fss_press_list.py`
- Modify: `docs/superpowers/README.md` (Plans 표)
- Modify: `docs/superpowers/specs/2026-09-09-fss-press-crawler-design.md` (상태 줄)
- Test: `scripts/tests/test_fss_press_list.py`

**Interfaces:**
- Consumes: `parse_press_list_html(html: str) -> list[dict]` from Task 2; module globals `session`, `START_DATE`, `END_DATE`, `start_dt`
- Produces: `fetch_press_release(max_page=50) -> list[dict]` with each item `{"date": "yy-mm-dd", "title": str, "link": str}` (절대 URL). 헬퍼가 `[]`이면 페이지 루프 `break`. `posted_on < start_dt`이면 그때까지 결과 반환.

- [ ] **Step 1: Write the failing fetch wiring test**

Append to `scripts/tests/test_fss_press_list.py`:

```python
from unittest.mock import MagicMock


def test_fetch_press_release_uses_krds_parser(monkeypatch):
    html = FIXTURE.read_text(encoding="utf-8")
    empty = "<table><tbody></tbody></table>"

    def fake_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.text = html if (params or {}).get("pageIndex") == 1 else empty
        return resp

    monkeypatch.setattr(FSS, "START_DATE", "2026-09-01")
    monkeypatch.setattr(FSS, "END_DATE", "2026-09-30")
    monkeypatch.setattr(FSS, "start_dt", datetime(2026, 9, 1))
    monkeypatch.setattr(FSS.session, "get", fake_get)

    items = FSS.fetch_press_release(max_page=3)
    assert len(items) == 2
    assert items[0]["date"] == "26-09-09"
    assert items[0]["title"] == "공모 목표전환형 펀드 현황 및 투자자 유의사항 안내"
    assert items[0]["link"].startswith("https://www.fss.or.kr/")
    assert "nttId=227554" in items[0]["link"]
    assert items[1]["date"] == "26-09-08"
    assert "nttId=227555" in items[1]["link"]


def test_fetch_press_release_stops_before_start_dt(monkeypatch):
    html = FIXTURE.read_text(encoding="utf-8")

    def fake_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.text = html
        return resp

    monkeypatch.setattr(FSS, "START_DATE", "2026-09-09")
    monkeypatch.setattr(FSS, "END_DATE", "2026-09-30")
    monkeypatch.setattr(FSS, "start_dt", datetime(2026, 9, 9))
    monkeypatch.setattr(FSS.session, "get", fake_get)

    items = FSS.fetch_press_release(max_page=1)
    assert len(items) == 1
    assert items[0]["date"] == "26-09-09"
```

- [ ] **Step 2: Run the new test to verify it fails**

Run:

```bash
cd scripts && python -m pytest tests/test_fss_press_list.py::test_fetch_press_release_uses_krds_parser tests/test_fss_press_list.py::test_fetch_press_release_stops_before_start_dt -v
```

Expected: FAIL with `assert 0 == 2` and `assert 0 == 1`. `fetch_press_release` still selects `div.bd-list table tbody tr`, so the fixture yields no rows.

- [ ] **Step 3: Wire `fetch_press_release` to the helper**

Replace the body of `fetch_press_release` in `scripts/crawler/FSS.py` so it looks like this (URL·params·print·`max_page` 유지):

```python
def fetch_press_release(max_page=50):
    BASE_URL = "https://www.fss.or.kr/fss/bbs/B0000188/list.do"
    results = []

    print("\n[START] 보도자료 수집", flush=True)

    for page in range(1, max_page + 1):
        print(f"[보도자료] pageIndex={page}", flush=True)

        res = session.get(
            BASE_URL,
            params={
                "menuNo": "200218",
                "pageIndex": page,
                "sdate": START_DATE,
                "edate": END_DATE,
                "searchCnd": "1",
                "searchWrd": "",
            },
            timeout=10,
        )

        rows = parse_press_list_html(res.text)
        print(f"  └ rows: {len(rows)}", flush=True)

        if not rows:
            break

        for item in rows:
            if item["posted_on"] < start_dt:
                print("  └ 시작일 이전 도달 → 종료", flush=True)
                return results

            results.append({
                "date": item["posted_on"].strftime("%y-%m-%d"),
                "title": item["title"],
                "link": urljoin(BASE_URL, item["href"]),
            })

    return results
```

Do not edit `fetch_accounting_trend` or `fetch_rules_revision`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd scripts && python -m pytest tests/test_fss_press_list.py tests/test_crawl.py -q
```

Expected: PASS. `test_fss_press_list.py` 6 tests + existing `test_crawl.py` tests.

- [ ] **Step 5: Index the plan and mark the spec approved**

In `docs/superpowers/README.md`, add this row at the top of the **Plans (구현)** table (same pattern as Specs):

```markdown
| 2026-09-09 | [fss-press-crawler.md](plans/2026-09-09-fss-press-crawler.md) | FSS 보도자료 목록 파서 KRDS 셀렉터 수정 |
```

In `docs/superpowers/specs/2026-09-09-fss-press-crawler-design.md`, change:

```markdown
**상태**: 초안 (브레인스토밍 합의됨)
```

to:

```markdown
**상태**: 승인됨
```

- [ ] **Step 6: Commit**

```bash
git add scripts/crawler/FSS.py scripts/tests/test_fss_press_list.py docs/superpowers/README.md docs/superpowers/specs/2026-09-09-fss-press-crawler-design.md
git commit -m "Wire FSS press crawl to the KRDS list parser."
```

---

## Spec coverage

| Spec requirement | Task |
|------------------|------|
| 셀렉터 `table tbody tr` | Task 2–3 |
| `td.title a` + `tds[3]` 날짜 | Task 2 |
| URL·쿼리 유지 | Task 3 |
| `parse_press_list_html` 분리 | Task 2 |
| 헬퍼 `[]` → 페이지 `break` | Task 3 |
| `posted_on < start_dt` 종료 | Task 3 (`test_fetch_press_release_stops_before_start_dt`) |
| KRDS 2건 픽스처 | Task 1 |
| 빈 tbody → `[]` | Task 1–2 |
| `bd-list` 없어도 행 발견 | Task 1–2 |
| 무효 행 skip | Task 1–2 |
| 동향자료·세칙·편집기·live crawl 금지 | Global Constraints + Task 3 Step 3 |
| 완료 검증 `test_fss_press_list.py` + `test_crawl.py` | Task 3 Step 4 |
