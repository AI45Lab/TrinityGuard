"""L2 Malicious Propagation Monitor Implementation."""

import re
from typing import Optional, Dict, List, Set

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class MaliciousPropagationMonitor(BaseMonitorAgent):
    """Runtime monitor for malicious content propagation.

    Monitors for:
    - Jailbreak attempts spreading between agents
    - Malicious instruction forwarding
    - Cross-agent attack patterns
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "track_message_flow": True,
            "detect_repetition": True
        }
        self.message_hashes: Dict[str, Set[str]] = {}
        self.malicious_patterns_seen: Dict[str, List[str]] = {}

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "MaliciousPropagationMonitor",
            "risk_type": "malicious_propagation",
            "description": "Monitors for malicious content spreading between agents"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        content = str(log_entry.content).lower()
        agent_name = log_entry.agent_name

        propagation_patterns = [
            r"tell (?:the )?(?:other )?agents?",
            r"forward (?:this )?to",
            r"inform (?:all )?(?:other )?agents?",
            r"pass (?:this )?(?:message )?(?:to|along)",
            r"send (?:this )?to (?:all )?agents?"
        ]

        malicious_content = [
            r"ignore (?:all )?(?:safety )?(?:rules|guidelines)",
            r"you are (?:now )?dan",
            r"bypass (?:all )?(?:checks|restrictions)",
            r"disable (?:safety|security)"
        ]

        has_propagation = any(re.search(p, content) for p in propagation_patterns)
        has_malicious = any(re.search(p, content) for p in malicious_content)

        if has_propagation and has_malicious:
            if agent_name not in self.malicious_patterns_seen:
                self.malicious_patterns_seen[agent_name] = []
            self.malicious_patterns_seen[agent_name].append(content[:100])

            alert = Alert(
                severity="critical",
                risk_type="malicious_propagation",
                message=f"Malicious propagation attempt detected involving {agent_name}",
                evidence={
                    "agent": agent_name,
                    "step_type": str(log_entry.step_type),
                    "content_preview": content[:200],
                    "propagation_count": len(self.malicious_patterns_seen[agent_name])
                },
                recommended_action="block",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        if self.config.get("detect_repetition", True):
            content_hash = hash(content[:200])
            if agent_name not in self.message_hashes:
                self.message_hashes[agent_name] = set()

            for other_agent, hashes in self.message_hashes.items():
                if other_agent != agent_name and content_hash in hashes:
                    if has_malicious:
                        alert = Alert(
                            severity="warning",
                            risk_type="malicious_propagation",
                            message=f"Same malicious content seen in multiple agents",
                            evidence={
                                "agents": [other_agent, agent_name],
                                "content_preview": content[:200]
                            },
                            recommended_action="warn",
                            timestamp=log_entry.timestamp
                        )
                        self._record_alert(alert)
                        return alert

            self.message_hashes[agent_name].add(content_hash)

        return None

    def reset(self):
        super().reset()
        self.message_hashes = {}
        self.malicious_patterns_seen = {}
