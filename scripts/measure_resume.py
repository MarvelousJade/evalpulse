"""Measure local mock execution using pytest's disposable database fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New JSON evidence file")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("output already exists; choose a new filename to preserve earlier evidence")
    sources = sorted(
        [ROOT / "pyproject.toml", Path(__file__).resolve()]
        + list((ROOT / "python/evalpulse").glob("*.py"))
        + list((ROOT / "tests").rglob("*.py"))
    )
    hashes = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sources
    }
    environment = dict(os.environ)
    # Never inherit an opt-in destructive PostgreSQL test target for this local benchmark.
    environment.pop("TEST_DATABASE_URL", None)
    environment.update(LLM_ENABLED="false", GEMINI_API_KEY="")
    with TemporaryDirectory(prefix="evalpulse-evidence-") as directory:
        payload = Path(directory) / "measurements.json"
        environment["EVALPULSE_EVIDENCE_OUTPUT"] = str(payload)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/benchmarks/test_resume_evidence.py", "-v"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        if result.returncode:
            return result.returncode
        measurements = json.loads(payload.read_text(encoding="utf-8"))
    report = {
        "schema_version": 1,
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True
        ).splitlines(),
        "source_sha256": hashes,
        "environment": {
            "python": platform.python_version(),
            "os": platform.platform(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "packages": {
                name: version(name)
                for name in ["evalpulse", "pytest", "fastapi", "sqlalchemy", "pydantic", "httpx"]
            },
            "database": "disposable file-backed SQLite; default fixture settings",
            "execution": "direct engine; one process; dispatch stubbed; no broker or live model",
        },
        "pytest_stdout": result.stdout,
        "pytest_stderr": result.stderr,
        "measurements": measurements,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(f"Evidence saved to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
