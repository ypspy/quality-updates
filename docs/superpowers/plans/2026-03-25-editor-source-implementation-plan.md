# Editor SOURCE(근거) + WEB 프리뷰 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 큐레이션 편집 도구에서 `PDF` 전용 컬럼을 `SOURCE` 컬럼으로 일반화하고(PDF/WEB/CLIP), `iframe`이 막힌 사이트도 서버 fetch 기반으로 “정제된 HTML” 프리뷰를 제공한다.

**Architecture:** 링크 아래 마커를 `<!-- source: <type>|<ref> -->`로 통일하고, 편집기는 행마다 source를 편집한다. WEB 프리뷰는 Flask가 URL을 fetch→정제(sanitize)→링크 rewrite 후 반환하며, 첨부 링크는 프록시 엔드포인트로 전달한다.

**Tech Stack:** Flask, vanilla JS, pytest(테스트), `requests`(fetch), `bleach`(sanitize), `beautifulsoup4`(HTML parsing) *(필요 시 `lxml`)*

**Run (local):** `python scripts/editor.py` (기본 포트: `http://localhost:5000`)

**Status (완료):** 2026-03-25 기준 `feat/editor-source`를 `main`에 fast-forward 반영. 검증: 저장소 루트에서 `cd scripts && python -m pytest -q` → **91 passed**.

---

## File Map (create/modify)

**Modify**
- `scripts/editor.py`: 실행 엔트리포인트 (`python scripts/editor.py`) — Flask `app`를 import해서 실행만 담당(부트스트랩)
- `scripts/editor/parser.py`: `<!-- source: ... -->` 파싱 + 기존 `<!-- pdf: ... -->` 호환
- `scripts/editor/saver.py`: `source` 마커 저장 + 기존 `pdf` 마커 마이그레이션(쓰기 규칙)
- `scripts/editor/app.py`: source preview/proxy API + clip 저장 API + downloads API(메타 optional)
- `scripts/editor/templates/index.html`: `PDF` → `SOURCE` 컬럼 UI + 프리뷰 영역(iframe fallback → server preview)
- `scripts/editor/static/editor.js`: source 모델/피커(UI), WEB/CLIP 워크플로우, 키보드 플로우, “최근” 저장
- `scripts/editor/static/editor.css`: 피커/프리뷰 스타일
- `docs/superpowers/specs/2026-03-25-editor-pdf-picker-design.md`: spec 최신 상태 유지(이미 작성됨)

**Create**
- `scripts/editor/source_fetch.py`: URL 검증(SSRF) + fetch + redirect 정책 + 크기 제한
- `scripts/editor/html_sanitize.py`: HTML sanitize + 링크 rewrite 유틸
- `scripts/editor/clip_store.py`: clip 저장/로드(파일 기반) + id 생성 + (optional) dedupe
- `scripts/tests/test_source_markers.py`: source 마커 파싱/저장 테스트
- `scripts/tests/test_web_preview_security.py`: SSRF 차단/리다이렉트/스킴 차단 테스트(가능한 범위)
- `requirements-dev.txt`: `pytest` 등 개발 의존성

---

### Task 1: SOURCE 마커 파싱/저장(백엔드 기반 정리)

**Files:**
- Modify: `scripts/editor/parser.py`
- Modify: `scripts/editor/saver.py`
- Create: `scripts/tests/test_source_markers.py`

- [x] **Step 1: Write failing tests for parsing `source` marker**

`scripts/tests/test_source_markers.py`에 아래 케이스를 추가한다.
- `<!-- source: pdf|downloads/a.pdf -->` → `state=needs_summary`, `source={type:'pdf', ref:'downloads/a.pdf'}`
- `<!-- source: url|https://example.com -->` → `state=needs_summary`, `source={type:'web', ref:'https://example.com'}`
- `<!-- source: clip|clip_x -->` → `state=needs_summary`, `source={type:'clip', ref:'clip_x'}`
- 기존 `<!-- pdf: downloads/old.pdf -->`는 **호환**: `source.type='pdf'`로 읽히도록

- [x] **Step 2: Run tests (expect FAIL)**

Run: `python -m pytest -q scripts/tests/test_source_markers.py`
Expected: FAIL (parser/saver가 `source`를 모름)

- [x] **Step 3: Implement parser changes**

