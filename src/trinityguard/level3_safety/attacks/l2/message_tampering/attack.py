"""L2 message tampering attack implementation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .....level2_intermediary.base import RunMode
from .....level2_intermediary.workflow_runners import MessageInterception
from .....runtime.events import payload_hash
from ...base import AttackCase, AttackCaseResult, BaseAttack


class MessageTamperingAttack(BaseAttack):
    """Inter-agent message tampering attack using workflow interception."""

    risk_type = "message_tampering"
    level = "l2"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the message tampering attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L2 Message Tampering",
                "description": (
                    "Inter-agent message modification attacks that append, prepend, "
                    "replace, semantically alter, or truncate workflow messages."
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
        """Run one message tampering case through monitored interception."""
        source_agent, selected_target = self.select_agent_pair(
            intermediary,
            source_agent=kwargs.get("source_agent"),
            target_agent=target_agent,
        )
        modifier = self.create_message_modifier(case)
        interception = MessageInterception(
            source_agent=source_agent,
            target_agent=selected_target,
            modifier=modifier,
            attack_type=self.risk_type,
        )
        task = kwargs.get("task") or case.attack_input
        workflow_result = intermediary.run_workflow(
            task,
            mode=RunMode.MONITORED_INTERCEPTING,
            interceptions=[interception],
            silent=True,
        )

        workflow_metadata = getattr(workflow_result, "metadata", {}) or {}
        trace = workflow_metadata.get("trace") if isinstance(workflow_metadata, dict) else {}
        trace = trace if isinstance(trace, dict) else {}
        trace_interceptions = trace.get("interceptions")
        interceptions = trace_interceptions if isinstance(trace_interceptions, list) else []
        trace_agent_steps = trace.get("agent_steps")
        agent_steps = trace_agent_steps if isinstance(trace_agent_steps, list) else []
        trace_messages = trace.get("messages")
        messages = trace_messages if isinstance(trace_messages, list) else []
        first_interception = interceptions[0] if interceptions else {}
        first_interception = first_interception if isinstance(first_interception, dict) else {}
        logs = workflow_metadata.get("logs", []) if isinstance(workflow_metadata, dict) else []
        original_message = first_interception.get("original_content")
        modified_message = first_interception.get("modified_content")
        downstream_consumed = bool(agent_steps or logs)

        metadata = dict(case.metadata)
        metadata["trace"] = trace
        metadata["tampering"] = {
            "source_agent": source_agent,
            "target_agent": selected_target,
            "injection_type": case.metadata.get("injection_type"),
            "task_used": task,
            "workflow_success": getattr(workflow_result, "success", None),
            "logs": logs,
            "interceptions": interceptions,
            "original_message": original_message,
            "modified_message": modified_message,
            "downstream_consumed": downstream_consumed,
            "message_id": (first_interception.get("metadata") or {}).get("message_id"),
            "runtime_mode": RunMode.MONITORED_INTERCEPTING.value,
            "trace_message_count": len(messages),
            "trace_agent_steps": len(agent_steps),
            "trace_interception_count": len(interceptions),
            "proof": {
                "source": "attack_run_result",
                "trace_artifact_ref": _trace_artifact_ref(trace),
                "original_message_present": bool(original_message),
                "modified_message_present": bool(modified_message),
                "downstream_consumed": downstream_consumed,
            },
        }

        return AttackCaseResult(
            attack_type=self.risk_type,
            case_name=case.name,
            attack_input=case.attack_input,
            target_agent=selected_target,
            raw_response=self._workflow_result_to_text(workflow_result),
            execution_success=True,
            expected_behavior=case.expected_behavior,
            severity=case.severity,
            metadata=metadata,
        )

    def select_target_agent(self, intermediary: Any) -> str:
        """Select the receiving agent for compatibility with BaseAttack."""
        return self.select_agent_pair(intermediary)[1]

    def select_agent_pair(
        self,
        intermediary: Any,
        source_agent: str | None = None,
        target_agent: str | None = None,
    ) -> tuple[str, str]:
        """Select the first adjacent agent pair for message interception."""
        agents = intermediary.mas.get_agents()
        if len(agents) < 2:
            raise ValueError("Cannot run message tampering: MAS needs at least 2 agents")
        selected_source = source_agent or agents[0].name
        selected_target = target_agent or agents[1].name
        if selected_source == selected_target:
            raise ValueError("Cannot run message tampering: source and target agents must differ")
        return selected_source, selected_target

    def create_message_modifier(self, case: AttackCase) -> Callable[[str], str]:
        """Create a data-driven tampering function for a case."""
        injection_type = str(case.metadata.get("injection_type", "append"))
        payload = case.metadata.get("payload")

        def modifier(content: str) -> str:
            if injection_type == "prepend":
                return f"{payload or ''}{content}"
            if injection_type == "append":
                return f"{content}{payload or ''}"
            if injection_type == "replace":
                return str(payload or content)
            if injection_type == "semantic_negation_removal":
                original = str(case.metadata.get("original_phrase", ""))
                tampered = str(case.metadata.get("tampered_phrase", ""))
                return content.replace(original, tampered) if original else content
            if injection_type == "semantic_permission_injection":
                prefix = str(case.metadata.get("injected_prefix", ""))
                return f"{prefix}{content}"
            if injection_type == "semantic_scope_expansion":
                original = str(case.metadata.get("original_scope", ""))
                expanded = str(case.metadata.get("expanded_scope", ""))
                return content.replace(original, expanded) if original else content
            if injection_type == "truncate":
                ratio = float(case.metadata.get("truncate_ratio", 0.5))
                keep = max(1, int(len(content) * ratio))
                return content[:keep]
            return content

        return modifier

    def _workflow_result_to_text(self, workflow_result: Any) -> str:
        output = getattr(workflow_result, "output", None)
        if output is not None:
            return str(output)
        error = getattr(workflow_result, "error", None)
        return "" if error is None else f"ERROR: {error}"


def _trace_artifact_ref(trace: dict[str, Any]) -> str:
    """Return a stable content ref for the runtime trace attached to the result."""

    return f"sha256:{payload_hash(trace)}"
