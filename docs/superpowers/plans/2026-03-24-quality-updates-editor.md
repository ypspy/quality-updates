# Quality Updates Editor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python scripts/editor.py`로 실행하는 로컬 Flask 웹 UI — 크롤러 생성 `.md`의 링크를 선별(요약/스킵)하고 PDF를 연결하여 Claude Code Phase 0·1 수행 전 `.md`에 주석으로 저장한다.

**Architecture:** Flask가 `.md` 파일을 파싱해 링크 목록 JSON을 반환하고, 브라우저에서 큐레이션한 결과를 다시 Flask가 받아 `.md`에 `<!-- skip -->` / `<!-- pdf: ... -->` 주석으로 삽입한다. 우측 패널은 iframe 시도 후 차단 감지 시 새 탭 fallback. 설정(다운로드 폴더·마지막 파일)은 `scripts/editor_config.json`에 영속화한다.

**Tech Stack:** Python 3, Flask, vanilla JS (ES6), HTML/CSS (no framework)

**Spec:** `docs/superpowers/specs/2026-03-24-quality-updates-editor-design.md`

---

## Chunk 1: 백엔드 — 파서 + 저장 로직

### Task 1: 프로젝트 스캐폴드

**Files:**
- Modify: `requirements.txt`
- Create: `scripts/editor/__init__.py`
- Create: `scripts/editor/templates/index.html` (빈 플레이스홀더)
- Create: `scripts/editor/static/editor.js` (빈 플레이스홀더)
- Create: `scripts/editor/static/editor.css` (빈 플레이스홀더)

- [ ] **Step 1: requirements.txt에 flask 추가**

`requirements.txt` 끝에 추가:
```
flask>=3.0
```

- [ ] **Step 2: 디렉터리 및 빈 파일 생성**

```bash
mkdir -p scripts/editor/templates scripts/editor/static
touch scripts/editor/__init__.py
echo "<!DOCTYPE html><html><body>placeholder</body></html>" > scripts/editor/templates/index.html
echo "" > scripts/editor/static/editor.js
echo "" > scripts/editor/static/editor.css
```

- [ ] **Step 3: flask 설치 확인**

```bash
pip install flask
python -c "import flask; print(flask.__version__)"
```
Expected: 버전 출력 (3.x)

- [ ] **Step 4: 커밋**

```bash
git add requirements.txt scripts/editor/
git commit -m "chore: scaffold quality-updates editor structure"
```

---

### Task 2: .md 파서

**Files:**
- Create: `scripts/editor/parser.py`
- Create: `scripts/tests/test_parser.py`

#### 파서 스펙 요약
- 링크 패턴: `- (YY-MM-DD) [제목](URL)` (들여쓰기 허용)
- `## Appendix` 헤더 이후 라인 무시
- 각 링크 다음 줄 주석으로 상태 복원:
  - `<!-- skip -->` → `skip`
  - `<!-- pdf: 경로 -->` → `needs_summary` + pdf_path
  - `!!! note` 또는 `??? note` → `done`
  - 없으면 → `undecided`
- 기관 섹션 헤더(`### 금융감독원` 등)로 agency 태깅

- [ ] **Step 1: 실패하는 테스트 작성**

