# Quality Updates Crawler — 메인 프로젝트 통합 설계 스펙

**날짜**: 2026-06-25  
**상태**: 승인됨  
**범위**: `quality-updates-crawler` 별도 저장소를 메인 `quality-updates` 레포에 단일 저장소로 통합

---

## 개요

금융당국(FSS, FSC, KICPA, KASB) 보도자료·공지를 수집하는 크롤러가 별도 git 저장소(`quality-updates-crawler/`)로 중첩 클론되어 있으며, 출력은 `outputs/`에 쓰이고 메인 `docs/quality-updates/`와 수동으로 연결된다. 편집기(`scripts/editor.py`)와 요약 스킬(`quality-updates-writer`)은 `docs/quality-updates/`만 읽는다.

**목적**: 크롤러 코드·의존성·실행 경로를 메인 프로젝트에 통합하고, 신규 분기 문서를 `docs/quality-updates/`에 직접 생성하여 큐레이션 파이프라인과 자연스럽게 연결한다.

**범위 외**: mkdocs.yml nav 자동 등록, CI에서 실제 외부 사이트 크롤, 크롤러 스케줄링(Cron/GitHub Actions)

---

## 배경·현황

| 영역 | 상태 |
|------|------|
| 메인 사이트 | MkDocs + CI + Render 배포 — 양호 |
| 큐레이션 편집기 | `scripts/editor/` — 성숙, 테스트 다수 |
| 요약 스킬 | Phase 0~2, skip 제거 — 성숙 |
| 크롤러 | 중첩 `.git`, 메인 git 미추적, README 미언급 |
| 출력 | 크롤러 `outputs/` ≠ 편집기 `docs/quality-updates/` |

### 확정된 통합 방향 (브레인스토밍 합의)

1. **단일 저장소** — 별도 crawler repo 유지 안 함  
2. **신규 분기만 직접 출력** — `docs/quality-updates/YYYY/`에 파일이 없을 때만 생성 (기존 큐레이션본 보호)  
3. **실행 방식** — 분기 단축 CLI + 명시적 날짜 오버라이드 (`--year`/`--quarter` 권장)

---

## 아키텍처

### 통합 후 디렉터리

```
quality-updates/
├── scripts/
│   ├── crawl.py              # CLI 진입점 (신규)
│   ├── crawler/              # 기존 quality-updates-crawler 이전
│   │   ├── __init__.py
│   │   ├── unified.py        # unified_crawler.py 리네임·리팩터
│   │   ├── FSS.py
│   │   ├── FSC.py
│   │   ├── KICPA.py
│   │   ├── KICPA_Standards.py
│   │   └── KASB.py
│   ├── editor.py             # 기존 유지
│   └── ...
├── docs/quality-updates/     # 크롤러 출력 대상
└── requirements.txt          # lxml, python-dateutil 추가
```

### 제거

- `quality-updates-crawler/` 폴더 전체 (코드 이전 후, 중첩 `.git` 포함)
- `quality-updates-crawler/requirements.txt`
- `quality-updates-crawler/outputs/` — 이전하지 않음 (`docs/`에 큐레이션본 존재)

### 통합 후 파이프라인

```
python scripts/crawl.py --year YYYY --quarter N
    → docs/quality-updates/YYYY/YYYY-MM-DD_to_YYYY-MM-DD.md (신규만)
    → mkdocs.yml nav 수동 등록
    → python scripts/editor.py (큐레이션)
    → quality-updates-writer (요약·Phase 2)
    → skip 제거 → mkdocs build --strict → 배포
    → docs/index.md Latest Update 갱신 (CONTRIBUTING 기존 절차)
```

---

## CLI 설계 (`scripts/crawl.py`)

### 사용 예

```bash
# 분기 단축 (일반 사용)
python scripts/crawl.py --year 2026 --quarter 1

# 인자 생략 → 오늘 날짜 기준 현재 분기
python scripts/crawl.py

# 비분기·예외 기간
python scripts/crawl.py --start 2026-01-15 --end 2026-03-31

# 강제 덮어쓰기 (기본: skip)
python scripts/crawl.py --year 2026 --quarter 1 --force

# 수집만, 파일 미생성
python scripts/crawl.py --year 2026 --quarter 1 --dry-run
```

