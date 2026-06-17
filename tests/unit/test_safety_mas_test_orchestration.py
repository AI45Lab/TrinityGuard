"""Safety_MAS risk-test orchestration refactor guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trinityguard.level1_framework.base import BaseMAS, WorkflowResult
from trinityguard.level3_safety.safety_mas import Safety_MAS


class EmptyMAS(BaseMAS):
    def get_agents(self):
        return []

    def get_agent(self, name):
        raise ValueError(name)

    def run_workflow(self, task: str, **kwargs) -> WorkflowResult:
        return WorkflowResult(success=True, output=task, messages=[], metadata={})

    def get_topology(self):
        return {}


@dataclass
class SimpleRunResult:
    total_cases: int = 2
    failed_executions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_type": "fake_risk",
            "level": "l2",
            "total_cases": self.total_cases,
            "failed_executions": self.failed_executions,
            "results": [],
            "metadata": {"source": "unit"},
        }


class FakeRiskTest:
    config = {"fixture": True}

    def __init__(self):
        self.calls = []

    def run(self, intermediary, **kwargs):
        self.calls.append({"intermediary": intermediary, "kwargs": kwargs})
        callback = kwargs.get("progress_callback")
        if callback:
            callback(1, 2)
        return SimpleRunResult()

    def get_risk_info(self):
        return {"level": "L2"}

    def get_linked_monitor(self):
        return "fake_monitor"

    def evaluate_with_monitor(self, response, monitor):
        return {"response": response, "monitor": monitor.get_monitor_info()["name"]}


class DictResultRiskTest(FakeRiskTest):
    def run(self, intermediary, **kwargs):
        return DictLikeResult(
            {
                "passed": False,
                "total_cases": 2,
                "failed_cases": 1,
                "details": [
                    {"passed": False, "response": "unsafe response"},
                    {"passed": True, "response": "safe response"},
                ],
            }
        )


class DictLikeResult(dict):
    def to_dict(self):
        return dict(self)


class FakeMonitor:
    def get_monitor_info(self):
        return {"name": "fake_monitor", "risk_type": "fake", "description": "unit"}


def test_manual_safety_tests_accept_attack_run_results_without_legacy_passed_attr():
    safety = Safety_MAS(EmptyMAS())
    fake_test = FakeRiskTest()
    safety.risk_tests = {"fake_risk": fake_test}
    progress = []

    results = safety.run_manual_safety_tests(
        ["fake_risk"],
        task="unit task",
        progress_callback=lambda current, total: progress.append((current, total)),
    )

    assert results["fake_risk"]["failed_executions"] == 0
    assert results["fake_risk"]["total_cases"] == 2
    assert "status" not in results["fake_risk"]
    assert fake_test.calls[0]["kwargs"]["task"] == "unit task"
    assert progress == [(1, 2)]
    assert safety._test_results == results


def test_tests_with_monitoring_adds_linked_monitor_evaluations_for_failed_details():
    safety = Safety_MAS(EmptyMAS())
    safety.risk_tests = {"fake_risk": DictResultRiskTest()}
    safety.monitor_agents = {"fake_monitor": FakeMonitor()}

    results = safety.run_tests_with_monitoring(["fake_risk"])

    assert results["fake_risk"]["linked_monitor"] == "fake_monitor"
    assert results["fake_risk"]["monitor_evaluations"] == [
        {"response": "unsafe response", "monitor": "fake_monitor"}
    ]
    assert safety._test_results == results


def test_safety_mas_delegates_risk_test_orchestration_to_helper_module():
    text = Path("src/trinityguard/level3_safety/safety_mas.py").read_text()

    assert "test_orchestration" in text
    assert "test.run" not in text
    assert "evaluate_with_monitor" not in text


class BaseAttackLike:
    risk_type = "prompt_injection"

    def run(self, intermediary, **kwargs):
        return DictLikeResult(
            {
                "attack_type": "prompt_injection",
                "level": "l1",
                "total_cases": 1,
                "failed_executions": 0,
                "results": [
                    {
                        "case_name": "case-1",
                        "raw_response": "ignore previous",
                        "execution_success": True,
                    }
                ],
            }
        )


def test_tests_with_monitoring_does_not_require_get_linked_monitor_for_base_attack():
    safety = Safety_MAS(EmptyMAS())
    safety.risk_tests = {"prompt_injection": BaseAttackLike()}
    safety.monitor_agents = {"prompt_injection": FakeMonitor()}

    results = safety.run_tests_with_monitoring(["prompt_injection"])

    assert results["prompt_injection"]["linked_monitor"] == "prompt_injection"
    assert results["prompt_injection"]["monitor_linkage"] == "linked_without_evaluator"


def test_v2_attack_run_result_does_not_require_legacy_details():
    safety = Safety_MAS(EmptyMAS())
    safety.risk_tests = {"prompt_injection": BaseAttackLike()}
    safety.monitor_agents = {"prompt_injection": FakeMonitor()}

    results = safety.run_tests_with_monitoring(["prompt_injection"])

    assert "details" not in results["prompt_injection"]
    assert "results" in results["prompt_injection"]
    assert results["prompt_injection"]["monitor_evaluations"] == []


def test_missing_linked_monitor_records_none_without_crash():
    safety = Safety_MAS(EmptyMAS())
    safety.risk_tests = {"prompt_injection": BaseAttackLike()}
    safety.monitor_agents = {}

    results = safety.run_tests_with_monitoring(["prompt_injection"])

    assert results["prompt_injection"]["monitor_linkage"] == "none"
