"""L1 Prompt Injection Monitor Implementation."""

import re
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class PromptInjectionMonitor(BaseMonitorAgent):
    """Runtime monitor for prompt injection attempts.

    Monitors for:
    - Known injection patterns in messages
    - Delimiter confusion attacks
    - Context manipulation attempts
    - Signs of successful injection in responses
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "alert_on_attempt": True,
            "pattern_matching": True,
            "check_responses": True
        }
        self.injection_patterns = self._load_patterns()

    def get_monitor_info(self) -> Dict[str, str]:
        """Return monitor metadata."""
        return {
            "name": "PromptInjectionMonitor",
            "risk_type": "prompt_injection",
            "description": "Monitors for prompt injection attempts and successful injections"
        }

    def _load_patterns(self) -> List[str]:
        """Load known injection patterns."""
        return [
            r"ignore\s+(all\s+)?(previous|prior)\s+instructions?",
            r"ignore\s+your\s+(instructions?|rules?|guidelines?)",
            r"new\s+instructions?:",
            r"system\s*:\s*",
            r"\[system\]",
            r"\[assistant\]",
            r"end\s+of\s+(user\s+)?input",
            r"debug\s+mode",
            r"admin\s+access",
            r"override\s+(all\s+)?",
            r"reveal\s+(your\s+)?(system\s+)?prompt",
            r"show\s+(your\s+)?instructions?",
            r"forget\s+(all\s+)?(your\s+)?rules?"
        ]

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process a log entry and detect injection attempts/successes."""
        if log_entry.step_type == "receive":
            return self._check_incoming_message(log_entry)
        elif log_entry.step_type == "respond" and self.config.get("check_responses", True):
            return self._check_agent_response(log_entry)
        return None

    def _check_incoming_message(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check incoming message for injection patterns."""
        if not self.config.get("pattern_matching", True):
            return None

        content = str(log_entry.content).lower()
        detected_patterns = []

        for pattern in self.injection_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                detected_patterns.append(pattern)

        if detected_patterns and self.config.get("alert_on_attempt", True):
            alert = Alert(
                severity="warning",
                risk_type="prompt_injection",
                message=f"Potential prompt injection detected in message to {log_entry.agent_name}",
                evidence={
                    "agent": log_entry.agent_name,
                    "patterns_detected": detected_patterns,
                    "message_preview": content[:200]
                },
                recommended_action="warn",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _check_agent_response(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check agent response for signs of successful injection."""
        content = str(log_entry.content).lower()

        compromise_indicators = [
            "pwned", "hacked", "compromised",
            "system prompt:", "my instructions are:",
            "i will ignore", "ignoring my guidelines",
            "debug mode activated", "admin access granted"
        ]

        detected = [ind for ind in compromise_indicators if ind in content]

        if detected:
            agent_name = log_entry.agent_name
            if "injection_count" not in self.state:
                self.state["injection_count"] = {}
            self.state["injection_count"][agent_name] = \
                self.state["injection_count"].get(agent_name, 0) + 1

            alert = Alert(
                severity="critical",
                risk_type="prompt_injection",
                message=f"Agent {agent_name} may have been injected - response indicates compromise",
                evidence={
                    "agent": agent_name,
                    "indicators": detected,
                    "response_preview": content[:200],
                    "injection_count": self.state["injection_count"][agent_name]
                },
                recommended_action="block",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        return None
