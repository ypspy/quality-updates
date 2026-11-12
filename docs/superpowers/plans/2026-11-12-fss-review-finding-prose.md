# 품질관리감리 지적 원문 문장 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docs/fss-review/index.md`의 지적 원문에서 끊긴 문장만 잇고, 한 문장에 섞인 지적만 나누며, 맞춤법·띄어쓰기·비문만 고친다.

**Architecture:** 문장 판단은 에이전트가 한다. 분할 규칙 함수는 만들지 않는다. `scripts/fss_review_cards.py`는 카드 배치만 하고 원문 HTML을 유지한다. 삼일회계법인 예시로 결과 모양을 고정한 뒤, 연도마다 원문을 고친다.

**Tech Stack:** Python 3, pytest, 기존 `scripts/fss_review_cards.py`, `scripts/validate_content.py`.

**Spec:** `docs/superpowers/specs/2026-11-12-fss-review-finding-prose-design.md`

## Global Constraints

- 대상은 `div.fss-original` 안의 본문이다.
- 심각도 뱃지 `일부미흡`, `일부미운영`, `미설계`의 글자와 위치는 유지한다. 같은 심각도가 이어지면 뱃지는 한 번만 붙인다. 뱃지 바로 뒤 공백 하나는 유지한다.
- 법인, 연도, 군, 중분류, 숫자, 고유명사는 옮기거나 지어내지 않는다.
- 문장이 문단 중간에서 끊긴 곳만 잇는다. 다음 문단이 앞 문장의 나머지이면 한 문단으로 합친다.
- 한 문장 안에 지적이 둘 이상이면 지적마다 `p.fss-finding` 하나로 나눈다. 나누는 판단은 에이전트가 한다. 규칙 함수로 갈라내지 않는다.
- 나눈 뒤 `미흡하고`, `미흡하며`처럼 뒷말을 기다리던 어미는 그 지적의 원래 줄기인 `미흡`으로 맺는다. `함`이나 `음`을 새로 붙이지 않는다.
- `하였으나`, `등`으로 같은 사실을 풀어 쓴 부분은 그 지적 안에 남긴다. 한 지적인지 둘인지 가르기 어려우면 나누지 않고 한 문단에 둔다.
- 맞춤법, 띄어쓰기, 비문만 고친다. `~함`, `~음` 같은 개조식 어미는 유지한다. `~합니다`, `~다` 체로 바꾸지 않는다. 없는 어미를 새로 붙이지 않는다.
- 유료 API를 호출하지 않는다.
- `scripts/fss_review_cards.py`는 수정하지 않는다.

## File Structure

- `scripts/tests/test_fss_review_cards.py`: 카드 재작성 뒤에도 원문 문장이 같은지, 삼일 예시가 두 문단인지 검사한다.
- `docs/fss-review/index.md`: 지적 원문 문장만 고친다. 카드 구조, 연도, 법인, 뱃지 종류는 유지한다.
- `scripts/fss_review_cards.py`: 변경하지 않는다. 배치 함수가 원문 HTML을 유지하는지만 테스트로 잠근다.

---

### Task 1: 카드 재작성은 원문 문장을 유지한다

**Files:**

- Modify: `scripts/tests/test_fss_review_cards.py`
- Test: `scripts/tests/test_fss_review_cards.py`

**Interfaces:**

- Consumes: `PAGE`, `arrange_by_year`, `place_labels`, `collapse_document`, `repair_severity_gap`
- Produces: `test_card_rewrite_keeps_original_sentences`. 이후 태스크가 `index.md` 문장을 고쳐도 이 테스트는 통과해야 한다.

- [ ] **Step 1: Write the preservation test**

`scripts/tests/test_fss_review_cards.py` 맨 위에 `import re`를 추가한다. 파일 끝에 다음 테스트를 넣는다.

```python
def test_card_rewrite_keeps_original_sentences():
    text = PAGE.read_text(encoding="utf-8")
    rewritten = arrange_by_year(place_labels(collapse_document(text)))

    def bodies(html):
        return sorted(
            repair_severity_gap(body)
            for body in re.findall(r'<div class="fss-original"[^>]*>(.*?)</div>', html)
        )

    assert bodies(rewritten) == bodies(text)
```

