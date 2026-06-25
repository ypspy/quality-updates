# -*- coding: utf-8 -*-
"""Page routes: index and favicon."""
from flask import Blueprint, Response, make_response, render_template

bp = Blueprint("pages", __name__)

# Browsers request /favicon.ico by default; SVG payload is widely supported.
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" rx="6" fill="#1a1a2e"/>'
    '<path fill="#e3f2fd" d="M9 9h14v3H9zm0 6h10v3H9zm0 6h12v3H9z"/></svg>'
)


@bp.route("/favicon.ico")
def favicon():
    resp = Response(_FAVICON_SVG, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@bp.route("/")
def index():
    resp = make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp
