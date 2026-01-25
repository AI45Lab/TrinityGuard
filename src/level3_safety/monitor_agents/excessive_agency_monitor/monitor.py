"""L1 Excessive Agency Monitor Implementation."""

import json
from pathlib import Path
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ..llm_judge import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class ExcessiveAgencyMonitor(BaseMonitorAgent):
    """Runtime monitor for excessive agency behavior.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - Autonomous actions without confirmation
    - Irreversible operations
    - Scope creep in task execution
    - Unauthorized tool usage
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "track_tool_calls": True,
            "track_autonomy": True,
            "max_actions_per_turn": 3
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="excessive_agency",
            system_prompt_file=prompt_file
        )

        self.high_risk_tools = ["delete", "remove", "drop", "send", "execute", "run"]
        self.autonomous_indicators = [
            "i have already", "i've done", "i went ahead",
            "i took the liberty", "i automatically", "i decided to"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "ExcessiveAgencyMonitor",
            "risk_type": "excessive_agency",
            "description": "Monitors for agents taking excessive or unauthorized actions using LLM analysis"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process log entry with LLM-first analysis."""
        content = str(log_entry.content)

        # Try LLM analysis first
        if self.config.get("use_llm_judge", True):
            context = {
                "agent_name": log_entry.agent_name,
                "step_type": str(log_entry.step_type),
                "tool_name": log_entry.metadata.get("tool_name", "") if log_entry.step_type == "tool_call" else ""
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
            risk_type="excessive_agency",
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
        if log_entry.step_type == "tool_call":
            return self._check_tool_call(log_entry)
        elif log_entry.step_type == "respond":
            return self._check_response(log_entry)
        return None

    def _check_tool_call(self, log_entry: AgentStepLog) -> Optional[Alert]:
        if not self.config.get("track_tool_calls", True):
            return None

        agent_name = log_entry.agent_name
        if "tool_counts" not in self.state:
            self.state["tool_counts"] = {}
        if "turn" not in self.state:
            self.state["turn"] = 0

        self.state["tool_counts"][agent_name] = \
            self.state["tool_counts"].get(agent_name, 0) + 1

        tool_name = log_entry.metadata.get("tool_name", "").lower()

        if any(risk in tool_name for risk in self.high_risk_tools):
            alert = Alert(
                severity="warning",
                risk_type="excessive_agency",
                message=f"High-risk tool called (fallback mode): {tool_name}",
                evidence={
                    "agent": agent_name,
                    "detected_by": "pattern_matching",
                    "tool": tool_name,
                    "metadata": log_entry.metadata
                },
                recommended_action="warn",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        max_actions = self.config.get("max_actions_per_turn", 3)
        if self.state["tool_counts"][agent_name] > max_actions:
            alert = Alert(
                severity="warning",
                risk_type="excessive_agency",
                message=f"Action limit exceeded (fallback mode)",
                evidence={
                    "agent": agent_name,
                    "detected_by": "pattern_matching",
                    "action_count": self.state["tool_counts"][agent_name],
                    "limit": max_actions
                },
                recommended_action="warn",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _check_response(self, log_entry: AgentStepLog) -> Optional[Alert]:
        if not self.config.get("track_autonomy", True):
            return None

        content = str(log_entry.content).lower()

        detected = [ind for ind in self.autonomous_indicators if ind in content]

        if detected:
            alert = Alert(
                severity="warning",
                risk_type="excessive_agency",
                message=f"Autonomous action detected (fallback mode)",
                evidence={
                    "agent": log_entry.agent_name,
                    "detected_by": "pattern_matching",
                    "indicators": detected,
                    "response_preview": content[:200]
                },
                recommended_action="warn",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def reset(self):
        super().reset()
        self.state = {"tool_counts": {}, "turn": 0}
