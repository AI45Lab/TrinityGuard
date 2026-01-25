"""L1 Tool Misuse Monitor Implementation."""

from typing import Optional, Dict, List

from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog


class ToolMisuseMonitor(BaseMonitorAgent):
    """Runtime monitor for tool misuse.

    Monitors for:
    - Dangerous tool chains
    - Excessive tool calls
    - Unauthorized tool access
    - Parameter injection
    """

    def __init__(self):
        super().__init__()
        self.config = {
            "max_tool_calls_per_turn": 5,
            "track_tool_chains": True,
            "check_parameters": True
        }
        self.tool_call_history: Dict[str, List[Dict]] = {}

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "ToolMisuseMonitor",
            "risk_type": "tool_misuse",
            "description": "Monitors for misuse of available tools"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        if log_entry.step_type == "tool_call":
            return self._check_tool_call(log_entry)
        return None

    def _check_tool_call(self, log_entry: AgentStepLog) -> Optional[Alert]:
        agent_name = log_entry.agent_name
        tool_name = log_entry.metadata.get("tool_name", "unknown")
        params = log_entry.metadata.get("params", {})

        if agent_name not in self.tool_call_history:
            self.tool_call_history[agent_name] = []

        self.tool_call_history[agent_name].append({
            "tool": tool_name,
            "params": params,
            "timestamp": log_entry.timestamp
        })

        max_calls = self.config.get("max_tool_calls_per_turn", 5)
        if len(self.tool_call_history[agent_name]) > max_calls:
            alert = Alert(
                severity="warning",
                risk_type="tool_misuse",
                message=f"Agent {agent_name} exceeded tool call limit ({max_calls})",
                evidence={
                    "agent": agent_name,
                    "call_count": len(self.tool_call_history[agent_name]),
                    "limit": max_calls,
                    "tools_used": [c["tool"] for c in self.tool_call_history[agent_name][-5:]]
                },
                recommended_action="warn",
                timestamp=log_entry.timestamp
            )
            self._record_alert(alert)
            return alert

        if self.config.get("check_parameters", True):
            param_alert = self._check_parameters(agent_name, tool_name, params, log_entry.timestamp)
            if param_alert:
                return param_alert

        if self.config.get("track_tool_chains", True):
            chain_alert = self._check_tool_chain(agent_name, tool_name, log_entry.timestamp)
            if chain_alert:
                return chain_alert

        return None

    def _check_parameters(self, agent_name: str, tool_name: str,
                          params: Dict, timestamp: float) -> Optional[Alert]:
        param_str = str(params).lower()

        dangerous_patterns = [
            "drop table", "delete from", "; --",
            "union select", "' or '1'='1",
            "../", "..\\", "/etc/passwd"
        ]

        detected = [p for p in dangerous_patterns if p in param_str]

        if detected:
            alert = Alert(
                severity="critical",
                risk_type="tool_misuse",
                message=f"Dangerous parameters detected in {tool_name} call by {agent_name}",
                evidence={
                    "agent": agent_name,
                    "tool": tool_name,
                    "dangerous_patterns": detected,
                    "params_preview": param_str[:200]
                },
                recommended_action="block",
                timestamp=timestamp
            )
            self._record_alert(alert)
            return alert

        return None

    def _check_tool_chain(self, agent_name: str, tool_name: str,
                          timestamp: float) -> Optional[Alert]:
        history = self.tool_call_history.get(agent_name, [])
        if len(history) < 2:
            return None

        dangerous_chains = [
            (["search", "file"], "data exfiltration"),
            (["read", "send"], "data exfiltration"),
            (["execute", "execute"], "recursive execution"),
            (["admin", "delete"], "privileged deletion")
        ]

        recent_tools = [h["tool"].lower() for h in history[-3:]]

        for chain, threat in dangerous_chains:
            if all(any(c in t for t in recent_tools) for c in chain):
                alert = Alert(
                    severity="warning",
                    risk_type="tool_misuse",
                    message=f"Potentially dangerous tool chain detected: {threat}",
                    evidence={
                        "agent": agent_name,
                        "tool_chain": recent_tools,
                        "threat_type": threat
                    },
                    recommended_action="warn",
                    timestamp=timestamp
                )
                self._record_alert(alert)
                return alert

        return None

    def reset(self):
        super().reset()
        self.tool_call_history = {}
