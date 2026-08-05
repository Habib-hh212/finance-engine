from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.main import app


def _capture_reset_url(monkeypatch):
    captured = {}

    def fake_send(to_email, reset_url):
        captured["to_email"] = to_email
        captured["reset_url"] = reset_url

    monkeypatch.setattr("app.api.auth.send_password_reset_email", fake_send)
    return captured


def test_forgot_password_unknown_email_returns_generic_message(monkeypatch):
    _capture_reset_url(monkeypatch)
    with TestClient(app) as c:
        r = c.post("/auth/forgot-password", json={"email": "nobody-at-all@example.com"})
        assert r.status_code == 200
        assert "reset link" in r.json()["message"].lower()


def test_forgot_password_then_reset_password_end_to_end(monkeypatch):
    captured = _capture_reset_url(monkeypatch)
    with TestClient(app) as c:
        c.post("/auth/register", json={"email": "resetme@example.com", "password": "original-pw-123", "name": "Reset Me"})

        r = c.post("/auth/forgot-password", json={"email": "resetme@example.com"})
        assert r.status_code == 200
        assert captured["to_email"] == "resetme@example.com"
        token = parse_qs(urlparse(captured["reset_url"]).query)["token"][0]

        r = c.post("/auth/reset-password", json={"token": token, "new_password": "brand-new-pw-456"})
        assert r.status_code == 200

        r = c.post("/auth/login", json={"email": "resetme@example.com", "password": "original-pw-123"})
        assert r.status_code == 401

        r = c.post("/auth/login", json={"email": "resetme@example.com", "password": "brand-new-pw-456"})
        assert r.status_code == 200


def test_reset_token_is_single_use(monkeypatch):
    captured = _capture_reset_url(monkeypatch)
    with TestClient(app) as c:
        c.post("/auth/register", json={"email": "onetime@example.com", "password": "original-pw-123", "name": "One Time"})
        c.post("/auth/forgot-password", json={"email": "onetime@example.com"})
        token = parse_qs(urlparse(captured["reset_url"]).query)["token"][0]

        r = c.post("/auth/reset-password", json={"token": token, "new_password": "first-reset-789"})
        assert r.status_code == 200

        r = c.post("/auth/reset-password", json={"token": token, "new_password": "second-reset-000"})
        assert r.status_code == 400


def test_reset_password_rejects_bogus_token():
    with TestClient(app) as c:
        r = c.post("/auth/reset-password", json={"token": "not-a-real-token", "new_password": "whatever-123"})
        assert r.status_code == 400


def test_new_forgot_password_request_invalidates_previous_token(monkeypatch):
    captured = _capture_reset_url(monkeypatch)
    with TestClient(app) as c:
        c.post("/auth/register", json={"email": "tworequests@example.com", "password": "original-pw-123", "name": "Two Requests"})

        c.post("/auth/forgot-password", json={"email": "tworequests@example.com"})
        first_token = parse_qs(urlparse(captured["reset_url"]).query)["token"][0]

        c.post("/auth/forgot-password", json={"email": "tworequests@example.com"})
        second_token = parse_qs(urlparse(captured["reset_url"]).query)["token"][0]

        r = c.post("/auth/reset-password", json={"token": first_token, "new_password": "whatever-123"})
        assert r.status_code == 400

        r = c.post("/auth/reset-password", json={"token": second_token, "new_password": "whatever-123"})
        assert r.status_code == 200
