import os
from collections.abc import Generator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

_test_directory: TemporaryDirectory[str] | None = None
_test_database_url = os.environ.get("TEST_DATABASE_URL")
if _test_database_url:
    _url = make_url(_test_database_url)
    if _url.get_backend_name() != "postgresql" or not (_url.database or "").endswith("_test"):
        raise ValueError(
            "TEST_DATABASE_URL must name a disposable PostgreSQL database ending in _test"
        )
else:
    _test_directory = TemporaryDirectory(prefix="evalpulse-tests-")
    _database_path = Path(_test_directory.name) / "test.db"
    _test_database_url = f"sqlite:///{_database_path.as_posix()}"

# Select test-owned storage before importing modules that initialize the application engine.
os.environ["DATABASE_URL"] = _test_database_url
os.environ.setdefault("SESSION_SECRET", "test-secret-that-is-long-enough-for-tests")


@pytest.fixture(scope="session", autouse=True)
def release_test_database() -> Generator[None, None, None]:
    from evalpulse.database import engine

    try:
        yield
    finally:
        engine.dispose()
        if _test_directory is not None:
            _test_directory.cleanup()


@pytest.fixture(autouse=True)
def clean_database() -> None:
    from evalpulse.auth import ensure_demo_user
    from evalpulse.database import Base, SessionLocal, engine

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_demo_user(db)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    from evalpulse.api import app

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
