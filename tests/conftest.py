import os

os.environ["DATABASE_URL"] = "sqlite:///./test_evalpulse.db"
os.environ["SESSION_SECRET"] = "test-secret-that-is-long-enough-for-tests"

import pytest
from evalpulse.api import app
from evalpulse.auth import ensure_demo_user
from evalpulse.database import Base, SessionLocal, engine
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def clean_database() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_demo_user(db)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("evalpulse.api.dispatch_pending", lambda limit=1: 0)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client: TestClient) -> tuple[TestClient, dict[str, str]]:
    response = client.post(
        "/api/auth/login",
        json={"email": "demo@evalpulse.local", "password": "evalpulse-demo"},
    )
    assert response.status_code == 200
    return client, {"X-CSRF-Token": client.cookies["evalpulse_csrf"]}
