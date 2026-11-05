# KASB 질의회신 아카이브 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 질의회신 요약 전체 게시판을 `data/kasb-replies/{seq}/` 항목 폴더로 저장하고, `item.md`만 옵시디안 `raw/kasb-replies/`로 복사한다.

**Architecture:** 파서·추출·저장은 `scripts/crawler/kasb_replies.py` 한 모듈이다. 수집 CLI와 복사 CLI는 그 함수만 호출한다. 테스트는 fixture HTML과 작은 파일이며 `kasb.or.kr`을 호출하지 않는다. 분기 크롤러와 MkDocs 본문에는 질의회신 항목을 넣지 않는다.

**Tech Stack:** Python 3, pytest, BeautifulSoup4, PyYAML, requests, pypdf, openpyxl, olefile

**Spec:** `docs/superpowers/specs/2026-11-04-kasb-reply-archive-design.md`

## Global Constraints

- 아카이브 경로는 `data/kasb-replies/{seq}/item.md`와 원본 첨부. `seq`는 `fn_Detail`의 첫 인자. gitignore하지 않는다.
- 목록 URL은 `https://www.kasb.or.kr/front/board/allReplySummaryList.do`. POST body는 `siteCd=002000000000000`, `searchfield=ALL`, `searchword=""`, `page`. 분류 필터는 없다. 세션은 GET 1회 후 POST.
- 상세 URL은 `https://www.kasb.or.kr/front/board/View{ctgCd}.do`. POST 필드는 `seq`, `ctgCd`.
- 다운로드 URL은 `https://www.kasb.or.kr/commonFile/fileDownload.do`. POST 필드는 `fileNo`, `fileSeq`. 편집기 모듈은 import하지 않는다.
- 마지막 페이지는 `li.pag_last a`의 `G_MovePage(N)`. 공지 행을 포함한다. 같은 `seq`는 처음 것만 남긴다.
- `item.md`는 UTF-8 YAML 프론트매터와 `## 상세 안내`, `## 첨부: {파일명}` 본문. 항목 상태는 `ok`, `partial`, `failed`, `empty`.
- pdf·hwpx·xlsx는 글이 있으면 `ok`, 없으면 `empty`. hwp `PrvText`가 있으면 `partial`, 없거나 깨지면 `failed`. 그 외 확장자는 `failed`. 한글 프로그램과 LibreOffice는 호출하지 않는다.
- 기본 실행은 `item.md`가 있고, 첨부가 모두 있고, `extract_status`가 `ok`인 항목을 건너뛴다. `--retry-failed`는 `failed`, `partial`, `empty`만 다시 시도한다. `ok`이고 파일이 있는 항목은 다시 받지 않는다.
- `--delay` 기본값 `0.2`. `--limit`는 이번에 시도하는 항목 수이고, 건너뛴 항목은 세지 않는다.
- 상세·다운로드가 실패하면 `item.md`를 만들지 않는다. manifest에는 실패 한 줄을 추가한다.
- 복사 기본 경로는 `C:\dev\obsidian-vault\raw\kasb-replies`. `{seq}.md`가 있으면 덮어쓰지 않는다. 첨부 파일은 복사하지 않는다.
- `scripts/crawler/KASB.py`, `unified.py`, `scripts/crawl.py`, 분기 문서, MCP 코퍼스는 수정하지 않는다.
- CI와 단위 테스트는 `kasb.or.kr`을 호출하지 않는다. 게시판 전체 수집은 이 계획의 완료 조건이 아니다.
- 사이트 문장: `회계기준원(KASB) 질의회신 원문은 이 사이트에 게시하지 않는다. 유관기관 보도자료 확장은 추가 예정.`

---

## File map

| File | Responsibility |
|------|----------------|
| `scripts/crawler/kasb_replies.py` | 목록·상세 파서, 추출, `item.md`, manifest, 크롤, HTTP, 복사 |
| `scripts/crawl_kasb_replies.py` | 수집 CLI |
| `scripts/export_kasb_replies_raw.py` | `item.md` 복사 CLI |
| `scripts/tests/test_kasb_replies.py` | 네트워크 없는 단위 테스트 |
| `requirements.txt` | `pypdf`, `openpyxl`, `olefile` 추가 |
| `docs/index.md` | 질의회신 사이트 게시 약속 삭제 |

`docs/superpowers/README.md`의 스펙·플랜 색인과 스펙 상태 `승인됨 (2026-11-04)`는 이미 반영되어 있다. 되돌리지 않는다.

---

### Task 1: 목록 파서

**Files:**

- Create: `scripts/tests/test_kasb_replies.py`
- Create: `scripts/crawler/kasb_replies.py`
- Test: `scripts/tests/test_kasb_replies.py`

**Interfaces:**

- Consumes: 없음
- Produces: `AttachmentRef(name, file_no, file_seq)`, `ListRow(seq, ctg_cd, number, category, title, reply_date, published_date, attachments)`, `parse_list_page(html) -> list[ListRow]`, `last_page_number(html) -> int`, `dedupe_rows(rows) -> list[ListRow]`, `parse_date(value) -> str | None`

- [ ] **Step 1: Write the failing test**

Create `scripts/tests/test_kasb_replies.py`:

```python
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler import kasb_replies

LIST_HTML = """
<table>
<tbody>
<tr>
  <td>공지</td><td></td>
  <td><a onclick="javascript:fn_Detail('40533','016009');">비교표</a></td>
  <td><a onclick="javascript:fileDownload('-49990797','1'); return false;">compare.xlsx</a></td>
  <td></td><td></td>
</tr>
<tr>
  <td>2193</td><td>정착지원TF</td>
  <td><a onclick="javascript:fn_Detail('40689','016008');">제1118호 정착지원 TF 논의 내용(5차)</a></td>
  <td><a onclick="javascript:fileDownload('-49993299','1'); return false;">261016_note.hwpx</a></td>
  <td>2026-10-16</td><td></td>
</tr>
<tr>
  <td>1</td><td>없음</td><td><span>링크 없음</span></td><td></td><td></td><td></td>
</tr>
</tbody>
</table>
<div class="paging_wrap">
  <li class="pag_last"><a href="javascript:G_MovePage(220);">Last</a></li>
</div>
"""


def test_parse_list_page_reads_notice_and_item():
    rows = kasb_replies.parse_list_page(LIST_HTML)
    assert len(rows) == 2
    notice, item = rows
    assert notice.seq == "40533"
    assert notice.ctg_cd == "016009"
    assert notice.number == "공지"
    assert notice.reply_date is None
    assert notice.attachments[0].file_no == "-49990797"
    assert notice.attachments[0].name == "compare.xlsx"
    assert item.seq == "40689"
    assert item.ctg_cd == "016008"
    assert item.number == "2193"
    assert item.category == "정착지원TF"
    assert item.title == "제1118호 정착지원 TF 논의 내용(5차)"
    assert item.reply_date == "2026-10-16"
    assert item.published_date is None
    assert item.attachments[0].file_seq == "1"


def test_last_page_number_and_default():
    assert kasb_replies.last_page_number(LIST_HTML) == 220
    assert kasb_replies.last_page_number("<table></table>") == 1


def test_dedupe_rows_keeps_first_seq():
    rows = kasb_replies.parse_list_page(LIST_HTML)
    merged = kasb_replies.dedupe_rows(rows + rows)
    assert [row.seq for row in merged] == ["40533", "40689"]
```

