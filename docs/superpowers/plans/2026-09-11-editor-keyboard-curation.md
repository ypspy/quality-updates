# Editor Row-Keyboard Curation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 큐레이션 편집기에서 링크 행을 위·아래로 고르고, Enter로 미리보기, Space로 상태 순환, 좌우로 출처 탭을 바꾸며, 첨부 저장이 원문 미리보기를 덮지 않고, 다운로드 목록은 최신 파일이 위에 오게 한다.

**Architecture:** `GET /api/downloads`를 mtime 내림차순으로 바꾼다. 미리보기 HTML에서 확장자가 파일인 링크는 `/api/source/save_fetched`로 rewrite하고, 부모 JS는 저장 후 iframe을 비우지 않으며 stub이 뜨면 직전 미리보기로 되돌린다. 목록은 선택 행 하나(`selectedIdx`)에 roving tabindex를 두고 행 모드/출처 편집 모드로 키를 나눈다. 저장 마커·sidecar 스키마는 바꾸지 않는다.

**Tech Stack:** Flask, vanilla JS (`scripts/editor/static/editor.js`), pytest, 기존 `download_helpers` / `html_sanitize`

**Spec:** `docs/superpowers/specs/2026-09-11-editor-keyboard-curation-design.md`

## Global Constraints

- Space 순환은 `undecided → skip → no_summary → needs_summary → undecided`이다. `done`은 Space로 바꾸지 않는다.
- 좌·우는 상태가 `needs_summary`일 때만 PDF ↔ WEB ↔ CLIP 탭(`sourcePanel`)만 바꾼다. 검색·캡쳐·붙여넣기·`setSourceKind`의 출처 비우기는 실행하지 않는다.
- 행 모드 Enter는 선택 행 **원문 URL** 미리보기만 한다. 포커스는 선택 행에 남긴다. iframe `tabindex="-1"`.
- 첨부 저장 성공 시 iframe을 `about:blank`로 두지 않는다. `clearIframeOnSuccess`는 쓰지 않는다. 토스트는 2.5초(`2500ms`).
- `GET /api/downloads`는 `st_mtime` 내림차순, 동점이면 경로 소문자. 피커 검색은 필터만 하고 그 순서를 유지한다.
- 전역 문자 단축키(`C` 캡쳐 등), iframe 안 키보드, PDF 렌더, 요약 자동 생성은 이 플랜에 없다.
- 기존 큐레이션 저장 마커·sidecar 계약을 바꾸지 않는다.
- JS 테스트 러너는 레포에 없다. Python으로 검증 가능한 계약만 pytest로 고정하고, 키보드·iframe 포커스는 spec §7 수동 목록으로 확인한다.

---

## File map

| File | Action |
|------|--------|
| `scripts/editor/routes/files.py` | Modify — `list_downloads` mtime 정렬 |
| `scripts/tests/test_downloads_folder_policy.py` | Modify — 최신순 assert |
| `scripts/editor/download_helpers.py` | Modify — `url_looks_like_attachment` |
| `scripts/editor/html_sanitize.py` | Modify — 첨부 href를 `save_fetched`로 rewrite |
| `scripts/tests/test_html_sanitize.py` | Modify — 첨부 rewrite 테스트 |
| `scripts/editor/static/editor.js` | Modify — 토스트/iframe 유지, 행 키보드, 출처 편집 모드, 피커 필터, 캡쳐 토스트 |
| `scripts/editor/static/editor.css` | Modify — 선택 행 강조 |
| `scripts/editor/templates/index.html` | Modify — iframe `tabindex="-1"`, `editor.js?v=5` |
| `docs/project/editor-curation-workflow.md` | Modify — 키보드·토스트·목록 순서 |
| `docs/superpowers/specs/2026-09-11-editor-keyboard-curation-design.md` | Modify — 상태 승인됨 |
| `docs/superpowers/README.md` | Modify — Plans 색인 |

`scripts/editor_config.json`은 커밋하지 않는다.

---

### Task 1: 다운로드 목록 mtime 최신순

**Files:**
- Modify: `scripts/editor/routes/files.py`
- Modify: `scripts/tests/test_downloads_folder_policy.py`
- Modify: `scripts/editor/static/editor.js` (`filterAndSortPdfPaths`)
- Test: `scripts/tests/test_downloads_folder_policy.py`

