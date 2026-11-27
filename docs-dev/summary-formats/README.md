# 요약 형식 DoD 색인 (2026 Q3 골드셋)

이 디렉터리는 분기 페이지 링크별 `!!! note` / `!!! info` 요약의 **작성·리뷰 Pass/Fail** 기준이다. 모범 전체는 `docs/quality-updates/2026/2026-07-01_to_2026-09-30.md`이나, **SUMMARIZE 세션마다 Q3 전문을 매번 로드하지 않는다.** verbatim 표본은 `.claude/skills/quality-updates-writer/reference/gold-excerpts.md`를 쓰고, 이 파일들은 규칙·리뷰 체크리스트 SSOT다.

**완결성**(백필 누락·큐레이션 누락)은 형식과 별축이다 → [completeness.md](completeness.md).

저장소 루트 `docs-dev/`에 두어 MkDocs 사이트에 올리지 않는다. 설계 배경은 [docs/superpowers/specs/2026-11-27-summary-format-dod-design.md](../../docs/superpowers/specs/2026-11-27-summary-format-dod-design.md).

---

## 기관×절 → family 매핑

Q3 본문(Appendix 이전)에 note가 있는 절만 포함한다.

| 기관 | 절 | Family | DoD |
|------|-----|--------|-----|
| 금융감독원 | 보도자료 | general-note | [general-note.md](general-note.md) |
| 금융감독원 | 세칙제ㆍ개정예고 | legislative | [legislative.md](legislative.md) |
| 금융감독원 | 회계감독 동향자료 | trend-briefing | [trend-briefing.md](trend-briefing.md) |
| 금융위원회 | 보도자료 | general-note | [general-note.md](general-note.md) |
| 금융위원회 | 제재 의결 | sanctions | [../sanctions-format.md](../sanctions-format.md) |
| 금융위원회 | 고시/공고/훈령 | general-note | [general-note.md](general-note.md) |
| 금융위원회 | 입법예고/규정변경예고 | legislative | [legislative.md](legislative.md) |
| 한국공인회계사회 | 알림마당 - 공지사항 | general-note | [general-note.md](general-note.md) |
| 한국공인회계사회 | 회계감사 - 감사인증기준 | general-note | [general-note.md](general-note.md) |
| 한국회계기준원 | 소통광장 - 공지사항 | general-note | [general-note.md](general-note.md) |
| 한국회계기준원 | 주요일정 | kasb-schedule | [kasb-schedule.md](kasb-schedule.md) |

제재 family는 본 디렉터리가 아니라 기존 [sanctions-format.md](../sanctions-format.md)를 따른다.

---

## 공통 리뷰 3축

`gold-excerpts-checklist`와 동일. family별 DoD 표에도 이 세 축을 반복한다.

| 축 | Pass | Fail 예 |
|----|------|---------|
| **Format** | note 문법·들여쓰기·접두어 혼용 없음·family 스키마 준수 | style-A/B 혼용, 표 열 누락, □ 헤더 누락 |
| **Facts** | 수치·기한·대상·금액이 원문과 일치, 추정 없음 | 반올림·추정·원문에 없는 칸 채움 |
| **Tone-detail** | 불릿 밀도·증류 수준이 Q3 앵커와 동급 | 원문 재현, 과소·과다 |

---

## 리뷰 사용법

1. 백필·분기 PR에서는 먼저 [completeness.md](completeness.md)로 분기 파일·요약 완결·큐레이션 누락을 본다.
2. 변경된 링크가 있는 초안에서 위 표로 **family**를 확정한다.
3. 해당 family DoD 파일의 **DoD Pass/Fail** 절만 연다(장문 스킬·Q3 전문 전체 로드는 피한다).
4. **독립 리뷰 세션**은 AGENTS.md §6.3에 따라 코드 수정·푸시·PR 댓글 없이 완결성 + 3축 + family 전용 행에 대해 Pass/Fail만 기록한다.