- [ ] **Step 2: Run test to verify it fails**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py::test_parse_list_page_reads_notice_and_item -q`

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `kasb_replies`

- [ ] **Step 3: Write minimal implementation**

Create `scripts/crawler/kasb_replies.py`:

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup

_DETAIL_RE = re.compile(r"fn_Detail\s*\(\s*'(\d+)'\s*,\s*'(\d+)'\s*\)")
_FILE_RE = re.compile(r"fileDownload\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")
_PAGE_RE = re.compile(r"G_MovePage\((\d+)\)")


@dataclass(frozen=True)
class AttachmentRef:
    name: str
    file_no: str
    file_seq: str


@dataclass(frozen=True)
class ListRow:
    seq: str
    ctg_cd: str
    number: str
    category: str
    title: str
    reply_date: str | None
    published_date: str | None
    attachments: tuple[AttachmentRef, ...]


def parse_date(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _attachments_in(node) -> list[AttachmentRef]:
    found = []
    for link in node.find_all("a"):
        match = _FILE_RE.search(link.get("onclick") or "")
        if not match:
            continue
        name = link.get_text(strip=True) or f"file-{match.group(2)}"
        found.append(AttachmentRef(name=name, file_no=match.group(1), file_seq=match.group(2)))
    return found


def parse_list_page(html: str) -> list[ListRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        cells = tr.find_all("td")
        if len(cells) < 6:
            continue
        title_link = None
        detail = None
        for link in cells[2].find_all("a"):
            detail = _DETAIL_RE.search(link.get("onclick") or "")
            if detail:
                title_link = link
                break
        if not detail or title_link is None:
            continue
        rows.append(
            ListRow(
                seq=detail.group(1),
                ctg_cd=detail.group(2),
                number=cells[0].get_text(strip=True),
                category=cells[1].get_text(strip=True),
                title=title_link.get_text(strip=True),
                reply_date=parse_date(cells[4].get_text(strip=True)),
                published_date=parse_date(cells[5].get_text(strip=True)),
                attachments=tuple(_attachments_in(cells[3])),
            )
        )
    return rows


def last_page_number(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("li.pag_last a")
    if node is None:
        return 1
    match = _PAGE_RE.search(node.get("href") or "")
    return int(match.group(1)) if match else 1


def dedupe_rows(rows: list[ListRow]) -> list[ListRow]:
    seen: set[str] = set()
    kept = []
    for row in rows:
        if row.seq in seen:
            continue
        seen.add(row.seq)
        kept.append(row)
    return kept
```

- [ ] **Step 4: Run test to verify it passes**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py -q`

Expected: PASS, 3 tests

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test_kasb_replies.py scripts/crawler/kasb_replies.py
git commit -m "$(cat <<'EOF'
feat: parse KASB reply list pages

EOF
)"
```

---

### Task 2: 상세 파서

**Files:**

- Modify: `scripts/crawler/kasb_replies.py`
- Modify: `scripts/tests/test_kasb_replies.py`
- Test: `scripts/tests/test_kasb_replies.py`

**Interfaces:**

- Consumes: `AttachmentRef`, `parse_date`, `_attachments_in`
- Produces: `DetailPage(category, standards, registered_date, notice, attachments)`, `parse_detail_page(html) -> DetailPage`

- [ ] **Step 1: Write the failing test**

Append to `scripts/tests/test_kasb_replies.py`:

```python
DETAIL_HTML = """
<nav>주메뉴로 가기</nav>
<div class="board_view_wrap">
  <table>
    <tr><th>분류</th><td class="left">정착지원TF</td></tr>
    <tr>
      <th>관련기준서</th>
      <td>
        <table>
          <tr><th>기준서 구분</th><td>제1118호 재무제표 표시와 공시</td></tr>
          <tr><th>기준서 명</th><td></td></tr>
        </table>
      </td>
    </tr>
    <tr><th>등록일</th><td><p class="board_date">2026-10-16</p></td></tr>
    <tr>
      <th>첨부파일</th>
      <td>
        <a onclick="javascript:fileDownload('-49993299','1'); return false;"><span>261016_note.hwpx</span></a>
        <a onclick="javascript:fn_fileViewer('abc');">미리보기</a>
      </td>
    </tr>
  </table>
  <div class="board_view_cont"><p>※ 본 자료는 참고 목적으로 정리한 것입니다.</p></div>
</div>
"""


def test_parse_detail_page_reads_standards_and_notice():
    detail = kasb_replies.parse_detail_page(DETAIL_HTML)
    assert detail.category == "정착지원TF"
    assert detail.standards == ("제1118호 재무제표 표시와 공시",)
    assert detail.registered_date == "2026-10-16"
    assert detail.notice == "※ 본 자료는 참고 목적으로 정리한 것입니다."
    assert "주메뉴로 가기" not in detail.notice
    assert len(detail.attachments) == 1
    assert detail.attachments[0].name == "261016_note.hwpx"
    assert detail.attachments[0].file_no == "-49993299"
```

- [ ] **Step 2: Run test to verify it fails**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py::test_parse_detail_page_reads_standards_and_notice -q`

Expected: FAIL with `AttributeError: module 'crawler.kasb_replies' has no attribute 'parse_detail_page'`

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/crawler/kasb_replies.py`:

