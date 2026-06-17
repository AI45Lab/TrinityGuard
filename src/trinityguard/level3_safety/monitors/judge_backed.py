"""Judge-backed runtime monitor implementation for readiness evidence."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from trinityguard.level2_intermediary.structured_logging import AgentStepLog
from trinityguard.runtime.events import payload_hash, redact_text, sanitize_error

from ..judges.base import BaseJudge, JudgeResult
from ..monitors_base_ref import Alert, BaseMonitorAgent

JUDGE_MONITOR_STATE_KEY = "_last_judge_backed_observation"


class JudgeBackedRiskMonitor(BaseMonitorAgent):
    """Runtime monitor that delegates semantic risk decisions to a judge.

    The monitor remains deterministic when supplied with a deterministic fixture
    judge, and it records invocation metadata for monitor-observation artifacts.
    Pattern monitors stay available as fast smoke coverage; this class is the
    first-class judge-backed path used for paper-design-goal evidence.
    """

    def __init__(self, risk_type: str, *, judge: BaseJudge, name: str | None = None) -> None:
        super().__init__()
        self.risk_type = str(risk_type)
        self.judge = judge
        self.name = str(name or risk_type)
        self.judge_call_count = 0
        self.last_judge_result: dict[str, Any] | None = None
        self.last_invocation_id: str | None = None
        self.last_insufficiency_reason: str | None = None
        self.last_observation_metadata: dict[str, Any] | None = None

    def get_monitor_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "risk_type": self.risk_type,
            "description": f"Judge-backed runtime monitor for {self.risk_type}.",
            "monitor_strategy": "judge_backed",
            "judge_backed": True,
        }

    def reset(self) -> None:
        super().reset()
        self.judge_call_count = 0
        self.last_judge_result = None
        self.last_invocation_id = None
        self.last_insufficiency_reason = None
        self.last_observation_metadata = None

    def process(self, log_entry: AgentStepLog) -> Alert | None:
        """Process a runtime event and return an alert for risky judge verdicts."""

        self.last_observation_metadata = None
        content = _content_text(log_entry.content)
        context = _runtime_context(log_entry)
        sufficiency_reason = _pre_judge_insufficiency(content=content, context=context)
        if sufficiency_reason:
            self.last_insufficiency_reason = sufficiency_reason
            self._record_observation_metadata(
                _not_invoked_metadata(
                    reason=sufficiency_reason,
                    call_count=self.judge_call_count,
                )
            )
            return None

        invocation_id = f"judge-monitor-{uuid4()}"
        self.last_invocation_id = invocation_id
        judge_context = {
            "risk_type": self.risk_type,
            "runtime_context": context,
            "runtime_event": {
                "agent_name": context.get("agent_name"),
                "source_agent": context.get("source_agent"),
                "target_agent": context.get("target_agent"),
                "message_id": context.get("message_id"),
                "step_type": context.get("step_type"),
            },
            "observed_event": {
                "content_hash": f"sha256:{payload_hash(content)}",
                "content_summary": redact_text(content, max_length=300),
                "step_type": log_entry.step_type,
            },
        }

        self.judge_call_count += 1
        try:
            result = self.judge.analyze(content, context=judge_context)
        except Exception as exc:  # noqa: BLE001 - judge failure is explicit evidence.
            self.last_insufficiency_reason = f"judge failure: {sanitize_error(exc)}"
            self._record_observation_metadata(
                _insufficient_metadata(
                    invocation_id=invocation_id,
                    call_count=self.judge_call_count,
                    reason=self.last_insufficiency_reason,
                    result=None,
                )
            )
            return None

        if result is None:
            self.last_insufficiency_reason = "judge returned no result"
            self._record_observation_metadata(
                _insufficient_metadata(
                    invocation_id=invocation_id,
                    call_count=self.judge_call_count,
                    reason=self.last_insufficiency_reason,
                    result=None,
                )
            )
            return None

        if (
            result.parse_status != "valid"
            or result.sufficiency_status != "sufficient"
            or result.has_risk is None
        ):
            self.last_insufficiency_reason = "judge result invalid or insufficient"
            self.last_judge_result = result.to_dict()
            self._record_observation_metadata(
                _insufficient_metadata(
                    invocation_id=invocation_id,
                    call_count=self.judge_call_count,
                    reason=self.last_insufficiency_reason,
                    result=result,
                )
            )
            return None

        metadata = _verdict_metadata(
            invocation_id=invocation_id,
            call_count=self.judge_call_count,
            result=result,
            observation_type="alert" if result.has_risk else "non_alert",
        )
        self._record_observation_metadata(metadata)
        self.last_judge_result = result.to_dict()

        if not result.has_risk:
            return None

        alert = Alert(
            severity=(
                result.severity if result.severity in {"info", "warning", "critical"} else "warning"
            ),
            risk_type=self.risk_type,
            message=f"Judge-backed monitor detected {self.risk_type} risk.",
            evidence={
                "judge_invocation_id": invocation_id,
                "judge_call_count": self.judge_call_count,
                "judge_result": metadata["judge_result"],
                "judge_result_hash": metadata["judge_result_hash"],
            },
            recommended_action=result.recommended_action
            if result.recommended_action in {"log", "warn", "block"}
            else "warn",
            detection_reason=result.reason,
        )
        self._record_alert(alert)
        return alert

    def _record_observation_metadata(self, metadata: dict[str, Any]) -> None:
        self.last_observation_metadata = metadata
        self.state[JUDGE_MONITOR_STATE_KEY] = metadata


def _content_text(content: Any) -> str:
    if isinstance(content, dict):
        return str(content.get("content") or content)
    return "" if content is None else str(content)


def _runtime_context(log_entry: AgentStepLog) -> dict[str, Any]:
    metadata = log_entry.metadata or {}
    return {
        "run_id": metadata.get("run_id"),
        "case_name": metadata.get("case_name"),
        "attack_type": metadata.get("attack_type"),
        "level": str(metadata.get("level") or "unknown").lower(),
        "source_agent": metadata.get("from"),
        "target_agent": metadata.get("to") or log_entry.agent_name,
        "message_id": metadata.get("message_id"),
        "step_type": log_entry.step_type,
        "agent_name": log_entry.agent_name,
        "content_truncated": bool(metadata.get("content_truncated", False)),
        "trace_truncated": bool(metadata.get("trace_truncated", False)),
    }


def _pre_judge_insufficiency(*, content: str, context: dict[str, Any]) -> str | None:
    missing: list[str] = []
    if not content.strip():
        missing.append("content")
    if not context.get("source_agent"):
        missing.append("source_agent")
    if not context.get("target_agent"):
        missing.append("target_agent")
    if context.get("content_truncated") or context.get("trace_truncated"):
        missing.append("untruncated_trace")
    if not missing:
        return None
    return f"missing or insufficient judge monitor context: {', '.join(missing)}"


def _not_invoked_metadata(*, reason: str, call_count: int) -> dict[str, Any]:
    return {
        "observation_type": "insufficient",
        "insufficiency_reason": reason,
        "judge_invocation_id": f"not_invoked:{payload_hash(reason)}",
        "judge_call_count": call_count,
        "judge_result_hash": None,
        "judge_result": {
            "has_risk": None,
            "severity": "inconclusive",
            "reason": redact_text(reason, max_length=300),
            "evidence": [],
            "recommended_action": "log",
            "judge_type": "not_invoked",
            "parse_status": "not_invoked",
            "sufficiency_status": "insufficient",
        },
    }


def _insufficient_metadata(
    *,
    invocation_id: str,
    call_count: int,
    reason: str,
    result: JudgeResult | None,
) -> dict[str, Any]:
    judge_result = _judge_result_dict(result, fallback_reason=reason)
    return {
        "observation_type": "insufficient",
        "insufficiency_reason": reason,
        "judge_invocation_id": invocation_id,
        "judge_call_count": call_count,
        "judge_result_hash": f"sha256:{payload_hash(judge_result)}",
        "judge_result": judge_result,
    }


def _verdict_metadata(
    *,
    invocation_id: str,
    call_count: int,
    result: JudgeResult,
    observation_type: str,
) -> dict[str, Any]:
    judge_result = _judge_result_dict(result, fallback_reason=result.reason)
    return {
        "observation_type": observation_type,
        "judge_invocation_id": invocation_id,
        "judge_call_count": call_count,
        "judge_result_hash": f"sha256:{payload_hash(judge_result)}",
        "judge_result": judge_result,
    }


def _judge_result_dict(result: JudgeResult | None, *, fallback_reason: str) -> dict[str, Any]:
    if result is None:
        return {
            "has_risk": None,
            "severity": "inconclusive",
            "reason": redact_text(fallback_reason, max_length=300),
            "evidence": [],
            "recommended_action": "log",
            "judge_type": "unknown",
            "parse_status": "inconclusive",
            "sufficiency_status": "insufficient",
        }
    return {
        "has_risk": result.has_risk,
        "severity": result.severity,
        "reason": redact_text(result.reason, max_length=300),
        "evidence": [redact_text(item, max_length=200) for item in result.evidence],
        "recommended_action": result.recommended_action,
        "judge_type": result.judge_type,
        "parse_status": result.parse_status,
        "missing_fields": list(result.missing_fields),
        "invalid_fields": list(result.invalid_fields),
        "sufficiency_status": result.sufficiency_status,
    }


__all__ = ["JUDGE_MONITOR_STATE_KEY", "JudgeBackedRiskMonitor"]
