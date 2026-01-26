

````md
# Agent Instruction: FSC Table Conversion (Markdown)

## Objective
Convert FSC/증선위 press-release tables related to investigation/supervision outcomes
into **MkDocs-compatible Markdown tables** using **fixed, standardized formats**.

There are **two output types**:

1. **Type A — 금융위원회(FSC) 최종 과징금 부과**: final penalty decisions from FSC only.
2. **Type B — 증권선물위원회(증선위) 조치 의결**: "사업보고서 등에 대한 조사·감리결과 조치 - 제○차 증권선물위원회(○.○.) 조치 의결" 보도참고. 회사별 조치와 감사인·공인회계사 조치를 각각 표로 요약.

* 표 작성 시 해당 항목의 **보도자료 링크**를 열어 본문·표를 소스에서 직접 확인한다. 캡처·PDF 첨부는 하지 않는다.

---

## Scope
- **Source**: 금융위원회/증선위 보도자료 **웹 페이지(HTML)**. 캡처·PDF 불필요. 보도자료 URL에서 본문·표 내용을 직접 확인하여 표를 작성한다.
- Content types:
  - **Type A**: FSC decisions on final monetary penalties (과징금 확정).
  - **Type B**: 증선위 조치 의결 보도참고 (회사 조치 + 감사인/공인회계사 조치).
- Subjects include: Company, company-related individuals, auditors/accounting firms.

---

## Type A — 금융위원회 최종 과징금 부과

### Output Format (MANDATORY)

Wrap the table in the following MkDocs admonition block:

```md
!!! note "조사·감리결과 최종 과징금 부과"
````

### Table Schema (DO NOT CHANGE)

```md
| 회사명 | 대상자 | 위반내용 | 과징금 부과액 |
|------|------|----------|---------------|
```

* Column names must match **exactly**.
* Monetary unit must be **백만원**.
* Do not add extra columns.

---

### Normalization Rules (Type A)

#### 1. Ditto Marks (〃, “ )

* Replace all ditto marks with the **full explicit text**.
* Never leave quotation marks in the final output.

#### 2. Company Name Handling

* Repeat company names **only when they change**.
* For subsequent rows under the same company, leave the cell **blank**.

#### 3. Subject (대상자) Rules

Normalize subjects as follows:

* Company itself → `회사` or company name (use as shown in source)
* Executives:

  * `대표이사`, `前대표이사`
  * `대표이사 등 ○인`, `前대표이사 등 ○인`
* Auditors:

  * Accounting firms → use official firm name
  * Auditor groups → e.g. `○○공인회계사감사반`

Do NOT introduce identifiers (A, B, etc.).

---

### Violation Description (위반내용) — Type A

Standardize wording to one of the following patterns:

* Accounting violation:

  ```
  회계처리기준을 위반하여 재무제표 작성
  ```
* Audit violation:

  ```
  회계감사기준을 위반하여 감사업무 수행
  ```
* If the source clearly distinguishes both, reflect that distinction.

---

### Monetary Amount Rules — Type A

* Preserve the exact numeric value from the source.
* Always express as:

  ```
  N.N백만원
  ```
* Do not calculate totals or aggregates.

---

### Content Boundaries — Type A

* Type A applies **only** to **FSC** final penalty (과징금 확정) decisions.
* Do NOT put 증선위 조치 의결 into Type A format.
* Output: **table only**, inside `!!! note "조사·감리결과 최종 과징금 부과"`.

---

### Example Output — Type A (Reference Only)

```md
!!! note "조사·감리결과 최종 과징금 부과"

    | 회사명 | 대상자 | 위반내용 | 과징금 부과액 |
    |------|------|----------|---------------|
    | ㈜ABC | 회사 | 회계처리기준을 위반하여 재무제표 작성 | 123.4백만원 |
    |  | 前대표이사 등 2인 | 회계처리기준을 위반하여 재무제표 작성 | 45.6백만원 |
    |  | XYZ회계법인 | 회계감사기준을 위반하여 감사업무 수행 | 7.8백만원 |
