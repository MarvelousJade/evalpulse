import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts.measure_resume import main


def test_existing_evidence_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "evidence.json"
    output.write_text("existing evidence", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["measure_resume.py", "--output", str(output)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert output.read_text(encoding="utf-8") == "existing evidence"


def test_measurement_forces_local_storage_and_disables_live_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "evidence.json"
    monkeypatch.setattr(sys, "argv", ["measure_resume.py", "--output", str(output)])
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://placeholder/disposable_test")
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        environment = kwargs["env"]
        assert "TEST_DATABASE_URL" not in environment
        assert environment["LLM_ENABLED"] == "false"
        assert environment["GEMINI_API_KEY"] == ""
        Path(environment["EVALPULSE_EVIDENCE_OUTPUT"]).write_text(
            '{"verified": true}', encoding="utf-8"
        )
        return subprocess.CompletedProcess(command, 0, "measurement passed\n", "")

    monkeypatch.setattr("scripts.measure_resume.subprocess.run", run)
    monkeypatch.setattr("scripts.measure_resume.subprocess.check_output", lambda *a, **k: "test\n")
    assert main() == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["measurements"] == {"verified": True}
    assert report["source_sha256"]["scripts/measure_resume.py"]
    assert report["pytest_stdout"] == "measurement passed\n"


def test_failed_measurement_does_not_publish_success_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "evidence.json"
    monkeypatch.setattr(sys, "argv", ["measure_resume.py", "--output", str(output)])
    monkeypatch.setattr(
        "scripts.measure_resume.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, "failed\n", ""),
    )
    assert main() == 1
    assert not output.exists()
