# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup

_DETAIL_RE = re.compile(r"fn_Detail\s*\(\s*'(\d+)'\s*,\s*'(\d+)'\s*\)")
_FILE_RE = re.compile(r"fileDownload\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")
_PAGE_RE = re.compile(r"G_MovePage\((\d+)\)")


@dataclass(frozen=True)
class AttachmentRef:
    name: str
    file_no: str
    file_seq: str


@dataclass(frozen=True)
class ListRow:
    seq: str
    ctg_cd: str
    number: str
    category: str
    title: str
    reply_date: str | None
    published_date: str | None
    attachments: tuple[AttachmentRef, ...]


def parse_date(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _attachments_in(node) -> list[AttachmentRef]:
    found = []
    for link in node.find_all("a"):
        match = _FILE_RE.search(link.get("onclick") or "")
        if not match:
            continue
        name = link.get_text(strip=True) or f"file-{match.group(2)}"
        found.append(AttachmentRef(name=name, file_no=match.group(1), file_seq=match.group(2)))
    return found


def parse_list_page(html: str) -> list[ListRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.select("table tbody tr"):
        cells = tr.find_all("td")
        if len(cells) < 6:
            continue
        title_link = None
        detail = None
        for link in cells[2].find_all("a"):
            detail = _DETAIL_RE.search(link.get("onclick") or "")
            if detail:
                title_link = link
                break
        if not detail or title_link is None:
            continue
        rows.append(
            ListRow(
                seq=detail.group(1),
                ctg_cd=detail.group(2),
                number=cells[0].get_text(strip=True),
                category=cells[1].get_text(strip=True),
                title=title_link.get_text(strip=True),
                reply_date=parse_date(cells[4].get_text(strip=True)),
                published_date=parse_date(cells[5].get_text(strip=True)),
                attachments=tuple(_attachments_in(cells[3])),
            )
        )
    return rows


def last_page_number(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("li.pag_last a")
    if node is None:
        return 1
    match = _PAGE_RE.search(node.get("href") or "")
    return int(match.group(1)) if match else 1


def dedupe_rows(rows: list[ListRow]) -> list[ListRow]:
    seen: set[str] = set()
    kept = []
    for row in rows:
        if row.seq in seen:
            continue
        seen.add(row.seq)
        kept.append(row)
    return kept


@dataclass(frozen=True)
class DetailPage:
    category: str | None
    standards: tuple[str, ...]
    registered_date: str | None
    notice: str
    attachments: tuple[AttachmentRef, ...]


def _labeled_text(wrap, label: str) -> str:
    for th in wrap.find_all("th"):
        if th.get_text(strip=True) == label:
            td = th.find_next("td")
            return td.get_text(" ", strip=True) if td else ""
    return ""


def parse_detail_page(html: str) -> DetailPage:
    soup = BeautifulSoup(html, "html.parser")
    wrap = soup.select_one(".board_view_wrap") or soup
    category = _labeled_text(wrap, "분류") or None
    standards: list[str] = []
    for th in wrap.find_all("th"):
        if th.get_text(strip=True) != "관련기준서":
            continue
        td = th.find_next("td")
        if td is not None:
            inner_rows = td.find_all("tr")
            if not inner_rows:
                text = td.get_text(" ", strip=True)
                if text:
                    standards.append(text)
            else:
                for row in inner_rows:
                    label_th = row.find("th")
                    label = label_th.get_text(strip=True) if label_th else ""
                    td_texts = [
                        cell.get_text(" ", strip=True)
                        for cell in row.find_all("td")
                        if cell.get_text(" ", strip=True)
                    ]
                    joined = " ".join(td_texts)
                    if not joined:
                        continue
                    if label == "기준서 명" and standards:
                        standards[-1] = f"{standards[-1]} {joined}"
                    else:
                        standards.append(joined)
        break
    notice_node = wrap.select_one(".board_view_cont")
    notice = notice_node.get_text(" ", strip=True) if notice_node else ""
    return DetailPage(
        category=category,
        standards=tuple(standards),
        registered_date=parse_date(_labeled_text(wrap, "등록일")),
        notice=notice,
        attachments=tuple(_attachments_in(wrap)),
    )
