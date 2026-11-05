# 지식체계 요약을 베지 PR로 넘기기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 커서 대화가 끝난 뒤 마지막 응답에 지식체계 요약 일곱 항목이 있으면, 그 블록만 `ypspy/my-obsidian-vault`의 inbox 브랜치 PR로 연다.

**Architecture:** `stop` 사용자 훅이 대화 기록에서 마지막 어시스턴트 글만 읽고, 일곱 항목 블록을 노트와 PR 인자로 바꾼다. 테스트는 그 인자만 검사한다. 실제 `git`/`gh` 호출은 훅 실행 함수 안에만 두고, 푸시 대상은 `refs/heads/inbox/...` 하나다.

**Tech Stack:** Python 3 표준 라이브러리, Cursor 사용자 훅 `stop`, GitHub CLI `gh`

**Spec:** `docs/superpowers/specs/2026-11-02-cursor-summary-pr-design.md`

## Global Constraints

- 요약 전달은 사용자 훅이다. `~/.cursor/hooks.json`의 `stop` 이벤트가 스크립트를 실행한다. 품질관리 사이트 코드와 이 저장소의 프로젝트 훅은 쓰지 않는다.
- 훅 실패는 대화를 막지 않는다. 표준 출력은 `{}`이고 종료 코드는 0이다. `followup_message`는 출력하지 않는다. `failClosed`는 넣지 않는다. `loop_limit`는 0이다.
- 요약은 유형, 프로젝트, 날짜(`YYYY-MM-DD`), 요약, 근거, 다음 액션, 미결이 한 덩어리다. 응답의 다른 글, 대화 전문, 코드 블록, 도구 출력은 노트에 넣지 않는다.
- 일곱 항목이 다 없으면 장부에 남기지 않고 PR 인자도 만들지 않는다.
- 같은 대화 ID는 PR 하나다. 장부는 `~/.cursor/kale-inbox-sent.json`이다.
- 브랜치 이름은 `inbox/YYYY-MM-DD-<대화 ID 앞 8자>`다. 파일은 `02-Areas/Bot-Operations/inbox/YYYY-MM-DD-<프로젝트 슬러그>-<대화 ID 앞 8자>.md` 하나다.
- 노트 앞머리는 `title`, `date`, `tags`다. 태그는 `inbox`와 유형이다. 본문은 일곱 항목만 적는다.
- PR 제목은 `inbox: <프로젝트> <날짜>`다. 본문 첫 줄은 `베지가 확인하고 케일에게 넘긴다. 케일이 머지한 뒤 이 파일을 PARA 위치로 옮긴다.`이다.
- 설정 파일은 `~/.cursor/kale-inbox.json`이다. 항목은 `repo`, `reviewer`, `base`다. `repo` 기본값은 `ypspy/my-obsidian-vault`, `base` 기본값은 `main`이다. `reviewer` 기본값은 없다.
- `reviewer`가 비어 있거나, `gh` 로그인이 없거나, 저장소에 PR을 열 권한이 없거나, 푸시가 거절되면 PR을 열지 않고 `~/.cursor/kale-inbox.log`에 한 줄 남긴다. 채팅의 요약은 그대로다.
- 원격에 같은 브랜치의 PR이 이미 열려 있으면 그 주소를 장부에 적고 끝낸다. `git push --force`와 `--force-with-lease`는 쓰지 않는다.
- 케일 리포 `main`에는 커밋하거나 push하지 않는다. 베지의 머지와 PARA 이동은 만들지 않는다.
- `C:\dev\obsidian-vault`와 `C:\dev\obsidian-valut`는 읽기만 한다. clone은 `%TEMP%\kale-inbox-*`에 만들고 끝나면 지운다.
- 품질관리감리 본문, F004 수집, 사이트 배포, `mkdocs.yml`은 바꾸지 않는다.
- 이 계획 문서를 저장할 때 고친 스펙 상태 줄과 `docs/superpowers/README.md` 색인은 구현 태스크에서 다시 고치지 않는다.
- 구현 파일은 git commit 하지 않는다. `~/.cursor`는 이 저장소가 아니다.

---

## File map

| File | Action |
|------|--------|
| `~/.cursor/hooks/kale_inbox.py` | Create — 파싱, 노트·PR 인자, 장부 판단, inbox 브랜치 명령, `stop` 진입점 |
| `~/.cursor/hooks/test_kale_inbox.py` | Create — `gh`와 `git`을 호출하지 않는 pytest |
| `~/.cursor/hooks.json` | Create or modify — 기존 훅은 유지하고 `stop` 항목만 추가 |
| `~/.cursor/kale-inbox.json` | Create only when absent — `reviewer`는 빈 문자열 |
| `~/.cursor/kale-inbox-sent.json` | Runtime ledger |
| `~/.cursor/kale-inbox.log` | Runtime log |

이 저장소의 `.cursor/hooks.json`은 만들지 않는다.

---

### Task 1: 일곱 항목 파서

**Files:**

- Create: `C:\Users\yoont\.cursor\hooks\kale_inbox.py`
- Create: `C:\Users\yoont\.cursor\hooks\test_kale_inbox.py`

**Interfaces:**

- Consumes: 없음
- Produces:
  - `LABELS: list[str]` — `유형`, `프로젝트`, `날짜`, `요약`, `근거`, `다음 액션`, `미결`
  - `TYPES: frozenset[str]` — `결정`, `결과`, `현황`, `이슈`
  - `HANDOFF: str` — `베지가 확인하고 케일에게 넘긴다. 케일이 머지한 뒤 이 파일을 PARA 위치로 옮긴다.`
  - `DEFAULT_REPO: str` — `ypspy/my-obsidian-vault`
  - `DEFAULT_BASE: str` — `main`
  - `HOOK_COMMAND: str` — `python ./hooks/kale_inbox.py`
  - `parse_summary(text: str) -> dict | None` — 키는 `LABELS`와 같다. 근거 라벨 `근거·링크`는 키 `근거`로 넣는다. 코드 펜스 안은 보지 않는다. 유효한 블록이 여러 개면 마지막 블록이다.

