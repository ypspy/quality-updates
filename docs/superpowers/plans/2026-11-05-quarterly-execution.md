# 크롤 분류·의사록 수신·처리 기록 작성 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 새 분기 크롤이 조사·감리 제목을 `제재 의결`에 두고, 의사록 명령이 의사록 PDF만 연결하며, 요약 세션이 처리 기록을 함수로 남기게 한다.

**Architecture:** 제목 분리는 `classify_url`을 부르는 순수 함수 `split_fsc_press`가 한다. 의사록은 보도 제목의 `meeting_key`와 의결정보 제목의 `decision_key`를 맞추고, HTML 수신은 테스트가 주입한다. 처리 기록은 `write_quarterly_record.py`만 쓰고, 요약 스킬은 그 명령을 호출하라고 적는다.

**Tech Stack:** Python 3, pytest, pathlib, BeautifulSoup, requests. 새 의존성 없음.

**Spec:** `docs/superpowers/specs/2026-11-05-quarterly-execution-design.md`

## Global Constraints

- 금융위 보도 링크는 제목에 `조사·감리결과 조치`가 있을 때만 `제재 의결`로 간다. 가운뎃점은 U+00B7이다. `제N차`와 `조치 의결`만으로는 옮기지 않는다.
- 금감원·한공회·회계기준원 링크는 `제재 의결`로 옮기지 않는다. 이미 있는 분기 파일은 다시 배치하지 않는다.
- 의사록으로 받는 글은 제목에 `의사록`이 있는 글뿐이다. `회의결과` 글의 PDF는 받지 않는다. 첨부 이름에 `의사록`이 있고 `.pdf`로 끝나는 파일만 받는다. 안건 ZIP과 의결 PDF는 요청하지 않는다.
- 한 회의 키의 의사록 PDF가 둘이 되면 마커를 붙이지 않는다. `의사록(추가)`도 같은 키의 두 번째 PDF다.
- 마커 대상은 `#### 제재 의결` 안에서 `위원 논의`가 없거나 그 노트에 `미공개`가 있는 항목이다. 조치 표와 `위원 논의` 문장은 명령이 쓰지 않는다.
- 목록 검색 시작일은 분기 시작일, 종료일은 분기 말일에 70일을 더한 날짜다. 파일명이 `YYYY-MM-DD_to_YYYY-MM-DD.md`가 아니면 종료 코드 2다.
- 처리 기록 경로는 `data/quarterly-processed/{분기 파일 stem}/{YY-MM-DD}-{제목 앞 40자}.md`다. 같은 경로가 있으면 기본 모드는 바이트를 유지한다.
- `<!-- skip -->`, `<!-- no_summary -->`, Appendix 항목은 처리 기록 파일을 만들지 않는다. 이 명령은 분기 파일을 수정하지 않는다.
- 테스트는 저장해 둔 HTML과 임시 디렉터리만 쓴다. 금융위 사이트에 접속하지 않는다. `repair_quarterly_structure.py`를 `docs/quality-updates/2026/2026-07-01_to_2026-09-30.md`에 실행하지 않는다. 그 파일은 커밋하지 않는다.
- 웨일을 실행하지 않고 LibreOffice를 호출하지 않는다. 위키 `wiki/`는 쓰지 않는다.

---

### Task 1: 크롤 때 제목 이동

**Files:**
- Modify: `scripts/crawler/unified.py` (`collect_fsc`, 새 `split_fsc_press`, 새 `render_fsc_press`)
- Test: `scripts/tests/test_fsc_section_order.py`

**Interfaces:**
- Consumes: `repair_quarterly_structure.classify_url(url: str, title: str = "") -> tuple[str, str]`, `repair_quarterly_structure.LINK_RE`, `FSC_MAIN_HEADINGS`, `sort_md_link_lines(items: list[str]) -> list[str]`
- Produces: `split_fsc_press(lines: list[str]) -> tuple[list[str], list[str]]`, `render_fsc_press(lines: list[str]) -> str`. 첫 목록은 보도자료, 둘째 목록은 제재 의결이다.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_fsc_section_order.py` 끝에 다음을 추가한다.

```python
from crawler.unified import render_fsc_press

SANCTION = "- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치 - 제13차 증권선물위원회(’26.7.8.) 조치 의결](https://fsc.go.kr/no010101/87293)"
UNFAIR = "- (26-09-02) [상장사 IR 담당 임원의 불공정거래 혐의 적발·조치 - 제15차 증권선물위원회(9.2.) 의결](https://fsc.go.kr/no010101/87638)"
CARD = "- (26-07-31) [롯데카드(주)의 정보유출 관련 1.5개월 업무정지 및 50억원 과징금 부과 - 제14차 금융위원회(’26.7.31.) 조치 의결](https://fsc.go.kr/no010101/87455)"
NO_NUMBER = "- (26-07-23) [사업보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/87394)"


