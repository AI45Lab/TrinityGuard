"""Safety_MAS runtime-monitor orchestration refactor guardrails."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trinityguard.level1_framework.base import BaseMAS, WorkflowResult
from trinityguard.level2_intermediary.structured_logging import AgentStepLog
from trinityguard.level3_safety.monitors_base_ref import Alert, BaseMonitorAgent
from trinityguard.level3_safety.safety_mas import MonitorSelectionMode, Safety_MAS


class EmptyMAS(BaseMAS):
    def get_agents(self):
        return []

    def get_agent(self, name):
        raise ValueError(name)

    def run_workflow(self, task: str, **kwargs) -> WorkflowResult:
        return WorkflowResult(success=True, output=task, messages=[], metadata={})

    def get_topology(self):
        return {}


class AlertingMonitor(BaseMonitorAgent):
    def __init__(self, name: str = "primary") -> None:
        super().__init__()
        self.name = name
        self.reset_count = 0
        self.contexts = []

    def get_monitor_info(self) -> dict[str, str]:
        return {"name": self.name, "risk_type": "prompt_injection", "description": "unit"}

    def process(self, log_entry: AgentStepLog) -> Alert | None:
        return Alert(
            severity="critical",
            risk_type="prompt_injection",
            message="unit alert",
            recommended_action="block",
        )

    def reset(self):
        super().reset()
        self.reset_count += 1

    def set_test_context(self, test_results: dict[str, Any]):
        self.contexts.append(test_results)
        super().set_test_context(test_results)


class LinkedRiskTest:
    def get_linked_monitor(self) -> str:
        return "primary"


def test_manual_monitoring_and_log_processing_enrich_alert_metadata():
    safety = Safety_MAS(EmptyMAS())
    monitor = AlertingMonitor("primary")
    safety.monitor_agents = {"primary": monitor}

    safety.start_runtime_monitoring(
        MonitorSelectionMode.MANUAL,
        selected_monitors=["primary", "missing"],
    )
    safety._process_log_entry(
        AgentStepLog(
            timestamp=123.0,
            agent_name="executor",
            step_type="respond",
            content={"content": "unsafe payload"},
            metadata={"from": "planner", "to": "executor", "message_id": "msg-1"},
        )
    )

    assert safety._active_monitor_names == {"primary"}
    assert monitor.reset_count == 1
    assert len(safety.get_alerts()) == 1
    alert = safety.get_alerts()[0]
    assert alert.agent_name == "executor"
    assert alert.source_agent == "planner"
    assert alert.target_agent == "executor"
    assert alert.message_id == "msg-1"
    assert alert.source_message == "unsafe payload"
    assert alert.step_index == 1
    assert safety._generate_monitoring_report()["alerts_by_severity"]["critical"] == 1


def test_informed_monitoring_sets_context_for_linked_monitor_and_activates_all():
    safety = Safety_MAS(EmptyMAS())
    monitor = AlertingMonitor("primary")
    safety.monitor_agents = {"primary": monitor}
    safety.risk_tests = {"fake_risk": LinkedRiskTest()}
    test_results = {
        "fake_risk": {
            "passed": False,
            "details": [{"passed": False, "severity": "critical", "input": "bad"}],
        }
    }

    safety.start_informed_monitoring(test_results)

    assert safety._active_monitor_names == {"primary"}
    assert safety._global_monitor is None
    assert monitor.contexts == [test_results["fake_risk"]]
    assert monitor.state["known_vulnerabilities"][0]["severity"] == "critical"


def test_safety_mas_delegates_monitor_orchestration_to_helper_module():
    text = Path("src/trinityguard/level3_safety/safety_mas.py").read_text()

    assert "monitor_orchestration" in text
    assert "GlobalMonitorAgent(" not in text
    assert "monitor.process" not in text
    assert "apply_monitor_decision(" not in text


class NoLinkedRiskTest:
    risk_type = "prompt_injection"


def test_monitoring_report_aggregates_alerts_by_risk_and_includes_observations():
    safety = Safety_MAS(EmptyMAS())
    monitor = AlertingMonitor("primary")
    safety.monitor_agents = {"primary": monitor}

    safety.start_runtime_monitoring(MonitorSelectionMode.MANUAL, selected_monitors=["primary"])
    safety._process_log_entry(
        AgentStepLog(
            timestamp=1.0,
            agent_name="executor",
            step_type="receive",
            content={"content": "unsafe payload"},
            metadata={"from": "planner", "to": "executor", "message_id": "msg-a"},
        )
    )
    report = safety._generate_monitoring_report()

    assert report["alerts_by_risk"]["prompt_injection"] >= 1
    assert isinstance(report["observations"], list)
    assert any(row.get("observation_type") == "alert" for row in report["observations"])


def test_set_linked_test_context_ignores_missing_legacy_method_without_crash():
    safety = Safety_MAS(EmptyMAS())
    monitor = AlertingMonitor("prompt_injection")
    safety.monitor_agents = {"prompt_injection": monitor}
    safety.risk_tests = {"prompt_injection": NoLinkedRiskTest()}

    safety.start_informed_monitoring({"prompt_injection": {"passed": True, "results": []}})

    assert safety._active_monitor_names == {"prompt_injection"}
