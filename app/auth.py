"""Authentication via AWS Application Load Balancer OIDC.

The ALB authenticates users with the company IdP (e.g. Entra ID / Cognito) and
forwards a signed JWT in the `x-amzn-oidc-data` header. We verify that signature
(ES256, key published by AWS per region) and that the token was signed by *our*
ALB, so a request that bypasses the ALB cannot impersonate a user.

https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html
"""
import logging
import re
import threading

import jwt
import requests
from flask import abort, g, redirect, request, session, url_for

log = logging.getLogger(__name__)

PUBLIC_PATHS = {"/api/health", "/login", "/demo-login", "/login/google"}
KID_RE = re.compile(r"^[A-Za-z0-9-]{1,128}$")


class AlbJwtVerifier:
    def __init__(self, region, alb_arn):
        self.region = region
        self.alb_arn = alb_arn
        self._keys = {}
        self._lock = threading.Lock()

    def _public_key(self, kid):
        with self._lock:
            if kid in self._keys:
                return self._keys[kid]
        url = f"https://public-keys.auth.elb.{self.region}.amazonaws.com/{kid}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        with self._lock:
            self._keys[kid] = response.text
        return response.text

    def verify(self, token):
        header = jwt.get_unverified_header(token)
        if header.get("signer") != self.alb_arn:
            raise jwt.InvalidTokenError("Token was not signed by the configured ALB")
        kid = header.get("kid", "")
        if not KID_RE.match(kid):
            raise jwt.InvalidTokenError("Malformed key id")
        return jwt.decode(
            token,
            self._public_key(kid),
            algorithms=["ES256"],
            options={"verify_aud": False, "require": ["exp"]},
            leeway=30,
        )


def init_auth(app, settings):
    verifier = AlbJwtVerifier(settings.aws_region, settings.alb_arn) if settings.auth_mode == "alb-oidc" else None

    @app.before_request
    def authenticate():
        settings = app.extensions["simba"]["settings"]
        if request.path in PUBLIC_PATHS or request.path.startswith("/static/"):
            return None
        # Local login is intentionally demo-only; it is not a production identity system.
        if verifier is None:
            if settings.demo_mode and settings.demo_login_required:
                if not session.get("simba_demo_authenticated"):
                    if request.path.startswith("/api/"):
                        abort(401)
                    return redirect(url_for("portal.login"))
                g.user = {"name": session.get("simba_demo_username", "SIMBA Demo"), "email": None, "auth": "demo-session"}
                return None
            g.user = {"name": "Local user", "email": None, "auth": "disabled"}
            return None

        token = request.headers.get("x-amzn-oidc-data")
        if not token:
            abort(401)
        try:
            claims = verifier.verify(token)
        except Exception:  # noqa: BLE001 - any verification failure is a 401
            log.warning("Rejected request with invalid ALB OIDC token from %s", request.remote_addr)
            abort(401)

        email = (claims.get("email") or "").lower()
        if settings.allowed_email_domains:
            domain = email.rsplit("@", 1)[-1] if "@" in email else ""
            if domain not in settings.allowed_email_domains:
                abort(403)
        g.user = {
            "name": claims.get("name") or email or claims.get("sub"),
            "email": email or None,
            "auth": "alb-oidc",
        }
        return None
