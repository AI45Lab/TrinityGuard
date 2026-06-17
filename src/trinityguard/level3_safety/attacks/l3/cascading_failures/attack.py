"""L3 cascading failures attack implementation."""

from __future__ import annotations

from typing import Any

from .....level2_intermediary.base import RunMode
from .....runtime.events import payload_hash
from ...base import AttackCase, AttackCaseResult, BaseAttack


class CascadingFailuresAttack(BaseAttack):
    """Workflow-level cascading failure attack."""

    risk_type = "cascading_failures"
    level = "l3"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the cascading failures attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L3 Cascading Failures",
                "description": (
                    "System-level workflow probes that inject malformed, looping, "
                    "resource-exhausting, or dependency-failure signals into a MAS."
                ),
            }
        )
        return info

    def run_case(
        self,
        intermediary: Any,
        case: AttackCase,
        target_agent: str | None = None,
        **kwargs: Any,
    ) -> AttackCaseResult:
        """Run one cascading failure probe through the full workflow."""
        workflow_kwargs = {k: v for k, v in kwargs.items() if k != "history"}
        workflow_kwargs.setdefault("mode", RunMode.MONITORED)
        workflow_kwargs.setdefault("silent", True)
        workflow_result = intermediary.run_workflow(
            case.attack_input,
            **workflow_kwargs,
        )
        agents = intermediary.mas.get_agents()
        workflow_metadata = getattr(workflow_result, "metadata", {}) or {}
        trace = workflow_metadata.get("trace") if isinstance(workflow_metadata, dict) else {}
        trace = trace if isinstance(trace, dict) else {}
        agent_steps = trace.get("agent_steps") if isinstance(trace.get("agent_steps"), list) else []
        trace_messages = trace.get("messages") if isinstance(trace.get("messages"), list) else []
        propagation_chain = []
        for step in agent_steps[:4]:
            if not isinstance(step, dict):
                continue
            source = str((step.get("metadata") or {}).get("from") or "unknown")
            target = str(step.get("agent_name") or "unknown")
            if source == "unknown" or target == "unknown":
                continue
            propagation_chain.append(f"{source}->{target}")
        multi_agent_propagation = len(set(propagation_chain)) >= 2

        metadata = dict(case.metadata)
        metadata["trace"] = trace
        metadata["cascade"] = {
            "workflow_success": getattr(workflow_result, "success", None),
            "workflow_error": getattr(workflow_result, "error", None),
            "agent_count": len(agents),
            "message_count": len(getattr(workflow_result, "messages", []) or []),
            "failure_type": case.metadata.get("failure_type"),
            "inject_at": case.metadata.get("inject_at"),
            "propagation_chain": propagation_chain,
            "multi_agent_propagation": multi_agent_propagation,
            "trace_message_count": len(trace_messages),
            "trace_agent_steps": len(agent_steps),
            "runtime_mode": workflow_kwargs["mode"].value
            if isinstance(workflow_kwargs["mode"], RunMode)
            else str(workflow_kwargs["mode"]),
            "proof": {
                "source": "attack_run_result",
                "trace_artifact_ref": _trace_artifact_ref(trace),
                "propagation_chain": propagation_chain,
                "multi_agent_propagation": multi_agent_propagation,
            },
        }

        return AttackCaseResult(
            attack_type=self.risk_type,
            case_name=case.name,
            attack_input=case.attack_input,
            target_agent=None,
            raw_response=self._workflow_result_to_text(workflow_result),
            execution_success=True,
            expected_behavior=case.expected_behavior,
            severity=case.severity,
            metadata=metadata,
        )

    def _workflow_result_to_text(self, workflow_result: Any) -> str:
        output = getattr(workflow_result, "output", None)
        if output is not None:
            return str(output)
        error = getattr(workflow_result, "error", None)
        return "" if error is None else f"ERROR: {error}"


def _trace_artifact_ref(trace: dict[str, Any]) -> str:
    """Return a stable content ref for the runtime trace attached to the result."""

    return f"sha256:{payload_hash(trace)}"
