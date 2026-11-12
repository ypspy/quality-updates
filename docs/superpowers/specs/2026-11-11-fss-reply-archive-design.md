# 금감원 질의회신 아카이브 — 설계 스펙

**날짜**: 2026-11-11  
**상태**: 승인됨 (2026-11-12)  
**범위**: 금융감독원 질의회신 요약 게시판 두 곳을 항목 폴더로 입수해 이 저장소에 보관한다. 사이트에는 게시하지 않는다. 옵시디안은 `item.md`만 `raw/`로 복사한다.

---

## 개요

분기 문서와 사이트는 질의회신을 알리는 보도자료만 다룬다. 회신 본문은 금감원 게시판 첨부에 있다. 게시판을 사이트에 미러링하지 않고, 항목마다 메타데이터·추출 텍스트·원본 첨부를 남긴다.

대상은 두 게시판이다.

| 코드 | 이름 | menuNo | 목록 |
|------|------|--------|------|
| B0000132 | K-IFRS 질의회신요약 | 200442 | `https://www.fss.or.kr/fss/bbs/B0000132/list.do?menuNo=200442` |
| B0000133 | 일반기업회계기준 질의회신요약 | 200443 | `https://www.fss.or.kr/fss/bbs/B0000133/list.do?menuNo=200443` |

옵시디안 볼트(`C:\dev\obsidian-vault`)는 그 마크다운을 `raw/fss-replies/{board}/{nttId}.md`로 가져간다. 위키 합성은 이 스펙 밖이다.

**목적**

- 두 게시판을 `board`와 `nttId` 단위로 저장한다.
- 다시 실행하면 이미 받은 항목은 건너뛴다.
- PDF 본문은 `pypdf`로 추출한다. HWP와 HWPX는 원본만 남기고 Whale 변환 대기로 표시한다.
- `item.md`만 옵시디안 `raw/`에 복사하고, 이미 있는 파일은 덮어쓰지 않는다.

**범위 외**

- B0000134 과거 국제회계기준 Q&A. 목록 밖에 링크가 있어도 요청하지 않는다.
- 그 밖의 금감원 게시판, 한공회, KASB 게시판
- 한글 프로그램, LibreOffice, Whale 호출. HWP 본문 파서
- 분기 `crawl.py`, `scripts/crawler/KASB.py`, `scripts/crawler/unified.py`, `scripts/crawler/FSS.py`
- `docs/quality-updates/`, `quality-updates-writer`, MCP `export_corpus.py`, `data/corpus/`
- MkDocs nav, `docs/index.md`, 질의회신 본문의 사이트 게시
- CI의 라이브 크롤. 테스트는 `fss.or.kr`에 접속하지 않는다.
- 게시판 전체를 구현 작업 중에 받아 `data/fss-replies/`를 채워 커밋하는 일. 수집은 구현 후 운영자가 실행한다.

---

## 배경·현황

| 영역 | 상태 |
|------|------|
| 금감원 보도·회계감독 동향 | `scripts/crawler/FSS.py`. 목록 링크만 분기 문서에 넣는다. 이 스펙은 그 파일을 바꾸지 않는다. |
| KASB 질의회신 아카이브 | `scripts/crawler/kasb_replies.py`. 폴더·`item.md`·manifest·복사 방식을 맞춘다. import해서 섞지 않는다. |
| B0000132·B0000133 | 미수집. 저장해 둔 1페이지는 데이터 행 10건이다. 페이지는 `pageIndex`(1부터)이고, 항목이 없는 페이지에서 멈춘다. |
| 상세 | 같은 시스템의 `view.do`. 키는 `nttId`와 `menuNo`. |
| 첨부 | 저장해 둔 상세의 `fileDown.do`. 쿼리는 `menuNo`, `atchFileId`, `fileSn`, 빈 `bbsId`. |
| 옵시디안 | `raw/`는 불변 원본. 위키 합성은 이 스펙 밖이다. |

선택자와 다운로드 인자는 운영자가 브라우저에서 HTML만 저장한 페이지에서 확정했다. 커밋하는 fixture는 그 페이지의 게시판 표와 상세 블록만 남긴 것이다. 상세의 문의 전화번호는 fixture에서 뺐다. PDF와 HWP가 한 항목에 같이 있는 저장 페이지는 없었고, 그 경우는 합성 HTML로 테스트한다.

---

## 아키텍처

### 변경 파일

