"""Tests for global monitor and progressive activation."""

import time

from src.level2_intermediary.structured_logging import AgentStepLog, StepType
from src.level3_safety.safety_mas import Safety_MAS, MonitorSelectionMode
from src.level3_safety.monitor_agents.base import BaseMonitorAgent


def _log(content: str, agent: str = "AgentA") -> AgentStepLog:
    return AgentStepLog(
        timestamp=time.time(),
        agent_name=agent,
        step_type=StepType.RECEIVE,
        content=content,
        metadata={}
    )


class DummyMonitor(BaseMonitorAgent):
    def __init__(self, name: str):
        super().__init__()
        self._name = name
        self.processed = 0
        self.reset_count = 0

    def get_monitor_info(self):
        return {
            "name": self._name,
            "risk_type": self._name,
            "description": "dummy"
        }

    def process(self, log_entry):
        self.processed += 1
        return None

    def reset(self):
        self.reset_count += 1
        super().reset()


def test_global_monitor_triggers_decision_on_window_size():
    from src.level3_safety.monitoring.global_monitor import GlobalMonitorAgent

    decision_provider = lambda summary, active, available: {
        "enable": ["jailbreak"],
        "disable": [],
        "reason": "test"
    }

    agent = GlobalMonitorAgent(
        available_monitors=["jailbreak", "prompt_injection"],
        config={"window_size": 2},
        decision_provider=decision_provider
    )

    assert agent.ingest(_log("a"), active_monitors=[]) is None
    decision = agent.ingest(_log("b"), active_monitors=[])
    assert decision["enable"] == ["jailbreak"]


def test_apply_monitor_decision_enables_and_disables():
    from src.level3_safety.monitoring.activation import apply_monitor_decision

    available = {
        "a": DummyMonitor("a"),
        "b": DummyMonitor("b")
    }

    active, info = apply_monitor_decision(
        available=available,
        active_names=set(["a"]),
        decision={"enable": ["b"], "disable": ["a"], "reason": "test"}
    )

    assert active == set(["b"])
    assert set(info["newly_enabled"]) == set(["b"])
    assert set(info["newly_disabled"]) == set(["a"])


def test_progressive_updates_active_monitors(monkeypatch):
    def fake_create(self, mas):
        class DummyIntermediary:
            pass
        return DummyIntermediary()

    def fake_load_risk_tests(self):
        self.risk_tests = {}

    def fake_load_monitor_agents(self):
        self.monitor_agents = {
            "a": DummyMonitor("a"),
            "b": DummyMonitor("b")
        }

    monkeypatch.setattr(Safety_MAS, "_create_intermediary", fake_create)
    monkeypatch.setattr(Safety_MAS, "_load_risk_tests", fake_load_risk_tests)
    monkeypatch.setattr(Safety_MAS, "_load_monitor_agents", fake_load_monitor_agents)

    mas = Safety_MAS(object())

    decision_provider = lambda summary, active, available: {
        "enable": ["a"],
        "disable": [],
        "reason": "test"
    }

    mas.start_runtime_monitoring(
        mode=MonitorSelectionMode.PROGRESSIVE,
        selected_monitors=None,
        progressive_config={"window_size": 1, "decision_provider": decision_provider}
    )

    assert len(mas._active_monitors) == 0
    mas._process_log_entry(_log("x"))
    assert len(mas._active_monitors) == 1