`scripts/tests/test_parser.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from editor.parser import parse_links

SAMPLE_MD = """
### 금융감독원

#### 보도자료

- (25-01-10) [제목A](https://fss.or.kr/a)
<!-- skip -->

- (25-01-15) [제목B](https://fss.or.kr/b)
<!-- pdf: downloads/250115.pdf -->

- (25-01-20) [제목C](https://fss.or.kr/c)

    !!! note "주요 내용"

        - 내용

- (25-01-25) [제목D](https://fss.or.kr/d)

### 금융위원회

- (25-02-01) [제목E](https://fsc.go.kr/e)

## Appendix A. Complete List

- (25-02-05) [Appendix링크](https://fss.or.kr/x)
"""


def test_parse_count():
    links = parse_links(SAMPLE_MD)
    assert len(links) == 5, f"expected 5 links (not Appendix), got {len(links)}"


def test_skip_state():
    links = parse_links(SAMPLE_MD)
    a = next(l for l in links if l['title'] == '제목A')
    assert a['state'] == 'skip'


def test_pdf_state():
    links = parse_links(SAMPLE_MD)
    b = next(l for l in links if l['title'] == '제목B')
    assert b['state'] == 'needs_summary'
    assert b['pdf_path'] == 'downloads/250115.pdf'


def test_done_state():
    links = parse_links(SAMPLE_MD)
    c = next(l for l in links if l['title'] == '제목C')
    assert c['state'] == 'done'


def test_undecided_state():
    links = parse_links(SAMPLE_MD)
    d = next(l for l in links if l['title'] == '제목D')
    assert d['state'] == 'undecided'


def test_agency_tagging():
    links = parse_links(SAMPLE_MD)
    a = next(l for l in links if l['title'] == '제목A')
    assert a['agency'] == '금융감독원'
    e = next(l for l in links if l['title'] == '제목E')
    assert e['agency'] == '금융위원회'


def test_appendix_excluded():
    links = parse_links(SAMPLE_MD)
    titles = [l['title'] for l in links]
    assert 'Appendix링크' not in titles


def test_line_index():
    # SAMPLE_MD starts with \n → line 0 is blank
    # line 5: 제목A, line 8: 제목B, line 11: 제목C, line 17: 제목D, line 21: 제목E
    links = parse_links(SAMPLE_MD)
    by_title = {l['title']: l for l in links}
    assert by_title['제목A']['line_index'] == 5
    assert by_title['제목B']['line_index'] == 8
    assert by_title['제목C']['line_index'] == 11
    assert by_title['제목D']['line_index'] == 17
    assert by_title['제목E']['line_index'] == 21
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /c/Users/yoont/source/03_Development/audit-quality/quality-updates
python -m pytest scripts/tests/test_parser.py -v
```
Expected: `ImportError` 또는 `ModuleNotFoundError`

- [ ] **Step 3: parser.py 구현**

`scripts/editor/parser.py`:
```python
# -*- coding: utf-8 -*-
"""Parse quality-updates .md files to extract link items."""
import re
from typing import Optional

LINK_RE = re.compile(
    r'^\s*- \((\d{2}-\d{2}-\d{2})\) \[(.+?)\]\((https?://[^\)]+)\)'
)
SECTION_RE = re.compile(r'^#{1,4}\s+(.+)')
APPENDIX_RE = re.compile(r'^## Appendix')
SKIP_RE = re.compile(r'^<!-- skip -->')
PDF_RE = re.compile(r'^<!-- pdf: (.+?) -->')
NOTE_RE = re.compile(r'^\s+[!?]{3} note')

AGENCY_KEYWORDS = {
    '금융감독원': '금융감독원',
    '금융위원회': '금융위원회',
    '한국공인회계사회': '한국공인회계사회',
    '한국회계기준원': '한국회계기준원',
}


def _detect_agency(header: str) -> Optional[str]:
    for key, name in AGENCY_KEYWORDS.items():
        if key in header:
            return name
    return None


def parse_links(content: str) -> list[dict]:
    """Parse .md content and return list of link dicts.

    Each dict: {date, title, url, state, pdf_path, agency, line_index}
    state: 'undecided' | 'skip' | 'needs_summary' | 'done'
    """
    lines = content.splitlines()
    links = []
    current_agency = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # Stop at Appendix boundary
        if APPENDIX_RE.match(line):
            break

        # Track agency section headers
        section_match = SECTION_RE.match(line)
        if section_match:
            agency = _detect_agency(section_match.group(1))
            if agency:
                current_agency = agency

        # Match link line
        link_match = LINK_RE.match(line)
        if link_match:
            date, title, url = link_match.groups()
            state = 'undecided'
            pdf_path = None

            # Look ahead for state markers
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1

            if j < len(lines):
                next_line = lines[j]
                if SKIP_RE.match(next_line):
                    state = 'skip'
                elif PDF_RE.match(next_line):
                    state = 'needs_summary'
                    pdf_path = PDF_RE.match(next_line).group(1).strip()
                elif NOTE_RE.match(next_line):
                    state = 'done'

            links.append({
                'date': date,
                'title': title,
                'url': url,
                'state': state,
                'pdf_path': pdf_path,
                'agency': current_agency,
                'line_index': i,
            })

        i += 1

    return links
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest scripts/tests/test_parser.py -v
```
Expected: 8개 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add scripts/editor/parser.py scripts/tests/test_parser.py
git commit -m "feat(editor): add .md link parser with Appendix boundary"
```

---

### Task 3: .md 저장 로직

**Files:**
- Create: `scripts/editor/saver.py`
- Create: `scripts/tests/test_saver.py`

#### 저장 전략
- 원본 텍스트를 라인 단위로 순회
- Appendix 이전까지만 주석 삽입/삭제
- 기존 `<!-- skip -->` / `<!-- pdf: ... -->` 제거 후 새 상태에 맞게 재삽입
- `!!! note` 블록이 있는 링크(done)는 수정하지 않음
- 저장 전 `.md.bak` 생성

- [ ] **Step 1: 실패하는 테스트 작성**

`scripts/tests/test_saver.py`:
```python
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from editor.saver import apply_curation