**Interfaces:**
- Consumes: `GET /api/downloads` → `{ "files": list[str], "folder_exists": bool }`
- Produces: `files`는 `st_mtime` 내림차순. `filterAndSortPdfPaths(paths, rawQuery)`는 검색어가 있으면 원배열 순서를 유지한 채 파일명 부분일치만 남긴다.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_downloads_folder_policy.py`의 `test_downloads_list_default_folder`를 아래로 **교체**하고, 같은 파일에 최신순 테스트를 추가한다.

```python
def test_downloads_list_default_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(editor_config, "CONFIG_PATH", tmp_path / "editor_config.json")
    monkeypatch.setattr(editor_config, "repo_root", lambda: tmp_path)

    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "a.pdf").write_bytes(b"%PDF-1.7\n%...")
    (downloads / "b.pdf").write_bytes(b"%PDF-1.7\n%...")
    (downloads / "c.zip").write_bytes(b"PK\x03\x04")
    (downloads / "c.txt").write_text("nope", encoding="utf-8")

    client = editor_app.app.test_client()
    resp = client.get("/api/downloads")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["folder_exists"] is True
    assert set(data["files"]) == {
        "downloads/a.pdf",
        "downloads/b.pdf",
        "downloads/c.txt",
        "downloads/c.zip",
    }


def test_downloads_list_newest_mtime_first(monkeypatch, tmp_path):
    monkeypatch.setattr(editor_config, "CONFIG_PATH", tmp_path / "editor_config.json")
    monkeypatch.setattr(editor_config, "repo_root", lambda: tmp_path)

    downloads = tmp_path / "downloads"
    downloads.mkdir()
    older = downloads / "older.pdf"
    newer = downloads / "newer.pdf"
    older.write_bytes(b"%PDF-1.7\n%...")
    newer.write_bytes(b"%PDF-1.7\n%...")
    os.utime(older, (1_000_000, 1_000_000))
    os.utime(newer, (2_000_000, 2_000_000))

    client = editor_app.app.test_client()
    resp = client.get("/api/downloads")
    assert resp.status_code == 200
    files = resp.get_json()["files"]
    assert files.index("downloads/newer.pdf") < files.index("downloads/older.pdf")
```

파일 상단에 이미 `import os`가 있다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_downloads_folder_policy.py::test_downloads_list_newest_mtime_first -v`

Expected: FAIL — `a.pdf`가 가나다순으로 `newer`보다 앞에 있거나, index 순서가 기대와 다름.

- [ ] **Step 3: Sort `list_downloads` by mtime**

`scripts/editor/routes/files.py`의 `list_downloads`에서 경로 소문자 정렬을 교체한다.

```python
    files = [f for f in folder.rglob("*") if f.is_file()]

    def _download_sort_key(p: Path):
        try:
            mtime = p.stat().st_mtime
        except OSError:
            mtime = 0.0
        return (-mtime, p.as_posix().lower())

    files.sort(key=_download_sort_key)
    rel = [f.relative_to(root).as_posix() for f in files]
```

- [ ] **Step 4: Keep picker filter order**

`scripts/editor/static/editor.js`의 `filterAndSortPdfPaths`를 필터만 하도록 바꾼다 (함수명은 호출부 유지를 위해 그대로).

```javascript
  function filterAndSortPdfPaths(paths, rawQuery) {
    const query = String(rawQuery || '');
    const qNorm = normalizeForMatch(query);
    const all = Array.isArray(paths) ? paths : [];
    if (!qNorm) return all.slice();
    return all.filter((p) => {
      const candNorm = normalizeForMatch(String(p || ''));
      return candNorm.indexOf(qNorm) !== -1;
    });
  }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd scripts && python -m pytest tests/test_downloads_folder_policy.py -v`

Expected: PASS (해당 파일의 모든 테스트)

- [ ] **Step 6: Commit**

```bash
git add scripts/editor/routes/files.py scripts/tests/test_downloads_folder_policy.py scripts/editor/static/editor.js
git commit -m "fix(editor): list downloads newest-first by mtime"
```

---

### Task 2: 미리보기 첨부 링크를 save_fetched로 rewrite

**Files:**
- Modify: `scripts/editor/download_helpers.py`
- Modify: `scripts/editor/html_sanitize.py`
- Modify: `scripts/tests/test_html_sanitize.py`
- Test: `scripts/tests/test_html_sanitize.py`