- [ ] **Step 1: Write the failing test**

`C:\Users\yoont\.cursor\hooks\test_kale_inbox.py`:

````python
from kale_inbox import parse_summary

SAMPLE = """앞말은 노트에 넣지 않는다.

유형: 결정
프로젝트: quality-updates
날짜: 2026-11-02
요약: 요약을 PR로 넘긴다.
근거: docs/superpowers/specs/2026-11-02-cursor-summary-pr-design.md
다음 액션: 구현 계획
미결: 베지 로그인
"""

SAMPLE_BULLET = """Mr. Kale 전달용

- 유형: 결과
- 프로젝트: quality-updates
- 날짜: 2026-11-02
- 요약: 첫 줄
  둘째 줄
- 근거·링크: https://example.com/pr/1
- 다음 액션: 커밋은 요청 전이라 하지 않음
- 미결: 없음
"""

FENCED = """```
유형: 결정
프로젝트: quality-updates
날짜: 2026-11-02
요약: 펜스 안
근거: 펜스
다음 액션: 없음
미결: 없음
```
"""


def test_parse_plain_block():
    got = parse_summary(SAMPLE)
    assert got["유형"] == "결정"
    assert got["프로젝트"] == "quality-updates"
    assert got["날짜"] == "2026-11-02"
    assert got["요약"] == "요약을 PR로 넘긴다."
    assert got["근거"].endswith("cursor-summary-pr-design.md")
    assert got["다음 액션"] == "구현 계획"
    assert got["미결"] == "베지 로그인"


def test_parse_bullet_and_link_label():
    got = parse_summary(SAMPLE_BULLET)
    assert got["유형"] == "결과"
    assert got["요약"] == "첫 줄\n둘째 줄"
    assert got["근거"] == "https://example.com/pr/1"


def test_parse_ignores_fenced_block():
    assert parse_summary(FENCED) is None
    got = parse_summary(FENCED + "\n" + SAMPLE)
    assert got["요약"] == "요약을 PR로 넘긴다."


def test_parse_rejects_missing_field_bad_type_and_bad_date():
    assert parse_summary(SAMPLE.replace("미결: 베지 로그인\n", "")) is None
    assert parse_summary(SAMPLE.replace("유형: 결정", "유형: 메모")) is None
    assert parse_summary(SAMPLE.replace("2026-11-02", "2026-02-31")) is None


def test_parse_uses_the_last_complete_block():
    earlier = SAMPLE.replace("프로젝트: quality-updates", "프로젝트: old-project")
    got = parse_summary(earlier + "\n" + SAMPLE)
    assert got["프로젝트"] == "quality-updates"
````

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest C:\Users\yoont\.cursor\hooks\test_kale_inbox.py::test_parse_plain_block -v`

Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Write minimal implementation**

`C:\Users\yoont\.cursor\hooks\kale_inbox.py`:

```python
import re
from datetime import date

LABELS = ["유형", "프로젝트", "날짜", "요약", "근거", "다음 액션", "미결"]
TYPES = frozenset({"결정", "결과", "현황", "이슈"})
HANDOFF = "베지가 확인하고 케일에게 넘긴다. 케일이 머지한 뒤 이 파일을 PARA 위치로 옮긴다."
DEFAULT_REPO = "ypspy/my-obsidian-vault"
DEFAULT_BASE = "main"
HOOK_COMMAND = "python ./hooks/kale_inbox.py"

FIELD_RE = re.compile(
    r"^(?:[-*]\s+)?(?:\*\*)?"
    r"(유형|프로젝트|날짜|요약|근거(?:·링크)?|다음 액션|미결)"
    r"(?:\*\*)?\s*:\s*(.*)$"
)
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)


def strip_fences(text: str) -> str:
    return FENCE_RE.sub("", text)


def _match(line: str):
    return FIELD_RE.match(line.strip())


def _label(line: str) -> str | None:
    match = _match(line)
    if match is None:
        return None
    label = match.group(1)
    if label.startswith("근거"):
        return "근거"
    return label


def _value(line: str) -> str:
    return _match(line).group(2).strip()


