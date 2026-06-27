# Platform Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 크롤러를 메인 repo에 통합하고, CI(pytest·validate strict)·배포 전처리(skip·힌트)·편집기 Blueprint 분리까지 완료하여 분기 운영 파이프라인을 단일 저장소에서 end-to-end로 실행 가능하게 한다.

**Architecture:** P1→P4 순차 구현. 크롤러는 `scripts/crawl.py` + `scripts/crawler/`; 배포 전처리는 `skip_removal` → `validate_content` → `deploy_hints` 오케스트레이션; 편집기는 Flask Blueprint로 라우트 분리하되 API 계약 불변.

**Tech Stack:** Python 3.11, Flask, pytest, MkDocs, argparse, PyYAML (front matter), 기존 requests/bs4/lxml

**Specs:**
- `docs/superpowers/specs/2026-06-25-platform-hardening-design.md`
- `docs/superpowers/specs/2026-06-25-crawler-integration-design.md` (P1)

---

## File map (전체)

| 파일 | 책임 |
|------|------|
| `scripts/crawl.py` | 크롤러 CLI 진입점 |
| `scripts/crawler/unified.py` | 수집·front matter·Appendix 조립 |
| `scripts/crawler/FSS.py` 등 | 기관별 크롤러 |
| `scripts/tests/test_crawl.py` | 크롤러 CLI·메타데이터 테스트 |
| `.github/workflows/ci.yml` | pytest job, validate strict |
| `scripts/skip_removal.py` | skip 쌍 제거 순수 함수 |
| `scripts/deploy_hints.py` | mkdocs.yml·index.md diff 힌트 |
| `scripts/prepare_deploy.py` | 배포 전처리 CLI |
| `scripts/tests/test_skip_removal.py` | skip 제거 테스트 |
| `scripts/tests/test_deploy_hints.py` | 힌트 생성 테스트 |
| `scripts/editor/config.py` | config·repo_root·downloads policy |
| `scripts/editor/preview_helpers.py` | preview·OCR·security headers |
| `scripts/editor/download_helpers.py` | filename·unique path helpers |
| `scripts/editor/routes/*.py` | Blueprint 라우트 |
| `scripts/editor/app.py` | create_app() 슬림화 |

---

## P1: 크롤러 통합

> 상세: `2026-06-25-crawler-integration-design.md`

### Task P1-1: crawler 패키지 스캐폴드

**Files:**
- Create: `scripts/crawler/__init__.py`
- Create: `scripts/crawler/unified.py` (from `quality-updates-crawler/unified_crawler.py`)
- Copy: `quality-updates-crawler/crawlers/*.py` → `scripts/crawler/`

- [ ] **Step 1: 디렉터리 생성 및 모듈 복사**

```bash
mkdir -p scripts/crawler
cp quality-updates-crawler/crawlers/*.py scripts/crawler/
cp quality-updates-crawler/unified_crawler.py scripts/crawler/unified.py
touch scripts/crawler/__init__.py
```

- [ ] **Step 2: unified.py import 수정**

`from crawlers import FSS` → `from crawler import FSS` (또는 `from . import FSS`)

- [ ] **Step 3: OUTPUT_DIR를 repo root 기준으로 변경**

```python
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent

OUTPUT_DIR = repo_root() / "docs" / "quality-updates" / str(start_year)
```

- [ ] **Step 4: compute_period_metadata — monthly 분기 제거**

항상 `frequency: quarterly`, `period_label: f"{YEAR}-Q{q}"` 반환.

- [ ] **Step 5: FSS.py 디버그 print 제거** (`### SCRIPT STARTED ###` 등)

- [ ] **Step 6: Commit**

```bash
git add scripts/crawler/
git commit -m "feat(crawler): move crawler modules into scripts/crawler"
```

---

### Task P1-2: crawl.py CLI

**Files:**
- Create: `scripts/crawl.py`
- Create: `scripts/tests/test_crawl.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`scripts/tests/test_crawl.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawl import parse_args, quarter_dates, compute_output_path

