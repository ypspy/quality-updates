# 회계기준위원회 회의록 수집기

회계기준위원회 회의록·의안 수집은 질의회신 수집(`scripts/crawler/kasb_replies.py`)과 별도다. 모듈을 합치지 않는다. 자문위원회와 지속가능성기준위원회는 넣지 않는다.

## 범위

- 코드: `scripts/crawler/kasb_meetings.py`
- 목록: `calListA.do`에서 중분류가 회계기준위원회인 행만 읽는다. seq, 회차, 날짜를 남긴다.
- 상세: `calView.do`(본문이 비면 `calViewB.do`)와 `calmeetView.do`에서 안건 제목과 첨부 메타를 읽는다.
- 저장: `downloads/kasb-meetings/{연도}-회계기준위원회-{N}회/`
- 그 폴더에 `record.md`, `agenda/`, `results/`를 둔다. 의안 첨부는 `agenda/`, 회의결과·회의록은 `results/`다.
- 첨부가 없으면 `record.md`의 상태는 `meta_only`다.
- 회의결과 페이지가 404이면 결과 첨부는 비운다. 404가 아닌 오류이면 의안과 메타는 남기고 상태는 `partial`이다. 그 seq는 실패로 남고, `--retry-failed`일 때만 다시 연다.
- 상태 파일은 `downloads/kasb-meetings/_state.json`이다. 끝난 seq는 다시 받지 않는다. `--retry-failed`는 실패 seq를 다시 시도하고, 이번 선택에 들어온 새 seq도 받는다.
- `downloads/`는 gitignore다. 첨부 원문은 커밋하지 않는다.

## 실행

오프라인 확인만 한다. 아래 명령은 `scripts/tests/fixtures/kasb_meetings/`의 HTML만 읽고 사이트를 열지 않는다.

```bash
cd scripts && python -m crawler.kasb_meetings --dry-run --limit 3
```

인자가 없거나 `--live`만 있으면 끝난다. 전량 수집은 하지 않는다. 요청한 `--seq`가 이번 목록에 없으면 안내를 내고 종료 코드 1이다. `--limit` 때문에 다음 쪽을 열지 않아 확인하지 못한 seq도 같다.

실사이트 수집은 별도 승인이 난 뒤에만 `--live`와 `--limit` 또는 `--seq`를 함께 준다.

```bash
cd scripts && python -m crawler.kasb_meetings --live --limit 3 --delay 0.3
cd scripts && python -m crawler.kasb_meetings --live --seq 1105 --retry-failed
```

실수집의 연속 HTTP 사이에는 `--delay`초를 둔다. 기본값은 0.3초다. 세션을 여는 첫 GET 전에는 쉬지 않고, 그 다음 목록·`calView.do`(본문이 비면 `calViewB.do`)·`calmeetView.do`·첨부 요청마다 쉰다. `--delay 0`이면 쉬지 않는다. `--dry-run`은 사이트를 열지 않으므로 이 간격을 적용하지 않는다.

같은 호스트 질의회신 수집(`crawl_kasb_replies.py`)은 0.2초다. 금감원 질의회신(`crawl_fss_replies.py`)은 0.3초다. 회의록은 한 건에 상세와 첨부가 이어지므로 0.3초를 기본으로 둔다.

## 승인 전 실수집에서 정할 것

- 시범 범위. 예: 최근 3회, 또는 seq 목록
- 기간(`--start`, `--end`)을 둘지
- 첨부 원문(HWP, HWPX)을 받을지, 메타만 둘지
- `calView.do`가 비어 `calViewB.do`로 넘어가는 동작이 맞는지
