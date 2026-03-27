# 큐레이션 편집 도구 — SOURCE(근거) 선택 UX 개선 스펙

## Background

`scripts/editor` 로컬 편집 도구에서 링크별 “근거(Source)”를 연결할 때, 소스 파일/URL이 많아지면 원하는 항목을 찾는 시간이 작업 전체의 병목이 된다.

또한 일부 사이트(예: 한국회계기준원)는 `iframe` 로 프리뷰가 차단되므로, 링크 내용을 확인하려면 **서버가 HTML을 fetch해서 정제 렌더링**하는 프리뷰가 필요하다.

현재 UI는 각 행에서 `<select>`로 PDF 파일만 선택할 수 있으며, 웹 페이지 fetch나 클립보드(직접 붙여넣기) 같은 소스 타입을 표현하기 어렵다.

## Scope

- **In scope**
  - 테이블의 `PDF` 컬럼을 `SOURCE` 컬럼으로 변경 (소스 타입: PDF / WEB / CLIP)
  - PDF 선택 UI를 **검색 가능한 피커(콤보박스)** 로 교체
  - WEB 소스: URL을 서버가 fetch하여 **정제된 HTML 프리뷰** 제공(iframe 의존 제거)
  - CLIP 소스: 사용자 붙여넣기 텍스트/HTML을 **별도 저장소에 저장**하고 ID로 참조
  - “최근 사용” 탭(또는 섹션) 제공
  - 키보드 중심 플로우(포커스/이동/선택/닫기)
  - 대량 PDF에서도 체감 성능 유지(클라이언트 필터 + 결과 제한)
  - 소스가 설정되면 `needs_summary`로 전환하는 규칙은 유지

- **Out of scope**
  - PDF 원문 렌더링/미리보기(별도 기능으로 추후)
  - 링크 요약(Phase 1/2) 자동 생성 로직(Claude Code 워크플로우의 영역)
  - 서버/DB 도입(현 단계에서는 단일 Flask + 정적 자원 유지)

## Current System Snapshot

- **Backend**: Flask
  - `GET /api/downloads` → `downloads_folder` 아래 `*.pdf` 파일 목록 반환(문자열 경로 배열)
  - `POST /api/save` → `curation`을 받아 마크다운에 반영(백업 포함)
  - `GET/POST /api/config` → `downloads_folder`, `last_file`

- **Frontend**: Vanilla JS
  - `pdfDropdown()`에서 `<select class="pdf-select">` 렌더
  - 선택 시 `pdf_path` 설정 + `needs_summary`로 전환

## Design Goals (Success Criteria)

- **Speed**: PDF 200~1000개 수준에서도 “키 몇 번 + Enter”로 선택 완료
- **Low error**: 잘못 선택/선택 누락을 쉽게 발견하고 수정 가능
- **Flow**: 마우스 없이도 처리 속도가 올라가도록 키보드 동선 제공
- **No surprise**: 기존 데이터 모델/저장 규칙을 최대한 유지
- **Preview reliability**: `iframe` 차단 사이트에서도 “내용 확인”이 가능해야 함(서버 fetch 기반)

## Proposed UX

### 0) Column rename: PDF → SOURCE

테이블의 `PDF` 컬럼을 `SOURCE`로 변경하고, 각 행은 다음 중 하나의 소스 타입을 가질 수 있다.

- **PDF**: 로컬 폴더(`downloads_folder`)의 PDF 파일
- **WEB**: 링크 URL(또는 별도 URL)을 서버가 fetch한 HTML
- **CLIP**: 사용자가 직접 붙여넣은 텍스트/HTML (별도 저장소에 저장)

### 1) PDF Picker (ComboBox) — SOURCE 타입이 PDF일 때

각 링크 행의 “PDF” 셀을 다음 형태로 구성한다.

- **Default view**
  - `input` (placeholder: `PDF 검색: 파일명/날짜/키워드`)
  - 우측에 “▼” 또는 “최근” 버튼(마우스 진입점)

- **Dropdown panel**
  - 상단: 탭 `최근` / `전체`
  - 본문: 결과 리스트(최대 10~12개 렌더, 스크롤)
  - 항목 표시:
    - 1줄: 파일명(굵게, 매칭 하이라이트)
    - 2줄(작게): 수정일(가능하면) / 폴더(옵션)

### 2) Matching / Filtering Rules

클라이언트에서 빠르게 필터링한다.

- 입력은 **대소문자 무시**
- 공백/하이픈/언더스코어 차이는 무시(정규화)
- 기본은 부분일치(contains)
- 결과 정렬:
  - 1순위: 접두/완전 일치
  - 2순위: 포함 위치가 앞에 있을수록
  - 3순위: 수정일 최신(메타가 있으면)

### 3) Keyboard Flow

- **포커스**
  - 현재 행 PDF 입력 포커스: `Ctrl+K` (또는 `/`) — 전역 단축키
  - 탭 이동: `Tab` / `Shift+Tab` (기본)

- **드롭다운 조작**
  - 열기: 입력 포커스 상태에서 `ArrowDown`
  - 이동: `ArrowUp/Down`
  - 선택: `Enter`
  - 닫기: `Esc`

### 4) State Rules

- SOURCE 설정 시(어떤 타입이든):
  - `linksData[idx].source = { type, ref }`
  - `linksData[idx].state = 'needs_summary'`
- SOURCE 해제(비우기) 시:
  - `linksData[idx].source = null`
  - `linksData[idx].state = 'undecided'`

> Note: 현재 구현은 “비우기” 시 상태를 자동 변경하지 않으므로, 이 스펙은 **행동을 명시적으로 변경**한다.

### 5) “최근 사용” (Recents)

PDF 선택 UX 가속을 위해 최근 목록을 제공한다.