def test_quarter_dates_q1():
    start, end = quarter_dates(2026, 1)
    assert start == "2026-01-01"
    assert end == "2026-03-31"

def test_output_path_uses_start_year():
    p = compute_output_path("2022-12-15", "2023-04-03")
    assert "docs/quality-updates/2022" in str(p)
    assert p.name == "2022-12-15_to_2023-04-03.md"

def test_skip_if_exists(tmp_path, monkeypatch):
    # mock repo root + existing file → should_skip True
    ...
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```bash
cd scripts && python -m pytest tests/test_crawl.py -v
```

- [ ] **Step 3: crawl.py 구현**

```python
# scripts/crawl.py
"""Entry: python scripts/crawl.py [--year Y --quarter Q] [--start ... --end ...]"""
import argparse, sys, os
from pathlib import Path
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

def quarter_dates(year: int, quarter: int) -> tuple[str, str]:
    ...

def parse_args(argv=None):
    ...

def main():
    args = parse_args()
    # resolve dates, check exists + not force → skip exit 0
    # import crawler.unified, inject dates, run collection, atomic write os.replace
```

argparse 규칙:
- `--year` + `--quarter` 또는 `--start` + `--end`
- 둘 다 없으면 `date.today()` 기준 현재 분기
- `--year`만 있으면 exit 2

- [ ] **Step 4: 테스트 PASS 확인**

```bash
cd scripts && python -m pytest tests/test_crawl.py -v
```

- [ ] **Step 5: requirements.txt에 lxml, python-dateutil 추가**

```
lxml>=5.1.0
python-dateutil>=2.8.2
```

- [ ] **Step 6: Commit**

```bash
git add scripts/crawl.py scripts/tests/test_crawl.py requirements.txt
git commit -m "feat(crawler): add crawl.py CLI with quarter dates and skip-if-exists"
```

---

### Task P1-3: 정리 및 문서 (P1)

**Files:**
- Delete: `quality-updates-crawler/` (전체)
- Modify: `README.md`, `CONTRIBUTING.md`, `package.json`
- Modify: `.claude/skills/quality-updates-writer/SKILL.md` (BOILERPLATE 절)

- [ ] **Step 1: quality-updates-crawler/ 삭제**

```bash
rm -rf quality-updates-crawler/
```

- [ ] **Step 2: README에 크롤러 절 추가**

```bash
python scripts/crawl.py --year 2026 --quarter 1
```

- [ ] **Step 3: package.json**

```json
"crawl": "python scripts/crawl.py"
```

- [ ] **Step 4: dry-run으로 CLI 스모크 테스트 (네트워크)**

```bash
python scripts/crawl.py --year 2026 --quarter 1 --dry-run
```

Expected: `[INFO] Period: ...` 출력, 파일 미생성

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(crawler): remove nested repo, document crawl CLI"
```

---

## P2: CI 강화

### Task P2-1: validate 이슈 스캔 및 수정

**Files:**
- Modify: `docs/quality-updates/**/*.md` (포맷만)
- Modify: `scripts/validate_content.py` (필요 시)

- [ ] **Step 1: validate strict 로컬 실행**

```bash
python scripts/validate_content.py --strict
```

- [ ] **Step 2: 에러 목록별 최소 수정**

admonition 들여쓰기, `!!!`/`???` 빈 줄, `(YYYY-MM-DD)` → `(YY-MM-DD)` 경고 등. **본문 요약 내용 변경 금지.**

- [ ] **Step 3: 재실행 — exit 0 확인**

```bash
python scripts/validate_content.py --strict
echo $?
```

Expected: `0`

- [ ] **Step 4: Commit**

```bash
git add docs/quality-updates/
git commit -m "fix(docs): satisfy validate_content --strict"
```

---

### Task P2-2: CI workflow 갱신

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `package.json`

- [ ] **Step 1: test job 추가**

```yaml
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: cd scripts && python -m pytest tests/ -q
```

- [ ] **Step 2: validate job에서 continue-on-error 제거**

```yaml
  validate:
    name: Validate Content
    runs-on: ubuntu-latest
    steps:
      ...
      - run: python scripts/validate_content.py --strict
