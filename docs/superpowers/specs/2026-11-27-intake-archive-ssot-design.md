# 입수 아카이브 문서 SSOT — 설계 스펙

**날짜**: 2026-11-27  
**상태**: 설계 합의됨 (파일럿 3 · 범위 **1** 문서만).  
**선행**: [cursor-quarterly-routine-design](2026-11-26-cursor-quarterly-routine-design.md) §5.4 (아카이브 규격화 = 후속 brainstorming).

합의:

- Intent = 레인 B–E 누적 아카이브 As-Is를 **한 문서 SSOT**로 고정한다.
- 범위 = **옵션 1** — 문서만. `.gitignore` 통일·볼트 이관 자동화·첨부 정책 변경은 Non-Goal (후속 2·3).
- 산출 = `docs/project/intake-archive.md` + 가이드 §3.3·문서 지도 링크.
- 공개 사이트 노출은 계속 분기 md·corpus. 파이프라인은 볼트에 직접 쓰지 않는다.

---

## 1. Intent & Why

분기 가이드 §3.3에 짧은 표만 있고, B/C 스펙·D README·E collector가 흩어져 있다. 정규 루틴·Automation이 같은 표를 보게 하려면 교차 레인 SSOT가 필요하다. 이번은 **문서로 고정**만 한다.

---

## 2. Non-Goals

- `.gitignore` / nested ignore 변경, E README carve-out (옵션 2)
- `export_*_raw` 기본 경로 수정·스케줄화, D 박스 이관 자동화 (옵션 3)
- C 첨부 커밋 정책 변경, 연도 백필, V-249 해제
- 크롤러 코드 변경

---

## 3. SSOT 문서에 넣을 열

레인 B–E 각각: 경로 · 키 · state/manifest · git 경계 · skip/증분 · 볼트 export (있으면) · 상세 문서 링크 · 비고(박스 정본 등).

기존 상세(제재 폴더 규칙, kasb meetings CLI)는 **링크만** 하고 장문 복사하지 않는다.

---

## 4. Acceptance

1. `docs/project/intake-archive.md`가 B–E를 한 표(+짧은 원칙)로 설명한다.
2. 가이드 §3.3이 그 문서를 정본으로 가리킨다.
3. gitignore/코드 변경 없음.
4. `npm run lint:md` exit 0.

---

## 5. Definition of Done

- [ ] 스펙·SSOT·교차 링크·색인
- [ ] 옵션 2·3은 후속으로 명시
- [ ] PR (V-249 파일럿 3)
