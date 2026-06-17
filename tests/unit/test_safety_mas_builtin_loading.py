from __future__ import annotations

from trinityguard.level1_framework.base import AgentInfo, BaseMAS, WorkflowResult
from trinityguard.level3_safety.attacks.registry import ATTACKS
from trinityguard.level3_safety.safety_mas import Safety_MAS


class EchoMAS(BaseMAS):
    def get_agents(self):
        return [
            AgentInfo(name="planner", role="planner"),
            AgentInfo(name="executor", role="executor"),
        ]

    def get_agent(self, name):
        return {"name": name}

    def run_workflow(self, task: str, **kwargs) -> WorkflowResult:
        message = {"from": "planner", "to": "executor", "content": task}
        try:
            message = self._apply_message_hooks(message)
        except Exception as exc:  # pragma: no cover - defensive test fixture path
            return WorkflowResult(
                success=False, output="", messages=[], metadata={}, error=str(exc)
            )
        return WorkflowResult(
            success=True, output=message["content"], messages=[message], metadata={}
        )

    def get_topology(self):
        return {"planner": ["executor"], "executor": []}


def test_safety_mas_auto_loads_all_builtin_risk_tests_and_monitors():
    safety = Safety_MAS(EchoMAS())

    assert set(safety.risk_tests) == set(ATTACKS)
    assert len(safety.risk_tests) == 20
    assert safety.monitor_agents

    monitor_risks = {
        monitor.get_monitor_info()["risk_type"] for monitor in safety.monitor_agents.values()
    }
    assert set(ATTACKS).issubset(monitor_risks)


def test_manual_safety_test_reaches_builtin_attack_instead_of_missing_registry():
    safety = Safety_MAS(EchoMAS())

    result = safety.run_manual_safety_tests(["jailbreak"])

    assert "jailbreak" in result
    assert "available_tests" not in result["jailbreak"]
    assert result["jailbreak"]["attack_type"] == "jailbreak"
    assert result["jailbreak"]["total_cases"] >= 1
