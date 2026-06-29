# -*- coding: utf-8 -*-
"""Entry point: python scripts/editor.py"""
import os
import sys
from pathlib import Path

_REEXEC_ENV = "QUALITY_UPDATES_EDITOR_VENV_REEXEC"
_RELOADER_EXCLUDES = [
    "**/.venv/**",
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/site-packages/**",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _venv_python() -> Path | None:
    root = _repo_root()
    if sys.platform == "win32":
        cand = root / ".venv" / "Scripts" / "python.exe"
    else:
        cand = root / ".venv" / "bin" / "python"
    return cand if cand.is_file() else None


def _maybe_reexec_with_venv() -> None:
    """Use repo .venv when system python lacks editor capture deps (playwright)."""
    if os.environ.get(_REEXEC_ENV) == "1":
        return
    try:
        import playwright  # noqa: F401
        return
    except ImportError:
        pass

    venv_py = _venv_python()
    if not venv_py:
        return
    try:
        if Path(sys.executable).resolve() == venv_py.resolve():
            return
    except OSError:
        return

    os.environ[_REEXEC_ENV] = "1"
    os.execv(str(venv_py), [str(venv_py), *sys.argv])


def _warn_capture_deps() -> None:
    missing: list[str] = []
    try:
        import playwright  # noqa: F401
    except ImportError:
        missing.append(
            "playwright (`pip install playwright` 후 `python -m playwright install chromium`)"
        )
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        missing.append("pytesseract (`pip install pytesseract`)")
    if missing:
        print("WARNING: WEB 캡쳐+OCR 비활성 — " + "; ".join(missing), flush=True)


_maybe_reexec_with_venv()

import threading
import webbrowser

sys.path.insert(0, os.path.dirname(__file__))
from editor.app import app

PORT = 5000

# nodemon처럼 코드 변경 시 자동 재기동: FLASK_DEBUG=0 이면 끔 (기본 켬).
def _want_debug() -> bool:
    v = (os.environ.get("FLASK_DEBUG") or "1").strip().lower()
    return v not in ("0", "false", "off", "no")


def _use_reloader(debug: bool) -> bool:
    """Playwright capture + Flask watchdog reloader kills in-flight POST requests."""
    if not debug:
        return False
    if os.environ.get("QUALITY_UPDATES_EDITOR_FORCE_RELOAD", "").strip() == "1":
        return True
    try:
        import playwright  # noqa: F401
    except ImportError:
        return True
    print(
        "FLASK_DEBUG=1 이지만 Playwright 사용 시 자동 재시작을 끕니다 (캡쳐 중 요청 끊김 방지).",
        flush=True,
    )
    print(
        "  hot-reload가 필요하면 편집기를 재시작하거나 QUALITY_UPDATES_EDITOR_FORCE_RELOAD=1",
        flush=True,
    )
    return False


if __name__ == '__main__':
    url = f'http://localhost:{PORT}'
    debug = _want_debug()
    rules = {r.rule for r in app.url_map.iter_rules()}
    for path in ('/favicon.ico', '/api/source/preview'):
        if path not in rules:
            print(f'WARNING: route {path} missing — use an up-to-date scripts/editor tree and restart.', flush=True)
    # 디버그+리로더: .py 수정 시 자식만 재시작됨. 자식에서 webbrowser.open 하면 탭이 매번 열림 → 부모에서만 1회 오픈.
    # 비디버그: 단일 프로세스이므로 항상 오픈.
    if debug:
        open_browser = os.environ.get("WERKZEUG_RUN_MAIN") != "true"
    else:
        open_browser = True
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f'Quality Updates Editor → {url}', flush=True)
    _warn_capture_deps()
    if debug:
        print("FLASK_DEBUG=1: .py 수정 시 서버가 자동 재시작합니다. 끄려면 FLASK_DEBUG=0", flush=True)
    print('If favicon or /api/source/preview returns 404, stop other apps on this port and restart this process.', flush=True)
    app.run(
        port=PORT,
        debug=debug,
        use_reloader=_use_reloader(debug),
        exclude_patterns=_RELOADER_EXCLUDES,
    )
