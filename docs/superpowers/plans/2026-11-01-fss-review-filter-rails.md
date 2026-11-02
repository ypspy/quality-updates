# 품질관리감리 필터 레일 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 품질관리감리 페이지에서 왼쪽은 참고2 순서의 등록 법인과 일반·감사반 묶음, 오른쪽 위는 연도, 그 아래는 대분류 목차가 되고, 법인 필터와 연도 필터가 함께 걸리게 한다.

**Architecture:** 필터 규칙만 `fss-filter.js`에 둔다. `extra.js`는 기존 본문 DOM에 그 규칙을 적용하고, Material 왼쪽·오른쪽 레일에 목록을 끼운다. 본문 HTML은 다시 생성하지 않는다. 중분류 연도 탭은 숨기고, 연도 블록은 최근 해부터 모두 펼친다.

**Tech Stack:** MkDocs Material, 기존 `docs/assets/javascripts/extra.js`, `docs/assets/stylesheets/extra.css`, Node.js 내장 `node --test`

**Spec:** `docs/superpowers/specs/2026-11-01-fss-review-filter-rails-design.md`

## Global Constraints

- 이 페이지(`/fss-review/`)에서만 레일이 바뀐다. 다른 페이지의 사이트 메뉴와 헤더 탭은 유지한다.
- 등록 40곳의 순서와 군 이름은 스펙의 가군→나군→다군→라군 목록 그대로다. 군 이름은 버튼이 아니다.
- 본문의 가·나·다·라 묶음, 요약 문장, 뱃지, 분류 규칙은 바꾸지 않는다.
- `scripts/classify_fss_findings.py --write`로 `docs/fss-review/index.md`를 다시 만들지 않는다.
- 법인 쪽 필터는 하나(`name` 또는 `kind`), 연도 필터는 하나다. 같은 값을 다시 고르면 그 필드만 비운다.
- 등록 이름 또는 검색으로 한 법인을 고르면 그 법인만 남고 원문이 열린다. 일반회계법인·감사반 줄을 고르면 그 묶음만 남고 원문은 닫혀 있다.
- 지우기와 빈 검색창은 법인 필터만 푼다. 연도는 유지한다.
- 필터가 켜져 있는데 보이는 묶음이 없으면 문장은 `이 조건에 해당하는 분류된 지적이 없습니다.`이다.
- 필터가 모두 꺼지면 빈 군은 `분류된 지적 없음`을 다시 보인다.
- 화면 너비 40em 이하에서 연도 버튼 글자는 `'24년` 형식이고, 버튼 안에서는 줄바꿈하지 않는다. 그보다 넓으면 `2024년`이다.
- 분기 보도자료와 HITL 마커는 수정하지 않는다.
- 작업 트리는 `G:\내 드라이브\80_개발_AI\quality-updates`이다. 이 폴더는 git 저장소가 아니다. 커밋은 `C:\Users\yoont\AppData\Local\qu-pr-work`의 `fss-review-full-period`에, 그 태스크가 바꾼 파일만 복사한 뒤 한다. PDF, Mint 폴더, `mkdocs.yml`, `docs/index.md`, `docs/fss-review/fr2022.md`는 복사하지 않는다.

---

## File map

| File | Action |
|------|--------|
| `docs/assets/javascripts/fss-filter.js` | Create — 등록 순서, 연도 글자, 필터 상태 |
| `docs/assets/javascripts/fss-filter.test.js` | Create — `node --test` |
| `mkdocs.yml` | Modify — `extra_javascript`에서 `fss-filter.js`를 `extra.js`보다 앞에 둔다 |
| `docs/assets/javascripts/extra.js` | Modify — 레일 주입, 본문 필터, 연도 블록 |
| `docs/assets/stylesheets/extra.css` | Modify — 레일, 연도 블록, `nowrap` |
| `docs/superpowers/README.md` | Modify — spec·plan 색인 한 줄씩 |
| `docs/superpowers/specs/2026-11-01-fss-review-filter-rails-design.md` | Modify — 상태를 구현 중으로 |

`docs/fss-review/index.md`는 수정하지 않는다.

---

### Task 1: 필터 상태 모듈