def test_split_fsc_press_puts_investigation_titles_under_sanctions():
    rendered = render_fsc_press([SANCTION, UNFAIR, CARD, NO_NUMBER])
    sanction_at = rendered.index("#### 제재 의결")
    press_at = rendered.index("#### 보도자료")
    assert press_at < sanction_at
    assert rendered.index(SANCTION) > sanction_at
    assert rendered.index(NO_NUMBER) > sanction_at
    assert rendered.index(UNFAIR) < sanction_at
    assert rendered.index(CARD) < sanction_at


def test_sanction_heading_remains_when_no_title_matches():
    rendered = render_fsc_press([UNFAIR])
    assert "#### 제재 의결" in rendered
    assert rendered.index(UNFAIR) < rendered.index("#### 제재 의결")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_fsc_section_order.py::test_split_fsc_press_puts_investigation_titles_under_sanctions -q`

Expected: FAIL with `ImportError: cannot import name 'render_fsc_press'`

- [ ] **Step 3: Write minimal implementation**

`scripts/crawler/unified.py`의 `sort_md_link_lines` 위에 다음을 추가한다.

```python
def split_fsc_press(lines: list[str]) -> tuple[list[str], list[str]]:
    """Return press lines and sanction lines. Sanction titles contain 조사·감리결과 조치."""
    import repair_quarterly_structure as repair

    press: list[str] = []
    sanctions: list[str] = []
    for line in lines:
        matched = repair.LINK_RE.match(line)
        if matched is None:
            press.append(line)
            continue
        _agency, section = repair.classify_url(matched.group(5), matched.group(4))
        if section == "제재 의결":
            sanctions.append(line)
        else:
            press.append(line)
    return press, sanctions


def render_fsc_press(lines: list[str]) -> str:
    briefing, sanctions = split_fsc_press(lines)
    parts = [
        "#### 보도자료\n",
        "\n".join(sort_md_link_lines(briefing)),
        f"\n#### {FSC_MAIN_HEADINGS[1]}\n",
        "\n".join(sort_md_link_lines(sanctions)),
    ]
    return "\n".join(parts)
```

`collect_fsc()`의 보도자료 조립을 다음으로 바꾼다. `APPENDIX["금융위원회"]["보도자료"]`는 게시판에서 받은 전체 `press`를 유지한다.

```python
    press = FSC.crawl_board("보도자료", FSC.BASE_URLS["보도자료"])
    APPENDIX["금융위원회"]["보도자료"] = press
    lines += [render_fsc_press(press)]
```

기존의 `#### 보도자료` 줄과 빈 `#### 제재 의결` 줄은 이 호출이 대신한다. 고시·입법예고 줄은 그대로 둔다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts && python -m pytest tests/test_fsc_section_order.py tests/test_repair_quarterly_structure.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/crawler/unified.py scripts/tests/test_fsc_section_order.py
git commit -m "feat: place investigation sanctions while crawling FSC press"
```

---

### Task 2: 의결정보 제목 키와 논의 있는 항목 제외

**Files:**
- Modify: `scripts/attach_sanction_minutes.py`
- Test: `scripts/tests/test_attach_sanction_minutes.py`

**Interfaces:**
- Consumes: 기존 `meeting_key`, `select_minutes_pdf`, `attach_minutes`, `DecisionPost`
- Produces: `decision_key(title: str) -> tuple[int, str, str, int] | None`. 튜플은 `(연도, "금융위"|"증선위", "정기"|"임시"|"서면", 차수)`다. `attach_minutes`는 `위원 논의`가 있고 `미공개`가 없으면 마커를 넣지 않고 `skipped discussion {year} {committee} {kind} {number}`를 보고한다.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_attach_sanction_minutes.py` 끝에 다음을 추가한다.

```python
from attach_sanction_minutes import decision_key


def test_decision_key_reads_the_live_board_title():
    assert decision_key("2026년 제15차 증권선물위원회 의사록, 안건 및 제재안건 의결서") == (
        2026,
        "증선위",
        "정기",
        15,
    )
    assert decision_key("2026년 제1차 임시증권선물위원회 의사록 및 안건") == (
        2026,
        "증선위",
        "임시",
        1,
    )
    assert decision_key("2026년 제2차 증권선물위원회 임시회의 회의결과") == (
        2026,
        "증선위",
        "임시",
        2,
    )
    assert decision_key("2026년 제14차 금융위원회 의사록") == (2026, "금융위", "정기", 14)
    assert decision_key("회의 안내") is None


def test_filled_discussion_does_not_receive_a_minutes_marker():
    filled = PRESS.replace("미공개임", "회사 조치는 원안임")
    updated, report = attach_minutes(filled, [POSTS[0]])
    assert updated == filled
    assert report == ["skipped discussion 2026 증선위 정기 13"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_attach_sanction_minutes.py::test_decision_key_reads_the_live_board_title tests/test_attach_sanction_minutes.py::test_filled_discussion_does_not_receive_a_minutes_marker -q`

Expected: FAIL with `ImportError: cannot import name 'decision_key'`. 구현 후 두 번째 테스트만 남으면 `skipped discussion` 보고가 없어 FAIL이다.

- [ ] **Step 3: Write minimal implementation**

`scripts/attach_sanction_minutes.py`에 다음을 추가한다.

```python
DECISION_KEY_RE = re.compile(
    r"(?P<year>\d{4})년\s*제\s*(?P<number>\d+)\s*차\s*"
    r"(?P<early>임시|서면)?\s*"
    r"(?P<committee>증권선물위원회|금융위원회)"
)


def decision_key(title: str) -> tuple[int, str, str, int] | None:
    """Year, committee, kind, and number from a decision-board title."""
    matched = DECISION_KEY_RE.search(title)
    if matched is None:
        return None
    if matched.group("early"):
        kind = matched.group("early")
    elif "임시" in title:
        kind = "임시"
    elif "서면" in title:
        kind = "서면"
    else:
        kind = "정기"
    committee = "증선위" if matched.group("committee") == "증권선물위원회" else "금융위"
    return int(matched.group("year")), committee, kind, int(matched.group("number"))


def _eligible_block(block: str) -> bool:
    marker = '!!! note "위원 논의"'
    start = block.find(marker)
    if start < 0:
        return True
    body = block[start + len(marker) :]
    next_note = body.find("!!! note")
    if next_note >= 0:
        body = body[:next_note]
    return "미공개" in body
```

`attach_minutes`의 항목 루프에서 `meeting_key`를 구하기 전에 다음을 넣는다. 키가 있고 논의가 이미 채워져 있으면 마커를 넣지 않고 보고만 한다.

```python
            if not _eligible_block(block):
                if key := meeting_key(matched.group(4) + "\n" + block):
                    report.append(
                        f"skipped discussion {key[0]} {key[1]} {key[2]} {key[3]}"
                    )
                i = block_end
                continue
```

기존 `key = meeting_key(...)` 줄은 이 분기 다음에 둔다. 파일명이 이미 있는 항목의 빈 보고는 유지한다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts && python -m pytest tests/test_attach_sanction_minutes.py -q`

Expected: PASS. 기존 `미공개` fixture는 계속 마커가 붙는다.

- [ ] **Step 5: Commit**

```bash
git add scripts/attach_sanction_minutes.py scripts/tests/test_attach_sanction_minutes.py
git commit -m "feat: read decision-board titles and skip filled discussions"
```

---

### Task 3: 의사록 PDF 수신

**Files:**
- Modify: `scripts/attach_sanction_minutes.py`
- Test: `scripts/tests/test_attach_sanction_minutes.py`

**Interfaces:**
- Consumes: `decision_key`, `meeting_key`, `select_minutes_pdf`, `attach_minutes`, `_eligible_block`, `_minutes_filename`
- Produces: `parse_decision_list(html: str) -> list[tuple[str, str]]`, `minutes_pdf_urls(detail_html: str) -> list[str]`, `collect_posts(fetch_text, start: date, end: date) -> list[DecisionPost]`, `pending_downloads(text: str, posts: list[DecisionPost]) -> list[tuple[str, str]]`, `run_minutes(text: str, quarter_name: str, fetch_text, download, downloads: Path) -> tuple[int, str, list[str]]`, `main(argv: list[str] | None = None) -> int`

`fetch_text(url: str) -> str`다. `download(url: str, dest: Path) -> None`이다. `pending_downloads`의 각 쌍은 `(pdf_url, 파일명)`이고 파일명에는 `downloads/`를 붙이지 않는다.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_attach_sanction_minutes.py` 끝에 다음을 추가한다.

