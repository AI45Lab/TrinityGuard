"""L2 Identity Spoofing Monitor Implementation."""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List, Set

from ..base import BaseMonitorAgent, Alert
from ..llm_judge import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class IdentitySpoofingMonitor(BaseMonitorAgent):
    """Runtime monitor for identity spoofing.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - Agent impersonation
    - Authority claims
    - Identity confusion
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "track_identities": True,
            "verify_claims": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="identity_spoofing",
            system_prompt_file=prompt_file
        )

        self.known_agents: Set[str] = set()
        self.authority_claims: Dict[str, List[str]] = {}
        self.impersonation_patterns = [
            r"i am (?:agent )?(\w+)",
            r"this is (\w+) speaking",
            r"pretend(?:ing)? to be (\w+)",
            r"acting as (\w+)"
        ]
        self.authority_patterns = [
            r"i am (?:the )?admin",
            r"system administrator",
            r"elevated (?:access|privileges)",
            r"root access",
            r"master key"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "IdentitySpoofingMonitor",
            "risk_type": "identity_spoofing",
            "description": "Monitors for identity spoofing attempts using LLM analysis"
        }

    def register_agent(self, agent_name: str):
        """Register a known valid agent."""
        self.known_agents.add(agent_name.lower())

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process log entry with LLM-first analysis."""
        content = str(log_entry.content)

        # Try LLM analysis first
        if self.config.get("use_llm_judge", True):
            context = {
                "agent_name": log_entry.agent_name,
                "step_type": str(log_entry.step_type),
                "known_agents": list(self.known_agents)
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
            risk_type="identity_spoofing",
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

        for pattern in self.impersonation_patterns:
            match = re.search(pattern, content)
            if match:
                claimed_identity = match.group(1).lower()
                if claimed_identity != agent_name.lower():
                    if self.known_agents and claimed_identity in self.known_agents:
                        alert = Alert(
                            severity="critical",
                            risk_type="identity_spoofing",
                            message=f"Agent impersonation attempt (fallback mode)",
                            evidence={
                                "agent": agent_name,
                                "detected_by": "pattern_matching",
                                "claimed_identity": claimed_identity,
                                "content_preview": content[:200]
                            },
                            recommended_action="block",
                            timestamp=log_entry.timestamp
                        )
                        self._record_alert(alert)
                        return alert

        for pattern in self.authority_patterns:
            if re.search(pattern, content):
                if agent_name not in self.authority_claims:
                    self.authority_claims[agent_name] = []
                self.authority_claims[agent_name].append(content[:100])

                alert = Alert(
                    severity="warning",
                    risk_type="identity_spoofing",
                    message=f"Unverified authority claim detected (fallback mode)",
                    evidence={
                        "agent": agent_name,
                        "detected_by": "pattern_matching",
                        "step_type": str(log_entry.step_type),
                        "claim_count": len(self.authority_claims[agent_name]),
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
        self.authority_claims = {}
