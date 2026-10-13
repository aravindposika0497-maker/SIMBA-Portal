import logging
import os
import secrets

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from .auth import init_auth
from .config import Settings
from .databricks_client import DatabricksClient
from .demo_source import DemoSource
from .live_source import LiveSource
from .routes import bp, load_content
from .snapshot import SnapshotService

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def create_app(settings=None, start_background=True):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = settings or Settings.from_env()
    problems = settings.validate()
    if problems:
        raise RuntimeError("Invalid SIMBA portal configuration:\n  - " + "\n  - ".join(problems))

    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config.update(MAX_CONTENT_LENGTH=1024 * 1024)
    # Demo sessions are short-lived UI gating only. Production sign-in belongs at the ALB/IdP.
    app.secret_key = os.getenv("SIMBA_SESSION_SECRET") or secrets.token_urlsafe(32)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.getenv("SIMBA_COOKIE_SECURE", "false").lower() == "true", PERMANENT_SESSION_LIFETIME=1800)
    app.json.sort_keys = False

    source = DemoSource(settings) if settings.demo_mode else LiveSource(settings, DatabricksClient(settings))
    snapshots = SnapshotService(settings, source)
    app.extensions["simba"] = {
        "settings": settings,
        "source": source,
        "snapshots": snapshots,
        "content": load_content(),
    }

    init_auth(app, settings)
    app.register_blueprint(bp)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(HTTPException)
    def http_error(exc):
        if request.path.startswith("/api/"):
            return jsonify(error=exc.name), exc.code
        return exc

    logging.getLogger(__name__).info(
        "SIMBA portal starting in %s mode (auth=%s, catalog=%s)",
        source.mode, settings.auth_mode, settings.catalog,
    )
    if start_background:
        snapshots.start()
    return app