```python
from datetime import date
from attach_sanction_minutes import (
    collect_posts,
    minutes_pdf_urls,
    parse_decision_list,
    run_minutes,
)

LIST_HTML = """
<ul>
  <li><div class="inner"><div class="subject"><a href="/no020102/88040">2026년 제15차 증권선물위원회 의사록, 안건 및 제재안건 의결서</a></div><div class="day">2026-10-30</div></div></li>
  <li><div class="inner"><div class="subject"><a href="/no020102/88015">2026년 제19차 증권선물위원회 회의결과</a></div><div class="day">2026-10-29</div></div></li>
  <li><div class="inner"><div class="subject"><a href="/no020102/87906">2026년 제1차 임시증권선물위원회 의사록 및 안건</a></div><div class="day">2026-10-09</div></div></li>
</ul>
"""

DETAIL_MINUTES = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=1">2026년 제15차 증권선물위원회 의사록 (공개용)_F.pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=1">파일다운로드</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=2">2026년 제15차 증권선물위원회 안건 및 제재안건 의결서.zip</a>
"""

DETAIL_RESULT = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=88015&fileTy=ATTACH&fileNo=1">제19차 증권선물위원회 정례회의 결과(홈).pdf</a>
"""

DETAIL_SPECIAL = """
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87906&fileTy=ATTACH&fileNo=1">2026년 제1차 임시증권선물위원회 의사록 (공개용)_F.pdf</a>
<a href="/comm/getFile?srvcId=BBSTY1&upperNo=87906&fileTy=ATTACH&fileNo=2">(공개용) 의결 234.pdf</a>
"""

QUARTER = """### 금융위원회

#### 제재 의결

- (26-09-02) [사업보고서 등에 대한 조사·감리결과 조치 - 제15차 증권선물위원회(’26.9.2.) 조치 의결](https://fsc.go.kr/no010101/87639)

    !!! note "위원 논의"

        - 미공개임

- (26-10-09) [사업보고서 등에 대한 조사·감리결과 조치 - 제1차 임시증권선물위원회(’26.10.9.) 조치 의결](https://fsc.go.kr/no010101/87900)

    !!! note "위원 논의"

        - 미공개임
"""


def test_parser_keeps_minutes_pdfs_and_drops_other_attachments():
    rows = parse_decision_list(LIST_HTML)
    assert rows[0][0].startswith("2026년 제15차")
    assert rows[0][1] == "https://www.fsc.go.kr/no020102/88040"
    assert minutes_pdf_urls(DETAIL_MINUTES) == [
        "https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=88040&fileTy=ATTACH&fileNo=1"
    ]
    assert minutes_pdf_urls(DETAIL_RESULT) == []
    assert minutes_pdf_urls(DETAIL_SPECIAL) == [
        "https://www.fsc.go.kr/comm/getFile?srvcId=BBSTY1&upperNo=87906&fileTy=ATTACH&fileNo=1"
    ]


def test_run_minutes_downloads_only_minutes_pdfs(tmp_path):
    requested = []

    def fetch_text(url: str) -> str:
        requested.append(url)
        if "curPage=1" in url and "no020102" in url:
            return LIST_HTML
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/88040"):
            return DETAIL_MINUTES
        if url.endswith("/87906"):
            return DETAIL_SPECIAL
        if url.endswith("/88015"):
            raise AssertionError("meeting-result page must not be fetched")
        raise AssertionError(url)

    def download(url: str, dest: Path) -> None:
        assert "fileNo=2" not in url
        assert url.endswith("fileNo=1")
        dest.write_bytes(b"pdf")

    code, updated, report = run_minutes(
        QUARTER,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download,
        tmp_path,
    )
    assert code == 0
    assert "minutes-2026-증선위-정기-15.pdf" in updated
    assert "minutes-2026-증선위-임시-1.pdf" in updated
    assert "fileNo=2" not in updated
    assert (tmp_path / "minutes-2026-증선위-정기-15.pdf").read_bytes() == b"pdf"
    assert not any("88015" in url for url in requested)
    assert any("srchBeginDt=2026-07-01" in url and "srchEndDt=2026-12-09" in url for url in requested)


def test_two_minutes_pdfs_for_one_meeting_do_not_attach(tmp_path):
    extra = LIST_HTML.replace(
        "</ul>",
        '<li><div class="inner"><div class="subject"><a href="/no020102/87747">2026년 제15차 증권선물위원회 의사록(추가)</a></div><div class="day">2026-09-18</div></div></li></ul>',
    )

    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020102" in url:
            return extra
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/88040") or url.endswith("/87747"):
            return DETAIL_MINUTES
        if url.endswith("/87906"):
            return DETAIL_SPECIAL
        return "<ul></ul>"

    def download(url: str, dest: Path) -> None:
        if "upperNo=88040" in url or "upperNo=87747" in url:
            raise AssertionError("ambiguous minutes must not be downloaded")
        dest.write_bytes(b"pdf")

    code, updated, report = run_minutes(
        QUARTER,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download,
        tmp_path,
    )
    assert code == 0
    assert "정기-15.pdf" not in updated
    assert any(line.startswith("ambiguous 2026 증선위 정기 15") for line in report)


def test_download_failure_leaves_the_quarter_text_unchanged(tmp_path):
    def fetch_text(url: str) -> str:
        if "curPage=1" in url and "no020102" in url:
            return LIST_HTML
        if "curPage=" in url:
            return "<ul></ul>"
        if url.endswith("/88040"):
            return DETAIL_MINUTES
        if url.endswith("/87906"):
            return DETAIL_SPECIAL
        return "<ul></ul>"

    def download(url: str, dest: Path) -> None:
        dest.write_bytes(b"partial")
        raise OSError("disk full")

    code, updated, report = run_minutes(
        QUARTER,
        "2026-07-01_to_2026-09-30.md",
        fetch_text,
        download,
        tmp_path,
    )
    assert code == 1
    assert updated == QUARTER
    assert list(tmp_path.iterdir()) == []


def test_bad_quarter_filename_exits_2(tmp_path):
    code, updated, report = run_minutes("x", "notes.md", lambda url: "", lambda url, dest: None, tmp_path)
    assert code == 2
    assert updated == "x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_attach_sanction_minutes.py::test_parser_keeps_minutes_pdfs_and_drops_other_attachments -q`

