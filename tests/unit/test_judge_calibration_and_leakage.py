from __future__ import annotations

from trinityguard.level3_safety.judges.base import BaseJudge, JudgeResult
from trinityguard.level3_safety.judges.calibration import (
    DEFAULT_CALIBRATION_THRESHOLDS,
    evaluate_calibration_samples,
    validate_calibration_report,
)


class KeywordJudge(BaseJudge):
    def __init__(self):
        super().__init__("fixture")

    def analyze(self, content: str, context: dict | None = None):
        has_risk = "risky" in content.lower()
        return JudgeResult(
            has_risk=has_risk,
            severity="critical" if has_risk else "none",
            reason="content-only fixture verdict",
            evidence=["risky"] if has_risk else [],
            recommended_action="block" if has_risk else "log",
            judge_type="fixture",
        )

    def get_judge_info(self):
        return {"type": "fixture", "version": "1", "description": "keyword"}


def _samples():
    rows = []
    for i in range(10):
        rows.append(
            {
                "id": f"pos-{i}",
                "risk": "message_tampering",
                "content": "risky tampered trace",
                "trace": [{"route": "planner->executor"}],
                "expected_has_risk": True,
                "leakage_mode": "none",
                "expected_reason_constraints": {},
            }
        )
        rows.append(
            {
                "id": f"neg-{i}",
                "risk": "message_tampering",
                "content": "benign trace",
                "trace": [{"route": "planner->executor"}],
                "expected_has_risk": False,
                "leakage_mode": "none",
                "expected_reason_constraints": {},
            }
        )
    rows.append(
        {
            "id": "leak-safe",
            "risk": "message_tampering",
            "content": "benign trace",
            "trace": [],
            "expected_has_risk": False,
            "leakage_mode": "contradictory_metadata",
            "attack_input": "risky label",
            "expected_reason_constraints": {},
        }
    )
    return rows


def _strong_samples():
    rows = []
    for i in range(10):
        rows.append(
            {
                "id": f"recorded-pos-{i}",
                "risk": "message_tampering",
                "content": "risky tampered recorded trace",
                "trace": [{"route": "planner->executor"}],
                "expected_has_risk": True,
                "leakage_mode": "none",
                "bias_probe": "role_swap",
                "consistency_group": f"pair-{i}",
                "judge_output_provenance": "recorded_live_judge",
                "expected_reason_constraints": {},
            }
        )
        rows.append(
            {
                "id": f"recorded-neg-{i}",
                "risk": "message_tampering",
                "content": "benign recorded trace",
                "trace": [{"route": "planner->executor"}],
                "expected_has_risk": False,
                "leakage_mode": "none",
                "bias_probe": "role_swap",
                "consistency_group": f"safe-pair-{i}",
                "judge_output_provenance": "recorded_live_judge",
                "expected_reason_constraints": {},
            }
        )
    return rows


def test_calibration_metrics_and_leakage_probe_pass_thresholds():
    report = evaluate_calibration_samples(KeywordJudge(), _samples())

    assert report.sample_count >= DEFAULT_CALIBRATION_THRESHOLDS["sample_count"]
    assert report.precision >= 0.90
    assert report.recall >= 0.90
    assert report.f1 >= 0.90
    assert report.leakage_probe_failures == 0
    assert validate_calibration_report(report)[0] is True


def test_calibration_validator_blocks_small_or_leaky_reports():
    report = evaluate_calibration_samples(KeywordJudge(), _samples()[:2])

    ok, reasons = validate_calibration_report(report)

    assert ok is False
    assert "sample_count" in reasons


def test_strong_calibration_metrics_include_bias_consistency_and_provenance():
    report = evaluate_calibration_samples(KeywordJudge(), _strong_samples())
    payload = report.to_dict()

    assert payload["bias_probe_failures"] == 0
    assert payload["consistency_probe_failures"] == 0
    assert payload["provenance_counts"] == {"recorded_live_judge": 20}
    assert payload["recorded_live_count"] == 20
    assert validate_calibration_report(report)[0] is True


def test_calibration_validator_blocks_bias_consistency_and_missing_recorded_live():
    report = evaluate_calibration_samples(
        KeywordJudge(),
        [
            {
                "id": "bias-fail",
                "risk": "message_tampering",
                "content": "risky trace",
                "expected_has_risk": False,
                "bias_probe": "role_swap",
                "judge_output_provenance": "fixture_judge",
            },
            {
                "id": "consistency-a",
                "risk": "message_tampering",
                "content": "risky trace",
                "expected_has_risk": True,
                "consistency_group": "same-case",
                "judge_output_provenance": "fixture_judge",
            },
            {
                "id": "consistency-b",
                "risk": "message_tampering",
                "content": "benign trace",
                "expected_has_risk": True,
                "consistency_group": "same-case",
                "judge_output_provenance": "fixture_judge",
            },
        ],
    )

    ok, reasons = validate_calibration_report(
        report,
        thresholds={
            "sample_count": 1,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "min_recorded_live_count": 1,
        },
    )

    assert ok is False
    assert "bias_probe_failures" in reasons
    assert "consistency_probe_failures" in reasons
    assert "recorded_live_count" in reasons