**Interfaces:**
- Consumes: `sanitize_html_for_web_preview(html: str, base_url: str) -> str`
- Produces: `url_looks_like_attachment(url: str) -> bool`. 참이면 첨부 href는 `/api/source/save_fetched?url=…`, 아니면 기존 `/api/source/preview?url=…`.

- [ ] **Step 1: Write the failing tests**

`scripts/tests/test_html_sanitize.py` 끝에 추가한다.

```python
def test_url_looks_like_attachment_by_suffix():
    import editor.download_helpers as dh

    assert dh.url_looks_like_attachment("https://kasb.or.kr/files/a.pdf") is True
    assert dh.url_looks_like_attachment("https://example.com/x.HWPX?x=1") is True
    assert dh.url_looks_like_attachment("https://example.com/page") is False
    assert dh.url_looks_like_attachment("https://example.com/view.do") is False


def test_rewrites_pdf_href_to_save_fetched():
    import editor.html_sanitize as hs

    html = '<a href="attach/foo.pdf">첨부</a>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/dir/")
    assert "/api/source/save_fetched?url=" in out
    assert "foo.pdf" in out
    assert "/api/source/preview?url=" not in out


def test_html_article_href_still_goes_to_preview():
    import editor.html_sanitize as hs

    html = '<a href="https://example.com/article">본문</a>'
    out = hs.sanitize_html_for_web_preview(html, base_url="https://example.com/")
    assert "/api/source/preview?url=" in out
    assert "/api/source/save_fetched?url=" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python -m pytest tests/test_html_sanitize.py::test_url_looks_like_attachment_by_suffix tests/test_html_sanitize.py::test_rewrites_pdf_href_to_save_fetched tests/test_html_sanitize.py::test_html_article_href_still_goes_to_preview -v`

Expected: FAIL — `url_looks_like_attachment` 없음, PDF 링크가 여전히 `preview?url=`.

- [ ] **Step 3: Add `url_looks_like_attachment`**

`scripts/editor/download_helpers.py`에 추가한다 (`urlsplit`은 이미 import됨).

```python
_ATTACHMENT_SUFFIXES = frozenset(
    {
        ".pdf",
        ".hwp",
        ".hwpx",
        ".hml",
        ".zip",
        ".7z",
        ".rar",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".tif",
        ".tiff",
    }
)


def url_looks_like_attachment(url: str) -> bool:
    """True when the URL path suffix is a downloadable file, not an HTML page."""
    if not isinstance(url, str) or not url.strip():
        return False
    path = urlsplit(url.strip()).path.lower()
    dot = path.rfind(".")
    if dot < 0:
        return False
    return path[dot:] in _ATTACHMENT_SUFFIXES
```

- [ ] **Step 4: Rewrite attachment hrefs in sanitize**

`scripts/editor/html_sanitize.py` 상단 import에 `from .download_helpers import url_looks_like_attachment`를 추가한다.

`sanitize_html_for_web_preview`의 링크 rewrite 블록에서 `encoded = quote(abs_url, safe="")` 다음을 이렇게 바꾼다.

```python
        encoded = quote(abs_url, safe="")
        if url_looks_like_attachment(abs_url):
            el.attrs["href"] = f"/api/source/save_fetched?url={encoded}"
        else:
            el.attrs["href"] = f"/api/source/preview?url={encoded}"
        el.attrs["rel"] = "noopener noreferrer"
```

`/api/source/`로 이미 시작하는 href(KASB `kasb_file` 등)는 기존처럼 그대로 둔다.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd scripts && python -m pytest tests/test_html_sanitize.py tests/test_preview_endpoint.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/editor/download_helpers.py scripts/editor/html_sanitize.py scripts/tests/test_html_sanitize.py
git commit -m "fix(editor): rewrite preview file links to save_fetched"
```

---

### Task 3: 저장 후 미리보기 유지와 토스트 2.5초

**Files:**
- Modify: `scripts/editor/static/editor.js`
- Modify: `scripts/editor/templates/index.html`
- Test: 없음 (JS). 회귀: `cd scripts && python -m pytest tests/test_preview_endpoint.py tests/test_html_sanitize.py -q`

**Interfaces:**
- Consumes: iframe 클릭 위임 `onIframeSaveLinkClick`, `runSaveByPath(path, opts)`, `showToast`, `postMessage` `quality-updates-fetch-save`
- Produces: `lastGoodPreviewSrc` (string). 저장 성공 시 iframe을 `about:blank`로 바꾸지 않음. stub 로드 시 `lastGoodPreviewSrc`로 복구. 토스트 `2500ms`. 캡쳐 성공/실패는 `alert` 대신 `showToast`.

- [ ] **Step 1: Stop blanking the iframe**

`showToast` 타이머를 `2500`으로 바꾼다.

`runSaveByPath`에서 `clearIframeOnSuccess` 분기를 **삭제**한다. 성공 시 토스트 + `await loadPdfFiles()`만 하고, **`renderTable()`을 호출하지 않는다** (선택 행·포커스를 지우지 않기 위함). PDF 피커는 다음 열 때 `ensureFreshPdfFiles(true)`가 이미 있다.

`setupParentSaveMessageListener`는 다음처럼 고친다.

```javascript
      runSaveByPath(String(d.path), {});
      restorePreviewIfStub();