Expected: FAIL with `ImportError: cannot import name 'parse_decision_list'`

- [ ] **Step 3: Write minimal implementation**

`scripts/attach_sanction_minutes.py` 맨 위에 `from datetime import date, timedelta`와 `from pathlib import Path`를 추가한다. BeautifulSoup는 함수 안에서 `from bs4 import BeautifulSoup`로 가져온다.

```python
BOARDS = ("https://www.fsc.go.kr/no020101", "https://www.fsc.go.kr/no020102")
QUARTER_NAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})\.md$")


def parse_decision_list(html: str) -> list[tuple[str, str]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    rows: list[tuple[str, str]] = []
    for item in soup.select("li > div.inner"):
        subject = item.select_one(".subject a")
        if subject is None or not subject.get("href"):
            continue
        href = subject["href"]
        if href.startswith("http"):
            url = href
        else:
            url = "https://www.fsc.go.kr" + href
        rows.append((subject.get_text(" ", strip=True), url.split("?", 1)[0]))
    return rows


def minutes_pdf_urls(detail_html: str) -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(detail_html, "html.parser")
    found: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = anchor.get("href") or ""
        name = anchor.get_text(" ", strip=True)
        if "getFile" not in href or "의사록" not in name or not name.lower().endswith(".pdf"):
            continue
        url = href if href.startswith("http") else "https://www.fsc.go.kr" + href
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
    return found


def _list_url(board: str, page: int, start: date, end: date) -> str:
    return (
        f"{board}?curPage={page}&srchBeginDt={start.isoformat()}"
        f"&srchEndDt={end.isoformat()}&srchCtgry=&srchKey=&srchText="
    )


def collect_posts(fetch_text, start: date, end: date) -> list[DecisionPost]:
    posts: list[DecisionPost] = []
    for board in BOARDS:
        page = 1
        while True:
            rows = parse_decision_list(fetch_text(_list_url(board, page, start, end)))
            if not rows:
                break
            for title, url in rows:
                key = decision_key(title)
                if key is None or "의사록" not in title:
                    continue
                pdfs = minutes_pdf_urls(fetch_text(url))
                if not pdfs:
                    posts.append(DecisionPost(*key, "", []))
                else:
                    for pdf in pdfs:
                        posts.append(DecisionPost(*key, pdf, []))
            page += 1
    return posts


def pending_downloads(text: str, posts: list[DecisionPost]) -> list[tuple[str, str]]:
    lines = text.splitlines()
    pending: list[tuple[str, str]] = []
    in_resolution = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#### "):
            in_resolution = stripped == "#### 제재 의결"
        matched = LINK_RE.match(lines[i]) if in_resolution else None
        if matched:
            block_end = i + 1
            while block_end < len(lines) and not LINK_RE.match(lines[block_end]) and not lines[block_end].startswith("####"):
                block_end += 1
            block = "\n".join(lines[i:block_end])
            key = meeting_key(matched.group(4) + "\n" + block)
            if key and _eligible_block(block):
                found = [post.pdf_url for post in posts if (post.year, post.committee, post.kind, post.number) == key and post.pdf_url]
                if len(found) == 1:
                    name = _minutes_filename(found[0], key)
                    if f"downloads/{name}" not in block:
                        pending.append((found[0], name))
            i = block_end
            continue
        i += 1
    return pending


def _quarter_window(quarter_name: str) -> tuple[date, date] | None:
    matched = QUARTER_NAME_RE.search(quarter_name)
    if matched is None:
        return None
    start = date.fromisoformat(matched.group(1))
    end = date.fromisoformat(matched.group(2)) + timedelta(days=70)
    return start, end


def run_minutes(text, quarter_name, fetch_text, download, downloads: Path):
    window = _quarter_window(quarter_name)
    if window is None:
        return 2, text, []
    written: list[Path] = []
    try:
        posts = collect_posts(fetch_text, *window)
        pending = pending_downloads(text, posts)
        for url, name in pending:
            dest = downloads / name
            if dest.is_file():
                continue
            written.append(dest)
            download(url, dest)
        updated, report = attach_minutes(text, posts)
    except Exception:
        for dest in written:
            if dest.is_file():
                dest.unlink()
        return 1, text, []
    return 0, updated, report


def _http_text(url: str) -> str:
    import requests

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def _http_download(url: str, dest: Path) -> None:
    import requests

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)


def main(argv: list[str] | None = None) -> int:
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        return 2
    path = Path(args[0])
    if not path.is_file():
        return 2
    text = path.read_text(encoding="utf-8")
    downloads = Path(__file__).resolve().parent.parent / "downloads"
    code, updated, report = run_minutes(text, path.name, _http_text, _http_download, downloads)
    if code == 0 and updated != text:
        path.write_text(updated, encoding="utf-8")
    for line in report:
        print(line)
    return code
```