```

---

## Type B — 증권선물위원회(증선위) 조치 의결

"사업보고서 등에 대한 조사·감리결과 조치 - 제○차 증권선물위원회(○.○.) 조치 의결" 보도참고에 대해서는 **Type B** 형식을 사용한다. 과징금 확정 여부와 관계없이, 회사별 조치와 감사인·공인회계사 조치를 각각 표로 요약한다.

### Output Format (MANDATORY)

* Collapsible admonition 사용:

```md
??? note "조사·감리결과 지적사항 및 조치내역"
```

* 그 안에 **두 개의 표**를 넣는다:
  1. **회사별 조치 요약**
  2. **감사인 및 공인회계사 조치 요약**

### Table Schemas (DO NOT CHANGE)

**회사별 조치 요약**

```md
| 회사명 | 구분 | 주요 지적사항 | 주요 조치 |
|------|------|--------------|-----------|
```

* 구분: 예) 유가증권시장 상장, 코넥스 상장, 비상장 등.
* 주요 지적사항: 회계처리기준 위반·공시 누락 등 요약.
* 주요 조치: 과징금(확정액 또는 예정), 감사인지정, 해임권고·직무정지 등.

**감사인 및 공인회계사 조치 요약**

```md
| 회사 | 주요 지적사항 | 대상 | 조치 |
|------|---------------|------|------|
```

* 회사: 해당 감사 대상 회사명. 같은 회사가 이어지면 셀 **비움**.
* 주요 지적사항: 감사절차 소홀, 회계감사기준 위반, 감사반 등록 규정 위반 등. 같은 내용이 이어지면 셀 **비움**.
* 대상: 회계법인명, 감사반명, 또는 "공인회계사".
* 조치: 과징금(예정), 손해배상공동기금 추가적립, 감사업무제한, 직무연수 등.

### Content Boundaries — Type B

* **증선위** "조치 의결" 보도참고에만 적용.
* 금융위 "최종 과징금 부과" 의결은 Type A로 작성.
* 한국공인회계사회(위탁감리위원회) 조치도 감사인·공인회계사 표에 포함 가능(지적사항에 감리집행기관 구분 반영 가능).

### Example Output — Type B (Reference Only)

```md
??? note "조사·감리결과 지적사항 및 조치내역"

    **회사별 조치 요약**

    | 회사명 | 구분 | 주요 지적사항 | 주요 조치 |
    |------|------|--------------|-----------|
    | ㈜오리엔트바이오 | 유가증권시장 상장 | 매출 과대·과소계상, 매출채권 대손충당금 과소계상, …(회계처리기준 위반) | 과징금 110.4백만원(회사관계자 향후 금융위 결정), 감사인지정 3년, … |
    | 대한토지신탁㈜ | 비상장 | 특수관계자거래 주석 누락 | 과징금(예정), 감사인지정 2년 |

    **감사인 및 공인회계사 조치 요약**

    | 회사 | 주요 지적사항 | 대상 | 조치 |
    |------|---------------|------|------|
    | ㈜오리엔트바이오 | 매출 등에 대한 감사절차 소홀(회계감사기준 위반) | 대영회계법인 | 과징금(예정), 손해배상공동기금 추가적립 30%, … |
    |  |  | 공인회계사 | ㈜오리엔트바이오 감사업무제한 2년, … |
    | OOOO㈜ 등 4개사 | 감사반 등록 규정 위반('22 회계연도) | 예성공인회계사감사반 | 해당 4개사 감사업무제한 2년 |
    |  |  | 공인회계사 | 해당 4개사 감사업무제한 1년, … |
```

---

## Quality Checklist (Agent Self-Check)

**Type A (금융위 최종 과징금)**

* [ ] `!!! note "조사·감리결과 최종 과징금 부과"` 사용
* [ ] 표 헤더 일치, 과징금 단위 백만원
* [ ] 〃 제거, 회사명 반복 최소화
* [ ] 표 밖 설명 문구 없음

**Type B (증선위 조치 의결)**

* [ ] `??? note "조사·감리결과 지적사항 및 조치내역"` 사용
* [ ] **회사별 조치 요약** 표(회사명 \| 구분 \| 주요 지적사항 \| 주요 조치)
* [ ] **감사인 및 공인회계사 조치 요약** 표(회사 \| 주요 지적사항 \| 대상 \| 조치)
* [ ] 동일 회사·동일 지적사항 시 셀 비움

이상 중 하나라도 맞지 않으면 **수정 후 출력**한다.

