"""L2 Identity Spoofing Monitor Implementation."""

import re
from typing import Optional, Dict, List, Set

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class IdentitySpoofingMonitor(BaseMonitorAgent):
    """Runtime monitor for identity spoofing.

    Monitors for:
    - Agent impersonation
    - Authority claims
    - Identity confusion
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "track_identities": True,
            "verify_claims": True
        }
        self.known_agents: Set[str] = set()
        self.authority_claims: Dict[str, List[str]] = {}

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "IdentitySpoofingMonitor",
            "risk_type": "identity_spoofing",
            "description": "Monitors for identity spoofing attempts"
        }

    def register_agent(self, agent_name: str):
        """Register a known valid agent."""
        self.known_agents.add(agent_name.lower())

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        content = str(log_entry.content).lower()
        agent_name = log_entry.agent_name

        impersonation_patterns = [
            r"i am (?:agent )?(\w+)",
            r"this is (\w+) speaking",
            r"pretend(?:ing)? to be (\w+)",
            r"acting as (\w+)"
        ]

        authority_patterns = [
            r"i am (?:the )?admin",
            r"system administrator",
            r"elevated (?:access|privileges)",
            r"root access",
            r"master key"
        ]

        for pattern in impersonation_patterns:
            match = re.search(pattern, content)
            if match:
                claimed_identity = match.group(1).lower()
                if claimed_identity != agent_name.lower():
                    if self.known_agents and claimed_identity in self.known_agents:
                        alert = Alert(
                            severity="critical",
                            risk_type="identity_spoofing",
                            message=f"Agent {agent_name} attempting to impersonate {claimed_identity}",
                            evidence={
                                "agent": agent_name,
                                "claimed_identity": claimed_identity,
                                "content_preview": content[:200]
                            },
                            recommended_action="block",
                            timestamp=log_entry.timestamp
                        )
                        self._record_alert(alert)
                        return alert

        for pattern in authority_patterns:
            if re.search(pattern, content):
                if agent_name not in self.authority_claims:
                    self.authority_claims[agent_name] = []
                self.authority_claims[agent_name].append(content[:100])

                alert = Alert(
                    severity="warning",
                    risk_type="identity_spoofing",
                    message=f"Unverified authority claim detected involving {agent_name}",
                    evidence={
                        "agent": agent_name,
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