`block =`부터 그 항목을 마치는 `continue`까지를 아래 코드로 바꾼다. Task 2에서 넣은 `_eligible_block` 분기가 그 구간에 있으면 이 코드가 대신하므로 남기지 않는다. `block_end`를 계산하는 루프는 이 코드 앞에 그대로 둔다.

```python
            block = "\n".join(lines[i:block_end])
            key = meeting_key(matched.group(4) + "\n" + block)
            if key and not _eligible_block(block):
                report.append(f"skipped discussion {key[0]} {key[1]} {key[2]} {key[3]}")
                i = block_end
                continue
            found = [
                post.pdf_url
                for post in posts
                if key and (post.year, post.committee, post.kind, post.number) == key and post.pdf_url
            ]
            if key and len(found) == 0:
                report.append(f"unpublished {key[0]} {key[1]} {key[2]} {key[3]}")
            elif key and len(found) > 1:
                report.append(f"ambiguous {key[0]} {key[1]} {key[2]} {key[3]}")
            elif key and len(found) == 1:
                name = _minutes_filename(found[0], key)
                if f"downloads/{name}" not in block:
                    lines.insert(i + 1, "")
                    lines.insert(i + 2, f"    <!-- source: pdf|downloads/{name} -->")
                    report.append(f"attached {key[0]} {key[1]} {key[2]} {key[3]}")
                    i = block_end + 2
                    continue
            i = block_end
            continue
```

`if __name__ == "__main__": raise SystemExit(main())`를 파일 끝에 둔다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts && python -m pytest tests/test_attach_sanction_minutes.py -q`

Expected: PASS. 이 테스트 파일 실행 중에 `fsc.go.kr` 요청이 없어야 한다.

- [ ] **Step 5: Commit**

```bash
git add scripts/attach_sanction_minutes.py scripts/tests/test_attach_sanction_minutes.py
git commit -m "feat: download one minutes PDF for an unpublished sanction"
```

---

### Task 4: 처리 기록 작성

**Files:**
- Create: `scripts/write_quarterly_record.py`
- Test: `scripts/tests/test_write_quarterly_record.py`

**Interfaces:**
- Consumes: `quarterly_handoff.LINK_RE`, `SOURCE_RE`, `SKIP_RE`, `APPENDIX_RE`, `_record_filename(date_text: str, title: str) -> str`, `_items(text: str) -> list[tuple[str, str, str, str]]`
- Produces: `write_record(quarter_text: str, quarter_stem: str, title: str, facts: list[str], date_text: str | None, mode: str, repo_root: Path) -> tuple[int, str]`. `mode`는 `"create"`, `"append-facts"`, `"append-minutes"` 중 하나다. 반환 문자열은 `kept`, `skipped`, `wrote` 중 하나로 시작하고 경로를 포함한다.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_write_quarterly_record.py`를 만든다.

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from write_quarterly_record import write_record

QUARTER = """### 금융위원회

#### 보도자료

- (26-07-09) [사업보고서 등에 대한 조사·감리결과 조치](https://fsc.go.kr/no010101/87293)

    <!-- source: pdf|downloads/260708.pdf -->

    !!! note "주요 내용"

        - 과징금 10백만원

- (26-07-09) [같은 제목](https://fsc.go.kr/no010101/2)

- (26-07-10) [같은 제목](https://fsc.go.kr/no010101/3)

- (26-07-11) [건너뜀](https://fsc.go.kr/no010101/4)

    <!-- skip -->

## Appendix

- (26-07-12) [부록 항목](https://fsc.go.kr/no010101/5)
"""


def test_write_record_creates_facts_and_keeps_existing_bytes(tmp_path):
    code, message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["과징금 10백만원", "사이트 노트에 없는 문단 번호 3"], None, "create", tmp_path,
    )
    assert code == 0
    assert message.startswith("wrote ")
    path = tmp_path / "data" / "quarterly-processed" / "2026-07-01_to_2026-09-30"
    saved = next(path.glob("26-07-09-*.md"))
    text = saved.read_text(encoding="utf-8")
    assert "https://fsc.go.kr/no010101/87293" in text
    assert "downloads/260708.pdf" in text
    assert "## 확인한 사실" in text
    assert "문단 번호 3" in text
    assert "부록 항목" not in text
    saved.write_text(text + "보존\n", encoding="utf-8")
    code, message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["다른 사실"], None, "create", tmp_path,
    )
    assert code == 0
    assert message.startswith("kept ")
    assert saved.read_text(encoding="utf-8").endswith("보존\n")


