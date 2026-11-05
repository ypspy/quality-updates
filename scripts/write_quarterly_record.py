"""Write one processed quarter record. Does not modify the quarter file."""

from __future__ import annotations

import sys
from pathlib import Path

from quarterly_handoff import (
    APPENDIX_RE,
    SKIP_RE,
    SOURCE_RE,
    _items,
    _record_filename,
)


def _matches(items, title: str, date_text: str | None):
    found = [item for item in items if item[3] == title and (date_text is None or item[2] == date_text)]
    return found


def _render(link: str, body: str, facts: list[str]) -> str:
    lines = [link.rstrip(), ""]
    for line in body.splitlines():
        if SOURCE_RE.search(line):
            lines.append(line.rstrip())
    lines.extend(["", "## 확인한 사실", ""])
    lines.extend(f"- {fact}" for fact in facts)
    return "\n".join(lines).rstrip() + "\n"


def _append_facts(text: str, facts: list[str]) -> str | None:
    marker = "## 확인한 사실\n"
    start = text.find(marker)
    if start < 0:
        return None
    body_start = start + len(marker)
    next_heading = text.find("\n## ", body_start)
    section = text[body_start:] if next_heading < 0 else text[body_start:next_heading]
    tail = "" if next_heading < 0 else text[next_heading:]
    existing = {line.strip()[2:] for line in section.splitlines() if line.strip().startswith("- ")}
    added = [fact for fact in facts if fact not in existing]
    if not added:
        return text
    if section and not section.endswith("\n"):
        section += "\n"
    addition = "".join(f"- {fact}\n" for fact in added)
    return text[:body_start] + section + addition + tail


def _append_minutes(text: str, facts: list[str]) -> str | None:
    if "## 위원 논의" in text:
        return None
    body = "".join(f"- {fact}\n" for fact in facts)
    return text.rstrip() + "\n\n## 위원 논의\n\n" + body


def write_record(quarter_text, quarter_stem, title, facts, date_text, mode, repo_root: Path):
    if mode not in {"create", "append-facts", "append-minutes"}:
        return 1, "invalid mode"
    body = APPENDIX_RE.split(quarter_text, maxsplit=1)[0]
    found = _matches(_items(body), title, date_text)
    if len(found) != 1:
        return 1, "not found"
    link, item_body, item_date, item_title = found[0]
    if SKIP_RE.search(item_body):
        return 0, "skipped"
    path = repo_root / "data" / "quarterly-processed" / quarter_stem / _record_filename(item_date, item_title)
    if mode == "create" and path.is_file():
        return 0, f"kept {path}"
    if mode != "create" and not path.is_file():
        return 1, f"missing {path}"
    if not facts:
        return 1, "empty facts"
    if mode == "create":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(link, item_body, facts), encoding="utf-8")
        return 0, f"wrote {path}"
    current = path.read_text(encoding="utf-8")
    if mode == "append-facts":
        updated = _append_facts(current, facts)
        if updated is None:
            return 0, f"kept {path}"
    else:
        updated = _append_minutes(current, facts)
        if updated is None:
            return 0, f"kept {path}"
    if updated == current:
        return 0, f"kept {path}"
    path.write_text(updated, encoding="utf-8")
    return 0, f"wrote {path}"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("quarter")
    parser.add_argument("--title", required=True)
    parser.add_argument("--date")
    parser.add_argument("--append-facts", action="store_true")
    parser.add_argument("--append-minutes", action="store_true")
    args = parser.parse_args(argv)
    if args.append_facts and args.append_minutes:
        return 1
    mode = "append-facts" if args.append_facts else "append-minutes" if args.append_minutes else "create"
    quarter = Path(args.quarter)
    facts = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
    code, message = write_record(
        quarter.read_text(encoding="utf-8"),
        quarter.stem,
        args.title,
        facts,
        args.date,
        mode,
        Path(__file__).resolve().parent.parent,
    )
    print(message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