**Files:**
- Create: `docs/assets/javascripts/fss-filter.js`
- Create: `docs/assets/javascripts/fss-filter.test.js`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `REGISTERED`: `{ gun: string, firms: string[] }[]` 길이 4. 군 순서는 `가군`, `나군`, `다군`, `라군`.
  - `yearLabel(year: string, narrow: boolean): string`
  - `reduceFilter(state: {name: string|null, kind: string|null, year: string|null}, action: {type: "name"|"kind"|"year"|"clearFirm", value?: string}): state`
  - `groupVisible(group: {names: string[], kind: string, year: string}, state): {show: boolean, open: boolean}`
  - 브라우저에서는 `window.FssFilter`, Node에서는 `module.exports`로 같은 객체를 내보낸다.

- [ ] **Step 1: Write the failing test**

`docs/assets/javascripts/fss-filter.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { REGISTERED, yearLabel, reduceFilter, groupVisible } = require("./fss-filter.js");

const empty = { name: null, kind: null, year: null };

test("registered order follows 참고2", function () {
  assert.deepEqual(REGISTERED.map(function (row) { return row.gun; }), ["가군", "나군", "다군", "라군"]);
  assert.deepEqual(REGISTERED[0].firms, ["삼일회계법인", "삼정회계법인", "안진회계법인", "한영회계법인"]);
  assert.equal(REGISTERED[3].firms[REGISTERED[3].firms.length - 1], "한길회계법인");
  assert.equal(REGISTERED.reduce(function (n, row) { return n + row.firms.length; }, 0), 40);
});

test("yearLabel", function () {
  assert.equal(yearLabel("2024", false), "2024년");
  assert.equal(yearLabel("2023", true), "'23년");
});

test("name and kind are one firm-side filter", function () {
  var named = reduceFilter(empty, { type: "name", value: "삼정회계법인" });
  assert.deepEqual(named, { name: "삼정회계법인", kind: null, year: null });
  var kind = reduceFilter(named, { type: "kind", value: "일반회계법인" });
  assert.deepEqual(kind, { name: null, kind: "일반회계법인", year: null });
  assert.deepEqual(reduceFilter(kind, { type: "kind", value: "일반회계법인" }), empty);
});

test("year survives clearFirm", function () {
  var both = reduceFilter(
    reduceFilter(empty, { type: "name", value: "대주회계법인" }),
    { type: "year", value: "2020" }
  );
  assert.deepEqual(reduceFilter(both, { type: "clearFirm" }), { name: null, kind: null, year: "2020" });
  assert.deepEqual(reduceFilter(both, { type: "year", value: "2020" }), { name: "대주회계법인", kind: null, year: null });
});

test("groupVisible", function () {
  var firm = { names: ["삼정회계법인", "안진회계법인"], kind: "등록", year: "2020" };
  var named = { name: "삼정회계법인", kind: null, year: "2020" };
  assert.deepEqual(groupVisible(firm, named), { show: true, open: true });
  assert.deepEqual(groupVisible(firm, { name: "삼정회계법인", kind: null, year: "2019" }), { show: false, open: false });
  assert.deepEqual(groupVisible(
    { names: ["가립회계법인"], kind: "일반회계법인", year: "2022" },
    { name: null, kind: "일반회계법인", year: null }
  ), { show: true, open: false });
  assert.deepEqual(groupVisible(firm, empty), { show: true, open: false });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test docs/assets/javascripts/fss-filter.test.js`

Expected: FAIL because `fss-filter.js` does not exist.

- [ ] **Step 3: Write minimal implementation**

`docs/assets/javascripts/fss-filter.js`는 스펙의 40개 이름을 `REGISTERED`에 그대로 둔다. `yearLabel`은 `narrow`이면 `'` + 뒤 두 자리 + `년`, 아니면 네 자리 + `년`이다. `reduceFilter`는 같은 `name`·`kind`·`year`를 다시 받으면 그 필드만 `null`로 둔다. `name` 액션은 `kind`를 지우고, `kind` 액션은 `name`을 지운다. `clearFirm`은 `name`과 `kind`만 지운다. `groupVisible`은 연도가 걸려 있고 다르면 `{show:false, open:false}`, `name`이 걸렸으면 그 이름이 `names`에 있을 때만 `{show:true, open:true}`, `kind`가 걸렸으면 `group.kind`가 같을 때만 `{show:true, open:false}`, 법인 필터가 없으면 `{show:true, open:false}`이다.

파일 끝:

```javascript
var api = { REGISTERED: REGISTERED, yearLabel: yearLabel, reduceFilter: reduceFilter, groupVisible: groupVisible };
if (typeof module !== "undefined" && module.exports) module.exports = api;
if (typeof window !== "undefined") window.FssFilter = api;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test docs/assets/javascripts/fss-filter.test.js`

Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

Drive에서 클론으로 이 두 파일만 복사한 뒤:

```powershell
git add -- docs/assets/javascripts/fss-filter.js docs/assets/javascripts/fss-filter.test.js
git commit -F C:\Users\yoont\AppData\Local\Temp\qu-commit.txt
```

메시지: `test(fss-review): 법인·연도 필터 상태를 분리한다`

---

### Task 2: 본문 연도를 쌓고 필터를 적용한다

**Files:**
- Modify: `mkdocs.yml` (`extra_javascript`)
- Modify: `docs/assets/javascripts/extra.js`
- Modify: `docs/assets/stylesheets/extra.css`
- Test: `docs/assets/javascripts/fss-filter.test.js` (회귀)

**Interfaces:**
- Consumes: `window.FssFilter.reduceFilter`, `window.FssFilter.groupVisible`, `window.FssFilter.yearLabel`
- Produces: `initFssReview`가 `state`를 갖고 `paint()`로 본문을 갱신한다. 중분류 연도 버튼(`.fss-years`)은 숨긴다. 각 `.fss-year` 앞에 `p.fss-year-label`을 한 번만 넣고 글자는 `FssFilter.yearLabel(year, false)`이다.

- [ ] **Step 1: Write the failing test**

`fss-filter.test.js`에 추가한다. DOM이 없으므로 “연도 라벨은 항상 네 자리”만 모듈로 고정한다. 본문 적용은 브라우저 확인(Task 4)에서 본다.

```javascript
test("body year label stays four digits", function () {
  assert.equal(yearLabel("2019", false), "2019년");
});
```

- [ ] **Step 2: Run test to verify it fails**

이미 `yearLabel("2024", false)`가 있으면 이 테스트는 구현 전에 통과할 수 있다. 그러면 실패를 새로 만들지 말고 Step 3으로 간다. `node --test docs/assets/javascripts/fss-filter.test.js`가 기존 5개를 통과하는지만 확인한다.

- [ ] **Step 3: Write minimal implementation**

`mkdocs.yml`의 `extra_javascript`를 다음 순서로 바꾼다.

```yaml
extra_javascript:
  - assets/javascripts/fss-filter.js
  - assets/javascripts/extra.js
```

`extra.js`의 `applyYearLabels`는 버튼 글자를 `FssFilter.yearLabel(year, yearQuery.matches)`로 둔다.

`initFssReview` 안에 `var state = { name: null, kind: null, year: null };`를 둔다. `restore()`가 연도 패널을 첫 해만 보이게 하던 부분은 지운다. 대신 `paint()`:

1. `document.querySelectorAll(".fss-years").forEach`로 `hidden = true`.
2. 각 `.fss-year`의 `hidden`은 `state.year`가 있고 그 값과 `data-year`가 다를 때만 `true`다. 연도 필터가 없으면 모든 연도 패널의 `hidden`은 `false`다. `p.fss-year-label`이 없으면 패널 첫 자식으로 넣는다. 텍스트는 `FssFilter.yearLabel(data-year, false)`이다.
3. 각 `.fss-group`에 대해 가장 가까운 `.fss-bundle .fss-bundle-name` 텍스트와 `.fss-year`의 `data-year`, `data-names`를 `groupVisible`에 넘긴다.
4. `show`가 아니면 그룹에 `fss-dim`을 준다. `open`이면 그 이름의 `.fss-original`만 `hidden = false`이고 뱃지에 `on`을 준다. `open`이 아니면 그 그룹의 원문은 닫고 `on`을 뺀다.
5. `.fss-year`, `.fss-gun`, `.fss-bundle`, `.fss-jung`, `.fss-dae`는 안에 `show`인 그룹이 하나도 없으면 `fss-dim`을 준다. 필터가 모두 꺼져 있으면 이 조상들의 `fss-dim`은 주지 않는다. 그래서 빈 군의 `분류된 지적 없음`은 필터가 없을 때만 보인다.
6. `state.name || state.kind || state.year`이고 보이는 그룹이 0이면 `#fss-empty`의 문장을 `이 조건에 해당하는 분류된 지적이 없습니다.`로 하고 `hidden = false`. 아니면 `hidden = true`.
7. `root.classList.toggle("is-filtering", Boolean(state.name || state.kind || state.year))`.

