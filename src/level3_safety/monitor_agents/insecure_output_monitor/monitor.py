"""L2 Insecure Output Monitor Implementation."""

import re
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class InsecureOutputMonitor(BaseMonitorAgent):
    """Runtime monitor for insecure output patterns.

    Monitors for:
    - XSS patterns
    - SQL injection
    - Command injection
    - Path traversal
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "check_xss": True,
            "check_sql": True,
            "check_command": True,
            "check_path": True
        }

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "InsecureOutputMonitor",
            "risk_type": "insecure_output",
            "description": "Monitors for insecure output that could enable injection attacks"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        if log_entry.step_type != "respond":
            return None

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
                message=f"Insecure output patterns detected in {log_entry.agent_name}'s response",
                evidence={
                    "agent": log_entry.agent_name,
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
            xss_patterns = [
                r"<script[^>]*>", r"javascript:", r"on\w+\s*=",
                r"<iframe", r"<object", r"<embed"
            ]
            for pattern in xss_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({"type": "xss", "pattern": pattern})
                    break

        if self.config.get("check_sql", True):
            sql_patterns = [
                r"'\s*or\s*'", r"'\s*or\s+\d+\s*=\s*\d+",
                r";\s*drop\s+table", r";\s*delete\s+from",
                r"union\s+select"
            ]
            for pattern in sql_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({"type": "sql_injection", "pattern": pattern})
                    break

        if self.config.get("check_command", True):
            cmd_patterns = [
                r";\s*rm\s+-rf", r"\|\s*bash", r"`[^`]+`",
                r"\$\([^)]+\)", r";\s*cat\s+/etc"
            ]
            for pattern in cmd_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({"type": "command_injection", "pattern": pattern})
                    break

        if self.config.get("check_path", True):
            path_patterns = [
                r"\.\./\.\./", r"\.\.\\\.\.\\",
                r"/etc/passwd", r"/etc/shadow"
            ]
            for pattern in path_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    vulnerabilities.append({"type": "path_traversal", "pattern": pattern})
                    break

        return vulnerabilities