- [ ] **Step 2: Run the test**

Run: `cd scripts && python -m pytest tests/test_fss_review_cards.py::test_card_rewrite_keeps_original_sentences -q`

Expected: PASS. 현재 페이지의 원문 1273개는 재작성 뒤에도 같다. FAIL이면 `fss_review_cards.py`를 고치지 않고 멈춘다.

- [ ] **Step 3: Commit**

```bash
git add scripts/tests/test_fss_review_cards.py
git commit -m "test(fss-review): 카드 재작성이 원문 문장을 유지하는지 잠근다"
```

### Task 2: 삼일회계법인 감사업무시간 예시를 두 문단으로 고친다

**Files:**

- Modify: `scripts/tests/test_fss_review_cards.py`
- Modify: `docs/fss-review/index.md`
- Test: `scripts/tests/test_fss_review_cards.py`

**Interfaces:**

- Consumes: `PAGE`, `test_card_rewrite_keeps_original_sentences`
- Produces: `test_samil_time_finding_is_two_paragraphs`. 이후 연도 태스크는 이 문단 경계를 되돌리지 않는다.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_fss_review_cards.py` 끝에 추가한다.

```python
def test_samil_time_finding_is_two_paragraphs():
    text = PAGE.read_text(encoding="utf-8")
    marker = "Time report에 입력"
    at = text.find(marker)
    assert at >= 0
    original_start = text.rfind('<div class="fss-original"', 0, at)
    original_end = text.find("</div>", at)
    body = text[original_start:original_end]
    assert body.count('<p class="fss-finding">') == 2
    assert "입력·승인하였으나" in body
    assert "입력· 승인" not in body
    assert "통제절차가 미흡</p>" in body
    assert "통제절차가 미흡하고" not in body
    assert "통제절차가 미흡함" not in body
    assert body.count("fss-sev") == 1
    assert "공시되는 외부감사 투입시간을 집계하는 절차 운영이 일부 미흡</p>" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest tests/test_fss_review_cards.py::test_samil_time_finding_is_two_paragraphs -q`

Expected: FAIL. 현재 본문에는 `입력· 승인하였으나,`와 `통제절차가 미흡하고`가 있다.

- [ ] **Step 3: Replace that one original**

`docs/fss-review/index.md`에서 아래 문자열만 바꾼다. 다른 삼일회계법인 원문은 이 태스크에서 건드리지 않는다.

고치기 전:

```html
<p class="fss-finding"><span class="fss-sev fss-sev-part">일부미흡</span> 일부 감사업무에 대해 동일 본부 내 다른 회계사들(파트너 등)이 검토 및 코칭업무를 인당 94~128시간 수행하였다고 Time report에 입력· 승인하였으나,</p><p class="fss-finding">동 회계사들이 Time report상 수행했다고 주장하는 업무에 대해 업무수행사실이 확인되지 않는 등 감사시간 입력 및 승인에 대한 통제절차가 미흡하고, 공시되는 외부감사 투입시간을 집계하는 절차 운영이 일부 미흡</p>
```

고친 뒤:

```html
<p class="fss-finding"><span class="fss-sev fss-sev-part">일부미흡</span> 일부 감사업무에 대해 동일 본부 내 다른 회계사들(파트너 등)이 검토 및 코칭업무를 인당 94~128시간 수행하였다고 Time report에 입력·승인하였으나, 동 회계사들이 Time report상 수행했다고 주장하는 업무에 대해 업무수행사실이 확인되지 않는 등 감사시간 입력 및 승인에 대한 통제절차가 미흡</p><p class="fss-finding">공시되는 외부감사 투입시간을 집계하는 절차 운영이 일부 미흡</p>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python -m pytest tests/test_fss_review_cards.py::test_samil_time_finding_is_two_paragraphs tests/test_fss_review_cards.py::test_card_rewrite_keeps_original_sentences -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/tests/test_fss_review_cards.py docs/fss-review/index.md
git commit -m "fix(fss-review): 삼일 감사업무시간 원문을 두 지적 문단으로 나눈다"
```

### Task 3: 2025년 나머지 원문

**Files:**

- Modify: `docs/fss-review/index.md`
- Test: `scripts/tests/test_fss_review_cards.py`

**Interfaces:**

- Consumes: Global Constraints, `test_samil_time_finding_is_two_paragraphs`
- Produces: `data-year="2025"` 안의 원문이 Global Constraints를 만족한다. 삼일 감사업무시간 예시는 Task 2 문장을 유지한다.

- [ ] **Step 1: List that year's originals**

저장소 루트에서 실행한다.

```python
from pathlib import Path
import re