검색에서 이름을 고르면 `state = reduceFilter(state, {type:"name", value})` 후 `input.value = state.name || ""`, `paint()`. 입력창이 비면 `clearFirm`만 한다. 지우기 버튼도 `clearFirm`만 한다. 뱃지 클릭은 `state.kind`일 때만 원문을 여닫고, `state.name`일 때는 이미 열린 원문을 유지한다.

CSS:

```css
.fss-years[hidden] { display: none !important; }
.fss-year-label { font-weight: 700; margin: 0.8rem 0 0.35rem; }
.fss-dim { display: none !important; }
.fss-year-btn { white-space: nowrap; flex: 0 0 auto; }
```

`white-space: nowrap`은 이미 있으면 중복 추가하지 않는다.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test docs/assets/javascripts/fss-filter.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

복사 대상: `mkdocs.yml`, `docs/assets/javascripts/extra.js`, `docs/assets/javascripts/fss-filter.js`, `docs/assets/stylesheets/extra.css`. 클론의 기존 `mkdocs.yml`과 다른 부분이 이 `extra_javascript` 한 곳뿐인지 보고, 그 한 곳만 고친다. Drive의 `mkdocs.yml` 전체를 덮어쓰지 않는다.

메시지: `feat(fss-review): 연도 블록을 펼치고 법인·연도 필터를 본문에 적용한다`

---

### Task 3: 왼쪽 법인 레일과 오른쪽 연도 레일

**Files:**
- Modify: `docs/assets/javascripts/extra.js`
- Modify: `docs/assets/stylesheets/extra.css`

**Interfaces:**
- Consumes: `FssFilter.REGISTERED`, `FssFilter.reduceFilter`, `FssFilter.yearLabel`, Task 2의 `state`와 `paint`
- Produces: `#fss-firm-rail`, `#fss-year-rail`. 연도 레일 버튼은 `class="fss-year-btn"`와 `data-year`를 가진다.

- [ ] **Step 1: Write the failing test**

`fss-filter.test.js`에 군 라벨이 법인 이름 목록에 섞이지 않는 검사를 추가한다.

```javascript
test("gun labels are not firm names", function () {
  var names = REGISTERED.flatMap(function (row) { return row.firms; });
  assert.equal(names.indexOf("가군"), -1);
  assert.equal(names.indexOf("일반회계법인"), -1);
});
```

- [ ] **Step 2: Run test to verify it fails**

`flatMap`이 없는 오래된 해석은 Node 24에서 문제 없다. 테스트는 구현 없이도 통과한다. 실패를 억지로 만들지 말고, 레일이 없다는 확인은 Step 4의 브라우저에서 한다. 단위 테스트는 `node --test docs/assets/javascripts/fss-filter.test.js`로 기존 통과를 확인한다.

- [ ] **Step 3: Write minimal implementation**

`initFssReview`에서 페이지에 `#fss-firm-rail`이 없으면 만든다.

- `.md-sidebar--primary .md-sidebar__inner`의 첫 자식으로 넣는다.
- `REGISTERED`를 돌며 `p.fss-rail-gun`에 군 이름만 넣고, 각 법인은 `button.fss-rail-firm[data-firm]`이다.
- 그 아래 `button.fss-rail-kind[data-kind="일반회계법인"]`, `button.fss-rail-kind[data-kind="감사반"]`.
- 이 페이지에서 `.md-sidebar--primary .md-nav--primary`에 `hidden`을 준다. `header.md-header`의 탭은 그대로 둔다.

`#fss-year-rail`은 `.md-sidebar--secondary .md-sidebar__inner`의 첫 자식이다. 연도는 본문의 `data-year`를 모아 숫자 내림차순으로, `button.fss-year-btn[data-year]`로 만든다. `applyYearLabels`가 이 버튼도 갱신하게 `paint()` 끝에서 `applyYearLabels()`를 호출한다.

클릭:

- `data-firm`이면 `reduceFilter(state, {type:"name", value})`, 검색창은 `state.name || ""`.
- `data-kind`이면 `reduceFilter(state, {type:"kind", value})`, 검색창은 비운다.
- 연도 레일 버튼이면 `reduceFilter(state, {type:"year", value})`.
- 선택된 `data-firm` 또는 `data-kind` 버튼에 `aria-pressed="true"`. 선택된 연도 버튼에 `on`.