def test_append_facts_and_minutes_do_not_rewrite_existing_sections(tmp_path):
    write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["과징금 10백만원"], None, "create", tmp_path,
    )
    code, _message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["과징금 10백만원", "추가 사실"], None, "append-facts", tmp_path,
    )
    assert code == 0
    saved = next((tmp_path / "data" / "quarterly-processed" / "2026-07-01_to_2026-09-30").glob("*.md"))
    text = saved.read_text(encoding="utf-8")
    assert text.count("과징금 10백만원") == 1
    assert "추가 사실" in text
    code, _message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["원안 의결함"], None, "append-minutes", tmp_path,
    )
    assert code == 0
    text = saved.read_text(encoding="utf-8")
    assert "## 위원 논의" in text
    assert "원안 의결함" in text
    assert text.index("## 확인한 사실") < text.index("## 위원 논의")
    code, message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        ["두 번째 논의"], None, "append-minutes", tmp_path,
    )
    assert code == 0
    assert message.startswith("kept ")
    assert saved.read_text(encoding="utf-8").count("## 위원 논의") == 1


def test_skip_duplicate_title_and_empty_facts(tmp_path):
    code, message = write_record(QUARTER, "2026-07-01_to_2026-09-30", "건너뜀", ["사실"], None, "create", tmp_path)
    assert code == 0
    assert message.startswith("skipped")
    assert not (tmp_path / "data").exists()
    code, message = write_record(QUARTER, "2026-07-01_to_2026-09-30", "같은 제목", ["사실"], None, "create", tmp_path)
    assert code == 1
    code, message = write_record(QUARTER, "2026-07-01_to_2026-09-30", "같은 제목", ["사실"], "26-07-10", "create", tmp_path)
    assert code == 0
    assert message.startswith("wrote ")
    code, message = write_record(QUARTER, "2026-07-01_to_2026-09-30", "없는 제목", ["사실"], None, "create", tmp_path)
    assert code == 1
    code, message = write_record(
        QUARTER, "2026-07-01_to_2026-09-30", "사업보고서 등에 대한 조사·감리결과 조치",
        [], None, "create", tmp_path,
    )
    assert code == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_write_quarterly_record.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'write_quarterly_record'`

- [ ] **Step 3: Write minimal implementation**

`scripts/write_quarterly_record.py`를 만든다.

```python
"""Write one processed quarter record. Does not modify the quarter file."""

from __future__ import annotations

import sys
from pathlib import Path

from quarterly_handoff import (
    APPENDIX_RE,
    SKIP_RE,
    SOURCE_RE,
    _items,
    _record_filename,
)


def _matches(items, title: str, date_text: str | None):
    found = [item for item in items if item[3] == title and (date_text is None or item[2] == date_text)]
    return found


def _render(link: str, body: str, facts: list[str]) -> str:
    lines = [link.rstrip(), ""]
    for line in body.splitlines():
        if SOURCE_RE.search(line):
            lines.append(line.rstrip())
    lines.extend(["", "## 확인한 사실", ""])
    lines.extend(f"- {fact}" for fact in facts)
    return "\n".join(lines).rstrip() + "\n"


def _append_facts(text: str, facts: list[str]) -> str | None:
    marker = "## 확인한 사실\n"
    start = text.find(marker)
    if start < 0:
        return None
    body_start = start + len(marker)
    next_heading = text.find("\n## ", body_start)
    section = text[body_start:] if next_heading < 0 else text[body_start:next_heading]
    tail = "" if next_heading < 0 else text[next_heading:]
    existing = {line.strip()[2:] for line in section.splitlines() if line.strip().startswith("- ")}
    added = [fact for fact in facts if fact not in existing]
    if not added:
        return text
    if section and not section.endswith("\n"):
        section += "\n"
    addition = "".join(f"- {fact}\n" for fact in added)
    return text[:body_start] + section + addition + tail


def _append_minutes(text: str, facts: list[str]) -> str | None:
    if "## 위원 논의" in text:
        return None
    body = "".join(f"- {fact}\n" for fact in facts)
    return text.rstrip() + "\n\n## 위원 논의\n\n" + body


