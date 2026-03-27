# 큐레이션 편집기·배포 워크플로

로컬 도구 `python scripts/editor.py`(Flask)로 `docs/quality-updates/**/*.md`의 링크 행을 정리하고, 이후 에이전트(SKILL)로 요약·배포 전처리를 수행할 때의 약속을 정리한다.

## 편집기 동작 요약 (2026-03 기준)

- **파일 선택**: `/api/files` — `docs/quality-updates` 아래 `.md`를 **수정일 최신 → 과거** 순.
- **설정**: `scripts/editor_config.json` — `downloads_folder`(저장소 루트 기준 `downloads/` 하위만 허용).
- **WEB 미리보기**: `/api/source/preview` — HTML은 sanitize 후 iframe. **PDF·Zip·Office·이미지 등** 바이너리(HTML/JSON·`text/*` 제외)는 iframe이 저장 URL로 가지 않고, 부모 창이 `/api/source/save_fetched`를 `fetch`한 뒤 토스트(약 1초)·다운로드 목록 갱신. 하위 호환으로 `/api/source/save_pdf`도 동일 동작.
- **KASB 첨부**: `/api/source/kasb_file` — 동일하게 JSON 응답 + 부모 `fetch`; 미리보기 HTML 내 링크 클릭은 기본 네비게이션 대신 가로채서 저장.
- **파일명**: `Content-Disposition`의 퍼센트 인코딩·Latin-1 깨짐 보정 후 로컬 저장.
- **개발**: `FLASK_DEBUG=1`(기본)일 때 코드 수정으로 리로더가 돌아도 **브라우저 탭을 자동으로 반복 열지 않음**(리로더 부모에서만 최초 오픈). `FLASK_DEBUG=0`이면 단일 프로세스로 기존과 같이 오픈.
- **줄 끝(CRLF)**: Windows에서 저장한 `.md`는 `\r\n` 줄바꿈을 쓰는 경우가 많다. `scripts/editor/saver.py`는 `<!-- skip -->` 등 마커를 인식할 때 `\r`을 제거한 뒤 비교한다. (과거에는 `\r` 때문에 다음 링크의 스킵 줄을 지우지 못해 **미결정으로 저장해도 스킵이 남거나** 마커가 엇갈린 것처럼 보일 수 있었다.)
- **저장 후 줄 번호**: 저장 시 마커가 빠지거나 생기면 **물리 줄 번호가 바뀐다**. 브라우저는 저장 성공 후 같은 파일을 다시 파싱해 `line_index`를 갱신한다. (갱신 없이 연속 저장하면 **잘못된 링크에 마커가 붙는** 현상이 날 수 있다.)

## 링크 상태(에디터 배지 ↔ `.md` 마커)

| 배지 | 의미 | 저장 시 마커 |
|------|------|----------------|
| **미결정** | 스킵/요약/완료 미선택, 처리 전 | (없음) |
| **요약 필요** | 요약 작업 대상; 출처(PDF·WEB·CLIP) 연결 | `<!-- source: … -->` (또는 레거시 `<!-- pdf: … -->`) |
| **스킵** | 공개 본문에서 제외해 두겠다는 표시 | 링크 **바로 다음 줄** `<!-- skip -->`(빈 줄 0~1개 허용; 파서·저장기가 동일 규칙) |
| **완료** | 요약 블록까지 반영됨 | 링크 다음 `!!! note` / `??? note` 등 기존 본문 유지 |

## MkDocs 배포와 `<!-- skip -->`

- MkDocs 기본 동작만으로는 **`<!-- skip -->` 줄은 HTML 주석으로 렌더에 안 보이지만**, **위 링크 불릿 한 줄은 그대로 사이트에 노출**된다.
- **배포본에서 항목까지 없애려면** SKILL·에이전트 패스에서 **링크 줄 + `<!-- skip -->` 줄**을 함께 제거하거나, 마크다운에서 링크 줄을 직접 삭제한다.

## 관련 코드

- 진입점: `scripts/editor.py`
- 앱: `scripts/editor/app.py`, 정적: `scripts/editor/static/editor.{js,css}`, 템플릿: `scripts/editor/templates/index.html`
- 파서·저장: `scripts/editor/parser.py`, `scripts/editor/saver.py`
- 테스트: `scripts/tests/test_preview_endpoint.py` 등
