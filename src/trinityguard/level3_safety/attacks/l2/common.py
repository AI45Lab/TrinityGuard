"""Shared helpers for L2 workflow-level static attacks."""

from __future__ import annotations

from typing import Any, ClassVar

from ..base import AttackCase, AttackCaseResult, BaseAttack


class WorkflowL2StaticAttack(BaseAttack):
    """Base for L2 attacks that exercise a full MAS workflow and return raw output."""

    metadata_key: ClassVar[str]

    def run_case(
        self,
        intermediary: Any,
        case: AttackCase,
        target_agent: str | None = None,
        **kwargs: Any,
    ) -> AttackCaseResult:
        """Run one L2 case through the workflow without assigning a judge verdict."""
        workflow_result = intermediary.run_workflow(
            kwargs.get("task") or case.attack_input,
            **{k: v for k, v in kwargs.items() if k not in {"history", "task"}},
        )
        agents = intermediary.mas.get_agents()
        metadata = dict(case.metadata)
        metadata[self.metadata_key] = {
            "workflow_success": getattr(workflow_result, "success", None),
            "workflow_error": getattr(workflow_result, "error", None),
            "agent_count": len(agents),
            "message_count": len(getattr(workflow_result, "messages", []) or []),
            "category": case.metadata.get("category"),
        }
        workflow_metadata = getattr(workflow_result, "metadata", {})
        trace = workflow_metadata.get("trace") if isinstance(workflow_metadata, dict) else None
        if isinstance(trace, dict) and trace:
            metadata["trace"] = trace

        return AttackCaseResult(
            attack_type=self.risk_type,
            case_name=case.name,
            attack_input=case.attack_input,
            target_agent=target_agent,
            raw_response=self._workflow_result_to_text(workflow_result),
            execution_success=True,
            expected_behavior=case.expected_behavior,
            severity=case.severity,
            metadata=metadata,
        )

    def select_target_agent(self, intermediary: Any) -> str:
        """Select the receiving agent for compatibility with BaseAttack."""
        agents = intermediary.mas.get_agents()
        if not agents:
            raise ValueError(f"Cannot run {self.risk_type}: MAS has no agents")
        return agents[-1].name

    def _workflow_result_to_text(self, workflow_result: Any) -> str:
        output = getattr(workflow_result, "output", None)
        if output is not None:
            return str(output)
        error = getattr(workflow_result, "error", None)
        return "" if error is None else f"ERROR: {error}"
