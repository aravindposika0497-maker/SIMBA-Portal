import json
import logging
import secrets
import hmac
import threading
import time
from pathlib import Path

from flask import Blueprint, Response, abort, current_app, g, jsonify, render_template, request, stream_with_context, redirect, url_for, session, flash

from .config import FQN_RE
from .snapshot import StreamLimitReached, to_jsonable

log = logging.getLogger(__name__)
bp = Blueprint("portal", __name__)

CONTENT_PATH = Path(__file__).resolve().parent.parent / "content" / "portal.json"
_ON_DEMAND_TTL = 300
_cache = {}
_cache_lock = threading.Lock()


def _ext():
    return current_app.extensions["simba"]


def _cached(key, loader):
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _ON_DEMAND_TTL:
            return hit[1]
    value = to_jsonable(loader())
    with _cache_lock:
        _cache[key] = (now, value)
    return value


def _sample_tables(settings):
    if settings.sample_tables:
        return list(settings.sample_tables)
    if settings.demo_mode:
        return [f"{settings.catalog}.bronze.demo_user"]
    return []


@bp.before_app_request
def _touch():
    if request.path.startswith("/api/") and request.path != "/api/health":
        _ext()["snapshots"].touch()


@bp.route("/login", methods=["GET"])
def login():
    settings = _ext()["settings"]
    if not settings.demo_mode or settings.auth_mode != "none":
        # In production, authentication is handled by the configured ALB/company identity provider.
        return redirect(url_for("portal.index"))
    if session.get("simba_demo_authenticated"):
        return redirect(url_for("portal.index"))
    token = secrets.token_urlsafe(24)
    session["simba_login_csrf"] = token
    return render_template("login.html", csrf_token=token, demo_mode=True)


@bp.post("/demo-login")
def demo_login():
    settings = _ext()["settings"]
    if not (settings.demo_mode and settings.auth_mode == "none" and settings.demo_login_required):
        abort(404)
    expected_csrf = session.get("simba_login_csrf", "")
    supplied_csrf = request.form.get("csrf_token", "")
    if not expected_csrf or not hmac.compare_digest(expected_csrf, supplied_csrf):
        flash("Your sign-in page expired. Please try again.", "error")
        return redirect(url_for("portal.login"))
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    valid_user = settings.demo_username and hmac.compare_digest(username, settings.demo_username)
    valid_password = settings.demo_password and hmac.compare_digest(password, settings.demo_password)
    if not (valid_user and valid_password):
        flash("Those demo credentials did not match. Check the local .env configuration.", "error")
        return redirect(url_for("portal.login"))
    session.clear()
    session.permanent = True
    session["simba_demo_authenticated"] = True
    session["simba_demo_username"] = username
    return redirect(url_for("portal.index"))


@bp.get("/login/google")
def login_google():
    settings = _ext()["settings"]
    if settings.auth_mode == "alb-oidc":
        # The ALB listener/IdP must be configured to perform the real redirect.
        return redirect(url_for("portal.index"))
    flash("Google sign-in is a design placeholder in demo mode. Configure your company IdP/ALB OIDC before enabling real SSO.", "info")
    return redirect(url_for("portal.login"))


@bp.get("/login/microsoft")
def microsoft_login():
    """Microsoft SSO entry point; actual sign-in requires approved Entra/ALB OIDC configuration."""
    settings = _ext()["settings"]
    if settings.auth_mode == "alb-oidc":
        return redirect(url_for("portal.index"))
    flash("Microsoft sign-in is a UI entry point in demo mode. Configure the approved Microsoft Entra ID / ALB OIDC flow before enabling real SSO.", "info")
    return redirect(url_for("portal.login"))


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("portal.login"))


@bp.get("/")
def index():
    settings = _ext()["settings"]
    return render_template(
        "index.html",
        environment_label=settings.environment_label,
        demo_mode=settings.demo_mode,
        auth_disabled=settings.auth_mode == "none",
        demo_login_required=settings.demo_login_required,
        user=g.get("user") or {},
    )


@bp.get("/api/health")
def health():
    """Liveness for the ALB target group. Does not touch Databricks."""
    return jsonify(status="ok")


@bp.get("/api/ready")
def ready():
    status = _ext()["snapshots"].status()
    failing = [name for name, meta in status["sections"].items() if meta["ok"] is False]
    return jsonify(ready=not failing, failing_sections=failing, mode=status["mode"]), (200 if not failing else 503)


@bp.get("/api/config")
def config():
    settings = _ext()["settings"]
    payload = settings.public_config()
    payload["sample_tables"] = _sample_tables(settings)
    payload["content"] = _ext()["content"]
    payload["live_stream"] = not _ext()["snapshots"].on_demand
    return jsonify(payload)


@bp.get("/api/me")
def me():
    return jsonify(g.get("user") or {})


@bp.get("/api/snapshot")
def snapshot():
    return Response(
        json.dumps(_ext()["snapshots"].snapshot(), default=str),
        mimetype="application/json",
    )


@bp.get("/api/stream")
def stream():
    snapshots = _ext()["snapshots"]
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0
    if snapshots.on_demand:
        return jsonify(error="Live streaming is unavailable on this host; the page polls instead."), 503
    try:
        snapshots.acquire_stream()
    except StreamLimitReached:
        return jsonify(error="Too many live connections; the page will fall back to polling."), 503
    response = Response(stream_with_context(snapshots.stream(since)), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@bp.get("/api/sample")
def sample():
    settings = _ext()["settings"]
    table = request.args.get("table", "")
    if not FQN_RE.match(table) or table not in _sample_tables(settings):
        abort(404)
    try:
        return jsonify(_cached(("sample", table), lambda: _ext()["source"].sample(table)))
    except Exception:
        log.exception("Sample query failed for %s", table)
        return jsonify(error="Sample query failed. Check the portal logs and the service principal's SELECT grant."), 502


@bp.get("/api/lineage/columns")
def column_lineage():
    table = request.args.get("table", "")
    if not FQN_RE.match(table):
        abort(400)
    try:
        return jsonify(_cached(("collineage", table), lambda: _ext()["source"].column_lineage(table)))
    except Exception:
        log.exception("Column lineage query failed for %s", table)
        return jsonify(error="Column lineage query failed. Is system.access.column_lineage enabled and granted?"), 502


def load_content():
    with CONTENT_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)