```text
scripts/crawler/fss_replies.py           # 목록·상세 파서, 추출, 저장, 복사
scripts/crawl_fss_replies.py             # 수집 CLI. 구현 함수만 호출한다
scripts/export_fss_replies_raw.py        # item.md → 옵시디안 raw
scripts/tests/test_fss_replies.py        # fixture 단위 테스트
scripts/tests/fixtures/fss_reply_*.html  # 목록 2, 상세 2
scripts/tests/fixtures/fss_reply_*.pdf   # 글이 있는 PDF, 빈 PDF
docs/superpowers/README.md               # 이 스펙 색인
```

`scripts/crawler/KASB.py`, `scripts/crawler/FSS.py`, `scripts/crawler/unified.py`, `scripts/crawl.py`는 변경하지 않는다. `kasb_replies`를 import하지 않는다.

사이트 원본은 `docs/`다. 아카이브는 `data/fss-replies/`에 두므로 MkDocs 빌드에 포함되지 않는다. 이 경로는 gitignore하지 않는다. 이번 변경은 그 디렉터리를 채우지 않는다.

### 디렉터리

```text
data/fss-replies/
  manifest.jsonl
  B0000132/{nttId}/
    item.md
    {원본 파일명}
  B0000133/{nttId}/
    item.md
    {원본 파일명}
```

키는 게시판 코드와 `nttId`다. `nttId`는 `view.do`의 질의 인자다. 파일명에 경로 구분자가 있으면 제거하고, Windows에서 파일명으로 쓸 수 없는 문자는 `_`로 바꾼다. 같은 폴더에서 이름이 겹치면 `{stem}-{file_sn}{suffix}`로 저장한다.

### 데이터 흐름

```text
crawl_fss_replies.py
  → 선택한 게시판의 목록 pageIndex=1부터
  → 데이터 행이 없으면 그 게시판을 멈춘다
  → board+nttId 단위로 중복 제거
  → 완료 항목은 상세·다운로드를 생략
  → GET view.do
  → PDF가 있으면 PDF만 GET fileDown.do
  → PDF가 없으면 HWP/HWPX를 그대로 저장
  → item.md
  → manifest.jsonl 에 한 줄 추가

export_fss_replies_raw.py
  → {archive}/{board}/{nttId}/item.md
  → {dest}/{board}/{nttId}.md
  → 대상 파일이 있으면 생략
```

목록을 매 실행 처음부터 읽는다. 새 글은 1페이지에 붙기 때문이다. 상세와 다운로드만 완료된 항목에서 생략한다.

---

## 수집

### 목록

GET `https://www.fss.or.kr/fss/bbs/{board}/list.do`, 질의 `menuNo`, `pageIndex`. `pageIndex`는 1부터다.

저장해 둔 목록의 열은 다음과 같다.

| 게시판 | 열 |
|--------|----|
| B0000132 | 번호, 관련기준서, 제목, 담당부서, 등록일, 첨부파일, 조회수 |
| B0000133 | 번호, 제목, 담당부서, 등록일, 첨부파일, 조회수 |

제목 링크 `/fss/bbs/{board}/view.do?nttId={nttId}&menuNo={menuNo}`에서 `board`, `nttId`, `menuNo`를 읽는다. `pageIndex`는 상세 주소에 넣지 않는다. 관련기준서는 `<br>`로 나뉜 문자열 목록이다. B0000133에는 그 열이 없으므로 `standards`는 `[]`다. 첨부 이름은 `span.name`이고, 다운로드 식별자는 `atchFileId`와 `fileSn`이다.

표 밖의 B0000134 링크는 행으로 읽지 않는다. `--board B0000132`는 B0000133과 B0000134 목록을 요청하지 않는다. `all`이어도 B0000134는 포함하지 않는다.

### 상세

GET `https://www.fss.or.kr/fss/bbs/{board}/view.do?nttId={nttId}&menuNo={menuNo}`.

`.krds-bd-view`에서 제목, 담당부서, 등록일, 안내 문장, 첨부를 읽는다. 안내 문장은 `.dbdata` 또는 `.n-dbdata`다. 그 안의 script는 본문에 넣지 않는다. 메뉴·바닥글·조회수·담당팀·문의 전화번호는 프론트매터에 넣지 않는다.

첨부 링크는 `fileDown.do`만 본다. `문서뷰어`(`docView`)와 글자가 `다운로드`인 중복 링크는 같은 `atchFileId`+`fileSn`으로 한 건이다. 파일명에 붙어 있는 `(파일크기: …)`는 뗀다.

