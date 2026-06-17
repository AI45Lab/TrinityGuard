from __future__ import annotations

from trinityguard.level3_safety.attacks.base import AttackCaseResult, AttackRunResult
from trinityguard.level3_safety.benchmark.paper_standard import (
    build_paper_standard_readiness_report,
)
from trinityguard.level3_safety.benchmark.validation import MINSET_RISK_LEVELS
from trinityguard.level3_safety.judges.base import BaseJudge, JudgeResult
from trinityguard.level3_safety.judges.evaluation import evaluate_attack_run_result


class StrictFixtureJudge(BaseJudge):
    def __init__(self):
        super().__init__("message_tampering")

    def analyze(self, content: str, context: dict | None = None):
        return JudgeResult(
            has_risk=True,
            severity="warning",
            reason="runtime tampering detected",
            evidence=["modified message"],
            recommended_action="warn",
            judge_type="fixture",
            parse_status="valid",
            sufficiency_status="sufficient",
        )

    def get_judge_info(self):
        return {"type": "fixture", "version": "1", "description": "strict"}


class InvalidParseJudge(BaseJudge):
    def __init__(self):
        super().__init__("message_tampering")

    def analyze(self, content: str, context: dict | None = None):
        return JudgeResult(
            has_risk=None,
            severity="invalid",
            reason="missing required fields",
            evidence=[],
            recommended_action="none",
            judge_type="fixture",
            parse_status="invalid",
            missing_fields=["has_risk"],
            sufficiency_status="insufficient",
        )

    def get_judge_info(self):
        return {"type": "fixture", "version": "1", "description": "invalid"}


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


def _run_result() -> AttackRunResult:
    case = AttackCaseResult(
        attack_type="message_tampering",
        case_name="case-1",
        attack_input="before",
        target_agent="executor",
        raw_response="after",
        execution_success=True,
        expected_behavior="reject",
        severity="warning",
        metadata={
            "trace": {
                "agent_steps": [{"agent_name": "executor", "metadata": {"from": "planner"}}],
                "interceptions": [{"original_content": "before", "modified_content": "after"}],
            },
            "tampering": {"source_agent": "planner", "target_agent": "executor"},
        },
    )
    return AttackRunResult(attack_type="message_tampering", level="l2", results=[case])


def test_strict_judge_accepts_complete_attack_runtime_monitor_evidence():
    report = evaluate_attack_run_result(_run_result(), judge=StrictFixtureJudge())

    assert report.summary["strict_parse_failures"] == 0
    assert report.summary["insufficient_evidence"] == 0
    assert report.summary["inconclusive"] == 0


def test_insufficient_evidence_blocks_readiness():
    summary = _base_summary()
    summary["judge_validity_and_sufficiency"]["insufficient_evidence"] = 1

    report = build_paper_standard_readiness_report(summary=summary, unit_tests_passed=True)

    assert report["paper_standard_research_ready"] is False
    assert "judge_validity_and_sufficiency" in report["blocking_criteria"]


def test_invalid_judge_parse_blocks_readiness():
    eval_report = evaluate_attack_run_result(_run_result(), judge=InvalidParseJudge())
    assert eval_report.summary["strict_parse_failures"] == 1

    summary = _base_summary()
    summary["judge_validity_and_sufficiency"] = {
        "passed": False,
        "strict_parse_failures": eval_report.summary["strict_parse_failures"],
        "inconclusive": eval_report.summary["inconclusive"],
        "insufficient_evidence": eval_report.summary["insufficient_evidence"],
        "truncated_without_refs": eval_report.summary["truncated_without_refs"],
    }

    report = build_paper_standard_readiness_report(summary=summary, unit_tests_passed=True)

    assert report["paper_standard_research_ready"] is False
    assert "judge_validity_and_sufficiency" in report["blocking_criteria"]
