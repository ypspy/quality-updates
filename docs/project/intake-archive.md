# 입수 아카이브 (B–E) — 문서 SSOT

**상태**: As-Is 고정 (2026-11-27). 코드·gitignore 변경 없음.  
**관련**: [quarterly-operations-guide.md](quarterly-operations-guide.md) §3.3, 스펙 [intake-archive-ssot-design](../superpowers/specs/2026-11-27-intake-archive-ssot-design.md).

분기마다 “그 분기 DB”를 새로 만들지 않는다. 정규 루틴 1b–1e는 **누적 저장소에 키가 있으면 skip**, 없으면(또는 실패 재시도면) 추가한다.  
공개 노출은 아카이브 전체가 아니라 **분기 md·corpus**다. 파이프라인은 **볼트에 직접 쓰지 않는다** (`export_*_raw`는 별도 복사).

---

## 1. 레인 요약

| 레인 | 누적 경로 | 키 | state / manifest | git | skip / 증분 | 볼트 |
|------|-----------|-----|------------------|-----|-------------|------|
| **B** 금감원 질의회신 | `data/fss-replies/{board}/{nttId}/` | `board`+`nttId` | 루트 `manifest.jsonl` | `item.md`·manifest 커밋. 첨부 HWP 등은 `data/fss-replies/.gitignore` | 완료 건 skipped | `export_fss_replies_raw.py` → `raw/fss-replies/…` (`item.md`만) |
| **C** 회계기준원 질의회신 | `data/kasb-replies/{seq}/` | `seq` | `manifest.jsonl` | `item.md`·**첨부 커밋** | 있으면 재수집 안 함 | `export_kasb_replies_raw.py` → `raw/kasb-replies/{seq}.md` |
| **D** 제재 안건·의사록 | `downloads/sanctions/{회차}/` | 회차 폴더명 | `_backfill-state.json`, `_failed-downloads.jsonl`, `_review-queue.jsonl`, `_pending-conversion.jsonl`, `_review/` | `downloads/*` ignore. **예외:** `downloads/sanctions/README.md`만 추적 | 회차·연결 누적; 미공개→다음 루틴 1d′ | 전용 `export_*_raw` 없음. 사이트는 `docs/quality-updates/` |
| **E** 회의록 | `downloads/kasb-meetings/…` | seq / 회 폴더 | `_state.json` (`done`/`failed`) | `downloads/` ignore (README carve-out 없음) | 끝난 seq 재수집 안 함 | 전용 export 없음. 실수집은 승인·`--live` 원칙 |

---

## 2. 원칙

1. **SSOT는 레인별 누적 경로**다. 분기 md는 공개 선택·요약본이다.
2. **git 경계는 레인마다 다르다** (C 첨부 커밋 vs B/D/E 바이너리 ignore). 이번 문서는 As-Is만 적는다. 통일은 후속(옵션 2).
3. **볼트는 복사본**이다. B/C는 `export_*_raw`; D/E 바이너리 볼트 이관 규칙은 후속(옵션 3).
4. **D 박스 정본**이 따로 있을 수 있다 (예: 저장소 밖 `qu-collect/downloads/sanctions/`). 저장소 `downloads/sanctions/`는 작업 사본·gitignore.
5. 상세 형식·폴더 명명·CLI는 아래 문서로 보낸다. 여기 장문 재서술 금지.

---

## 3. 상세 문서

| 레인 | 문서 |
|------|------|
| B | [fss-reply-archive-design](../superpowers/specs/2026-11-11-fss-reply-archive-design.md), `scripts/crawl_fss_replies.py`, `scripts/export_fss_replies_raw.py` |
| C | [kasb-reply-archive-design](../superpowers/specs/2026-11-04-kasb-reply-archive-design.md), `scripts/crawl_kasb_replies.py`, `scripts/export_kasb_replies_raw.py` |
| D | [sanctions-downloads-readme.md](sanctions-downloads-readme.md) (= `downloads/sanctions/README.md` 원본), `docs-dev/sanctions-format.md` |
| E | [kasb-meetings-collector.md](kasb-meetings-collector.md), `scripts/crawler/kasb_meetings.py` |
| 분기 공개 | [quarterly-operations-guide.md](quarterly-operations-guide.md), `scripts/export_quarterly_raw.py` (분기 md→볼트) |

---

## 4. 후속 (이 문서 Non-Goal)

| 옵션 | 내용 |
|------|------|
| **2** | gitignore/README 정합 (E README carve-out, FSS 스펙·nested ignore 문구 일치 등) |
| **3** | 볼트·박스/`downloads` 이관 계약 (`export_*_raw` 시기·주체, D 정본 경로, 기본 dest 정리) |

---

## 5. 개정

| 날짜 | 변경 |
|------|------|
| 2026-11-27 | 초판. 가이드 §3.3 As-Is를 교차 레인 SSOT로 승격 (스펙 intake-archive-ssot, 범위 1) |
