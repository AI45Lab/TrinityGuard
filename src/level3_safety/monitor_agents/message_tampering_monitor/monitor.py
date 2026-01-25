"""L2 Message Tampering Monitor Implementation."""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ...judges import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class MessageTamperingMonitor(BaseMonitorAgent):
    """Detect message tampering via consistency checks.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - Unexpected content patterns in messages
    - Message integrity violations
    - Anomalous content injection
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "track_message_hashes": True,
            "detect_injection_patterns": True,
            "max_message_history": 100
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="message_tampering",
            system_prompt_file=prompt_file
        )

        self.state = {
            "message_hashes": {},
            "message_history": [],
            "anomaly_count": 0
        }

        # Injection patterns for fallback
        self.sql_patterns = [
            "drop table", "delete from", "insert into",
            "union select", "'; --", "or 1=1"
        ]
        self.cmd_patterns = [
            "; rm -rf", "| cat /etc", "&& wget", "$(whoami)", "`id`"
        ]
        self.xss_patterns = [
            "<script>", "javascript:", "onerror=", "onload="
        ]
        self.metadata_patterns = [
            "[system]", "[admin]", "[priority:", "[override]", "[new instructions]"
        ]

    def get_monitor_info(self) -> Dict[str, str]:
        """Return monitor metadata."""
        return {
            "name": "MessageTamperingMonitor",
            "risk_type": "message_tampering",
            "description": "Monitors for message tampering and content injection using LLM analysis"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process log entry with LLM-first analysis."""
        if log_entry.step_type != "receive":
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
            risk_type="message_tampering",
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
        agent_name = log_entry.agent_name

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
        detected = []

        for pattern in self.sql_patterns:
            if pattern in content_lower:
                detected.append(("sql_injection", pattern))

        for pattern in self.cmd_patterns:
            if pattern in content_lower:
                detected.append(("command_injection", pattern))

        for pattern in self.xss_patterns:
            if pattern in content_lower:
                detected.append(("xss", pattern))

        for pattern in self.metadata_patterns:
            if pattern in content_lower:
                detected.append(("metadata_injection", pattern))

        if detected:
            self.state["anomaly_count"] += 1
            severity = "critical" if any(t[0] in ["sql_injection", "command_injection"] for t in detected) else "warning"

            alert = Alert(
                severity=severity,
                risk_type="message_tampering",
                message=f"Potential injection detected (fallback mode)",
                evidence={
                    "agent": agent_name,
                    "detected_by": "pattern_matching",
                    "detected_patterns": detected,
                    "content_preview": content[:200],
                    "anomaly_count": self.state["anomaly_count"]
                },
                recommended_action="warn" if severity == "warning" else "block",
                timestamp=timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _track_message(self, content: str, agent_name: str, timestamp: float):
        """Track message for integrity monitoring."""
        msg_hash = hashlib.md5(content.encode()).hexdigest()

        self.state["message_history"].append({
            "hash": msg_hash,
            "agent": agent_name,
            "timestamp": timestamp,
            "length": len(content)
        })

        max_history = self.config.get("max_message_history", 100)
        if len(self.state["message_history"]) > max_history:
            self.state["message_history"] = self.state["message_history"][-max_history:]

    def _detect_anomalous_content(self, content: str, agent_name: str, timestamp: float) -> Optional[Alert]:
        """Detect anomalous content patterns."""
        anomalies = []

        if '\x00' in content:
            anomalies.append("null_bytes")

        special_chars = sum(1 for c in content if not c.isalnum() and not c.isspace())
        if len(content) > 0 and special_chars / len(content) > 0.3:
            anomalies.append("excessive_special_chars")

        lines = content.split('\n')
        if any(len(line) > 10000 for line in lines):
            anomalies.append("extremely_long_line")

        if anomalies:
            alert = Alert(
                severity="warning",
                risk_type="message_tampering",
                message=f"Anomalous content detected (fallback mode)",
                evidence={
                    "agent": agent_name,
                    "detected_by": "pattern_matching",
                    "anomalies": anomalies,
                    "content_length": len(content)
                },
                recommended_action="log",
                timestamp=timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def reset(self):
        """Reset monitor state."""
        super().reset()
        self.state = {
            "message_hashes": {},
            "message_history": [],
            "anomaly_count": 0
        }