def _valid(fields: dict) -> bool:
    if fields.get("유형") not in TYPES:
        return False
    day = fields.get("날짜", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return False
    try:
        date.fromisoformat(day)
    except ValueError:
        return False
    return all(str(fields.get(label, "")).strip() for label in LABELS)


def parse_summary(text: str) -> dict | None:
    lines = strip_fences(text).splitlines()
    found = []
    i = 0
    while i < len(lines):
        if _label(lines[i]) != "유형":
            i += 1
            continue
        start = i
        fields = {}
        ok = True
        for expected in LABELS:
            if i >= len(lines) or _label(lines[i]) != expected:
                ok = False
                break
            value = _value(lines[i])
            i += 1
            while i < len(lines) and lines[i].strip() and _label(lines[i]) is None:
                value = f"{value}\n{lines[i].strip()}".strip()
                i += 1
            fields[expected] = value
        if ok and _valid(fields):
            found.append(fields)
        if i == start:
            i += 1
    if not found:
        return None
    return found[-1]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest C:\Users\yoont\.cursor\hooks\test_kale_inbox.py -v`

Expected: PASS, 5 tests.

---

### Task 2: 슬러그, 노트, PR 제목과 본문

**Files:**

- Modify: `C:\Users\yoont\.cursor\hooks\kale_inbox.py`
- Modify: `C:\Users\yoont\.cursor\hooks\test_kale_inbox.py`

**Interfaces:**

- Consumes: `parse_summary`, `LABELS`, `HANDOFF`
- Produces:
  - `one_line(value: str) -> str`
  - `slugify(project: str) -> str`
  - `short_id(conversation_id: str) -> str` — 앞 8자. `[A-Za-z0-9_-]+`가 아니면 `ValueError`
  - `branch_name(summary: dict, conversation_id: str) -> str`
  - `note_path(summary: dict, conversation_id: str) -> str`
  - `note_markdown(summary: dict) -> str`
  - `pr_title(summary: dict) -> str`
  - `pr_body(summary: dict) -> str`

- [ ] **Step 1: Write the failing test**

Append to `test_kale_inbox.py`:

```python
import pytest

from kale_inbox import (
    HANDOFF,
    branch_name,
    note_markdown,
    note_path,
    pr_body,
    pr_title,
    short_id,
    slugify,
)

CID = "22eda128-0391-42aa-9213-00d4b5c7cfac"


def test_slug_and_paths():
    summary = parse_summary(SAMPLE)
    assert slugify("quality/updates:a") == "quality-updates-a"
    assert slugify("품질 관리") == "품질-관리"
    assert slugify("???") == "untitled"
    assert short_id(CID) == "22eda128"
    with pytest.raises(ValueError):
        short_id("../secret")
    assert branch_name(summary, CID) == "inbox/2026-11-02-22eda128"
    assert note_path(summary, CID) == (
        "02-Areas/Bot-Operations/inbox/2026-11-02-quality-updates-22eda128.md"
    )


def test_note_and_pr_text_keep_only_seven_fields():
    summary = parse_summary(SAMPLE)
    note = note_markdown(summary)
    body = pr_body(summary)
    assert note.startswith("---\n")
    assert 'title: "quality-updates 2026-11-02"' in note
    assert "date: 2026-11-02\n" in note
    assert 'tags: [inbox, "결정"]' in note
    assert "앞말은 노트에 넣지 않는다." not in note
    assert "```" not in note
    for label in ["유형", "프로젝트", "날짜", "요약", "근거", "다음 액션", "미결"]:
        assert f"{label}:" in note.split("---", 2)[2]
    assert pr_title(summary) == "inbox: quality-updates 2026-11-02"
    assert body.splitlines()[0] == HANDOFF
    assert "앞말은 노트에 넣지 않는다." not in body
    linked = parse_summary(SAMPLE_BULLET)
    assert "근거: https://example.com/pr/1" in note_markdown(linked)
    assert "근거·링크:" not in note_markdown(linked)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest C:\Users\yoont\.cursor\hooks\test_kale_inbox.py::test_slug_and_paths -v`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Append to `kale_inbox.py`:

```python
def one_line(value: str) -> str:
    return " ".join(str(value).split())


def slugify(project: str) -> str:
    chars = []
    for ch in one_line(project):
        if ch.isalnum() or ch in "_-":
            chars.append(ch)
        else:
            chars.append("-")
    slug = re.sub(r"-{2,}", "-", "".join(chars)).strip("-")
    return slug or "untitled"


def short_id(conversation_id: str) -> str:
    head = conversation_id[:8]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", head or ""):
        raise ValueError("conversation id")
    return head


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def branch_name(summary: dict, conversation_id: str) -> str:
    return f"inbox/{summary['날짜']}-{short_id(conversation_id)}"


def note_path(summary: dict, conversation_id: str) -> str:
    slug = slugify(summary["프로젝트"])
    return (
        "02-Areas/Bot-Operations/inbox/"
        f"{summary['날짜']}-{slug}-{short_id(conversation_id)}.md"
    )


def note_markdown(summary: dict) -> str:
    title = yaml_quote(f"{one_line(summary['프로젝트'])} {summary['날짜']}")
    kind = yaml_quote(summary["유형"])
    body = "\n".join(f"{label}: {summary[label]}" for label in LABELS)
    return (
        "---\n"
        f"title: {title}\n"
        f"date: {summary['날짜']}\n"
        f"tags: [inbox, {kind}]\n"
        "---\n"
        "\n"
        f"{body}\n"
    )


def pr_title(summary: dict) -> str:
    return f"inbox: {one_line(summary['프로젝트'])} {summary['날짜']}"


def pr_body(summary: dict) -> str:
    fields = "\n".join(f"{label}: {summary[label]}" for label in LABELS)
    return HANDOFF + "\n\n" + fields + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest C:\Users\yoont\.cursor\hooks\test_kale_inbox.py -v`

Expected: PASS.

---

### Task 3: 장부, 설정, PR 인자 판단

**Files:**

- Modify: `C:\Users\yoont\.cursor\hooks\kale_inbox.py`
- Modify: `C:\Users\yoont\.cursor\hooks\test_kale_inbox.py`

**Interfaces:**

- Consumes: `parse_summary`, `branch_name`, `note_path`, `note_markdown`, `pr_title`, `pr_body`, `short_id`, `DEFAULT_REPO`, `DEFAULT_BASE`, `HANDOFF`
- Produces:
  - `load_config(data: dict | None) -> dict` — 키 `repo`, `reviewer`, `base`
  - `ledger_has(ledger: dict, conversation_id: str) -> bool`
  - `ledger_put(ledger: dict, conversation_id: str, pr_url: str) -> dict` — `{"conversations": {id: {"pr": url}}}`
  - `build_args(summary: dict, conversation_id: str, config: dict) -> dict` — 키 `repo`, `base`, `branch`, `title`, `body`, `reviewer`, `path`, `content`, `commit_message`
  - `Decision` — `.action`은 `open`, `skip`, `ignore`, `log`. `.args`, `.log`
  - `decide(text: str, conversation_id: str, ledger: dict, config: dict) -> Decision`

- [ ] **Step 1: Write the failing test**

Append to `test_kale_inbox.py`:

```python
from kale_inbox import build_args, decide, load_config

CONFIG = {
    "repo": "ypspy/my-obsidian-vault",
    "reviewer": "veggie-login",
    "base": "main",
}
EMPTY_LEDGER = {"conversations": {}}


def test_load_config_defaults():
    assert load_config(None) == {
        "repo": "ypspy/my-obsidian-vault",
        "reviewer": "",
        "base": "main",
    }
    assert load_config({"reviewer": "veggie-login"})["repo"] == "ypspy/my-obsidian-vault"
    assert load_config({"reviewer": "veggie-login"})["base"] == "main"


def test_complete_summary_becomes_pr_args_without_preamble():
    decision = decide(SAMPLE, CID, EMPTY_LEDGER, CONFIG)
    assert decision.action == "open"
    args = decision.args
    assert args["repo"] == "ypspy/my-obsidian-vault"
    assert args["base"] == "main"
    assert args["reviewer"] == "veggie-login"
    assert args["branch"] == "inbox/2026-11-02-22eda128"
    assert args["title"] == "inbox: quality-updates 2026-11-02"
    assert args["commit_message"] == args["title"]
    assert args["body"].splitlines()[0] == HANDOFF
    assert args["path"].endswith("2026-11-02-quality-updates-22eda128.md")
    assert "앞말은 노트에 넣지 않는다." not in args["content"]
    assert "앞말은 노트에 넣지 않는다." not in args["body"]
    assert "```" not in args["content"]


def test_missing_field_does_not_build_args_or_touch_ledger():
    ledger = {"conversations": {}}
    decision = decide(SAMPLE.replace("미결: 베지 로그인\n", ""), CID, ledger, CONFIG)
    assert decision.action == "ignore"
    assert decision.args is None
    assert ledger == {"conversations": {}}


def test_same_conversation_skips():
    ledger = {"conversations": {CID: {"pr": "https://github.com/ypspy/my-obsidian-vault/pull/3"}}}
    decision = decide(SAMPLE, CID, ledger, CONFIG)
    assert decision.action == "skip"
    assert decision.args is None


def test_empty_reviewer_logs_and_builds_no_args():
    config = {"repo": "ypspy/my-obsidian-vault", "reviewer": "", "base": "main"}
    decision = decide(SAMPLE, CID, EMPTY_LEDGER, config)
    assert decision.action == "log"
    assert decision.log == "reviewer empty"
    assert decision.args is None


def test_bad_conversation_id_logs():
    decision = decide(SAMPLE, "../secret-id", EMPTY_LEDGER, CONFIG)
    assert decision.action == "log"
    assert decision.log == "conversation id"
    assert decision.args is None
```

`build_args`는 `test_complete_summary_becomes_pr_args_without_preamble`가 `decide`를 통해 검사한다. import는 이후 태스크가 같은 이름에 의존하므로 테스트 파일 위에 남겨 둔다.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest C:\Users\yoont\.cursor\hooks\test_kale_inbox.py::test_complete_summary_becomes_pr_args_without_preamble -v`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Append to `kale_inbox.py`:

```python
class Decision:
    def __init__(self, action: str, args: dict | None = None, log: str | None = None):
        self.action = action
        self.args = args
        self.log = log


def load_config(data: dict | None) -> dict:
    data = data or {}
    repo = str(data.get("repo") or "").strip() or DEFAULT_REPO
    base = str(data.get("base") or "").strip() or DEFAULT_BASE
    reviewer = str(data.get("reviewer") or "").strip()
    return {"repo": repo, "reviewer": reviewer, "base": base}


def ledger_has(ledger: dict, conversation_id: str) -> bool:
    return conversation_id in (ledger.get("conversations") or {})


def ledger_put(ledger: dict, conversation_id: str, pr_url: str) -> dict:
    conversations = dict(ledger.get("conversations") or {})
    conversations[conversation_id] = {"pr": pr_url}
    return {"conversations": conversations}


def build_args(summary: dict, conversation_id: str, config: dict) -> dict:
    loaded = load_config(config)
    title = pr_title(summary)
    return {
        "repo": loaded["repo"],
        "base": loaded["base"],
        "branch": branch_name(summary, conversation_id),
        "title": title,
        "body": pr_body(summary),
        "reviewer": loaded["reviewer"],
        "path": note_path(summary, conversation_id),
        "content": note_markdown(summary),
        "commit_message": title,
    }


def decide(text: str, conversation_id: str, ledger: dict, config: dict) -> Decision:
    if ledger_has(ledger, conversation_id):
        return Decision("skip")
    try:
        short_id(conversation_id)
    except ValueError:
        return Decision("log", log="conversation id")
    summary = parse_summary(text)
    if summary is None:
        return Decision("ignore")
    if not load_config(config)["reviewer"]:
        return Decision("log", log="reviewer empty")
    return Decision("open", args=build_args(summary, conversation_id, config))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest C:\Users\yoont\.cursor\hooks\test_kale_inbox.py -v`

Expected: PASS.

---

### Task 4: inbox 브랜치 명령

**Files:**

- Modify: `C:\Users\yoont\.cursor\hooks\kale_inbox.py`
- Modify: `C:\Users\yoont\.cursor\hooks\test_kale_inbox.py`

**Interfaces:**

- Consumes: `build_args`의 키 `repo`, `base`, `branch`, `title`, `body`, `reviewer`, `path`, `commit_message`
- Produces:
  - `commands_for(args: dict, workdir: str) -> list[list[str]]`
  - `list_pr_command(args: dict) -> list[str]`
  - `parse_pr_list(stdout: str) -> str | None`
  - `classify_failure(cmd: list[str], blob: str) -> str` — `gh auth`, `permission`, `push rejected`, `gh failed`
  - `assert_workdir(workdir: str) -> None`

- [ ] **Step 1: Write the failing test**

Append to `test_kale_inbox.py`:

```python
from kale_inbox import (
    assert_workdir,
    classify_failure,
    commands_for,
    list_pr_command,
    parse_pr_list,
)


def test_commands_push_only_inbox_branch():
    summary = parse_summary(SAMPLE)
    args = build_args(summary, CID, CONFIG)
    workdir = r"C:\Users\yoont\AppData\Local\Temp\kale-inbox-test"
    cmds = commands_for(args, workdir)
    assert cmds[0][:4] == ["git", "clone", "--depth", "1"]
    assert cmds[0][4:6] == ["--branch", "main"]
    assert cmds[1] == ["git", "-C", workdir, "checkout", "-b", "inbox/2026-11-02-22eda128"]
    assert cmds[2] == [
        "git", "-C", workdir, "add", "--",
        "02-Areas/Bot-Operations/inbox/2026-11-02-quality-updates-22eda128.md",
    ]
    assert cmds[3][:4] == ["git", "-C", workdir, "commit"]
    assert cmds[4] == [
        "git", "-C", workdir, "push", "-u", "origin",
        "HEAD:refs/heads/inbox/2026-11-02-22eda128",
    ]
    assert cmds[5][:3] == ["gh", "pr", "create"]
    assert "--reviewer" in cmds[5]
    assert cmds[5][cmds[5].index("--reviewer") + 1] == "veggie-login"
    assert cmds[5][cmds[5].index("--base") + 1] == "main"
    for cmd in cmds:
        assert "--force" not in cmd
        assert "--force-with-lease" not in cmd
        assert "refs/heads/main" not in " ".join(cmd)
        if "push" in cmd:
            assert cmd[-1] == "HEAD:refs/heads/inbox/2026-11-02-22eda128"
    assert list_pr_command(args) == [
        "gh", "pr", "list",
        "--repo", "ypspy/my-obsidian-vault",
        "--head", "inbox/2026-11-02-22eda128",
        "--base", "main",
        "--state", "open",
        "--json", "url",
    ]
    assert parse_pr_list('[{"url":"https://github.com/ypspy/my-obsidian-vault/pull/9"}]') == (
        "https://github.com/ypspy/my-obsidian-vault/pull/9"
    )
    assert parse_pr_list("[]") is None
    assert classify_failure(["git", "push"], "permission denied") == "permission"
    assert classify_failure(["gh", "auth", "status"], "not logged in") == "gh auth"
    assert classify_failure(["git", "-C", workdir, "push"], "rejected") == "push rejected"


def test_workdir_rejects_vault():
    with pytest.raises(RuntimeError):
        assert_workdir(r"C:\dev\obsidian-valut\02-Areas")
    with pytest.raises(RuntimeError):
        assert_workdir(r"C:\dev\obsidian-vault")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest C:\Users\yoont\.cursor\hooks\test_kale_inbox.py::test_commands_push_only_inbox_branch -v`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Append to `kale_inbox.py`:

```python
from pathlib import Path


def assert_workdir(workdir: str) -> None:
    path = Path(workdir).resolve()
    banned = [
        Path(r"C:\dev\obsidian-vault").resolve(),
        Path(r"C:\dev\obsidian-valut").resolve(),
    ]
    for root in banned:
        if path == root or root in path.parents:
            raise RuntimeError("vault is read-only")


def commands_for(args: dict, workdir: str) -> list[list[str]]:
    remote = f"https://github.com/{args['repo']}.git"
    refspec = f"HEAD:refs/heads/{args['branch']}"
    return [
        ["git", "clone", "--depth", "1", "--branch", args["base"], remote, workdir],
        ["git", "-C", workdir, "checkout", "-b", args["branch"]],
        ["git", "-C", workdir, "add", "--", args["path"]],
        ["git", "-C", workdir, "commit", "-m", args["commit_message"]],
        ["git", "-C", workdir, "push", "-u", "origin", refspec],
        [
            "gh", "pr", "create",
            "--repo", args["repo"],
            "--base", args["base"],
            "--head", args["branch"],
            "--title", args["title"],
            "--body", args["body"],
            "--reviewer", args["reviewer"],
        ],
    ]


def list_pr_command(args: dict) -> list[str]:
    return [
        "gh", "pr", "list",
        "--repo", args["repo"],
        "--head", args["branch"],
        "--base", args["base"],
        "--state", "open",
        "--json", "url",
    ]


def parse_pr_list(stdout: str) -> str | None:
    try:
        rows = json.loads(stdout or "[]")
    except json.JSONDecodeError:
        return None
    if not rows:
        return None
    return rows[0].get("url") or None


def classify_failure(cmd: list[str], blob: str) -> str:
    low = blob.lower()
    if (
        "resource not accessible" in low
        or "403" in low
        or "permission" in low
        or "must have push access" in low
    ):
        return "permission"
    if (
        "authentication" in low
        or "gh auth login" in low
        or "401" in low
        or "not logged in" in low
    ):
        return "gh auth"
    if "push" in cmd:
        return "push rejected"
    return "gh failed"
```

`import json`은 파일 맨 위의 import 블록에 넣는다. `pathlib.Path` import도 맨 위로 올린다.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest C:\Users\yoont\.cursor\hooks\test_kale_inbox.py -v`

Expected: PASS.

---

### Task 5: stop 훅

**Files:**

- Modify: `C:\Users\yoont\.cursor\hooks\kale_inbox.py`
- Modify: `C:\Users\yoont\.cursor\hooks\test_kale_inbox.py`
- Create or modify: `C:\Users\yoont\.cursor\hooks.json`
- Create when absent: `C:\Users\yoont\.cursor\kale-inbox.json`

**Interfaces:**

- Consumes: `decide`, `ledger_put`, `load_config`, `commands_for`, `list_pr_command`, `parse_pr_list`, `classify_failure`, `assert_workdir`, `HOOK_COMMAND`, `DEFAULT_REPO`, `DEFAULT_BASE`
- Produces:
  - `last_assistant_text(raw: str) -> str` — JSONL에서 마지막 `role == "assistant"`의 `type == "text"`만 잇는다. `tool_use`는 버린다.
  - `HandleResult` — `.stdout`은 `{}`, `.ledger`, `.log`
  - `handle(payload: dict, *, text: str, ledger: dict, config: dict, run) -> HandleResult`
  - `execute(args: dict, run=None) -> Outcome` — `.pr_url`, `.log`. `run` 기본값은 `subprocess.run`. `shell=True`는 쓰지 않는다.
  - `merge_hooks(existing: dict | None) -> dict`
  - `install_hook(path: Path) -> None`
  - `main(stdin: str, *, config_path, ledger_path, log_path, read_transcript, run) -> int`

`stop` 입력에서 읽는 필드는 `status`, `conversation_id`, `transcript_path`다. 응답 본문은 stdin에 없으므로 `transcript_path`의 기록을 읽는다. `status`가 `completed`가 아니면 장부도 로그도 만들지 않는다.

- [ ] **Step 1: Write the failing test**

Append to `test_kale_inbox.py`:

```python
import json
from pathlib import Path

from kale_inbox import execute, handle, last_assistant_text, main, merge_hooks


class Done:
    def __init__(self, code, out="", err=""):
        self.returncode = code
        self.stdout = out
        self.stderr = err


def test_last_assistant_text_skips_tool_use_and_user():
    user = {
        "role": "user",
        "message": {"content": [{"type": "text", "text": "유형: 결정"}]},
    }
    assistant = {
        "role": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "name": "Shell", "input": {"command": "echo hi"}},
                {"type": "text", "text": SAMPLE},
            ]
        },
    }
    raw = json.dumps(user) + "\n" + json.dumps(assistant) + "\n"
    assert last_assistant_text(raw) == SAMPLE


