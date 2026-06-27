"""Unified regulatory updates crawler — assembles quarterly Markdown for docs/."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from . import FSS, FSC, KASB, KICPA, KICPA_Standards

JURISDICTION = "KR"

START_DATE_STR = "2024-10-01"
END_DATE_STR = "2024-12-31"
START_DATE = datetime.strptime(START_DATE_STR, "%Y-%m-%d")
END_DATE = datetime.strptime(END_DATE_STR, "%Y-%m-%d")
YEAR = START_DATE.year

APPENDIX: dict[str, dict] = {
    "금융감독원": {},
    "금융위원회": {},
    "한국공인회계사회": {},
    "한국회계기준원": {},
}


def repo_root() -> Path:
    """Repository root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent.parent


def configure_period(start_str: str, end_str: str) -> None:
    """Set crawl period globals and sync to agency modules."""
    global START_DATE_STR, END_DATE_STR, START_DATE, END_DATE, YEAR
    START_DATE_STR = start_str
    END_DATE_STR = end_str
    START_DATE = datetime.strptime(start_str, "%Y-%m-%d")
    END_DATE = datetime.strptime(end_str, "%Y-%m-%d")
    YEAR = START_DATE.year
    APPENDIX.clear()
    APPENDIX.update(
        {
            "금융감독원": {},
            "금융위원회": {},
            "한국공인회계사회": {},
            "한국회계기준원": {},
        }
    )
    sync_period_to_modules()


def output_dir() -> Path:
    return repo_root() / "docs" / "quality-updates" / str(START_DATE.year)


def output_file_name() -> str:
    return f"{START_DATE_STR}_to_{END_DATE_STR}.md"


def output_path() -> Path:
    return output_dir() / output_file_name()


def sync_period_to_modules() -> None:
    """Inject period into FSS/FSC module globals."""
    if hasattr(FSS, "START_DATE"):
        FSS.START_DATE = START_DATE_STR
    if hasattr(FSS, "END_DATE"):
        FSS.END_DATE = END_DATE_STR
    if hasattr(FSS, "start_dt"):
        FSS.start_dt = datetime.strptime(START_DATE_STR, "%Y-%m-%d")

    if hasattr(FSC, "START_DATE"):
        FSC.START_DATE = START_DATE_STR
    if hasattr(FSC, "END_DATE"):
        FSC.END_DATE = END_DATE_STR


def ensure_output_dir() -> None:
    output_dir().mkdir(parents=True, exist_ok=True)


def _yy_mm_dd_key(date_str: str) -> tuple[int, int, int]:
    yy, mm, dd = date_str.split("-")
    return (2000 + int(yy), int(mm), int(dd))


def sort_fss_items(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda i: _yy_mm_dd_key(i["date"]))


def sort_kicpa_dict_items(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda i: i["date"])


def sort_dated_tuples(items: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    return sorted(items, key=lambda t: _yy_mm_dd_key(t[0]))


def sort_md_link_lines(items: list[str]) -> list[str]:
    def key(line: str) -> tuple[int, int, int]:
        m = re.match(r"^- \((\d{2})-(\d{2})-(\d{2})\)", line)
        if not m:
            return (9999, 12, 31)
        yy, mm, dd = (int(x) for x in m.groups())
        return (2000 + yy, mm, dd)

    return sorted(items, key=key)


def md_lines(items):
    return "\n".join(f"- ({d}) [{title}]({link})" for d, title, link in items)


def indent_block(text: str, spaces: int = 4) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else "" for line in text.splitlines())


def compute_period_metadata() -> dict[str, str]:
    q = (START_DATE.month - 1) // 3 + 1
    return {"frequency": "quarterly", "period_label": f"{YEAR}-Q{q}"}


def build_front_matter() -> str:
    meta = compute_period_metadata()
    return f"""---
title: {START_DATE_STR} ~ {END_DATE_STR} Regulatory Updates
jurisdiction: {JURISDICTION}
year: {YEAR}
frequency: {meta['frequency']}
period_label: {meta['period_label']}
period:
  start: {START_DATE_STR}
  end: {END_DATE_STR}
category: Quality Updates
agencies:
  - FSS
  - FSC
  - KICPA
  - KASB
generated_by: quality-updates-crawler
generated_at: {END_DATE_STR}
---
"""


def collect_fss() -> str:
    lines = ["### 금융감독원\n"]

    press = FSS.fetch_press_release()
    APPENDIX["금융감독원"]["보도자료"] = press
    lines += [
        "#### 보도자료\n",
        md_lines([(i["date"], i["title"], i["link"]) for i in sort_fss_items(press)]),
    ]

    rules = FSS.fetch_rules_revision()
    APPENDIX["금융감독원"]["세칙제ㆍ개정예고"] = rules
    lines += [
        "\n#### 세칙제ㆍ개정예고\n",
        md_lines([(i["date"], i["title"], i["link"]) for i in sort_fss_items(rules)]),
    ]

    trend = FSS.fetch_accounting_trend()
    APPENDIX["금융감독원"]["회계감독 동향자료"] = trend
    lines += [
        "\n#### 회계감독 동향자료\n",
        md_lines([(i["date"], i["title"], i["link"]) for i in sort_fss_items(trend)]),
    ]

    return "\n".join(lines)


