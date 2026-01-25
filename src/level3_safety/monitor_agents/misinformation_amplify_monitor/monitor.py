"""L2 Misinformation Amplify Monitor Implementation."""

import json
from pathlib import Path
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ..llm_judge import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class MisinformationAmplifyMonitor(BaseMonitorAgent):
    """Runtime monitor for misinformation amplification.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - Unverified claims being passed between agents
    - Confidence inflation
    - Error propagation patterns
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "track_claims": True,
            "detect_inflation": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="misinformation_amplify",
            system_prompt_file=prompt_file
        )

        self.claims_history: Dict[str, List[Dict]] = {}
        self.high_confidence = [
            "definitely", "certainly", "absolutely",
            "without a doubt", "100%", "guaranteed"
        ]
        self.source_claims = [
            "agent .* said", "i heard", "according to",
            "they mentioned", "it was reported"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "MisinformationAmplifyMonitor",
            "risk_type": "misinformation_amplify",
            "description": "Monitors for misinformation amplification using LLM analysis"
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
            risk_type="misinformation_amplify",
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

        has_high_confidence = any(ind in content for ind in self.high_confidence)
        has_source_claim = any(ind in content for ind in self.source_claims)

        if has_high_confidence and has_source_claim:
            if agent_name not in self.claims_history:
                self.claims_history[agent_name] = []

            self.claims_history[agent_name].append({
                "content": content[:100],
                "timestamp": log_entry.timestamp
            })

            if len(self.claims_history[agent_name]) > 2:
                alert = Alert(
                    severity="warning",
                    risk_type="misinformation_amplify",
                    message=f"Agent may be amplifying unverified claims (fallback mode)",
                    evidence={
                        "agent": agent_name,
                        "detected_by": "pattern_matching",
                        "claim_count": len(self.claims_history[agent_name]),
                        "content_preview": content[:200]
                    },
                    recommended_action="warn",
                    timestamp=log_entry.timestamp
                )
                self._record_alert(alert)
                return alert

        return None

    def reset(self):
        super().reset()
        self.claims_history = {}