```python
@dataclass(frozen=True)
class DetailPage:
    category: str | None
    standards: tuple[str, ...]
    registered_date: str | None
    notice: str
    attachments: tuple[AttachmentRef, ...]


def _labeled_text(wrap, label: str) -> str:
    for th in wrap.find_all("th"):
        if th.get_text(strip=True) == label:
            td = th.find_next("td")
            return td.get_text(" ", strip=True) if td else ""
    return ""


def parse_detail_page(html: str) -> DetailPage:
    soup = BeautifulSoup(html, "html.parser")
    wrap = soup.select_one(".board_view_wrap") or soup
    category = _labeled_text(wrap, "분류") or None
    standards: list[str] = []
    for th in wrap.find_all("th"):
        if th.get_text(strip=True) != "관련기준서":
            continue
        td = th.find_next("td")
        if td is not None:
            for inner in td.find_all("td"):
                text = inner.get_text(" ", strip=True)
                if text:
                    standards.append(text)
        break
    notice_node = wrap.select_one(".board_view_cont")
    notice = notice_node.get_text(" ", strip=True) if notice_node else ""
    return DetailPage(
        category=category,
        standards=tuple(standards),
        registered_date=parse_date(_labeled_text(wrap, "등록일")),
        notice=notice,
        attachments=tuple(_attachments_in(wrap)),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py -q`

Expected: PASS, 4 tests

- [ ] **Step 5: Commit**

```bash
git add scripts/crawler/kasb_replies.py scripts/tests/test_kasb_replies.py
git commit -m "$(cat <<'EOF'
feat: parse KASB reply detail pages

EOF
)"
```

---

### Task 3: 첨부 추출과 상태 집계

**Files:**

- Modify: `requirements.txt`
- Modify: `scripts/crawler/kasb_replies.py`
- Modify: `scripts/tests/test_kasb_replies.py`
- Test: `scripts/tests/test_kasb_replies.py`

**Interfaces:**

- Consumes: 없음 (바이트와 파일명만 받는다)
- Produces: `extract_bytes(filename: str, data: bytes) -> tuple[str, str]`, `aggregate_status(statuses: list[str]) -> str`. 두 번째 값은 `ok`, `empty`, `partial`, `failed` 중 하나.

- [ ] **Step 1: Add dependencies and install them**

Append these lines to `requirements.txt`:

```text
pypdf
openpyxl
olefile
```

Run: `python -m pip install pypdf openpyxl olefile`

Expected: the three packages import.

- [ ] **Step 2: Write the failing test**

Append to `scripts/tests/test_kasb_replies.py`:

```python
import io
import struct
import zipfile

import pytest


def _hello_pdf() -> bytes:
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 55>>stream
BT /F1 12 Tf 20 100 Td (Hello Reply) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000052 00000 n 
0000000101 00000 n 
0000000208 00000 n 
0000000313 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
382
%%EOF
"""


def _empty_pdf() -> bytes:
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R>>endobj
4 0 obj<</Length 0>>stream
endstream
endobj
trailer<</Size 5/Root 1 0 R>>
startxref
230
%%EOF
"""


def _hwpx(inner: str) -> bytes:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        f"<hp:p><hp:run><hp:t>{inner}</hp:t></hp:run></hp:p></hs:sec>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Contents/header.xml", "<hp:t>헤더</hp:t>")
        zf.writestr("Contents/section0.xml", xml)
    return buf.getvalue()


def _xlsx() -> bytes:
    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.title = "비교"
    sheet.append(["항목", "값"])
    sheet.append(["면제", "a|b"])
    buf = io.BytesIO()
    book.save(buf)
    return buf.getvalue()


def _empty_xlsx() -> bytes:
    from openpyxl import Workbook

    book = Workbook()
    buf = io.BytesIO()
    book.save(buf)
    return buf.getvalue()


def _ole_dir(name: str, typ: int, child: int, start: int, size: int) -> bytes:
    raw = name.encode("utf-16-le")
    buf = bytearray(128)
    buf[0 : len(raw)] = raw
    struct.pack_into("<H", buf, 0x40, len(raw) + 2)
    buf[0x42] = typ
    buf[0x43] = 1
    struct.pack_into("<III", buf, 0x44, 0xFFFFFFFF, 0xFFFFFFFF, child)
    struct.pack_into("<I", buf, 0x74, start)
    struct.pack_into("<I", buf, 0x78, size)
    return bytes(buf)


def _ole_with_prvtext(text: str) -> bytes:
    data = text.encode("utf-16-le")
    if len(data) > 64:
        raise ValueError("fixture text must fit in one mini sector")
    directory = _ole_dir("Root Entry", 5, 1, 3, 64) + _ole_dir("PrvText", 2, 0xFFFFFFFF, 0, len(data))
    directory += bytes(256)
    fat = struct.pack("<IIII", 0xFFFFFFFD, 0xFFFFFFFE, 0xFFFFFFFE, 0xFFFFFFFE) + (b"\xff" * 4) * 124
    minifat = struct.pack("<I", 0xFFFFFFFE) + (b"\xff" * 4) * 127
    header = bytearray(512)
    header[0:8] = bytes.fromhex("D0CF11E0A1B11AE1")
    struct.pack_into("<H", header, 0x18, 0x003E)
    struct.pack_into("<H", header, 0x1A, 3)
    struct.pack_into("<H", header, 0x1C, 0xFFFE)
    struct.pack_into("<H", header, 0x1E, 9)
    struct.pack_into("<H", header, 0x20, 6)
    struct.pack_into("<I", header, 0x2C, 1)
    struct.pack_into("<I", header, 0x30, 1)
    struct.pack_into("<I", header, 0x38, 0x1000)
    struct.pack_into("<I", header, 0x3C, 2)
    struct.pack_into("<I", header, 0x40, 1)
    struct.pack_into("<I", header, 0x44, 0xFFFFFFFE)
    struct.pack_into("<I", header, 0x48, 0)
    struct.pack_into("<I", header, 0x4C, 0)
    mini = data + b"\x00" * (512 - len(data))
    return bytes(header) + fat + directory + minifat + mini


def test_extract_pdf_hwpx_and_xlsx():
    text, status = kasb_replies.extract_bytes("a.pdf", _hello_pdf())
    assert status == "ok"
    assert "Hello Reply" in text
    text, status = kasb_replies.extract_bytes("empty.pdf", _empty_pdf())
    assert status == "empty"
    text, status = kasb_replies.extract_bytes("a.hwpx", _hwpx("회신 문장"))
    assert status == "ok"
    assert "회신 문장" in text
    assert "헤더" not in text
    text, status = kasb_replies.extract_bytes("a.xlsx", _xlsx())
    assert status == "ok"
    assert "### 비교" in text
    assert "a\\|b" in text
    text, status = kasb_replies.extract_bytes("empty.xlsx", _empty_xlsx())
    assert status == "empty"


def test_extract_hwp_preview_and_garbage():
    text, status = kasb_replies.extract_bytes("a.hwp", _ole_with_prvtext("회신결론"))
    assert status == "partial"
    assert "회신결론" in text
    text, status = kasb_replies.extract_bytes("a.hwp", b"not-ole")
    assert status == "failed"
    text, status = kasb_replies.extract_bytes("a.zip", b"PK")
    assert status == "failed"


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([], "empty"),
        (["ok", "ok"], "ok"),
        (["partial", "ok"], "partial"),
        (["failed", "ok"], "failed"),
        (["empty", "empty"], "empty"),
        (["ok", "empty"], "partial"),
    ],
)
def test_aggregate_status(statuses, expected):
    assert kasb_replies.aggregate_status(statuses) == expected
```

