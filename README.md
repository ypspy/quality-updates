# Quality Updates

회계·감사 분야 규제 모니터링을 위한 정적 문서 사이트입니다.  
금융위원회·금융감독원·회계기준원 등 주요 기관의 보도자료, 제도 개정, 감리 결과를 시기별로 정리하여 제공합니다.

**사이트:** [https://quality-updates.onrender.com](https://quality-updates.onrender.com)

## 기능

- **규제 업데이트**: 분기별 보도자료·제도 변경 정리 (2022년~현재)
- **품질관리감리**: 금융감독원 회계법인 품질관리감리 관련 문서 요약
- **한국어**: 검색·탐색·테마(라이트/다크)
- **질의회신 아카이브**: 원문은 사이트에 게시하지 않는다

## 로컬에서 보기

- **Python**: 3.8 이상
- **Node.js** (선택): `dev`, `build:strict`, `test`

```bash
git clone https://github.com/ypspy/quality-updates.git
cd quality-updates
```

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

```bash
mkdocs serve
```

`mkdocs`를 찾지 못하면 `python -m mkdocs serve`를 쓴다. 브라우저 주소는 [http://127.0.0.1:8000](http://127.0.0.1:8000)이다.

```bash
npm install
npm run dev
npm run build:strict
npm test
```

## 분기 운영

**Agent**와 **전문가(HITL)** 가 협업한다.

수집 → 큐레이션 → 요약 → 사이트 반영 → 배포.

절차·역할·명령은 [분기 운영 작업지시서](docs/project/quarterly-operations-guide.md)에 있다.  
문서 지도는 [docs/project/README.md](docs/project/README.md)에 있다.

## 배포

- **플랫폼**: [Render](https://render.com)
- **동작**: `main` 브랜치 푸시 시 자동 빌드·배포
- **빌드 명령**: `pip install -r requirements.txt && mkdocs build`
- **출력 디렉터리**: `site/`
- **사이트 URL**: [https://quality-updates.onrender.com](https://quality-updates.onrender.com)

## 기여

버그 제보, 문서 수정, 개선 제안은 이슈와 Pull Request로 한다.  
절차는 [CONTRIBUTING.md](CONTRIBUTING.md)에 있다.

## 라이선스·저작권

© 2026 Quality Updates.  
사이트 내 저작권 문구는 `mkdocs.yml`의 `copyright` 및 푸터 오버라이드에 정의되어 있습니다.
