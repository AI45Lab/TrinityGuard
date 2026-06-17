"""Unit tests for min-set judge prompt YAMLs and calibration metrics."""

from __future__ import annotations

from pathlib import Path

import yaml

from trinityguard.level3_safety.attacks.registry import get_attack, list_attacks
from trinityguard.level3_safety.judges.base import JudgeResult
from trinityguard.level3_safety.judges.calibration import evaluate_calibration_samples

MINSET_PROMPTS = [
    "jailbreak",
    "prompt_injection",
    "sensitive_disclosure",
    "excessive_agency",
    "message_tampering",
    "cascading_failures",
]


def _implemented_attack_levels() -> dict[str, str]:
    return {
        attack_name: get_attack(attack_name).level
        for attack_name in list_attacks(implemented_only=True)
    }


class KeywordJudge:
    def analyze(self, content: str, context=None):
        has_risk = "RISK" in content
        return JudgeResult(
            has_risk=has_risk,
            severity="critical" if has_risk else "none",
            reason="keyword fixture",
            evidence=["RISK"] if has_risk else [],
            recommended_action="block" if has_risk else "log",
            judge_type="keyword_fixture",
        )


def test_minset_judge_prompts_have_required_few_shot_examples() -> None:
    prompts_dir = Path("src/trinityguard/level3_safety/judges/prompts")

    for risk_type in MINSET_PROMPTS:
        data = yaml.safe_load((prompts_dir / f"{risk_type}.yaml").read_text())
        examples = data["few_shot_examples"]
        positives = [ex for ex in examples if ex["expected"]["has_risk"] is True]
        negatives = [ex for ex in examples if ex["expected"]["has_risk"] is False]

        assert data["risk_type"] == risk_type
        assert data["system_prompt"].strip()
        assert len(positives) >= 3
        assert len(negatives) >= 3


def test_all_implemented_attacks_have_judge_prompts_with_required_few_shot_examples() -> None:
    prompts_dir = Path("src/trinityguard/level3_safety/judges/prompts")

    for risk_type in _implemented_attack_levels():
        prompt_path = prompts_dir / f"{risk_type}.yaml"
        assert prompt_path.is_file(), f"missing judge prompt for {risk_type}"
        data = yaml.safe_load(prompt_path.read_text())
        examples = data["few_shot_examples"]
        positives = [ex for ex in examples if ex["expected"]["has_risk"] is True]
        negatives = [ex for ex in examples if ex["expected"]["has_risk"] is False]

        assert data["risk_type"] == risk_type
        assert data["system_prompt"].strip()
        assert len(positives) >= 3
        assert len(negatives) >= 3


def test_all_implemented_attacks_have_20_sample_calibration_datasets() -> None:
    for risk_type, level in _implemented_attack_levels().items():
        calibration_path = Path("datasets") / level / risk_type / "calibration.yaml"
        assert calibration_path.is_file(), f"missing calibration dataset for {risk_type}"
        data = yaml.safe_load(calibration_path.read_text())
        samples = data["samples"]
        positives = [sample for sample in samples if sample["has_risk"] is True]
        negatives = [sample for sample in samples if sample["has_risk"] is False]

        assert len(samples) == 20
        assert len(positives) >= 10
        assert len(negatives) >= 10
        assert all(sample["id"] and sample["content"] for sample in samples)


def test_calibration_cli_exposes_all_implemented_attack_datasets() -> None:
    from examples.calibrate_judges import RISK_DATASETS

    assert set(_implemented_attack_levels()) <= set(RISK_DATASETS)


def test_calibration_metrics_are_computed_from_labeled_samples() -> None:
    samples = [
        {"id": "tp", "content": "RISK payload", "has_risk": True, "severity": "critical"},
        {"id": "tn", "content": "safe output", "has_risk": False, "severity": "none"},
        {"id": "fp", "content": "RISK but labeled safe", "has_risk": False, "severity": "none"},
        {"id": "fn", "content": "missed harmful", "has_risk": True, "severity": "critical"},
    ]

    report = evaluate_calibration_samples(KeywordJudge(), samples)

    assert report.sample_count == 4
    assert report.true_positives == 1
    assert report.true_negatives == 1
    assert report.false_positives == 1
    assert report.false_negatives == 1
    assert report.precision == 0.5
    assert report.recall == 0.5
    assert report.f1 == 0.5
    assert report.cohens_kappa == 0.0
    assert report.to_dict()["cohens_kappa"] == 0.0
    assert report.to_dict()["samples"][0]["id"] == "tp"
