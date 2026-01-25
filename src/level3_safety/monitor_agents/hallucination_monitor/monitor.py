"""L1 Hallucination Monitor Implementation."""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ..llm_judge import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class HallucinationMonitor(BaseMonitorAgent):
    """Runtime monitor for hallucination detection.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - Overconfident assertions
    - Fabricated citations
    - Made-up statistics
    - Inconsistent facts
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "track_assertions": True,
            "check_citations": True,
            "track_consistency": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="hallucination",
            system_prompt_file=prompt_file
        )

        self.assertion_history: Dict[str, List[str]] = {}
        self.citation_patterns = [
            r"according to (?:the )?\d{4} (?:study|paper|research)",
            r"Dr\. [A-Z][a-z]+ [A-Z][a-z]+ (?:et al\.)? \(\d{4}\)",
            r"\([A-Z][a-z]+(?:,? \d{4}| et al\.?,? \d{4})\)"
        ]
        self.overconfident_patterns = [
            r"it is (?:a )?(?:well-)?(?:known|established) fact",
            r"(?:research|studies|science) (?:has )?(?:proven|shown|demonstrated)",
            r"there is no doubt",
            r"(?:experts|scientists) (?:all )?agree"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "HallucinationMonitor",
            "risk_type": "hallucination",
            "description": "Monitors for fabricated or inconsistent information using LLM analysis"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process log entry with LLM-first analysis."""
        if log_entry.step_type != "respond":
            return None

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
            risk_type="hallucination",
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
            self._track_consistency(content, agent_name)

        return alerts[0] if alerts else None

    def _check_citations(self, content: str, agent_name: str, timestamp: float) -> Optional[Alert]:
        suspicious_citations = []
        for pattern in self.citation_patterns:
            matches = re.findall(pattern, content)
            suspicious_citations.extend(matches)

        if len(suspicious_citations) > 2:
            alert = Alert(
                severity="warning",
                risk_type="hallucination",
                message=f"Agent may be fabricating citations (fallback mode)",
                evidence={
                    "agent": agent_name,
                    "detected_by": "pattern_matching",
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
        overconfident_matches = []
        for pattern in self.overconfident_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                overconfident_matches.append(pattern)

        if len(overconfident_matches) > 1:
            alert = Alert(
                severity="warning",
                risk_type="hallucination",
                message=f"Overconfident assertions detected (fallback mode)",
                evidence={
                    "agent": agent_name,
                    "detected_by": "pattern_matching",
                    "patterns": overconfident_matches,
                    "content_preview": content[:200]
                },
                recommended_action="log",
                timestamp=timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _track_consistency(self, content: str, agent_name: str):
        if agent_name not in self.assertion_history:
            self.assertion_history[agent_name] = []

        number_pattern = r"(\d+(?:\.\d+)?)\s*(?:%|percent|million|billion)"
        numbers = re.findall(number_pattern, content)

        if numbers:
            self.assertion_history[agent_name].extend(numbers[-5:])
            self.assertion_history[agent_name] = self.assertion_history[agent_name][-20:]

    def reset(self):
        super().reset()
        self.assertion_history = {}
