"""Run on the EC2 instance or any machine with Python 3.10+:
    python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/pytest -q
"""
import json
import re
from dataclasses import replace

import pytest

from app import create_app
from app.auth import AlbJwtVerifier
from app.config import Settings
from app.masking import mask_rows
from app.snapshot import ALL_SECTIONS


@pytest.fixture()
def app():
    settings = Settings(demo_mode=True, auth_mode="none", mask_patterns=("email",))
    application = create_app(settings, start_background=False)
    application.extensions["simba"]["snapshots"].refresh(ALL_SECTIONS)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def test_health_is_public_and_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_index_renders_with_security_headers(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Demo mode" in r.data
    assert "script-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Frame-Options"] == "DENY"


def test_config_exposes_no_secrets(client):
    body = client.get("/api/config").get_json()
    text = json.dumps(body).lower()
    for forbidden in ("client_secret", "token", "http_path", "server_hostname"):
        assert forbidden not in text
    assert body["demo_mode"] is True
    assert body["content"]["about"]["heading"]


def test_snapshot_has_all_sections(client):
    body = client.get("/api/snapshot").get_json()
    for name in ALL_SECTIONS:
        assert body["sections"][name] is not None, name
        assert body["meta"]["sections"][name]["ok"] is True
    assert body["meta"]["mode"] == "demo"


def test_sample_allowlist(client):
    assert client.get("/api/sample?table=simba_data_poc.bronze.demo_user").status_code == 200
    assert client.get("/api/sample?table=simba_data_poc.bronze.not_allowed").status_code == 404
    assert client.get("/api/sample?table=x;DROP TABLE y").status_code == 404


def test_sample_is_masked(client):
    body = client.get("/api/sample?table=simba_data_poc.bronze.demo_user").get_json()
    assert "email" in body["masked_columns"]
    assert all(row["email"].endswith("***") for row in body["rows"])


def test_stream_limit(app):
    snapshots = app.extensions["simba"]["snapshots"]
    snapshots.settings = replace(snapshots.settings, max_streams=0)
    r = app.test_client().get("/api/stream")
    assert r.status_code == 503


def test_live_mode_requires_databricks_settings():
    with pytest.raises(RuntimeError):
        create_app(Settings(demo_mode=False, auth_mode="none"), start_background=False)


def test_alb_auth_rejects_missing_token():
    settings = Settings(demo_mode=True, auth_mode="alb-oidc", alb_arn="arn:aws:elasticloadbalancing:eu-west-1:000000000000:loadbalancer/app/x/y")
    client = create_app(settings, start_background=False).test_client()
    assert client.get("/api/config").status_code == 401
    assert client.get("/api/health").status_code == 200


def test_alb_verifier_rejects_wrong_signer():
    import jwt as pyjwt

    token = pyjwt.encode({"exp": 9999999999}, "k" * 32, algorithm="HS256", headers={"signer": "arn:other", "kid": "abc"})
    with pytest.raises(pyjwt.InvalidTokenError):
        AlbJwtVerifier("eu-west-1", "arn:expected").verify(token)


def test_mask_rows():
    rows, masked = mask_rows([{"customer_email": "a@b.com", "amount": 5}], ("email",))
    assert masked == ["customer_email"]
    assert rows[0]["customer_email"] == "a@***"
    assert rows[0]["amount"] == 5


def test_demo_login_gate_and_success(monkeypatch):
    monkeypatch.setenv("SIMBA_SESSION_SECRET", "test-session-secret-with-more-than-32-chars")
    settings = Settings(demo_mode=True, auth_mode="none", demo_login_required=True,
                        demo_username="demo-user", demo_password="test-password", mask_patterns=("email",))
    application = create_app(settings, start_background=False)
    client = application.test_client()
    assert client.get("/").status_code == 302
    login_page = client.get("/login")
    assert login_page.status_code == 200
    assert b"Data Lake Admin Portal" in login_page.data
    token = re.search(rb'name="csrf_token" value="([^"]+)"', login_page.data).group(1).decode()
    bad = client.post("/demo-login", data={"csrf_token": token, "username": "wrong", "password": "wrong"})
    assert bad.status_code == 302
    login_page = client.get("/login")
    token = re.search(rb'name="csrf_token" value="([^"]+)"', login_page.data).group(1).decode()
    good = client.post("/demo-login", data={"csrf_token": token, "username": "demo-user", "password": "test-password"})
    assert good.status_code == 302
    assert client.get("/").status_code == 200
    assert client.get("/api/config").status_code == 200
    assert client.post("/logout").status_code == 302
    assert client.get("/").status_code == 302
