# KASB 질의회신 아카이브 — 설계 스펙

**날짜**: 2026-11-04  
**상태**: 승인됨 (2026-11-04)  
**범위**: [질의회신 요약 전체](https://kasb.or.kr/front/board/allReplySummaryList.do)를 항목 폴더로 입수해 이 저장소에 보관한다. 사이트에는 게시하지 않는다. 옵시디안은 `item.md`만 `raw/`로 복사한다.

---

## 개요

분기 문서와 사이트는 질의회신 요약을 알리는 보도자료만 다룬다. 회신 결론은 첨부(hwp, hwpx, pdf, xlsx)에 있다. 게시판을 사이트에 미러링하지 않고, 항목마다 메타데이터·추출 텍스트·원본 첨부를 남긴다.

옵시디안 볼트(`C:\dev\obsidian-valut`)는 그 마크다운을 `raw/kasb-replies/{seq}.md`로 가져간다. 위키 합성은 이 스펙 밖이다. 다른 프로젝트가 second brain으로 읽는 지식은 옵시디안 저장소의 위키다.

**목적**

- 분류 전체와 상단 공지를 `seq` 단위로 저장한다.
- 다시 실행하면 이미 받은 항목은 건너뛴다.
- 추출이 실패해도 원본 첨부는 남긴다.
- `item.md`만 옵시디안 `raw/`에 복사하고, 이미 있는 파일은 덮어쓰지 않는다.

**범위 외**

- 옵시디안 `wiki/` 페이지, `wiki/index.md`, `wiki/log.md`
- 분기 `crawl.py`, `docs/quality-updates/`, `quality-updates-writer`, `auto_curate.py`
- MCP `export_corpus.py`와 `data/corpus/`
- MkDocs nav, 질의회신 본문의 사이트 게시, CI의 라이브 크롤, Cron. `docs/index.md`의 한 줄 정정은 범위에 포함한다.
- 한글 프로그램·LibreOffice 변환, HWP 본문 전체 파서
- 아카이브 2천 건을 구현 작업 중에 받아 커밋하는 일. 수집은 구현 후 운영자가 실행한다.

---

## 배경·현황

| 영역 | 상태 |
|------|------|
| KASB 공지·보도·주요일정 | `scripts/crawler/KASB.py`. 목록 링크만 분기 문서에 넣는다. |
| 질의회신 요약 전체 | 미수집. 목록 약 220페이지. 마지막 페이지는 `G_MovePage(220)`. |
| 상단 공지 | 비교표·정비목록. `ctg_cd` `016009`. 매 페이지에 반복된다. |
| 분류 | 한국채택국제회계기준, IFRS 해석위원회 논의 결과, 일반기업회계기준, 종전기업회계기준, K-IFRS 신속처리질의, 일반기준 신속처리질의, 정착지원TF |
| 상세 | POST `View{ctgCd}.do`. 분류·관련 기준서·등록일·안내 문장·첨부. 회신 본문은 첨부 파일이다. |
| 첨부 다운로드 | POST `https://www.kasb.or.kr/commonFile/fileDownload.do` (`fileNo`, `fileSeq`). 편집기 `fetch_kasb_bytes`와 같은 엔드포인트. |
| 사이트 문구 | `docs/index.md`가 질의회신 정리를 추가 예정으로 적는다. |
| 옵시디안 | `raw/`는 불변 원본. `wiki/`가 지식 페이지. 기존 `wiki/kasb-technical-enquiries.md`는 분기 요약만 인용한다. |

### 브레인스토밍 합의

1. 항목 폴더에 메타데이터 마크다운과 원본 첨부를 같이 둔다.
2. 게시판 전체(일곱 분류와 상단 공지)를 받는다.
3. 옵시디안으로는 `item.md`만 복사한다. 원본은 이 저장소에 한 벌이다.
4. 분기 크롤과 사이트 게시에는 넣지 않는다.

---

## 아키텍처

### 변경 파일

```text
scripts/crawler/kasb_replies.py          # 목록·상세 파서, 추출, 저장, 복사
scripts/crawl_kasb_replies.py            # 수집 CLI
scripts/export_kasb_replies_raw.py       # item.md → 옵시디안 raw
scripts/tests/test_kasb_replies.py       # fixture 단위 테스트
requirements.txt                         # pypdf, openpyxl, olefile
docs/index.md                            # 사이트 게시 약속을 한 줄로 정정
docs/superpowers/README.md               # 이 스펙 색인
```

`scripts/crawler/KASB.py`, `scripts/crawler/unified.py`, `scripts/crawl.py`는 변경하지 않는다. 크롤러는 편집기 `page_attachments`를 import하지 않고, 같은 다운로드 URL과 폼 필드만 사용한다.

사이트 원본은 `docs/`다. 아카이브는 `data/kasb-replies/`에 두므로 MkDocs 빌드에 포함되지 않는다. `downloads/`는 gitignore 대상이지만, 이 아카이브는 저장소 정본이므로 `data/kasb-replies/`는 gitignore하지 않는다.

### 디렉터리

```text
data/kasb-replies/
  manifest.jsonl
  {seq}/
    item.md
    {원본 파일명}
```

`seq`는 `fn_Detail('40689','016008')`의 첫 인자다. 폴더 키는 `seq`만 쓴다. 파일명에 경로 구분자가 있으면 제거한다. 같은 폴더에서 이름이 겹치면 `{stem}-{file_seq}{suffix}`로 저장한다.

### 데이터 흐름

```text
crawl_kasb_replies.py
  → 목록 1..마지막 페이지 (분류 필터 없음)
  → seq 단위로 중복 제거
  → 완료 항목은 상세·다운로드를 생략
  → 상세 POST View{ctgCd}.do
  → 첨부 POST fileDownload.do
  → 추출 후 item.md
  → manifest.jsonl 에 한 줄 추가

export_kasb_replies_raw.py
  → data/kasb-replies/{seq}/item.md
  → {dest}/{seq}.md
  → 대상 파일이 있으면 생략
```

목록을 매 실행 처음부터 읽는다. 새 글은 1페이지에 붙기 때문이다. 상세와 다운로드만 완료된 `seq`에서 생략한다.

---

## 수집

### 목록

| 항목 | 값 |
|------|-----|
| URL | `https://www.kasb.or.kr/front/board/allReplySummaryList.do` |
| 세션 | GET 1회 후 POST |
| Body | `siteCd=002000000000000`, `searchfield=ALL`, `searchword=""`, `page` |
| 마지막 페이지 | `li.pag_last a`의 `G_MovePage(N)` |
| 열 | 번호, 분류, 제목, 첨부, 회신일, 공개일 |

제목의 `fn_Detail('seq','ctgCd')`에서 `seq`와 `ctg_cd`를 읽는다. 첨부의 `fileDownload('fileNo','fileSeq')`와 링크 텍스트의 파일명을 읽는다. 번호가 `공지`인 행도 포함한다.

### 상세

POST `https://www.kasb.or.kr/front/board/View{ctgCd}.do`, 필드 `seq`, `ctgCd`.

가져오는 값: 분류, 관련 기준서 텍스트(화면에 보이는 순서), 등록일, 본문 안내 문장, 첨부 목록. 메뉴·바닥글·헤더는 본문에 넣지 않는다. 안쪽 표가 있으면 행 단위로 모은다. 기준서 명 칸에 글이 있으면 바로 앞 기준서 문자열 뒤에 붙인다. 안쪽 표가 없으면 그 칸의 글을 한 항목으로 둔다. 상세에 분류가 있으면 그 값을 쓰고, 없으면 목록 분류를 쓴다. 목록 회신일이 비어 있고 등록일만 있으면 등록일을 회신일로 둔다.

### 다운로드

POST `https://www.kasb.or.kr/commonFile/fileDownload.do`, 필드 `fileNo`, `fileSeq`. 한 항목에 첨부가 여러 개면 모두 저장한다.

`item.md`는 받을 첨부를 디스크에 저장한 뒤 추출까지 시도했을 때만 쓴다. 목록 파싱, 상세, 다운로드가 실패하면 `item.md`를 만들지 않는다. 파일은 받았는데 추출만 실패하면 `item.md`와 원본을 둘 다 남긴다.

### 요청 간격과 실패

`--delay` 기본값 0.2초. `kasb.or.kr` 요청 사이에 둔다. 한 항목의 HTTP 오류나 추출 오류는 그 항목만 manifest에 적고 다음 항목으로 넘어간다.

`--limit N`은 이번에 새로 받거나 다시 시도하는 항목 수다. 건너뛴 완료 항목은 세지 않는다. 생략하면 목록 전체를 처리한다.

### 건너뛰기

기본 실행은 아래를 모두 만족하는 `seq`를 완료로 보고 상세·다운로드를 하지 않는다.

- `item.md`가 있다.
- 프론트매터의 첨부 파일이 모두 디스크에 있다.
- `extract_status`가 `ok`다.

`--retry-failed`는 `extract_status`가 `failed`, `partial`, `empty`인 항목을 다시 추출한다. 첨부 파일이 없으면 다시 받는다. `ok`인 항목은 이 플래그로도 다시 받지 않는다.

---

## item.md

UTF-8. 프론트매터는 YAML.

```yaml
---
seq: "40689"
ctg_cd: "016008"
number: "2193"
category: "정착지원TF"
title: "제1118호 정착지원 TF 논의 내용(5차)"
standards:
  - "제1118호 재무제표 표시와 공시"
reply_date: "2026-10-16"
published_date: null
attachments:
  - name: "261016_example.hwpx"
    file_no: "-49993299"
    file_seq: "1"
    extract_status: ok
fetched_at: "2026-11-04T07:00:00+09:00"
extract_status: ok
---
```

| 필드 | 규칙 |
|------|------|
| `seq`, `ctg_cd` | 문자열. 재조회 키. GET 주소 하나는 만들지 않는다. |
| `number` | 목록 번호 문자열. 공지는 `공지`. |
| `category`, `title` | 상세 분류가 있으면 상세, 없으면 목록. |
| `standards` | 관련 기준서 문자열 목록. 한 기준서에서 구분과 명이 다른 칸이면 한 문자열로 잇고, 코드/이름 필드로 나누지 않는다. 없으면 `[]`. |
| `reply_date`, `published_date` | `YYYY-MM-DD` 또는 null. |
| `attachments` | `name`, `file_no`, `file_seq`, 파일별 `extract_status`. |
| `fetched_at` | 타임존이 있는 ISO 8601. |
| `extract_status` | 항목 전체 상태. `ok`, `partial`, `failed`, `empty` 중 하나. |

본문:

```markdown
## 상세 안내

{안내 문장. 없으면 "(없음)"}

## 첨부: {파일명}

{추출 텍스트}
```

첨부가 여러 개면 `## 첨부:` 절을 파일마다 둔다. 추출이 실패하거나 비면 그 절에는 상태와 이유 한 줄만 둔다. 첨부가 없는 항목은 `## 상세 안내`만 두고 항목 상태는 `empty`다.

### 항목 상태

첨부별 상태를 위에서부터 처음 맞는 조건 하나로 모은다.

| 순서 | 조건 | 항목 `extract_status` |
|------|------|------------------------|
| 1 | 첨부가 없다 | `empty` |
| 2 | 하나라도 `failed` | `failed` |
| 3 | 하나라도 `partial` | `partial` |
| 4 | 모두 `empty` | `empty` |
| 5 | `ok`와 `empty`가 섞여 있다 | `partial` |
| 6 | 모두 `ok` | `ok` |

---

## 추출

의존성: `pypdf`, `openpyxl`, `olefile`. 한글 프로그램과 LibreOffice는 호출하지 않는다.

| 확장자 | 방법 | 첨부 상태 |
|--------|------|-----------|
| pdf | `pypdf`로 페이지 텍스트를 이어 붙인다. 페이지 사이는 빈 줄. | 공백을 제외하고 글이 있으면 `ok`, 없으면 `empty` |
| hwpx | `Contents/section*.xml`만, 이름순. 로컬 이름이 `t`인 요소의 직접 텍스트만 문서 순으로 잇는다. | 글이 있으면 `ok`, 없으면 `empty` |
| xlsx | `openpyxl` `data_only=True`. 빈 시트는 생략. 시트마다 `### 시트명`과 마크다운 표. 셀 안의 줄바꿈은 공백으로 바꾸고, 세로줄 문자에는 백슬래시를 앞에 붙인다. | 글이 있으면 `ok`, 없으면 `empty` |
| hwp | OLE 스트림 `PrvText`를 UTF-16LE로 읽고 끝의 NUL과 공백을 제거한다. | 글이 있으면 `partial`. 스트림이 없거나 디코드에 실패하면 `failed` |
| 그 외 | 파일만 저장 | `failed` |

`partial`은 미리보기 길이에 잘릴 수 있다는 뜻이다. 원본 hwp가 대조 정본이다.

---

## manifest.jsonl

항목을 처리할 때마다 한 줄 추가한다. 같은 `seq`가 여러 줄이면 마지막 줄이 최신이다. 중간에 멈춰도 이전 줄은 남는다.

```json
{"seq":"40689","ctg_cd":"016008","number":"2193","category":"정착지원TF","title":"제1118호 정착지원 TF 논의 내용(5차)","reply_date":"2026-10-16","published_date":null,"extract_status":"ok","path":"40689/item.md","error":null}
```

상세를 열기 전에 실패한 항목은 `item.md`를 만들지 않고 `extract_status`를 `failed`, `path`를 null, `error`에 이유를 적는다. `item.md`가 없으면 다음 실행이 다시 시도한다.

---

## 옵시디안으로 복사

```text
python scripts/export_kasb_replies_raw.py [--dest PATH]
```

`--dest` 기본값은 `C:\dev\obsidian-valut\raw\kasb-replies`. `{seq}/item.md`를 `{dest}/{seq}.md`로 복사한다. 대상 파일이 있으면 생략한다. 첨부 파일과 `wiki/`는 복사하지 않는다. 끝난 뒤 복사 건수와 생략 건수를 출력한다. 아카이브에서 사라진 항목을 dest에서 지우지 않는다.

테스트는 임시 디렉터리를 dest로 쓴다. 기본 경로에 쓰지 않는다.

---

## 사이트 문구

`docs/index.md`의 추가 예정 항목에서 질의회신 정리 약속을 뺀다. 남기는 문장:

> 회계기준원(KASB) 질의회신 원문은 이 사이트에 게시하지 않는다. 유관기관 보도자료 확장은 추가 예정.

내부 경로 `data/kasb-replies/`는 사이트 첫 화면에 적지 않는다.

---

## 테스트

네트워크 없는 pytest. fixture HTML과 작은 pdf, hwpx, xlsx, hwp.

- 목록 행에서 `seq`, `ctg_cd`, 번호, 분류, 제목, 날짜, `fileNo`, `fileSeq`, 파일명을 읽는다.
- 매 페이지에 반복되는 공지를 `seq`로 한 건으로 모은다.
- `G_MovePage`에서 마지막 페이지 번호를 읽는다.
- 상세에서 기준서·안내 문장을 읽고 메뉴 문구는 본문에서 뺀다.
- pdf·hwpx·xlsx는 비어 있지 않으면 `ok`, 빈 파일은 `empty`.
- `PrvText`가 있는 hwp는 `partial`, 스트림이 없으면 `failed`.
- 첨부 상태 집계가 위의 표와 같다.
- `ok`이고 파일이 있으면 완료로 건너뛴다.
- `--retry-failed` 대상은 `failed`, `partial`, `empty`뿐이다.
- export는 dest에 같은 `{seq}.md`가 있으면 생략한다.

검증 명령:

```bash
cd scripts && python -m pytest tests/test_kasb_replies.py -q
cd scripts && python -m pytest tests/ -q
mkdocs build --strict
```

`validate_content.py`와 `export_corpus.py`의 대상은 분기 문서다. 이 아카이브는 그 검사에 넣지 않는다. CI에서 기준원 사이트를 호출하지 않는다.

---

## 완료 조건

코드 완료는 위 테스트와 `docs/index.md` 문장 반영이다. 게시판 전체 수집, `data/kasb-replies/` 채우기, git 커밋은 운영자가 크롤러를 실행한 뒤 따로 한다.