text = Path("docs/fss-review/index.md").read_text(encoding="utf-8")
year = re.search(
    r'<div class="fss-year" data-year="2025">(.*)<div class="fss-year" data-year="2024"',
    text,
)
assert year
bodies = re.findall(r'<div class="fss-original"[^>]*>(.*?)</div>', year.group(1))
print(len(bodies))
for index, body in enumerate(bodies):
    print(f"\n--- {index} ---")
    print(body)
```

Expected: `269`

- [ ] **Step 2: Edit each original**

Task 2에서 고친 `Time report에 입력·승인하였으나` 원문은 다시 쓰지 않는다. 나머지 2025년 원문마다 다음 순서로 고친다.

1. `</p><p class="fss-finding">`가 문장 중간에 있으면 앞뒤 문단을 공백 하나로 잇는다.
2. 한 문장에 지적이 둘 이상이면 `p.fss-finding`을 지적 수만큼 나눈다. 확신이 없으면 나누지 않는다.
3. 나눈 문단의 `미흡하고`, `미흡하며`는 `미흡`으로 맺는다. `함`, `음`은 추가하지 않는다.
4. 맞춤법, 띄어쓰기, 비문만 고친다. 개조식 어미, 숫자, 법인명, 심각도 뱃지는 유지한다.
5. 같은 심각도가 이어지면 `span.fss-sev`는 첫 문단에만 둔다.

- [ ] **Step 3: Run tests**

Run: `cd scripts && python -m pytest tests/test_fss_review_cards.py::test_samil_time_finding_is_two_paragraphs tests/test_fss_review_cards.py::test_card_rewrite_keeps_original_sentences -q`

Run from the repository root: `python scripts/validate_content.py --strict`

Expected: PASS, exit 0

- [ ] **Step 4: Commit**

```bash
git add docs/fss-review/index.md
git commit -m "fix(fss-review): 2025년 지적 원문의 끊긴 문장과 섞인 지적을 고친다"
```

### Task 4: 2024년 원문

**Files:**

- Modify: `docs/fss-review/index.md`
- Test: `scripts/tests/test_fss_review_cards.py`

**Interfaces:**

- Consumes: Global Constraints
- Produces: `data-year="2024"` 안의 원문이 Global Constraints를 만족한다.

- [ ] **Step 1: List that year's originals**

```python
from pathlib import Path
import re

text = Path("docs/fss-review/index.md").read_text(encoding="utf-8")
year = re.search(
    r'<div class="fss-year" data-year="2024"[^>]*>(.*)<div class="fss-year" data-year="2023"',
    text,
)
assert year
bodies = re.findall(r'<div class="fss-original"[^>]*>(.*?)</div>', year.group(1))
print(len(bodies))
for index, body in enumerate(bodies):
    print(f"\n--- {index} ---")
    print(body)
