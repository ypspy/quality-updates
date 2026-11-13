# FSS B0000291 2022 수집기

2022년 품질관리감리 글은 공개 목록에 없다. `scripts/crawler/fss_b0000291.py`가 `view.do`만 열고, 실행 진입점은 `scripts/crawl_fss_b0000291.py`다. 목록 크롤러 `scripts/crawler/FSS.py`는 확장하지 않는다.

## 시드 수집

시드 87건은 `scripts/tests/fixtures/b0000291/2022-seed.csv`다. 저장소 루트에서 실행한다.

```bash
python scripts/crawl_fss_b0000291.py --seed scripts/tests/fixtures/b0000291/2022-seed.csv
```

기본 출력 디렉터리는 `downloads/fss-review/B0000291`이다. 이 경로는 gitignore라 커밋하지 않는다. 첨부 원문은 `<nttId>/<파일명>`에만 저장한다. 글 단위 필드는 같은 디렉터리의 `manifest.jsonl`에 UTF-8 한 줄로 남긴다. 첨부까지 받아 manifest에 넣은 nttId만 `_state.json`의 `done`에, 감사인이 빈 시드 글은 `empty`에 글마다 바로 적는다. `--resume`은 `done`과 `empty`를 건너뛴다. 탐색의 `probed`만 있는 번호는 시드 수집이 첨부를 받는다. 실패한 요청은 `_failed.jsonl`에 같은 nttId의 마지막 결과만 남긴다. 이미 있고 해시가 같은 첨부는 덮어쓰지 않는다. 한 글에서 저장 이름이 겹치면 `report__2.hwpx`처럼 나누고, 그 글의 첨부가 모두 성공한 뒤에만 `_pending-conversion.jsonl`에 적는다.

받은 `.hwp`와 `.hwpx`는 변환하지 않는다. 경로만 `_pending-conversion.jsonl`에 적는다. HWP 변환은 이 수집기의 다음 단계다.

`--dry-run`은 view HTML을 파싱해 받을 파일, 빈 페이지, 실패 수만 출력하고 첨부 다운로드는 하지 않는다. 시드 `--dry-run`은 dest에 파일을 쓰지 않는다. `--delay`의 기본값은 1초다. 5xx, 연결 오류, 끊긴 청크, 연결 시간 초과, TLS `UNEXPECTED_EOF`는 최대 5회까지 지수 백오프로 다시 시도한다. 인증서 검증 실패는 재시도하지 않는다. 본문을 읽지 못한 글은 그 글만 실패로 남긴다. 403은 짧게 한 번만 다시 시도한 뒤 실패로 남긴다. 인증서 검증은 켜 둔다.

## 광역 탐색

```bash
python scripts/crawl_fss_b0000291.py --sweep --seed scripts/tests/fixtures/b0000291/2022-seed.csv
```

`--seed`를 탐색과 함께 주면 그 파일은 제외 목록이다. 시드 수집과 탐색을 한 명령에서 같이 수행하지는 않는다. 기본 구간은 127800–128800을 1씩 열고, 128800–136220은 간격 200으로 연다. `--range`, `--coarse-from`, `--coarse-to`, `--coarse-stride`로 바꾼다.

시드에 없는 글과 실패한 탐침만 `_sweep.jsonl`에 남긴다. `dl.bd-info`가 있고 감사인이 빈 페이지만 빈 페이지다. `dl.bd-info`가 없거나 전송에 실패하면 실패로 남기고 `probed`에 넣지 않아 `--resume`이 다시 연다. 성공적으로 분류한 새 글, 시드에서 뺀 글, 빈 페이지만 `probed`에 남는다. `--resume`은 그 페이지를 다시 열지 않고, `--resume --sweep-download`는 이미 보고한 새 글의 첨부만 받는다. `probed`만으로는 시드 수집이 끝났다고 보지 않는다. 간격에 걸리지 않는 끝 번호도 한 번은 연다. 탐색 `--dry-run`은 요약만 내고 파일을 쓰지 않는다.

## 백업

노트북 `C:\backups`로 복사하는 일은 이 스크립트 밖이다. 수집기는 저장소의 `downloads/`만 쓴다.
