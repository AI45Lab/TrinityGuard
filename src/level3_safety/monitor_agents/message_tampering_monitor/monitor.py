"""L2 Message Tampering Monitor Implementation."""

from typing import Optional, Dict, List
import time
import hashlib

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class MessageTamperingMonitor(BaseMonitorAgent):
    """Detect message tampering via consistency checks.

    Monitors for:
    - Unexpected content patterns in messages
    - Message integrity violations
    - Anomalous content injection
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "track_message_hashes": True,
            "detect_injection_patterns": True,
            "max_message_history": 100
        }
        self.state = {
            "message_hashes": {},
            "message_history": [],
            "anomaly_count": 0
        }

    def get_monitor_info(self) -> Dict[str, str]:
        """Return monitor metadata."""
        return {
            "name": "MessageTamperingMonitor",
            "risk_type": "message_tampering",
            "description": "Monitors for message tampering and content injection"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process a log entry and detect tampering."""

        if log_entry.step_type == "receive":
            return self._check_incoming_message(log_entry)

        return None

    def _check_incoming_message(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check incoming message for tampering indicators."""
        content = str(log_entry.content)
        agent_name = log_entry.agent_name

        alerts = []

        # Check for injection patterns
        if self.config.get("detect_injection_patterns", True):
            injection_alert = self._detect_injection_patterns(content, agent_name, log_entry.timestamp)
            if injection_alert:
                return injection_alert

        # Track message for integrity
        if self.config.get("track_message_hashes", True):
            self._track_message(content, agent_name, log_entry.timestamp)

        # Check for anomalous content
        anomaly_alert = self._detect_anomalous_content(content, agent_name, log_entry.timestamp)
        if anomaly_alert:
            return anomaly_alert

        return None

    def _detect_injection_patterns(self, content: str, agent_name: str, timestamp: float) -> Optional[Alert]:
        """Detect known injection patterns in content."""
        content_lower = content.lower()

        # SQL injection patterns
        sql_patterns = [
            "drop table",
            "delete from",
            "insert into",
            "union select",
            "'; --",
            "or 1=1"
        ]

        # Command injection patterns
        cmd_patterns = [
            "; rm -rf",
            "| cat /etc",
            "&& wget",
            "$(whoami)",
            "`id`"
        ]

        # XSS patterns
        xss_patterns = [
            "<script>",
            "javascript:",
            "onerror=",
            "onload="
        ]

        # Metadata injection patterns
        metadata_patterns = [
            "[system]",
            "[admin]",
            "[priority:",
            "[override]",
            "[new instructions]"
        ]

        detected = []

        for pattern in sql_patterns:
            if pattern in content_lower:
                detected.append(("sql_injection", pattern))

        for pattern in cmd_patterns:
            if pattern in content_lower:
                detected.append(("command_injection", pattern))

        for pattern in xss_patterns:
            if pattern in content_lower:
                detected.append(("xss", pattern))

        for pattern in metadata_patterns:
            if pattern in content_lower:
                detected.append(("metadata_injection", pattern))

        if detected:
            self.state["anomaly_count"] += 1
            severity = "critical" if any(t[0] in ["sql_injection", "command_injection"] for t in detected) else "warning"

            return Alert(
                severity=severity,
                risk_type="message_tampering",
                message=f"Potential injection detected in message to {agent_name}",
                evidence={
                    "agent": agent_name,
                    "detected_patterns": detected,
                    "content_preview": content[:200],
                    "anomaly_count": self.state["anomaly_count"]
                },
                recommended_action="warn" if severity == "warning" else "block",
                timestamp=timestamp
            )

        return None

    def _track_message(self, content: str, agent_name: str, timestamp: float):
        """Track message for integrity monitoring."""
        msg_hash = hashlib.md5(content.encode()).hexdigest()

        # Store in history
        self.state["message_history"].append({
            "hash": msg_hash,
            "agent": agent_name,
            "timestamp": timestamp,
            "length": len(content)
        })

        # Trim history if too long
        max_history = self.config.get("max_message_history", 100)
        if len(self.state["message_history"]) > max_history:
            self.state["message_history"] = self.state["message_history"][-max_history:]

    def _detect_anomalous_content(self, content: str, agent_name: str, timestamp: float) -> Optional[Alert]:
        """Detect anomalous content patterns."""
        # Check for unusual characters or patterns
        anomalies = []

        # Check for null bytes
        if '\x00' in content:
            anomalies.append("null_bytes")

        # Check for excessive special characters
        special_chars = sum(1 for c in content if not c.isalnum() and not c.isspace())
        if len(content) > 0 and special_chars / len(content) > 0.3:
            anomalies.append("excessive_special_chars")

        # Check for very long single lines (potential buffer overflow attempt)
        lines = content.split('\n')
        if any(len(line) > 10000 for line in lines):
            anomalies.append("extremely_long_line")

        if anomalies:
            return Alert(
                severity="warning",
                risk_type="message_tampering",
                message=f"Anomalous content detected in message to {agent_name}",
                evidence={
                    "agent": agent_name,
                    "anomalies": anomalies,
                    "content_length": len(content)
                },
                recommended_action="log",
                timestamp=timestamp
            )

        return None

    def reset(self):
        """Reset monitor state."""
        super().reset()
        self.state = {
            "message_hashes": {},
            "message_history": [],
            "anomaly_count": 0
        }