def collect_fsc() -> str:
    lines = ["\n\n### 금융위원회\n"]

    press = FSC.crawl_board("보도자료", FSC.BASE_URLS["보도자료"])
    APPENDIX["금융위원회"]["보도자료"] = press
    lines += ["#### 보도자료\n", "\n".join(sort_md_link_lines(press))]

    rules = FSC.crawl_board("소관규정", FSC.BASE_URLS["소관규정"])
    APPENDIX["금융위원회"]["고시/공고/훈령"] = rules
    lines += ["\n#### 고시/공고/훈령\n", "\n".join(sort_md_link_lines(rules))]

    legis = FSC.crawl_board("입법예고", FSC.BASE_URLS["입법예고"])
    APPENDIX["금융위원회"]["입법예고/규정변경예고"] = legis
    lines += ["\n#### 입법예고/규정변경예고\n", "\n".join(sort_md_link_lines(legis))]

    return "\n".join(lines)


def collect_kicpa() -> str:
    lines = ["\n\n### 한국공인회계사회\n"]

    noti = KICPA.crawl_period("noti", START_DATE, END_DATE)
    APPENDIX["한국공인회계사회"]["알림마당 - 공지사항"] = noti
    lines += [
        "#### 알림마당 - 공지사항\n",
        md_lines(
            [
                (i["date"].strftime("%y-%m-%d"), i["title"], i["link"])
                for i in sort_kicpa_dict_items(noti)
            ]
        ),
    ]

    std = KICPA_Standards.crawl_sumboard(START_DATE, END_DATE)
    APPENDIX["한국공인회계사회"]["회계감사 - 감사인증기준"] = std
    lines += [
        "\n#### 회계감사 - 감사인증기준\n",
        md_lines(
            [
                (i["date"].strftime("%y-%m-%d"), i["title"], i["link"])
                for i in sort_kicpa_dict_items(std)
            ]
        ),
    ]

    return "\n".join(lines)


def collect_kasb() -> str:
    lines = ["\n\n### 한국회계기준원\n"]

    noti = KASB.crawl_board("공지사항", KASB.BOARDS["공지사항"], START_DATE_STR, END_DATE_STR)
    APPENDIX["한국회계기준원"]["소통광장 - 공지사항"] = noti
    lines += ["#### 소통광장 - 공지사항\n", md_lines(sort_dated_tuples(noti))]

    press = KASB.crawl_board("보도자료", KASB.BOARDS["보도자료"], START_DATE_STR, END_DATE_STR)
    APPENDIX["한국회계기준원"]["소통광장 - 보도자료"] = press
    lines += ["\n#### 소통광장 - 보도자료\n", md_lines(sort_dated_tuples(press))]

    schedule = KASB.crawl_schedule(START_DATE_STR, END_DATE_STR)
    APPENDIX["한국회계기준원"]["주요일정"] = schedule
    lines += ["\n#### 주요일정\n", md_lines(schedule)]

    return "\n".join(lines)


def build_appendix() -> str:
    def normalize(items):
        rows = []
        for i in items:
            if isinstance(i, dict):
                d = i["date"].strftime("%y-%m-%d") if hasattr(i["date"], "strftime") else i["date"]
                rows.append((d, i["title"], i["link"]))
            elif isinstance(i, tuple):
                rows.append(i)
        return md_lines(rows)

    org_blocks = []
    for org, sections in APPENDIX.items():
        section_blocks = []
        for section, items in sections.items():
            if not items:
                continue
            content = "\n".join(items) if isinstance(items[0], str) else normalize(items)
            if content.strip():
                section_blocks.append(f"**{section}**\n\n{content}")
        if section_blocks:
            org_blocks.append(f'??? info "{org}"\n\n' + indent_block("\n\n".join(section_blocks), 4))

    return (
        "\n\n---\n"
        "## Appendix A. Complete List of Retrieved Items (Unfiltered)\n\n"
        '??? info "전체 자료 (전문가 가공 전)"\n\n'
        + indent_block(
            "> The following sections contain all items retrieved by the crawler during the period,\n"
            "> prior to any professional filtering or editorial judgment.\n\n"
            "> Note: Items listed below may include materials not discussed in the main body,\n"
            "> which were excluded based on professional relevance and judgment.\n\n"
            + "\n\n".join(org_blocks),
            4,
        )
    )


def run_collection() -> str:
    """Collect all agencies and return full markdown document."""
    sync_period_to_modules()
    sections = [collect_fss(), collect_fsc(), collect_kicpa(), collect_kasb()]
    return build_front_matter() + "\n\n" + "\n".join(sections) + build_appendix()


def write_markdown(path: Path | None = None) -> Path:
    """Write markdown to path (default: docs/quality-updates/{year}/)."""
    ensure_output_dir()
    dest = path or output_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = run_collection()
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, dest)
    return dest


def main() -> None:
    print("[INFO] Unified crawler started")
    print(f"[INFO] Jurisdiction: {JURISDICTION}")
    print(f"[INFO] Period: {START_DATE_STR} ~ {END_DATE_STR}")
    path = write_markdown()
    print(f"[DONE] Markdown generated → {path}")