ORIGINAL = """\
### 금융감독원

- (25-01-10) [제목A](https://fss.or.kr/a)

- (25-01-15) [제목B](https://fss.or.kr/b)
<!-- skip -->

- (25-01-20) [제목C](https://fss.or.kr/c)
<!-- pdf: downloads/old.pdf -->

- (25-01-25) [제목D](https://fss.or.kr/d)

    !!! note "주요 내용"

        - 내용

## Appendix A. Complete List

- (25-02-01) [AppendixLink](https://fss.or.kr/x)
"""

# Curation: A→skip, B→needs_summary+pdf, C→undecided, D(done)→unchanged
CURATION = [
    {'title': '제목A', 'line_index': 2, 'state': 'skip', 'pdf_path': None},
    {'title': '제목B', 'line_index': 4, 'state': 'needs_summary', 'pdf_path': 'downloads/250115.pdf'},
    {'title': '제목C', 'line_index': 7, 'state': 'undecided', 'pdf_path': None},
    {'title': '제목D', 'line_index': 10, 'state': 'done', 'pdf_path': None},
]


def test_skip_inserted():
    result = apply_curation(ORIGINAL, CURATION)
    lines = result.splitlines()
    idx = next(i for i, l in enumerate(lines) if '제목A' in l)
    assert lines[idx + 1] == '<!-- skip -->', f"got: {lines[idx+1]!r}"


def test_pdf_updated():
    result = apply_curation(ORIGINAL, CURATION)
    lines = result.splitlines()
    idx = next(i for i, l in enumerate(lines) if '제목B' in l)
    assert lines[idx + 1] == '<!-- pdf: downloads/250115.pdf -->'


def test_old_skip_removed():
    result = apply_curation(ORIGINAL, CURATION)
    # B had <!-- skip -->, now should have <!-- pdf: ... -->
    assert result.count('<!-- skip -->') == 1  # only A


def test_old_pdf_removed_for_undecided():
    result = apply_curation(ORIGINAL, CURATION)
    assert 'downloads/old.pdf' not in result


def test_done_unchanged():
    result = apply_curation(ORIGINAL, CURATION)
    assert '!!! note "주요 내용"' in result


def test_appendix_preserved():
    result = apply_curation(ORIGINAL, CURATION)
    assert '## Appendix A. Complete List' in result
    assert 'AppendixLink' in result


