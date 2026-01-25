"""L1 Sensitive Disclosure Monitor Implementation."""

import re
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class SensitiveDisclosureMonitor(BaseMonitorAgent):
    """Runtime monitor for sensitive information disclosure.

    Monitors for:
    - System prompt exposure
    - API key/credential leakage
    - Internal architecture disclosure
    - PII exposure
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "check_api_keys": True,
            "check_pii": True,
            "check_system_prompts": True
        }
        self.sensitive_patterns = self._load_patterns()

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "SensitiveDisclosureMonitor",
            "risk_type": "sensitive_disclosure",
            "description": "Monitors for disclosure of sensitive information in agent responses"
        }

    def _load_patterns(self) -> Dict[str, List[str]]:
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
        if log_entry.step_type != "respond":
            return None

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
                message=f"Agent {log_entry.agent_name} may have disclosed sensitive information",
                evidence={
                    "agent": log_entry.agent_name,
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
