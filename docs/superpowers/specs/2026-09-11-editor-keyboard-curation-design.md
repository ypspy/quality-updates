# 큐레이션 편집기 — 행 단위 키보드 UX

**날짜**: 2026-09-11  
**상태**: 설계 합의 (파일 검토 대기)  
**범위**: `scripts/editor` 목록 탐색·처리 단축키, 미리보기 첨부 클릭 시 iframe 유지, 다운로드 목록 최신순  
**선행**: [2026-03-24-quality-updates-editor-design.md](2026-03-24-quality-updates-editor-design.md), [2026-03-25-editor-pdf-picker-design.md](2026-03-25-editor-pdf-picker-design.md)

---

## 개요

분기 큐레이션은 링크를 한 줄씩 보고 상태(미결정/스킵/요약 없음/요약 필요)를 고른 뒤, 요약 필요면 PDF·WEB·CLIP을 붙이는 일이다. 지금은 행마다 제목·배지·출처 탭·입력·버튼이 각각 Tab 정거장이라, 다음 항목으로 가려면 칸을 여러 번 밟아야 한다.

**목적**: 선택 행 기준으로 키보드만으로 탐색·미리보기·상태·출처 종류를 처리하고, 첨부 저장이 원문 미리보기를 덮어쓰지 않게 한다.

---

## 브레인스토밍 합의

| 항목 | 결정 |
|------|------|
| 처리방법 (Space) | 배지와 동일 4상태 순환: 미결정 → 스킵 → 요약 없음 → 요약 필요 |
| 좌·우 | **요약 필요**일 때만 출처 탭 PDF ↔ WEB ↔ CLIP. 검색·캡쳐·붙여넣기는 실행하지 않음 |
| 모드 | 행 모드 / 출처 편집 모드. `Tab` 진입, `Esc` 복귀 |
| Enter 미리보기 | 포커스는 선택 행에 유지. iframe으로 넘기지 않음 |
| 미리보기 안 클릭 | 첨부(파일)만 가로채 저장+토스트. HTML 링크는 iframe 내 이동 허용 |
| 구현 뼈대 | 행 단위 **roving tabindex**. 전역 문자 단축키(`C` 캡쳐 등)는 하지 않음 |
| PDF 목록 | 파일 수정 시간 **최신순**. 검색은 필터만 하고 그 순서를 유지 |

마우스 클릭(행·배지·탭·버튼·미리보기 링크)은 기존과 같이 동작한다. 행(또는 제목)을 클릭하면 그 행을 선택한다. 제목 클릭은 지금처럼 미리보기도 연다. 키보드는 추가 동선이지 마우스 대체가 강제이지 않다. 다만 Tab 순서는 행 단위로 바꿔, Tab으로 모든 칸을 밟지 않게 한다.

---

## 범위 외

- 미리보기 iframe **안** 키보드 조작 (스크롤·링크 포커스)
- PDF 원문 렌더링
- 요약 자동 생성, 크롤러, MkDocs 배포
- 전역 문자 단축키, 명령 팔레트
- `aria-activedescendant` 리스트박스 패턴 (행 안에 출처 입력이 있어 채택하지 않음)
- 저장·폴더 변경·다운로드 비우기 헤더 단축키

---

## 1. 아키텍처

포커스와 키 해석은 `scripts/editor/static/editor.js`가 맡는다. 상태·출처 데이터 모델과 저장 API는 바꾸지 않는다.

```text
행 모드 (선택 tr tabindex=0)
  ↑↓     선택 행 이동 (기관 헤더 tr 건너뜀, 미리보기 자동 로드 없음)
  Enter  선택 행 URL → 우측 미리보기, 포커스 행 유지
  Space  상태 4순환 (완료는 무시)
  ←→     요약 필요일 때만 sourcePanel PDF/WEB/CLIP
  Tab    해당 행 활성 출처 칸으로 → 출처 편집 모드
  Shift+Tab  헤더(파일 선택 등)

출처 편집 모드 (활성 패널 첫 컨트롤에 포커스)
  기존 PDF 피커 키 (↓ 열기, ↑↓ 이동, Enter 선택, Esc 피커 닫기)
  Esc    피커 열려 있으면 닫기만, 아니면 행 모드 복귀
  ↑↓     행 이동에 쓰지 않음 (입력·피커가 사용)
```

