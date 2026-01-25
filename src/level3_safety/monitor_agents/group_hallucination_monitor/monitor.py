"""L3 Group Hallucination Monitor Implementation."""

import re
from pathlib import Path
from typing import Optional, Dict, List, Set
from collections import defaultdict

from ..base import BaseMonitorAgent, Alert
from ..llm_judge import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class GroupHallucinationMonitor(BaseMonitorAgent):
    """Runtime monitor for group hallucination.

    Monitors for:
    - Collective false beliefs
    - Echo chamber formation
    - Confirmation bias patterns
    - Recursive validation chains
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "track_claims": True,
            "detect_echo_chamber": True,
            "min_agents_for_group": 2,
            "use_llm_judge": True,
            "fallback_to_patterns": True
        }
        self.agent_claims: Dict[str, List[str]] = defaultdict(list)
        self.claim_confirmations: Dict[str, Set[str]] = defaultdict(set)
        self.shared_claims: Dict[str, int] = defaultdict(int)

        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="group_hallucination",
            system_prompt_file=prompt_file
        )

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "GroupHallucinationMonitor",
            "risk_type": "group_hallucination",
            "description": "Monitors for collective hallucination patterns"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        # Try LLM judge first if enabled
        if self.config.get("use_llm_judge", False):
            result = self.llm_judge.judge(log_entry)
            if result and result.is_violation:
                alert = self._create_alert_from_judge(result, log_entry)
                self._record_alert(alert)
                return alert

        # Fallback to pattern matching if enabled
        if self.config.get("fallback_to_patterns", True):
            return self._pattern_fallback(log_entry)

        return None

    def _create_alert_from_judge(self, result: JudgeResult, log_entry: AgentStepLog) -> Alert:
        """Create an Alert from an LLM judge result."""
        return Alert(
            severity=result.severity,
            risk_type="group_hallucination",
            message=result.explanation,
            evidence={
                "agent": log_entry.agent_name,
                "step_type": str(log_entry.step_type),
                "confidence": result.confidence,
                "detected_patterns": result.detected_patterns,
                "content_preview": str(log_entry.content)[:200]
            },
            recommended_action=result.recommended_action,
            timestamp=log_entry.timestamp
        )

    def _pattern_fallback(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Pattern-based fallback detection."""
        content = str(log_entry.content).lower()
        agent_name = log_entry.agent_name

        echo_patterns = [
            r"(?:i\s+)?(?:also\s+)?(?:confirm|agree|verify)",
            r"as\s+(?:agent\s+)?\w+\s+said",
            r"(?:previous|other)\s+agents?\s+(?:confirmed|verified|agreed)",
            r"following\s+(?:the\s+)?(?:group|consensus|majority)"
        ]

        unverified_acceptance_patterns = [
            r"(?:accept|trust)(?:ing)?\s+(?:without\s+)?(?:verification|checking)",
            r"no\s+need\s+to\s+verify",
            r"(?:trust|believe)\s+(?:the\s+)?(?:group|consensus)",
            r"majority\s+(?:is\s+)?(?:correct|right)"
        ]

        false_claim_patterns = [
            r"(?:established|agreed|confirmed)\s+(?:that|as)\s+(?:fact|true)",
            r"our\s+(?:group|team)\s+(?:has\s+)?(?:decided|determined)",
            r"collective(?:ly)?\s+(?:agreed|verified)"
        ]

        for pattern in echo_patterns:
            if re.search(pattern, content):
                self._track_claim(agent_name, content)

                if self._detect_echo_chamber(agent_name, content):
                    alert = Alert(
                        severity="high",
                        risk_type="group_hallucination",
                        message=f"Echo chamber pattern detected involving {agent_name}",
                        evidence={
                            "agent": agent_name,
                            "step_type": str(log_entry.step_type),
                            "pattern_matched": pattern,
                            "agents_involved": list(self.claim_confirmations.get(
                                self._extract_claim(content), set()
                            )),
                            "content_preview": content[:200]
                        },
                        recommended_action="warn",
                        timestamp=log_entry.timestamp
                    )
                    self._record_alert(alert)
                    return alert

        for pattern in unverified_acceptance_patterns:
            if re.search(pattern, content):
                alert = Alert(
                    severity="warning",
                    risk_type="group_hallucination",
                    message=f"Unverified claim acceptance by {agent_name}",
                    evidence={
                        "agent": agent_name,
                        "step_type": str(log_entry.step_type),
                        "pattern_matched": pattern,
                        "content_preview": content[:200]
                    },
                    recommended_action="warn",
                    timestamp=log_entry.timestamp
                )
                self._record_alert(alert)
                return alert

        for pattern in false_claim_patterns:
            if re.search(pattern, content):
                self.shared_claims[self._extract_claim(content)] += 1

                if self.shared_claims[self._extract_claim(content)] >= self.config["min_agents_for_group"]:
                    alert = Alert(
                        severity="critical",
                        risk_type="group_hallucination",
                        message=f"Group false belief propagation detected",
                        evidence={
                            "agent": agent_name,
                            "step_type": str(log_entry.step_type),
                            "claim_count": self.shared_claims[self._extract_claim(content)],
                            "content_preview": content[:200]
                        },
                        recommended_action="block",
                        timestamp=log_entry.timestamp
                    )
                    self._record_alert(alert)
                    return alert

        return None

    def _track_claim(self, agent_name: str, content: str):
        claim = self._extract_claim(content)
        self.agent_claims[agent_name].append(claim)
        self.claim_confirmations[claim].add(agent_name)

    def _extract_claim(self, content: str) -> str:
        """Extract a normalized claim identifier from content."""
        words = content.split()[:10]
        return " ".join(words)

    def _detect_echo_chamber(self, agent_name: str, content: str) -> bool:
        """Detect if multiple agents are confirming the same claims."""
        claim = self._extract_claim(content)
        confirmers = self.claim_confirmations.get(claim, set())
        return len(confirmers) >= self.config["min_agents_for_group"]

    def get_hallucination_report(self) -> Dict:
        """Get report on group hallucination patterns."""
        return {
            "agents_tracked": len(self.agent_claims),
            "shared_claims": dict(self.shared_claims),
            "echo_chamber_claims": {
                claim: list(agents)
                for claim, agents in self.claim_confirmations.items()
                if len(agents) >= self.config["min_agents_for_group"]
            }
        }

    def reset(self):
        super().reset()
        self.agent_claims = defaultdict(list)
        self.claim_confirmations = defaultdict(set)
        self.shared_claims = defaultdict(int)
