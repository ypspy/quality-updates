# 완결성 DoD — 백필 누락 · 큐레이션 누락 (C+3)

형식(Format) DoD와 **별축**이다. 요약 문장 스키마는 [README.md](README.md) family 파일을 보고, 이 문서는 **존재·선별·요약 완결**만 본다.

판정 프록시: [`scripts/auto_curate.py`](../../scripts/auto_curate.py) + [`docs/project/curation-rules.md`](../../docs/project/curation-rules.md).  
사람 큐레이션이 정본이며, 규칙 제안은 **confidence ≥ 0.75**일 때만 Fail로 친다(규칙 문서의 사람 재검토 문턱과 동일).

---

## 1. 범위

| 포함 | 제외 |
|------|------|
| 2012–2025 전 분기, 2026-Q1–Q3 파일 | 아직 공개 윈도 전인 분기(예: 진행 중·미도래 2026-Q4) |
| Appendix A 앞 본문 + Appendix A 수집 목록 | Format·Facts·Tone (family DoD) |
| `auto_curate --scope body` / `appendix` | 마커 대량 자동 수정, 본문 재작성 |

---

## 2. 백필 누락 (C의 A+B)

### A. 구조·존재

| 검사 항목 | Pass | Fail |
|-----------|------|------|
| **분기 파일** | 기대 분기에 `docs/quality-updates/YYYY/YYYY-MM-DD_to_YYYY-MM-DD.md` 존재 | 파일 없음 |
| **Appendix** | `## Appendix` (A) 헤더 존재 | Appendix 없음 |
| **기관 절** | 본문에 `###` 금융감독원·금융위원회·한국공인회계사회·한국회계기준원 | 네 기관 중 본문 `###` 누락 |

필수 게시판(`####`) 목록은 연도·크롤 범위에 따라 달라 1차 Fail에서 제외한다. 기관 절만 본다.

### B. 요약 완결

| 검사 항목 | Pass | Fail |
|-----------|------|------|
| **요약 누락** | `auto_curate`(body)가 `summarize`·conf≥0.75인 본문 링크에 `!!! note`/`!!! info` 있음 | 동일 조건인데 note/info **없고**, `<!-- no_summary -->`도 **없음**(미완 bare) |

본문에 `<!-- no_summary -->`만 있고 규칙이 `summarize`인 경우는 백필 미완이 아니라 **큐레이션 분류 불일치**로 본다(§3).

---

## 3. 큐레이션 누락 (C의 1+2)

| 검사 항목 | Pass | Fail |
|-----------|------|------|
| **미결정** | 본문 링크마다 note/info 또는 `<!-- no_summary -->` (또는 `<!-- skip -->` 잔존) | note도 `no_summary`도 없는 bare 링크. 단, 규칙 bucket=`review`(중점 점검 등)는 Pass 허용 |
| **본문 누락** | Appendix에서 `summarize`·conf≥0.75인 URL이 본문에도 있음 | Appendix-only(본문에 동일 URL 없음) |
| **분류 불일치** | 본문 `no_summary`인데 규칙이 `summarize`·conf≥0.75가 **아님** | 본문은 링크만(`no_summary`)인데 규칙은 `summarize`·conf≥0.75 |

`skip` 제안이 Appendix-only인 것은 정상(배포 후 skip 마커 제거)이므로 Fail이 아니다.

---

## 4. 리뷰 사용법

1. 분기·백필 PR에서는 **먼저** 이 문서 §2–§3로 완결성을 본다.
2. 본문에 남은 요약 링크만 family Format DoD로 넘긴다.
3. Fail 기록 시 코드(아래)와 링크 날짜·제목을 남긴다. `auto_curate` rule_id·confidence를 근거에 붙인다.

| 코드 | 축 |
|------|----|
| `Completeness·분기파일누락` | 백필 A |
| `Completeness·Appendix누락` | 백필 A |
| `Completeness·기관절누락` | 백필 A |
| `Completeness·요약누락` | 백필 B |
| `Curation·미결정` | 큐레이션 1 |
| `Curation·본문누락` | 큐레이션 2 |
| `Curation·분류불일치` | 큐레이션 (no_summary vs summarize) |

---

## 5. 잔차·주의

- 골드셋(2026-Q3)도 규칙 프록시와 사람 선별이 어긋나면 `Curation·본문누락`·`분류불일치`가 남을 수 있다. 사람 정본을 뒤집을 때는 소유자 확인 후 규칙을 고친다.
- 신뢰도 0.75 미만 제안은 Fail에 넣지 않고 리뷰 힌트만 한다.
- 이 축은 요약 **형식** Fail 목록과 섞지 않는다.