**Roving tabindex**

- 링크 행 `<tr>`만 목록의 Tab 정거장이다. 선택 행 `tabindex="0"`, 나머지 링크 행 `tabindex="-1"`.
- 제목 `.title-link`, 상태 배지, 출처 탭·버튼은 **행 모드에서 `tabindex="-1"`** (마우스는 동작).
- 출처 편집에 들어간 뒤에만 그 행의 활성 패널 컨트롤이 Tab 순서로 살아난다.
- 기관 섹션 헤더 행은 포커스·선택 대상이 아니다.

선택 식별자는 `linksData` 인덱스와 `line_index`다. `renderTable()`·저장 후 재파싱·PDF 목록 갱신 뒤에는 **같은 `line_index` 행**을 다시 선택하고, 행 모드면 그 `tr`에 포커스를 되돌린다. 해당 줄이 없으면 첫 링크 행.

---

## 2. 키맵 상세

### 행 모드에서만 해석

단축키는 다음일 때 **쓰지 않는다**.

- 포커스가 헤더 컨트롤(`#file-select`, 헤더 버튼)에 있을 때
- 출처 편집 모드일 때 (해당 컨트롤·피커가 키를 가짐)
- `contenteditable` / `textarea` / `input` / `select`에 포커스가 있을 때 (헤더·출처 편집 공통)

`Space`는 `preventDefault`로 페이지 스크롤을 막는다. `↑` `↓`도 행 모드에서는 왼쪽 패널이 아니라 **선택 이동**이다. 선택 행이 보이도록 `scrollIntoView({ block: 'nearest' })`.

### 상태 순환 (Space)

기존 `STATE_CYCLE`: `undecided → skip → no_summary → needs_summary → undecided`.

- `done`: Space 무시. 위·아래·Enter는 가능.
- `needs_summary`가 아닌 상태로 바뀌면 지금과 같이 `source` / `pdf_path` / `clipDraft`를 비우고 `sourcePanel`은 `pdf`.
- 순환 후 전체 테이블을 다시 그려도 **선택 행을 유지**한다. (지금은 `cycleState`가 `renderTable()`만 호출해 포커스가 사라진다.)

### 출처 종류 (← →)

상태가 `needs_summary`가 아니면 무시한다. `done`도 무시한다.

순환 순서: `pdf → web → clip → pdf`. 기존 `setSourceKind`를 호출해 탭·패널만 바꾼다. WEB 미리보기 로드, PDF 피커 열기, 캡쳐는 하지 않는다.

### 출처 편집 진입 (Tab)

1. 선택 행이 `done`이거나 출처 칸이 없으면 출처 편집으로 들어가지 않는다. 기본 Tab(헤더 등)만 따른다.
2. 그 외: `preventDefault` 후 활성 종류(`sourceKind`) 패널의 첫 컨트롤에 포커스.
   - PDF: `.source-input` (없으면 안내 문구만 있는 행은 편집 진입 취소, Tab 기본 동작)
   - WEB: `.web-btn-preview`
   - CLIP: `.clip-draft`
3. 출처 편집 중 그 행 패널 안의 컨트롤끼리만 Tab으로 이동한다. 다른 행의 버튼으로는 가지 않는다.
4. 출처 편집에서 `Shift+Tab`이 패널 첫 컨트롤을 벗어나면 행 모드로 복귀하고 선택 `tr`에 포커스.

### Enter 미리보기

