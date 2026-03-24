# quality-updates 문서 정리 설계

**날짜**: 2026-03-24
**상태**: 승인됨

---

## 배경

`quality-updates` 레포의 루트와 docs/ 구조를 정리한다. 주요 문제:

1. 루트에 AGENT 지침 파일 3개(`AGENT_INSTRUCTION.md`, `AGENT_BOILERPLATE.md`, `AGENT_PDF.md`)가 산재
   - `AGENT_INSTRUCTION.md`와 `AGENT_PDF.md` 사이에 Phase 0 PDF 경로 결정 로직 중복
2. 루트에 잡파일(`bash.exe.stackdump`, `nul`) 존재
3. `downloads/` 디렉터리가 git 미추적 상태 (`.gitignore`에 `*.pdf`/`*.hwp` 패턴만 있고 디렉터리 전체 제외 미설정)
4. 에이전트 지침이 일반 마크다운 파일로 존재해 자동 발견 불가

---

## 범위 (미포함)

- `docs/quality-updates/2023/` 중복 파일 — 변경 없음
- `mkdocs.yml` nav — 변경 없음

---

## 설계

### 1. 파일 시스템 변경

```
quality-updates/
│
├── .claude/
│   └── skills/                            ← 신규 디렉터리
│       └── quality-updates-writer/        ← 신규
│           ├── SKILL.md                   ← AGENT_INSTRUCTION + AGENT_PDF 통합
│           └── boilerplate.md             ← AGENT_BOILERPLATE 이동
│
├── .gitignore                             ← downloads/ 전체 추가
│
├── AGENT_INSTRUCTION.md                   ← 삭제
├── AGENT_BOILERPLATE.md                   ← 삭제
├── AGENT_PDF.md                           ← 삭제
├── bash.exe.stackdump                     ← 삭제
└── nul                                    ← 삭제
```

### 2. SKILL.md 구조

**frontmatter**:
```yaml
---
name: quality-updates-writer
description: Use when creating or updating quarterly regulatory update documents
  for Korean financial regulators (FSS, FSC, KICPA, KASB). Triggers on tasks
  like "분기 요약 작성", "보도자료 요약", "규제 업데이트 추가".
---
```

**본문 섹션**:
1. Overview — 역할 + 기준 파일 참조
2. 작업 순서 — Phase 0/1/2 표
3. Phase 0: PDF 경로 결정 — AGENT_INSTRUCTION Phase 0 표 + AGENT_PDF 전체 내용 통합 (중복 제거)
4. Phase 1: 개별 링크 요약 — 블록 문법, 들여쓰기, 작성 규칙, 요약 대상 선별, 제재 조치 표(Type A/B), 특수 유형
5. Phase 2: 분기 요약 — Executive Summary, 기관별 요약, 시사점 구조
6. 공통 규칙 — 원문 처리, Appendix A, 출력 요건
7. 품질 체크리스트
8. 말미: `> 보일러플레이트 생성은 boilerplate.md 참조.`

**핵심 변경점 (현재 대비)**:
- `AGENT_PDF.md` 23줄 → Phase 0에 완전 흡수, 별도 파일 삭제
- frontmatter description에 한국어 트리거 키워드 포함 → 자동 발견 가능
- 인코딩 예외처리(U+2019 fallback) Phase 0 내 통합

### 3. boilerplate.md

`AGENT_BOILERPLATE.md` 내용 그대로 이동. 파일명만 변경.

### 4. .gitignore 추가

```gitignore
# downloads/ 폴더 전체 제외 (PDF·HWP 원문)
downloads/
```

기존 `downloads/*.pdf`, `downloads/*.hwp` 패턴은 중복이 되므로 제거.

---

## 구현 단계

1. `.claude/skills/quality-updates-writer/` 디렉터리 생성 (`mkdir -p`)

2. `SKILL.md` 작성 (AGENT_INSTRUCTION + AGENT_PDF 통합)
   - `AGENT_INSTRUCTION.md` Phase 0 섹션의 `> 인코딩·HWP 변환 등 예외 처리는 AGENT_PDF.md 참조.` 줄을 **제거**하고 `AGENT_PDF.md` 전체 내용을 Phase 0에 인라인 통합
   - `AGENT_INSTRUCTION.md` line 185의 `> 상세 지침은 AGENT_BOILERPLATE.md 참조.`를 `> 보일러플레이트 생성은 boilerplate.md 참조.`로 **교체**

3. `boilerplate.md` 작성 (AGENT_BOILERPLATE 내용 그대로 이동)

4. **검증**: `SKILL.md`와 `boilerplate.md`가 완성되었는지 확인
   - `SKILL.md` 섹션 헤더 확인: Phase 0/1/2, 공통 규칙, 품질 체크리스트 모두 존재
   - `boilerplate.md` 비어있지 않음 확인
   - `SKILL.md` 내 `AGENT_PDF.md`, `AGENT_BOILERPLATE.md` 참조가 없음 확인

5. 루트 `AGENT_*.md` 3개 삭제 (Git Bash `rm` 사용)

6. `bash.exe.stackdump`, `nul` 삭제 (Git Bash `rm` 사용; cmd.exe `del` 사용 금지 — Windows 예약어 `nul` 처리 불안정)

7. `.gitignore` 업데이트: 기존 `downloads/*.pdf`, `downloads/*.hwp` 두 줄을 **제거**하고 `downloads/` 전체 제외 패턴으로 교체

8. 커밋
