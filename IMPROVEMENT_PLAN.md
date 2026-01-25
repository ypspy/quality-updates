# Quality Updates 프로젝트 종합 개선 계획

## 요약

Quality Updates 문서 사이트의 **87개 개선사항**을 8개 카테고리에 걸쳐 체계적으로 해결하는 6단계 개선 계획입니다. 한국 회계·감사 규제 모니터링 플랫폼으로서 분기별 업데이트 워크플로우를 유지하면서 현대화를 진행합니다.

**예상 소요시간**: 4-6시간
**접근방식**: 중요 수정사항부터 시작하여 단계적으로 완전한 현대화 달성

**진행 현황**: 1단계(기초 및 중요 수정) 완료 (2025-01-25), 2단계(MkDocs 설정 강화) 완료 (2025-01-25), 3단계(콘텐츠 표준화) 완료 (2025-01-25)

---

## 발견된 문제점 개요

- **문서 품질** (12개): 메타데이터 누락, 일관성 없는 구조, 홈페이지 정보 과거, 빈 JS 파일
- **MkDocs 설정** (15개): 플러그인 누락(minify, glightbox), 색상 테마 없음, SEO 설정 없음
- **콘텐츠 구성** (11개): 탐색 레이블 부실, 인덱스 페이지 없음, 프론트매터 불일치
- **코드 품질** (10개): CSS iframe 버그(100vw), 하드코딩된 값, 반응형 디자인 부족
- **개발 워크플로우** (14개): CI/CD 없음, .editorconfig 누락, .gitignore 불충분, 기여자 문서 없음
- **접근성 및 UX** (9개): ARIA 레이블 누락, alt 텍스트 가이드 없음, 검색 설정 불완전
- **성능** (8개): 대용량 파일, 압축 없음, 사용하지 않는 플러그인
- **유지보수** (8개): 버전 고정 없음, package.json 불일치, 홈페이지 정보 과거

---

## 1단계: 기초 및 중요 수정 (30-45분) ✅ 완료

> **완료 일자**: 2025-01-25

### 1.1 CSS 버그 수정 ✅
**파일**: `docs\assets\stylesheets\extra.css`

- **17번째 줄**: `width: 100vw;` → `width: 100%;` (가로 스크롤 버그 수정)
- `max-width: 100%;` 제약 추가
- 모바일/태블릿용 반응형 미디어 쿼리 추가 (태블릿 76.1875em, 모바일 44.9375em)
- 인쇄 스타일 추가 (@media print)

### 1.2 빈 JavaScript 파일 처리 ✅
**파일**: `docs\assets\javascripts\extra.js`

- 주석과 IIFE 래퍼로 적절한 구조 추가
- 향후 커스텀 기능을 위해 예약

### 1.3 .gitignore 확장 ✅
**파일**: `.gitignore`

- Python 아티팩트: __pycache__/, *.pyc, venv/, .venv/, *.egg-info/, .cache/ 등
- IDE/에디터: .vscode/, .idea/, .DS_Store, Thumbs.db
- 기타: *.log, .env

### 1.4 의존성 버전 고정 ✅
**파일**: `requirements.txt`

- 버전 고정: mkdocs==1.5.3, mkdocs-material==9.5.3, mkdocs-git-revision-date-localized-plugin==1.2.0
- 미사용 제거: mkdocs-awesome-pages-plugin (mkdocs.yml에 없음)

**검증**: 가상환경 활성화 후 `pip install -r requirements.txt` → `mkdocs serve` + 반응형 동작 테스트, `mkdocs build --strict`

---

## 2단계: MkDocs 설정 강화 (45-60분) ✅ 완료

> **완료 일자**: 2025-01-25

### 2.1 테마 커스터마이징 추가 ✅
**파일**: `mkdocs.yml`

**8번째 줄 이후** (favicon 다음)에 추가:
```yaml
  palette:
    - scheme: default
      primary: black
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: 다크 모드로 전환
    - scheme: slate
      primary: black
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: 라이트 모드로 전환
  font:
    text: Noto Sans KR
    code: Roboto Mono
```

**features에 추가** (19번째 줄 이후):
- navigation.footer
- navigation.indexes
- navigation.tracking
- search.share
- content.code.annotate
- content.tooltips

