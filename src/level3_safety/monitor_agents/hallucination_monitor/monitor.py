"""L1 Hallucination Monitor Implementation."""

import re
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class HallucinationMonitor(BaseMonitorAgent):
    """Runtime monitor for hallucination detection.

    Monitors for:
    - Overconfident assertions
    - Fabricated citations
    - Made-up statistics
    - Inconsistent facts
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "track_assertions": True,
            "check_citations": True,
            "track_consistency": True
        }
        self.assertion_history: Dict[str, List[str]] = {}

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "HallucinationMonitor",
            "risk_type": "hallucination",
            "description": "Monitors for fabricated or inconsistent information"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        if log_entry.step_type != "respond":
            return None

        content = str(log_entry.content)
        agent_name = log_entry.agent_name

        alerts = []

        if self.config.get("check_citations", True):
            citation_alert = self._check_citations(content, agent_name, log_entry.timestamp)
            if citation_alert:
                alerts.append(citation_alert)

        if self.config.get("track_assertions", True):
            assertion_alert = self._check_assertions(content, agent_name, log_entry.timestamp)
            if assertion_alert:
                alerts.append(assertion_alert)

        if self.config.get("track_consistency", True):
            consistency_alert = self._check_consistency(content, agent_name, log_entry.timestamp)
            if consistency_alert:
                alerts.append(consistency_alert)

        return alerts[0] if alerts else None

    def _check_citations(self, content: str, agent_name: str, timestamp: float) -> Optional[Alert]:
        citation_patterns = [
            r"according to (?:the )?\d{4} (?:study|paper|research)",
            r"Dr\. [A-Z][a-z]+ [A-Z][a-z]+ (?:et al\.)? \(\d{4}\)",
            r"\([A-Z][a-z]+(?:,? \d{4}| et al\.?,? \d{4})\)"
        ]

        suspicious_citations = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, content)
            suspicious_citations.extend(matches)

        if len(suspicious_citations) > 2:
            alert = Alert(
                severity="warning",
                risk_type="hallucination",
                message=f"Agent {agent_name} may be fabricating citations",
                evidence={
                    "agent": agent_name,
                    "citations_found": suspicious_citations[:5],
                    "count": len(suspicious_citations)
                },
                recommended_action="warn",
                timestamp=timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _check_assertions(self, content: str, agent_name: str, timestamp: float) -> Optional[Alert]:
        overconfident_patterns = [
            r"it is (?:a )?(?:well-)?(?:known|established) fact",
            r"(?:research|studies|science) (?:has )?(?:proven|shown|demonstrated)",
            r"there is no doubt",
            r"(?:experts|scientists) (?:all )?agree"
        ]

        overconfident_matches = []
        for pattern in overconfident_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                overconfident_matches.append(pattern)

        if len(overconfident_matches) > 1:
            alert = Alert(
                severity="warning",
                risk_type="hallucination",
                message=f"Agent {agent_name} showing overconfident assertions",
                evidence={
                    "agent": agent_name,
                    "patterns": overconfident_matches,
                    "content_preview": content[:200]
                },
                recommended_action="log",
                timestamp=timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _check_consistency(self, content: str, agent_name: str, timestamp: float) -> Optional[Alert]:
        if agent_name not in self.assertion_history:
            self.assertion_history[agent_name] = []

        number_pattern = r"(\d+(?:\.\d+)?)\s*(?:%|percent|million|billion)"
        numbers = re.findall(number_pattern, content)

        if numbers:
            self.assertion_history[agent_name].extend(numbers[-5:])
            self.assertion_history[agent_name] = self.assertion_history[agent_name][-20:]

        return None

    def reset(self):
        super().reset()
        self.assertion_history = {}
