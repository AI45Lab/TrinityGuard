"""Runtime MVP validation/readiness gate for local Phase 2 evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .reporting import verify_runtime_report_artifact

REQUIRED_DECISIONS = {"allow", "monitor_only", "block"}
REQUIRED_BLOCK_MODES = {"replace", "deny"}
REQUIRED_FAILURE_MODES = {"fail_open", "fail_closed"}
REQUIRED_NON_GOALS = {"production deployment", "Garak/OpenRT comparison"}
MATRIX_TYPE = "trinityguard.runtime_policy_matrix.v1"


def build_runtime_mvp_validation_report(
    summary: str | Path | dict[str, Any],
    *,
    unit_tests_passed: bool,
    phase1_minset_ready: bool,
    phase1_extension_ready: bool,
) -> dict[str, Any]:
    """Validate the local runtime MVP evidence matrix without production claims."""

    summary_data = _load_summary(summary)
    blocking: list[str] = []

    if summary_data.get("matrix_type") != MATRIX_TYPE:
        blocking.append("matrix_type")
    if not summary_data.get("runtime_mvp_ready"):
        blocking.append("matrix_runtime_ready")
    if not unit_tests_passed:
        blocking.append("unit_tests")
    if not phase1_minset_ready:
        blocking.append("phase1_minset")
    if not phase1_extension_ready:
        blocking.append("phase1_extension")

    policies = summary_data.get("policies", [])
    verified_artifacts = _verify_artifacts(policies, blocking)
    if int(summary_data.get("verified_artifacts", -1)) != len(policies):
        blocking.append("verified_artifact_count")
    if int(summary_data.get("total_artifacts", -1)) != len(policies):
        blocking.append("total_artifact_count")

    coverage = summary_data.get("coverage", {})
    if set(coverage.get("decisions", [])) != REQUIRED_DECISIONS:
        blocking.append("decision_coverage")
    if set(coverage.get("block_modes", [])) != REQUIRED_BLOCK_MODES:
        blocking.append("block_mode_coverage")
    if set(coverage.get("failure_modes", [])) != REQUIRED_FAILURE_MODES:
        blocking.append("failure_mode_coverage")
    if set(summary_data.get("non_goals", [])) != REQUIRED_NON_GOALS:
        blocking.append("non_goals")

    return {
        "report_type": "trinityguard.runtime_mvp_validation.v1",
        "runtime_mvp_ready": not blocking,
        "blocking_criteria": sorted(set(blocking)),
        "validated_artifacts": verified_artifacts,
        "coverage": {
            "decisions": sorted(coverage.get("decisions", [])),
            "block_modes": sorted(coverage.get("block_modes", [])),
            "failure_modes": sorted(coverage.get("failure_modes", [])),
        },
        "unit_tests_passed": bool(unit_tests_passed),
        "phase1_minset_ready": bool(phase1_minset_ready),
        "phase1_extension_ready": bool(phase1_extension_ready),
        "non_goals": sorted(summary_data.get("non_goals", [])),
    }


def _load_summary(summary: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(summary, dict):
        return dict(summary)
    return json.loads(Path(summary).read_text(encoding="utf-8"))


def _verify_artifacts(policies: list[dict[str, Any]], blocking: list[str]) -> int:
    verified = 0
    for policy in policies:
        artifact = policy.get("artifact")
        if not artifact:
            blocking.append("missing_artifact_path")
            continue
        try:
            verify_runtime_report_artifact(artifact)
        except Exception:
            blocking.append("artifact_verification")
            continue
        verified += 1
    return verified