`openPreview(link.url)` (또는 이미 CLIP이 연결된 행에서 미리보기가 CLIP이어야 하는 기존 버튼 동작은 **마우스/출처 편집의 「미리보기」 버튼**에 맡긴다). 행 모드 Enter는 **원문 URL** 미리보기만 한다.

iframe `src`를 바꿔도 `focus()`는 선택 행에 둔다. iframe `tabindex="-1"`로 두어 Tab이 iframe으로 빠지지 않게 한다.

---

## 3. 미리보기 첨부 · 토스트

### 문제

미리보기 HTML의 외부 링크는 `/api/source/preview?url=…`로 다시 쓰인다. 첨부(PDF·HWP·zip 등)를 누르면 iframe이 저장용 빈 페이지로 바뀌고, `postMessage` 경로가 성공 시 iframe을 `about:blank`로 비운다. 원문이 사라진다.

KASB `kasb_file` 등은 클릭을 가로채 JSON 저장하는 길이 있으나, 모든 첨부·저장 후 화면 유지가 아니다.

### 규칙

1. **첨부(파일) 클릭**: iframe 내비게이션을 막는다. 부모가 `save_fetched` / `kasb_file`(기존 프록시)로 저장하고 토스트한다. **현재 HTML 미리보기 `src`를 유지**한다. `clearIframeOnSuccess`는 쓰지 않는다 (`about:blank` 금지).
2. **본문 HTML 링크**: iframe 안에서 이동을 허용한다. 그 이동 결과가 다시 파일이면 1과 같다.
3. 파일 판별은 기존 `should_auto_download_fetched` / `save_fetched_allowed`와 같다 (PDF·Zip·Office·이미지 등, HTML/JSON·`text/*` 제외).
4. 클릭을 놓쳐 iframe이 저장용 stub 페이지를 로드한 경우: 저장+토스트 후 **직전 미리보기 URL로 되돌린다**. 빈 화면으로 두지 않는다.

캡쳐(`web_capture_to_clip`) 성공·실패는 차단 `alert` 대신 같은 토스트를 쓴다. 스크린샷만 성공한 부분 성공은 기존처럼 출처를 `shot`으로 연결하고, 안내도 토스트로 낸다.

### 토스트

기존 `#editor-toast`를 유지한다. 표시 시간은 **2.5초** (`1000ms` → `2500ms`). 다운로드 성공/실패, 캡쳐 성공/실패 메시지를 이 한 경로로 낸다.

첨부 저장 후 `loadPdfFiles()`는 하되, 선택 행·포커스·미리보기 `src`를 유지한다. 필요하면 행 HTML만 출처 칸을 갱신하고, 선택 상태를 지우는 전체 `renderTable()`은 피하거나 직후 선택을 복구한다.

---

## 4. PDF 목록 최신순

`GET /api/files`와 같이 `GET /api/downloads`는 `st_mtime` **내림차순**이다. 같은 시각이면 경로 소문자로 안정 정렬한다.

피커:

- 검색어 없음: `localStorage` 「최근 사용」 섹션(기존) 아래 「전체」는 API 순서 그대로.
- 검색어 있음: 파일명 정규화 부분일치 **필터만**. exact/prefix/localeCompare로 다시 정렬하지 않는다. API 최신순이 유지된다.

`scripts/tests/test_downloads_folder_policy.py`의 `test_downloads_list_default_folder`는 현재 가나다순을 고정한다. mtime을 심고 최신순을 assert 하도록 바꾼다.

---

## 5. 컴포넌트 · 데이터 흐름

