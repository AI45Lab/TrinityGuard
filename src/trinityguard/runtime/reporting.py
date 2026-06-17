"""Runtime report artifact export and verification helpers."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .events import redact_text

ARTIFACT_TYPE = "trinityguard.runtime_report.v1"
_SECRET_PATTERN = re.compile(
    r"sk-[A-Za-z0-9._-]{8,}|(?i:bearer\s+[A-Za-z0-9._-]+)|"
    r"(?i:(api[_-]?key|password|token|secret)\s*[:=]\s*(?!<redacted>)[^\s,;}]+)"
)
_DECISION_VALUES = {"allow", "monitor_only", "block"}
_BLOCK_MODE_VALUES = {"", "replace", "deny"}
_DELIVERY_ACTION_VALUES = {"", "allow", "replace", "deny"}


def summarize_runtime_decisions(decisions: list[dict[str, Any]]) -> dict[str, int]:
    """Summarize local runtime decision rows using the report artifact schema."""

    summary = {
        "total_decisions": len(decisions),
        "allow": 0,
        "monitor_only": 0,
        "block": 0,
        "failures": 0,
        "sink_errors": 0,
    }
    for decision in decisions:
        decision_name = decision.get("decision")
        if decision_name in _DECISION_VALUES:
            summary[decision_name] += 1
        if decision.get("failure"):
            summary["failures"] += 1
        if decision.get("sink_error"):
            summary["sink_errors"] += 1
    return summary


def build_runtime_report(
    *,
    enabled: bool,
    policy: dict[str, Any] | None,
    block_mode: str | None,
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a local runtime report with a shared summary implementation."""

    return {
        "enabled": bool(enabled),
        "policy": policy,
        "block_mode": block_mode,
        "summary": summarize_runtime_decisions(decisions),
        "decisions": list(decisions),
    }


def runtime_metadata_to_decision(runtime_metadata: dict[str, Any]) -> dict[str, Any]:
    """Normalize redacted runtime hook metadata into a report decision row."""

    return {
        "request_id": redact_text(runtime_metadata.get("request_id", "")),
        "decision": redact_text(runtime_metadata.get("decision", "")),
        "permitted": bool(runtime_metadata.get("permitted", False)),
        "reason": redact_text(runtime_metadata.get("reason", ""), max_length=500),
        "policy": runtime_metadata.get("policy", {}),
        "payload_ref": redact_text(runtime_metadata.get("original_payload_ref", "")),
        "delivery_action": redact_text(runtime_metadata.get("delivery_action", "")),
    }


def export_runtime_report(
    runtime_report: dict[str, Any],
    output_path: str | Path,
    *,
    source: str = "local",
) -> dict[str, Any]:
    """Write a redacted local runtime report artifact and return it."""

    sanitized_report = _sanitize_runtime_report(runtime_report)
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "created_at": time.time(),
        "source": redact_text(source, max_length=300),
        "runtime_protection": sanitized_report,
    }
    _validate_artifact(artifact)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return artifact


def verify_runtime_report_artifact(path: str | Path) -> dict[str, Any]:
    """Verify a local runtime report artifact and return compact evidence."""

    artifact_path = Path(path)
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    _validate_artifact(artifact)
    runtime = artifact["runtime_protection"]
    return {
        "valid": True,
        "artifact_type": artifact["artifact_type"],
        "path": str(artifact_path),
        "summary": runtime["summary"],
        "policy": runtime.get("policy"),
        "block_mode": runtime.get("block_mode"),
    }


def _sanitize_runtime_report(runtime_report: dict[str, Any]) -> dict[str, Any]:
    summary = dict(runtime_report.get("summary") or {})
    sanitized_decisions = [
        _sanitize_decision(decision) for decision in runtime_report.get("decisions", [])
    ]
    return {
        "enabled": bool(runtime_report.get("enabled", False)),
        "policy": _sanitize_policy(runtime_report.get("policy")),
        "block_mode": redact_text(runtime_report.get("block_mode", ""), max_length=40),
        "summary": _sanitize_summary(summary),
        "decisions": sanitized_decisions,
    }


def _sanitize_policy(policy: Any) -> dict[str, str] | None:
    if policy is None:
        return None
    return {
        "name": redact_text((policy or {}).get("name", ""), max_length=120),
        "version": redact_text((policy or {}).get("version", ""), max_length=120),
    }


def _sanitize_summary(summary: dict[str, Any]) -> dict[str, int]:
    return {
        "total_decisions": int(summary.get("total_decisions", 0)),
        "allow": int(summary.get("allow", 0)),
        "monitor_only": int(summary.get("monitor_only", 0)),
        "block": int(summary.get("block", 0)),
        "failures": int(summary.get("failures", 0)),
        "sink_errors": int(summary.get("sink_errors", 0)),
    }


def _sanitize_decision(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": redact_text(decision.get("request_id", ""), max_length=120),
        "decision": redact_text(decision.get("decision", ""), max_length=40),
        "permitted": bool(decision.get("permitted", False)),
        "reason": redact_text(decision.get("reason", ""), max_length=500),
        "policy": _sanitize_policy(decision.get("policy")) or {},
        "payload_ref": redact_text(decision.get("payload_ref", ""), max_length=120),
        "delivery_action": redact_text(decision.get("delivery_action", ""), max_length=40),
        "failure": redact_text(decision.get("failure", ""), max_length=300),
        "sink_error": redact_text(decision.get("sink_error", ""), max_length=300),
    }


def _validate_artifact(artifact: dict[str, Any]) -> None:
    if artifact.get("artifact_type") != ARTIFACT_TYPE:
        raise ValueError("runtime report artifact_type is invalid")
    serialized = json.dumps(artifact, ensure_ascii=False, sort_keys=True)
    if _SECRET_PATTERN.search(serialized):
        raise ValueError("runtime report artifact contains secret-like content")

    runtime = artifact.get("runtime_protection")
    if not isinstance(runtime, dict):
        raise ValueError("runtime report artifact missing runtime_protection")
    block_mode = runtime.get("block_mode", "")
    if block_mode not in _BLOCK_MODE_VALUES:
        raise ValueError(f"runtime report block_mode is invalid: {block_mode}")
    summary = runtime.get("summary")
    decisions = runtime.get("decisions")
    if not isinstance(summary, dict) or not isinstance(decisions, list):
        raise ValueError("runtime report artifact missing summary or decisions")
    _validate_summary(summary, decisions)


def _validate_summary(summary: dict[str, Any], decisions: list[dict[str, Any]]) -> None:
    counts = {"allow": 0, "monitor_only": 0, "block": 0}
    failures = 0
    sink_errors = 0
    for decision in decisions:
        decision_name = decision.get("decision")
        if decision_name not in _DECISION_VALUES:
            raise ValueError(f"runtime report decision is invalid: {decision_name}")
        delivery_action = decision.get("delivery_action", "")
        if delivery_action not in _DELIVERY_ACTION_VALUES:
            raise ValueError(f"runtime report delivery_action is invalid: {delivery_action}")
        counts[decision_name] += 1
        if decision.get("failure"):
            failures += 1
        if decision.get("sink_error"):
            sink_errors += 1
    expected = {
        "total_decisions": len(decisions),
        "allow": counts["allow"],
        "monitor_only": counts["monitor_only"],
        "block": counts["block"],
        "failures": failures,
        "sink_errors": sink_errors,
    }
    for key, value in expected.items():
        if int(summary.get(key, -1)) != value:
            raise ValueError(f"runtime report summary mismatch for {key}")
