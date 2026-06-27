# -*- coding: utf-8 -*-
"""Editor configuration load/save and downloads-folder policy."""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "editor_config.json"
DEFAULT_CONFIG = {
    "downloads_folder": "downloads/",
    "last_file": "",
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        merged = {**DEFAULT_CONFIG, **cfg}
    else:
        merged = dict(DEFAULT_CONFIG)

    # Defensive normalization so a stale/hand-edited config can't escape policy.
    try:
        merged["downloads_folder"] = _normalize_downloads_folder(merged.get("downloads_folder"), root=repo_root())
    except Exception:
        merged["downloads_folder"] = DEFAULT_CONFIG["downloads_folder"]
    return merged


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def repo_root() -> Path:
    """Return repository root (parent of scripts/)."""
    return Path(__file__).parent.parent.parent


def _normalize_downloads_folder(folder_value: object, *, root: Path) -> str:
    """Return normalized downloads folder as a repo-root-relative posix path ending with '/'.

    Policy:
    - must be a relative path (no absolute paths, no drive roots)
    - must not contain path traversal ("..")
    - resolved path must be under repo_root/downloads/
    """
    if not isinstance(folder_value, str) or not folder_value.strip():
        raise ValueError("downloads_folder must be a non-empty string")

    raw = folder_value.strip()
    p = Path(raw)

    if p.is_absolute():
        raise ValueError("downloads_folder must be relative")
    if any(part == ".." for part in p.parts):
        raise ValueError("downloads_folder must not contain '..'")

    root_resolved = root.resolve()
    base = (root_resolved / "downloads").resolve()
    full = (root_resolved / p).resolve()

    if not full.is_relative_to(base):
        raise ValueError("downloads_folder must be under downloads/")

    rel = full.relative_to(root_resolved).as_posix().rstrip("/") + "/"
    if not rel.startswith("downloads/"):
        # Defensive: should be guaranteed by is_relative_to(base) check.
        raise ValueError("downloads_folder must be under downloads/")
    return rel