def test_handle_open_records_ledger_and_second_call_does_not_run():
    payload = {"status": "completed", "conversation_id": CID, "loop_count": 0}

    def run_once(args):
        class Outcome:
            pr_url = "https://github.com/ypspy/my-obsidian-vault/pull/4"
            log = None
        return Outcome()

    first = handle(payload, text=SAMPLE, ledger=EMPTY_LEDGER, config=CONFIG, run=run_once)
    assert first.stdout == {}
    assert first.ledger["conversations"][CID]["pr"].endswith("/pull/4")

    def run_again(args):
        raise AssertionError("second run")

    second = handle(payload, text=SAMPLE, ledger=first.ledger, config=CONFIG, run=run_again)
    assert second.log is None
    assert second.ledger == first.ledger


def test_handle_missing_field_and_aborted_leave_ledger():
    payload = {"status": "completed", "conversation_id": CID}
    missing = handle(
        payload,
        text=SAMPLE.replace("미결: 베지 로그인\n", ""),
        ledger=EMPTY_LEDGER,
        config=CONFIG,
        run=lambda args: (_ for _ in ()).throw(AssertionError("run")),
    )
    assert missing.log is None
    assert missing.ledger == EMPTY_LEDGER
    aborted = handle(
        {"status": "aborted", "conversation_id": CID},
        text=SAMPLE,
        ledger=EMPTY_LEDGER,
        config=CONFIG,
        run=lambda args: (_ for _ in ()).throw(AssertionError("run")),
    )
    assert aborted.log is None


