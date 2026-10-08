import pytest
from evalpulse.auth import hash_password
from evalpulse.database import SessionLocal
from evalpulse.engine import execute_run
from evalpulse.models import ProjectMember, User
from fastapi.testclient import TestClient

from tests.helpers import create_mock_run


@pytest.mark.parametrize("suffix", ["", "/results"])
def test_nonmember_cannot_read_run_data(
    authenticated_client: tuple[TestClient, dict[str, str]], suffix: str
) -> None:
    client, csrf = authenticated_client
    run = create_mock_run(
        client,
        csrf,
        [{"input": {"mock_response": "PRIVATE"}, "expected": "PRIVATE", "tags": []}],
    )
    with SessionLocal() as db:
        assert execute_run(db, run["id"]) == "completed"
        outsider = User(
            email="outsider@example.test",
            display_name="Separate reviewer",
            password_hash=hash_password("local-outsider-test-password"),
        )
        db.add(outsider)
        db.commit()
        outsider_id = outsider.id

    path = f"/api/runs/{run['id']}{suffix}"
    assert client.get(path).status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"email": "outsider@example.test", "password": "local-outsider-test-password"},
    )
    assert login.status_code == 200
    assert client.get(path).status_code == 404
    assert client.get(f"/api/runs/unknown-run{suffix}").status_code == 404

    with SessionLocal() as db:
        db.add(ProjectMember(project_id=run["project_id"], user_id=outsider_id, role="viewer"))
        db.commit()
    assert client.get(path).status_code == 200
