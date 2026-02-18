# Quality Updates

회계·감사 분야 규제 모니터링을 위한 정적 문서 사이트입니다.  
금융위원회·금융감독원·회계기준원 등 주요 기관의 보도자료, 제도 개정, 감리 결과를 시기별로 정리하여 제공합니다.

- **사이트**: [https://quality-updates.onrender.com](https://quality-updates.onrender.com)
- **빌드**: [MkDocs](https://www.mkdocs.org/) + [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)

---

## 목차

- [기능](#기능)
- [로컬 개발 환경 설정](#로컬-개발-환경-설정)
- [프로젝트 구조](#프로젝트-구조)
- [콘텐츠 업데이트 가이드](#콘텐츠-업데이트-가이드)
- [배포](#배포)
- [기여](#기여)

---

## 기능

- **규제 업데이트**: 분기별(또는 기간별) 보도자료·제도 변경 정리 (2022년~현재)
- **품질관리감리**: 금융감독원 회계법인 품질관리감리 관련 문서 요약
- **한국어 우선**: 검색·탐색·테마(라이트/다크) 한국어 지원
- **반응형**: 데스크톱·태블릿·모바일 대응
- **검색**: MkDocs Material 검색 (한국어 구분자 지원)
- **이미지 라이트박스**: glightbox 플러그인
- **HTML/CSS/JS 최소화**: minify 플러그인으로 출력 최적화
- **CI**: GitHub Actions (markdownlint, MkDocs 빌드, 콘텐츠 검증)

---

## 로컬 개발 환경 설정

### 요구사항

- **Python**: 3.8 이상
- **Node.js** (선택): `package.json` 스크립트(dev, lint) 사용 시

### 1. 저장소 복제

```bash
git clone https://github.com/ypspy/quality-updates.git
cd quality-updates
```

### 2. Python 가상환경 및 의존성

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 로컬 서버 실행

```bash
mkdocs serve
```

브라우저에서 [http://127.0.0.1:8000](http://127.0.0.1:8000) 로 접속합니다.

### 4. npm 스크립트 (선택)

Node.js가 설치되어 있다면:

```bash
npm install
npm run dev          # mkdocs serve (동일)
npm run build        # mkdocs build
npm run build:strict # mkdocs build --strict (경고 시 실패)
npm run lint:md      # markdownlint-cli (docs 기준, AGENT_INSTRUCTION 제외)
npm run clean        # site, .cache 등 빌드 산출물 삭제
```

### 5. 스크립트 (콘텐츠 작업용)

```bash
# PDF 텍스트 추출
python scripts/extract_pdf.py

# HWP 텍스트 추출 (경로 지정 또는 최근 수정 .hwp 자동 탐색)
python scripts/extract_hwp.py
python scripts/extract_hwp.py --path "경로/파일.hwp"

# 분기 문서 시계열 정렬
python scripts/reorder_chronological.py docs/quality-updates/2025/2025-01-01_to_2025-03-31.md

# 콘텐츠 검증 (admonition, YAML, 날짜 형식 등)
python scripts/validate_content.py
```

### 6. 엄격 빌드 검증

배포 전 로컬에서 다음을 권장합니다.

```bash
# 가상환경 활성화 상태에서
mkdocs build --strict
```

경고가 있으면 빌드가 실패하므로, 링크·설정·문서 오류를 먼저 수정해야 합니다.

---

## 프로젝트 구조

```
quality-updates/
├── docs/                          # 문서 소스 (MkDocs 소스 루트)
│   ├── index.md                   # 홈페이지
│   ├── assets/
│   │   ├── images/                # 이미지 (로고 등)
│   │   ├── icons/
│   │   ├── stylesheets/extra.css  # 추가 CSS
│   │   └── javascripts/extra.js   # 추가 JS
│   ├── quality-updates/           # 규제 업데이트
│   │   ├── index.md               # 규제 업데이트 개요
│   │   ├── 2022/
│   │   ├── 2023/
│   │   ├── 2024/
│   │   └── 2025/
│   └── fss-review/                # 품질관리감리
│       ├── index.md
│       └── fr2022.md
├── overrides/
│   └── partials/                  # Material 테마 오버라이드
│       ├── header.html
│       └── footer.html
├── mkdocs.yml                     # MkDocs 설정
├── requirements.txt               # Python 의존성 (버전 고정)
├── package.json                   # npm 스크립트 및 devDependencies
├── .editorconfig                  # 에디터 포맷 규칙
├── .markdownlint.json             # Markdown 린트 설정
├── .github/
│   ├── workflows/ci.yml           # CI (lint, build, validate)
│   └── dependabot.yml             # 의존성 자동 업데이트
├── scripts/                       # 유틸리티 스크립트
│   ├── extract_pdf.py             # PDF 텍스트 추출
│   ├── extract_hwp.py             # HWP 텍스트 추출
│   ├── reorder_chronological.py   # 콘텐츠 시계열 정렬
│   ├── validate_content.py        # 콘텐츠 스키마 검증
│   └── tests/                     # 스크립트 단위 테스트
├── README.md                      # 이 파일
├── CONTRIBUTING.md                # 기여 가이드
└── IMPLEMENTATION_LOG.md          # 개선 작업 실행 로그
```

- **탐색 구조**: `mkdocs.yml`의 `nav`에서 메뉴·레이블·파일 매핑을 정의합니다.
- **스타일/스크립트**: `docs/assets/` 아래 파일은 `mkdocs.yml`의 `extra_css`, `extra_javascript`로 로드됩니다.

---

## 콘텐츠 업데이트 가이드

### 분기별 규제 업데이트 문서

새 기간 문서를 추가할 때는 아래 YAML 프론트매터 템플릿을 사용하세요.  
파일명은 `YYYY-MM-DD_to_YYYY-MM-DD.md` 형태를 권장합니다 (예: `2025-01-01_to_2025-03-31.md`).

**프론트매터 템플릿**

```yaml
---
title: YYYY-MM-DD ~ YYYY-MM-DD 규제 업데이트
description: [기간] 회계·감사 분야 규제 변화 및 주요 이슈 정리
jurisdiction: KR
year: YYYY
frequency: quarterly
period_label: YYYY-QX
period:
  start: YYYY-MM-DD
  end: YYYY-MM-DD
category: Quality Updates
agencies: [FSS, FSC, KICPA, KASB]
tags: [규제 업데이트, 회계기준, 감사감리, 금융감독]
---
```

- **title**: 페이지 제목 (탐색·검색에 사용)
- **description**: 요약 설명 (SEO·검색 결과용)
- **jurisdiction**: 관할 (한국: KR)
- **year**, **period_label**, **period**: 기간 정보
- **agencies**: 언급 기관 (FSS, FSC, KICPA, KASB 등)
- **tags**: 검색·필터용 태그

문서 본문은 기존 분기별 파일과 동일한 형식(금융감독원, 보도자료 등 섹션)을 따르면 됩니다.  
추가 후 **반드시 `mkdocs.yml`의 `nav`에 새 페이지를 등록**해야 사이드바/탭에 표시됩니다.

### 품질관리감리·기타 문서

- 새 문서에도 `title`, `description` 등 최소 프론트매터를 두는 것을 권장합니다.
- 이미지 추가 시 `CONTRIBUTING.md`의 이미지·alt 텍스트 가이드라인을 참고하세요.

자세한 워크플로우·커밋 규칙·테스트 체크리스트는 **[CONTRIBUTING.md](CONTRIBUTING.md)** 를 참조하세요.

---

## 배포

- **플랫폼**: [Render](https://render.com)
- **동작**: `main` 브랜치 푸시 시 자동 빌드·배포
- **빌드 명령**: `pip install -r requirements.txt && mkdocs build`
- **출력 디렉터리**: `site/`
- **사이트 URL**: [https://quality-updates.onrender.com](https://quality-updates.onrender.com)

Render 대시보드에서 환경 변수·브랜치·빌드 명령을 변경할 수 있습니다.  
로컬에서는 `mkdocs build --strict`로 동일한 빌드 결과를 검증할 수 있습니다.

---

## 기여

버그 제보, 문서 수정, 개선 제안은 이슈와 Pull Request로 환영합니다.  
진행 절차와 스타일 가이드는 **[CONTRIBUTING.md](CONTRIBUTING.md)** 에 정리되어 있습니다.

---

## 라이선스·저작권

© 2026 Quality Updates.  
사이트 내 저작권 문구는 `mkdocs.yml`의 `copyright` 및 푸터 오버라이드에 정의되어 있습니다.
