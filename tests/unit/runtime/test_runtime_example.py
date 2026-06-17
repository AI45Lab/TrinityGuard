"""Runtime protection local evidence example tests."""

import json
import subprocess
import sys


def test_runtime_protection_example_writes_redacted_jsonl(tmp_path):
    output = tmp_path / "events.jsonl"
    result = subprocess.run(
        [sys.executable, "examples/runtime_protection_mvp.py", "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_protection_mvp=ok" in result.stdout
    assert "redactedinput" not in result.stdout
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    payload = "\n".join(lines)
    assert "redactedinput" not in payload
    assert "payload_ref" in payload
    decisions = [json.loads(line)["decision"]["decision"] for line in lines]
    assert decisions == ["allow", "block"]


def test_runtime_protection_example_writes_report_artifact(tmp_path):
    events = tmp_path / "events.jsonl"
    report = tmp_path / "runtime-report.json"
    result = subprocess.run(
        [
            sys.executable,
            "examples/runtime_protection_mvp.py",
            "--output",
            str(events),
            "--report-output",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_report=" in result.stdout
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "trinityguard.runtime_report.v1"
    assert payload["runtime_protection"]["summary"]["allow"] == 1
    assert payload["runtime_protection"]["summary"]["block"] == 1
    assert "redactedinput" not in report.read_text(encoding="utf-8")