- [ ] **Step 3: Run test to verify it fails**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py::test_extract_pdf_hwpx_and_xlsx -q`

Expected: FAIL with `AttributeError` for `extract_bytes`

- [ ] **Step 4: Write minimal implementation**

Append to `scripts/crawler/kasb_replies.py`:

```python
import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree


def _nonempty(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    return (cleaned, "ok" if cleaned else "empty")


def _extract_pdf(data: bytes) -> tuple[str, str]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return _nonempty("\n\n".join(parts))


def _extract_hwpx(data: bytes) -> tuple[str, str]:
    texts = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = sorted(
            name
            for name in zf.namelist()
            if name.startswith("Contents/section") and name.endswith(".xml")
        )
        for name in names:
            root = ElementTree.fromstring(zf.read(name))
            for el in root.iter():
                if el.tag.split("}")[-1] == "t" and el.text:
                    texts.append(el.text)
    return _nonempty("\n".join(texts))


def _cell(value) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return text.replace("|", "\\|")


def _extract_xlsx(data: bytes) -> tuple[str, str]:
    from openpyxl import load_workbook

    book = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    chunks = []
    for sheet in book.worksheets:
        rows = []
        for row in sheet.iter_rows(values_only=True):
            if all(cell is None or str(cell).strip() == "" for cell in row):
                continue
            rows.append([_cell(cell) for cell in row])
        if not rows:
            continue
        width = max(len(row) for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]
        header = "| " + " | ".join(rows[0]) + " |"
        rule = "| " + " | ".join("---" for _ in rows[0]) + " |"
        body = ["| " + " | ".join(row) + " |" for row in rows[1:]]
        chunks.append("### " + sheet.title + "\n\n" + "\n".join([header, rule, *body]))
    return _nonempty("\n\n".join(chunks))


def _extract_hwp(data: bytes) -> tuple[str, str]:
    import olefile

    try:
        ole = olefile.OleFileIO(io.BytesIO(data))
    except Exception as exc:
        return (str(exc), "failed")
    if not ole.exists("PrvText"):
        return ("PrvText missing", "failed")
    raw = ole.openstream("PrvText").read()
    text = raw.decode("utf-16-le", errors="replace").replace("\x00", "").strip()
    if not text:
        return ("empty preview", "failed")
    return (text, "partial")


def extract_bytes(filename: str, data: bytes) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            return _extract_pdf(data)
        if suffix == ".hwpx":
            return _extract_hwpx(data)
        if suffix == ".xlsx":
            return _extract_xlsx(data)
        if suffix == ".hwp":
            return _extract_hwp(data)
    except Exception as exc:
        return (str(exc), "failed")
    return ("unsupported", "failed")


def aggregate_status(statuses: list[str]) -> str:
    if not statuses:
        return "empty"
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "partial" for status in statuses):
        return "partial"
    if all(status == "empty" for status in statuses):
        return "empty"
    if any(status == "empty" for status in statuses):
        return "partial"
    if all(status == "ok" for status in statuses):
        return "ok"
    return "failed"
```

- [ ] **Step 5: Run test to verify it passes**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt scripts/crawler/kasb_replies.py scripts/tests/test_kasb_replies.py
git commit -m "$(cat <<'EOF'
feat: extract text from KASB reply attachments

EOF
)"
```

---

### Task 4: item.md, 완료 판정, manifest

**Files:**

- Modify: `scripts/crawler/kasb_replies.py`
- Modify: `scripts/tests/test_kasb_replies.py`
- Test: `scripts/tests/test_kasb_replies.py`

**Interfaces:**

- Consumes: `ListRow`, `DetailPage`, `AttachmentRef`, `aggregate_status`
- Produces: `attachment_filename(name, file_seq, used) -> str`, `compose_item(row, detail, sections, fetched_at) -> str`, `read_meta(directory) -> dict | None`, `should_attempt(directory, retry_failed) -> bool`, `append_manifest(path, record) -> None`. `sections`는 `(filename, text, status)` 튜플의 리스트.

- [ ] **Step 1: Write the failing test**

Append to `scripts/tests/test_kasb_replies.py`:

```python
import json

import yaml


def _sample_row():
    return kasb_replies.ListRow(
        seq="40689",
        ctg_cd="016008",
        number="2193",
        category="",
        title="제목",
        reply_date=None,
        published_date=None,
        attachments=(),
    )


def _sample_detail():
    return kasb_replies.DetailPage(
        category="정착지원TF",
        standards=("제1118호 재무제표 표시와 공시",),
        registered_date="2026-10-16",
        notice="",
        attachments=(kasb_replies.AttachmentRef("note.hwpx", "-49993299", "1"),),
    )


def test_attachment_filename_strips_directories_and_dedupes():
    used = set()
    assert kasb_replies.attachment_filename(r"..\a\note.hwpx", "1", used) == "note.hwpx"
    assert kasb_replies.attachment_filename("note.hwpx", "2", used) == "note-2.hwpx"


def test_compose_item_uses_detail_category_and_registered_date():
    text = kasb_replies.compose_item(
        _sample_row(),
        _sample_detail(),
        [("note.hwpx", "본문", "ok")],
        "2026-11-04T07:00:00+09:00",
    )
    meta, body = text.split("---", 2)[1:]
    loaded = yaml.safe_load(meta)
    assert loaded["seq"] == "40689"
    assert loaded["category"] == "정착지원TF"
    assert loaded["reply_date"] == "2026-10-16"
    assert loaded["published_date"] is None
    assert loaded["standards"] == ["제1118호 재무제표 표시와 공시"]
    assert loaded["extract_status"] == "ok"
    assert loaded["attachments"][0]["file_no"] == "-49993299"
    assert loaded["attachments"][0]["extract_status"] == "ok"
    assert "## 상세 안내" in body
    assert "(없음)" in body
    assert "## 첨부: note.hwpx" in body
    assert "본문" in body


def test_compose_item_writes_failed_attachment_line():
    text = kasb_replies.compose_item(
        _sample_row(),
        _sample_detail(),
        [("note.hwp", "PrvText missing", "failed")],
        "2026-11-04T07:00:00+09:00",
    )
    assert "failed: PrvText missing" in text
    assert yaml.safe_load(text.split("---", 2)[1])["extract_status"] == "failed"


def test_should_attempt_and_manifest(tmp_path):
    directory = tmp_path / "40689"
    directory.mkdir()
    assert kasb_replies.should_attempt(directory, retry_failed=False) is True
    (directory / "note.hwpx").write_bytes(b"x")
    item = kasb_replies.compose_item(
        _sample_row(),
        _sample_detail(),
        [("note.hwpx", "본문", "ok")],
        "2026-11-04T07:00:00+09:00",
    )
    (directory / "item.md").write_text(item, encoding="utf-8")
    assert kasb_replies.should_attempt(directory, retry_failed=True) is False
    (directory / "note.hwpx").unlink()
    assert kasb_replies.should_attempt(directory, retry_failed=False) is True
    partial = kasb_replies.compose_item(
        _sample_row(),
        _sample_detail(),
        [("note.hwpx", "미리보기", "partial")],
        "2026-11-04T07:00:00+09:00",
    )
    (directory / "item.md").write_text(partial, encoding="utf-8")
    (directory / "note.hwpx").write_bytes(b"x")
    assert kasb_replies.should_attempt(directory, retry_failed=False) is False
    assert kasb_replies.should_attempt(directory, retry_failed=True) is True
    manifest = tmp_path / "manifest.jsonl"
    kasb_replies.append_manifest(
        manifest,
        {
            "seq": "40689",
            "ctg_cd": "016008",
            "number": "2193",
            "category": "정착지원TF",
            "title": "제목",
            "reply_date": "2026-10-16",
            "published_date": None,
            "extract_status": "ok",
            "path": "40689/item.md",
            "error": None,
        },
    )
    record = json.loads(manifest.read_text(encoding="utf-8").splitlines()[-1])
    assert record["path"] == "40689/item.md"
    assert record["error"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py::test_compose_item_uses_detail_category_and_registered_date -q`

Expected: FAIL with `AttributeError` for `compose_item`

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/crawler/kasb_replies.py`:

```python
import json

import yaml


def attachment_filename(name: str, file_seq: str, used: set[str]) -> str:
    cleaned = Path(name.replace("\\", "/")).name.strip() or f"attachment-{file_seq}"
    cleaned = cleaned.replace("\x00", "")
    if cleaned not in used:
        used.add(cleaned)
        return cleaned
    stem = Path(cleaned).stem
    suffix = Path(cleaned).suffix
    candidate = f"{stem}-{file_seq}{suffix}"
    number = 2
    while candidate in used:
        candidate = f"{stem}-{file_seq}-{number}{suffix}"
        number += 1
    used.add(candidate)
    return candidate


def compose_item(row: ListRow, detail: DetailPage, sections: list[tuple[str, str, str]], fetched_at: str) -> str:
    category = detail.category or row.category
    reply_date = row.reply_date or detail.registered_date
    source = detail.attachments or row.attachments
    names = []
    used: set[str] = set()
    for ref in source:
        names.append(attachment_filename(ref.name, ref.file_seq, used))
    by_saved = {filename: (text, status) for filename, text, status in sections}
    attachments = []
    body_sections = []
    for ref, filename in zip(source, names):
        text, status = by_saved.get(filename, ("missing extract", "failed"))
        attachments.append(
            {
                "name": filename,
                "file_no": ref.file_no,
                "file_seq": ref.file_seq,
                "extract_status": status,
            }
        )
        body_sections.append((filename, text, status))
    meta = {
        "seq": row.seq,
        "ctg_cd": row.ctg_cd,
        "number": row.number,
        "category": category,
        "title": row.title,
        "standards": list(detail.standards),
        "reply_date": reply_date,
        "published_date": row.published_date,
        "attachments": attachments,
        "fetched_at": fetched_at,
        "extract_status": aggregate_status([item["extract_status"] for item in attachments]),
    }
    dumped = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    lines = ["---", dumped, "---", "", "## 상세 안내", "", detail.notice.strip() or "(없음)", ""]
    for filename, text, status in body_sections:
        lines.extend([f"## 첨부: {filename}", ""])
        if status in {"ok", "partial"} and text.strip():
            lines.extend([text.rstrip(), ""])
        else:
            lines.extend([f"{status}: {text.strip() or status}", ""])
    return "\n".join(lines).rstrip() + "\n"


def read_meta(directory: Path) -> dict | None:
    item = directory / "item.md"
    if not item.is_file():
        return None
    text = item.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return meta if isinstance(meta, dict) else None


def should_attempt(directory: Path, retry_failed: bool) -> bool:
    meta = read_meta(directory)
    if meta is None:
        return True
    status = meta.get("extract_status")
    files_ok = all((directory / item["name"]).is_file() for item in meta.get("attachments") or [])
    if status == "ok" and files_ok:
        return False
    if status == "ok" and not files_ok:
        return True
    if not files_ok:
        return True
    return retry_failed and status in {"failed", "partial", "empty"}