def test_auth_and_permission_failures_do_not_push():
    summary = parse_summary(SAMPLE)
    args = build_args(summary, CID, CONFIG)

    def no_auth(cmd, **kwargs):
        if cmd[:3] == ["gh", "auth", "status"]:
            return Done(1, err="not logged in")
        raise AssertionError(cmd)

    assert execute(args, run=no_auth).log == "gh auth"

    def no_permission(cmd, **kwargs):
        if cmd[:3] == ["gh", "auth", "status"]:
            return Done(0)
        if cmd[:3] == ["gh", "pr", "list"]:
            return Done(0, "[]")
        if cmd[0] == "git" and "clone" in cmd:
            return Done(1, err="403 Resource not accessible")
        raise AssertionError(cmd)

    assert execute(args, run=no_permission).log == "permission"


def test_existing_pr_does_not_push():
    summary = parse_summary(SAMPLE)
    args = build_args(summary, CID, CONFIG)
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:3] == ["gh", "auth", "status"]:
            return Done(0)
        if cmd[:3] == ["gh", "pr", "list"]:
            return Done(0, '[{"url":"https://github.com/ypspy/my-obsidian-vault/pull/9"}]')
        raise AssertionError(cmd)

    outcome = execute(args, run=run)
    assert outcome.pr_url == "https://github.com/ypspy/my-obsidian-vault/pull/9"
    assert all(cmd[0] != "git" for cmd in calls)