변경 요지:
- `PDF_RE` 외에 `SOURCE_RE = r'^<!-- source: (.+?) -->'` 추가
- `source`를 `{type, ref}`로 파싱(구분자 `|`, type whitelist)
- `links` dict에 `source` 필드 추가
- 기존 `pdf_path`는 점진적으로 제거하되, 우선은 backward compatible로 유지(테스트 통과 우선)

- [x] **Step 4: Implement saver changes**

변경 요지:
- 저장 시 `state=='needs_summary'`이면 `source`가 있을 때 `<!-- source: ... -->`를 쓴다.
- 기존 `<!-- pdf: ... -->` / `<!-- skip -->`를 link 아래에서 제거하는 로직을 `source`까지 포함하도록 확장한다.
- Migration: 과거 문서에 `<!-- pdf: ... -->`가 있어도, 저장하면 `<!-- source: pdf|... -->`로 정규화되도록.

- [x] **Step 5: Re-run tests (expect PASS)**

Run: `python -m pytest -q scripts/tests/test_source_markers.py`
Expected: PASS

- [x] **Step 6: Commit**

```bash
git add scripts/editor/parser.py scripts/editor/saver.py scripts/tests/test_source_markers.py
git commit -m "feat(editor): support unified source markers"
```

---

### Task 2: PDF SOURCE 피커(검색/최근) UI (MVP-1)

**Files:**
- Modify: `scripts/editor/templates/index.html`
- Modify: `scripts/editor/static/editor.js`
- Modify: `scripts/editor/static/editor.css`

- [x] **Step 1: Adjust table column to SOURCE**

`index.html`에서 헤더 `PDF` → `SOURCE`.

- [x] **Step 2: Update client data model**

`linksData` 항목에 `source`를 추가해서 사용:
- `source = null | { type: 'pdf'|'web'|'clip', ref: string }`
- 기존 `pdf_path`는 파서 호환 단계에서만 존재 가능 → 렌더는 `source` 기반으로 단일화

- [x] **Step 3: Decide downloads API shape (Option A vs B)**

결정(초기 MVP): **Option A**로 시작한다.
- `/api/downloads`는 기존처럼 `string[] (path)` 반환 유지
- UI는 파일명만으로 검색/정렬(메타(수정일/크기) 표시는 MVP에서 제외)

> 이후 필요하면 Option B(메타 포함)는 별도 태스크로 추가.

- [x] **Step 4: Render PDF picker skeleton**

- SOURCE 타입이 `pdf`일 때: 셀에 `input` + “열기(▼)” 버튼 + 결과 컨테이너(숨김) 렌더
- 결과 리스트는 **최대 12개**만 DOM에 렌더(스크롤 컨테이너)

- [x] **Step 5: Implement filtering + sorting utility (unit-testable)**

요구사항(스펙 반영):
- 정규화: 대소문자 무시 + 공백/하이픈/언더스코어 제거
- 매칭: contains
- 정렬: 접두/완전 일치 우선 → 매칭 위치가 앞일수록 우선 (mtime 정렬은 Option B에서)

- [x] **Step 6: Implement open/close behavior**

- 열기: 입력 포커스에서 `ArrowDown` 또는 버튼 클릭
- 닫기: `Esc`, click-outside
- 선택 시 자동 닫기

- [x] **Step 7: Implement keyboard navigation**

- `ArrowUp/Down`: highlight 이동
- `Enter`: highlight 선택
- `Tab/Shift+Tab`: 기본 포커스 이동을 방해하지 않되, dropdown 열려 있으면 닫는 정책을 결정하고 적용

- [x] **Step 8: Implement state updates (select/clear)**

- 선택: `source={type:'pdf', ref:path}` + `state='needs_summary'`
- 비우기: `source=null` + `state='undecided'`
- 저장 payload는 `source`를 포함하도록 갱신(백엔드 저장과 연결)

- [x] **Step 9: Implement Recents (localStorage)**

- key 예시: `quality-updates-editor:recentSources:pdf`
- path 기반 dedupe + top 10
- UI: 입력이 비어 있으면 “최근” 섹션을 결과 상단에 노출(탭 대신 섹션으로 MVP 단순화)

- [x] **Step 10: Add minimal accessibility attributes**

