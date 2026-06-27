---
name: audit-regulatory-lens
description: 감사 Planning·Execution·Reporting(품질검토 포함) 단계에서 Quality Updates 코퍼스(링크+note)를 근거로 규제 렌즈 코멘트·체크리스트를 생성. 코퍼스 읽기 전용.
---

> **ADVISORY SKILL (RIGID-lite)** — Quality Updates 코퍼스를 **읽기만** 한다. `docs/quality-updates/` 및 파이프라인 파일을 **수정하지 않는다**. 감사 출력 스키마·인용 규칙은 엄격히 따른다.

> **`quality-updates-writer`와 동시 사용 금지** — 동일 세션에서 writer(요약·스킵·보일러)와 본 스킬을 함께 호출하지 않는다. 역할 충돌.

> **Gold output 예시**: [reference/output-samples.md](reference/output-samples.md)  
> **검색 키워드**: [reference/keywords.md](reference/keywords.md)

**설계 spec**: `docs/superpowers/specs/2026-06-27-audit-regulatory-lens-skill-design.md`

---

## 세션 시작

### Announce

스킬 호출 즉시 사용자에게 고지:

> `audit-regulatory-lens 스킬로 [PLANNING|EXECUTION|REPORTING]을 시작합니다. 근거: Quality Updates 코퍼스(링크+note). MCP 미연결 시 repo 검색 fallback.`

### 모드 감지

| 모드 | 감지 키워드 (예) |
|------|------------------|
| **PLANNING** | 감사계획, planning, RKRA, 중점영역, 감사절차 설계, 수임 초기 |
| **EXECUTION** | 수행, execution, fieldwork, 조서, 테스트, 중간, 실증 |
| **REPORTING** | reporting, 완료, 보고, 발행 전, quality review, 품질검토, EQCR |

- 모호하면 **1문장**으로 모드 확인.
- 복수 단계 요청 시 **Planning → Execution → Reporting** 순으로 섹션 분리 출력.
- REPORTING + quality review/EQCR 동시 요청 → **Part A Reporting / Part B Quality review** 분리.

---

## 공통 워크플로

1. **모드 감지** — 위 표 적용
2. **Engagement brief** — 필수 필드 수집 (사용자 제공 우선, 없으면 질문)
3. **Retrieve corpus** — MCP v1.1 우선, 없으면 repo fallback (아래)
4. **Map 단계별 프레임** — 모드 출력 스키마 적용
5. **Draft 출력** — 규제 메시지·감사 시사 분리
6. **Quality gate** — 체크리스트 통과
7. **Footer** — 한계·면책 블록

---

## Engagement brief (모드 공통)

| 필드 | 필수 | 예 |
|------|:----:|-----|
| `reporting_period` | ✓ | 2025-12-31 결산 |
| `entity_type` | ✓ | 상장 / 코스닥 / 비상장 / 금융(보험·은행) |
| `industry` | | 제조, IT, 생명보험 |
| `focus_areas` | ✓ | 수익인식, ICFR, 전환사채, … |
| `corpus_window` | | 기본: 결산일 기준 **최근 4분기** + 해당 사업연도 감독 메시지 |
| `user_context` | | 모드별 추가 (각 모드 절 참조) |

---

## Retrieve corpus

### 우선순위

1. **MCP v1.1** (구현 시) — 아래 § MCP tool 계약
2. **Repo fallback** — MCP tool 목록에 해당 이름 없을 때

### MCP v1.1 (placeholder — corpus spec 구현 후 활성화)

MCP [corpus spec](../../../docs/superpowers/specs/2026-06-27-mcp-corpus-design.md) 연결 시 **repo fallback skip**:

| Tool | 용도 |
|------|------|
| `list_quarterly_periods` | `corpus_window` 결정 |
| `search_regulatory_updates` | `query`, `agency`, `period_label`, `has_summary=true` |
| `get_regulatory_update` | note 전문·URL 확정 |

**Detect**: MCP tool 목록에 위 이름이 있으면 repo fallback **사용하지 않음**.

### Repo fallback (v1)

```bash
# 예: ICFR + 최근 분기
rg -i "내부회계|ICFR|운영실태" docs/quality-updates/2025/ docs/quality-updates/2026/
```

**절차**

