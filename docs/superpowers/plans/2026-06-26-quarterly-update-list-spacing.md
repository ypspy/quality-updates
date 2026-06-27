# Quarterly Update List Spacing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 분기 규제 업데이트 문서(`docs/quality-updates/{year}/*.md`) 렌더 시 리스트 항목 간 여백을 요약 note 유무와 무관하게 일정하게 만든다.

**Architecture:** `extra.js`가 URL `/quality-updates/{연도}/`일 때 `article.md-content__inner`에 `.quarterly-update` 부여; `extra.css`가 해당 스코프의 `ul > li`·`li > p`·`li > admonition/details` 여백을 정규화. 마크다운·스킬 변경 없음.

**Tech Stack:** MkDocs Material 9.x, `extra.css`, `extra.js`, `navigation.instant` (`document$`)

**Spec:** `docs/superpowers/specs/2026-06-26-quarterly-update-list-spacing-design.md`

---

### Task 1: 페이지 스코프 JS

**Files:**
- Modify: `docs/assets/javascripts/extra.js`

- [ ] **Step 1:** `QUARTERLY_PATH` 정규식과 `applyQuarterlyUpdateScope()` 구현
- [ ] **Step 2:** `document$` 구독 + `DOMContentLoaded` 폴백
- [ ] **Step 3:** 비분기 페이지에서 클래스 제거 (instant 네비게이션 대응)

### Task 2: 스코프 CSS

**Files:**
- Modify: `docs/assets/stylesheets/extra.css`

- [ ] **Step 1:** `.md-content__inner.quarterly-update ul > li` 여백 규칙 5종 추가
- [ ] **Step 2:** `mkdocs serve`로 2026 Q1 보도자료 구역 시각 확인

### Task 3: 문서·검증

**Files:**
- Modify: `docs/superpowers/README.md`

- [ ] **Step 1:** specs 테이블에 본 스펙 행 추가
- [ ] **Step 2:** `mkdocs build --strict`
- [ ] **Step 3:** `cd scripts && python -m pytest tests/ -q`
- [ ] **Step 4:** `python scripts/validate_content.py --strict`
