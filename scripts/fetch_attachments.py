# -*- coding: utf-8 -*-
"""Download attachments for summary-needed items and record source markers.

Run after ``auto_curate.py`` has classified a quarter file. Items marked
``<!-- skip -->`` or ``<!-- no_summary -->`` (link-only), and items that already
have a summary note, are left alone. Bare links use the same classification as
``auto_curate.py``.

HWP/HWPX files are saved only when no PDF of the same document was offered.
The owner converts those files to PDF in Naver Whale. This script does not
convert Hangul documents.

Example::

    python scripts/fetch_attachments.py docs/quality-updates/2026/2026-07-01_to_2026-09-30.md
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import auto_curate
from editor.page_attachments import (
    PageFetchResult,
    downloads_dir,
    fetch_page_attachments,
)
from editor.parser import parse_links
from editor.saver import apply_curation, save_with_backup

_FILE_TYPES = {"pdf", "hwp", "file"}
_PREVIEW_TYPES = {"clip", "shot", "web"}


@dataclass
class ItemReport:
    date: str
    title: str
    url: str
    pdfs: list[str] = field(default_factory=list)
    hwps: list[str] = field(default_factory=list)
    others: list[str] = field(default_factory=list)
    skipped_hwp: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class RunSummary:
    reports: list[ItemReport]
    updated: int
    report_path: Path

    def stdout_line(self) -> str:
        pdfs = sum(len(item.pdfs) for item in self.reports)
        hwps = sum(len(item.hwps) for item in self.reports)
        failed = sum(1 for item in self.reports if item.errors)
        skipped = sum(len(item.skipped_hwp) for item in self.reports)
        return (
            f"대상 {len(self.reports)}건 · PDF {pdfs}건 · "
            f"수동 변환 HWP {hwps}건 · PDF와 같아 건너뛴 HWP {skipped}건 · "
            f"실패 {failed}건 · 마커 갱신 {self.updated}건"
        )


def needs_attachment_fetch(link: dict, decision: auto_curate.Decision | None) -> bool:
    """True for summary items that are not skip, link-only, or already summarized."""
    state = link.get("state")
    if state in {"skip", "no_summary", "done"}:
        return False
    if state == "needs_summary":
        return True
    return decision is not None and decision.state == "needs_summary"


def merge_sources(existing: list[dict] | None, attached: list[dict]) -> list[dict]:
    """Keep real markers, drop ``pending`` placeholders, then append new files."""
    kept: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for src in existing or []:
        if not isinstance(src, dict):
            continue
        src_type = src.get("type")
        src_ref = str(src.get("ref") or "").strip()
        if not isinstance(src_type, str) or not src_ref or src_ref == "pending":
            continue
        key = (src_type, src_ref)
        if key in seen:
            continue
        seen.add(key)
        kept.append({"type": src_type, "ref": src_ref})
    for src in attached:
        key = (src["type"], src["ref"])
        if key in seen:
            continue
        seen.add(key)
        kept.append({"type": src["type"], "ref": src["ref"]})
    return kept


def render_report(md_path: Path, reports: list[ItemReport]) -> str:
    pdf_rows = [item for item in reports if item.pdfs]
    hwp_rows = [item for item in reports if item.hwps]
    other_rows = [item for item in reports if item.others]
    skipped_rows = [item for item in reports if item.skipped_hwp]
    failed_rows = [item for item in reports if item.errors]
    lines = [
        "# 첨부 다운로드 보고",
        "",
        f"- 분기 파일: `{md_path.as_posix()}`",
        f"- 대상: {len(reports)}건",
        "",
        "HWP/HWPX 변환은 네이버 웨일에서 PDF로 저장한 뒤, 그 PDF를 같은 항목의 source 마커로 연결한다.",
        "이 스크립트는 한글 파일을 PDF로 변환하지 않는다.",
        "",
        "## 받은 PDF",
        "",
    ]
    if not pdf_rows:
        lines.append("- 없음")
    else:
        for item in pdf_rows:
            lines.append(f"- {item.date} {item.title}")
            lines.append(f"  - {item.url}")
            for ref in item.pdfs:
                lines.append(f"  - `{ref}`")
    lines.extend(["", "## 그 밖 첨부", ""])
    lines.append("PDF·HWP가 아닌 저장 파일(zip, 오피스 문서 등)이다.")
    lines.append("")
    if not other_rows:
        lines.append("- 없음")
    else:
        for item in other_rows:
            lines.append(f"- {item.date} {item.title}")
            lines.append(f"  - {item.url}")
            for ref in item.others:
                lines.append(f"  - `{ref}`")
    lines.extend(["", "## 수동 변환 필요 (네이버 웨일)", ""])
    lines.append("같은 문서의 PDF가 없는 HWP/HWPX만 적는다.")
    lines.append("")
    if not hwp_rows:
        lines.append("- 없음")
    else:
        for item in hwp_rows:
            lines.append(f"- {item.date} {item.title}")
            lines.append(f"  - {item.url}")
            for ref in item.hwps:
                lines.append(f"  - `{ref}`")
    lines.extend(["", "## PDF와 같아 건너뛴 HWP", ""])
    lines.append("같은 첨부의 PDF를 받았으므로 한글 파일은 저장하지 않았다.")
    lines.append("")
    if not skipped_rows:
        lines.append("- 없음")
    else:
        for item in skipped_rows:
            listed = ", ".join(f"`{name}`" for name in item.skipped_hwp)
            lines.append(f"- {item.date} {item.title} — {listed}")
    lines.extend(["", "## 다운로드 실패", ""])
    if not failed_rows:
        lines.append("- 없음")
    else:
        for item in failed_rows:
            lines.append(f"- {item.date} {item.title}")
            lines.append(f"  - {item.url}")
            for error in item.errors:
                lines.append(f"  - {error}")
    lines.append("")
    return "\n".join(lines)


def run(md_path: Path, *, report_path: Path, root: Path, folder: Path) -> RunSummary:
    original = md_path.read_text(encoding="utf-8")
    links = parse_links(original)
    decisions = _decisions_for(original)
    reports: list[ItemReport] = []
    curation: list[dict] = []

    for link in links:
        decision = decisions.get(_link_key(link))
        if not needs_attachment_fetch(link, decision):
            continue
        report = ItemReport(
            date=str(link.get("date") or ""),
            title=str(link.get("title") or ""),
            url=str(link.get("url") or ""),
        )
        result = fetch_page_attachments(report.url, root=root, folder=folder)
        _fill_report(report, result, link, decision)
        reports.append(report)

        if not result.attached:
            continue
        existing = link.get("sources") if isinstance(link.get("sources"), list) else []
        if not existing and isinstance(link.get("source"), dict):
            existing = [link["source"]]
        merged = merge_sources(existing, [
            {"type": item.source_type, "ref": item.ref} for item in result.attached
        ])
        if not merged or _pairs(merged) == _pairs(existing):
            continue
        pdf_ref = next((item["ref"] for item in merged if item["type"] == "pdf"), None)
        curation.append(
            {
                "line_index": link.get("line_index"),
                "state": "needs_summary",
                "sources": merged,
                "source": merged[0],
                "pdf_path": pdf_ref,
            }
        )

    updated = 0
    if curation:
        new_content = apply_curation(original, curation)
        if new_content != original:
            save_with_backup(str(md_path), original, curation)
            updated = len(curation)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(md_path, reports), encoding="utf-8")
    return RunSummary(reports=reports, updated=updated, report_path=report_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="요약 대상 항목의 원문 첨부를 모두 받아 source 마커로 기록합니다."
    )
    parser.add_argument("path", type=Path, help="분기 markdown 파일")
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="보고 markdown 경로 (기본: 다운로드 폴더/fetch-attachments-report.md)",
    )
    args = parser.parse_args(argv)
    md_path = args.path
    if not md_path.is_file():
        print(f"파일을 찾을 수 없습니다: {md_path}", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parent.parent
    folder = downloads_dir(root)
    report_path = args.report or (folder / "fetch-attachments-report.md")
    summary = run(md_path, report_path=report_path, root=root, folder=folder)
    print(summary.stdout_line())
    print(f"보고: {report_path}")
    return 0


def _link_key(link: dict) -> tuple[str, str, str]:
    return (str(link.get("date") or ""), str(link.get("title") or ""), str(link.get("url") or ""))


def _decisions_for(text: str) -> dict[tuple[str, str, str], auto_curate.Decision]:
    body, _appendix = auto_curate.parse_document(text)
    decisions = auto_curate.decide_all(body)
    out: dict[tuple[str, str, str], auto_curate.Decision] = {}
    for item, decision in zip(body, decisions):
        out[(item.date, item.title, item.url)] = decision
    return out


def _expects_new_file(link: dict, decision: auto_curate.Decision | None) -> bool:
    sources = link.get("sources") if isinstance(link.get("sources"), list) else []
    if not sources and isinstance(link.get("source"), dict):
        sources = [link["source"]]
    real = [
        src
        for src in sources
        if isinstance(src, dict) and str(src.get("ref") or "").strip() not in {"", "pending"}
    ]
    if any(src.get("type") in _FILE_TYPES for src in real):
        return False
    if any(src.get("type") in _PREVIEW_TYPES for src in real):
        return False
    if decision is not None and link.get("state") != "needs_summary":
        if decision.source_type in _PREVIEW_TYPES:
            return False
    return True


def _fill_report(
    report: ItemReport,
    result: PageFetchResult,
    link: dict,
    decision: auto_curate.Decision | None,
) -> None:
    if not result.ok:
        report.errors.append(result.message)
        return
    for item in result.attached:
        if item.source_type == "pdf":
            report.pdfs.append(item.ref)
        elif item.source_type == "hwp":
            report.hwps.append(item.ref)
        else:
            report.others.append(item.ref)
    report.skipped_hwp.extend(result.skipped_hwp)
    for failed in result.failed:
        name = failed.get("name") or report.url
        report.errors.append(f"{name}: {failed.get('error') or '다운로드 실패'}")
    if not result.attached and not report.errors and _expects_new_file(link, decision):
        report.errors.append(result.message or "첨부 파일을 찾지 못했습니다.")


def _pairs(sources: list[dict] | None) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for src in sources or []:
        if isinstance(src, dict) and src.get("type") and src.get("ref"):
            out.append((str(src["type"]), str(src["ref"])))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
