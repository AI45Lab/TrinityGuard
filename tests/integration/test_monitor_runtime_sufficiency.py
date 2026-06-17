from __future__ import annotations

from trinityguard.level2_intermediary.structured_logging import AgentStepLog
from trinityguard.level3_safety.benchmark.paper_standard import (
    build_paper_standard_readiness_report,
)
from trinityguard.level3_safety.benchmark.validation import MINSET_RISK_LEVELS
from trinityguard.level3_safety.monitor_orchestration import (
    build_monitor_observation,
    summarize_observations,
)
from trinityguard.level3_safety.monitors_base_ref import Alert


def _base_summary() -> dict:
    return {
        "risk_case_realism": {
            "passed": True,
            "risks": {
                risk: {"passed": True, "case_count": 1, "invalid_cases": []}
                for risk in MINSET_RISK_LEVELS
            },
        },
        "runtime_effect": {
            "passed": True,
            "risks": {
                "message_tampering": {
                    "passed": True,
                    "runtime_effective_cases": 1,
                    "static_only_cases": 0,
                },
                "cascading_failures": {
                    "passed": True,
                    "runtime_effective_cases": 1,
                    "static_only_cases": 0,
                },
            },
        },
        "judge_validity_and_sufficiency": {
            "passed": True,
            "strict_parse_failures": 0,
            "inconclusive": 0,
            "insufficient_evidence": 0,
            "truncated_without_refs": 0,
        },
        "predeployment_runtime_modules": {
            "passed": True,
            "predeployment_gate_passed": True,
            "runtime_gate_passed": True,
            "delivery_actions": ["allow", "replace", "deny"],
            "runtime_hook_evidence_count": 3,
        },
        "production_ready": False,
        "formal_external_comparison_ready": False,
    }


def _entry(risk: str, *, content: str, include_route: bool = True, trace_truncated: bool = False):
    metadata = {
        "message_id": f"{risk}-id",
        "attack_type": risk,
        "level": MINSET_RISK_LEVELS[risk],
        "trace_truncated": trace_truncated,
    }
    if include_route:
        metadata.update({"from": "planner", "to": "executor"})
    return AgentStepLog(
        timestamp=1.0,
        agent_name="executor",
        step_type="receive",
        content=content,
        metadata=metadata,
    )


def _monitor_gate_from_artifacts(artifacts: list[dict]) -> dict:
    counts, invalid, missing = summarize_observations(artifacts, minset_risks=list(MINSET_RISK_LEVELS))
    return {
        "passed": invalid == 0
        and missing == []
        and all(
            row.get("alert", 0) > 0 and row.get("non_alert", 0) > 0 and row.get("insufficient", 0) == 0
            for row in counts.values()
        ),
        "risks": {
            risk: {
                "passed": row.get("alert", 0) > 0
                and row.get("non_alert", 0) > 0
                and row.get("insufficient", 0) == 0,
                "observations": row,
            }
            for risk, row in counts.items()
        },
        "invalid_observation_artifacts": invalid,
        "missing_required_observations": missing,
        "observation_artifacts": artifacts,
    }


def test_minset_attack_trace_emits_alert_observation_for_each_risk():
    artifacts = []
    for risk in MINSET_RISK_LEVELS:
        artifacts.append(
            build_monitor_observation(
                log_entry=_entry(risk, content="runtime trigger"),
                risk_type=risk,
                monitor_name=risk,
                monitor_strategy="pattern_based",
                judge_backed=False,
                observation_type="alert",
                alert=Alert(
                    severity="warning",
                    risk_type=risk,
                    message="detected",
                    recommended_action="warn",
                    detection_reason="keyword",
                ),
                step_index=1,
            )
        )
        artifacts.append(
            build_monitor_observation(
                log_entry=_entry(risk, content="benign trace"),
                risk_type=risk,
                monitor_name=risk,
                monitor_strategy="pattern_based",
                judge_backed=False,
                observation_type=None,
                alert=None,
                step_index=2,
            )
        )

    summary = _base_summary()
    summary["monitor_effectiveness_and_sufficiency"] = _monitor_gate_from_artifacts(artifacts)

    report = build_paper_standard_readiness_report(summary=summary, unit_tests_passed=True)

    assert report["paper_standard_research_ready"] is True


def test_missing_content_trace_emits_insufficient_and_blocks_readiness():
    artifacts = []
    for risk in MINSET_RISK_LEVELS:
        artifacts.append(
            build_monitor_observation(
                log_entry=_entry(risk, content="runtime trigger"),
                risk_type=risk,
                monitor_name=risk,
                monitor_strategy="pattern_based",
                judge_backed=False,
                observation_type="alert",
                alert=Alert(
                    severity="warning",
                    risk_type=risk,
                    message="detected",
                    recommended_action="warn",
                    detection_reason="keyword",
                ),
                step_index=1,
            )
        )
        artifacts.append(
            build_monitor_observation(
                log_entry=_entry(risk, content="", include_route=False),
                risk_type=risk,
                monitor_name=risk,
                monitor_strategy="pattern_based",
                judge_backed=False,
                observation_type="insufficient",
                alert=None,
                step_index=2,
                insufficiency_reason="missing content and route",
            )
        )

    summary = _base_summary()
    summary["monitor_effectiveness_and_sufficiency"] = _monitor_gate_from_artifacts(artifacts)

    report = build_paper_standard_readiness_report(summary=summary, unit_tests_passed=True)

    assert report["paper_standard_research_ready"] is False
    assert "monitor_effectiveness_and_sufficiency" in report["blocking_criteria"]


def test_truncated_trace_emits_insufficient_and_blocks_readiness():
    artifacts = []
    for risk in MINSET_RISK_LEVELS:
        artifacts.append(
            build_monitor_observation(
                log_entry=_entry(risk, content="runtime trigger"),
                risk_type=risk,
                monitor_name=risk,
                monitor_strategy="pattern_based",
                judge_backed=False,
                observation_type="alert",
                alert=Alert(
                    severity="warning",
                    risk_type=risk,
                    message="detected",
                    recommended_action="warn",
                    detection_reason="keyword",
                ),
                step_index=1,
            )
        )
        artifacts.append(
            build_monitor_observation(
                log_entry=_entry(risk, content="benign trace", trace_truncated=True),
                risk_type=risk,
                monitor_name=risk,
                monitor_strategy="pattern_based",
                judge_backed=False,
                observation_type=None,
                alert=None,
                step_index=2,
            )
        )

    summary = _base_summary()
    summary["monitor_effectiveness_and_sufficiency"] = _monitor_gate_from_artifacts(artifacts)

    report = build_paper_standard_readiness_report(summary=summary, unit_tests_passed=True)

    assert report["paper_standard_research_ready"] is False
    assert "monitor_effectiveness_and_sufficiency" in report["blocking_criteria"]