1. `docs/quality-updates/{year}/*.md` 대상 — `corpus_window`와 겹치는 분기 파일 우선
2. `focus_areas` 키워드 + [reference/keywords.md](reference/keywords.md) 동의어 + 기관명(FSS/FSC/KICPA/KASB)으로 `rg`/Read
3. **`summary_status` 우선**: note 있는 항목(`!!!`/`???` note) > `<!-- no_summary -->` > 제목만
4. `<!-- skip -->` 항목 **제외** (공개 코퍼스와 동일)
5. 매칭 링크 주변 **note 블록 전체** 읽기 (admonition 포함)

**인용 규칙**

- note bullet·표 내용만 **사실 인용**
- note 없으면 **제목 + URL만**
- corpus에 없는 제재·수치·제도명 **미기재**

**한계 고지 (v1)**: 키워드 검색 — 동의어 누락 가능 → MCP v1.1 권장.

---

## Quality gate (공통 RIGID-lite)

출력 전 아래를 모두 확인:

- [ ] 모든 **규제 사실**에 `(YY-MM-DD) [제목](URL)` 또는 MCP `id`+`url`
- [ ] corpus에 **없는** 제재·수치·제도명 **미기재**
- [ ] note 없는 항목에 **상세 내용 invent** 금지
- [ ] `(시사점)` bullet → **「당국 메시지」**; 감사인 행동 → **「감사 시사」** 라벨 **분리**
- [ ] **법률 자문·감사의견·적정/한정** 표명 금지
- [ ] 매칭 없음 → **「해당 기간·키워드 코퍼스 직접 매칭 없음」** 명시

---

## Footer (공통 — 모든 모드 출력 말미)

```markdown
---
**한계**: 본 출력은 Quality Updates에 수록된 보도·공지 note를 바탕으로 한 감사 **보조**이며,
KSA/K-IFRS 전문·감사결론·법률 자문을 대체하지 않습니다. 최종 판단은 engagement 팀이 합니다.
```

---

## PLANNING

**목적**: 감사계획·RKRA·중점영역·절차·문서요청에 **최근 감독 강조** 반영.

### 추가 brief

- 계획 수준: 그룹/단일 / 첫 수임·연속
- 알려진 경영자·IT·Fraud 리스크 (선택)

### Retrieve 초점

- 금감원: 운영계획, 중점심사, 유의사항, 지적사례
- 금융위: 제재·입법예고
- 한공회·기준원: 감사·공시 실무 유의

### 출력 스키마

중점영역(`focus_areas`)당 1블록. 필수 섹션:

```markdown
## Planning — 규제 렌즈

### Engagement 요약
- reporting_period, entity_type, industry, focus_areas 요약

### [중점영역: {name}]

#### 규제 메시지 (corpus)
- … (note 인용 bullet — 「당국 메시지」)

#### 감사 계획 시사
- **리스크·관심사**: … (「감사 시사」)
- **제안 절차/증빙**: …
- **문서·문답**: …

#### 출처
- (YY-MM-DD) [제목](URL)

### Planning 체크리스트 (팀 검토용)
- [ ] 각 focus_area에 corpus 출처 1건 이상 또는 미매칭 명시
- [ ] 중점심사·운영계획 note와 RKRA/절차 매핑 검토
- [ ] 제재·지적사례 note — 유사 업종·거래 유형 반영 여부
- [ ] 첫 수임·연속 — 전기 감사인·경영진 서한 이슈 corpus 반영
- [ ] 문서요청 목록에 감독 유의사항(공시·ICFR·특수관계자 등) 반영

### 코퍼스 미매칭 영역
- …
```

---

## EXECUTION

**목적**: 수행 중 **현재 작업**과 최근 감독 메시지 **정합**, 문서화·escalation 힌트.

### 추가 brief

- **현재 조서/절차** 요약 (**필수** — 없으면 질문 후 진행)
- 진행 중 finding·이슈 (선택)
- 테스트 단계: TOD/TOE/추정/특수관계자 등 (선택)

### Retrieve 초점

- `focus_areas` + **조서 키워드** 교집합
- 최근 **지적사례·제재** 중 유사 패턴 (note에 있을 때만)

### 출력 스키마

