"""Report builders for the local Safety_MAS compatibility façade."""

from __future__ import annotations

from typing import Any

from ..utils.message_utils import resolve_nested_messages
from .monitors_base_ref import Alert


def build_test_report(test_results: dict[str, Any]) -> str:
    """Build the legacy human-readable safety-test report."""

    if not test_results:
        return "No test results available. Run tests first."

    report_lines = ["=" * 60, "MAS Safety Test Report", "=" * 60, ""]

    for test_name, result in test_results.items():
        if "error" in result:
            report_lines.append(f"[FAIL] {test_name}: ERROR - {result['error']}")
            continue

        passed = result.get("passed", False)
        total = result.get("total_cases", 0)
        failed = result.get("failed_cases", 0)
        pass_rate = result.get("pass_rate", 0) * 100

        status = "[PASS]" if passed else "[FAIL]"
        report_lines.append(f"{status} {test_name}")
        report_lines.append(f"  Cases: {total}, Failed: {failed}, Pass Rate: {pass_rate:.1f}%")

        severity_summary = result.get("severity_summary", {})
        if any(severity_summary.values()):
            report_lines.append(f"  Severity: {severity_summary}")

        report_lines.append("")

    report_lines.append("=" * 60)
    return "\n".join(report_lines)


def build_comprehensive_report(
    *,
    test_results: dict[str, Any],
    risk_profiles: dict[str, dict],
    alerts: list[Alert],
    runtime_protection: dict[str, Any],
    active_monitor_count: int,
) -> dict[str, Any]:
    """Build the comprehensive Safety_MAS report schema."""

    report = {
        "test_results": test_results,
        "risk_profiles": risk_profiles,
        "alerts": [alert.to_dict() for alert in alerts],
        "runtime_protection": runtime_protection,
        "summary": {
            "tests_run": len(test_results),
            "tests_passed": sum(
                1
                for result in test_results.values()
                if isinstance(result, dict) and result.get("passed", False)
            ),
            "active_monitors": active_monitor_count,
            "total_alerts": len(alerts),
            "critical_alerts": sum(1 for alert in alerts if alert.severity == "critical"),
        },
    }
    return resolve_nested_messages(report)


def build_paper_standard_report(
    *,
    risk_results: list[dict[str, Any]],
    monitor_alerts: list[dict[str, Any]],
    runtime_protection: dict[str, Any],
    readiness_flags: dict[str, bool],
    notes: str | None = None,
) -> dict[str, Any]:
    """Build a redacted-by-default local paper-standard research report."""

    from datetime import UTC, datetime

    report = {
        "artifact_type": "trinityguard.paper_standard_report.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "local_offline_research_framework",
        "redaction": {
            "raw_payloads_included": False,
            "payload_reference_strategy": "sha256_refs_or_redacted_summaries",
        },
        "readiness_flags": {
            "fixture_smoke_ready": bool(readiness_flags.get("fixture_smoke_ready", False)),
            "local_research_ready": bool(readiness_flags.get("local_research_ready", False)),
            "paper_design_goal_ready": bool(readiness_flags.get("paper_design_goal_ready", False)),
            "paper_strong_alignment_ready": bool(
                readiness_flags.get("paper_strong_alignment_ready", False)
            ),
            "paper_standard_research_ready": bool(
                readiness_flags.get("paper_standard_research_ready", False)
                or readiness_flags.get("paper_design_goal_ready", False)
            ),
            "production_ready": bool(readiness_flags.get("production_ready", False)),
            "release_ready": bool(readiness_flags.get("release_ready", False)),
            "formal_external_comparison_ready": bool(
                readiness_flags.get("formal_external_comparison_ready", False)
            ),
        },
        "metrics": _paper_metrics(_sanitize_report_rows(risk_results)),
        "risk_results": _sanitize_report_rows(risk_results),
        "monitoring": {
            "total_alerts": len(monitor_alerts),
            "alerts": _sanitize_report_rows(monitor_alerts),
        },
        "runtime_protection": _sanitize_report_value(runtime_protection),
        "non_goals": {
            "production_deployment": True,
            "production_telemetry": True,
            "formal_external_comparison": True,
        },
    }
    if notes:
        from trinityguard.runtime.events import redact_text

        report["notes"] = redact_text(notes, max_length=1_000)
    return report


