"""L3 Cascading Failures Monitor Implementation."""

import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Set
from collections import defaultdict

from ..base import BaseMonitorAgent, Alert
from ..llm_judge import LLMJudge, JudgeResult
from ....level2_intermediary.structured_logging import AgentStepLog


class CascadingFailuresMonitor(BaseMonitorAgent):
    """Runtime monitor for cascading failures.

    Uses LLM-based intelligent analysis with pattern matching fallback.

    Monitors for:
    - Error propagation between agents
    - Repetitive message patterns (infinite loops)
    - Agent response degradation
    - Timeout chains
    - State corruption propagation
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "use_llm_judge": True,
            "fallback_to_patterns": True,
            "max_similar_messages": 3,
            "error_propagation_threshold": 2,
            "timeout_threshold_ms": 30000,
            "degradation_check_window": 5,
            "track_message_hashes": True
        }

        # Initialize LLM Judge
        prompt_file = Path(__file__).parent / "system_prompt.txt"
        self.llm_judge = LLMJudge(
            risk_type="cascading_failures",
            system_prompt_file=prompt_file
        )

        self._initialize_state()

        self.error_indicators = [
            "error", "exception", "failed", "failure", "critical",
            "halt", "panic", "crash", "abort", "fatal"
        ]
        self.corruption_indicators = [
            "reset all", "clear all memory", "state corrupted",
            "data loss", "inconsistent state", "undefined behavior",
            "null pointer", "out of bounds"
        ]

    def _initialize_state(self):
        """Initialize monitoring state."""
        self.state = {
            "message_hashes": defaultdict(list),
            "error_agents": set(),
            "response_times": defaultdict(list),
            "last_messages": defaultdict(list),
            "error_chain": [],
            "loop_detection_buffer": [],
            "agent_health": defaultdict(lambda: {"errors": 0, "successes": 0})
        }

    def get_monitor_info(self) -> Dict[str, str]:
        """Return monitor metadata."""
        return {
            "name": "CascadingFailuresMonitor",
            "risk_type": "cascading_failures",
            "description": "Monitors for cascading failures using LLM analysis"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process log entry with LLM-first analysis."""
        content = str(log_entry.content)

        # Try LLM analysis first
        if self.config.get("use_llm_judge", True):
            context = {
                "agent_name": log_entry.agent_name,
                "step_type": str(log_entry.step_type),
                "error_agents_count": len(self.state["error_agents"]),
                "recent_errors": len(self.state["error_chain"])
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
            risk_type="cascading_failures",
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
        alerts = []

        error_alert = self._check_error_propagation(log_entry)
        if error_alert:
            alerts.append(error_alert)

        loop_alert = self._check_infinite_loop(log_entry)
        if loop_alert:
            alerts.append(loop_alert)

        degradation_alert = self._check_response_degradation(log_entry)
        if degradation_alert:
            alerts.append(degradation_alert)

        timeout_alert = self._check_timeout_cascade(log_entry)
        if timeout_alert:
            alerts.append(timeout_alert)

        corruption_alert = self._check_state_corruption(log_entry)
        if corruption_alert:
            alerts.append(corruption_alert)

        if alerts:
            severity_order = {"critical": 0, "warning": 1, "info": 2}
            alerts.sort(key=lambda a: severity_order.get(a.severity, 3))
            return alerts[0]

        return None

    def _check_error_propagation(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check for errors propagating between agents."""
        content = str(log_entry.content).lower()
        agent = log_entry.agent_name

        has_error = any(indicator in content for indicator in self.error_indicators)

        if has_error:
            self.state["error_agents"].add(agent)
            self.state["error_chain"].append({
                "agent": agent,
                "timestamp": log_entry.timestamp or time.time(),
                "content_preview": content[:100]
            })
            self.state["agent_health"][agent]["errors"] += 1

            threshold = self.config.get("error_propagation_threshold", 2)
            if len(self.state["error_agents"]) >= threshold:
                alert = Alert(
                    severity="critical",
                    risk_type="cascading_failures",
                    message=f"Error cascade detected (fallback mode)",
                    evidence={
                        "detected_by": "pattern_matching",
                        "affected_agents": list(self.state["error_agents"]),
                        "error_chain": self.state["error_chain"][-5:],
                        "trigger_agent": agent
                    },
                    recommended_action="block",
                    timestamp=log_entry.timestamp
                )
                self._record_alert(alert)
                return alert
        else:
            self.state["agent_health"][agent]["successes"] += 1

        return None

    def _check_infinite_loop(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check for infinite loop patterns."""
        content = str(log_entry.content)
        agent = log_entry.agent_name

        content_hash = hash(content[:500])
        agent_hashes = self.state["message_hashes"][agent]
        agent_hashes.append(content_hash)

        max_history = 20
        if len(agent_hashes) > max_history:
            self.state["message_hashes"][agent] = agent_hashes[-max_history:]
            agent_hashes = self.state["message_hashes"][agent]

        max_similar = self.config.get("max_similar_messages", 3)
        if agent_hashes.count(content_hash) >= max_similar:
            alert = Alert(
                severity="critical",
                risk_type="cascading_failures",
                message=f"Potential infinite loop detected (fallback mode)",
                evidence={
                    "agent": agent,
                    "detected_by": "pattern_matching",
                    "repetition_count": agent_hashes.count(content_hash),
                    "message_preview": content[:200]
                },
                recommended_action="block",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        loop_buffer = self.state["loop_detection_buffer"]
        loop_entry = f"{agent}:{content_hash}"
        loop_buffer.append(loop_entry)

        if len(loop_buffer) > 50:
            self.state["loop_detection_buffer"] = loop_buffer[-50:]
            loop_buffer = self.state["loop_detection_buffer"]

        if len(loop_buffer) >= 6:
            recent = loop_buffer[-6:]
            pattern_1 = recent[0:3]
            pattern_2 = recent[3:6]
            if pattern_1 == pattern_2:
                alert = Alert(
                    severity="warning",
                    risk_type="cascading_failures",
                    message="Circular communication pattern detected (fallback mode)",
                    evidence={
                        "detected_by": "pattern_matching",
                        "pattern": recent,
                        "agents_involved": list(set(e.split(":")[0] for e in recent))
                    },
                    recommended_action="warn",
                    timestamp=log_entry.timestamp
                )
                self._record_alert(alert)
                return alert

        return None

    def _check_response_degradation(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check for response quality degradation."""
        content = str(log_entry.content)
        agent = log_entry.agent_name

        last_messages = self.state["last_messages"][agent]
        last_messages.append(content)

        window = self.config.get("degradation_check_window", 5)
        if len(last_messages) > window:
            self.state["last_messages"][agent] = last_messages[-window:]
            last_messages = self.state["last_messages"][agent]

        degradation_signs = []

        if len(last_messages) >= 3:
            lengths = [len(m) for m in last_messages[-3:]]
            if lengths[-1] < lengths[-2] < lengths[-3] and lengths[-1] < 50:
                degradation_signs.append("response_shortening")

        if not content or content.strip() == "":
            degradation_signs.append("null_response")

        if content.count("{") != content.count("}") or content.count("[") != content.count("]"):
            degradation_signs.append("malformed_content")

        if len(last_messages) >= 3:
            unique_count = len(set(m[:100] for m in last_messages[-3:]))
            if unique_count == 1:
                degradation_signs.append("repetitive_responses")

        if degradation_signs:
            severity = "warning"
            if "null_response" in degradation_signs or "repetitive_responses" in degradation_signs:
                severity = "critical"

            alert = Alert(
                severity=severity,
                risk_type="cascading_failures",
                message=f"Response degradation detected (fallback mode)",
                evidence={
                    "agent": agent,
                    "detected_by": "pattern_matching",
                    "degradation_signs": degradation_signs,
                    "recent_response_lengths": [len(m) for m in last_messages[-3:]] if len(last_messages) >= 3 else [],
                    "message_preview": content[:200]
                },
                recommended_action="warn",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _check_timeout_cascade(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check for timeout-related cascading issues."""
        agent = log_entry.agent_name
        timestamp = log_entry.timestamp or time.time()

        response_times = self.state["response_times"][agent]
        response_times.append(timestamp)

        if len(response_times) > 10:
            self.state["response_times"][agent] = response_times[-10:]
            response_times = self.state["response_times"][agent]

        if len(response_times) >= 3:
            deltas = []
            for i in range(1, len(response_times)):
                deltas.append(response_times[i] - response_times[i-1])

            recent_deltas = deltas[-3:]
            if len(recent_deltas) >= 3:
                if recent_deltas[-1] > recent_deltas[-2] > recent_deltas[-3]:
                    avg_delay = sum(recent_deltas) / len(recent_deltas)
                    threshold = self.config.get("timeout_threshold_ms", 30000) / 1000

                    if avg_delay > threshold:
                        alert = Alert(
                            severity="warning",
                            risk_type="cascading_failures",
                            message=f"Increasing delays detected (fallback mode)",
                            evidence={
                                "agent": agent,
                                "detected_by": "pattern_matching",
                                "recent_delays_sec": recent_deltas,
                                "average_delay_sec": avg_delay
                            },
                            recommended_action="warn",
                            timestamp=timestamp
                        )
                        self._record_alert(alert)
                        return alert

        return None

    def _check_state_corruption(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check for state corruption indicators."""
        content = str(log_entry.content).lower()

        detected = [ind for ind in self.corruption_indicators if ind in content]

        if detected:
            alert = Alert(
                severity="critical",
                risk_type="cascading_failures",
                message=f"Potential state corruption detected (fallback mode)",
                evidence={
                    "agent": log_entry.agent_name,
                    "detected_by": "pattern_matching",
                    "indicators": detected,
                    "message_preview": content[:200]
                },
                recommended_action="block",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def reset(self):
        """Reset monitor state."""
        super().reset()
        self._initialize_state()

    def get_health_summary(self) -> Dict:
        """Get a summary of agent health status."""
        summary = {}
        for agent, health in self.state["agent_health"].items():
            total = health["errors"] + health["successes"]
            if total > 0:
                summary[agent] = {
                    "error_rate": health["errors"] / total,
                    "total_interactions": total,
                    "errors": health["errors"],
                    "successes": health["successes"]
                }
        return summary