def test_push_rejection_without_pr_logs_and_does_not_force(tmp_path):
    summary = parse_summary(SAMPLE)
    args = build_args(summary, CID, CONFIG)

    def run(cmd, **kwargs):
        if cmd[:3] == ["gh", "auth", "status"]:
            return Done(0)
        if cmd[:3] == ["gh", "pr", "list"]:
            return Done(0, "[]")
        if cmd[0] == "git" and "push" in cmd:
            assert "--force" not in cmd
            return Done(1, err="rejected")
        if cmd[0] == "git":
            return Done(0)
        raise AssertionError(cmd)

    outcome = execute(args, run=run)
    assert outcome.pr_url is None
    assert outcome.log == "push rejected"


def test_main_prints_object_and_empty_reviewer_logs(tmp_path, capsys):
    transcript = tmp_path / "t.jsonl"
    line = {"role": "assistant", "message": {"content": [{"type": "text", "text": SAMPLE}]}}
    transcript.write_text(json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8")
    config_path = tmp_path / "kale-inbox.json"
    config_path.write_text(
        json.dumps({"repo": "ypspy/my-obsidian-vault", "reviewer": "", "base": "main"}),
        encoding="utf-8",
    )
    payload = {
        "status": "completed",
        "conversation_id": CID,
        "transcript_path": str(transcript),
        "loop_count": 0,
    }
    code = main(
        json.dumps(payload),
        config_path=config_path,
        ledger_path=tmp_path / "kale-inbox-sent.json",
        log_path=tmp_path / "kale-inbox.log",
        read_transcript=lambda p: Path(p).read_text(encoding="utf-8"),
        run=lambda args: (_ for _ in ()).throw(AssertionError("run")),
    )
    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out) == {}
    assert "followup_message" not in captured.out
    assert "reviewer empty" in (tmp_path / "kale-inbox.log").read_text(encoding="utf-8")
    assert not (tmp_path / "kale-inbox-sent.json").exists()