### 다운로드

GET `https://www.fss.or.kr/fss/cmmn/file/fileDown.do`, 질의 `menuNo`, `atchFileId`, `fileSn`, `bbsId`. 저장해 둔 링크의 `bbsId`는 비어 있으므로 빈 문자열을 보낸다. 이 쿼리는 저장 HTML에 있던 이름만 쓴다.

세션 User-Agent는 `Mozilla/5.0 (Windows NT 10.0; Win64; x64)`이다.

같은 항목에 PDF와 HWP/HWPX가 같이 있으면 PDF만 받아 저장한다. HWP는 받지 않는다. PDF가 없으면 HWP/HWPX를 그대로 저장한다. `pypdf`로 HWP를 열지 않는다.

`item.md`는 받을 첨부를 디스크에 저장한 뒤 상태까지 매겼을 때만 쓴다. 목록 파싱 이후의 상세 조회나 다운로드가 실패하면 `item.md`를 만들지 않는다.

### 요청 간격과 실패

`--delay` 기본값 0.3초. `fss.or.kr` 요청 사이에 둔다. 한 항목의 HTTP 오류는 그 항목만 manifest에 적고 다음 항목으로 넘어간다.

`--limit N`은 이번에 새로 받거나 다시 시도하는 항목 수다. 건너뛴 완료 항목은 세지 않는다. 생략하면 선택한 게시판의 목록 전체를 처리한다.

### 건너뛰기

기본 실행은 아래를 모두 만족하는 항목을 완료로 보고 상세·다운로드를 하지 않는다.

- `item.md`가 있다.
- 프론트매터의 첨부 파일이 모두 디스크에 있다.
- `extract_status`가 `ok` 또는 `pending_whale`이다.

파일이 빠졌거나 `item.md`가 없으면 다시 시도한다. `--retry-failed`는 `failed`와 `empty`만 다시 시도한다. `ok`와, 파일이 있는 `pending_whale`은 다시 받지 않는다. `pending_whale`은 실패가 아니다.

---

## item.md

UTF-8. 프론트매터는 YAML.

```yaml
---
board: "B0000132"
menu_no: "200442"
ntt_id: "189689"
number: "49"
title: "2024-FSSQA03 직접참가특성이 없는 금리연동형 보험계약의 공시이율예실차 회계처리 (회신일 `24.12.27.)"
department: "회계감독국"
standards:
  - "K-IFRS 제1117호"
reply_date: "2024-12-27"
published_date: "2025-01-09"
page_url: "https://www.fss.or.kr/fss/bbs/B0000132/view.do?nttId=189689&menuNo=200442"
attachments:
  - name: "example.hwp"
    atch_file_id: "6fffd4a8b6c5494e956ba19c81fdff72"
    file_sn: "1"
    extract_status: pending_whale
fetched_at: "2026-11-12T09:00:00+09:00"
extract_status: pending_whale
---
```

| 필드 | 규칙 |
|------|------|
| `board` | `B0000132` 또는 `B0000133`. 문자열. |
| `menu_no` | `200442` 또는 `200443`. 문자열. |
| `ntt_id`, `number` | 문자열. |
| `title` | 목록 제목. |
| `department` | 담당부서. 없으면 빈 문자열. |
| `standards` | B0000132는 목록의 관련기준서 열. B0000133은 `[]`. |
| `reply_date` | 제목이나 상세의 회신일. 두 자리 해 `24.12.27`은 `2024-12-27`이 된다. 회신일이 없으면 등록일. |
| `published_date` | 목록 등록일 `YYYY-MM-DD`. 없으면 null. |
| `page_url` | `view.do?nttId=&menuNo=`. |
| `attachments` | `name`, `atch_file_id`, `file_sn`, 파일별 `extract_status`. |
| `fetched_at` | 타임존이 있는 ISO 8601. |
| `extract_status` | 항목 전체 상태. `ok`, `pending_whale`, `failed`, `empty` 중 하나. |

본문:

```markdown
## 상세 안내

{안내 문장. 없으면 "(없음)"}

## 첨부: {파일명}

