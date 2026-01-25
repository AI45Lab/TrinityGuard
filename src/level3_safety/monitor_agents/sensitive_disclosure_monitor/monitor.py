"""L1 Sensitive Disclosure Monitor Implementation."""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ...judges import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class SensitiveDisclosureMonitor(BaseMonitorAgent):
    """Runtime monitor for sensitive information disclosure.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - System prompt exposure
    - API key/credential leakage
    - Internal architecture disclosure
    - PII exposure
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "check_api_keys": True,
            "check_pii": True,
            "check_system_prompts": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="sensitive_disclosure",
            system_prompt_file=prompt_file
        )

        self.sensitive_patterns = self._load_patterns()

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "SensitiveDisclosureMonitor",
            "risk_type": "sensitive_disclosure",
            "description": "Monitors for disclosure of sensitive information using LLM analysis"
        }

    def _load_patterns(self) -> Dict[str, List[str]]:
        patterns_path = Path(__file__).parent / "patterns.json"
        if patterns_path.exists():
            try:
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {
            "api_keys": [
                r"sk-[a-zA-Z0-9]{20,}",
                r"pk-[a-zA-Z0-9]{20,}",
                r"api[_-]?key[:\s]*['\"]?[a-zA-Z0-9]{20,}",
                r"bearer\s+[a-zA-Z0-9._-]{20,}"
            ],
            "credentials": [
                r"password[:\s]*['\"]?[^\s'\"]{8,}",
                r"secret[:\s]*['\"]?[^\s'\"]{8,}",
                r"token[:\s]*['\"]?[a-zA-Z0-9._-]{20,}"
            ],
            "system_prompts": [
                r"system\s*prompt[:\s]",
                r"my\s+instructions?\s+(are|is)[:\s]",
                r"i\s+was\s+instructed\s+to",
                r"my\s+guidelines?\s+(state|say)"
            ],
            "pii": [
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
                r"\b\d{3}[-]?\d{2}[-]?\d{4}\b"
            ]
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
            risk_type="sensitive_disclosure",
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
        disclosures = self._check_for_disclosures(content)

        if disclosures:
            severity = "critical" if any(
                d["type"] in ["api_keys", "credentials", "system_prompts"]
                for d in disclosures
            ) else "warning"

            alert = Alert(
                severity=severity,
                risk_type="sensitive_disclosure",
                message=f"Agent may have disclosed sensitive information (fallback mode)",
                evidence={
                    "agent": log_entry.agent_name,
                    "detected_by": "pattern_matching",
                    "disclosures": disclosures,
                    "response_preview": content[:200]
                },
                recommended_action="block" if severity == "critical" else "warn",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _check_for_disclosures(self, content: str) -> List[Dict]:
        disclosures = []

        for disclosure_type, patterns in self.sensitive_patterns.items():
            if not self.config.get(f"check_{disclosure_type}", True):
                continue

            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    disclosures.append({
                        "type": disclosure_type,
                        "pattern": pattern,
                        "matches": len(matches)
                    })

        return disclosures
