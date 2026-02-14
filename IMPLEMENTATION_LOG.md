# Project Improvement Proposal — 실행 결과 로그

> **실행일**: 2026-02-13  
> **기준 문서**: `PROJECT_IMPROVEMENT_PROPOSAL.md`

---

## 요약

| Task | 상태 | 비고 |
|------|------|------|
| Task 1: scripts/ Git 추적 | ✅ 완료 | .gitignore 수정, scripts 추가 |
| Task 2: read_hwp.py 정리 | ✅ 완료 | 파일 삭제 |
| Task 3: HWP_EXTRACT_INSTRUCTION 현행화 | ✅ 완료 | extract_hwp_temp.py 제거, CLI 갱신 |
| Task 4: reorder CLI 인자 | ✅ 완료 | argparse, --dry-run, 파일 존재 검증 |
| Task 5: validate_content.py | ✅ 완료 | admonition, YAML, 날짜, 테이블 스키마 검증 |
| Task 6: GitHub Actions CI | ✅ 완료 | lint, build, validate jobs |
| Task 7: index.md 최신화 | ✅ 완료 | 2025 Q4 반영, copyright 2026 |
| Task 8: Dependabot | ✅ 완료 | pip + github-actions |

---

## Task별 상세

### Task 1: scripts/ Git 추적 활성화

**변경 사항**

- `.gitignore`: `*.py` → `/*.py` (루트만 무시), `scripts/hwp_extracted.txt` 추가
- `git add scripts/extract_hwp.py scripts/reorder_chronological.py scripts/HWP_EXTRACT_INSTRUCTION.md`

**검증**

```powershell
git ls-files scripts/extract_hwp.py       # → scripts/extract_hwp.py
git ls-files scripts/HWP_EXTRACT_INSTRUCTION.md
git check-ignore -v scripts/hwp_extracted.txt
```

---

### Task 2: read_hwp.py 정리

**변경 사항**

- `read_hwp.py` 삭제 (scripts/extract_hwp.py와 기능 중복)
- `hwp_extract` 의존성은 다른 곳에서 미사용 확인

**검증**

```powershell
Test-Path read_hwp.py   # → False
py scripts/extract_hwp.py --help
```

---

### Task 3: HWP_EXTRACT_INSTRUCTION.md 현행화

**변경 사항**

- "3. 현재 스크립트 구성" 테이블: `extract_hwp_temp.py` 행 제거, `extract_hwp.py` 설명을 현재 CLI로 수정
- "6. 수정 시 참고 사항": 구현 완료 항목 표기
- "7. Claude에게 줄 수정 요청 예시": 통합 반영 예시로 변경

---

### Task 4: reorder_chronological.py CLI 인자 지원

**변경 사항**

- `argparse` 도입: `files` (positional, nargs='*'), `--dry-run`
- 파일 존재 여부 검증 추가

**사용 예**

```powershell
py scripts/reorder_chronological.py
py scripts/reorder_chronological.py docs/quality-updates/2025/2025-01-01_to_2025-03-31.md
py scripts/reorder_chronological.py --dry-run
py scripts/reorder_chronological.py nonexistent.md   # → 에러 메시지 + exit 1
```

---

### Task 5: validate_content.py 신규 작성

**검증 항목**

1. **admonition 들여쓰기**: `!!!`/`???` 블록 내용 4칸 추가 들여쓰기
2. **빈 줄 규칙**: `!!!`/`???`과 첫 내용 줄 사이 빈 줄 필수
3. **YAML front matter**: `title`, `period`/`period_label` 필수
4. **날짜 형식**: `(YY-MM-DD)` 사용, `(YYYY-MM-DD)` 경고
5. **테이블 스키마**: Type A/B 제재 표 헤더 검증

**CLI**

- `files` (positional): 대상 파일, 미지정 시 `docs/quality-updates/` 전체
- `--strict`: 경고도 에러로 처리

**참고**

- 기존 콘텐츠에 Executive Summary / 기관별 요약 등의 `!!! success` 블록이 AGENT_INSTRUCTION과 다른 들여쓰기를 사용하는 경우가 있어, CI validate job은 `continue-on-error: true`로 설정함
- 추가 콘텐츠 수정 또는 검증 규칙 조정 후 `continue-on-error` 제거 권장

---

### Task 6: GitHub Actions CI

**파일**: `.github/workflows/ci.yml`

**Jobs**

- **lint**: markdownlint로 `docs/**/*.md` 검사 (AGENT_INSTRUCTION 제외)
- **build**: `mkdocs build --strict`
- **validate**: `python scripts/validate_content.py`

**트리거**: `push`, `pull_request` on `main`

**기타**

- `.markdownlint.json`: MD013, MD033, MD041 비활성화
- validate job: `continue-on-error: true` (기존 콘텐츠 검증 이슈 완화)

---

### Task 7: index.md 최신 콘텐츠 반영

**변경 사항**

- 규제 업데이트 바로가기: `2024-10-01_to_2024-12-31` → `2025-10-01_to_2025-12-31`
- Latest Update 블록: 2025 Q4 기준으로 갱신
- 사이트 구조: "2022~2024" → "2022~2025"
- copyright: 2025 → 2026 (`docs/index.md`, `mkdocs.yml`)

---

### Task 8: Dependabot 설정

**파일**: `.github/dependabot.yml`

- **pip**: `/` (requirements.txt), 매월
- **github-actions**: `/`, 매월

---

## 변경 파일 목록

| 파일 | 작업 |
|------|------|
| `.gitignore` | 수정 |
| `read_hwp.py` | 삭제 |
| `scripts/HWP_EXTRACT_INSTRUCTION.md` | 수정 |
| `scripts/reorder_chronological.py` | 수정 |
| `scripts/validate_content.py` | 신규 |
| `.github/workflows/ci.yml` | 신규 |
| `.markdownlint.json` | 신규 |
| `.github/dependabot.yml` | 신규 |
| `docs/index.md` | 수정 |
| `mkdocs.yml` | 수정 |
| `docs/quality-updates/2024/2024-10-01_to_2024-12-31.md` | 수정 (admonition 빈 줄 1건) |
| `docs/quality-updates/2025/2025-01-01_to_2025-03-31.md` | 수정 (reorder 실행으로 인한 재정렬) |

---

## 향후 작업

- [ ] 기존 콘텐츠의 ADMON_INDENT/TABLE_A 등 검증 이슈 정리 후 validate job에서 `continue-on-error` 제거
- [ ] 2022~2023 문서의 `(YYYY-MM-DD)` 형식 → `(YY-MM-DD)` 변환 검토
