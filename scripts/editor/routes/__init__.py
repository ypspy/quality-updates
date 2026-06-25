# -*- coding: utf-8 -*-
"""Flask route blueprints for the quality-updates editor."""
from .clips import bp as clips_bp
from .curation import bp as curation_bp
from .files import bp as files_bp
from .pages import bp as pages_bp
from .source import bp as source_bp

__all__ = ["clips_bp", "curation_bp", "files_bp", "pages_bp", "source_bp"]