def write_record(quarter_text, quarter_stem, title, facts, date_text, mode, repo_root: Path):
    if mode not in {"create", "append-facts", "append-minutes"}:
        return 1, "invalid mode"
    body = APPENDIX_RE.split(quarter_text, maxsplit=1)[0]
    found = _matches(_items(body), title, date_text)
    if len(found) != 1:
        return 1, "not found"
    link, item_body, item_date, item_title = found[0]
    if SKIP_RE.search(item_body):
        return 0, "skipped"
    path = repo_root / "data" / "quarterly-processed" / quarter_stem / _record_filename(item_date, item_title)
    if mode == "create" and path.is_file():
        return 0, f"kept {path}"
    if mode != "create" and not path.is_file():
        return 1, f"missing {path}"
    if not facts:
        return 1, "empty facts"
    if mode == "create":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(link, item_body, facts), encoding="utf-8")
        return 0, f"wrote {path}"
    current = path.read_text(encoding="utf-8")
    if mode == "append-facts":
        updated = _append_facts(current, facts)
        if updated is None:
            return 0, f"kept {path}"
    else:
        updated = _append_minutes(current, facts)
        if updated is None:
            return 0, f"kept {path}"
    if updated == current:
        return 0, f"kept {path}"
    path.write_text(updated, encoding="utf-8")
    return 0, f"wrote {path}"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("quarter")
    parser.add_argument("--title", required=True)
    parser.add_argument("--date")
    parser.add_argument("--append-facts", action="store_true")
    parser.add_argument("--append-minutes", action="store_true")
    args = parser.parse_args(argv)
    if args.append_facts and args.append_minutes:
        return 1
    mode = "append-facts" if args.append_facts else "append-minutes" if args.append_minutes else "create"
    quarter = Path(args.quarter)
    facts = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
    code, message = write_record(
        quarter.read_text(encoding="utf-8"),
        quarter.stem,
        args.title,
        facts,
        args.date,
        mode,
        Path(__file__).resolve().parent.parent,
    )
    print(message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts && python -m pytest tests/test_write_quarterly_record.py tests/test_export_quarterly_raw.py -q`

Expected: PASS. 내보내기 테스트는 기록이 있을 때 다시 만들지 않는 기존 동작을 유지한다.

- [ ] **Step 5: Commit**

```bash
git add scripts/write_quarterly_record.py scripts/tests/test_write_quarterly_record.py
git commit -m "feat: write a quarter record without replacing an existing one"
```

---

### Task 5: 요약 스킬에 기록 명령 연결

**Files:**
- Modify: `.claude/skills/quality-updates-writer/SKILL.md` (Phase 0 표 다음, Phase 1 상태 표 다음, REFERENCE D 끝)
- Test: `scripts/tests/test_writer_skill_record.py`

**Interfaces:**
- Consumes: `python scripts/write_quarterly_record.py <분기.md> --title <제목>`, `--append-facts`, `--append-minutes`
- Produces: 스킬 문서 안의 그 명령 문구. 코드 함수는 추가하지 않는다.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_writer_skill_record.py`를 만든다.

```python
from pathlib import Path


def test_summarize_skill_calls_the_record_writer():
    skill = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "quality-updates-writer" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    assert "python scripts/write_quarterly_record.py" in text
    assert "--append-facts" in text
    assert "--append-minutes" in text
    assert "data/quarterly-processed/" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_writer_skill_record.py -q`

Expected: FAIL because `write_quarterly_record.py` is absent from the skill

- [ ] **Step 3: Write minimal implementation**

Phase 0의 우선순위 표 바로 아래에 다음을 넣는다.

```markdown
처리 기록 파일이 `data/quarterly-processed/{분기 stem}/{YY-MM-DD}-{제목}.md`에 있으면 그 파일을 읽고 노트를 쓴다. 노트에 필요한 사실이 기록에 없을 때만 해당 PDF를 연다. 새로 확인한 사실은 표준 입력으로 `python scripts/write_quarterly_record.py <분기.md> --title <제목> --append-facts`에 넘긴다. `pdf_extracted.txt` 전문은 넘기지 않는다.
```

Phase 1 상태 표 바로 아래에 다음을 넣는다.

```markdown
노트를 쓴 뒤 처리 기록이 없고 항목이 `skip`, `no_summary`가 아니면 `python scripts/write_quarterly_record.py <분기.md> --title <제목>`을 호출한다. 표준 입력은 원문에서 확인한 사실이며, 사이트 노트에 넣지 않은 사실도 포함한다. `data/quarterly-processed/` 파일은 직접 편집하지 않는다. `위원 논의`를 의사록으로 채운 뒤에는 `python scripts/write_quarterly_record.py <분기.md> --title <제목> --append-minutes`를 호출한다.
```

REFERENCE D의 위원 논의 문단 끝에 다음 문장을 붙인다.

```markdown
처리 기록이 있으면 그 기록의 `## 위원 논의`로 이 노트를 쓴다. 기록 파일은 `write_quarterly_record.py`로만 고친다.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts && python -m pytest tests/test_writer_skill_record.py tests/ -q`

Expected: PASS. 전체 테스트가 통과한다.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/quality-updates-writer/SKILL.md scripts/tests/test_writer_skill_record.py
git commit -m "docs: tell the summary skill to store processed records"
```

---

## 운영 (이 계획의 커밋 밖)

다섯 작업이 `main`에 반영된 뒤, 2026년 3분기 작업본에 `python scripts/attach_sanction_minutes.py <분기.md>`를 한 번 실행할 수 있다. 그 실행은 미공개 항목에 PDF 마커만 추가한다. 결과 파일은 이 계획의 커밋에 넣지 않는다.
