# README 앞문 — 설계 스펙

**날짜**: 2026-11-07  
**상태**: 설계 합의됨. 이 파일 검토 후 구현 계획.  
**범위**: GitHub `README.md`를 앞문으로 줄이고, 절차 문장은 이미 있는 정본으로 옮긴다.

참고: [awesome-readme](https://github.com/matiassingers/awesome-readme). 좋은 README는 이름, 설명, 설치, 사용, 기여, 라이선스를 앞에 두고 긴 절차는 링크로 뺀다.

---

## 개요

`README.md`는 처음 온 사람과 운영하는 Agent·전문가가 함께 보는 앞문이다. 첫 화면은 소개와 공개 사이트이고, 이어서 설치, 그 아래 운영은 짧은 목록과 작업지시서 링크다.

절차의 정본은 그대로다.

- 분기 운영: `docs/project/quarterly-operations-guide.md`
- 기여·프론트매터: `CONTRIBUTING.md`
- 문서 지도·저장소 트리·MCP: `docs/project/README.md`

**목적**

- README를 150줄 안쪽으로 줄인다.
- 첫 화면에서 소개와 사이트 주소가 보이게 한다.
- README에만 있는 조작 문장을 정본에 남긴다.
- 정본에 이미 있는 문장은 다시 쓰지 않는다.

**범위 외**

- 코드, 스크립트, 테스트, 분기 본문, `docs/fss-review/`, `docs/index.md`
- 기존 설계 스펙·구현 계획의 본문. 색인 한 줄은 이 스펙을 가리키려고 넣는다.
- 새 Phase, 새 감리 절차, 품질관리감리 HWP 입수 절차
- export 스크립트를 누가 실행하는지 정하는 일
- `export_quarterly_raw.py` 목적지 철자를 고치는 일
- `raw/sanctions/` 경로를 새로 풀거나 제재 export를 추가하는 일
- 배지, 스크린샷, 사람 이름
- 저장소 트리를 다시 세는 일

---

## README 목차

제목 아래에 현재 소개 두 문장과 사이트 `https://quality-updates.onrender.com`을 둔다. 그 아래 `##` 여섯 개다. 목차 목록, 배지, 스크린샷은 넣지 않는다.

1. **기능.** 규제 업데이트(2022년~현재), 품질관리감리, 한국어 검색·탐색과 라이트/다크. 질의회신 원문은 사이트에 게시하지 않는다는 한 줄. glightbox, minify, CI는 넣지 않는다.
2. **로컬에서 보기.** Python 3.8 이상, 선택 Node.js. 클론, 가상환경, `pip`, `mkdocs serve`, `http://127.0.0.1:8000`. 명령이 없으면 `python -m mkdocs serve`. npm은 `dev`, `build:strict`, `test` 세 줄. `~/.bashrc` alias 예는 넣지 않는다. `mkdocs serve`는 작업지시서로 옮기지 않는다.
3. **분기 운영.** Agent와 전문가(HITL)가 협업한다. 단계는 수집, 큐레이션, 요약, 사이트 반영, 배포. 절차·역할·명령은 작업지시서. 문서 지도는 `docs/project/README.md`.
4. **배포.** Render, `main` 푸시, `pip install -r requirements.txt && mkdocs build`, 출력 `site/`, 사이트 주소.
5. **기여.** `CONTRIBUTING.md` 링크.
6. **라이선스·저작권.** 현재 문구 유지.

로컬 개발의 정본은 계속 README다 (`docs/project/README.md`의 SSOT 표).

---

## 문장 배치

작업지시서에 이미 있는 문장은 README에서만 지운다. 해당하는 것: 협업 상세 불릿, mermaid, 8행 단계 표, `auto_curate.py`는 출력만 한다는 설명, 웨일에서 PDF로 저장한다는 Phase 3 문장, 6절에 있는 npm 단축, 품질관리감리의 최소 프론트매터와 이미지 안내.

### 작업지시서 6절 — 없는 명령만

`fetch_attachments.py`, `attach_sanction_minutes.py`, `write_quarterly_record.py`, `export_quarterly_raw.py`, `crawl_kasb_replies.py`, `export_kasb_replies_raw.py`, `extract_pdf.py`, `extract_hwp.py`, `reorder_chronological.py`.

질의회신 인계 문장은 원칙에 이미 있으므로 6절에 다시 쓰지 않는다. 6절에 두는 복사 규칙은 다음뿐이다. `item.md`와 첨부가 있으면 다시 받지 않는다. `--retry-failed`는 `failed`, `partial`, `empty`를 다룬다. export는 `item.md`만 복사하고, 목적지는 `--dest`로 바꿀 수 있다. 같은 `{seq}.md`는 유지하고 첨부는 복사하지 않는다.

### 작업지시서 Phase 2 — 첨부 불릿

새 Phase는 만들지 않는다. 불릿은 다음이다.

- skip, 링크만, 이미 요약된 항목은 건너뛴다.
- 마커가 없는 링크는 `auto_curate.py`와 같은 규칙으로 고른다.
- HWP/HWPX와 PDF가 같이 있으면 PDF만 받는다.
- PDF가 없는 HWP/HWPX만 보고의 수동 변환 목록에 둔다.
- 보고 기본 경로와, 받은 PDF·기타 첨부·웨일 변환·다운로드 실패로 나뉜다는 점.
- 편집기 PDF 탭에서 첨부를 더하거나 뺄 수 있다. 「페이지 첨부 모두 연결」은 그 행의 원문 페이지에서 같은 규칙으로 받는다.

### 작업지시서 Phase 3 — 없는 문장만

- 제목에 `의사록(추가)`인 글은 회차 키가 같으면 같은 회의로 합치고, 합친 PDF마다 마커를 붙인다. 추가가 아닌 의사록 PDF가 같은 회의에 둘이면 마커를 붙이지 않는다.
- 안건 ZIP 선별 문단 가운데 작업지시서에 없는 문장. 의안번호가 있거나 실명 회사가 하나일 때만 연결하고, 아니면 unmatched.
- 제재 안건 HWP는 변환하지 않고 Whale 변환 필요 목록으로만 보고한다. 분기 첨부의 웨일 저장 문장과 이 문장을 한쪽으로 합치지 않는다.
- `write_quarterly_record.py`의 파일명, 같은 경로면 바이트 유지, `skip`·`no_summary`·Appendix는 만들지 않음, 2026년 3분기는 이 명령으로 만들지 않음, 같은 제목이면 `--date`.
- `export_quarterly_raw.py`가 분기 마크다운, 처리 기록, PDF·캡처를 복사하고 저장소 파일은 수정하지 않는다는 문장. 목적지 문자열은 그대로 둔다.
- 볼트로 보낼 때의 경로는 `raw/sanctions/`이고, 그 복사는 `export_quarterly_raw.py`에 들어가기 전까지 미룬다. 이 문장만 옮긴다. 경로를 새로 풀지 않는다.

### 작업지시서 Phase 1 — 한 문장

`조사·감리결과 조치`가 없는 금융위 보도와 금감원·한공회·회계기준원 링크는 보도자료 등 기존 제목에 둔다. 새 파일만 만든다는 규칙은 Phase 1 표에 이미 있다.

작업지시서 10절 개정 이력에 이번 이동 한 줄을 남긴다.

### CONTRIBUTING.md

프론트매터 YAML과 필드 설명, 파일명 규칙을 「수동으로 파일을 만들 때」아래에 둔다. README 앵커로 가던 링크는 그 템플릿을 가리키게 한다.

### docs/project/README.md 와 AGENTS.md

저장소 트리 코드블록을 새 절로 옮긴다. 연도 폴더와 파일 목록은 다시 세지 않는다. 트리 아래의 탐색·스타일 두 문장도 그 절에 둔다.

MCP 인용 계약, stdio, HTTP 메모, 스펙 링크를 새 절으로 옮긴다. `AGENTS.md`의 MCP 링크만 그 절로 바꾼다.

---

## 확인

- README는 위 목차이고 150줄 안쪽이다. 사람 이름은 없다.
- 작업지시서에 이미 있던 문장은 두 벌이 되지 않는다. 새 Phase는 없다.
- `CONTRIBUTING.md`는 README의 콘텐츠 업데이트 앵커를 가리키지 않는다.
- `AGENTS.md`의 MCP 링크는 `docs/project/README.md`의 MCP 절이다.
- `docs/`를 고친 뒤 `npm run lint:md`가 통과한다.

---

## 변경 파일

```text
README.md
docs/project/quarterly-operations-guide.md
CONTRIBUTING.md
docs/project/README.md
AGENTS.md
docs/superpowers/README.md
```

`docs/superpowers/README.md`는 이 스펙의 색인 한 줄이다.