```markdown
## Execution — 규제 렌즈

### 수행 맥락 요약
- 조서/절차, 테스트 유형, 진행 이슈

### [작업 영역: {name}]

#### 규제 메시지 (corpus)
- …

#### 수행 대비 시사
- **정합**: 조서가 반영하는 감독 포인트
- **갭/보완**: 추가 절차·문서·질문
- **Escalation**: 팀/EQCR 상의 트리거 (corpus 근거 있을 때만)

#### 조서용 코멘트 초안 (선택)
- 「…」

#### 출처
- (YY-MM-DD) [제목](URL)

### Execution 체크리스트
- [ ] 조서 맥락과 corpus 메시지 1:1 매핑 또는 gap 명시
- [ ] 지적사례·제재 note — 유사 패턴만 인용 (과잉 일반화 금지)
- [ ] Escalation 트리거는 corpus 근거 있을 때만
- [ ] note 없는 항목 — 제목+URL만
- [ ] 추가 실증·문서요청이 WP에 반영 가능한 형태로 기술
```

---

## REPORTING (Quality review 포함)

**목적**: 완료·보고 단계 및 **품질검토**에서 결론·공시·Significant matters가 **최근 감독 기대**와 맞는지 점검.

### 서브플로

| 서브 | 트리거 | 초점 |
|------|--------|------|
| **REPORTING** | 보고, 완료, 발행 | 공시·보고서·후속사건·경영자 서한 |
| **QUALITY_REVIEW** | quality review, EQCR, 품질검토 | 감사품질·독립성·네트워크 공시·감리 메시지 |

### 추가 brief

- 초안 결론·KAM·Significant matters 요약 (**Reporting 필수**)
- Quality review: 검토 범위(계획·조서·결론) (**QR 시 필수**)

### Retrieve 초점

- 사업보고서·내부회계·공시 유의사항
- 감사품질·감사인 지정·네트워크·비감사용역
- 제재 사례 중 **보고·공시** 관련

### Part A — Reporting 출력 스키마

```markdown
## Reporting — 규제 렌즈

### 보고 맥락 요약
- KAM, 결론 초안, 발행 일정

### [보고 이슈: {name}]

#### 규제 메시지 (corpus)
- …

#### 보고·공시 시사
- **정합 / 갭**
- **발행 전 확인**

#### 출처
- (YY-MM-DD) [제목](URL)

### Reporting sign-off 체크리스트
- [ ] KAM·공시 항목과 corpus 유의사항 대조
- [ ] 내부회계·자금부정 통제 공시('25~'26 적용) 반영 여부
- [ ] 사업보고서·감사보고서 주석 충실도 — corpus 중점이슈와 정합
- [ ] 후속사건·경영자 서한 — corpus 제재·유의사항 반영
- [ ] 발행 전 sign-off 문서에 규제 렌즈 검토 기록
```

### Part B — Quality review 출력 스키마

```markdown
## Quality review — 규제 렌즈

### QR 범위
- 검토 대상: 계획 / 조서 / 결론 / …

### [QR 초점: {name}]

#### 규제·감독 메시지 (corpus)
- …

#### 품질검토 시사
- **계획·수행·결론** 중 deep dive 지점
- **문서화·증빙** QR 코멘트 초안

#### 출처
- (YY-MM-DD) [제목](URL)

### EQCR/QR 체크리스트
- [ ] 감사품질·감사인감리 메시지와 engagement 투입시간·독립성 대조
- [ ] 비감사용역·네트워크 공시('26~) — 독립성 WP 검토
- [ ] 중점심사·제재 사례 — KAM·절차 설계와 정합
- [ ] QR 코멘트가 corpus 인용 없이 일반론만이 아님
- [ ] EQCR sign-off 전 미해결 gap 목록
```

---

## `quality-updates-writer`와의 경계

| | writer | audit-regulatory-lens |
|---|--------|----------------------|
| 목적 | 코퍼스 **생산** | 코퍼스 **소비** |
| 파일 수정 | 예 (note) | **금지** |
| 트리거 | 요약·스킵·보일러 | Planning/Execution/Reporting |
| 포맷 | note admonition RIGID | 감사 출력 스키마 RIGID-lite |

---

## MCP tool 계약 (v1.1 — 소비자 요구)

corpus spec 구현 후 본 스킬은 MCP를 **우선** 호출한다. 상세는 [Retrieve corpus § MCP v1.1](#mcp-v11-placeholder--corpus-spec-구현-후-활성화) 및 `docs/superpowers/specs/2026-06-27-mcp-corpus-design.md`.