```

Expected: `264`

- [ ] **Step 2: Edit each original**

2024년 원문마다 다음 순서로 고친다.

1. `</p><p class="fss-finding">`가 문장 중간에 있으면 앞뒤 문단을 공백 하나로 잇는다.
2. 한 문장에 지적이 둘 이상이면 `p.fss-finding`을 지적 수만큼 나눈다. 확신이 없으면 나누지 않는다.
3. 나눈 문단의 `미흡하고`, `미흡하며`는 `미흡`으로 맺는다. `함`, `음`은 추가하지 않는다.
4. 맞춤법, 띄어쓰기, 비문만 고친다. 개조식 어미, 숫자, 법인명, 심각도 뱃지는 유지한다.
5. 같은 심각도가 이어지면 `span.fss-sev`는 첫 문단에만 둔다.

- [ ] **Step 3: Run tests**

Run: `cd scripts && python -m pytest tests/test_fss_review_cards.py::test_samil_time_finding_is_two_paragraphs tests/test_fss_review_cards.py::test_card_rewrite_keeps_original_sentences -q`

Run from the repository root: `python scripts/validate_content.py --strict`

Expected: PASS, exit 0

- [ ] **Step 4: Commit**

```bash
git add docs/fss-review/index.md
git commit -m "fix(fss-review): 2024년 지적 원문의 끊긴 문장과 섞인 지적을 고친다"
```

### Task 5: 2023년 원문

**Files:**

- Modify: `docs/fss-review/index.md`
- Test: `scripts/tests/test_fss_review_cards.py`

**Interfaces:**

- Consumes: Global Constraints
- Produces: `data-year="2023"` 안의 원문이 Global Constraints를 만족한다.

- [ ] **Step 1: List that year's originals**

```python
from pathlib import Path
import re

text = Path("docs/fss-review/index.md").read_text(encoding="utf-8")
year = re.search(
    r'<div class="fss-year" data-year="2023"[^>]*>(.*)<div class="fss-year" data-year="2022"',
    text,
)
assert year
bodies = re.findall(r'<div class="fss-original"[^>]*>(.*?)</div>', year.group(1))
print(len(bodies))
for index, body in enumerate(bodies):
    print(f"\n--- {index} ---")
    print(body)
```

Expected: `261`

- [ ] **Step 2: Edit each original**

2023년 원문마다 다음 순서로 고친다.

1. `</p><p class="fss-finding">`가 문장 중간에 있으면 앞뒤 문단을 공백 하나로 잇는다.
2. 한 문장에 지적이 둘 이상이면 `p.fss-finding`을 지적 수만큼 나눈다. 확신이 없으면 나누지 않는다.
3. 나눈 문단의 `미흡하고`, `미흡하며`는 `미흡`으로 맺는다. `함`, `음`은 추가하지 않는다.
4. 맞춤법, 띄어쓰기, 비문만 고친다. 개조식 어미, 숫자, 법인명, 심각도 뱃지는 유지한다.
5. 같은 심각도가 이어지면 `span.fss-sev`는 첫 문단에만 둔다.

- [ ] **Step 3: Run tests**

Run: `cd scripts && python -m pytest tests/test_fss_review_cards.py::test_samil_time_finding_is_two_paragraphs tests/test_fss_review_cards.py::test_card_rewrite_keeps_original_sentences -q`

Run from the repository root: `python scripts/validate_content.py --strict`

Expected: PASS, exit 0

- [ ] **Step 4: Commit**

```bash
git add docs/fss-review/index.md
git commit -m "fix(fss-review): 2023년 지적 원문의 끊긴 문장과 섞인 지적을 고친다"
```

### Task 6: 2022년 원문

**Files:**

- Modify: `docs/fss-review/index.md`
- Test: `scripts/tests/test_fss_review_cards.py`

**Interfaces:**

- Consumes: Global Constraints
- Produces: `data-year="2022"` 안의 원문이 Global Constraints를 만족한다.

- [ ] **Step 1: List that year's originals**

```python
from pathlib import Path
import re

text = Path("docs/fss-review/index.md").read_text(encoding="utf-8")
year = re.search(
    r'<div class="fss-year" data-year="2022"[^>]*>(.*)<div class="fss-year" data-year="2021"',
    text,
)
assert year
bodies = re.findall(r'<div class="fss-original"[^>]*>(.*?)</div>', year.group(1))
print(len(bodies))
for index, body in enumerate(bodies):
    print(f"\n--- {index} ---")
    print(body)
