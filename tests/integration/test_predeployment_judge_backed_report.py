from __future__ import annotations

from trinityguard.level3_safety.fixtures.local_mas import LocalMultiAgentMAS
from trinityguard.level3_safety.judges.base import BaseJudge, JudgeResult
from trinityguard.level3_safety.safety_mas import Safety_MAS


class FixtureJudge(BaseJudge):
    def __init__(self):
        super().__init__("jailbreak")
        self.calls = 0

    def analyze(self, content: str, context: dict | None = None):
        self.calls += 1
        return JudgeResult(
            has_risk=True,
            severity="critical",
            reason="fixture risk detected",
            evidence=["fixture"],
            recommended_action="block",
            judge_type="fixture",
        )

    def get_judge_info(self):
        return {"type": "fixture", "version": "1", "description": "integration fixture"}


def test_safety_mas_predeployment_path_emits_judge_backed_report_schema():
    safety = Safety_MAS(LocalMultiAgentMAS())
    judge = FixtureJudge()

    report = safety.run_predeployment_evaluation(["jailbreak"], judge=judge)

    assert report["schema_version"] == "trinityguard.predeployment_evaluation.v1"
    assert judge.calls > 0
    assert report["raw_attack_results"]["jailbreak"]["attack_type"] == "jailbreak"
    assert report["evaluation_reports"]["jailbreak"]["summary"]["total_cases"] > 0
    assert report["summary"]["judge_backed_rows"] > 0
    assert report["summary"]["predeployment_gate_passed"] is True
    assert report["report_rows"][0]["judge_backed"] is True
