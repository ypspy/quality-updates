# -*- coding: utf-8 -*-
"""Corpus item schema and ID generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "1.0.0"


@dataclass
class NoteBlock:
    admonition: str  # "!!!" or "???"
    title: str
    bullets: list[str] = field(default_factory=list)
    tables: list[list[str]] = field(default_factory=list)


@dataclass
class CorpusItem:
    id: str
    schema_version: str
    period_label: str
    period: dict[str, str]
    agency: str
    date: str
    title: str
    url: str
    summary_status: str
    source_doc: str
    subsection: str = ""
    source: dict[str, str] | None = None
    notes: list[dict[str, Any]] = field(default_factory=list)
    public_page: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d.get("source") is None:
            del d["source"]
        if not d.get("subsection"):
            del d["subsection"]
        if not d.get("public_page"):
            del d["public_page"]
        if not d.get("notes"):
            del d["notes"]
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def url_hash8(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]


def make_id(period_label: str, agency: str, date: str, url: str) -> str:
    return f"{period_label}|{agency}|{date}|{url_hash8(url)}"


def state_to_summary_status(state: str) -> str:
    if state == "skip":
        return "skip"
    if state == "no_summary":
        return "no_summary"
    if state == "done":
        return "done"
    return "undecided"
