"""Prove destructive test setup never selects an inherited application database."""

import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_inherited_application_database_is_not_modified(tmp_path: Path) -> None:
    database = tmp_path / "application.db"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TABLE projects (marker TEXT NOT NULL)")
        connection.execute("INSERT INTO projects VALUES ('preserve application data')")

    environment = os.environ.copy()
    environment.pop("TEST_DATABASE_URL", None)
    environment["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    environment["PYTHONPATH"] = str(ROOT / "python")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy; "
            "setup = runpy.run_path('tests/conftest.py'); "
            "setup['clean_database'].__wrapped__(); "
            "from evalpulse.database import engine; engine.dispose()",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, "Disposable test setup subprocess failed"
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT marker FROM projects").fetchall() == [
            ("preserve application data",)
        ]


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///application.db",
        "postgresql+psycopg://localhost/evalpulse",
        "postgresql+psycopg://localhost/",
    ],
)
def test_explicit_test_database_rejects_non_test_targets(database_url: str) -> None:
    environment = os.environ.copy()
    environment["TEST_DATABASE_URL"] = database_url
    environment["PYTHONPATH"] = str(ROOT / "python")
    result = subprocess.run(
        [sys.executable, "-c", "import runpy; runpy.run_path('tests/conftest.py')"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert "TEST_DATABASE_URL must name a disposable PostgreSQL database ending in _test" in (
        result.stderr
    )
