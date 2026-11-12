# -*- coding: utf-8 -*-
"""오프라인 HWP/HWPX 본문 추출.

.hwp 는 pyhwp 의 ``hwp5html --html`` 만 쓴다. ``hwp5txt`` 는 쓰지 않는다.
.hwpx 는 ZIP 의 ``Contents/section*.xml`` 에서 문단과 표를 읽는다.
"""
from __future__ import annotations

import io
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup


class HwpConvertError(RuntimeError):
    """hwp5html 이 실패했거나 HWPX 에서 글을 읽지 못했다."""


def hwp5html_command(hwp_path: Path, output: Path) -> list[str]:
    """``hwp5html --html --output`` 인자. ``hwp5txt`` 는 포함하지 않는다."""
    tail = ["--html", "--output", str(output), str(hwp_path)]
    script = shutil.which("hwp5html")
    if script:
        return [script, *tail]
    return [
        sys.executable,
        "-c",
        "import sys; from hwp5.hwp5html import main; sys.argv = ['hwp5html', *sys.argv[1:]]; main()",
        *tail,
    ]


def hwp_file_to_html(path: Path, timeout: float = 90) -> str:
    """임시 디렉터리에서 hwp5html --html 을 실행하고 HTML 문자열을 돌려준다.

    변환 파일은 임시 디렉터리와 함께 지운다. 아카이브 폴더에는 남기지 않는다.
    """
    import tempfile

    source = Path(path).resolve()
    with tempfile.TemporaryDirectory(prefix="fss-hwp-") as tmp:
        out = Path(tmp) / "out.html"
        completed = subprocess.run(
            hwp5html_command(source, out),
            cwd=tmp,
            timeout=timeout,
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or b"").decode("utf-8", "replace").strip()
            raise HwpConvertError(detail or f"hwp5html exit {completed.returncode}")
        if not out.is_file():
            raise HwpConvertError("hwp5html produced no html")
        return out.read_text(encoding="utf-8", errors="replace")


def html_to_markdown(html: str) -> str:
    """문단은 문단으로, 표는 마크다운 표로 남긴다. head, style, script 는 버린다."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all(["head", "style", "script"]):
        tag.decompose()
    root = soup.body or soup
    blocks = [block for block in _html_blocks(root) if block.strip()]
    return "\n\n".join(blocks).strip()


def _html_blocks(node) -> list[str]:
    blocks: list[str] = []
    for child in list(getattr(node, "children", []) or []):
        name = getattr(child, "name", None)
        if name is None:
            text = str(child).strip()
            if text:
                blocks.append(text)
            continue
        if name in {"head", "style", "script"}:
            continue
        if name == "table":
            table = _html_table(child)
            if table:
                blocks.append(table)
            continue
        if name in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}:
            if child.find("table"):
                blocks.extend(_html_blocks(child))
            else:
                text = " ".join(child.get_text(" ", strip=True).split())
                if text:
                    blocks.append(text)
            continue
        blocks.extend(_html_blocks(child))
    return blocks


def _html_table(table) -> str:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [_cell_text(cell) for cell in tr.find_all(["th", "td"], recursive=False)]
        if not cells:
            cells = [_cell_text(cell) for cell in tr.find_all(["th", "td"])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    lines = [
        "| " + " | ".join(padded[0]) + " |",
        "| " + " | ".join("---" for _ in padded[0]) + " |",
    ]
    for row in padded[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _cell_text(cell) -> str:
    return " ".join(cell.get_text(" ", strip=True).split()).replace("|", "\\|")


def hwpx_to_text(data: bytes) -> str:
    """HWPX ZIP 의 section XML 에서 ``hp:t`` 와 표 행·셀을 읽는다."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise HwpConvertError(str(exc)) from exc
    blocks: list[str] = []
    with archive:
        for name in _section_names(archive.namelist()):
            try:
                root = ET.fromstring(archive.read(name))
            except ET.ParseError as exc:
                raise HwpConvertError(f"{name}: {exc}") from exc
            blocks.extend(_hwpx_container(root))
    return "\n\n".join(block for block in blocks if block.strip()).strip()


def _section_names(names: list[str]) -> list[str]:
    picked = []
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if len(parts) != 2 or parts[0].lower() != "contents":
            continue
        leaf = parts[1].lower()
        if leaf.startswith("section") and leaf.endswith(".xml"):
            picked.append(name)
    return sorted(picked)


def _local(tag: str) -> str:
    if isinstance(tag, str) and tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return str(tag)


def _hwpx_container(elem) -> list[str]:
    blocks: list[str] = []
    for child in list(elem):
        name = _local(child.tag)
        if name == "p":
            blocks.extend(_hwpx_paragraph(child))
        elif name == "tbl":
            table = _hwpx_table(child)
            if table:
                blocks.append(table)
        else:
            blocks.extend(_hwpx_container(child))
    return blocks


def _hwpx_paragraph(paragraph) -> list[str]:
    blocks: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        text = "".join(buf).strip()
        buf.clear()
        if text:
            blocks.append(text)

    def consume(node) -> None:
        for child in list(node):
            name = _local(child.tag)
            if name == "tbl":
                flush()
                table = _hwpx_table(child)
                if table:
                    blocks.append(table)
                if child.tail:
                    buf.append(child.tail)
                continue
            if name == "t":
                if child.text:
                    buf.append(child.text)
                consume(child)
                if child.tail:
                    buf.append(child.tail)
                continue
            consume(child)
            if child.tail:
                buf.append(child.tail)

    consume(paragraph)
    flush()
    return blocks


def _hwpx_rows(table) -> list:
    rows = []
    for child in list(table):
        name = _local(child.tag)
        if name == "tr":
            rows.append(child)
        elif name != "tbl":
            rows.extend(grand for grand in list(child) if _local(grand.tag) == "tr")
    return rows


def _hwpx_table(table) -> str:
    rows: list[list[str]] = []
    for tr in _hwpx_rows(table):
        cells = []
        for tc in list(tr):
            if _local(tc.tag) != "tc":
                continue
            parts = _hwpx_container(tc)
            text = " ".join(part.replace("\n", " ") for part in parts)
            cells.append(" ".join(text.split()).replace("|", "\\|"))
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    lines = [
        "| " + " | ".join(padded[0]) + " |",
        "| " + " | ".join("---" for _ in padded[0]) + " |",
    ]
    for row in padded[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)