가능한 범위에서:
- input: `role="combobox"`, `aria-expanded`, `aria-controls`
- list: `role="listbox"`, option: `role="option"`, `aria-selected`

- [x] **Step 11: Manual sanity check**

Run: `python scripts/editor.py`
Expected:
- PDF가 많아도 입력으로 즉시 필터링
- 선택/해제가 상태 규칙대로 동작

- [x] **Step 12: Commit**

```bash
git add scripts/editor/templates/index.html scripts/editor/static/editor.js scripts/editor/static/editor.css
git commit -m "feat(editor): add searchable source picker for PDFs"
```

---

### Task 3A: WEB fetch 보안(SSRF) + 런타임 의존성 정리 (MVP-2)

**Files:**
- Create: `scripts/editor/source_fetch.py`
- Create: `scripts/tests/test_web_preview_security.py`
- Modify: `requirements.txt`
- Create: `requirements-dev.txt`

- [x] **Step 1: Add dev deps for tests**

Create `requirements-dev.txt`:
- `pytest`
- `requests`
- `beautifulsoup4`
- `bleach`
- optional: `lxml`

- [x] **Step 2: Decide runtime vs dev deps**

결정(권장):
- `requests`, `beautifulsoup4`, `bleach`는 **런타임**(서버 프리뷰에 필요) → `requirements.txt`에 추가
- `pytest`는 **dev** → `requirements-dev.txt`

- [x] **Step 3: Write failing tests for URL validation**

`test_web_preview_security.py`에 최소 케이스:
- `file://...` / `ftp://...` 거부
- `http://127.0.0.1` / `http://localhost` 거부
- redirect가 localhost/private로 향하면 거부
- IPv6 loopback: `http://[::1]` 거부
- private ranges(RFC1918), link-local, `0.0.0.0` 거부
- userinfo trick: `http://good.com@127.0.0.1` 거부
- port policy(최소: 80/443 외 허용 여부 결정 후 테스트)

Run: `python -m pytest -q scripts/tests/test_web_preview_security.py`
Expected: FAIL

- [x] **Step 4: Implement SSRF-safe fetch utility**

`source_fetch.py`에 포함할 정책(최소):
- scheme allowlist: http/https
- DNS resolve 후 private IP/loopback/link-local deny (IPv4/IPv6)
- redirect limit(<=3)
- timeout(예: connect 3s, read 8s)
- max bytes(예: 2~5MB) 초과 시 중단
- redirect hop마다 URL 재검증(리다이렉트 기반 SSRF 방지)

- [x] **Step 5: Re-run SSRF tests (expect PASS)**

Run: `python -m pytest -q scripts/tests/test_web_preview_security.py`
Expected: PASS

- [x] **Step 6: Commit**

```bash
git add scripts/editor/source_fetch.py scripts/tests/test_web_preview_security.py requirements.txt requirements-dev.txt
git commit -m "feat(editor): add SSRF-safe fetch utility for web sources"
```

---

### Task 3B: HTML 정제(sanitize) + 링크 rewrite 유틸 (MVP-2)

**Files:**
- Create: `scripts/editor/html_sanitize.py`
- Create: `scripts/tests/test_html_sanitize.py`

- [x] **Step 1: Write failing tests for sanitize + rewrite**

케이스:
- `<script>`/`onload=` 등 제거
- `href="javascript:..."` 제거
- 상대 링크가 base URL 기준 절대 URL로 resolve
- `<a href>`가 `/api/source/preview?url=...`로 rewrite

> Attachment 처리 규칙: rewrite는 일단 **전부 preview로 통일**한다. 클릭된 URL이 **PDF**이면 `/api/source/preview`가 content-type을 보고 `/api/source/proxy`로 redirect한다. (proxy는 PDF 전용)

Run: `python -m pytest -q scripts/tests/test_html_sanitize.py`
Expected: FAIL

- [x] **Step 2: Implement sanitize pipeline (split)**

- (a) base URL resolve
- (b) `<a href>` rewrite → `/api/source/preview?url=...`
- (c) 위험 태그/속성 제거
- (d) `bleach` allowlist 최종 sanitize

- [x] **Step 3: Re-run tests (expect PASS)**

Run: `python -m pytest -q scripts/tests/test_html_sanitize.py`
Expected: PASS

- [x] **Step 4: Commit**

