"""Runtime report artifact verifier CLI tests."""

import json
import subprocess
import sys

from tests.unit.runtime.test_runtime_report_artifact import runtime_report
from trinityguard.runtime.reporting import export_runtime_report


def test_verify_runtime_report_artifact_cli_accepts_valid_report(tmp_path):
    artifact_path = tmp_path / "runtime-report.json"
    export_runtime_report(runtime_report(), artifact_path, source="cli-test")

    result = subprocess.run(
        [sys.executable, "examples/verify_runtime_report_artifact.py", str(artifact_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["summary"]["block"] == 1
    assert payload["path"] == str(artifact_path)


def test_verify_runtime_report_artifact_cli_rejects_invalid_report(tmp_path):
    artifact_path = tmp_path / "runtime-report.json"
    artifact = export_runtime_report(runtime_report(), artifact_path, source="cli-test")
    artifact["runtime_protection"]["summary"]["block"] = 99
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "examples/verify_runtime_report_artifact.py", str(artifact_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "runtime_report_artifact=invalid" in result.stderr