```

- [ ] **Step 3: package.json test 스크립트**

```json
"test": "cd scripts && python -m pytest tests/ -q"
```

- [ ] **Step 4: 로컬 pytest 전체 실행**

```bash
pip install -r requirements.txt -r requirements-dev.txt
cd scripts && python -m pytest tests/ -q
```

Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml package.json
git commit -m "ci: add pytest job, enforce validate_content --strict"
```

---

## P3: 배포 전처리

### Task P3-1: skip_removal 모듈

**Files:**
- Create: `scripts/skip_removal.py`
- Create: `scripts/tests/test_skip_removal.py`

- [ ] **Step 1: 실패 테스트 (parser/saver와 동일 케이스)**

```python
from skip_removal import remove_skip_pairs

SAMPLE = "- (25-01-10) [A](https://a.com)\n<!-- skip -->\n\n- (25-01-11) [B](https://b.com)\n"

def test_removes_skip_pair():
    out = remove_skip_pairs(SAMPLE)
    assert "<!-- skip -->" not in out
    assert "[A]" not in out
    assert "[B]" in out

def test_crlf():
    ...
```

- [ ] **Step 2: pytest FAIL 확인**

- [ ] **Step 3: skip_removal.py 구현**

`parser.LINK_RE`, `parser.SKIP_RE` 재사용 또는 동일 정규식 import. Appendix 이후 무시. `## Appendix` 전까지만 처리.

- [ ] **Step 4: pytest PASS**

- [ ] **Step 5: Commit**

```bash
git add scripts/skip_removal.py scripts/tests/test_skip_removal.py
git commit -m "feat(deploy): add skip pair removal for prepare_deploy"
```

---

### Task P3-2: deploy_hints 모듈

**Files:**
- Create: `scripts/deploy_hints.py`
- Create: `scripts/tests/test_deploy_hints.py`

- [ ] **Step 1: 테스트 — nav 누락 탐지**

```python
def test_missing_nav_entry(tmp_path):
  # minimal mkdocs.yml + md with front matter → hint contains path
```

- [ ] **Step 2: deploy_hints.py 구현**

- `collect_period_files(docs_root)` — YAML `period.start/end` 파싱
- `nav_paths_from_mkdocs(mkdocs_yml)` — nav 트리에서 `.md` 경로 집합
- `hint_missing_nav(...)` → unified diff str
- `hint_index_latest(docs_index, latest_end)` → diff str if mismatch

- [ ] **Step 3: pytest PASS**

- [ ] **Step 4: Commit**

```bash
git add scripts/deploy_hints.py scripts/tests/test_deploy_hints.py
git commit -m "feat(deploy): add mkdocs nav and index diff hints"
```

---

### Task P3-3: prepare_deploy CLI

**Files:**
- Create: `scripts/prepare_deploy.py`
- Modify: `README.md`, `CONTRIBUTING.md`, `docs/editor-curation-workflow.md`
- Modify: `.claude/skills/quality-updates-writer/SKILL.md`

- [ ] **Step 1: prepare_deploy.py 구현**

```python
def main():
    # 1. glob files (or single path arg)
    # 2. for each: remove_skip_pairs (or dry-run count)
    # 3. write or skip write if dry-run
    # 4. validate_content.validate_file(..., strict=True)
    # 5. print deploy_hints to stdout
```

- [ ] **Step 2: --dry-run 스모크**

```bash
python scripts/prepare_deploy.py --dry-run docs/quality-updates/2025/2025-10-01_to_2025-12-31.md
```

- [ ] **Step 3: package.json**

```json
"prepare:deploy": "python scripts/prepare_deploy.py"
```

- [ ] **Step 4: 문서·스킬 갱신** (워크플로에 prepare_deploy 단계)