def append_manifest(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
```

`Path` is already imported in Task 3. Do not import it again.

- [ ] **Step 4: Run test to verify it passes**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/crawler/kasb_replies.py scripts/tests/test_kasb_replies.py
git commit -m "$(cat <<'EOF'
feat: write KASB reply item markdown and manifest lines

EOF
)"
```

---

### Task 5: 크롤 오케스트레이션

**Files:**

- Modify: `scripts/crawler/kasb_replies.py`
- Modify: `scripts/tests/test_kasb_replies.py`
- Test: `scripts/tests/test_kasb_replies.py`

**Interfaces:**

- Consumes: `parse_list_page`, `last_page_number`, `dedupe_rows`는 페이지를 합친 뒤가 아니라 페이지를 돌며 seen으로 대체한다. `parse_detail_page`, `extract_bytes`, `compose_item`, `should_attempt`, `append_manifest`, `attachment_filename`
- Produces: `crawl_archive(archive, *, fetch_list, fetch_detail, fetch_file, delay=0.2, limit=None, retry_failed=False, sleep=time.sleep, now=None) -> dict`. 키는 `saved`, `skipped`, `failed`. `fetch_list(page) -> str`, `fetch_detail(seq, ctg_cd) -> str`, `fetch_file(file_no, file_seq) -> bytes`.

- [ ] **Step 1: Write the failing test**

Append to `scripts/tests/test_kasb_replies.py`:

```python
from datetime import datetime, timedelta, timezone


def _crawl_pages():
    page1 = """
    <table><tbody>
    <tr>
      <td>공지</td><td></td>
      <td><a onclick="javascript:fn_Detail('40533','016009');">비교표</a></td>
      <td><a onclick="fileDownload('-1','1'); return false;">compare.xlsx</a></td>
      <td></td><td></td>
    </tr>
    <tr>
      <td>2193</td><td>정착지원TF</td>
      <td><a onclick="javascript:fn_Detail('40689','016008');">제목</a></td>
      <td><a onclick="fileDownload('-49993299','1'); return false;">note.hwpx</a></td>
      <td>2026-10-16</td><td></td>
    </tr>
    </tbody></table>
    <li class="pag_last"><a href="javascript:G_MovePage(2);">Last</a></li>
    """
    page2 = """
    <table><tbody>
    <tr>
      <td>공지</td><td></td>
      <td><a onclick="javascript:fn_Detail('40533','016009');">비교표</a></td>
      <td><a onclick="fileDownload('-1','1'); return false;">compare.xlsx</a></td>
      <td></td><td></td>
    </tr>
    <tr>
      <td>2192</td><td>정착지원TF</td>
      <td><a onclick="javascript:fn_Detail('40690','016008');">다음</a></td>
      <td><a onclick="fileDownload('-2','1'); return false;">next.hwpx</a></td>
      <td>2026-08-18</td><td>2026-09-30</td>
    </tr>
    </tbody></table>
    <li class="pag_last"><a href="javascript:G_MovePage(2);">Last</a></li>
    """
    return {1: page1, 2: page2}


def test_crawl_archive_saves_once_and_skips_complete(tmp_path):
    pages = _crawl_pages()
    details = []
    slept = []

    def fetch_list(page):
        return pages[page]

    def fetch_detail(seq, ctg_cd):
        details.append(seq)
        return DETAIL_HTML.replace("40689", seq)

    def fetch_file(file_no, file_seq):
        return _hwpx("본문")

    def sleep(seconds):
        slept.append(seconds)

    moment = datetime(2026, 11, 4, 7, 0, tzinfo=timezone(timedelta(hours=9)))
    result = kasb_replies.crawl_archive(
        tmp_path,
        fetch_list=fetch_list,
        fetch_detail=fetch_detail,
        fetch_file=fetch_file,
        delay=0.2,
        sleep=sleep,
        now=lambda: moment,
    )
    assert result == {"saved": 3, "skipped": 0, "failed": 0}
    assert details == ["40533", "40689", "40690"]
    item = (tmp_path / "40689" / "item.md").read_text(encoding="utf-8")
    assert "fetched_at: '2026-11-04T07:00:00+09:00'" in item or "2026-11-04T07:00:00+09:00" in item
    assert (tmp_path / "40689" / "261016_note.hwpx").is_file()
    saved_next = yaml.safe_load((tmp_path / "40690" / "item.md").read_text(encoding="utf-8").split("---", 2)[1])
    assert saved_next["published_date"] == "2026-09-30"
    again = kasb_replies.crawl_archive(
        tmp_path,
        fetch_list=fetch_list,
        fetch_detail=fetch_detail,
        fetch_file=fetch_file,
        delay=0,
        sleep=lambda seconds: None,
        now=lambda: moment,
    )
    assert again["skipped"] == 3
    assert again["saved"] == 0
    assert len(slept) == 7


def test_crawl_archive_limit_and_download_failure(tmp_path):
    pages = _crawl_pages()

    def fetch_list(page):
        return pages[page]

    def fetch_detail(seq, ctg_cd):
        if seq == "40689":
            raise RuntimeError("detail down")
        return DETAIL_HTML

    def fetch_file(file_no, file_seq):
        return _hwpx("본문")

    result = kasb_replies.crawl_archive(
        tmp_path,
        fetch_list=fetch_list,
        fetch_detail=fetch_detail,
        fetch_file=fetch_file,
        delay=0,
        limit=2,
        sleep=lambda seconds: None,
    )
    assert result["saved"] == 1
    assert result["failed"] == 1
    assert not (tmp_path / "40689" / "item.md").exists()
    assert (tmp_path / "40690").exists() is False
    lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert any(json.loads(line)["error"] == "detail down" for line in lines)
```

첫 목록 요청에는 `sleep`을 호출하지 않는다. 그 다음 HTTP마다 `sleep(delay)`를 호출한다. 이 테스트의 HTTP는 목록 2회, 상세 3회, 파일 3회라서 `sleep`은 7회다. `delay=0`이면 `sleep`을 호출하지 않는다.

- [ ] **Step 2: Run test to verify it fails**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py::test_crawl_archive_saves_once_and_skips_complete -q`

Expected: FAIL with `AttributeError` for `crawl_archive`

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/crawler/kasb_replies.py`:

```python
import time
from datetime import datetime, timezone


def crawl_archive(
    archive: Path,
    *,
    fetch_list,
    fetch_detail,
    fetch_file,
    delay: float = 0.2,
    limit: int | None = None,
    retry_failed: bool = False,
    sleep=time.sleep,
    now=None,
) -> dict[str, int]:
    archive.mkdir(parents=True, exist_ok=True)
    counts = {"saved": 0, "skipped": 0, "failed": 0}
    seen: set[str] = set()
    attempts = 0
    first_http = True

    def call(func, *args):
        nonlocal first_http
        if not first_http and delay:
            sleep(delay)
        first_http = False
        return func(*args)

    page = 1
    last_page = 1
    while page <= last_page:
        html = call(fetch_list, page)
        if page == 1:
            last_page = last_page_number(html)
        for row in parse_list_page(html):
            if row.seq in seen:
                continue
            seen.add(row.seq)
            directory = archive / row.seq
            if not should_attempt(directory, retry_failed):
                counts["skipped"] += 1
                continue
            if limit is not None and attempts >= limit:
                return counts
            attempts += 1
            try:
                detail = parse_detail_page(call(fetch_detail, row.seq, row.ctg_cd))
                refs = detail.attachments or row.attachments
                directory.mkdir(parents=True, exist_ok=True)
                used: set[str] = set()
                sections = []
                for ref in refs:
                    filename = attachment_filename(ref.name, ref.file_seq, used)
                    payload = call(fetch_file, ref.file_no, ref.file_seq)
                    (directory / filename).write_bytes(payload)
                    text, status = extract_bytes(filename, payload)
                    sections.append((filename, text, status))
                moment = now() if now else datetime.now(timezone.utc)
                if moment.tzinfo is None:
                    moment = moment.replace(tzinfo=timezone.utc)
                item = compose_item(row, detail, sections, moment.isoformat())
                (directory / "item.md").write_text(item, encoding="utf-8")
                meta = read_meta(directory) or {}
                append_manifest(
                    archive / "manifest.jsonl",
                    {
                        "seq": row.seq,
                        "ctg_cd": row.ctg_cd,
                        "number": row.number,
                        "category": meta.get("category", row.category),
                        "title": row.title,
                        "reply_date": meta.get("reply_date", row.reply_date),
                        "published_date": row.published_date,
                        "extract_status": meta.get("extract_status", "failed"),
                        "path": f"{row.seq}/item.md",
                        "error": None,
                    },
                )
                counts["saved"] += 1
            except Exception as exc:
                append_manifest(
                    archive / "manifest.jsonl",
                    {
                        "seq": row.seq,
                        "ctg_cd": row.ctg_cd,
                        "number": row.number,
                        "category": row.category,
                        "title": row.title,
                        "reply_date": row.reply_date,
                        "published_date": row.published_date,
                        "extract_status": "failed",
                        "path": None,
                        "error": str(exc),
                    },
                )
                counts["failed"] += 1
        page += 1
    return counts
```

상세 첨부가 있으면 목록 첨부 이름 대신 상세 이름을 쓴다. 이 테스트의 상세 파일명은 `261016_note.hwpx`다. 크롤과 `compose_item`은 같은 첨부 순서와 빈 `used`로 `attachment_filename`을 계산하므로 디스크 이름과 `item.md`의 첨부 이름이 같다.

- [ ] **Step 4: Run test to verify it passes**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py::test_crawl_archive_saves_once_and_skips_complete tests/test_kasb_replies.py::test_crawl_archive_limit_and_download_failure -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/crawler/kasb_replies.py scripts/tests/test_kasb_replies.py
git commit -m "$(cat <<'EOF'
feat: resume KASB reply archive crawls by seq

EOF
)"
```

---

### Task 6: HTTP 헬퍼와 CLI

**Files:**

- Modify: `scripts/crawler/kasb_replies.py`
- Create: `scripts/crawl_kasb_replies.py`
- Create: `scripts/export_kasb_replies_raw.py`
- Modify: `scripts/tests/test_kasb_replies.py`
- Test: `scripts/tests/test_kasb_replies.py`

**Interfaces:**

- Consumes: `crawl_archive`, `copy_archive_markdown` (이 태스크에서 추가), `LIST_URL`, `DOWNLOAD_URL`
- Produces: `make_session()`, `http_fetch_list(session, page) -> str`, `http_fetch_detail(session, seq, ctg_cd) -> str`, `http_fetch_file(session, file_no, file_seq) -> bytes`, `default_archive() -> Path`, `default_raw_dest() -> Path`, `copy_archive_markdown(archive, dest) -> tuple[int, int]`, `crawl_kasb_replies.parse_args`, `export_kasb_replies_raw.parse_args`

- [ ] **Step 1: Write the failing test**

Append to `scripts/tests/test_kasb_replies.py`:

```python
import crawl_kasb_replies
import export_kasb_replies_raw