```

모듈 스코프에 추가:

```javascript
  let lastGoodPreviewSrc = '';

  function isSaveDelegateStub(doc) {
    try {
      return !!(doc && doc.body && /quality-updates-fetch-save/.test(doc.body.innerHTML));
    } catch (_) {
      return false;
    }
  }

  function restorePreviewIfStub() {
    const iframe = document.getElementById('preview-iframe');
    if (!iframe || !lastGoodPreviewSrc) return;
    let doc = null;
    try { doc = iframe.contentDocument; } catch (_) { doc = null; }
    if (isSaveDelegateStub(doc) || !iframe.src || iframe.src === 'about:blank') {
      iframe.src = lastGoodPreviewSrc;
    }
  }
```

`showPreviewIframe`에서 `iframe.src = srcUrl` 직전에 `lastGoodPreviewSrc = srcUrl`을 넣는다. stub URL을 `lastGoodPreviewSrc`에 넣지 않는다 (우리가 넣는 src는 `preview_fast` / `preview` / clips뿐이다).

- [ ] **Step 2: Intercept save links without navigating**

`onIframeSaveLinkClick` pathname 허용 목록을 유지하고, `preview` / `preview_fast`이면서 중첩 `url`이 첨부로 보이면 `save_fetched`로 저장한다.

```javascript
  function onIframeSaveLinkClick(ev) {
    const a = ev.target.closest('a');
    if (!a || !a.href) return;
    let u;
    try {
      u = new URL(a.href, window.location.origin);
    } catch (_) {
      return;
    }
    if (u.origin !== window.location.origin) return;
    const p = u.pathname || '';
    const savePaths = ['/api/source/kasb_file', '/api/source/save_pdf', '/api/source/save_fetched'];
    if (savePaths.indexOf(p) !== -1) {
      ev.preventDefault();
      ev.stopPropagation();
      runSaveByPath(u.pathname + u.search, {});
      return;
    }
    if (p === '/api/source/preview' || p === '/api/source/preview_fast') {
      const nested = u.searchParams.get('url') || '';
      if (nestedLooksLikeAttachment(nested)) {
        ev.preventDefault();
        ev.stopPropagation();
        runSaveByPath('/api/source/save_fetched?url=' + encodeURIComponent(nested), {});
      }
    }
  }

  function nestedLooksLikeAttachment(url) {
    const path = String(url || '').split('?')[0].split('#')[0].toLowerCase();
    const m = path.match(/\.[a-z0-9]+$/);
    if (!m) return false;
    const suffixes = {
      '.pdf': 1, '.hwp': 1, '.hwpx': 1, '.hml': 1, '.zip': 1, '.7z': 1, '.rar': 1,
      '.doc': 1, '.docx': 1, '.xls': 1, '.xlsx': 1, '.ppt': 1, '.pptx': 1,
      '.png': 1, '.jpg': 1, '.jpeg': 1, '.gif': 1, '.webp': 1, '.tif': 1, '.tiff': 1
    };
    return !!suffixes[m[0]];
  }
```

`showPreviewIframe`의 `onload`에서 `wireIframeDelegatedSaveClicks` 뒤에:

```javascript
        if (isSaveDelegateStub(iframe.contentDocument)) {
          restorePreviewIfStub();
        }