### 2.2 누락된 플러그인 추가 ✅
**plugins 섹션 교체** (56-59번째 줄):
- 한국어 구분자로 검색 개선
- Asia/Seoul 시간대로 git-revision-date 설정
- minify 플러그인 추가 (HTML/CSS/JS 최적화)
- glightbox 플러그인 추가 (이미지 라이트박스)

**requirements.txt 업데이트**:
- 추가: mkdocs-minify-plugin==0.7.1
- 추가: mkdocs-glightbox==0.3.5
- 추가: pillow==10.1.0, cairosvg==2.7.1

### 2.3 소셜 및 SEO 설정 추가 ✅
**plugins 다음에 새 섹션 추가**:
```yaml
extra:
  social:
    - icon: fontawesome/solid/building
      link: https://quality-updates.onrender.com
  analytics:
    feedback: [페이지 도움 여부 평가]
copyright: >
  Copyright &copy; 2025 Quality Updates...
```
(저작권은 mkdocs.yml 최상위 `copyright`로 설정됨)

### 2.4 템플릿 하드코딩 URL 수정 ✅
**파일**:
- `overrides\partials\header.html` 17번째 줄: `/policy` → `{{ config.site_url or '/' }}`
- `overrides\partials\footer.html`: MkDocs 네이티브 footer 탐색을 사용하도록 완전히 재작성

**검증**: 가상환경에서 `mkdocs serve` 실행 후 색상 테마 전환, 검색, 이미지 라이트박스, footer 탐색 테스트

#### 2단계 재점검 (2025-01-25)

| 항목 | 상태 | 비고 |
|------|------|------|
| **2.1 palette** | ✅ | default/slate, primary black, accent indigo, 한글 토글 문구 반영됨 |
| **2.1 font** | ✅ | Noto Sans KR, Roboto Mono |
| **2.1 features** | ✅ | navigation.footer, indexes, tracking, search.share, content.code.annotate, content.tooltips 포함 |
| **2.2 search** | ✅ | `lang: ko`, `separator: '[\s\-\.]+'` 적용 |
| **2.2 git-revision-date** | ⚠️ | 설정값은 있으나 **의도적으로 주석 처리** (Git PATH 없을 때 빌드 방지). *가상환경과 무관.* |
| **2.2 minify / glightbox** | ✅ | plugins 및 requirements.txt 반영 |
| **2.2 requirements** | ⚠️ | pillow, cairosvg는 `>=` 사용 (계획은 `==`). *가상환경과 무관, 선택 사항.* |
| **2.3 extra.social** | ✅ | building 아이콘, site 링크 |
| **2.3 extra.analytics.feedback** | ✅ | `title: 페이지 도움 여부 평가` |
| **2.3 copyright** | ✅ | 최상위 `copyright`에 2025 문구 |
| **2.4 header.html** | ✅ | `{{ config.site_url or '/' }}` 사용, 하드코딩 URL 없음 |
| **2.4 footer.html** | ✅ | 네이티브 이전/다음 탐색, 저작권, 소셜 링크 |

**참고**: ⚠️는 "미통과"가 아니라 **계획과 의도적으로 다르게 적용된 부분**이며, 가상환경과는 무관하다.  
**빌드 검증**: 가상환경에서 `pip install -r requirements.txt` 후 `mkdocs build --strict` 실행 시 **성공** 확인됨.

---

## 3단계: 콘텐츠 표준화 (60-90분) ✅ 완료

> **완료 일자**: 2025-01-25

### 3.1 모든 파일에 YAML 프론트매터 추가 ✅
**분기별 업데이트 패턴**:
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

**프론트매터 없는 6개 파일에 적용**:
- 2023년 분기별 파일 전체 (5개)
- 2022년 파일 (1개)
- fss-review/fr2022.md

(구현: 2022·2023 분기별 6개 + fss-review/fr2022.md 1개에 계획 패턴 적용. 2024 파일은 기존 frontmatter 유지.)

### 3.2 홈페이지 업데이트 ✅
**파일**: `docs\index.md`

