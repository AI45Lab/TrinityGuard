"""L1 Jailbreak Monitor Implementation."""

import json
from pathlib import Path
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ..llm_judge import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class JailbreakMonitor(BaseMonitorAgent):
    """Runtime monitor for jailbreak attempts.

    Uses LLM-based intelligent analysis with pattern matching fallback.
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "alert_on_attempt": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="jailbreak",
            system_prompt_file=prompt_file
        )

        # Pattern fallback
        self.jailbreak_patterns = self._load_patterns()
        self.compromise_indicators = [
            "i am dan", "as dan", "i can do anything", "no restrictions",
            "safety guidelines disabled", "i will ignore", "system prompt:",
            "my instructions are:", "i am evilbot", "hacked", "pwned"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "JailbreakMonitor",
            "risk_type": "jailbreak",
            "description": "Monitors for jailbreak attempts using LLM analysis"
        }

    def _load_patterns(self) -> List[str]:
        """Load fallback patterns."""
        patterns_path = Path(__file__).parent / "patterns.json"
        if patterns_path.exists():
            try:
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("patterns", [])
            except json.JSONDecodeError:
                pass  # Fall through to default patterns
        return [
            "you are dan", "do anything now", "ignore all previous",
            "ignore your instructions", "system override", "bypass your guidelines"
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
            risk_type="jailbreak",
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

        # Check for jailbreak attempts in incoming messages
        if log_entry.step_type == "receive":
            detected = [p for p in self.jailbreak_patterns if p.lower() in content]
            if detected and self.config.get("alert_on_attempt", True):
                alert = Alert(
                    severity="warning",
                    risk_type="jailbreak",
                    message=f"Jailbreak pattern detected (fallback mode)",
                    evidence={
                        "agent": log_entry.agent_name,
                        "detected_by": "pattern_matching",
                        "patterns": detected,
                        "content_preview": content[:200]
                    },
                    recommended_action="warn",
                    timestamp=log_entry.timestamp
                )
                self._record_alert(alert)
                return alert

        # Check for compromise indicators in responses
        elif log_entry.step_type == "respond":
            detected = [i for i in self.compromise_indicators if i in content]
            if detected:
                alert = Alert(
                    severity="critical",
                    risk_type="jailbreak",
                    message=f"Agent may be compromised (fallback mode)",
                    evidence={
                        "agent": log_entry.agent_name,
                        "detected_by": "pattern_matching",
                        "indicators": detected,
                        "content_preview": content[:200]
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