### 인자

| 인자 | 설명 |
|------|------|
| `--year`, `--quarter` | 분기 시작일·종료일 자동 계산 (Q1=01-01~03-31, …) |
| `--start`, `--end` | `--quarter`보다 우선 |
| `--force` | 기존 파일 덮어쓰기 |
| `--dry-run` | 네트워크 수집만, 파일 쓰기 안 함 |

### 분기 메타데이터

**결정**: 한국 규제 업데이트는 2026년 이후에도 **분기(quarterly)** 단위를 유지한다.  
기존 `unified_crawler.py`의 `YEAR >= 2026 → monthly` 분기는 **제거**한다. (mkdocs nav, `quality-updates-writer` BOILERPLATE, 기존 큐레이션 문서와 일치)

- `frequency: quarterly`
- `period_label: YYYY-QN` (N = `(start_month - 1) // 3 + 1`)

### 기본값 (인자 생략)

`python scripts/crawl.py` 단독 실행 시:

- **기준 시각**: 로컬 타임존의 `date.today()`
- **연도·분기**: 오늘 날짜가 속한 달력 분기 (Q1=1–3월, …, Q4=10–12월)
- **기간**: 해당 분기 1일 ~ 말일 (`YYYY-MM-01` ~ 분기 말일)

`--year`만 지정하고 `--quarter` 생략 시 → exit 2 (에러 메시지: `--quarter` 필요).

### 출력 폴더 연도

`docs/quality-updates/{YEAR}/`의 `{YEAR}`는 **시작일(`--start` 또는 분기 시작일)의 연도**를 사용한다.  
교차 연도 기간(예: `2022-12-15` ~ `2023-04-03`)은 시작 연도 폴더에 둔다 — 기존 `2022/` 문서와 동일 관례.

---

## 출력·보호 로직

1. CLI에서 `START_DATE`, `END_DATE` 결정  
2. `path = docs/quality-updates/{YEAR}/{START}_to_{END}.md`  
3. `path` 존재 && `!force` → stderr 경고, **exit 0** (skip)  
4. `sync_period_to_modules()` — FSS/FSC 모듈 전역 기간 주입  
5. FSS, FSC, KICPA(+Standards), KASB 순 수집  
6. YAML front matter + 본문 + Appendix A 조립  
7. `os.makedirs(parent, exist_ok=True)` 후 동일 디렉터리 임시 파일 작성 → `os.replace(tmp, path)` (Windows 포함 atomic)  
8. stdout: `[DONE] Markdown generated → {path}`

### 실행 경로·import (editor.py와 동일 패턴)

- 사용자는 **저장소 루트**에서 `python scripts/crawl.py` 실행 (README·CONTRIBUTING 예시와 동일).
- `scripts/crawl.py` 진입점:
  ```python
  sys.path.insert(0, os.path.dirname(__file__))  # scripts/ on path
  from crawler.unified import main  # scripts/crawler/ 패키지
  ```
- 출력 경로는 `Path(__file__).resolve().parent.parent / "docs" / "quality-updates" / …` 로 **repo root 기준** 해석 (`scripts/editor/app.py`의 `repo_root()`와 동일: `scripts/`의 부모).

### Front matter (기존 유지)

```yaml
---
title: {START} ~ {END} Regulatory Updates
jurisdiction: KR
year: {YEAR}
frequency: quarterly
period_label: {label}   # YYYY-QN
period:
  start: {START}
  end: {END}
category: Quality Updates
agencies: [FSS, FSC, KICPA, KASB]
generated_by: quality-updates-crawler
generated_at: {END}
---
```

---

## 에러 처리