```bash
git add scripts/editor/html_sanitize.py scripts/tests/test_html_sanitize.py
git commit -m "feat(editor): add sanitized HTML preview rendering"
```

---

### Task 3C: Flask preview 엔드포인트 + 보안 헤더 + iframe sandbox 정합 (MVP-2)

**Files:**
- Modify: `scripts/editor/app.py`
- Modify: `scripts/editor/templates/index.html`

- [x] **Step 1: Implement `/api/source/preview`**

- `source_fetch`로 URL fetch
- content-type이 `text/html`이면 `html_sanitize`로 정제 후 반환
- content-type이 `application/pdf`이면 `/api/source/proxy?url=...`로 **redirect**
- content-type이 `application/octet-stream`이더라도, URL이 `.pdf`로 끝나거나(또는 헤더/매직바이트로 PDF로 식별 가능하면) PDF로 취급하여 proxy로 redirect
- 그 외 비-HTML(예: 이미지/zip 등)은 MVP에서는 프리뷰에서 “지원하지 않는 첨부” 에러로 표시하고, 필요 시 allowlist 확장
- `text/html; charset=utf-8`로 반환
- 보안 헤더:
  - `Content-Security-Policy` (preview 전용, remote resource 로드 금지)
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: no-referrer`

- [x] **Step 2: Tighten `preview-iframe` sandbox + link behavior decision**

결정(일관성, 명시):
- WEB preview는 **항상** same-origin `/api/source/preview`만 렌더
- `preview-iframe`는 **scripts 불허**
- 링크 클릭은 **iframe 안에서 이동**(새 탭 강제하지 않음)

> 이 플랜에서는 **iframe 안에서 이동**을 기본으로 하고, PDF는 브라우저가 iframe에서 열거나 다운로드하도록 둔다.

- [x] **Step 3: Manual check**

Run: `python scripts/editor.py`
Expected: WEB source 프리뷰가 뜨고, 링크 클릭이 최소한 “죽지 않고” 동작(iframe 내 이동/열림)

- [x] **Step 4: Commit**

```bash
git add scripts/editor/app.py scripts/editor/templates/index.html
git commit -m "feat(editor): serve sanitized web previews with safe iframe sandbox"
```

---

### Task 3D: `/api/source/proxy` 하드닝 + `downloads_folder` 정책 확정 (MVP-2)

**Files:**
- Modify: `scripts/editor/app.py`
- (Optional) Create: `scripts/tests/test_proxy_policy.py`

- [x] **Step 1: Define explicit proxy policy**

결정(명시적으로 고정):
- destination validation: preview와 **동일한 SSRF 검증** 적용
- request headers: 쿠키/인증 헤더 등 **절대 전달하지 않음**, 고정 User-Agent 사용
- methods: GET only
- max bytes/timeout: preview와 동일 또는 더 엄격
- content-type allowlist (초기): `application/pdf` + `application/octet-stream`(단, **PDF로 식별되는 경우만**) (첨부 파일 전용)
- redirect hop마다 재검증

- [x] **Step 2: Implement proxy policy + (가능하면) tests**

- [x] **Step 3: Decide and enforce `downloads_folder` rule**

결정(보안/단순성 우선):
- `downloads_folder`는 **repo_root 아래 경로만 허용** (예: `downloads/`)
- config에 절대경로가 들어오면 거부하고 안내(복사/이동 또는 repo 내 링크 사용)
- `/api/downloads`는 항상 repo_root 기준 **상대 경로**만 반환

> repo_root 정의: `scripts/editor/app.py`의 `repo_root()`(현재 `Path(__file__).parent.parent.parent`)를 단일 기준으로 사용한다.

- [x] **Step 4: Commit**

```bash
git add scripts/editor/app.py
git commit -m "fix(editor): harden proxy and restrict downloads folder"
```

---

### Task 3E: 프론트 WEB source 편집 UI 연결 + KASB 검증 (MVP-2)

**Files:**
- Modify: `scripts/editor/static/editor.js`
- Modify: `scripts/editor/static/editor.css`

- [x] **Step 1: Add WEB source editor controls**

- type 선택: `web`
- URL 입력 + “가져오기/새로고침”
- 프리뷰는 `iframe.src = /api/source/preview?url=...`

- [x] **Step 2: Error UX**

- 403/404/timeout → 프리뷰 영역에 메시지
- “원문 새 탭 열기”는 단순 링크(사용자 클릭)로 제공

- [x] **Step 3: Manual test with KASB**

Run: `python scripts/editor.py`
Expected:
- KASB URL도 프리뷰가 표시됨(본문 확인 중심)
- 첨부 PDF 링크가 동작(iframe 내에서 열리거나 다운로드)

- [x] **Step 4: Commit**

```bash
git add scripts/editor/static/editor.js scripts/editor/static/editor.css
git commit -m "feat(editor): wire web source preview UI"
```

---

### Task 4: CLIP SOURCE 저장소 (MVP-3)

**Files:**
- Create: `scripts/editor/clip_store.py`
- Modify: `scripts/editor/app.py`
- Modify: `scripts/editor/static/editor.js`
- (Optional) Create: `scripts/tests/test_clip_store.py`

- [x] **Step 1: Define clip storage format**

`scripts/editor/clips/<clip_id>.json`:
- `id`, `created_at`, `updated_at`
- `content_type` (`text/plain` 우선)
- `raw` (붙여넣기 내용)
- optional: `sha256`, `byte_length`, `title`, `source_url`

- [x] **Step 2: Add API to create/read clip**

`app.py`:
- `POST /api/clips` → clip 생성 후 `{id}` 반환
- `GET /api/clips/<id>` → clip 조회(프리뷰/검증용)

- [x] **Step 3: Add UI for CLIP source**

`editor.js`:
- SOURCE 타입 `clip` 선택
- 텍스트 붙여넣기 → `/api/clips`로 저장 → `source={type:'clip', ref:id}` 설정
- 우측 프리뷰는 clip을 **텍스트로 escape**해서 렌더(HTML 실행 금지)

- [x] **Step 4: Manual test**

Expected:
- 새로고침/재실행 후에도 clip id로 동일 내용 복원 가능

- [x] **Step 5: Commit**

```bash
git add scripts/editor/clip_store.py scripts/editor/app.py scripts/editor/static/editor.js
git commit -m "feat(editor): add clipboard source storage"
```

---

### Task 5: Backward compatibility + cleanup

**Files:**
- Modify: `scripts/editor/parser.py`
- Modify: `scripts/editor/saver.py`
- Modify: `scripts/editor/static/editor.js`
- Modify: `scripts/tests/test_parser.py`
- Modify: `scripts/tests/test_saver.py`

- [x] **Step 1: Update existing tests**

- `test_parser.py`: `<!-- pdf: ... -->` 케이스가 `source`로도 해석되는지 보강
- `test_saver.py`: 저장 결과가 `<!-- source: pdf|... -->`로 정규화되는지 기대값 갱신

- [x] **Step 2: Run full tests**

Run: `python -m pytest -q scripts/tests`
Expected: PASS

- [x] **Step 3: Commit**

```bash
git add scripts/tests/test_parser.py scripts/tests/test_saver.py scripts/editor/parser.py scripts/editor/saver.py scripts/editor/static/editor.js
git commit -m "test(editor): update tests for source marker migration"
```

---

## Acceptance Criteria (prioritized)

- **P0**
  - `SOURCE` 컬럼에서 PDF를 **검색으로** 선택 가능(대량 목록에서도 빠름)
  - `<!-- source: ... -->` 마커가 저장되고, 기존 `<!-- pdf: ... -->`는 읽히며 저장 시 정규화됨
  - WEB 소스는 iframe 차단과 무관하게 **서버 fetch 기반 프리뷰**가 뜬다
  - 프리뷰 HTML은 스크립트가 실행되지 않으며(정제), 링크는 동작한다(iframe 내 이동 + 필요 시 proxy로 redirect)
  - URL fetch는 SSRF 기본 방어(스킴/localhost/사설IP/리다이렉트/타임아웃/크기 제한)

- **P1**
  - 최근 PDF 소스가 제공되어 반복 선택이 빨라진다
  - CLIP 소스가 별도 저장소에 저장되고 id로 재참조된다

- **P2**
  - WEB 프리뷰에서 상대 링크/첨부 링크 rewrite가 안정적으로 동작한다
  - 프리뷰 에러 상태(403/404/timeout)가 UI에 명확히 표시된다

