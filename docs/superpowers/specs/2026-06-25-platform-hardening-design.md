# Quality Updates Platform Hardening — 통합 설계 스펙

**날짜**: 2026-06-25  
**상태**: 승인됨  
**범위**: 크롤러 통합(P1) + CI 강화(P2) + 배포 전처리(P3) + 편집기 Blueprint 분리(P4)

**관련 스펙**: `docs/superpowers/specs/2026-06-25-crawler-integration-design.md` (P1 상세)

---

## 개요

메인 Quality Updates 프로젝트는 MkDocs 사이트·Flask 큐레이션 편집기·에이전트 스킬로 성숙했으나, 크롤러가 별도 저장소에 분리되어 있고 CI·배포 전처리·편집기 구조에 기술 부채가 있다.

**목적**: 분기별 운영 파이프라인을 단일 저장소에서 end-to-end로 실행 가능하게 하고, 품질 게이트(CI·validate·pytest)와 배포 전처리를 자동화하며, 편집기 유지보수성을 높인다.

**범위 외 (이번 릴리스)**:
- 콘텐츠 백필 (2023 Q2, 2024 Q1·Q2 gold standard화)
- fss-review·홈 “추가 예정” 정리
- mkdocs nav/index **자동 적용** (diff 힌트만 제공)
- CI에서 실제 외부 크롤

---

## 확정 결정 (브레인스토밍)

| 항목 | 결정 |
|------|------|
| 구현 순서 | P1 → P2 → P3 → P4 (의존성 순차) |
| P1 크롤러 | 기존 crawler-integration 스펙 그대로 |
| P2 CI | pytest job 추가; validate `continue-on-error` 제거 |
| P3 배포 전처리 | skip 제거 + validate strict + nav/index **diff 힌트** (자동 패치 없음) |
| P4 편집기 | Flask Blueprint 분리; API 계약·`editor.js` 변경 없음 |

---

## P1: 크롤러 통합

`2026-06-25-crawler-integration-design.md` 참조. 요약:

- `scripts/crawl.py` + `scripts/crawler/`
- 출력: `docs/quality-updates/{start_year}/` — 파일 없을 때만 생성
- CLI: `--year --quarter`, `--force`, `--dry-run`
- `frequency: quarterly` only (2026+ monthly 분기 제거)
- `quality-updates-crawler/` 삭제

---

## P2: CI 강화

### pytest job

- `pip install -r requirements.txt -r requirements-dev.txt`
- `cd scripts && python -m pytest tests/ -q`
- 트리거: `push`/`pull_request` on `main`

### validate job

- `continue-on-error: true` **제거**
- `python scripts/validate_content.py --strict`
- 실패 시: `docs/quality-updates/` 포맷만 최소 수정 (admonition 들여쓰기, 날짜 형식 등)

### package.json

```json
"test": "cd scripts && python -m pytest tests/ -q",
"prepare:deploy": "python scripts/prepare_deploy.py"
```

---

## P3: `scripts/prepare_deploy.py`

### 실행

```bash
python scripts/prepare_deploy.py
python scripts/prepare_deploy.py --dry-run
python scripts/prepare_deploy.py docs/quality-updates/2025/2025-10-01_to_2025-12-31.md
```

### 처리 순서

1. **Skip 쌍 제거** — `parser.SKIP_RE`·`saver.py` CRLF 규칙과 동일  
   - 링크 줄 + `<!-- skip -->` (+ 허용 빈 줄) 삭제
2. **`validate_content --strict`** — skip 제거 후 검증
3. **nav / index 힌트** — unified diff stdout; 자동 적용 없음
   - `mkdocs.yml` nav에 없는 분기 `.md` 탐지
   - `docs/index.md` Latest Update 링크 vs 최신 `period.end` 불일치

### exit code

| 코드 | 의미 |
|------|------|
| 0 | 성공 (힌트만 있어도 0) |
| 1 | validate 실패 |
| 2 | 인자 오류 |

### 모듈 분리

- `scripts/skip_removal.py` — skip 제거 순수 함수 (테스트 가능)
- `scripts/deploy_hints.py` — nav/index diff 생성
- `scripts/prepare_deploy.py` — CLI 오케스트레이션

---

## P4: 편집기 Blueprint 분리

### 목표 구조

```
scripts/editor/
  app.py              # create_app(), blueprint 등록 (~80줄)
  config.py           # load/save config, repo_root, downloads policy
  preview_helpers.py  # preview HTML, jobs, OCR, security headers
  download_helpers.py # Content-Disposition, safe filenames
  routes/
    pages.py          # /, favicon
    files.py          # /api/files, links, downloads
    curation.py       # /api/save, sync, config
    clips.py          # /api/clips/*
    source.py         # /api/source/*
  parser.py, saver.py, source_fetch.py, clip_store.py, ...
```

### 제약

- URL·JSON 응답 형식 변경 없음
- `scripts/editor.py` → `from editor.app import app` 유지
- 완료 조건: `cd scripts && python -m pytest tests/ -q` 전부 통과

---

## 문서 갱신

| 파일 | 내용 |
|------|------|
| `README.md` | crawl, prepare_deploy, test |
| `CONTRIBUTING.md` | crawl → editor → skill → prepare_deploy → build |
| `docs/editor-curation-workflow.md` | 배포 전처리 절 |
| `quality-updates-writer` SKILL | SKIP_REMOVAL: prepare_deploy 우선 |

---

## 리스크

| 리스크 | 완화 |
|--------|------|
| validate strict로 CI 대량 실패 | P2에서 포맷-only 수정 선행 |
| Blueprint 분리 회귀 | P4 마지막; 기존 테스트 전부 유지 |
| prepare_deploy가 nav를 잘못 패치 | diff 힌트만; 자동 적용 없음 |

---

## 구현 체크리스트

- [ ] P1: 크롤러 통합 (crawler-integration 스펙)
- [ ] P2: CI pytest + validate strict + 콘텐츠 포맷 수정
- [ ] P3: skip_removal + deploy_hints + prepare_deploy
- [ ] P4: editor Blueprint 분리
- [ ] 문서·스킬 갱신
