# -*- coding: utf-8 -*-
"""Entry point: python scripts/editor.py"""
import os
import sys
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(__file__))
from editor.app import app

PORT = 5000

if __name__ == '__main__':
    url = f'http://localhost:{PORT}'
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f'Quality Updates Editor → {url}')
    app.run(port=PORT, debug=False)
