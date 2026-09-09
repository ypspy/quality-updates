# FSS 보도자료 목록 크롤러 — KRDS 마크업 대응

**날짜**: 2026-09-09  
**상태**: 승인됨  
**범위**: 금융감독원 보도자료 목록 파서만 개편 HTML에 맞춤  
**선행 스펙**: [2026-06-25-crawler-integration-design.md](2026-06-25-crawler-integration-design.md)

---

## 개요

금감원 홈페이지가 KRDS 마크업으로 개편된 뒤 `python scripts/crawl.py`의 **보도자료** 섹션이 비어 있다. 목록 URL은 그대로이고, 동향자료·세칙은 수집된다.

**목적**: `FSS.fetch_press_release()`가 개편된 `list.do` HTML에서 제목·등록일·상세 링크를 다시 뽑게 한다.

**범위 외**

- 회계감독 동향자료·세칙 제·개정예고 파서
- 편집기 상세 미리보기 (`div.bd-view` 등)
- 금감원 보도자료 Open API
- CI에서 실제 `fss.or.kr` 크롤
- 기존 분기 문서 백필

---

## 배경

`scripts/crawler/FSS.py`의 `fetch_press_release()`는 다음을 그대로 쓴다.

- URL: `https://www.fss.or.kr/fss/bbs/B0000188/list.do`
- 쿼리: `menuNo=200218`, `pageIndex`, `sdate`, `edate`, `searchCnd`, `searchWrd`

개편 후에도 GET 응답에 목록 테이블이 있고, `sdate`/`edate` 기간 필터도 동작한다.

깨진 지점은 행 선택자다. 보도자료만 `div.bd-list table tbody tr`를 쓰고, 새 HTML에는 `bd-list`가 없다. 래퍼는 `div.krds-table-wrap`, 테이블은 `table.tbl.col.list-data`다. 0행이면 즉시 `break`하여 빈 목록을 반환한다.

동향자료는 처음부터 `table tbody tr`라서 같은 개편에도 수집된다. 제목 셀 `td.title a`와 등록일 칸(0-based index 3, `YYYY-MM-DD`)은 보도자료에서도 유지된다. 첨부·영상 칸이 늘어 행은 7칸이지만, 앞 4칸 순서는 번호·제목·담당부서·등록일이다.

### 브레인스토밍 합의 (1안)

1. **보도자료 목록 셀렉터만** 동향자료와 같게 `table tbody tr`로 맞춘다.  
2. URL·기간 파라미터·`td.title a`·날짜 칸·페이징·조기 종료는 유지한다.  
3. 링크 기준 파서·Open API는 하지 않는다.

---

## 아키텍처

### 변경 파일

```
scripts/crawler/FSS.py                 # fetch_press_release() 행 선택자 (+ 테스트용 HTML 파서 분리)
scripts/tests/test_fss_press_list.py   # 픽스처 단위 테스트 (신규)
scripts/tests/fixtures/fss_press_list_krds.html
```

`unified.py`, 동향자료·세칙 함수, 편집기는 변경하지 않는다.

### 파서

행 선택은 동향자료와 같게 `table tbody tr`다.

`parse_press_list_html(html)`:

1. `td.title a`가 있고 `td`가 4개 이상인 행만 사용  
2. `tds[3]`을 `%Y-%m-%d`로 파싱해 `posted_on`에 넣는다. 실패하면 그 행 skip  
3. `{"title", "href", "posted_on"}` 리스트 반환. href는 문서 그대로(상대경로). 테이블이 없거나 유효 행이 없으면 `[]`

`fetch_press_release()`:

1. 기존 URL·쿼리로 GET  
2. 헬퍼 결과가 비면 페이지 루프 `break`  
3. `posted_on < start_dt`이면 수집 종료  
4. `{date: yy-mm-dd, title, link}`를 `urljoin(BASE_URL, href)`로 적재  

`max_page`·`pageIndex`는 기존과 동일하다.

### 데이터 흐름

```
crawl.py
  → unified.collect_fss()
    → FSS.fetch_press_release()
      → GET list.do (기존 params)
      → parse press table rows
    → Appendix["금융감독원"]["보도자료"]
    → 본문 #### 보도자료 마크다운
```

출력 포맷·정렬(`sort_fss_items`)·파일 쓰기 규칙은 [크롤러 통합 스펙](2026-06-25-crawler-integration-design.md)을 따른다.

---

## 에러 처리

| 상황 | 동작 |
|------|------|
| 테이블 없음 또는 `tbody` 빈 행 | 예외 없이 빈 목록, 페이지 루프 종료 |
| 행에 제목 링크 없음 / 날짜 파싱 실패 | 해당 행 skip |
| 기간 시작일 이전 행 | 수집 종료, 그때까지 결과 반환 |
| HTTP 타임아웃·HTTP 오류 | 기존 `FSS.py` 동작 유지 (이번 스펙에서 새로 감싸지 않음) |
| 마크업 재개편 감지 | 하지 않음 |

기관 예외 시 빈 섹션·나머지 기관 계속은 통합 스펙의 기존 규칙을 따른다.

---

## 테스트

CI는 `fss.or.kr`을 호출하지 않는다.

픽스처는 최소 HTML이다. `bd-list` 없이 `table` / `td.title a` / 등록일 칸을 넣고, 상세 href는 `/fss/bbs/B0000188/view.do?nttId=…` 형태다.

| 케이스 | 기대 |
|------|------|
| KRDS 목록 1페이지 (2건) | 제목, `posted_on` 날짜, href에 `B0000188/view.do`와 `nttId` |
| `tbody` 빈 테이블 | `[]` |
| `div.bd-list` 없는 HTML | 행을 찾음 (회귀: 옛 셀렉터로는 0건이던 입력) |

동향자료·세칙·live GET 테스트는 추가하지 않는다.

완료 검증: `cd scripts && python -m pytest tests/test_fss_press_list.py tests/test_crawl.py -q`

---

## 비기능

- 기존 분기 마크다운·HITL 마커는 수정하지 않는다.  
- 픽스처는 전체 페이지(~640KB 메뉴 포함)가 아니라 목록 테이블 조각만 둔다.
