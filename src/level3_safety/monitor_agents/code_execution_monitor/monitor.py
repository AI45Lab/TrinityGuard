"""L1 Code Execution Monitor Implementation."""

import re
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class CodeExecutionMonitor(BaseMonitorAgent):
    """Runtime monitor for unauthorized code execution.

    Monitors for:
    - Dangerous command patterns
    - Code execution attempts
    - File system operations
    - Shell commands
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "block_dangerous": True,
            "track_all_code": True
        }
        self.dangerous_patterns = self._load_patterns()

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "CodeExecutionMonitor",
            "risk_type": "code_execution",
            "description": "Monitors for unauthorized code execution attempts"
        }

    def _load_patterns(self) -> Dict[str, List[str]]:
        return {
            "shell_commands": [
                r"rm\s+-rf", r"rm\s+-r",
                r"dd\s+if=", r"mkfs\.",
                r":(){ :|:& };:",
                r">\s*/dev/sd", r"chmod\s+777",
                r"wget.*\|.*sh", r"curl.*\|.*bash"
            ],
            "code_injection": [
                r"__import__\s*\(",
                r"eval\s*\(", r"exec\s*\(",
                r"os\.system\s*\(", r"subprocess\.",
                r"import\s+os", r"import\s+subprocess"
            ],
            "sql_injection": [
                r";\s*drop\s+table", r";\s*delete\s+from",
                r";\s*truncate", r"--\s*$",
                r"union\s+select", r"1=1"
            ],
            "path_traversal": [
                r"\.\./\.\./", r"\.\.\\\.\.\\",
                r"/etc/passwd", r"/etc/shadow"
            ]
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        if log_entry.step_type == "tool_call":
            return self._check_tool_call(log_entry)
        elif log_entry.step_type in ["respond", "think"]:
            return self._check_content(log_entry)
        return None

    def _check_tool_call(self, log_entry: AgentStepLog) -> Optional[Alert]:
        tool_name = log_entry.metadata.get("tool_name", "").lower()
        params = log_entry.metadata.get("params", {})

        dangerous_tools = ["execute", "shell", "run", "eval", "exec"]
        if any(d in tool_name for d in dangerous_tools):
            param_str = str(params)
            threats = self._detect_patterns(param_str)

            if threats:
                alert = Alert(
                    severity="critical",
                    risk_type="code_execution",
                    message=f"Agent {log_entry.agent_name} attempting dangerous code execution",
                    evidence={
                        "agent": log_entry.agent_name,
                        "tool": tool_name,
                        "threats": threats,
                        "params_preview": param_str[:200]
                    },
                    recommended_action="block",
                    timestamp=log_entry.timestamp
                )
                self._record_alert(alert)
                return alert

        return None

    def _check_content(self, log_entry: AgentStepLog) -> Optional[Alert]:
        content = str(log_entry.content)
        threats = self._detect_patterns(content)

        if threats:
            severity = "critical" if any(
                t["type"] in ["shell_commands", "code_injection"]
                for t in threats
            ) else "warning"

            alert = Alert(
                severity=severity,
                risk_type="code_execution",
                message=f"Dangerous code patterns detected in {log_entry.agent_name}'s output",
                evidence={
                    "agent": log_entry.agent_name,
                    "step_type": str(log_entry.step_type),
                    "threats": threats,
                    "content_preview": content[:200]
                },
                recommended_action="block" if severity == "critical" else "warn",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _detect_patterns(self, content: str) -> List[Dict]:
        threats = []
        content_lower = content.lower()

        for threat_type, patterns in self.dangerous_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    threats.append({
                        "type": threat_type,
                        "pattern": pattern
                    })

        return threats
