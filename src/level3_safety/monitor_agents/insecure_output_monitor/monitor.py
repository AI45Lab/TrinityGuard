"""L2 Insecure Output Monitor Implementation."""

import json
import re
from pathlib import Path
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ...judges import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class InsecureOutputMonitor(BaseMonitorAgent):
    """Runtime monitor for insecure output patterns.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - XSS patterns
    - SQL injection
    - Command injection
    - Path traversal
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "check_xss": True,
            "check_sql": True,
            "check_command": True,
            "check_path": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="insecure_output",
            system_prompt_file=prompt_file
        )

        self.xss_patterns = [
            r"<script[^>]*>", r"javascript:", r"on\w+\s*=",
            r"<iframe", r"<object", r"<embed"
        ]
        self.sql_patterns = [
            r"'\s*or\s*'", r"'\s*or\s+\d+\s*=\s*\d+",
            r";\s*drop\s+table", r";\s*delete\s+from",
            r"union\s+select"
        ]
        self.cmd_patterns = [
            r";\s*rm\s+-rf", r"\|\s*bash", r"`[^`]+`",
            r"\$\([^)]+\)", r";\s*cat\s+/etc"
        ]
        self.path_patterns = [
            r"\.\./\.\./", r"\.\.\\\.\.\\",
            r"/etc/passwd", r"/etc/shadow"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "InsecureOutputMonitor",
            "risk_type": "insecure_output",
            "description": "Monitors for insecure output patterns using LLM analysis"
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
            risk_type="insecure_output",
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
        vulnerabilities = self._check_for_vulnerabilities(content)

        if vulnerabilities:
            severity = "critical" if any(
                v["type"] in ["sql_injection", "command_injection"]
                for v in vulnerabilities
            ) else "warning"

            alert = Alert(
                severity=severity,
                risk_type="insecure_output",
                message=f"Insecure output patterns detected (fallback mode)",
                evidence={
                    "agent": log_entry.agent_name,
                    "detected_by": "pattern_matching",
                    "vulnerabilities": vulnerabilities,
                    "content_preview": content[:200]
                },
                recommended_action="block" if severity == "critical" else "warn",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _check_for_vulnerabilities(self, content: str) -> List[Dict]:
        vulnerabilities = []

        if self.config.get("check_xss", True):
            for pattern in self.xss_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({"type": "xss", "pattern": pattern})
                    break

        if self.config.get("check_sql", True):
            for pattern in self.sql_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({"type": "sql_injection", "pattern": pattern})
                    break

        if self.config.get("check_command", True):
            for pattern in self.cmd_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({"type": "command_injection", "pattern": pattern})
                    break

        if self.config.get("check_path", True):
            for pattern in self.path_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({"type": "path_traversal", "pattern": pattern})
                    break

        return vulnerabilities