```

- [ ] **Step 3: Capture uses toast only**

`web-btn-save-clip` 핸들러에서 `alert(...)` 세 곳을 `showToast(...)`로 바꾼다. 부분 성공 문구는 `showToast((data.error || '캡쳐 오류') + ' — 스크린샷은 연결됨: ' + shotPath)`로 둔다. `renderTable()` 호출은 Task 4의 선택 복구가 생길 때까지 유지한다.

- [ ] **Step 4: Iframe is not a tab stop**

`scripts/editor/templates/index.html`:

```html
        <iframe id="preview-iframe" src="about:blank" tabindex="-1"></iframe>
```

같은 파일의 스크립트를 `/static/editor.js?v=5`로 올린다.

- [ ] **Step 5: Run Python regression**

Run: `cd scripts && python -m pytest tests/test_preview_endpoint.py tests/test_html_sanitize.py tests/test_web_to_clip_route.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/editor/static/editor.js scripts/editor/templates/index.html
git commit -m "fix(editor): keep preview HTML after attachment save"
```

---

### Task 4: 행 모드 키보드 (↑↓ Enter Space ←→)

**Files:**
- Modify: `scripts/editor/static/editor.js`
- Modify: `scripts/editor/static/editor.css`
- Test: 없음 (JS). 회귀: `cd scripts && python -m pytest tests/ -q`

**Interfaces:**
- Consumes: `linksData`, `cycleState(idx)`, `openPreview(url)`, `sourceKind(link)`
- Produces: `selectedIdx: number`, `selectedLineIndex: number|null`, `uiMode: 'row'|'source-edit'` (이 태스크에서는 `'row'`만 사용). `moveSelection(delta)`, `cycleSourcePanel(idx, delta)`, `applyRowTabStops()`, `restoreSelectionAfterRender()`. 좌우는 `sourcePanel`만 변경.

- [ ] **Step 1: Add selection state and CSS**

`editor.js`의 `openPicker` 선언 근처에 추가:

```javascript
  let selectedIdx = 0;
  let selectedLineIndex = null;
  let uiMode = 'row';
  const SOURCE_PANEL_CYCLE = ['pdf', 'web', 'clip'];
```

`editor.css` 행 상태 블록 뒤에 추가:

```css
#link-tbody tr[data-idx].is-selected td {
  box-shadow: inset 4px 0 0 #1565c0;
  outline: 2px solid rgba(21, 101, 192, 0.45);
  outline-offset: -2px;
}
```

- [ ] **Step 2: Apply roving tabindex after each render**

`renderTable` 끝(모든 행 append 후)과 `loadLinks`의 `renderTable()` 앞에 `selectedIdx = 0`을 두지 말고, `loadLinks`에서는 파일을 바꾼 뒤 `selectedIdx = 0; selectedLineIndex = linksData[0] ? linksData[0].line_index : null; uiMode = 'row';`를 설정한다.

다음 함수를 `renderTable` 위에 둔다.

```javascript
  function rememberSelection() {
    const link = linksData[selectedIdx];
    selectedLineIndex = link ? link.line_index : null;
  }

  function restoreSelectionAfterRender() {
    if (!linksData.length) {
      selectedIdx = 0;
      selectedLineIndex = null;
      return;
    }
    if (selectedLineIndex != null) {
      const found = linksData.findIndex((l) => l.line_index === selectedLineIndex);
      selectedIdx = found >= 0 ? found : 0;
    } else if (selectedIdx < 0 || selectedIdx >= linksData.length) {
      selectedIdx = 0;
    }
    selectedLineIndex = linksData[selectedIdx].line_index;
    applyRowTabStops();
    if (uiMode === 'row') {
      const tr = document.querySelector('#link-tbody tr[data-idx="' + selectedIdx + '"]');
      if (tr) {
        tr.focus({ preventScroll: true });
        tr.scrollIntoView({ block: 'nearest' });
      }
    }
  }

  function applyRowTabStops() {
    const rows = document.querySelectorAll('#link-tbody tr[data-idx]');
    rows.forEach((tr) => {
      const idx = Number(tr.dataset.idx);
      const selected = idx === selectedIdx;
      tr.tabIndex = selected ? 0 : -1;
      tr.classList.toggle('is-selected', selected);
      tr.querySelectorAll('.title-link, .state-badge, .source-tab, .source-btn, .source-input, .clip-draft').forEach((el) => {
        if (uiMode === 'source-edit' && selected) return;
        el.tabIndex = -1;
      });
    });
  }

  function selectRow(idx, opts) {
    if (idx < 0 || idx >= linksData.length) return;
    selectedIdx = idx;
    selectedLineIndex = linksData[idx].line_index;
    uiMode = (opts && opts.keepMode) ? uiMode : 'row';
    applyRowTabStops();
    const tr = document.querySelector('#link-tbody tr[data-idx="' + idx + '"]');
    if (tr && uiMode === 'row') {
      tr.focus({ preventScroll: true });
      tr.scrollIntoView({ block: 'nearest' });
    }
  }

  function moveSelection(delta) {
    if (!linksData.length) return;
    const next = Math.max(0, Math.min(linksData.length - 1, selectedIdx + delta));
    selectRow(next);
  }

  function cycleSourcePanel(idx, delta) {
    const link = linksData[idx];
    if (!link || link.state !== 'needs_summary') return;
    const cur = sourceKind(link);
    const i = Math.max(0, SOURCE_PANEL_CYCLE.indexOf(cur));
    const next = SOURCE_PANEL_CYCLE[(i + delta + SOURCE_PANEL_CYCLE.length) % SOURCE_PANEL_CYCLE.length];
    link.sourcePanel = next;
    closeOpenPicker();
    rememberSelection();
    renderTable();
  }