class _Resp:
    def __init__(self, text="", content=b"", status=200):
        self.text = text
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


def test_http_helpers_post_the_spec_forms():
    calls = []

    class Session:
        def post(self, url, data, timeout):
            calls.append((url, data, timeout))
            return _Resp(text="ok", content=b"file")

    session = Session()
    assert kasb_replies.http_fetch_list(session, 3) == "ok"
    assert kasb_replies.http_fetch_detail(session, "40689", "016008") == "ok"
    assert kasb_replies.http_fetch_file(session, "-12", "1") == b"file"
    assert calls[0][0] == kasb_replies.LIST_URL
    assert calls[0][1]["siteCd"] == "002000000000000"
    assert calls[0][1]["searchfield"] == "ALL"
    assert calls[0][1]["searchword"] == ""
    assert calls[0][1]["page"] == 3
    assert calls[1][0] == "https://www.kasb.or.kr/front/board/View016008.do"
    assert calls[1][1] == {"seq": "40689", "ctgCd": "016008"}
    assert calls[2][0] == kasb_replies.DOWNLOAD_URL
    assert calls[2][1] == {"fileNo": "-12", "fileSeq": "1"}


def test_make_session_gets_list_once(monkeypatch):
    calls = []

    class Session:
        def __init__(self):
            self.headers = {}

        def get(self, url, timeout):
            calls.append(url)

    monkeypatch.setattr(kasb_replies.requests, "Session", Session)
    kasb_replies.make_session()
    assert calls == [kasb_replies.LIST_URL]


def test_copy_archive_markdown_skips_existing(tmp_path):
    archive = tmp_path / "archive"
    item = archive / "40689"
    item.mkdir(parents=True)
    (item / "item.md").write_text("hello", encoding="utf-8")
    (item / "note.hwpx").write_bytes(b"bin")
    dest = tmp_path / "raw"
    copied, skipped = kasb_replies.copy_archive_markdown(archive, dest)
    assert (copied, skipped) == (1, 0)
    assert (dest / "40689.md").read_text(encoding="utf-8") == "hello"
    assert not (dest / "note.hwpx").exists()
    copied, skipped = kasb_replies.copy_archive_markdown(archive, dest)
    assert (copied, skipped) == (0, 1)
    assert (dest / "40689.md").read_text(encoding="utf-8") == "hello"


