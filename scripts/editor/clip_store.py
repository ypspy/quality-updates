# -*- coding: utf-8 -*-
"""File-backed clip storage for SOURCE type clip (pasteboard text)."""
from __future__ import annotations

import hashlib
import json
import secrets
import time
import re
from pathlib import Path

_CLIP_ID_RE = re.compile(r"^clip_\d+_[0-9a-f]{8}$")


def clips_dir() -> Path:
    return Path(__file__).parent / "clips"


def _ensure_dir() -> None:
    clips_dir().mkdir(parents=True, exist_ok=True)


def _clip_path(clip_id: str) -> Path:
    if not clip_id or not _CLIP_ID_RE.match(clip_id):
        raise ValueError("invalid clip id")
    return clips_dir() / f"{clip_id}.json"


def create_clip(raw: str, *, content_type: str = "text/plain") -> str:
    """Save pasted text and return a new clip id."""
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    text = raw
    if len(text.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("clip too large (max 2MB utf-8)")

    _ensure_dir()
    now = time.time()
    clip_id = f"clip_{int(now)}_{secrets.token_hex(4)}"
    path = _clip_path(clip_id)

    body = text.encode("utf-8")
    record = {
        "id": clip_id,
        "created_at": now,
        "updated_at": now,
        "content_type": content_type or "text/plain",
        "raw": text,
        "byte_length": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return clip_id


def get_clip(clip_id: str) -> dict | None:
    """Load clip record or None if missing."""
    try:
        path = _clip_path(clip_id)
    except ValueError:
        return None
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