```

Expected: `300`

- [ ] **Step 2: Edit each original**

2022년 원문마다 다음 순서로 고친다.

1. `</p><p class="fss-finding">`가 문장 중간에 있으면 앞뒤 문단을 공백 하나로 잇는다.
2. 한 문장에 지적이 둘 이상이면 `p.fss-finding`을 지적 수만큼 나눈다. 확신이 없으면 나누지 않는다.
3. 나눈 문단의 `미흡하고`, `미흡하며`는 `미흡`으로 맺는다. `함`, `음`은 추가하지 않는다.
4. 맞춤법, 띄어쓰기, 비문만 고친다. 개조식 어미, 숫자, 법인명, 심각도 뱃지는 유지한다.
5. 같은 심각도가 이어지면 `span.fss-sev`는 첫 문단에만 둔다.

- [ ] **Step 3: Run tests**

Run: `cd scripts && python -m pytest tests/test_fss_review_cards.py::test_samil_time_finding_is_two_paragraphs tests/test_fss_review_cards.py::test_card_rewrite_keeps_original_sentences -q`

Run from the repository root: `python scripts/validate_content.py --strict`

Expected: PASS, exit 0

- [ ] **Step 4: Commit**

```bash
git add docs/fss-review/index.md
git commit -m "fix(fss-review): 2022년 지적 원문의 끊긴 문장과 섞인 지적을 고친다"
```

### Task 7: 2021년 원문

**Files:**

- Modify: `docs/fss-review/index.md`
- Test: `scripts/tests/test_fss_review_cards.py`

**Interfaces:**

- Consumes: Global Constraints
- Produces: `data-year="2021"` 안의 원문이 Global Constraints를 만족한다.

- [ ] **Step 1: List that year's originals**

```python
from pathlib import Path
import re

text = Path("docs/fss-review/index.md").read_text(encoding="utf-8")
year = re.search(
    r'<div class="fss-year" data-year="2021"[^>]*>(.*)<div class="fss-year" data-year="2020"',
    text,
)
assert year
bodies = re.findall(r'<div class="fss-original"[^>]*>(.*?)</div>', year.group(1))
print(len(bodies))
for index, body in enumerate(bodies):
    print(f"\n--- {index} ---")
    print(body)
```

Expected: `80`

- [ ] **Step 2: Edit each original**

2021년 원문마다 다음 순서로 고친다.

1. `</p><p class="fss-finding">`가 문장 중간에 있으면 앞뒤 문단을 공백 하나로 잇는다.
2. 한 문장에 지적이 둘 이상이면 `p.fss-finding`을 지적 수만큼 나눈다. 확신이 없으면 나누지 않는다.
3. 나눈 문단의 `미흡하고`, `미흡하며`는 `미흡`으로 맺는다. `함`, `음`은 추가하지 않는다.
4. 맞춤법, 띄어쓰기, 비문만 고친다. 개조식 어미, 숫자, 법인명, 심각도 뱃지는 유지한다.
5. 같은 심각도가 이어지면 `span.fss-sev`는 첫 문단에만 둔다.

- [ ] **Step 3: Run tests**

Run: `cd scripts && python -m pytest tests/test_fss_review_cards.py::test_samil_time_finding_is_two_paragraphs tests/test_fss_review_cards.py::test_card_rewrite_keeps_original_sentences -q`

Run from the repository root: `python scripts/validate_content.py --strict`

Expected: PASS, exit 0

- [ ] **Step 4: Commit**

```bash
git add docs/fss-review/index.md
git commit -m "fix(fss-review): 2021년 지적 원문의 끊긴 문장과 섞인 지적을 고친다"
```

### Task 8: 2020년 원문

**Files:**

- Modify: `docs/fss-review/index.md`
- Test: `scripts/tests/test_fss_review_cards.py`

**Interfaces:**

- Consumes: Global Constraints
- Produces: `data-year="2020"` 안의 원문이 Global Constraints를 만족한다.

- [ ] **Step 1: List that year's originals**

```python
from pathlib import Path
import re

