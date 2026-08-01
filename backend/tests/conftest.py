import os
import pathlib

_TEST_DB = pathlib.Path(__file__).parent / "_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
    if _TEST_DB.exists():
        _TEST_DB.unlink()


@pytest.fixture()
def company(client):
    r = client.post("/companies", json={"name": "Test Co", "base_currency": "USD"})
    assert r.status_code == 200, r.text
    return r.json()