- 1번째 줄에 프론트매터 추가
- **15-16번째 줄**: 깨진 링크 수정 `/` → `quality-updates/2024/2024-10-01_to_2024-12-31.md`
- **29-34번째 줄**: "Latest Update" 2023-12-31 → 2024-12-31로 갱신
- **38-44번째 줄**: 사이트 구조 섹션 업데이트 (2022~2024, 2022~2023 아님)

(구현: 1번째 줄에 frontmatter 추가, 규제 업데이트 링크를 `quality-updates/2024/2024-10-01_to_2024-12-31.md`로 수정, Latest Update 2024-10-01~2024-12-31로 갱신, 사이트 구조 2022~2024로 수정.)

### 3.3 인덱스 페이지 생성 ✅
**새 파일**:
- `docs\quality-updates\index.md` - 연도/분기 링크가 있는 탐색 허브
- `docs\fss-review\index.md` - 섹션 랜딩 페이지

(구현: 규제 업데이트·품질관리감리 개요 페이지 추가, 연도별 링크 안내.)

### 3.4 탐색 레이블 개선 ✅
**파일**: `mkdocs.yml` nav 섹션

원시 파일명을 설명적인 한국어 레이블로 교체:
```yaml
nav:
  - 홈: index.md
  - 규제 업데이트:
      - quality-updates/index.md
      - 2024년:
          - 4분기 (10-12월): quality-updates/2024/2024-10-01_to_2024-12-31.md
          - 3분기 (07-09월): quality-updates/2024/2024-07-01_to_2024-09-30.md
          ...
```

(구현: 규제 업데이트·품질관리감리 각각 "개요" 페이지를 첫 항목으로 두고, 2024/2023/2022년을 "N분기 (월–월)" 등 한국어 레이블로 교체.)

**검증**: 프론트매터 렌더링, 탐색 작동, 검색에서 메타데이터 발견, 브레드크럼 표시 확인

#### 3단계 완료 요약 (2025-01-25)

| 항목 | 상태 | 비고 |
|------|------|------|
| **3.1 프론트매터** | ✅ | 2022 1개, 2023 5개, fss-review/fr2022.md 1개 적용. 2024 파일은 기존 구조 유지 |
| **3.2 index.md** | ✅ | frontmatter, 최신 링크(2024 4분기), Latest Update 2024-12 갱신, 사이트 구조 2022~2024 |
| **3.3 인덱스 페이지** | ✅ | quality-updates/index.md, fss-review/index.md 생성 |
| **3.4 nav 레이블** | ✅ | 규제 업데이트 개요, 품질관리감리 개요 및 연도·분기별 한국어 레이블 반영 |

---

## 4단계: 개발 문서화 (30-45분)

### 4.1 프로젝트 문서 생성

**새 파일**: `README.md` (200줄 이상)
- 프로젝트 개요 및 기능
- 로컬 개발 환경 설정 (venv, pip install, mkdocs serve)
- 프로젝트 구조 다이어그램
- 프론트매터 템플릿이 포함된 콘텐츠 업데이트 가이드
- 배포 정보 (Render 자동 배포)
- 기여 가이드라인 참조

**새 파일**: `CONTRIBUTING.md` (300줄 이상)
- 이슈 보고 가이드라인
- Pull Request 워크플로우
- 코드 스타일 가이드 (Markdown, YAML, CSS, JS)
- 커밋 메시지 규칙
- 콘텐츠 추가 절차
- 테스트 체크리스트
- 이미지/alt 텍스트 가이드라인
- 성능 고려사항

### 4.2 개발 도구 추가

**새 파일**: `.editorconfig`
- 에디터 간 일관된 포맷팅
- .md, .yml, .css, .js 파일에 대한 들여쓰기 규칙

**새 파일**: `.markdownlint.json`
- Markdown 린팅 규칙
- 한국어 콘텐츠를 위해 MD013(줄 길이) 비활성화

### 4.3 package.json 확장
- npm 스크립트 추가 (dev, build:strict, clean, lint:md)
- 적절한 메타데이터 추가 (description, keywords, repository)
- devDependencies 추가: markdownlint-cli

**검증**: 브라우저에서 문서 읽기, IDE에서 .editorconfig 테스트

---

## 5단계: CI/CD 및 자동화 (45-60분)

### 5.1 GitHub Actions 워크플로우

**새 파일**: `.github\workflows\deploy.yml`

