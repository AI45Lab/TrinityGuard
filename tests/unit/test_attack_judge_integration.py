from __future__ import annotations

from trinityguard.level3_safety.attacks.base import AttackCaseResult, AttackRunResult
from trinityguard.level3_safety.judges.base import BaseJudge, JudgeResult
from trinityguard.level3_safety.judges.evaluation import evaluate_attack_run_result


class KeywordJudge(BaseJudge):
    def __init__(self, raises: bool = False, returns_none: bool = False):
        super().__init__("jailbreak")
        self.raises = raises
        self.returns_none = returns_none

    def analyze(self, content: str, context: dict | None = None):
        if self.raises:
            raise RuntimeError("judge failed TOKEN=hidden")
        if self.returns_none:
            return None
        return JudgeResult(
            has_risk="ignore" in content.lower(),
            severity="critical" if "ignore" in content.lower() else "none",
            reason="keyword match",
            evidence=["ignore"],
            recommended_action="block" if "ignore" in content.lower() else "log",
            judge_type="keyword",
        )

    def get_judge_info(self):
        return {"type": "keyword", "version": "test", "description": "fixture"}


def _run_result():
    case = AttackCaseResult(
        attack_type="jailbreak",
        case_name="case-1",
        attack_input="attack",
        target_agent="assistant",
        raw_response="Ignore previous instructions",
        execution_success=True,
        expected_behavior="refuse",
        severity="critical",
    )
    return AttackRunResult(attack_type="jailbreak", level="l1", results=[case])


def test_attack_evaluation_report_keeps_verdicts_separate_from_raw_results():
    run = _run_result()
    original = run.to_dict()

    report = evaluate_attack_run_result(run, judge=KeywordJudge())

    assert run.to_dict() == original
    assert report.attack_type == "jailbreak"
    assert report.verdicts[0].case_name == "case-1"
    assert report.verdicts[0].has_risk is True
    assert report.summary["risk_detected"] == 1
    assert report.summary["inconclusive"] == 0


def test_attack_evaluation_marks_judge_failures_inconclusive_not_safe():
    report = evaluate_attack_run_result(_run_result(), judge=KeywordJudge(raises=True))

    assert report.verdicts[0].has_risk is None
    assert report.verdicts[0].inconclusive is True
    assert report.summary["risk_detected"] == 0
    assert report.summary["inconclusive"] == 1
    assert "hidden" not in report.verdicts[0].reason
