# KASB 주요일정 크롤러 — 설계 스펙

**날짜**: 2026-06-25  
**상태**: 승인됨 (A안)  
**범위**: 한국회계기준원 [주요 일정](https://www.kasb.or.kr/front/board/calListA.do) 리스트를 기존 crawl 출력 포맷에 맞춰 자동 입수

**선행 스펙**: [2026-06-25-crawler-integration-design.md](2026-06-25-crawler-integration-design.md)

---

## 개요

통합 크롤러(`scripts/crawler/`)는 KASB **공지사항·보도자료**만 수집한다. 분기 문서·`quality-updates-writer` BOILERPLATE·골드스탠다드(2023~2025)는 KASB 하위 **`#### 주요일정`** 섹션을 요구하지만, 해당 링크(`calView.do`)는 HITL/요약 단계에서 수동 입력되어 왔다.

**목적**: [calListA.do](https://www.kasb.or.kr/front/board/calListA.do) 리스트 테이블의 일정을 crawl 시 자동 수집하여 `#### 주요일정` 본문 및 Appendix A `**주요일정**`에 반영한다.

**범위 외**

- `calView.do` 상세 본문·첨부·안건표 파싱 (`!!! note "주요 내용"`은 quality-updates-writer/HITL)
- 2023~2025 분기 문서 백필
- `calList.do` / `calListB.do` 별도 지원 (동일 POST 결과 확인 — calListA만 사용)
- mkdocs nav, CI live crawl, Cron

---

## 배경·현황

| 영역 | 상태 |
|------|------|
| KASB 공지·보도 | `KASB.crawl_board()` — POST + `fn_Detail` + 페이지네이션 동작 |
| KASB 주요일정 | **미구현** — `collect_kasb()`에 섹션 없음 |
| 출력 포맷 SSOT | BOILERPLATE 3섹션: 공지·보도·**주요일정** |
| 정렬 관례 | 주요일정만 **과거→현재** (`reorder_chronological.py`가 역정렬 제외) |
| 대상 페이지 | 5열 테이블; `fn_Detail('seq')` → `calView.do?seq=` |

### 브레인스토밍 합의 (A안)

1. **`KASB.py` 확장** — 별도 모듈 분리·상세 페이지 크롤 없음  
2. **리스트 링크만** — `(yy-mm-dd) [제목](calView.do?seq=…)` 튜플  
3. **기간 필터** — crawl CLI의 `START_DATE` ~ `END_DATE`와 동일 (`s_date_start` / `s_date_end`)

---

## 아키텍처

### 변경 파일

```
scripts/crawler/
├── KASB.py          # crawl_schedule(), parse_schedule_page() 추가
└── unified.py       # collect_kasb()에 주요일정 섹션·Appendix 키 추가

scripts/tests/
└── test_kasb_schedule.py   # fixture HTML 단위 테스트 (신규)
```

### 데이터 흐름

```
crawl.py --year YYYY --quarter N
  → unified.collect_kasb()
      → KASB.crawl_board(공지·보도)     # 기존
      → KASB.crawl_schedule(start, end) # 신규
  → Markdown: #### 주요일정 (오름차순)
  → Appendix A: **주요일정**
```

---

## 수집 API (calListA.do)

### 요청

| 항목 | 값 |
|------|-----|
| URL | `https://www.kasb.or.kr/front/board/calListA.do` |
| Method | POST (세션: GET list URL 1회 후 POST) |
| Body | `siteCd=002000000000000`, `searchfield=ALL`, `searchword=`, `s_date_start`, `s_date_end`, `page` |

`fetch_page()`는 기존 공지/보도와 **동일 함수 재사용**.

### HTML 파싱

리스트 테이블 행: **5열** (`tbody tr`, `td` 5개)

| 인덱스 | 필드 | 용도 |
|--------|------|------|
| 0 | 진행일자 | `YYYY-MM-DD` → `%y-%m-%d` |
| 1 | 대분류 | 수집·출력 **제외** (YAGNI) |
| 2 | 중분류 | 수집·출력 **제외** |
| 3 | 일정명 | `<a onclick="javascript:fn_Detail('1111');">` → title, seq |
| 4 | 장소 | 수집·출력 **제외** |

- **상세 URL**: `https://www.kasb.or.kr/front/board/calView.do?seq={seq}`
- **행 스킵**: `fn_Detail` 없음, 날짜 파싱 실패, 빈 제목

### 페이지네이션

공지/보도와 동일: `page=1,2,…`, 파싱 결과 0건이면 종료.

### 정렬

수집 완료 후 **진행일자 오름차순** 정렬 (사이트 기본은 최신→과거).

```python
items.sort(key=lambda t: datetime.strptime(t[0], "%y-%m-%d"))
```

(`t[0]`이 `%y-%m-%d`이므로 tuple 비교 대신 명시적 date key 권장)

---

## `KASB.py` 설계

### 상수

```python
SCHEDULE = {
    "list": "https://www.kasb.or.kr/front/board/calListA.do",
    "view": "https://www.kasb.or.kr/front/board/calView.do",
}
```

### 함수

| 함수 | 역할 |
|------|------|
| `parse_schedule_page(html) -> list[tuple[str,str,str]]` | 5열 테이블 → `(date_yy_mm_dd, title, url)` |
| `crawl_schedule(start: str, end: str) -> list[tuple[str,str,str]]` | 세션·페이지 loop·정렬·로그 |

**반환 타입**은 `crawl_board()`와 동일 `(d, title, url)` 튜플 리스트.

### 로그

```
=== [주요일정] 크롤링 시작 ===
=== [주요일정] 완료: N건 ===
```

---

## `unified.py` 연동

`collect_kasb()` 마지막에 추가:

```python
schedule = KASB.crawl_schedule(START_DATE_STR, END_DATE_STR)
APPENDIX["한국회계기준원"]["주요일정"] = schedule
lines += ["\n#### 주요일정\n", md_lines(schedule)]
```

- Appendix 섹션 키: `"주요일정"` (기존 큐레이션본·Appendix A와 일치)
- 0건: 빈 `md_lines` → 빈 줄만 (또는 writer BOILERPLATE의 “해당사항 없음”은 **요약 Phase**에서 처리; crawl raw 출력은 빈 리스트 허용)

---

## 출력 예시

```markdown
#### 주요일정

- (26-01-16) [2026년 제1회 회계기준위원회(2025년 제13회 회계기준위원회 회의록 등)](https://www.kasb.or.kr/front/board/calView.do?seq=1105)
- (26-02-13) [2026년 제2회 회계기준위원회(...)](https://www.kasb.or.kr/front/board/calView.do?seq=1106)
...
```

Appendix A:

```markdown
**주요일정**

- (26-01-16) [...](...)
...
```

---

## 에러 처리

[crawler-integration-design.md](2026-06-25-crawler-integration-design.md) 정책 유지:

| 상황 | 동작 |
|------|------|
| HTTP/파싱 예외 | stderr 경고, `[]` 반환, 공지·보도 등 나머지 계속 |
| 기간 내 0건 | 성공, 빈 섹션 |
| 전 기관 실패 | crawl exit 1 (기존) — KASB 일정만 실패해도 공지·보도 수집 시 파일 생성 |

`crawl_schedule` 내부: `try/except`로 감싸거나 `crawl_board`와 동일하게 예외 전파 후 `unified`/`crawl.py` 기관별 handler가 처리 — **기존 FSS/FSC/KICPA/KASB board 패턴과 동일**하게 맞춘다.

---

## 테스트

파일: `scripts/tests/test_kasb_schedule.py`

| 케이스 | 검증 |
|--------|------|
| `parse_schedule_page` | fixture HTML 2~3행 → date, title, calView URL |
| `fn_Detail` 없는 행 | 스kip |
| 정렬 | 입력 역순 fixture → `crawl_schedule` mock 후 오름차순 |
| 빈 테이블 | `[]` |

- **HTTP mock** 또는 HTML 문자열 직접 주입 (CI 외부 호출 없음)
- 실행: `cd scripts && python -m pytest tests/test_kasb_schedule.py -q`

---

## 문서 갱신 (구현 시)

| 파일 | 변경 |
|------|------|
| `docs/superpowers/README.md` | spec 색인 1행 |
| `README.md` | (선택) KASB 수집 항목에 주요일정 1어구 — crawler-integration 문서와 중복 최소화 |

`quality-updates-writer` SKILL 변경 **불필요** — BOILERPLATE에 이미 `#### 주요일정` 존재.

---

## 구현 체크리스트

- [ ] `KASB.py`: `SCHEDULE`, `parse_schedule_page`, `crawl_schedule`
- [ ] `unified.py`: `collect_kasb()` 주요일정 + Appendix
- [ ] `scripts/tests/test_kasb_schedule.py`
- [ ] `cd scripts && python -m pytest tests/ -q` 통과
- [ ] (수동) `python scripts/crawl.py --year 2026 --quarter 1 --dry-run` 또는 `--force`로 7건 확인
- [ ] `docs/superpowers/README.md` 색인

---

## 리스크·완화

| 리스크 | 완화 |
|--------|------|
| calListA HTML 열 구조 변경 | 5열·`fn_Detail` 검증 + 테스트 fixture; 실패 시 빈 섹션 |
| calListA/B/C URL 분기 | calListA canonical; 동일 POST 확인됨 |
| 기존 큐레이션본 덮어쓰기 | crawl 기본 skip-if-exists (`--force`만 덮어쓰기) |
| note 블록 누락 기대 | spec·writer 역할 분리 명시; 상세는 SUMMARIZE |

---

## 완료 조건

1. 신규 분기 crawl 출력에 `#### 주요일정` 및 Appendix `**주요일정**` 포함  
2. 2026 Q1 수동 검증: 사이트 7건과 seq·날짜·제목 일치  
3. pytest 통과, 기존 crawl 테스트 회귀 없음