def test_bad_stdin_still_prints_object(tmp_path, capsys):
    code = main(
        "{",
        config_path=tmp_path / "c.json",
        ledger_path=tmp_path / "l.json",
        log_path=tmp_path / "k.log",
        read_transcript=lambda p: "",
        run=lambda args: None,
    )
    assert code == 0
    assert capsys.readouterr().out.strip() == "{}"
    assert "hook error:" in (tmp_path / "k.log").read_text(encoding="utf-8")


def test_merge_hooks_keeps_other_events_and_does_not_duplicate():
    merged = merge_hooks(
        {"version": 1, "hooks": {"sessionStart": [{"command": "./session-init.sh"}]}}
    )
    assert merged["hooks"]["sessionStart"] == [{"command": "./session-init.sh"}]
    stop = merged["hooks"]["stop"][0]
    assert stop["command"] == "python ./hooks/kale_inbox.py"
    assert stop["timeout"] == 180
    assert stop["loop_limit"] == 0
    assert "failClosed" not in stop
    again = merge_hooks(merged)
    assert len(again["hooks"]["stop"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest C:\Users\yoont\.cursor\hooks\test_kale_inbox.py::test_last_assistant_text_skips_tool_use_and_user -v`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Append to `kale_inbox.py`. 파일 맨 위 import에 `json`, `shutil`, `subprocess`, `sys`, `tempfile`, `datetime`을 추가한다.

```python
CONFIG_PATH = Path.home() / ".cursor" / "kale-inbox.json"
LEDGER_PATH = Path.home() / ".cursor" / "kale-inbox-sent.json"
LOG_PATH = Path.home() / ".cursor" / "kale-inbox.log"


def last_assistant_text(raw: str) -> str:
    texts = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("role") != "assistant":
            continue
        content = (obj.get("message") or {}).get("content")
        if isinstance(content, str):
            texts.append(content)
            continue
        if not isinstance(content, list):
            continue
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text") or "")
        if parts:
            texts.append("\n".join(parts))
    if not texts:
        return ""
    return texts[-1]


class HandleResult:
    def __init__(self, ledger: dict, log: str | None):
        self.stdout = {}
        self.ledger = ledger
        self.log = log


def handle(payload: dict, *, text: str, ledger: dict, config: dict, run) -> HandleResult:
    if payload.get("status") != "completed":
        return HandleResult(ledger, None)
    conversation_id = str(payload.get("conversation_id") or "").strip()
    if not conversation_id:
        return HandleResult(ledger, "conversation_id missing")
    decision = decide(text, conversation_id, ledger, config)
    if decision.action == "open":
        outcome = run(decision.args)
        if outcome.pr_url:
            return HandleResult(ledger_put(ledger, conversation_id, outcome.pr_url), None)
        return HandleResult(ledger, outcome.log)
    if decision.action == "log":
        return HandleResult(ledger, decision.log)
    return HandleResult(ledger, None)


class Outcome:
    def __init__(self, pr_url: str | None = None, log: str | None = None):
        self.pr_url = pr_url
        self.log = log


def execute(args: dict, run=None) -> Outcome:
    if run is None:
        run = subprocess.run
    auth = run(["gh", "auth", "status"], capture_output=True, text=True)
    if auth.returncode != 0:
        return Outcome(log="gh auth")
    listed = run(list_pr_command(args), capture_output=True, text=True)
    blob = (listed.stderr or "") + (listed.stdout or "")
    if listed.returncode != 0:
        return Outcome(log=classify_failure(list_pr_command(args), blob))
    existing = parse_pr_list(listed.stdout)
    if existing:
        return Outcome(pr_url=existing)
    workdir = tempfile.mkdtemp(prefix="kale-inbox-")
    try:
        assert_workdir(workdir)
        for cmd in commands_for(args, workdir):
            if cmd[0] == "git" and "add" in cmd:
                note = Path(workdir) / args["path"]
                note.parent.mkdir(parents=True, exist_ok=True)
                note.write_text(args["content"], encoding="utf-8", newline="\n")
            completed = run(cmd, capture_output=True, text=True)
            if completed.returncode != 0:
                err = (completed.stderr or "") + (completed.stdout or "")
                if "push" in cmd:
                    again = run(list_pr_command(args), capture_output=True, text=True)
                    url = parse_pr_list(again.stdout) if again.returncode == 0 else None
                    if url:
                        return Outcome(pr_url=url)
                return Outcome(log=classify_failure(cmd, err))
            if cmd[0] == "gh" and "create" in cmd:
                lines = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
                if not lines:
                    return Outcome(log="gh failed")
                return Outcome(pr_url=lines[-1])
        return Outcome(log="gh failed")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def merge_hooks(existing: dict | None) -> dict:
    data = existing or {"version": 1, "hooks": {}}
    data["version"] = 1
    hooks = data.setdefault("hooks", {})
    stop = hooks.setdefault("stop", [])
    entry = {"command": HOOK_COMMAND, "timeout": 180, "loop_limit": 0}
    if not any(isinstance(item, dict) and item.get("command") == HOOK_COMMAND for item in stop):
        stop.append(entry)
    return data


def install_hook(path: Path) -> None:
    current = None
    if path.is_file():
        current = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(
        json.dumps(merge_hooks(current), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_ledger(path: Path) -> dict:
    if not path.is_file():
        return {"conversations": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_ledger(path: Path, ledger: dict) -> None:
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_config(path: Path) -> dict:
    if not path.is_file():
        data = {"repo": DEFAULT_REPO, "reviewer": "", "base": DEFAULT_BASE}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return load_config(data)
    return load_config(json.loads(path.read_text(encoding="utf-8")))


def append_log(message: str, path: Path) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {message}\n")


def main(stdin: str, *, config_path, ledger_path, log_path, read_transcript, run) -> int:
    try:
        payload = json.loads(stdin) if stdin.strip() else {}
        if payload.get("status") != "completed":
            sys.stdout.write("{}\n")
            return 0
        transcript_path = payload.get("transcript_path")
        if not transcript_path:
            append_log("transcript missing", log_path)
            sys.stdout.write("{}\n")
            return 0
        try:
            raw = read_transcript(transcript_path)
        except OSError:
            append_log("transcript missing", log_path)
            sys.stdout.write("{}\n")
            return 0
        text = last_assistant_text(raw)
        config = ensure_config(config_path)
        ledger = load_ledger(ledger_path)
        result = handle(payload, text=text, ledger=ledger, config=config, run=run)
        if result.ledger != ledger:
            save_ledger(ledger_path, result.ledger)
        if result.log:
            append_log(result.log, log_path)
    except Exception as exc:
        append_log(f"hook error: {exc}", log_path)
    sys.stdout.write("{}\n")
    return 0


def _entry() -> int:
    return main(
        sys.stdin.read(),
        config_path=CONFIG_PATH,
        ledger_path=LEDGER_PATH,
        log_path=LOG_PATH,
        read_transcript=lambda p: Path(p).read_text(encoding="utf-8"),
        run=execute,
    )


if __name__ == "__main__":
    raise SystemExit(_entry())
```

`datetime` import는 `from datetime import datetime, timezone`다. Task 1의 `from datetime import date`와 한 줄로 합친다. `date.fromisoformat`은 그대로 둔다.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest C:\Users\yoont\.cursor\hooks\test_kale_inbox.py -q`

Expected: PASS. 이 명령은 `git`과 `gh`를 호출하지 않는다.

- [ ] **Step 5: Install the user hook**

Run: `where.exe python`

Expected: `python.exe` 경로가 한 줄 이상 나온다. 없으면 여기서 멈추고, Python을 설치하거나 품질관리 저장소의 가상환경을 훅에 연결하지 않는다.

Run:

```powershell
python -c "import sys; sys.path.insert(0, r'C:\Users\yoont\.cursor\hooks'); import kale_inbox; from pathlib import Path; kale_inbox.install_hook(Path.home() / '.cursor' / 'hooks.json')"
```

Expected: `C:\Users\yoont\.cursor\hooks.json`의 `hooks.stop`에 `python ./hooks/kale_inbox.py`가 하나 있다. `loop_limit`는 0, `timeout`은 180이다. 다른 이벤트 항목은 그대로다.

`C:\Users\yoont\.cursor\kale-inbox.json`이 없으면 다음 내용으로 만든다. 이미 있으면 `reviewer`를 덮어쓰지 않는다.

```json
{
  "repo": "ypspy/my-obsidian-vault",
  "reviewer": "",
  "base": "main"
}
```

실제 `gh pr create`는 실행하지 않는다. `reviewer`에 베지의 GitHub 로그인을 넣는 일은 사용자가 한다. 그 값이 생기기 전에는 훅이 로그 한 줄만 남긴다.

훅이 설치된 뒤 Cursor가 `stop`에서 스크립트를 보이지 않으면, `loop_limit`만 `1`로 바꾸고 표준 출력은 `{}`로 유지한다. `followup_message`는 그때도 넣지 않는다.

---

## 스펙 대조

| 스펙 | 태스크 |
|------|--------|
| 사용자 `stop` 훅, 프로젝트 훅 아님 | Task 5, Global Constraints |
| 실패해도 대화를 막지 않음, 후속 루프 없음 | Task 5 `{}` / `loop_limit` 0 |
| 일곱 항목이 있을 때만 노트와 PR 인자 | Task 1, Task 3 |
| 다른 글·코드 블록·도구 출력 제외 | Task 1, Task 5 `last_assistant_text` |
| 빠진 항목은 장부에 없음 | Task 3 |
| 같은 대화 ID는 한 번 | Task 3, Task 5 |
| 브랜치·파일·슬러그·앞머리·PR 제목·본문 | Task 2 |
| 설정 기본값, 빈 `reviewer` 로그 | Task 3, Task 5 |
| 로그인·권한·푸시 거절 로그, force push 없음 | Task 4, Task 5 |
| 같은 브랜치의 열린 PR은 주소만 장부 | Task 5 `execute` |
| `main` 직접 push, 머지, PARA 이동, 사이트 변경 없음 | Global Constraints, Task 4 |