본문 `.fss-years` 버튼 클릭 핸들러는 레일이 연도를 담당하므로 제거한다. 이벤트는 `#fss-year-rail`만 받는다.

CSS는 레일 버튼을 블록으로 쌓고, 군 라벨은 작은 글씨로 둔다. 선택된 법인 버튼은 `.fss-year-btn.on`과 같은 대비를 쓴다. 40em 이하에서도 레일은 사이드바 서랍 안에만 있고, 본문 폭을 줄이는 둘째 열을 만들지 않는다.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test docs/assets/javascripts/fss-filter.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

복사 대상: `docs/assets/javascripts/extra.js`, `docs/assets/stylesheets/extra.css`, `docs/assets/javascripts/fss-filter.test.js`.

메시지: `feat(fss-review): 왼쪽 법인 목록과 오른쪽 연도 목록을 둔다`

---

### Task 4: 브라우저에서 스펙 확인과 색인

**Files:**
- Modify: `docs/superpowers/README.md`
- Modify: `docs/superpowers/specs/2026-11-01-fss-review-filter-rails-design.md` (상태 한 줄)

**Interfaces:**
- Consumes: Task 3의 레일
- Produces: 스펙의 확인 목록을 로컬 `http://127.0.0.1:8000/fss-review/`에서 통과한 기록. 실패하면 Task 2 또는 3의 해당 분기만 고친다.

- [ ] **Step 1: Write the failing test**

자동 테스트는 추가하지 않는다. 확인할 관찰을 이 단계의 기대 결과로 고정한다.

- 왼쪽 첫 등록 이름이 `삼일회계법인`이고, `가군` 글자는 버튼이 아니다.
- `삼정회계법인`을 누르면 다른 법인 묶음이 숨고 그 원문이 열린다. 검색창은 `삼정회계법인`이다. 같은 줄을 다시 누르면 법인 필터와 검색창이 비워진다.
- `일반회계법인`을 누르면 그 묶음만 남고 원문은 닫혀 있다. 검색창은 비어 있다. 그 안의 이름을 누르면 원문이 열린다.
- 그 상태에서 `2020` 연도를 누르면 2020년 블록만 남는다. 연도를 다시 누르면 법인 묶음은 유지되고 다른 해도 돌아온다.
- 지우기를 누르면 일반회계법인 필터만 풀리고, 연도를 켜 두었다면 연도는 남는다.
- 삼정 + 본문에 없는 해를 고르면 `이 조건에 해당하는 분류된 지적이 없습니다.`만 보인다.
- 너비 390px에서 오른쪽 연도 버튼 글자가 `'24년`이고 `white-space`가 `nowrap`이다. 너비 1200px에서는 `2024년`이다.

- [ ] **Step 2: Run test to verify it fails**

로컬 서버가 떠 있으면 `http://127.0.0.1:8000/fss-review/`를 연다. Task 3까지 반영된 뒤에는 이 목록이 통과해야 한다. 하나라도 실패하면 그 항목만 고치고 다시 본다.

- [ ] **Step 3: Write minimal implementation**

실패가 없을 때는 코드 대신 색인만 고친다. `docs/superpowers/README.md`의 Specs 표 맨 위와 Plans 표 맨 위에 2026-11-01 행을 추가한다.

- spec 요약: `품질관리감리 왼쪽 법인 목록과 오른쪽 연도 필터`
- plan 요약: 같은 문장

스펙 첫 상태 줄을 `상태: 구현 계획이 docs/superpowers/plans/2026-11-01-fss-review-filter-rails.md 에 있다.`로 바꾼다.

- [ ] **Step 4: Run test to verify it passes**

`node --test docs/assets/javascripts/fss-filter.test.js`가 PASS이고, Step 1의 브라우저 관찰이 모두 맞다.

- [ ] **Step 5: Commit**

복사 대상: `docs/superpowers/README.md`, `docs/superpowers/specs/2026-11-01-fss-review-filter-rails-design.md`, 그리고 Task 2·3에서 아직 클론에 없는 자산 파일.

메시지: `docs(fss-review): 필터 레일 계획과 확인 결과를 색인에 남긴다`

원격에는 올리지 않는다.