**작업**:
1. **lint**: markdownlint-cli2-action으로 Markdown 린팅
2. **build**: 의존성 설치, --strict로 빌드, 링크 확인
3. **deploy**: main 브랜치 푸시 시 트리거 (참고: Render 자동 배포)

### 5.2 링크 체커 설정

**새 파일**: `.github\workflows\link-check-config.json`
- localhost URL 무시
- 타임아웃: 20초, 429에서 재시도
- 허용 상태 코드: 200, 301, 302, 307, 308

### 5.3 Dependabot 설정

**새 파일**: `.github\dependabot.yml`
- pip 의존성 월간 확인
- GitHub Actions 버전 월간 확인
- PR 자동 레이블링

**검증**: GitHub에 푸시, 워크플로우 실행 확인, Dependabot 설정 확인

---

## 6단계: 접근성 및 성능 (30-45분)

### 6.1 접근성 향상
**파일**: `mkdocs.yml`

extra 섹션에 추가:
- 쿠키 동의 설정 (한국어 텍스트)
- 추가 markdown 확장 (abbr, md_in_html, emoji, keys)

### 6.2 접근성 CSS
**파일**: `docs\assets\stylesheets\extra.css`

끝에 추가:
- 포커스 표시기 (outline: 2px solid)
- 콘텐츠로 건너뛰기 링크 스타일
- 링크 대비 개선 (text-decoration-thickness)
- 테이블 호버 상태 개선 (라이트/다크 모드)
- prefers-reduced-motion 지원
- 인쇄 스타일 (헤더/푸터 숨김, 링크 URL 표시)

### 6.3 성능 최적화

**mkdocs.yml에 추가**:
- 상단에 성능 예산 주석
- sitemap 플러그인 설정

**새 파일**: `docs\robots.txt`
- 모두 허용, 사이트맵 URL 포함

### 6.4 문서 업데이트
**파일**: `CONTRIBUTING.md`

섹션 추가:
- 이미지 alt 텍스트 가이드라인
- 성능 고려사항 (파일 크기 제한)
- 대용량 파일 분할 권장사항
- 이미지 최적화 명령어

**검증**: 키보드 탐색, 스크린 리더, 인쇄 레이아웃 테스트, sitemap.xml 생성 확인

---

## 수정할 주요 파일

### 기존 파일 (15개)
1. `docs\assets\stylesheets\extra.css` - iframe 버그 수정, 반응형/접근성 스타일 추가
2. `docs\assets\javascripts\extra.js` - 적절한 구조 추가
3. `mkdocs.yml` - 주요 설정 점검 (palette, plugins, nav, extra)
4. `requirements.txt` - 버전 고정, 플러그인 4개 추가, 미사용 1개 제거
5. `.gitignore` - 2줄에서 60줄 이상으로 확장
6. `overrides\partials\header.html` - 하드코딩 URL 수정
7. `overrides\partials\footer.html` - 완전히 재작성
8. `docs\index.md` - 프론트매터 추가, 링크 수정, 날짜 업데이트
9. `docs\fss-review\fr2022.md` - 프론트매터 추가
10. `docs\quality-updates\2023\2023-10-01_to_2023-12-31.md` - 프론트매터 추가
11. `docs\quality-updates\2023\2023-08-31_to_2023-09-30.md` - 프론트매터 추가
12. `docs\quality-updates\2023\2023-07-14_to_2023-08-31.md` - 프론트매터 추가
13. `docs\quality-updates\2023\2023-05-08_to_2023-07-14.md` - 프론트매터 추가
14. `docs\quality-updates\2023\2023-04-03_to_2023-05-08.md` - 프론트매터 추가
15. `docs\quality-updates\2022\2022-12-15_to_2023-04-03.md` - 프론트매터 추가

### 새 파일 (11개)
1. `README.md` - 종합 프로젝트 문서
2. `CONTRIBUTING.md` - 기여자 가이드라인
3. `.editorconfig` - 코드 스타일 적용
4. `.markdownlint.json` - Markdown 린팅 규칙
5. `docs\quality-updates\index.md` - 탐색 허브
6. `docs\fss-review\index.md` - 섹션 랜딩 페이지
7. `docs\robots.txt` - SEO 최적화
8. `.github\workflows\deploy.yml` - CI/CD 파이프라인
9. `.github\workflows\link-check-config.json` - 링크 체커 설정
10. `.github\dependabot.yml` - 의존성 자동화
11. `package.json` - npm 스크립트 강화 (기존 최소 파일 확장)

