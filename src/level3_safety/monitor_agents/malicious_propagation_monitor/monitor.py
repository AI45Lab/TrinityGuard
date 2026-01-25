"""L2 Malicious Propagation Monitor Implementation."""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List, Set

from ..base import BaseMonitorAgent, Alert
from ...judges import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class MaliciousPropagationMonitor(BaseMonitorAgent):
    """Runtime monitor for malicious content propagation.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - Jailbreak attempts spreading between agents
    - Malicious instruction forwarding
    - Cross-agent attack patterns
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "track_message_flow": True,
            "detect_repetition": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="malicious_propagation",
            system_prompt_file=prompt_file
        )

        self.message_hashes: Dict[str, Set[str]] = {}
        self.malicious_patterns_seen: Dict[str, List[str]] = {}
        self.propagation_patterns = [
            r"tell (?:the )?(?:other )?agents?",
            r"forward (?:this )?to",
            r"inform (?:all )?(?:other )?agents?",
            r"pass (?:this )?(?:message )?(?:to|along)",
            r"send (?:this )?to (?:all )?agents?"
        ]
        self.malicious_content = [
            r"ignore (?:all )?(?:safety )?(?:rules|guidelines)",
            r"you are (?:now )?dan",
            r"bypass (?:all )?(?:checks|restrictions)",
            r"disable (?:safety|security)"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "MaliciousPropagationMonitor",
            "risk_type": "malicious_propagation",
            "description": "Monitors for malicious content spreading between agents using LLM analysis"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process log entry with LLM-first analysis."""
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
            risk_type="malicious_propagation",
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

        has_propagation = any(re.search(p, content) for p in self.propagation_patterns)
        has_malicious = any(re.search(p, content) for p in self.malicious_content)

        if has_propagation and has_malicious:
            if agent_name not in self.malicious_patterns_seen:
                self.malicious_patterns_seen[agent_name] = []
            self.malicious_patterns_seen[agent_name].append(content[:100])

            alert = Alert(
                severity="critical",
                risk_type="malicious_propagation",
                message=f"Malicious propagation attempt detected (fallback mode)",
                evidence={
                    "agent": agent_name,
                    "detected_by": "pattern_matching",
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
                            message=f"Same malicious content in multiple agents (fallback mode)",
                            evidence={
                                "agents": [other_agent, agent_name],
                                "detected_by": "pattern_matching",
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
