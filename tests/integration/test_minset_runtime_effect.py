from __future__ import annotations

from trinityguard.level3_safety.attacks.base import AttackCaseResult
from trinityguard.level3_safety.benchmark.paper_standard import (
    build_paper_standard_readiness_report,
)
from trinityguard.level3_safety.benchmark.validation import MINSET_RISK_LEVELS
from trinityguard.level3_safety.judges.evidence import build_judge_evidence_package


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
        "monitor_effectiveness_and_sufficiency": {
            "passed": True,
            "risks": {
                risk: {
                    "passed": True,
                    "observations": {"alert": 1, "non_alert": 1, "insufficient": 0},
                }
                for risk in MINSET_RISK_LEVELS
            },
            "invalid_observation_artifacts": 0,
            "missing_required_observations": [],
        },
        "production_ready": False,
        "formal_external_comparison_ready": False,
    }


def test_message_tampering_runtime_effect_has_original_modified_and_consumed_message():
    result = AttackCaseResult(
        attack_type="message_tampering",
        case_name="tamper-1",
        attack_input="before",
        target_agent="executor",
        raw_response="after",
        execution_success=True,
        expected_behavior="reject",
        severity="warning",
        metadata={
            "trace": {
                "agent_steps": [{"agent_name": "executor", "metadata": {"from": "planner"}}],
                "interceptions": [
                    {"original_content": "before", "modified_content": "after"},
                ],
            },
            "tampering": {"source_agent": "planner", "target_agent": "executor"},
        },
    )

    package = build_judge_evidence_package(result=result, tier="l2")

    assert package.runtime_effect_markers["message_tampering"]["original_message_present"] is True
    assert package.runtime_effect_markers["message_tampering"]["modified_message_present"] is True
    assert package.runtime_effect_markers["message_tampering"]["downstream_consumed"] is True


def test_cascading_failures_runtime_effect_has_multi_agent_propagation_chain():
    result = AttackCaseResult(
        attack_type="cascading_failures",
        case_name="cascade-1",
        attack_input="seed",
        target_agent=None,
        raw_response="error",
        execution_success=True,
        expected_behavior="contain",
        severity="critical",
        metadata={
            "trace": {
                "agent_steps": [
                    {"agent_name": "executor", "metadata": {"from": "planner"}},
                    {"agent_name": "reviewer", "metadata": {"from": "executor"}},
                ],
            },
            "cascade": {"failure_type": "retry_loop"},
        },
    )

    package = build_judge_evidence_package(result=result, tier="l3")

    assert package.runtime_effect_markers["cascading_failures"]["multi_agent_propagation"] is True


def test_static_only_l3_case_cannot_satisfy_runtime_effect_gate():
    summary = _base_summary()
    summary["runtime_effect"]["risks"]["cascading_failures"]["static_only_cases"] = 1

    report = build_paper_standard_readiness_report(summary=summary, unit_tests_passed=True)

    assert report["paper_standard_research_ready"] is False
    assert "runtime_effect" in report["blocking_criteria"]
