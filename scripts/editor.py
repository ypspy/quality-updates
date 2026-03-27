# -*- coding: utf-8 -*-
"""Entry point: python scripts/editor.py"""
import os
import sys
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(__file__))
from editor.app import app

PORT = 5000

# nodemon처럼 코드 변경 시 자동 재기동: FLASK_DEBUG=0 이면 끔 (기본 켬).
def _want_debug() -> bool:
    v = (os.environ.get("FLASK_DEBUG") or "1").strip().lower()
    return v not in ("0", "false", "off", "no")


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
    if debug:
        print("FLASK_DEBUG=1: .py 수정 시 서버가 자동 재시작합니다. 끄려면 FLASK_DEBUG=0", flush=True)
    print('If favicon or /api/source/preview returns 404, stop other apps on this port and restart this process.', flush=True)
    app.run(port=PORT, debug=debug, use_reloader=debug)
