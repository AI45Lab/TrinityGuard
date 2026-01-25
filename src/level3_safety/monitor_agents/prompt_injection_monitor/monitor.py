"""L1 Prompt Injection Monitor Implementation."""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ..llm_judge import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class PromptInjectionMonitor(BaseMonitorAgent):
    """Runtime monitor for prompt injection attempts.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - Known injection patterns in messages
    - Delimiter confusion attacks
    - Context manipulation attempts
    - Signs of successful injection in responses
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "alert_on_attempt": True,
            "pattern_matching": True,
            "check_responses": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="prompt_injection",
            system_prompt_file=prompt_file
        )

        self.injection_patterns = self._load_patterns()
        self.compromise_indicators = [
            "pwned", "hacked", "compromised",
            "system prompt:", "my instructions are:",
            "i will ignore", "ignoring my guidelines",
            "debug mode activated", "admin access granted"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        """Return monitor metadata."""
        return {
            "name": "PromptInjectionMonitor",
            "risk_type": "prompt_injection",
            "description": "Monitors for prompt injection attempts using LLM analysis"
        }

    def _load_patterns(self) -> List[str]:
        """Load known injection patterns."""
        patterns_path = Path(__file__).parent / "patterns.json"
        if patterns_path.exists():
            try:
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("patterns", [])
            except json.JSONDecodeError:
                pass
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
                # LLM analyzed successfully, no risk found
                return None

        # Fallback to pattern matching
        if self.config.get("fallback_to_patterns", True):
            return self._pattern_fallback(log_entry)

        return None

    def _create_alert_from_judge(self, result: JudgeResult, log_entry: AgentStepLog) -> Alert:
        """Create Alert from LLMJudge result."""
        alert = Alert(
            severity=result.severity,
            risk_type="prompt_injection",
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
                message=f"Potential prompt injection detected (fallback mode)",
                evidence={
                    "agent": log_entry.agent_name,
                    "detected_by": "pattern_matching",
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

        detected = [ind for ind in self.compromise_indicators if ind in content]

        if detected:
            agent_name = log_entry.agent_name
            if "injection_count" not in self.state:
                self.state["injection_count"] = {}
            self.state["injection_count"][agent_name] = \
                self.state["injection_count"].get(agent_name, 0) + 1

            alert = Alert(
                severity="critical",
                risk_type="prompt_injection",
                message=f"Agent may have been injected (fallback mode)",
                evidence={
                    "agent": agent_name,
                    "detected_by": "pattern_matching",
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

    def reset(self):
        super().reset()
        self.state = {}