text = Path("docs/fss-review/index.md").read_text(encoding="utf-8")
year = re.search(
    r'<div class="fss-year" data-year="2020"[^>]*>(.*)<div class="fss-year" data-year="2019"',
    text,
)
assert year
bodies = re.findall(r'<div class="fss-original"[^>]*>(.*?)</div>', year.group(1))
print(len(bodies))
for index, body in enumerate(bodies):
    print(f"\n--- {index} ---")
    print(body)
```

Expected: `59`

- [ ] **Step 2: Edit each original**

2020년 원문마다 다음 순서로 고친다.

1. `</p><p class="fss-finding">`가 문장 중간에 있으면 앞뒤 문단을 공백 하나로 잇는다.
2. 한 문장에 지적이 둘 이상이면 `p.fss-finding`을 지적 수만큼 나눈다. 확신이 없으면 나누지 않는다.
3. 나눈 문단의 `미흡하고`, `미흡하며`는 `미흡`으로 맺는다. `함`, `음`은 추가하지 않는다.
4. 맞춤법, 띄어쓰기, 비문만 고친다. 개조식 어미, 숫자, 법인명, 심각도 뱃지는 유지한다.
5. 같은 심각도가 이어지면 `span.fss-sev`는 첫 문단에만 둔다.

- [ ] **Step 3: Run tests**

Run: `cd scripts && python -m pytest tests/test_fss_review_cards.py::test_samil_time_finding_is_two_paragraphs tests/test_fss_review_cards.py::test_card_rewrite_keeps_original_sentences -q`

Run from the repository root: `python scripts/validate_content.py --strict`

Expected: PASS, exit 0

- [ ] **Step 4: Commit**

```bash
git add docs/fss-review/index.md
git commit -m "fix(fss-review): 2020년 지적 원문의 끊긴 문장과 섞인 지적을 고친다"
```

### Task 9: 2019년 원문

**Files:**

- Modify: `docs/fss-review/index.md`
- Test: `scripts/tests/test_fss_review_cards.py`

**Interfaces:**

- Consumes: Global Constraints
- Produces: `data-year="2019"` 안의 원문이 Global Constraints를 만족한다. 이 태스크가 현재 페이지 교정의 마지막이다.

- [ ] **Step 1: List that year's originals**

```python
from pathlib import Path
import re

text = Path("docs/fss-review/index.md").read_text(encoding="utf-8")
year = re.search(
    r'<div class="fss-year" data-year="2019"[^>]*>(.*)<div id="fss-firm-index"',
    text,
    re.S,
)
assert year
bodies = re.findall(r'<div class="fss-original"[^>]*>(.*?)</div>', year.group(1))
print(len(bodies))
for index, body in enumerate(bodies):
    print(f"\n--- {index} ---")
    print(body)
```

Expected: `40`. `re.S`가 필요하다. 2019년 블록과 이름 목록 사이에 줄바꿈이 있다.

- [ ] **Step 2: Edit each original**

2019년 원문마다 다음 순서로 고친다.

1. `</p><p class="fss-finding">`가 문장 중간에 있으면 앞뒤 문단을 공백 하나로 잇는다.
2. 한 문장에 지적이 둘 이상이면 `p.fss-finding`을 지적 수만큼 나눈다. 확신이 없으면 나누지 않는다.
3. 나눈 문단의 `미흡하고`, `미흡하며`는 `미흡`으로 맺는다. `함`, `음`은 추가하지 않는다.
4. 맞춤법, 띄어쓰기, 비문만 고친다. 개조식 어미, 숫자, 법인명, 심각도 뱃지는 유지한다.
5. 같은 심각도가 이어지면 `span.fss-sev`는 첫 문단에만 둔다.

- [ ] **Step 3: Run tests**

Run: `cd scripts && python -m pytest tests/test_fss_review_cards.py -q`

Run from the repository root: `python scripts/validate_content.py --strict`

Expected: PASS, exit 0

- [ ] **Step 4: Commit**

```bash
git add docs/fss-review/index.md
git commit -m "fix(fss-review): 2019년 지적 원문의 끊긴 문장과 섞인 지적을 고친다"
```
