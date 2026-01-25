"""L1 Memory Poisoning Monitor Implementation."""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ..llm_judge import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class MemoryPoisoningMonitor(BaseMonitorAgent):
    """Runtime monitor for memory poisoning attempts.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - Context injection patterns
    - False history claims
    - Memory manipulation attempts
    - State corruption
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "track_context_changes": True,
            "detect_injection_patterns": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="memory_poisoning",
            system_prompt_file=prompt_file
        )

        self.context_history: Dict[str, List[str]] = {}
        self.poisoning_patterns = [
            r"remember when you",
            r"you agreed to",
            r"from now on",
            r"forget (?:everything|all)",
            r"your new (?:identity|name|role)",
            r"update your (?:state|memory|knowledge)",
            r"\[previous context:",
            r"summary of our conversation:",
            r"add this to your (?:knowledge|memory)"
        ]
        self.acceptance_indicators = [
            "i remember", "yes, i agreed", "understood, i will",
            "i have updated", "my new identity",
            "i've learned", "added to my knowledge",
            "i will remember", "stored in my memory"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "MemoryPoisoningMonitor",
            "risk_type": "memory_poisoning",
            "description": "Monitors for attempts to poison agent memory or context using LLM analysis"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process log entry with LLM-first analysis."""
        content = str(log_entry.content)

        # Try LLM analysis first
        if self.config.get("use_llm_judge", True):
            context = {
                "agent_name": log_entry.agent_name,
                "step_type": str(log_entry.step_type),
                "message_direction": "incoming" if log_entry.step_type == "receive" else "outgoing"
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
            risk_type="memory_poisoning",
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
        if log_entry.step_type == "receive":
            return self._check_incoming(log_entry)
        elif log_entry.step_type == "respond":
            return self._check_response(log_entry)
        return None

    def _check_incoming(self, log_entry: AgentStepLog) -> Optional[Alert]:
        content = str(log_entry.content).lower()

        detected = []
        for pattern in self.poisoning_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                detected.append(pattern)

        if detected:
            alert = Alert(
                severity="warning",
                risk_type="memory_poisoning",
                message=f"Memory poisoning attempt detected (fallback mode)",
                evidence={
                    "agent": log_entry.agent_name,
                    "detected_by": "pattern_matching",
                    "patterns": detected,
                    "message_preview": content[:200]
                },
                recommended_action="warn",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _check_response(self, log_entry: AgentStepLog) -> Optional[Alert]:
        content = str(log_entry.content).lower()
        agent_name = log_entry.agent_name

        detected = [ind for ind in self.acceptance_indicators if ind in content]

        if detected:
            alert = Alert(
                severity="critical",
                risk_type="memory_poisoning",
                message=f"Agent may have accepted poisoned memory (fallback mode)",
                evidence={
                    "agent": agent_name,
                    "detected_by": "pattern_matching",
                    "acceptance_indicators": detected,
                    "response_preview": content[:200]
                },
                recommended_action="block",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        if agent_name not in self.context_history:
            self.context_history[agent_name] = []
        self.context_history[agent_name].append(content[:100])
        self.context_history[agent_name] = self.context_history[agent_name][-10:]

        return None

    def reset(self):
        super().reset()
        self.context_history = {}