def validate_paper_standard_report(report: dict[str, Any]) -> None:
    """Validate the local paper-standard report and anti-overclaim gates."""

    required = {
        "artifact_type",
        "scope",
        "redaction",
        "readiness_flags",
        "metrics",
        "risk_results",
        "monitoring",
        "runtime_protection",
        "non_goals",
    }
    missing = required - set(report)
    if missing:
        raise ValueError(f"paper-standard report missing required keys: {sorted(missing)}")
    if report["artifact_type"] != "trinityguard.paper_standard_report.v1":
        raise ValueError("invalid paper-standard report artifact_type")
    flags = report.get("readiness_flags") or {}
    if flags.get("production_ready") is True:
        raise ValueError("production_ready must remain false for local paper-standard report")
    if flags.get("release_ready") is True:
        raise ValueError("release_ready must remain false for local paper-standard report")
    if flags.get("formal_external_comparison_ready") is True:
        raise ValueError(
            "formal_external_comparison_ready must remain false without comparison gate"
        )
    redaction = report.get("redaction") or {}
    if redaction.get("raw_payloads_included") is not False:
        raise ValueError("paper-standard reports must be redacted-by-default")
    if _contains_secret_like(report):
        raise ValueError("paper-standard report contains secret-like content")


_RAW_PAYLOAD_KEYS = {
    "attack_input": "input_payload",
    "raw_response": "output_payload",
    "agent_response": "output_payload",
    "source_message": "trace_payload",
    "message": "trace_payload",
    "messages": "trace_payload",
    "content": "trace_payload",
}


def _sanitize_report_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_sanitize_report_value(row) for row in rows]


def _sanitize_report_value(value: Any) -> Any:
    from trinityguard.runtime.events import redact_text

    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text in _RAW_PAYLOAD_KEYS:
                sanitized[_RAW_PAYLOAD_KEYS[key_text]] = _payload_ref_only(item)
            else:
                sanitized[key_text] = _sanitize_report_value(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_report_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_report_value(item) for item in value]
    if isinstance(value, str):
        return redact_text(value, max_length=1_000)
    return value


def _payload_ref_only(value: Any) -> dict[str, str]:
    from trinityguard.runtime.events import payload_hash

    digest = payload_hash(value)
    return {"payload_sha256": digest, "payload_ref": f"sha256:{digest}"}


def _paper_metrics(risk_results: list[dict[str, Any]]) -> dict[str, Any]:
    total_cases = sum(int(row.get("total_cases", 0) or 0) for row in risk_results)
    risk_detected = sum(int(row.get("risk_detected", 0) or 0) for row in risk_results)
    inconclusive = sum(int(row.get("inconclusive", 0) or 0) for row in risk_results)
    by_risk = {str(row.get("risk")): row for row in risk_results}
    by_tier: dict[str, dict[str, int]] = {}
    by_granularity: dict[str, dict[str, int]] = {}
    for row in risk_results:
        tier = str(row.get("tier", "unknown"))
        bucket = by_tier.setdefault(tier, {"total_cases": 0, "risk_detected": 0, "inconclusive": 0})
        bucket["total_cases"] += int(row.get("total_cases", 0) or 0)
        bucket["risk_detected"] += int(row.get("risk_detected", 0) or 0)
        bucket["inconclusive"] += int(row.get("inconclusive", 0) or 0)

        granularity = str(row.get("target_granularity") or row.get("granularity") or "unknown")
        granularity_bucket = by_granularity.setdefault(
            granularity, {"total_cases": 0, "risk_detected": 0, "inconclusive": 0}
        )
        granularity_bucket["total_cases"] += int(row.get("total_cases", 0) or 0)
        granularity_bucket["risk_detected"] += int(row.get("risk_detected", 0) or 0)
        granularity_bucket["inconclusive"] += int(row.get("inconclusive", 0) or 0)
    return {
        "total_cases": total_cases,
        "risk_detected": risk_detected,
        "inconclusive": inconclusive,
        "risk_rate": risk_detected / total_cases if total_cases else 0.0,
        "by_risk": by_risk,
        "by_tier": by_tier,
        "by_granularity": by_granularity,
    }


def _contains_secret_like(value: Any) -> bool:
    import re

    text = str(value)
    patterns = [
        re.compile(r"sk-[A-Za-z0-9._-]{20,}"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"),
        re.compile(
            r"(?i)(api[_-]?key|password|token|secret)\s*[=:]\s*(?!<redacted>|sha256:)[^\s,;}']+"
        ),
    ]
    return any(pattern.search(text) for pattern in patterns)
