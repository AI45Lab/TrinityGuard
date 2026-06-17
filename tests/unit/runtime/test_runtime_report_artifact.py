"""Runtime report artifact exporter/verifier tests."""

import json
from pathlib import Path

import pytest

from trinityguard.runtime.reporting import (
    build_runtime_report,
    export_runtime_report,
    runtime_metadata_to_decision,
    summarize_runtime_decisions,
    verify_runtime_report_artifact,
)


def runtime_report() -> dict:
    return {
        "enabled": True,
        "policy": {"name": "trinityguard-runtime-mvp", "version": "phase2-mvp"},
        "block_mode": "deny",
        "summary": {
            "total_decisions": 2,
            "allow": 1,
            "monitor_only": 0,
            "block": 1,
            "failures": 0,
            "sink_errors": 0,
        },
        "decisions": [
            {
                "request_id": "req-allow",
                "decision": "allow",
                "permitted": True,
                "reason": "safe",
                "policy": {"name": "trinityguard-runtime-mvp", "version": "phase2-mvp"},
                "payload_ref": "sha256:" + "a" * 64,
                "delivery_action": "allow",
            },
            {
                "request_id": "req-block",
                "decision": "block",
                "permitted": False,
                "reason": "blocked TOKEN=artifact-secret",
                "policy": {"name": "trinityguard-runtime-mvp", "version": "phase2-mvp"},
                "payload_ref": "sha256:" + "b" * 64,
                "delivery_action": "deny",
            },
        ],
    }


def test_export_runtime_report_artifact_is_redacted_and_verifiable(tmp_path: Path):
    output = tmp_path / "runtime-report.json"

    artifact = export_runtime_report(
        runtime_report(),
        output,
        source="unit-test TOKEN=artifact-secret",
    )
    verified = verify_runtime_report_artifact(output)

    serialized = json.dumps(artifact) + output.read_text(encoding="utf-8")
    assert "artifact-secret" not in serialized
    assert artifact["artifact_type"] == "trinityguard.runtime_report.v1"
    assert artifact["source"] == "unit-test TOKEN=<redacted>"
    assert artifact["runtime_protection"]["summary"]["block"] == 1
    assert artifact["runtime_protection"]["block_mode"] == "deny"
    assert [item["delivery_action"] for item in artifact["runtime_protection"]["decisions"]] == [
        "allow",
        "deny",
    ]
    assert verified["valid"] is True
    assert verified["summary"] == artifact["runtime_protection"]["summary"]


def test_build_runtime_report_summarizes_decisions_for_local_callers():
    decisions = [
        {
            "request_id": "req-allow",
            "decision": "allow",
            "permitted": True,
            "reason": "safe",
            "policy": {"name": "p", "version": "v"},
            "payload_ref": "sha256:" + "a" * 64,
            "delivery_action": "allow",
        },
        {
            "request_id": "req-block",
            "decision": "block",
            "permitted": False,
            "reason": "blocked",
            "policy": {"name": "p", "version": "v"},
            "payload_ref": "sha256:" + "b" * 64,
            "delivery_action": "replace",
            "failure": "judge failed",
            "sink_error": "sink failed",
        },
        {
            "request_id": "req-monitor",
            "decision": "monitor_only",
            "permitted": True,
            "reason": "monitor",
            "policy": {"name": "p", "version": "v"},
            "payload_ref": "sha256:" + "c" * 64,
            "delivery_action": "allow",
        },
    ]

    assert summarize_runtime_decisions(decisions) == {
        "total_decisions": 3,
        "allow": 1,
        "monitor_only": 1,
        "block": 1,
        "failures": 1,
        "sink_errors": 1,
    }
    assert build_runtime_report(
        enabled=True,
        policy={"name": "p", "version": "v"},
        block_mode="replace",
        decisions=decisions,
    ) == {
        "enabled": True,
        "policy": {"name": "p", "version": "v"},
        "block_mode": "replace",
        "summary": {
            "total_decisions": 3,
            "allow": 1,
            "monitor_only": 1,
            "block": 1,
            "failures": 1,
            "sink_errors": 1,
        },
        "decisions": decisions,
    }


def test_runtime_metadata_to_decision_normalizes_and_redacts_hook_metadata():
    decision = runtime_metadata_to_decision(
        {
            "request_id": "req TOKEN=metadata-secret",
            "decision": "block",
            "permitted": False,
            "reason": "blocked TOKEN=reason-secret",
            "policy": {"name": "p", "version": "v"},
            "original_payload_ref": "sha256:" + "a" * 64,
            "delivery_action": "deny",
        }
    )

    assert decision == {
        "request_id": "req TOKEN=<redacted>",
        "decision": "block",
        "permitted": False,
        "reason": "blocked TOKEN=<redacted>",
        "policy": {"name": "p", "version": "v"},
        "payload_ref": "sha256:" + "a" * 64,
        "delivery_action": "deny",
    }


def test_verify_runtime_report_rejects_summary_mismatch(tmp_path: Path):
    output = tmp_path / "runtime-report.json"
    artifact = export_runtime_report(runtime_report(), output)
    artifact["runtime_protection"]["summary"]["total_decisions"] = 999
    output.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="summary"):
        verify_runtime_report_artifact(output)


def test_verify_runtime_report_rejects_raw_secret_like_artifact(tmp_path: Path):
    output = tmp_path / "runtime-report.json"
    artifact = export_runtime_report(runtime_report(), output)
    artifact["runtime_protection"]["decisions"][0]["reason"] = "Bearer artifact-secret"
    output.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="secret-like"):
        verify_runtime_report_artifact(output)


def test_verify_runtime_report_rejects_invalid_delivery_action(tmp_path: Path):
    output = tmp_path / "runtime-report.json"
    artifact = export_runtime_report(runtime_report(), output)
    artifact["runtime_protection"]["decisions"][0]["delivery_action"] = "silently_drop"
    output.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="delivery_action"):
        verify_runtime_report_artifact(output)


def test_verify_runtime_report_rejects_invalid_block_mode(tmp_path: Path):
    output = tmp_path / "runtime-report.json"
    artifact = export_runtime_report(runtime_report(), output)
    artifact["runtime_protection"]["block_mode"] = "silent"
    output.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="block_mode"):
        verify_runtime_report_artifact(output)
