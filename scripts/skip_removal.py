# -*- coding: utf-8 -*-
"""Remove link + <!-- skip --> pairs from quality-updates markdown (pre-deploy)."""

from __future__ import annotations

import re

from editor.parser import APPENDIX_RE, LINK_RE, SKIP_RE

_BLANK_RE = re.compile(r"^\s*$")


def _norm(line: str) -> str:
    return line.rstrip("\r\n")


def remove_skip_pairs(content: str) -> str:
    """Delete link lines immediately followed by ``<!-- skip -->`` (0-1 blank lines allowed).

    Processing stops at ``## Appendix`` (Appendix links are preserved).
    """
    lines = content.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = _norm(raw)
        if APPENDIX_RE.match(line):
            out.extend(lines[i:])
            break

        link_match = LINK_RE.match(line)
        if not link_match:
            out.append(raw)
            i += 1
            continue

        j = i + 1
        while j < len(lines) and _BLANK_RE.match(_norm(lines[j])):
            j += 1

        if j < len(lines) and SKIP_RE.match(_norm(lines[j])):
            i = j + 1
            while i < len(lines) and _BLANK_RE.match(_norm(lines[i])):
                i += 1
            continue

        out.append(raw)
        i += 1

    return "".join(out)