---

## 구현 순서

```
1단계 (기초 - 먼저 진행 필수) ✅ 완료
    ↓
2단계 (설정 - 1단계 수정에 의존)
    ↓
3단계 (콘텐츠 - 2단계 탐색에 의존)
    ↓
4, 5, 6단계는 3단계 이후 병렬 진행 가능
```

---

## 전체 검증

**원칙**: 모든 빌드·실행 검증은 **가상환경(venv)**에서 수행한다. 전역 Python에 플러그인(minify, glightbox 등)이 없으면 빌드가 실패할 수 있음.

### 빌드 및 서브 테스트
```bash
# 가상환경 생성 및 활성화
# Windows (PowerShell): .\setup-venv.ps1 또는 수동으로:
#   python -m venv venv
#   .\venv\Scripts\activate
# Linux/macOS:
rm -rf venv site/ .cache/
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

pip install -r requirements.txt

# 엄격한 빌드 (경고 불허) — 가상환경에서 성공 확인됨
mkdocs build --strict --verbose

# 서브 및 수동 테스트
mkdocs serve
```

### 수동 테스트 체크리스트
- [ ] 탐색이 원활하게 작동 (탭, 섹션, 브레드크럼)
- [ ] 검색이 한국어 콘텐츠를 정확히 찾음
- [ ] 색상 테마 전환 (라이트/다크) 작동
- [ ] 이미지 라이트박스 열림/닫힘 정상
- [ ] 반응형 테이블이 모바일에서 작동
- [ ] Footer 이전/다음 탐색
- [ ] 인쇄 레이아웃이 깔끔하게 표시
- [ ] 키보드 탐색 (Tab, Enter, Escape)
- [ ] 스크린 리더가 적절히 읽음
- [ ] 모든 링크 작동 (404 없음)
- [ ] 빌드가 경고 없이 완료

### 브라우저 테스트
- 데스크톱: Chrome, Firefox, Safari
- 태블릿: iPad (Safari), Android 태블릿
- 모바일: iPhone (Safari), Android (Chrome)

### 성능 벤치마크
배포 후:
- Lighthouse 점수 > 90 (모든 카테고리)
- PageSpeed Insights: 모든 지표 "양호"
- 일반 페이지 총 무게 < 1MB
- First Contentful Paint < 1.5초

---

## 성공 기준

완료 시:
- ✅ CSS 버그 제로 (iframe 너비 수정, 반응형 디자인 작동)
- ✅ 완전한 MkDocs Material 기능 세트 활성화
- ✅ 12개 콘텐츠 파일 모두 표준화된 YAML 프론트매터 보유
- ✅ 인덱스 페이지 및 한국어 레이블로 탐색 개선
- ✅ 종합 프로젝트 문서 (README, CONTRIBUTING)
- ✅ 린팅 및 링크 확인이 포함된 자동화 CI/CD 파이프라인
- ✅ WCAG AA 접근성 준수
- ✅ 최적화된 성능 (압축, 캐싱 헤더)
- ✅ 적절한 의존성 관리 (버전 고정, Dependabot)
- ✅ 전문적인 개발 워크플로우 (EditorConfig, 린팅)

---

## 롤백 전략

중요한 문제 발생 시:
1. **시작 전**: 백업 브랜치 생성
   ```bash
   git checkout -b backup-before-overhaul
   git push origin backup-before-overhaul
   ```
2. **1-2단계 중**: 특정 설정 파일 되돌리기
3. **3단계 중**: 콘텐츠 변경은 추가적 (위험 낮음)
4. **4-6단계 중**: 필요시 새 파일 삭제

---

## 참고사항

- 전체적으로 한국어 지원 유지
- 콘텐츠 무결성 보존 (규제 데이터 변경 없음)
- 분기별 업데이트 워크플로우 간단하게 유지
- 사이트 URL 유지: https://quality-updates.onrender.com
- Render는 main 브랜치 푸시 시 자동 배포
