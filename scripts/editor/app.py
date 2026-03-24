# -*- coding: utf-8 -*-
"""Flask routes for the quality-updates editor."""
import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .parser import parse_links
from .saver import save_with_backup

app = Flask(__name__)

CONFIG_PATH = Path(__file__).parent.parent / 'editor_config.json'
DEFAULT_CONFIG = {
    'downloads_folder': 'downloads/',
    'last_file': '',
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding='utf-8') as f:
            cfg = json.load(f)
        return {**DEFAULT_CONFIG, **cfg}
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def repo_root() -> Path:
    """Return repository root (parent of scripts/)."""
    return Path(__file__).parent.parent.parent


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/files')
def list_files():
    root = repo_root()
    updates_dir = root / 'docs' / 'quality-updates'
    files = sorted(updates_dir.rglob('*.md'))
    return jsonify([str(f.relative_to(root)) for f in files])


@app.route('/api/links')
def get_links():
    file_path = request.args.get('file')
    if not file_path:
        return jsonify({'error': 'file param required'}), 400
    root = repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({'error': 'invalid path'}), 400
    if not full_path.exists():
        return jsonify({'error': 'file not found'}), 404
    content = full_path.read_text(encoding='utf-8')
    links = parse_links(content)
    cfg = load_config()
    cfg['last_file'] = file_path
    save_config(cfg)
    return jsonify({'links': links, 'content': content})


@app.route('/api/downloads')
def list_downloads():
    cfg = load_config()
    folder = repo_root() / cfg['downloads_folder']
    if not folder.exists():
        return jsonify([])
    files = sorted(folder.glob('*.pdf'))
    rel = [str(Path(cfg['downloads_folder']) / f.name) for f in files]
    return jsonify(rel)


@app.route('/api/save', methods=['POST'])
def save():
    data = request.get_json()
    file_path = data.get('file')
    curation = data.get('curation', [])
    if not file_path:
        return jsonify({'error': 'file required'}), 400
    root = repo_root().resolve()
    full_path = (root / file_path).resolve()
    if not full_path.is_relative_to(root):
        return jsonify({'error': 'invalid path'}), 400
    if not full_path.exists():
        return jsonify({'error': 'file not found'}), 404
    original = full_path.read_text(encoding='utf-8')
    save_with_backup(str(full_path), original, curation)
    return jsonify({'ok': True})


ALLOWED_CONFIG_KEYS = {'downloads_folder', 'last_file'}

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        return jsonify(load_config())
    cfg = load_config()
    incoming = {k: v for k, v in request.get_json().items() if k in ALLOWED_CONFIG_KEYS}
    cfg.update(incoming)
    save_config(cfg)
    return jsonify(cfg)