| 단위 | 역할 | 의존 |
|------|------|------|
| 선택 상태 (`selectedIdx` + `line_index`) | 어떤 링크 행이 키보드 대상인지 | `linksData` |
| 모드 (`row` / `source-edit`) | 키 해석 분기, Tab 정거장 | 선택 행 DOM |
| `cycleState` / `setSourceKind` | 기존 상태·출처 패널 | 저장 페이로드 불변 |
| `openPreview` | 우측 iframe | 포커스를 iframe에 넘기지 않음 |
| iframe 클릭 위임 | 첨부 → 부모 fetch+토스트, HTML은 통과 | `/api/source/save_fetched`, `kasb_file` |
| `list_downloads` | mtime 최신순 경로 배열 | `downloads_folder` |

저장 스키마(`undecided`/`skip`/`no_summary`/`needs_summary`/`done`, `<!-- source -->`)는 이 스펙에서 바꾸지 않는다.

---

## 6. 오류 처리

| 상황 | 동작 |
|------|------|
| 첨부 저장 HTTP 실패 | 토스트에 서버 `message`. 미리보기 유지 |
| 캡쳐 실패 | 토스트. 가능하면 부분 성공(스크린샷만) 기존 연결 로직 유지 + 토스트 |
| PDF 폴더 없음 / 파일 없음 | 출처 편집 Tab 진입 실패 → 행 모드 유지 |
| 파일 전환 | 선택 인덱스 0, 행 모드. iframe `src`는 기존 `loadLinks`처럼 건드리지 않음 |
| 피커 연 채 행 이동 | 행 모드 단축키가 꺼져 있으므로 발생하지 않음. `Esc`로 닫고 행 모드 |

---

## 7. 테스트

**자동화 (`scripts/tests/`)**

- `GET /api/downloads` mtime 최신순 (mtime를 명시적으로 다르게 설정).
- 첨부 저장 성공 경로가 iframe을 `about:blank`로 바꾸라는 신호를 주지 않는지 (헬퍼/`clearIframeOnSuccess` 제거 후 회귀). 클릭 위임은 JS라 서버 테스트로 못 보면, stub 응답이 미리보기를 대체하지 않는 계약을 문서·헬퍼 단위로 고정.
- 기존 sanitize, preview, save, downloads 정책 테스트 유지.

**수동 (편집기 한 분기 파일)**

1. 위·아래로 행만 이동, Tab으로 칸을 전부 밟지 않음.
2. Enter로 미리보기, 이어서 Space·화살표가 목록에서 동작 (iframe이 키를 가져가지 않음).
3. Space 4상태 순환, 완료 행은 상태 불변.
4. 요약 필요에서 ← → 가 PDF/WEB/CLIP만 바꿈.
5. Tab → PDF 검색 → Esc → 행 모드 → 위·아래.
6. 미리보기에서 첨부 클릭 → 토스트, 원문 HTML 유지, 피커 「전체」 맨 위에 그 파일.
7. 본문 HTML 링크는 iframe에서 이동.

---

## 8. 변경 파일 (예상)

```
scripts/editor/static/editor.js
scripts/editor/static/editor.css          # 선택 행 강조
scripts/editor/templates/index.html      # iframe tabindex 등 최소
scripts/editor/routes/files.py           # list_downloads mtime 정렬
scripts/editor/preview_helpers.py        # stub 저장 후 화면 비우기 금지에 맞춰 필요 시
scripts/tests/test_downloads_folder_policy.py
docs/project/editor-curation-workflow.md # 구현 후 키보드·토스트·목록 순서 한 절
```

`editor.css` 선택 행은 기존 `tr.state-needs` 파란 배경과 겹쳐도 **아웃라인 또는 왼쪽 강조선**으로 구분한다. 상태 색을 대체하지 않는다.

---

## 성공 기준

- Tab 없이 ↑↓만으로 링크 행을 순회할 수 있다.
- Enter / Space / ←→ / Tab / Esc가 위 표대로 동작한다.
- 첨부 저장 후 원문 미리보기가 남아 있고 토스트가 2.5초 보인다.
- 방금 받은 파일이 PDF 피커 「전체」 상단에 온다.
- 기존 큐레이션 저장 마커·sidecar 계약이 그대로다.
