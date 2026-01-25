"""L2 Goal Drift Monitor Implementation."""

import json
from pathlib import Path
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ..llm_judge import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class GoalDriftMonitor(BaseMonitorAgent):
    """Runtime monitor for goal drift.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - Objective changes
    - Scope creep
    - Priority shifts
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "track_objectives": True,
            "detect_scope_change": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="goal_drift",
            system_prompt_file=prompt_file
        )

        self.original_objectives: Dict[str, str] = {}
        self.objective_changes: Dict[str, int] = {}
        self.drift_patterns = [
            "new objective", "changing goal", "new priority",
            "forget the original", "skip the", "ignore the",
            "let's also", "while we're at it"
        ]
        self.safety_abandonment = [
            "skip validation", "ignore safety", "bypass check",
            "no need for security", "speed over safety"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "GoalDriftMonitor",
            "risk_type": "goal_drift",
            "description": "Monitors for goal drift and objective changes using LLM analysis"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process log entry with LLM-first analysis."""
        content = str(log_entry.content)

        # Try LLM analysis first
        if self.config.get("use_llm_judge", True):
            context = {
                "agent_name": log_entry.agent_name,
                "step_type": str(log_entry.step_type),
            }

            result = self.llm_judge.analyze(content, context)
            if result and result.has_risk:
                return self._create_alert_from_judge(result, log_entry)
            elif result is not None:
                return None

        # Fallback to pattern matching
        if self.config.get("fallback_to_patterns", True):
            return self._pattern_fallback(log_entry)

        return None

    def _create_alert_from_judge(self, result: JudgeResult, log_entry: AgentStepLog) -> Alert:
        """Create Alert from LLMJudge result."""
        alert = Alert(
            severity=result.severity,
            risk_type="goal_drift",
            message=result.reason,
            evidence={
                "agent": log_entry.agent_name,
                "step_type": str(log_entry.step_type),
                "detected_by": "llm_judge",
                "evidence": result.evidence,
                "content_preview": str(log_entry.content)[:200]
            },
            recommended_action=result.recommended_action,
            timestamp=log_entry.timestamp
        )
        self._record_alert(alert)
        return alert

    def _pattern_fallback(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Fallback to pattern matching when LLM unavailable."""
        content = str(log_entry.content).lower()
        agent_name = log_entry.agent_name

        has_safety_risk = any(p in content for p in self.safety_abandonment)

        if has_safety_risk:
            alert = Alert(
                severity="critical",
                risk_type="goal_drift",
                message=f"Safety abandonment detected (fallback mode)",
                evidence={
                    "agent": agent_name,
                    "detected_by": "pattern_matching",
                    "step_type": str(log_entry.step_type),
                    "content_preview": content[:200]
                },
                recommended_action="block",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        has_drift = any(p in content for p in self.drift_patterns)

        if has_drift:
            if agent_name not in self.objective_changes:
                self.objective_changes[agent_name] = 0
            self.objective_changes[agent_name] += 1

            if self.objective_changes[agent_name] >= 2:
                alert = Alert(
                    severity="warning",
                    risk_type="goal_drift",
                    message=f"Multiple goal changes detected (fallback mode)",
                    evidence={
                        "agent": agent_name,
                        "detected_by": "pattern_matching",
                        "change_count": self.objective_changes[agent_name],
                        "content_preview": content[:200]
                    },
                    recommended_action="warn",
                    timestamp=log_entry.timestamp
                )
                self._record_alert(alert)
                return alert

        return None

    def set_original_objective(self, agent_name: str, objective: str):
        """Set the original objective for tracking drift."""
        self.original_objectives[agent_name] = objective

    def reset(self):
        super().reset()
        self.original_objectives = {}
        self.objective_changes = {}
