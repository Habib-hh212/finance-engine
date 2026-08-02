def test_register_then_me(client):
    r = client.post("/auth/register", json={"email": "alice@example.com", "password": "hunter22", "name": "Alice"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "alice@example.com"
    assert r.json()["name"] == "Alice"


def test_register_duplicate_email_rejected(client):
    client.post("/auth/register", json={"email": "bob@example.com", "password": "hunter22", "name": "Bob"})
    r = client.post("/auth/register", json={"email": "bob@example.com", "password": "different", "name": "Bob2"})
    assert r.status_code == 409


def test_login_success_and_wrong_password(client):
    client.post("/auth/register", json={"email": "carol@example.com", "password": "correct-horse", "name": "Carol"})

    r = client.post("/auth/login", json={"email": "carol@example.com", "password": "correct-horse"})
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()

    r = client.post("/auth/login", json={"email": "carol@example.com", "password": "wrong-password"})
    assert r.status_code == 401

    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever"})
    assert r.status_code == 401


def test_protected_endpoint_rejects_without_token():
    # Use a plain, header-less client so we don't inherit the shared fixture's Authorization header.
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as bare_client:
        r = bare_client.get("/companies")
        assert r.status_code == 401


def test_protected_endpoint_rejects_bogus_token():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as bare_client:
        r = bare_client.get("/companies", headers={"Authorization": "Bearer not-a-real-token"})
        assert r.status_code == 401


def test_protected_endpoint_accepts_valid_token(client):
    r = client.get("/companies")
    assert r.status_code == 200
