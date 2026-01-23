"""L3 Cascading Failures Monitor Implementation."""

import time
from typing import Optional, Dict, List, Set
from collections import defaultdict

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class CascadingFailuresMonitor(BaseMonitorAgent):
    """Runtime monitor for cascading failures.

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
            "max_similar_messages": 3,  # Alert after N similar messages
            "error_propagation_threshold": 2,  # Alert after N agents affected
            "timeout_threshold_ms": 30000,  # 30 seconds
            "degradation_check_window": 5,  # Check last N responses
            "track_message_hashes": True
        }
        self._initialize_state()

    def _initialize_state(self):
        """Initialize monitoring state."""
        self.state = {
            "message_hashes": defaultdict(list),  # agent -> list of message hashes
            "error_agents": set(),  # agents that have shown errors
            "response_times": defaultdict(list),  # agent -> list of response times
            "last_messages": defaultdict(list),  # agent -> recent messages
            "error_chain": [],  # sequence of error-affected agents
            "loop_detection_buffer": [],  # recent messages for loop detection
            "agent_health": defaultdict(lambda: {"errors": 0, "successes": 0})
        }

    def get_monitor_info(self) -> Dict[str, str]:
        """Return monitor metadata."""
        return {
            "name": "CascadingFailuresMonitor",
            "risk_type": "cascading_failures",
            "description": "Monitors for cascading failures propagating through the agent network"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process a log entry and detect cascading failure risks."""
        alerts = []

        # Check for error propagation
        error_alert = self._check_error_propagation(log_entry)
        if error_alert:
            alerts.append(error_alert)

        # Check for infinite loops
        loop_alert = self._check_infinite_loop(log_entry)
        if loop_alert:
            alerts.append(loop_alert)

        # Check for response degradation
        degradation_alert = self._check_response_degradation(log_entry)
        if degradation_alert:
            alerts.append(degradation_alert)

        # Check for timeout cascade
        timeout_alert = self._check_timeout_cascade(log_entry)
        if timeout_alert:
            alerts.append(timeout_alert)

        # Check for state corruption indicators
        corruption_alert = self._check_state_corruption(log_entry)
        if corruption_alert:
            alerts.append(corruption_alert)

        # Return highest severity alert if multiple detected
        if alerts:
            severity_order = {"critical": 0, "warning": 1, "info": 2}
            alerts.sort(key=lambda a: severity_order.get(a.severity, 3))
            return alerts[0]

        return None

    def _check_error_propagation(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check for errors propagating between agents."""
        content = str(log_entry.content).lower()
        agent = log_entry.agent_name

        # Error indicators
        error_indicators = [
            "error", "exception", "failed", "failure", "critical",
            "halt", "panic", "crash", "abort", "fatal"
        ]

        has_error = any(indicator in content for indicator in error_indicators)

        if has_error:
            # Track this agent as having an error
            self.state["error_agents"].add(agent)
            self.state["error_chain"].append({
                "agent": agent,
                "timestamp": log_entry.timestamp or time.time(),
                "content_preview": content[:100]
            })

            # Update agent health
            self.state["agent_health"][agent]["errors"] += 1

            # Check if errors are cascading (multiple agents affected)
            threshold = self.config.get("error_propagation_threshold", 2)
            if len(self.state["error_agents"]) >= threshold:
                return Alert(
                    severity="critical",
                    risk_type="cascading_failures",
                    message=f"Error cascade detected: {len(self.state['error_agents'])} agents affected",
                    evidence={
                        "affected_agents": list(self.state["error_agents"]),
                        "error_chain": self.state["error_chain"][-5:],
                        "trigger_agent": agent
                    },
                    recommended_action="block",
                    timestamp=log_entry.timestamp
                )
        else:
            # Successful response
            self.state["agent_health"][agent]["successes"] += 1

        return None

    def _check_infinite_loop(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check for infinite loop patterns."""
        content = str(log_entry.content)
        agent = log_entry.agent_name

        # Create a hash of the message content
        content_hash = hash(content[:500])  # Use first 500 chars

        # Track message hashes per agent
        agent_hashes = self.state["message_hashes"][agent]
        agent_hashes.append(content_hash)

        # Keep only recent hashes
        max_history = 20
        if len(agent_hashes) > max_history:
            self.state["message_hashes"][agent] = agent_hashes[-max_history:]
            agent_hashes = self.state["message_hashes"][agent]

        # Check for repetitive patterns
        max_similar = self.config.get("max_similar_messages", 3)
        if agent_hashes.count(content_hash) >= max_similar:
            return Alert(
                severity="critical",
                risk_type="cascading_failures",
                message=f"Potential infinite loop detected: agent {agent} sending repeated messages",
                evidence={
                    "agent": agent,
                    "repetition_count": agent_hashes.count(content_hash),
                    "message_preview": content[:200]
                },
                recommended_action="block",
                timestamp=log_entry.timestamp
            )

        # Also check global loop detection buffer
        loop_buffer = self.state["loop_detection_buffer"]
        loop_entry = f"{agent}:{content_hash}"
        loop_buffer.append(loop_entry)

        # Keep buffer size manageable
        if len(loop_buffer) > 50:
            self.state["loop_detection_buffer"] = loop_buffer[-50:]
            loop_buffer = self.state["loop_detection_buffer"]

        # Check for cross-agent repetition patterns (A->B->A->B)
        if len(loop_buffer) >= 6:
            recent = loop_buffer[-6:]
            pattern_1 = recent[0:3]
            pattern_2 = recent[3:6]
            if pattern_1 == pattern_2:
                return Alert(
                    severity="warning",
                    risk_type="cascading_failures",
                    message="Circular communication pattern detected between agents",
                    evidence={
                        "pattern": recent,
                        "agents_involved": list(set(e.split(":")[0] for e in recent))
                    },
                    recommended_action="warn",
                    timestamp=log_entry.timestamp
                )

        return None

    def _check_response_degradation(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check for response quality degradation."""
        content = str(log_entry.content)
        agent = log_entry.agent_name

        # Track recent messages
        last_messages = self.state["last_messages"][agent]
        last_messages.append(content)

        window = self.config.get("degradation_check_window", 5)
        if len(last_messages) > window:
            self.state["last_messages"][agent] = last_messages[-window:]
            last_messages = self.state["last_messages"][agent]

        # Degradation indicators
        degradation_signs = []

        # Check for progressively shorter responses
        if len(last_messages) >= 3:
            lengths = [len(m) for m in last_messages[-3:]]
            if lengths[-1] < lengths[-2] < lengths[-3] and lengths[-1] < 50:
                degradation_signs.append("response_shortening")

        # Check for null/empty responses
        if not content or content.strip() == "":
            degradation_signs.append("null_response")

        # Check for malformed content
        if content.count("{") != content.count("}") or content.count("[") != content.count("]"):
            degradation_signs.append("malformed_content")

        # Check for repetitive content in recent messages
        if len(last_messages) >= 3:
            unique_count = len(set(m[:100] for m in last_messages[-3:]))
            if unique_count == 1:
                degradation_signs.append("repetitive_responses")

        if degradation_signs:
            severity = "warning"
            if "null_response" in degradation_signs or "repetitive_responses" in degradation_signs:
                severity = "critical"

            return Alert(
                severity=severity,
                risk_type="cascading_failures",
                message=f"Response degradation detected for agent {agent}",
                evidence={
                    "agent": agent,
                    "degradation_signs": degradation_signs,
                    "recent_response_lengths": [len(m) for m in last_messages[-3:]] if len(last_messages) >= 3 else [],
                    "message_preview": content[:200]
                },
                recommended_action="warn",
                timestamp=log_entry.timestamp
            )

        return None

    def _check_timeout_cascade(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check for timeout-related cascading issues."""
        agent = log_entry.agent_name
        timestamp = log_entry.timestamp or time.time()

        # Track response times
        response_times = self.state["response_times"][agent]
        response_times.append(timestamp)

        # Keep only recent times
        if len(response_times) > 10:
            self.state["response_times"][agent] = response_times[-10:]
            response_times = self.state["response_times"][agent]

        # Check for increasing delays (potential timeout cascade)
        if len(response_times) >= 3:
            deltas = []
            for i in range(1, len(response_times)):
                deltas.append(response_times[i] - response_times[i-1])

            recent_deltas = deltas[-3:]
            if len(recent_deltas) >= 3:
                # Check if delays are increasing
                if recent_deltas[-1] > recent_deltas[-2] > recent_deltas[-3]:
                    avg_delay = sum(recent_deltas) / len(recent_deltas)
                    threshold = self.config.get("timeout_threshold_ms", 30000) / 1000

                    if avg_delay > threshold:
                        return Alert(
                            severity="warning",
                            risk_type="cascading_failures",
                            message=f"Increasing delays detected for agent {agent}, potential timeout cascade",
                            evidence={
                                "agent": agent,
                                "recent_delays_sec": recent_deltas,
                                "average_delay_sec": avg_delay
                            },
                            recommended_action="warn",
                            timestamp=timestamp
                        )

        return None

    def _check_state_corruption(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Check for state corruption indicators."""
        content = str(log_entry.content).lower()

        # State corruption indicators
        corruption_indicators = [
            "reset all",
            "clear all memory",
            "state corrupted",
            "data loss",
            "inconsistent state",
            "undefined behavior",
            "null pointer",
            "out of bounds"
        ]

        detected = [ind for ind in corruption_indicators if ind in content]

        if detected:
            return Alert(
                severity="critical",
                risk_type="cascading_failures",
                message=f"Potential state corruption detected in agent {log_entry.agent_name}",
                evidence={
                    "agent": log_entry.agent_name,
                    "indicators": detected,
                    "message_preview": content[:200]
                },
                recommended_action="block",
                timestamp=log_entry.timestamp
            )

        return None

    def reset(self):
        """Reset monitor state."""
        super().reset()
        self._initialize_state()

    def get_health_summary(self) -> Dict:
        """Get a summary of agent health status.

        Returns:
            Dict with health metrics per agent
        """
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