```

`renderTable` 마지막에 `restoreSelectionAfterRender();`를 호출한다. `closeOpenPicker()`가 렌더마다 호출되므로 출처 편집 중 전체 재렌더는 행 모드로 떨어질 수 있다. `cycleState` / `cycleSourcePanel` / 배지 클릭은 행 모드가 맞다.

각 `tr`에 `tr.addEventListener('mousedown', () => selectRow(idx, { keepMode: true }));`를 달아 클릭한 행을 선택한다. 제목 클릭 핸들러는 `selectRow(idx); openPreview(link.url);` 순으로 바꾼다. 제목/배지의 `keydown` Enter/Space는 **제거**한다 (행 모드 전역 핸들러가 담당). 배지 `click`은 `selectRow(idx); cycleState(idx);`로 둔다.

`cycleState` 안의 `renderTable()` 앞에 `rememberSelection();`을 넣는다. `selectedIdx`가 인자 `idx`와 다르면 먼저 `selectedIdx = idx`로 맞춘다.

- [ ] **Step 3: Document-level row-mode keys**

`init()` 끝에 `document.addEventListener('keydown', onEditorKeyDown);`를 추가한다.

```javascript
  function isHeaderTarget(el) {
    return !!(el && el.closest && el.closest('#header'));
  }

  function isTypingTarget(el) {
    if (!el) return false;
    const tag = (el.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
    if (el.isContentEditable) return true;
    return false;
  }

  function onEditorKeyDown(e) {
    if (e.defaultPrevented) return;
    if (openPicker) return;
    if (uiMode === 'source-edit') return;
    const t = e.target;
    if (isHeaderTarget(t) || isTypingTarget(t)) return;
    if (!linksData.length) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      moveSelection(1);
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      moveSelection(-1);
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      const url = linksData[selectedIdx] && linksData[selectedIdx].url;
      if (url) openPreview(url);
      selectRow(selectedIdx);
      return;
    }
    if (e.key === ' ' || e.key === 'Spacebar') {
      e.preventDefault();
      cycleState(selectedIdx);
      return;
    }
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      cycleSourcePanel(selectedIdx, -1);
      return;
    }
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      cycleSourcePanel(selectedIdx, 1);
      return;
    }
  }
