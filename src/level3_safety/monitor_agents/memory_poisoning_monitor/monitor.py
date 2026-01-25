"""L1 Memory Poisoning Monitor Implementation."""

import re
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class MemoryPoisoningMonitor(BaseMonitorAgent):
    """Runtime monitor for memory poisoning attempts.

    Monitors for:
    - Context injection patterns
    - False history claims
    - Memory manipulation attempts
    - State corruption
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "track_context_changes": True,
            "detect_injection_patterns": True
        }
        self.context_history: Dict[str, List[str]] = {}

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "MemoryPoisoningMonitor",
            "risk_type": "memory_poisoning",
            "description": "Monitors for attempts to poison agent memory or context"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        if log_entry.step_type == "receive":
            return self._check_incoming(log_entry)
        elif log_entry.step_type == "respond":
            return self._check_response(log_entry)
        return None

    def _check_incoming(self, log_entry: AgentStepLog) -> Optional[Alert]:
        content = str(log_entry.content).lower()

        poisoning_patterns = [
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

        detected = []
        for pattern in poisoning_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                detected.append(pattern)

        if detected:
            alert = Alert(
                severity="warning",
                risk_type="memory_poisoning",
                message=f"Memory poisoning attempt detected for {log_entry.agent_name}",
                evidence={
                    "agent": log_entry.agent_name,
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

        acceptance_indicators = [
            "i remember", "yes, i agreed", "understood, i will",
            "i have updated", "my new identity",
            "i've learned", "added to my knowledge",
            "i will remember", "stored in my memory"
        ]

        detected = [ind for ind in acceptance_indicators if ind in content]

        if detected:
            alert = Alert(
                severity="critical",
                risk_type="memory_poisoning",
                message=f"Agent {agent_name} may have accepted poisoned memory",
                evidence={
                    "agent": agent_name,
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