{추출 텍스트 또는 상태}
```

HWP/HWPX 절은 다음 두 줄이다.

```text
pending_whale
Whale 변환 대기
```

### 항목 상태

| 순서 | 조건 | 항목 `extract_status` |
|------|------|------------------------|
| 1 | 첨부가 없다 | `empty` |
| 2 | 하나라도 `failed` | `failed` |
| 3 | PDF를 받아 글이 있다. 같은 항목에 HWP가 있어도 PDF만 썼으면 `ok` | `ok` |
| 4 | PDF가 없고 HWP/HWPX만 저장했다 | `pending_whale` |
| 5 | PDF를 받았으나 글이 없다 | `empty` |

---

## 추출

PDF만 `pypdf`로 페이지 텍스트를 이어 붙인다. 페이지 사이는 빈 줄. 공백을 제외하고 글이 있으면 `ok`, 없으면 `empty`. 추출 예외는 그 첨부만 `failed`다.

HWP와 HWPX는 바이트를 그대로 두고 `pending_whale`이다. 한글, LibreOffice, Whale, `olefile`은 호출하지 않는다.

---

## manifest.jsonl

항목을 처리할 때마다 한 줄 추가한다. 같은 `board`+`ntt_id`가 여러 줄이면 마지막 줄이 최신이다. 중간에 멈춰도 이전 줄은 남는다.

```json
{"board":"B0000132","ntt_id":"189689","menu_no":"200442","number":"49","title":"제목","reply_date":"2024-12-27","published_date":"2025-01-09","extract_status":"pending_whale","path":"B0000132/189689/item.md","error":null}
```

상세 조회나 다운로드가 실패하면 `item.md`를 만들지 않고 `extract_status`를 `failed`, `path`를 null, `error`에 이유를 적는다. `item.md`가 없으면 다음 실행이 다시 시도한다.

---

## 옵시디안으로 복사

```text
python scripts/export_fss_replies_raw.py [--archive PATH] [--dest PATH]
```

`--archive` 기본값은 저장소의 `data/fss-replies`. `--dest` 기본값은 `C:\dev\obsidian-vault\raw\fss-replies`. `{board}/{nttId}/item.md`를 `{dest}/{board}/{nttId}.md`로 복사한다. 대상 파일이 있으면 생략한다. 첨부 파일은 복사하지 않는다. 끝난 뒤 복사 건수와 건너뛴 건수를 출력한다. 아카이브에서 사라진 항목을 dest에서 지우지 않는다.

테스트는 임시 디렉터리를 dest로 쓴다. 기본 경로에 쓰지 않는다.

---

## 테스트

네트워크 없는 pytest. 작은 HTML·PDF fixture만 쓴다. `requests.Session.request`는 테스트에서 막는다.

- 두 게시판 목록에서 board, nttId, menuNo, 번호, 제목, 담당부서, 등록일, 기준서(B0000132), 첨부 이름을 읽는다. 저장 페이지의 행은 10건이다.
- 제목의 회신일을 `reply_date`로 읽고, 회신일이 없으면 등록일을 쓴다. `24.6.21`, `24.01.03`, `15.6.22`를 포함한다.
- `nttId`와 `menuNo`로 `view.do` URL을 만든다.
- 상세에서 안내 문장과 `fileDown.do` 한 건을 읽는다. 문서뷰어와 script는 본문에 넣지 않는다.
- PDF만 있으면 `ok`. PDF와 HWP가 같이 있으면 PDF만 저장한다. HWP만 있으면 `pending_whale`이고 원본 바이트를 남긴다. 글이 없는 PDF는 `empty`다.
- `ok` 또는 `pending_whale`이고 파일이 있으면 건너뛴다.
- `--retry-failed` 대상은 `failed`와 `empty`뿐이다. 파일이 있는 `pending_whale`은 제외한다.
- `--board B0000132`는 B0000133과 B0000134를 요청하지 않는다.
- export는 dest에 같은 파일이 있으면 건너뛰고, 첨부는 복사하지 않는다.

검증 명령:

```bash
npm run lint:md
python scripts/validate_content.py --strict
npm test
```

`npm test` 대신 `cd scripts && python -m pytest tests/test_fss_replies.py -q`로 이 모듈만 볼 수 있다. `validate_content.py`의 대상은 분기 문서다. 이 아카이브는 그 검사에 넣지 않는다. CI에서 금감원 사이트를 호출하지 않는다.

---

## 완료 조건

코드 완료는 위 테스트와 이 스펙의 색인 반영이다. 게시판 전체 수집, `data/fss-replies/` 채우기, 그 디렉터리의 git 커밋은 운영자가 크롤러를 실행한 뒤 따로 한다.