- [ ] **Step 5: Commit**

```bash
git add scripts/prepare_deploy.py README.md CONTRIBUTING.md docs/editor-curation-workflow.md .claude/skills/quality-updates-writer/SKILL.md package.json
git commit -m "feat(deploy): add prepare_deploy orchestration and docs"
```

---

## P4: 편집기 Blueprint 분리

### Task P4-1: config·helpers 추출

**Files:**
- Create: `scripts/editor/config.py`
- Create: `scripts/editor/download_helpers.py`
- Create: `scripts/editor/preview_helpers.py`
- Modify: `scripts/editor/app.py`

- [ ] **Step 1: config.py 추출**

`load_config`, `save_config`, `repo_root`, `_normalize_downloads_folder` 이동.

- [ ] **Step 2: download_helpers.py 추출**

`_parse_content_disposition_filename`, `_safe_pdf_storage_name`, `_unique_file_path` 등.

- [ ] **Step 3: preview_helpers.py 추출**

`_build_preview_document`, `_apply_preview_security_headers`, preview job 함수들.

- [ ] **Step 4: app.py에서 import로 교체**

- [ ] **Step 5: pytest 전체 PASS**

```bash
cd scripts && python -m pytest tests/ -q
```

- [ ] **Step 6: Commit**

```bash
git add scripts/editor/
git commit -m "refactor(editor): extract config and helper modules from app.py"
```

---

### Task P4-2: Blueprint 라우트 분리

**Files:**
- Create: `scripts/editor/routes/__init__.py`
- Create: `scripts/editor/routes/pages.py`
- Create: `scripts/editor/routes/files.py`
- Create: `scripts/editor/routes/curation.py`
- Create: `scripts/editor/routes/clips.py`
- Create: `scripts/editor/routes/source.py`
- Modify: `scripts/editor/app.py`

- [ ] **Step 1: pages blueprint** — `/`, `/favicon.ico`

```python
# routes/pages.py
from flask import Blueprint
pages_bp = Blueprint("pages", __name__)
```

- [ ] **Step 2: files blueprint** — `/api/files`, `/api/links`, `/api/downloads`, clear

- [ ] **Step 3: curation blueprint** — `/api/save`, sync, `/api/config`

- [ ] **Step 4: clips blueprint** — `/api/clips/*`

- [ ] **Step 5: source blueprint** — `/api/source/*`

- [ ] **Step 6: app.py → create_app()**

```python
def create_app():
    app = Flask(__name__)
    app.register_blueprint(pages_bp)
    ...
    return app

app = create_app()
```

- [ ] **Step 7: pytest 전체 PASS + 수동 스모크**

```bash
cd scripts && python -m pytest tests/ -q
# 별도 터미널: python scripts/editor.py → /api/files 200
```

- [ ] **Step 8: Commit**

```bash
git add scripts/editor/
git commit -m "refactor(editor): split Flask routes into blueprints"
```

---

## 최종 검증

- [ ] **Step 1: 전체 테스트**

```bash
pip install -r requirements.txt -r requirements-dev.txt
cd scripts && python -m pytest tests/ -q
python scripts/validate_content.py --strict
```

- [ ] **Step 2: MkDocs strict build**

```bash
mkdocs build --strict
```

- [ ] **Step 3: 파이프라인 스모크 (선택)**

```bash
python scripts/crawl.py --year 2026 --quarter 2 --dry-run
python scripts/prepare_deploy.py --dry-run
```

---

## 커밋 순서 요약

1. `feat(crawler): move modules`
2. `feat(crawler): add crawl.py CLI`
3. `chore(crawler): remove nested repo, docs`
4. `fix(docs): validate strict`
5. `ci: pytest + validate strict`
6. `feat(deploy): skip_removal`
7. `feat(deploy): deploy_hints`
8. `feat(deploy): prepare_deploy`
9. `refactor(editor): extract helpers`
10. `refactor(editor): blueprints`
