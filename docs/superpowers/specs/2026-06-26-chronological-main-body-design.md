# 본문 날짜순(과거→현재) 정렬 — 설계 스펙

**날짜**: 2026-06-26  
**상태**: 승인됨 (A안)  
**범위**: 크롤러 본문 출력을 과거→현재 순으로 통일. Appendix A는 크롤 순(최신→과거) 유지.

**선행 스펙**: [2026-06-25-crawler-integration-design.md](2026-06-25-crawler-integration-design.md), [2026-06-25-kasb-schedule-crawler-design.md](2026-06-25-kasb-schedule-crawler-design.md)

---

## 개요

금융당국 게시판은 페이지네이션이 **최신→과거** 순이다. 통합 크롤러(`unified.py`)가 이 순서를 본문에 그대로 쓰면, 편집기(`editor.py`)·요약 스킬·MkDocs 본문까지 역순으로 큐레이션이 진행된다.

**목적**: 본문(`###` ~ `## Appendix A` 이전) dated list만 **과거→현재**로 정렬하고, Appendix A(전체 자료)는 크롤 수집 순을 유지한다.

**브레인스토밍 합의**

| 항목 | 결정 |
|------|------|
| 방안 | **A안** — `unified.py`에서 본문만 오름차순 |
| 2026 Q1 | **지금** `reorder_chronological.py` 1회 실행 |
| 2022~2025 완료 분기 | **역순 유지** (백필 없음) |

**범위 외**

- Appendix A 정렬 변경
- 2022~2025 분기 `.md` 백필
- 편집기 UI 정렬 토글
- `validate_content.py` 본문 단조성 lint (2단계)

---

## 배경·현황

| 영역 | 변경 전 | 변경 후 |
|------|---------|---------|
| FSS/FSC/KICPA/KASB(공지·보도) | 사이트 최신순 그대로 | 본문만 오름차순 |
| KASB 주요일정 | 이미 오름차순 | 동일 (멱등) |
| KICPA_Standards | `reverse=True` 명시 | unified 정렬로 흡수 |
| Appendix A | 크롤 순 | **변경 없음** |
| `reorder_chronological.py` | Appendix까지 재정렬 가능 | `## Appendix A` 이전만 처리 |

---

## 아키텍처

### 변경 파일

```
scripts/crawler/
├── unified.py           # sort_* 헬퍼, collect_* 본문만 정렬
└── KICPA_Standards.py   # 역순 sort 제거

scripts/
├── reorder_chronological.py   # #### 단위 정렬 (Appendix·헤더 보존)
├── repair_quarterly_structure.py  # URL 기반 섹션 재조립 (reorder 손상 복구)

scripts/tests/
├── test_unified_sort.py         # 신규
└── test_reorder_chronological.py # 신규

docs/project/quarterly-operations-guide.md  # Phase 1 정렬 정책
docs/superpowers/README.md                  # spec 색인
docs/quality-updates/2026/2026-01-01_to_2026-03-31.md  # 1회 reorder
```

### 데이터 흐름

```
crawl.py
  → agency modules (최신순 수집)
  → APPENDIX dict (수집 순 그대로)
  → collect_* 본문 md_lines(sort_*(items))  # 오름차순
  → build_appendix() (무정렬)

editor.py / writer
  → 파일 줄 순 = 본문 과거→현재
```

---

## 정렬 규칙

1. **키**: `(YY-MM-DD)` → `(year, month, day)` (`year = 2000 + yy`)
2. **동일 날짜**: Python stable sort → **수집 순** 유지
3. **적용 대상**: 본문 `md_lines()` 입력만
4. **제외**: `APPENDIX` dict, `build_appendix()`, FSC appendix `list[str]` 원본

### 헬퍼 (`unified.py`)

| 함수 | 입력 |
|------|------|
| `sort_fss_items` | `list[dict]` (`date`: `yy-mm-dd`) |
| `sort_kicpa_dict_items` | `list[dict]` (`date`: `datetime`) |
| `sort_dated_tuples` | `list[tuple[str,str,str]]` (KASB) |
| `sort_md_link_lines` | `list[str]` (FSC `- (yy-mm-dd) [...]`) |

---

## 마이그레이션

| 대상 | 조치 |
|------|------|
| **신규 분기** (2026 Q2~) | `crawl.py`만으로 본문 날짜순 |
| **2026 Q1** (진행 중) | `repair_quarterly_structure.py`로 섹션 복구 후 `reorder_chronological.py` (#### 단위) |
| **2022~2025** | 변경 없음 (역순 유지) |

**2026 Q1 reorder 후 HITL**: 편집기 `line_index`가 바뀌므로 저장 전 파일 reload 권장.

---

## 완료 조건

```bash
cd scripts && python -m pytest tests/ -q
python scripts/reorder_chronological.py docs/quality-updates/2026/2026-01-01_to_2026-03-31.md  # 1회 (이미 적용 시 No change)
python scripts/validate_content.py --strict
mkdocs build --strict
```

- `test_unified_sort`: 본문 sort 헬퍼 단위 테스트
- `test_reorder_chronological`: Appendix A 이후 미변경 assertion

---

## 문서

- `quarterly-operations-guide.md` Phase 1: 본문 과거→현재, Appendix 크롤 순 명시
- gold standard(2023 Q2, 2025 Q4): **note 포맷** SSOT — 순서는 2026 Q1부터 오름차순 관례
