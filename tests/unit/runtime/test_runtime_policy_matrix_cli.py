"""Runtime policy matrix CLI tests for academic/local experiments."""

import json
import subprocess
import sys


def test_runtime_policy_matrix_cli_exports_verified_artifacts(tmp_path):
    output_dir = tmp_path / "matrix"
    result = subprocess.run(
        [
            sys.executable,
            "examples/runtime_policy_matrix.py",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_policy_matrix=ok" in result.stdout
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_artifacts"] == 6
    assert summary["verified_artifacts"] == 6
    assert summary["runtime_mvp_ready"] is True
    assert summary["coverage"] == {
        "decisions": ["allow", "block", "monitor_only"],
        "block_modes": ["deny", "replace"],
        "failure_modes": ["fail_closed", "fail_open"],
    }
    assert summary["non_goals"] == [
        "production deployment",
        "Garak/OpenRT comparison",
    ]
    by_policy = {item["policy_name"]: item for item in summary["policies"]}
    assert by_policy["runtime-mvp-default"]["summary"]["block"] == 1
    assert by_policy["runtime-mvp-monitor-only"]["summary"]["monitor_only"] == 1
    assert by_policy["runtime-mvp-fail-closed"]["summary"]["block"] == 1
    assert by_policy["runtime-mvp-warning-block"]["summary"]["block"] == 1
    assert by_policy["runtime-mvp-resilient-local"]["summary"]["failures"] >= 2
    assert by_policy["runtime-mvp-deny-local"]["block_mode"] == "deny"
    assert by_policy["runtime-mvp-deny-local"]["summary"]["block"] == 1
    default_artifact = json.loads(
        (output_dir / "runtime-mvp-default" / "runtime-report.json").read_text(encoding="utf-8")
    )
    assert {
        item["delivery_action"] for item in default_artifact["runtime_protection"]["decisions"]
    } == {"allow", "replace"}

    combined = result.stdout + (output_dir / "summary.json").read_text(encoding="utf-8")
    assert "matrix-secret" not in combined


def test_runtime_mvp_validation_cli_accepts_policy_matrix(tmp_path):
    output_dir = tmp_path / "matrix"
    subprocess.run(
        [
            sys.executable,
            "examples/runtime_policy_matrix.py",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "examples/validate_runtime_mvp.py",
            "--summary",
            str(output_dir / "summary.json"),
            "--unit-tests-passed",
            "--phase1-minset-ready",
            "--phase1-extension-ready",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_mvp_validation=ready" in result.stdout
    payload = json.loads(result.stdout.splitlines()[-1])
    assert payload["runtime_mvp_ready"] is True
    assert payload["blocking_criteria"] == []
    assert payload["validated_artifacts"] == 6
