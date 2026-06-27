# -*- coding: utf-8 -*-
"""Flask application factory for the quality-updates editor."""
import threading

import requests
from flask import Flask

from .config import (
    CONFIG_PATH,
    DEFAULT_CONFIG,
    _normalize_downloads_folder,
    load_config,
    repo_root,
    save_config,
)
from .download_helpers import _parse_content_disposition_filename
from .preview_helpers import (
    _PREVIEW_JOBS,
    _PREVIEW_JOBS_LOCK,
    _build_preview_payload,
    _capture_preview_png_bytes,
    _fetch_exception_user_message,
    _ocr_png_to_text,
)
from .routes.clips import bp as clips_bp
from .routes.curation import bp as curation_bp
from .routes.files import bp as files_bp
from .routes.pages import bp as pages_bp
from .routes.source import _KASB_DOWNLOAD_POST_URL, bp as source_bp
from .source_fetch import fetch_url


def create_app() -> Flask:
    """Create and configure the Flask application."""
    application = Flask(__name__)
    application.register_blueprint(pages_bp)
    application.register_blueprint(files_bp)
    application.register_blueprint(curation_bp)
    application.register_blueprint(clips_bp)
    application.register_blueprint(source_bp)
    return application


app = create_app()

__all__ = [
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "_KASB_DOWNLOAD_POST_URL",
    "_PREVIEW_JOBS",
    "_PREVIEW_JOBS_LOCK",
    "_build_preview_payload",
    "_capture_preview_png_bytes",
    "_fetch_exception_user_message",
    "_normalize_downloads_folder",
    "_ocr_png_to_text",
    "_parse_content_disposition_filename",
    "app",
    "create_app",
    "fetch_url",
    "load_config",
    "repo_root",
    "requests",
    "save_config",
    "threading",
]
