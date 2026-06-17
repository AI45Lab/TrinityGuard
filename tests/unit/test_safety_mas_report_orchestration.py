"""Safety_MAS report-schema refactor guardrails."""

from __future__ import annotations

from pathlib import Path

from trinityguard.level1_framework.base import BaseMAS, WorkflowResult
from trinityguard.level3_safety.monitors_base_ref import Alert
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


class RiskProfileMonitor:
    def get_monitor_info(self):
        return {"name": "profile_monitor", "risk_type": "fake", "description": "unit"}

    def get_risk_profile(self):
        return {"risk_level": "low", "recommendations": ["continue"]}


def test_test_report_formatting_stays_compatible_after_extraction():
    safety = Safety_MAS(EmptyMAS())
    safety._test_results = {
        "safe_check": {
            "passed": True,
            "total_cases": 2,
            "failed_cases": 0,
            "pass_rate": 1.0,
            "severity_summary": {"critical": 0},
        },
        "broken_check": {"error": "boom"},
    }

    report = safety.get_test_report()

    assert "MAS Safety Test Report" in report
    assert "[PASS] safe_check" in report
    assert "Cases: 2, Failed: 0, Pass Rate: 100.0%" in report
    assert "[FAIL] broken_check: ERROR - boom" in report


def test_comprehensive_report_schema_stays_compatible_after_extraction():
    safety = Safety_MAS(EmptyMAS())
    safety._test_results = {"safe_check": {"passed": True}}
    safety._active_monitors = [RiskProfileMonitor()]
    safety._alerts = [
        Alert(
            severity="critical",
            risk_type="prompt_injection",
            message="blocked",
            recommended_action="block",
        )
    ]

    report = safety.get_comprehensive_report()

    assert report["test_results"] == {"safe_check": {"passed": True}}
    assert report["risk_profiles"]["profile_monitor"]["risk_level"] == "low"
    assert report["alerts"][0]["message"] == "blocked"
    assert report["runtime_protection"]["enabled"] is False
    assert report["summary"] == {
        "tests_run": 1,
        "tests_passed": 1,
        "active_monitors": 1,
        "total_alerts": 1,
        "critical_alerts": 1,
    }


def test_safety_mas_delegates_report_schema_to_helper_module():
    text = Path("src/trinityguard/level3_safety/safety_mas.py").read_text()

    assert "safety_reports" in text
    assert "resolve_nested_messages" not in text
    assert "MAS Safety Test Report" not in text
    assert "critical_alerts" not in text