def test_cli_defaults():
    crawl_args = crawl_kasb_replies.parse_args([])
    assert crawl_args.delay == 0.2
    assert crawl_args.limit is None
    assert crawl_args.retry_failed is False
    assert crawl_args.archive == kasb_replies.default_archive()
    export_args = export_kasb_replies_raw.parse_args([])
    assert export_args.dest == kasb_replies.default_raw_dest()
    assert str(export_args.dest).endswith(r"raw\kasb-replies") or str(export_args.dest).endswith("raw/kasb-replies")
```

- [ ] **Step 2: Run test to verify it fails**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py::test_http_helpers_post_the_spec_forms tests/test_kasb_replies.py::test_copy_archive_markdown_skips_existing -q`

Expected: FAIL with `AttributeError` for `http_fetch_list` or `copy_archive_markdown`

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/crawler/kasb_replies.py`:

```python
import requests

LIST_URL = "https://www.kasb.or.kr/front/board/allReplySummaryList.do"
DOWNLOAD_URL = "https://www.kasb.or.kr/commonFile/fileDownload.do"


def default_archive() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "kasb-replies"


def default_raw_dest() -> Path:
    return Path(r"C:\dev\obsidian-vault\raw\kasb-replies")


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    session.get(LIST_URL, timeout=30)
    return session


def _view_url(ctg_cd: str) -> str:
    return f"https://www.kasb.or.kr/front/board/View{ctg_cd}.do"


def http_fetch_list(session, page: int) -> str:
    response = session.post(
        LIST_URL,
        data={
            "siteCd": "002000000000000",
            "searchfield": "ALL",
            "searchword": "",
            "page": page,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def http_fetch_detail(session, seq: str, ctg_cd: str) -> str:
    response = session.post(_view_url(ctg_cd), data={"seq": seq, "ctgCd": ctg_cd}, timeout=30)
    response.raise_for_status()
    return response.text


def http_fetch_file(session, file_no: str, file_seq: str) -> bytes:
    response = session.post(
        DOWNLOAD_URL,
        data={"fileNo": file_no, "fileSeq": file_seq},
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def copy_archive_markdown(archive: Path, dest: Path) -> tuple[int, int]:
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0
    if not archive.is_dir():
        return copied, skipped
    for item in sorted(archive.glob("*/item.md")):
        target = dest / f"{item.parent.name}.md"
        if target.exists():
            skipped += 1
            continue
        target.write_bytes(item.read_bytes())
        copied += 1
    return copied, skipped
```

Create `scripts/crawl_kasb_replies.py`:

```python
# -*- coding: utf-8 -*-
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crawler import kasb_replies


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=kasb_replies.default_archive())
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--retry-failed", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    session = kasb_replies.make_session()
    result = kasb_replies.crawl_archive(
        args.archive,
        fetch_list=lambda page: kasb_replies.http_fetch_list(session, page),
        fetch_detail=lambda seq, ctg_cd: kasb_replies.http_fetch_detail(session, seq, ctg_cd),
        fetch_file=lambda file_no, file_seq: kasb_replies.http_fetch_file(session, file_no, file_seq),
        delay=args.delay,
        limit=args.limit,
        retry_failed=args.retry_failed,
    )
    print(f"saved={result['saved']} skipped={result['skipped']} failed={result['failed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `scripts/export_kasb_replies_raw.py`:

```python
# -*- coding: utf-8 -*-
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crawler import kasb_replies


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=kasb_replies.default_archive())
    parser.add_argument("--dest", type=Path, default=kasb_replies.default_raw_dest())
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    copied, skipped = kasb_replies.copy_archive_markdown(args.archive, args.dest)
    print(f"copied={copied} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py -q`

Expected: PASS. `test_make_session_gets_list_once`는 `requests`를 실제로 열지 않는다.

- [ ] **Step 5: Commit**

```bash
git add scripts/crawler/kasb_replies.py scripts/crawl_kasb_replies.py scripts/export_kasb_replies_raw.py scripts/tests/test_kasb_replies.py
git commit -m "$(cat <<'EOF'
feat: add KASB reply crawl and raw export commands

EOF
)"
```

---

### Task 7: 사이트 문구와 전체 검증

**Files:**

- Modify: `docs/index.md`
- Modify: `scripts/tests/test_kasb_replies.py`
- Test: `scripts/tests/test_kasb_replies.py`

**Interfaces:**

- Consumes: 없음
- Produces: `docs/index.md`의 질의회신 문장

- [ ] **Step 1: Write the failing test**

Append to `scripts/tests/test_kasb_replies.py`:

```python
def test_site_index_does_not_promise_reply_pages():
    index = Path(__file__).resolve().parents[2] / "docs" / "index.md"
    text = index.read_text(encoding="utf-8")
    assert "질의회신 원문은 이 사이트에 게시하지 않는다" in text
    assert "질의회신 정리" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py::test_site_index_does_not_promise_reply_pages -q`

Expected: FAIL because `docs/index.md` still contains `질의회신 정리`

- [ ] **Step 3: Replace the index sentence**

In `docs/index.md`, replace:

```markdown
- **(추가 예정)** 회계기준원(KASB) 질의회신 정리, 유관기관 보도자료 확장 등
```

with:

```markdown
- 회계기준원(KASB) 질의회신 원문은 이 사이트에 게시하지 않는다. 유관기관 보도자료 확장은 추가 예정.
```

Confirm `docs/superpowers/specs/2026-11-04-kasb-reply-archive-design.md` contains `**상태**: 승인됨 (2026-11-04)`. Confirm `docs/superpowers/README.md` links this plan. Do not add the archive under `docs/`.

- [ ] **Step 4: Run the verification commands**

Working directory: `scripts`

Run: `python -m pytest tests/test_kasb_replies.py -q`

Expected: PASS

Working directory: `scripts`

Run: `python -m pytest tests/ -q`

Expected: PASS

Working directory: repository root

Run: `mkdocs build --strict`

Expected: exit code 0. The build output does not list `data/kasb-replies`.

- [ ] **Step 5: Commit**

```bash
git add docs/index.md scripts/tests/test_kasb_replies.py
git commit -m "$(cat <<'EOF'
docs: state that KASB replies stay off the site

EOF
)"
```

Do not run `python scripts/crawl_kasb_replies.py` in this task. Filling `data/kasb-replies/` is a later operator run.