```

`openPreview` 끝에서 `selectRow(selectedIdx)` 대신 선택 `tr`에 `focus({ preventScroll: true })`만 한다 (iframe이 포커스를 가져가지 않게).

- [ ] **Step 4: Run Python regression**

Run: `cd scripts && python -m pytest tests/ -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/editor/static/editor.js scripts/editor/static/editor.css
git commit -m "feat(editor): row-mode arrow keys for curation"
```

---

### Task 5: 출처 편집 모드 (Tab / Esc)

**Files:**
- Modify: `scripts/editor/static/editor.js`
- Test: 없음 (JS). 회귀: `cd scripts && python -m pytest tests/ -q`

**Interfaces:**
- Consumes: Task 4의 `uiMode`, `selectedIdx`, `applyRowTabStops`, `selectRow`
- Produces: `enterSourceEdit() -> boolean`, `exitSourceEdit()`. Tab은 선택 행 활성 패널 첫 컨트롤로. Esc는 피커가 열려 있으면 닫기만, 아니면 행 모드. 출처 편집 중 ↑↓는 행 이동에 쓰지 않음 (`onEditorKeyDown`이 `uiMode === 'source-edit'`에서 return).

- [ ] **Step 1: Enter and leave source-edit**

```javascript
  function panelControls(tr) {
    const cell = tr.querySelector('.source-cell');
    if (!cell) return [];
    return Array.prototype.slice.call(cell.querySelectorAll('button, input, textarea'));
  }

  function enterSourceEdit() {
    const link = linksData[selectedIdx];
    if (!link || link.state === 'done') return false;
    const tr = document.querySelector('#link-tbody tr[data-idx="' + selectedIdx + '"]');
    if (!tr) return false;
    const cell = tr.querySelector('.source-cell');
    if (!cell) return false;
    const kind = sourceKind(link);
    let target = null;
    if (kind === 'pdf') target = cell.querySelector('.source-input');
    else if (kind === 'web') target = cell.querySelector('.web-btn-preview');
    else target = cell.querySelector('.clip-draft');
    if (!target) return false;
    uiMode = 'source-edit';
    panelControls(tr).forEach((el) => {
      const panel = el.closest('.source-panel');
      const hidden = panel && panel.style.display === 'none';
      el.tabIndex = hidden ? -1 : 0;
    });
    cell.querySelectorAll('.source-tab').forEach((el) => { el.tabIndex = 0; });
    target.focus();
    return true;
  }

  function exitSourceEdit() {
    if (openPicker) {
      closeOpenPicker();
      return;
    }
    uiMode = 'row';
    applyRowTabStops();
    const tr = document.querySelector('#link-tbody tr[data-idx="' + selectedIdx + '"]');
    if (tr) tr.focus({ preventScroll: true });
  }
```

- [ ] **Step 2: Tab / Shift+Tab / Esc in `onEditorKeyDown`**

`onEditorKeyDown` 앞부분에 출처 편집·행 모드 Tab을 넣는다. `openPicker`가 열려 있어도 Esc는 기존 `onDocKeyDown`이 피커를 닫는다. 출처 편집 Esc는 피커가 없을 때만 `exitSourceEdit`한다.

`onEditorKeyDown`을 다음 순서로 바꾼다.

```javascript
  function onEditorKeyDown(e) {
    if (e.defaultPrevented) return;
    const t = e.target;

    if (e.key === 'Escape' && uiMode === 'source-edit' && !openPicker) {
      e.preventDefault();
      exitSourceEdit();
      return;
    }

    if (uiMode === 'source-edit') {
      if (e.key === 'Tab') {
        const tr = document.querySelector('#link-tbody tr[data-idx="' + selectedIdx + '"]');
        if (!tr) return;
        const focusables = panelControls(tr).filter((el) => el.tabIndex >= 0 && !el.disabled);
        const tabs = Array.prototype.slice.call(tr.querySelectorAll('.source-tab'));
        const list = tabs.concat(focusables);
        if (!list.length) return;
        const i = list.indexOf(document.activeElement);
        if (e.shiftKey && (i <= 0)) {
          e.preventDefault();
          exitSourceEdit();
          return;
        }
        if (!e.shiftKey && i === list.length - 1) {
          e.preventDefault();
          list[list.length - 1].focus();
          return;
        }
      }
      return;
    }

    if (openPicker) return;
    if (isHeaderTarget(t) || isTypingTarget(t)) return;
    if (!linksData.length) return;

    if (e.key === 'Tab' && !e.shiftKey) {
      if (enterSourceEdit()) e.preventDefault();
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      moveSelection(1);
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      moveSelection(-1);
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      const url = linksData[selectedIdx] && linksData[selectedIdx].url;
      if (url) openPreview(url);
      const tr = document.querySelector('#link-tbody tr[data-idx="' + selectedIdx + '"]');
      if (tr) tr.focus({ preventScroll: true });
      return;
    }
    if (e.key === ' ' || e.key === 'Spacebar') {
      e.preventDefault();
      cycleState(selectedIdx);
      return;
    }
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      cycleSourcePanel(selectedIdx, -1);
      return;
    }
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      cycleSourcePanel(selectedIdx, 1);
    }
  }
