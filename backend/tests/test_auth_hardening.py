from fastapi.testclient import TestClient

from app.main import app


def _fresh_client() -> TestClient:
    c = TestClient(app)
    c.__enter__()
    return c


def test_login_sets_httponly_session_cookies():
    c = _fresh_client()
    c.post("/auth/register", json={"email": "cookie1@example.com", "password": "hunter22222", "name": "Cookie One"})
    r = c.post("/auth/login", json={"email": "cookie1@example.com", "password": "hunter22222"})
    assert r.status_code == 200, r.text
    assert "fe_access_token" in r.cookies
    assert "fe_refresh_token" in r.cookies


def test_cookie_alone_authenticates_without_bearer_header():
    c = _fresh_client()
    c.post("/auth/register", json={"email": "cookie2@example.com", "password": "hunter22222", "name": "Cookie Two"})
    # No Authorization header set anywhere on this client -- register's
    # Set-Cookie is what /auth/me relies on here.
    r = c.get("/auth/me")
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "cookie2@example.com"


def test_refresh_rotates_token_and_invalidates_the_old_one():
    c = _fresh_client()
    c.post("/auth/register", json={"email": "cookie3@example.com", "password": "hunter22222", "name": "Cookie Three"})
    old_refresh = c.cookies.get("fe_refresh_token")
    assert old_refresh

    r = c.post("/auth/refresh")
    assert r.status_code == 200, r.text
    new_refresh = c.cookies.get("fe_refresh_token")
    assert new_refresh != old_refresh

    # Presenting the now-rotated-away token again should fail -- it was
    # revoked the moment it was used. Must overwrite the same (domain, path)
    # entry the jar already holds for this cookie, or httpx keeps both and
    # sends the current (still-valid) one instead of this stale one.
    for cookie in c.cookies.jar:
        if cookie.name == "fe_refresh_token":
            c.cookies.set("fe_refresh_token", old_refresh, domain=cookie.domain, path=cookie.path)
            break
    r = c.post("/auth/refresh")
    assert r.status_code == 401


def test_logout_revokes_refresh_token():
    c = _fresh_client()
    c.post("/auth/register", json={"email": "cookie4@example.com", "password": "hunter22222", "name": "Cookie Four"})
    refresh_token = c.cookies.get("fe_refresh_token")

    r = c.post("/auth/logout")
    assert r.status_code == 200

    c.cookies.set("fe_refresh_token", refresh_token)
    r = c.post("/auth/refresh")
    assert r.status_code == 401


def test_password_reset_revokes_all_refresh_tokens(monkeypatch):
    captured = {}

    def _fake_send(email, reset_url):
        captured["reset_url"] = reset_url

    monkeypatch.setattr("app.api.auth.send_password_reset_email", _fake_send)

    c = _fresh_client()
    c.post("/auth/register", json={"email": "cookie5@example.com", "password": "original-pw-1", "name": "Cookie Five"})
    refresh_token = c.cookies.get("fe_refresh_token")

    c.post("/auth/forgot-password", json={"email": "cookie5@example.com"})
    from urllib.parse import parse_qs, urlparse

    token = parse_qs(urlparse(captured["reset_url"]).query)["token"][0]
    r = c.post("/auth/reset-password", json={"token": token, "new_password": "brand-new-pw-1"})
    assert r.status_code == 200, r.text

    c.cookies.set("fe_refresh_token", refresh_token)
    r = c.post("/auth/refresh")
    assert r.status_code == 401


def test_login_rate_limited_after_repeated_attempts():
    # A dedicated fake source IP, so this test's count can't be pushed over
    # the edge by unrelated registrations/logins elsewhere in the suite --
    # every TestClient shares the same fake address by default since there's
    # no real network involved.
    headers = {"x-forwarded-for": "203.0.113.10"}
    c = _fresh_client()
    c.post(
        "/auth/register",
        json={"email": "ratelimited@example.com", "password": "correct-password-1", "name": "Rate Limited"},
        headers=headers,
    )

    statuses = []
    for _ in range(9):
        r = c.post("/auth/login", json={"email": "ratelimited@example.com", "password": "wrong-password"}, headers=headers)
        statuses.append(r.status_code)

    assert statuses[:8] == [401] * 8
    assert statuses[8] == 429


def test_register_rate_limited_after_repeated_attempts():
    headers = {"x-forwarded-for": "203.0.113.20"}
    c = _fresh_client()
    statuses = []
    for i in range(21):
        r = c.post("/auth/register", json={"email": f"flood{i}@example.com", "password": "hunter22222", "name": "Flood"}, headers=headers)
        statuses.append(r.status_code)

    assert statuses[:20] == [200] * 20
    assert statuses[20] == 429