def test_bak_created(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text(ORIGINAL, encoding='utf-8')
    from editor.saver import save_with_backup
    save_with_backup(str(md_file), ORIGINAL, CURATION)
    assert (tmp_path / "test.md.bak").exists()
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python -m pytest scripts/tests/test_saver.py -v
```
Expected: `ImportError`

- [ ] **Step 3: saver.py 구현**

`scripts/editor/saver.py`:
```python
# -*- coding: utf-8 -*-
"""Apply curation results to .md file content."""
import re
import shutil
from typing import Optional

SKIP_RE = re.compile(r'^<!-- skip -->$')
PDF_RE = re.compile(r'^<!-- pdf: .+ -->$')
APPENDIX_RE = re.compile(r'^## Appendix')
NOTE_RE = re.compile(r'^\s+[!?]{3} note')


def _is_comment(line: str) -> bool:
    return bool(SKIP_RE.match(line) or PDF_RE.match(line))


def apply_curation(content: str, curation: list[dict]) -> str:
    """Return new .md content with curation comments applied."""
    lines = content.splitlines(keepends=True)
    # Build lookup: line_index → curation entry
    curation_map = {entry['line_index']: entry for entry in curation}

    result = []
    i = 0
    in_appendix = False

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip('\n')

        if APPENDIX_RE.match(stripped):
            in_appendix = True

        if in_appendix:
            result.append(line)
            i += 1
            continue

        if i in curation_map:
            entry = curation_map[i]

            # done entries: leave everything after the link untouched
            # (blank line + !!! note block must stay intact for MkDocs)
            if entry['state'] == 'done':
                result.append(line)
                i += 1
                continue

            result.append(line)  # keep link line as-is
            i += 1

            # Skip blank lines + old comments immediately after link
            while i < len(lines):
                next_stripped = lines[i].rstrip('\n')
                if next_stripped == '' or _is_comment(next_stripped):
                    i += 1
                else:
                    break

            # Insert new comment based on state
            state = entry['state']
            if state == 'skip':
                result.append('<!-- skip -->\n')
            elif state == 'needs_summary' and entry.get('pdf_path'):
                result.append(f"<!-- pdf: {entry['pdf_path']} -->\n")
            # undecided / done → no comment

            # If next line is a note block (done state), leave it alone
            continue

        result.append(line)
        i += 1

    return ''.join(result)


def save_with_backup(file_path: str, original_content: str, curation: list[dict]) -> None:
    """Create .bak then write curated content to file_path."""
    shutil.copy2(file_path, file_path + '.bak')
    new_content = apply_curation(original_content, curation)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest scripts/tests/test_saver.py -v
```
Expected: 7개 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add scripts/editor/saver.py scripts/tests/test_saver.py
git commit -m "feat(editor): add .md curation saver with bak backup"
```

---

## Chunk 2: Flask 앱 + 프론트엔드

### Task 4: Flask 앱

**Files:**
- Create: `scripts/editor.py` (진입점)
- Create: `scripts/editor/app.py` (Flask routes)

- [ ] **Step 1: app.py 구현**

`scripts/editor/app.py`:
```python
# -*- coding: utf-8 -*-
"""Flask routes for the quality-updates editor."""
import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .parser import parse_links
from .saver import save_with_backup

app = Flask(__name__)

CONFIG_PATH = Path(__file__).parent.parent / 'editor_config.json'
DEFAULT_CONFIG = {
    'downloads_folder': 'downloads/',
    'last_file': '',
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding='utf-8') as f:
            cfg = json.load(f)
        return {**DEFAULT_CONFIG, **cfg}
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def repo_root() -> Path:
    """Return repository root (parent of scripts/)."""
    return Path(__file__).parent.parent.parent


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/files')
def list_files():
    root = repo_root()
    updates_dir = root / 'docs' / 'quality-updates'
    files = sorted(updates_dir.rglob('*.md'))
    return jsonify([str(f.relative_to(root)) for f in files])


@app.route('/api/links')
def get_links():
    file_path = request.args.get('file')
    if not file_path:
        return jsonify({'error': 'file param required'}), 400
    root = repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({'error': 'invalid path'}), 400
    if not full_path.exists():
        return jsonify({'error': 'file not found'}), 404
    content = full_path.read_text(encoding='utf-8')
    links = parse_links(content)
    cfg = load_config()
    cfg['last_file'] = file_path
    save_config(cfg)
    return jsonify({'links': links, 'content': content})


@app.route('/api/downloads')
def list_downloads():
    cfg = load_config()
    folder = repo_root() / cfg['downloads_folder']
    if not folder.exists():
        return jsonify([])
    files = sorted(folder.glob('*.pdf'))
    rel = [str(Path(cfg['downloads_folder']) / f.name) for f in files]
    return jsonify(rel)


@app.route('/api/save', methods=['POST'])
def save():
    data = request.get_json()
    file_path = data.get('file')
    curation = data.get('curation', [])
    if not file_path:
        return jsonify({'error': 'file required'}), 400
    root = repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({'error': 'invalid path'}), 400
    if not full_path.exists():
        return jsonify({'error': 'file not found'}), 404
    original = full_path.read_text(encoding='utf-8')
    save_with_backup(str(full_path), original, curation)
    return jsonify({'ok': True})


ALLOWED_CONFIG_KEYS = {'downloads_folder', 'last_file'}

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        return jsonify(load_config())
    cfg = load_config()
    incoming = {k: v for k, v in request.get_json().items() if k in ALLOWED_CONFIG_KEYS}
    cfg.update(incoming)
    save_config(cfg)
    return jsonify(cfg)
```

- [ ] **Step 2: editor.py 진입점 작성**

`scripts/editor.py`:
```python
# -*- coding: utf-8 -*-
"""Entry point: python scripts/editor.py"""
import os
import sys
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(__file__))
from editor.app import app

PORT = 5000

if __name__ == '__main__':
    url = f'http://localhost:{PORT}'
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f'Quality Updates Editor → {url}')
    app.run(port=PORT, debug=False)
```

- [ ] **Step 3: 수동 스모크 테스트**

```bash
cd /c/Users/yoont/source/03_Development/audit-quality/quality-updates
python scripts/editor.py
```
Expected:
- 브라우저가 `http://localhost:5000`으로 열림
- `http://localhost:5000/api/files` → JSON 배열 반환
- `http://localhost:5000/api/config` → `{"downloads_folder": "downloads/", "last_file": ""}` 반환

- [ ] **Step 4: 커밋**

```bash
git add scripts/editor.py scripts/editor/app.py
git commit -m "feat(editor): add Flask app with API routes"
```

---

### Task 5: 프론트엔드 UI

**Files:**
- Modify: `scripts/editor/templates/index.html`
- Modify: `scripts/editor/static/editor.js`
- Modify: `scripts/editor/static/editor.css`

- [ ] **Step 1: index.html 작성**

`scripts/editor/templates/index.html`:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>Quality Updates Editor</title>
  <link rel="stylesheet" href="/static/editor.css">
</head>
<body>
  <!-- Header -->
  <header id="header">
    <div id="header-left">
      <label>파일:
        <select id="file-select"><option value="">선택...</option></select>
      </label>
      <span id="dl-folder-display"></span>
      <button id="btn-change-folder">폴더 변경</button>
    </div>
    <div id="header-center">
      전체 <span id="cnt-total">0</span> |
      요약 필요 <span id="cnt-needs">0</span> |
      스킵 <span id="cnt-skip">0</span> |
      미결정 <span id="cnt-undecided">0</span> |
      완료 <span id="cnt-done">0</span>
    </div>
    <div id="header-right">
      <button id="btn-save">저장</button>
    </div>
  </header>

  <!-- Main: split pane -->
  <div id="main">
    <div id="left-panel">
      <table id="link-table">
        <thead>
          <tr>
            <th>날짜</th>
            <th>제목</th>
            <th>기관</th>
            <th>상태</th>
            <th>PDF</th>
          </tr>
        </thead>
        <tbody id="link-tbody"></tbody>
      </table>
    </div>
    <div id="divider"></div>
    <div id="right-panel">
      <div id="iframe-container">
        <iframe id="preview-iframe" src="about:blank" sandbox="allow-scripts allow-same-origin allow-forms allow-popups"></iframe>
        <div id="iframe-fallback" style="display:none">
          <p>이 사이트는 분할 화면을 지원하지 않습니다.</p>
          <a id="fallback-link" href="#" target="_blank">새 탭에서 열기 →</a>
        </div>
      </div>
    </div>
  </div>

  <script src="/static/editor.js"></script>
</body>
</html>
```

- [ ] **Step 2: editor.css 작성**

`scripts/editor/static/editor.css`:
```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Noto Sans KR', sans-serif; font-size: 13px; height: 100vh; display: flex; flex-direction: column; }

#header { display: flex; align-items: center; justify-content: space-between; padding: 6px 12px; background: #1a1a2e; color: #fff; gap: 12px; flex-shrink: 0; }
#header select, #header button { font-size: 12px; padding: 3px 8px; }
#header button { cursor: pointer; }
#btn-save { background: #4caf50; color: #fff; border: none; border-radius: 4px; padding: 4px 14px; font-weight: bold; }
#header-center { flex: 1; text-align: center; font-size: 12px; }

#main { display: flex; flex: 1; overflow: hidden; }
#left-panel { width: 55%; overflow-y: auto; border-right: 2px solid #ccc; }
#divider { width: 4px; background: #ddd; cursor: col-resize; }
#right-panel { flex: 1; display: flex; flex-direction: column; }
#iframe-container { flex: 1; display: flex; flex-direction: column; }
#preview-iframe { flex: 1; border: none; width: 100%; height: 100%; }
#iframe-fallback { padding: 40px; text-align: center; }
#iframe-fallback a { color: #1976d2; font-size: 15px; }

/* Table */
#link-table { width: 100%; border-collapse: collapse; }
#link-table th { background: #f0f0f0; padding: 6px 8px; text-align: left; position: sticky; top: 0; border-bottom: 2px solid #ccc; }
#link-table td { padding: 5px 8px; border-bottom: 1px solid #eee; vertical-align: middle; }
.section-header td { background: #e8eaf6; font-weight: bold; padding: 4px 8px; }

/* Row states */
tr.state-skip td { color: #aaa; }
tr.state-needs td { background: #e3f2fd; }
tr.state-done td { color: #888; font-style: italic; }

/* State badge */
.state-badge { cursor: pointer; padding: 2px 8px; border-radius: 12px; font-size: 11px; user-select: none; white-space: nowrap; }
.badge-undecided { background: #eeeeee; }
.badge-needs { background: #1976d2; color: #fff; }
.badge-skip { background: #757575; color: #fff; }
.badge-done { background: #388e3c; color: #fff; cursor: default; }

/* Title link */
.title-link { color: #1976d2; text-decoration: none; cursor: pointer; }
.title-link:hover { text-decoration: underline; }
```

- [ ] **Step 3: editor.js 작성**

`scripts/editor/static/editor.js`:
```javascript
/* Quality Updates Editor — main JS */
(function () {
  'use strict';

  let currentFile = null;
  let originalContent = null;
  let linksData = [];   // [{date, title, url, state, pdf_path, agency, line_index}]
  let pdfFiles = [];

  // ── Bootstrap ──────────────────────────────────────────────────────────────
  async function init() {
    await loadConfig();
    await populateFileSelect();
    await loadPdfFiles();
    document.getElementById('file-select').addEventListener('change', onFileChange);
    document.getElementById('btn-save').addEventListener('click', onSave);
    document.getElementById('btn-change-folder').addEventListener('click', onChangeFolder);
    setupDivider();
  }

  async function loadConfig() {
    const cfg = await fetchJSON('/api/config');
    document.getElementById('dl-folder-display').textContent = '다운로드 폴더: ' + cfg.downloads_folder;
    if (cfg.last_file) {
      currentFile = cfg.last_file;
    }
  }

  async function populateFileSelect() {
    const files = await fetchJSON('/api/files');
    const sel = document.getElementById('file-select');
    files.forEach(f => {
      const opt = document.createElement('option');
      opt.value = f;
      opt.textContent = f.split('/').slice(-1)[0];
      sel.appendChild(opt);
    });
    if (currentFile) {
      sel.value = currentFile;
      await loadLinks(currentFile);
    }
  }

  async function loadPdfFiles() {
    pdfFiles = await fetchJSON('/api/downloads');
  }

  // ── Events ──────────────────────────────────────────────────────────────────
  async function onFileChange(e) {
    currentFile = e.target.value;
    if (currentFile) await loadLinks(currentFile);
  }

  async function onSave() {
    if (!currentFile) return alert('파일을 선택하세요.');
    const curation = linksData
      .filter(l => l.state !== 'done')
      .map(l => ({
        title: l.title,
        line_index: l.line_index,
        state: l.state,
        pdf_path: l.pdf_path || null,
      }));
    const res = await fetch('/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file: currentFile, curation }),
    });
    if (res.ok) alert('저장 완료');
    else alert('저장 실패');
  }

  async function onChangeFolder() {
    const folder = prompt('다운로드 폴더 경로 (예: downloads/ 또는 C:/Users/me/Downloads)');
    if (!folder) return;
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ downloads_folder: folder }),
    });
    document.getElementById('dl-folder-display').textContent = '다운로드 폴더: ' + folder;
    await loadPdfFiles();
    renderTable();
  }

  // ── Data loading ────────────────────────────────────────────────────────────
  async function loadLinks(file) {
    const data = await fetchJSON(`/api/links?file=${encodeURIComponent(file)}`);
    linksData = data.links;
    originalContent = data.content;
    renderTable();
    updateCounter();
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  function renderTable() {
    const tbody = document.getElementById('link-tbody');
    tbody.innerHTML = '';
    let lastAgency = null;

    linksData.forEach((link, idx) => {
      // Section header row
      if (link.agency !== lastAgency) {
        lastAgency = link.agency;
        const hdr = document.createElement('tr');
        hdr.className = 'section-header';
        const td = document.createElement('td');
        td.colSpan = 5;
        td.textContent = link.agency || '기타';
        hdr.appendChild(td);
        tbody.appendChild(hdr);
      }

      const tr = document.createElement('tr');
      tr.dataset.idx = idx;
      tr.className = stateClass(link.state);

      tr.innerHTML = `
        <td>${link.date}</td>
        <td><span class="title-link" data-url="${escHtml(link.url)}">${escHtml(link.title)}</span></td>
        <td>${link.agency || ''}</td>
        <td>${stateBadge(link, idx)}</td>
        <td>${pdfDropdown(link, idx)}</td>
      `;

      // Title click → preview
      tr.querySelector('.title-link').addEventListener('click', () => openPreview(link.url));

      // State badge click (not done)
      if (link.state !== 'done') {
        tr.querySelector('.state-badge').addEventListener('click', () => cycleState(idx));
      }

      // PDF dropdown change
      const sel = tr.querySelector('.pdf-select');
      if (sel) {
        sel.addEventListener('change', e => {
          linksData[idx].pdf_path = e.target.value || null;
          if (e.target.value) linksData[idx].state = 'needs_summary';
          updateCounter();
          reRenderRow(tr, idx);
        });
      }

      tbody.appendChild(tr);
    });
  }

  function reRenderRow(tr, idx) {
    const link = linksData[idx];
    tr.className = stateClass(link.state);
    tr.querySelector('td:nth-child(4)').innerHTML = stateBadge(link, idx);
    if (link.state !== 'done') {
      tr.querySelector('.state-badge').addEventListener('click', () => cycleState(idx));
    }
  }

  function stateClass(state) {
    return { undecided: '', needs_summary: 'state-needs', skip: 'state-skip', done: 'state-done' }[state] || '';
  }

  function stateBadge(link, idx) {
    const labels = { undecided: '미결정', needs_summary: '요약 필요', skip: '스킵', done: '완료' };
    const cls = { undecided: 'badge-undecided', needs_summary: 'badge-needs', skip: 'badge-skip', done: 'badge-done' };
    return `<span class="state-badge ${cls[link.state]}" data-idx="${idx}">${labels[link.state]}</span>`;
  }

  function pdfDropdown(link, idx) {
    if (link.state === 'done') return '';
    if (pdfFiles.length === 0) return '<span style="color:#aaa">폴더 없음</span>';
    const selected = link.pdf_path || '';
    const options = ['<option value="">선택 안 함</option>',
      ...pdfFiles.map(f => `<option value="${escHtml(f)}"${f === selected ? ' selected' : ''}>${f.split(/[\\/]/).pop()}</option>`)
    ].join('');
    return `<select class="pdf-select" data-idx="${idx}">${options}</select>`;
  }

  // ── State cycling ────────────────────────────────────────────────────────────
  const STATE_CYCLE = ['undecided', 'needs_summary', 'skip'];

  function cycleState(idx) {
    const link = linksData[idx];
    const cur = STATE_CYCLE.indexOf(link.state);
    link.state = STATE_CYCLE[(cur + 1) % STATE_CYCLE.length];
    if (link.state !== 'needs_summary') link.pdf_path = null;
    updateCounter();
    renderTable(); // simple full re-render
  }

  // ── Counter ──────────────────────────────────────────────────────────────────
  function updateCounter() {
    const counts = { total: linksData.length, needs_summary: 0, skip: 0, undecided: 0, done: 0 };
    linksData.forEach(l => { counts[l.state] = (counts[l.state] || 0) + 1; });
    document.getElementById('cnt-total').textContent = counts.total;
    document.getElementById('cnt-needs').textContent = counts.needs_summary;
    document.getElementById('cnt-skip').textContent = counts.skip;
    document.getElementById('cnt-undecided').textContent = counts.undecided;
    document.getElementById('cnt-done').textContent = counts.done;
  }

  // ── Preview (iframe + fallback) ──────────────────────────────────────────────
  function openPreview(url) {
    const iframe = document.getElementById('preview-iframe');
    const fallback = document.getElementById('iframe-fallback');
    const fallbackLink = document.getElementById('fallback-link');

    fallback.style.display = 'none';
    iframe.style.display = 'block';
    iframe.src = url;
    fallbackLink.href = url;

    // Detect X-Frame-Options block via timeout heuristic
    iframe.onload = () => {
      try {
        // If same-origin, contentDocument exists; cross-origin: null but no error yet
        // We rely on the onerror event for blocked iframes where supported
      } catch (e) {
        showFallback(url);
      }
    };
    iframe.onerror = () => showFallback(url);

    // Heuristic: many blocking sites trigger neither load nor error within 3s
    // So we also check after a short delay by attempting contentDocument access
    setTimeout(() => {
      try {
        const doc = iframe.contentDocument;
        if (doc && doc.body && doc.body.innerHTML === '') showFallback(url);
      } catch (e) {
        showFallback(url);
      }
    }, 3000);
  }

  function showFallback(url) {
    document.getElementById('preview-iframe').style.display = 'none';
    const fallback = document.getElementById('iframe-fallback');
    fallback.style.display = 'block';
    document.getElementById('fallback-link').href = url;
  }

  // ── Divider drag ─────────────────────────────────────────────────────────────
  function setupDivider() {
    const divider = document.getElementById('divider');
    const left = document.getElementById('left-panel');
    let dragging = false;

    divider.addEventListener('mousedown', () => { dragging = true; });
    document.addEventListener('mousemove', e => {
      if (!dragging) return;
      const main = document.getElementById('main');
      const rect = main.getBoundingClientRect();
      const pct = Math.min(80, Math.max(20, ((e.clientX - rect.left) / rect.width) * 100));
      left.style.width = pct + '%';
    });
    document.addEventListener('mouseup', () => { dragging = false; });
  }

  // ── Utils ────────────────────────────────────────────────────────────────────
  async function fetchJSON(url) {
    const res = await fetch(url);
    return res.json();
  }

  function escHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Start ────────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);
})();
```

- [ ] **Step 4: 수동 E2E 테스트**

```bash
python scripts/editor.py
```

확인 항목:
1. 브라우저가 열리고 파일 드롭다운에 `.md` 파일이 표시됨
2. 파일 선택 시 링크 테이블이 기관별 섹션으로 표시됨
3. 상태 배지 클릭 시 미결정→요약 필요→스킵→미결정 순환
4. PDF 드롭다운에서 선택 시 상태가 "요약 필요"로 변경
5. 제목 클릭 시 우측 iframe에 URL 로드, 차단 시 "새 탭에서 열기" 표시
6. 저장 버튼 → `.md` 파일에 주석 삽입 확인, `.md.bak` 생성 확인
7. 다운로드 폴더 변경 버튼 동작 확인

- [ ] **Step 5: 커밋**

```bash
git add scripts/editor/templates/index.html scripts/editor/static/
git commit -m "feat(editor): add frontend UI with split pane and state management"
```

---

### Task 6: 마무리 및 문서화

**Files:**
- Modify: `README.md` (에디터 사용법 섹션 추가)

- [ ] **Step 1: README에 에디터 실행 방법 추가**

`README.md`의 적절한 위치에 추가:

```markdown
## 큐레이션 편집 도구

크롤러 생성 `.md` 파일의 링크를 선별하고 PDF를 연결하는 로컬 편집 도구.

```bash
pip install flask   # 최초 1회
python scripts/editor.py
```

- 파일 선택 → 링크 목록에서 요약 필요 / 스킵 결정
- PDF 다운로드 후 드롭다운에서 연결
- 저장 → Claude Code에서 SKILL.md Phase 0·1 수행
```

- [ ] **Step 2: 전체 테스트 재실행**

```bash
python -m pytest scripts/tests/ -v
```
Expected: 모든 테스트 PASS

- [ ] **Step 3: 최종 커밋**

```bash
git add README.md
git commit -m "docs: add editor usage to README"
```