```

기존 PDF 피커 input의 `ArrowDown`/`Enter`/`Escape` 핸들러는 그대로 둔다. 출처 편집 중 `onEditorKeyDown`이 `openPicker`가 아니라도 `uiMode === 'source-edit'`에서 Tab/Esc 외에는 return하므로 피커 키와 충돌하지 않는다. 피커가 열린 뒤 Esc는 `onDocKeyDown`이 먼저 닫고, 그다음 Esc가 행 모드로 돌아온다.

- [ ] **Step 3: Run Python regression**

Run: `cd scripts && python -m pytest tests/ -q`

Expected: PASS

- [ ] **Step 4: Manual check (spec §7)**

`python scripts/editor.py`로 편집기를 연 뒤:

1. Tab 없이 ↑↓만으로 링크 행 이동.
2. Enter 미리보기 후 Space·화살표가 목록에서 동작.
3. Space 4상태, 완료 행은 불변.
4. 요약 필요에서 ← → 가 PDF/WEB/CLIP만 변경.
5. Tab → PDF 검색 → Esc(피커) → Esc(행 모드) → ↑↓.
6. 첨부 클릭 → 토스트 2.5초, 원문 HTML 유지, 피커 「전체」 상단에 그 파일.
7. 본문 HTML 링크는 iframe에서 이동.

- [ ] **Step 5: Commit**

```bash
git add scripts/editor/static/editor.js
git commit -m "feat(editor): Tab/Esc source-edit mode for link rows"
```

---

### Task 6: 워크플로 문서와 spec 상태

**Files:**
- Modify: `docs/project/editor-curation-workflow.md`
- Modify: `docs/superpowers/specs/2026-09-11-editor-keyboard-curation-design.md`
- Modify: `docs/superpowers/README.md`

**Interfaces:**
- Consumes: 구현된 키맵·토스트 2.5초·mtime 목록
- Produces: HITL 문서에 키보드 절. spec 상태 `승인됨`. Plans 색인 행.

- [ ] **Step 1: Update the HITL workflow doc**

`docs/project/editor-curation-workflow.md`의 「편집기 동작 요약」 목록에 아래를 추가한다 (WEB 미리보기 불릿의 토스트 「약 1초」는 **2.5초**로 고친다).

```markdown
- **키보드 (행 모드)**: `↑` `↓` 링크 선택, `Enter` 원문 미리보기(포커스는 행 유지), `Space` 상태 순환(미결정→스킵→요약 없음→요약 필요), `←` `→` 요약 필요일 때 PDF/WEB/CLIP 탭, `Tab` 해당 행 출처 편집, `Esc` 행 모드 복귀.
- **다운로드 목록**: `/api/downloads`는 파일 수정 시간 **최신순**. PDF 피커 「전체」도 이 순서다.
```

- [ ] **Step 2: Mark spec approved and index the plan**

스펙 헤더:

```markdown
**상태**: 승인됨
```

`docs/superpowers/README.md` Plans 표 최상단:

```markdown
| 2026-09-11 | [editor-keyboard-curation.md](plans/2026-09-11-editor-keyboard-curation.md) | 편집기 행 키보드, 첨부 토스트, PDF 최신순 |
```

- [ ] **Step 3: Commit**

```bash
git add docs/project/editor-curation-workflow.md docs/superpowers/specs/2026-09-11-editor-keyboard-curation-design.md docs/superpowers/README.md docs/superpowers/plans/2026-09-11-editor-keyboard-curation.md
git commit -m "docs: editor keyboard curation plan and workflow notes"
```

---

## Spec coverage (self-review)

| Spec 절 | Task |
|---------|------|
| Space 4상태, done 무시 | 4 |
| ←→ 탭만, 요약 필요일 때만 | 4 (`cycleSourcePanel`) |
| 행/출처 편집, Tab, Esc | 5 |
| Enter 미리보기, 포커스 행 유지, iframe tabindex -1 | 3, 4 |
| 첨부 저장+토스트, HTML 이동 허용, about:blank 금지, stub 복구 | 2, 3 |
| 토스트 2.5초, 캡쳐도 토스트 | 3 |
| PDF mtime 최신순, 검색은 필터만 | 1 |
| 선택 행 강조, line_index 복구 | 4 |
| 마우스 유지, 제목 클릭=선택+미리보기 | 4 |
| 범위 외 문자 단축키 | 하지 않음 |
| HITL 문서 | 6 |