| 상황 | 동작 |
|------|------|
| 기관별 예외(타임아웃·HTTP·파싱 오류) | 해당 기관 결과 `[]` + stderr 경고, 나머지 계속 |
| 기관별 **정상 수집·기간 내 항목 0건** | 성공으로 간주 (빈 섹션 허용) |
| **전 기관 예외** (4개 모두 예외) | exit 1, 파일 미생성 (`--dry-run`도 exit 1) |
| 1개 이상 기관 정상 완료 | 파일 생성 (수집된 항목만 Appendix 포함), exit 0 |
| 잘못된 날짜 (`start > end` 등) | argparse 검증, exit 2 |
| `--year`만 있고 `--quarter` 없음 | exit 2 |
| 파일 존재 (no `--force`) | skip, exit 0 |

---

## 코드 이전·정리

| 항목 | 조치 |
|------|------|
| `unified_crawler.py` | `scripts/crawler/unified.py`로 이동; `OUTPUT_DIR`는 repo root 기준 `docs/quality-updates/{start_year}` |
| `crawlers/*.py` | `scripts/crawler/*.py`로 이동 (`KICPA_Standards.py` 포함) |
| 내부 import | `from crawlers import FSS` → `from crawler import FSS` (또는 `from . import FSS` in unified.py) |
| 디버그 print | `FSS.py` 등 `### SCRIPT STARTED ###` 제거 |
| `sync_period_to_modules` | 기존 로직 유지 |
| `compute_period_metadata` | `YEAR >= 2026` monthly 분기 **삭제**, 항상 quarterly |

---

## 의존성

`requirements.txt`에 추가:

```
lxml>=5.1.0
python-dateutil>=2.8.2
```

(`requests`, `beautifulsoup4`는 이미 메인 requirements에 존재)

---

## 문서 갱신

| 파일 | 변경 |
|------|------|
| `README.md` | 크롤러 실행 절, 프로젝트 트리에 `scripts/crawler/` |
| `CONTRIBUTING.md` | 분기 추가 1단계: `python scripts/crawl.py` |
| `docs/editor-curation-workflow.md` | 크롤 → 편집기 직결 흐름 |
| `.claude/skills/quality-updates-writer/SKILL.md` | BOILERPLATE: `crawl.py` 출력이 골격(링크+Appendix)이며 Executive Summary·기관별 요약은 Phase 2에서 추가함을 명시 |

### mkdocs.yml

1차 범위: **nav 수동 등록 유지** (레이블 형식 `N분기 (MM–MM월)` 연도별 수동 관리).

---

## 테스트

| 항목 | 범위 |
|------|------|
| 분기 날짜 계산 (기본값·`--year --quarter`) | 단위 테스트 |
| skip-if-exists / `--force` | 단위 테스트 |
| front matter (`frequency: quarterly`, `period_label`) | 단위 테스트 |
| repo root 출력 경로 해석 | 단위 테스트 |
| HTTP mock 기관 수집 | 통합 테스트 (선택) |
| CI 실제 크롤 | **제외** |

테스트: `scripts/tests/test_crawl.py` — 기존 `cd scripts && python -m pytest` 관례 유지.

---

## 구현 체크리스트

- [ ] `scripts/crawler/` 패키지 생성 및 모듈 이전
- [ ] `scripts/crawl.py` CLI (argparse)
- [ ] 출력 경로 `docs/quality-updates/{YEAR}/`, skip-if-exists
- [ ] `requirements.txt` 갱신
- [ ] `quality-updates-crawler/` 삭제
- [ ] 단위 테스트
- [ ] README, CONTRIBUTING, editor-curation-workflow 갱신
- [ ] `package.json`에 `"crawl": "python scripts/crawl.py"` 추가
- [ ] `quality-updates-writer` SKILL BOILERPLATE 절 crawl 연동 문구

---

## 리스크·완화

| 리스크 | 완화 |
|--------|------|
| 실수로 큐레이션본 덮어쓰기 | 기본 skip; `--force`만 덮어쓰기 |
| 외부 사이트 HTML 변경 | 기관별 독립 모듈, 부분 실패 허용 |
| nav 누락으로 사이트 미노출 | CONTRIBUTING 체크리스트에 nav 등록 단계 유지 |