- 저장 위치(우선순위)
  - 1안: 브라우저 `localStorage` (사용자별, 빠르고 단순)
  - 2안: `editor_config.json`에 `recent_pdfs` 추가(환경 공유 필요 시)

- 동작
  - PDF 선택 시 top N(예: 10)로 갱신
  - `최근` 탭은 입력이 비어 있을 때 기본 노출
  - 기준은 **전체 경로(path) 단위**로 dedupe (동일 파일명이 다른 폴더에 있을 수 있음)

## API Changes (minimal)

### Source marker (Markdown) — recommended direction

현재는 링크 바로 아래에 `<!-- pdf: ... -->` / `<!-- skip -->` 같은 코멘트로 상태를 표현한다.

소스 타입 일반화를 위해 다음 마커로 전환한다.

- `<!-- skip -->` (유지)
- `<!-- source: <type>|<ref> -->` (신규, PDF/WEB/CLIP 통일)
  - 예: `<!-- source: pdf|downloads/foo.pdf -->`
  - 예: `<!-- source: url|https://kasb.or.kr/... -->`
  - 예: `<!-- source: clip|clip_20260325_abcdef -->`

> Migration: 기존 `<!-- pdf: ... -->`는 파서가 `source: pdf|...`로 읽도록 호환 처리(점진적 전환).

### Option A (no API change, simplest)

- 현재 `GET /api/downloads`가 문자열 배열만 반환
- 프론트는 파일명만으로 검색/정렬/최근 제공
- 수정일/크기 기반 정렬은 불가(또는 추정)

### Option B (recommended if easy): include metadata

`GET /api/downloads` 응답을 확장:

```json
[
  { "path": "downloads/foo.pdf", "name": "foo.pdf", "mtime": 1710000000, "size": 1234567 }
]
```

장점: 최신 파일 우선, 검색 결과에서 보조 정보 제공 가능.

### WEB Preview (iframe 차단 대응)

`iframe`이 막힌 사이트(예: 한국회계기준원) 및 일반 사이트에서도 동일한 방식으로 프리뷰를 제공한다.

- `GET /api/source/preview?url=<...>`:
  - 서버가 URL HTML을 fetch
  - **정제된 HTML**을 반환 (스크립트 제거, 인라인 이벤트 제거, 리소스 최소화)
  - 본문 내 링크가 동작하도록 `<a href>`를 **프록시 URL**로 rewrite
    - 예: `/api/source/proxy?url=<encoded>`

- `GET /api/source/proxy?url=<...>`:
  - 첨부 PDF/다운로드 링크 또는 다음 페이지 링크를 서버가 fetch하여 전달
  - Content-Type을 보존하고, 브라우저가 새 탭에서 열거나 다운로드할 수 있도록 함

정제는 “요약 작업에 필요한 콘텐츠 확인”이 목적이므로, 레이아웃/스타일 재현보다 **본문 가독성 + 링크 동작**을 우선한다.

### CLIP Storage (별도 저장소)

클립보드 소스는 마크다운에 인라인 저장하지 않고, 에디터가 관리하는 별도 저장소에 저장한다.

- 저장 위치(예시): `scripts/editor/clips/`
  - 파일: `<clip_id>.json` (본문, mime, created_at, source_url(optional) 등)
- 마크다운에는 `<!-- source: clip|<clip_id> -->`만 저장
- 장점: 문서 파일이 커지지 않고, 소스 관리/재사용/정리가 쉬움

## Open Questions (decide before implementation)

- 전역 단축키는 `Ctrl+K` / `/` 중 무엇을 기본으로 할지? (브라우저/OS 단축키와 충돌 가능)
- “최근”을 탭으로 분리할지, 결과 리스트 상단 섹션으로 노출할지?
- `downloads_folder`가 절대경로일 때, UI에 폴더 표시를 어디까지 보여줄지? (기본은 숨김, hover에서만 권장)

## Implementation Notes

- 렌더 성능을 위해 각 행마다 무거운 DOM을 만들기보다:
  - 1) “활성 행”에서만 드롭다운을 펼치거나
  - 2) 피커 컴포넌트를 재사용(overlay)하는 방식 고려
- `renderTable()`의 전체 재렌더링은 단축키/포커스 유지에 불리하므로
  - 행 단위 업데이트 또는 “상태/선택 변경”만 부분 업데이트하는 방향을 선호

## Edge Cases

- `downloads_folder`에 PDF가 0개인 경우: 현재처럼 안내 텍스트 유지
- 파일명에 한글/특수문자 포함: 정규화/이스케이프 유지
- 경로 구분자(`\` vs `/`): 현재 옵션 생성에서 이미 처리 중 (`split(/[\\/]/)`)
- 저장 전 변경 표시: 선택 변경 시 행에 “dirty” 표시(스타일)로 실수 방지
- URL fetch 실패(403/404/timeout/CORS 등): 프리뷰 영역에 에러 메시지 + “새 탭 열기” 제공
- 상대 링크/첨부 링크가 많은 페이지: rewrite가 누락되지 않도록 base URL 기준 처리

## Test Plan (manual)

- PDF 0개 / 20개 / 500개 환경에서 검색/선택 체감 확인
- 키보드만으로 “행 이동 → PDF 선택 → 다음 행” 반복 가능 확인
- PDF 선택/해제에 따른 상태 전이가 기대대로 되는지 확인
- 저장 시 payload가 기존과 호환되는지 확인
- KASB 등 iframe 차단 사이트에서 프리뷰가 정상 표시되는지 확인
- 프리뷰 내 PDF/첨부 링크 클릭이 동작하는지 확인

## References

- `scripts/editor/templates/index.html`
- `scripts/editor/static/editor.js`
- `scripts/editor/static/editor.css`
- `scripts/editor/app.py`

