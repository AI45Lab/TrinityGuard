"""Trace-aware evidence packaging for LLM-as-judge calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from trinityguard.runtime.events import payload_hash, redact_text

from ..attacks.base import AttackCase, AttackCaseResult


@dataclass(frozen=True)
class JudgeEvidencePackage:
    """Redacted, bounded evidence supplied to a risk judge."""

    risk_type: str
    tier: str
    case_name: str
    attack_input: str
    expected_behavior: str
    target_entity: str | None
    raw_response: str
    execution_success: bool
    severity: str
    target_granularity: str = "agent"
    trace: dict[str, Any] = field(default_factory=dict)
    trace_artifact_refs: list[str] = field(default_factory=list)
    truncation: dict[str, bool] = field(default_factory=dict)
    payload_refs: dict[str, str] = field(default_factory=dict)
    runtime_effect_markers: dict[str, Any] = field(default_factory=dict)
    monitor_observation_refs: list[str] = field(default_factory=list)
    sufficiency_status: str = "sufficient"
    insufficiency_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_type": self.risk_type,
            "tier": self.tier,
            "case_name": self.case_name,
            "attack_input": self.attack_input,
            "expected_behavior": self.expected_behavior,
            "target_entity": self.target_entity or "",
            "target_granularity": self.target_granularity,
            "raw_response": self.raw_response,
            "execution_success": self.execution_success,
            "severity": self.severity,
            "trace": self.trace,
            "trace_artifact_refs": list(self.trace_artifact_refs),
            "truncation": self.truncation,
            "payload_refs": self.payload_refs,
            "runtime_effect_markers": self.runtime_effect_markers,
            "monitor_observation_refs": list(self.monitor_observation_refs),
            "sufficiency_status": self.sufficiency_status,
            "insufficiency_reasons": list(self.insufficiency_reasons),
        }

    def to_judge_inputs(self) -> tuple[str, dict[str, Any]]:
        content = self.raw_response
        context = self.to_dict()
        context.pop("raw_response", None)
        return content, context


def build_judge_evidence_package(
    *,
    case: AttackCase | None = None,
    result: AttackCaseResult,
    tier: str | None = None,
    max_text_length: int = 1_200,
    max_trace_items: int = 10,
    include_trace_ref: bool = True,
) -> JudgeEvidencePackage:
    """Build redacted judge evidence from one raw attack case result."""

    attack_input = case.attack_input if case is not None else result.attack_input
    expected = case.expected_behavior if case is not None else result.expected_behavior
    raw_response = result.raw_response or ""
    trace = _extract_trace(result.metadata, max_items=max_trace_items, max_length=max_text_length)
    redacted_input, input_truncated = _redact_bounded(attack_input, max_text_length)
    redacted_response, response_truncated = _redact_bounded(raw_response, max_text_length)

    payload_refs = {
        "attack_input": f"sha256:{payload_hash(attack_input)}",
        "raw_response": f"sha256:{payload_hash(raw_response)}",
    }
    if include_trace_ref:
        payload_refs["trace"] = f"sha256:{payload_hash(trace)}"
    trace_artifact_refs = _extract_trace_artifact_refs(result.metadata)
    monitor_refs = _extract_monitor_observation_refs(result.metadata)
    runtime_effect_markers = _runtime_effect_markers(
        result.metadata,
        trace=trace,
        risk_type=result.attack_type,
    )

    tier_value = tier or _level_from_metadata(result.metadata)
    truncation = {
        "attack_input": input_truncated,
        "raw_response": response_truncated,
        "trace_items": bool(trace.get("truncated", False)),
    }

    insufficiency_reasons = _insufficiency_reasons(
        risk_type=result.attack_type,
        tier=tier_value,
        trace=trace,
        trace_artifact_refs=trace_artifact_refs,
        truncation=truncation,
        payload_refs=payload_refs,
        runtime_effect_markers=runtime_effect_markers,
    )

    return JudgeEvidencePackage(
        risk_type=result.attack_type,
        tier=tier_value,
        case_name=result.case_name,
        attack_input=redacted_input,
        expected_behavior=redact_text(expected, max_length=max_text_length),
        target_entity=result.target_agent,
        raw_response=redacted_response,
        execution_success=result.execution_success,
        severity=result.severity,
        target_granularity=_target_granularity(
            result.metadata,
            tier=tier_value,
            risk_type=result.attack_type,
        ),
        trace=trace,
        trace_artifact_refs=trace_artifact_refs,
        truncation=truncation,
        payload_refs=payload_refs,
        runtime_effect_markers=runtime_effect_markers,
        monitor_observation_refs=monitor_refs,
        sufficiency_status="sufficient" if not insufficiency_reasons else "insufficient",
        insufficiency_reasons=insufficiency_reasons,
    )


def _redact_bounded(value: Any, max_length: int) -> tuple[str, bool]:
    text = "" if value is None else str(value)
    return redact_text(text, max_length=max_length), len(text) > max_length


def _extract_trace(metadata: dict[str, Any], *, max_items: int, max_length: int) -> dict[str, Any]:
    trace = metadata.get("trace") if isinstance(metadata, dict) else None
    if not isinstance(trace, dict):
        for value in metadata.values() if isinstance(metadata, dict) else []:
            if isinstance(value, dict) and isinstance(value.get("logs"), list):
                trace = {"agent_steps": value.get("logs", [])}
                break
    if not isinstance(trace, dict):
        return {
            "messages": [],
            "agent_steps": [],
            "tool_events": [],
            "interceptions": [],
            "truncated": False,
        }

    messages = _redact_items(trace.get("messages", []), max_items=max_items, max_length=max_length)
    steps = _redact_items(trace.get("agent_steps", []), max_items=max_items, max_length=max_length)
    interceptions = _redact_items(
        trace.get("interceptions", []),
        max_items=max_items,
        max_length=max_length,
    )
    tool_events = [
        item
        for item in steps[0]
        if str(item.get("step_type", "")).lower() in {"tool_call", "tool_response"}
    ]
    return {
        "messages": messages[0],
        "agent_steps": steps[0],
        "tool_events": tool_events,
        "interceptions": interceptions[0],
        "message_count": len(trace.get("messages", []) or []),
        "agent_step_count": len(trace.get("agent_steps", []) or []),
        "interception_count": len(trace.get("interceptions", []) or []),
        "truncated": messages[1] or steps[1] or interceptions[1],
    }


def _redact_items(
    items: Any,
    *,
    max_items: int,
    max_length: int,
) -> tuple[list[dict[str, Any]], bool]:
    if not isinstance(items, list):
        return [], False
    redacted = []
    for item in items[:max_items]:
        if isinstance(item, dict):
            redacted.append(
                {str(k): redact_text(v, max_length=max_length) for k, v in item.items()}
            )
        else:
            redacted.append({"value": redact_text(item, max_length=max_length)})
    return redacted, len(items) > max_items


def _level_from_metadata(metadata: dict[str, Any]) -> str:
    level = metadata.get("level") if isinstance(metadata, dict) else None
    return str(level or "unknown").lower()


def _extract_monitor_observation_refs(metadata: dict[str, Any]) -> list[str]:
    observations = metadata.get("monitor_observations") if isinstance(metadata, dict) else None
    refs: list[str] = []
    if not isinstance(observations, list):
        return refs
    for row in observations:
        if not isinstance(row, dict):
            continue
        observation_id = row.get("observation_id")
        if observation_id:
            refs.append(str(observation_id))
    return refs


def _extract_trace_artifact_refs(metadata: dict[str, Any]) -> list[str]:
    if not isinstance(metadata, dict):
        return []

    refs: list[str] = []
    raw_refs = metadata.get("trace_artifact_refs", [])
    if isinstance(raw_refs, str):
        raw_refs = [raw_refs]
    if isinstance(raw_refs, list):
        refs.extend(str(ref) for ref in raw_refs if ref)

    for key in ("tampering", "cascade", "runtime_effect"):
        section = metadata.get(key)
        if not isinstance(section, dict):
            continue
        proof = section.get("proof")
        if not isinstance(proof, dict):
            continue
        raw_proof_refs = proof.get("trace_artifact_refs", [])
        if isinstance(raw_proof_refs, str):
            raw_proof_refs = [raw_proof_refs]
        if isinstance(raw_proof_refs, list):
            refs.extend(str(ref) for ref in raw_proof_refs if ref)
        single_ref = proof.get("trace_artifact_ref")
        if single_ref:
            refs.append(str(single_ref))

    return list(dict.fromkeys(refs))


def _target_granularity(
    metadata: dict[str, Any],
    *,
    tier: str,
    risk_type: str,
) -> str:
    explicit = metadata.get("target_granularity") if isinstance(metadata, dict) else None
    if explicit in {"agent", "channel", "trajectory"}:
        return str(explicit)
    risk = str(risk_type)
    if risk == "cascading_failures" or str(tier).lower() == "l3":
        return "trajectory"
    if risk == "message_tampering" or str(tier).lower() == "l2":
        return "channel"
    return "agent"


def _runtime_effect_markers(
    metadata: dict[str, Any],
    *,
    trace: dict[str, Any],
    risk_type: str,
) -> dict[str, Any]:
    markers: dict[str, Any] = {
        "has_runtime_trace": bool(trace.get("message_count") or trace.get("agent_step_count")),
        "trace_message_count": int(trace.get("message_count", 0) or 0),
        "trace_agent_step_count": int(trace.get("agent_step_count", 0) or 0),
        "trace_interception_count": int(trace.get("interception_count", 0) or 0),
    }

    tampering = metadata.get("tampering") if isinstance(metadata, dict) else None
    if isinstance(tampering, dict) or risk_type == "message_tampering":
        trace_interceptions = trace.get("interceptions")
        interceptions = trace_interceptions if isinstance(trace_interceptions, list) else []
        has_original = any(
            bool(row.get("original_content")) for row in interceptions if isinstance(row, dict)
        )
        has_modified = any(
            bool(row.get("modified_content")) for row in interceptions if isinstance(row, dict)
        )
        has_consumed = int(trace.get("agent_step_count", 0) or 0) > 0
        markers["message_tampering"] = {
            "source_agent": (
                (tampering or {}).get("source_agent") if isinstance(tampering, dict) else None
            ),
            "target_agent": (
                (tampering or {}).get("target_agent") if isinstance(tampering, dict) else None
            ),
            "proof_source": _proof_value(tampering, "source"),
            "trace_artifact_ref": _proof_value(tampering, "trace_artifact_ref"),
            "original_message_present": has_original,
            "modified_message_present": has_modified,
            "downstream_consumed": has_consumed,
        }

    cascade = metadata.get("cascade") if isinstance(metadata, dict) else None
    if isinstance(cascade, dict) or risk_type == "cascading_failures":
        trace_agent_steps = trace.get("agent_steps")
        agent_steps = trace_agent_steps if isinstance(trace_agent_steps, list) else []
        chain = []
        for step in agent_steps[:3]:
            if not isinstance(step, dict):
                continue
            step_metadata = step.get("metadata")
            source = (
                str(step_metadata.get("from") or "unknown")
                if isinstance(step_metadata, dict)
                else "unknown"
            )
            target = str(step.get("agent_name") or "unknown")
            chain.append(f"{source}->{target}")
        markers["cascading_failures"] = {
            "failure_type": (
                (cascade or {}).get("failure_type") if isinstance(cascade, dict) else None
            ),
            "proof_source": _proof_value(cascade, "source"),
            "trace_artifact_ref": _proof_value(cascade, "trace_artifact_ref"),
            "propagation_chain": chain,
            "multi_agent_propagation": len(set(chain)) >= 2,
        }

    return markers


def _proof_value(metadata_section: Any, key: str) -> Any:
    if not isinstance(metadata_section, dict):
        return None
    proof = metadata_section.get("proof")
    if not isinstance(proof, dict):
        return None
    return proof.get(key)


def _insufficiency_reasons(
    *,
    risk_type: str,
    tier: str,
    trace: dict[str, Any],
    trace_artifact_refs: list[str],
    truncation: dict[str, bool],
    payload_refs: dict[str, str],
    runtime_effect_markers: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []

    tier_normalized = str(tier).lower()
    l2_or_l3 = tier_normalized in {"l2", "l3"}
    if l2_or_l3 and not runtime_effect_markers.get("has_runtime_trace"):
        reasons.append("missing_runtime_trace")

    if truncation.get("attack_input") and not payload_refs.get("attack_input"):
        reasons.append("missing_attack_input_ref")
    if truncation.get("raw_response") and not payload_refs.get("raw_response"):
        reasons.append("missing_raw_response_ref")
    if truncation.get("trace_items") and not (payload_refs.get("trace") or trace_artifact_refs):
        reasons.append("truncated_trace_without_refs")

    if risk_type == "message_tampering":
        tampering = runtime_effect_markers.get("message_tampering")
        if not isinstance(tampering, dict) or not (
            tampering.get("original_message_present")
            and tampering.get("modified_message_present")
            and tampering.get("downstream_consumed")
        ):
            reasons.append("missing_message_tampering_runtime_markers")

    if risk_type == "cascading_failures":
        cascade = runtime_effect_markers.get("cascading_failures")
        if not isinstance(cascade, dict) or not cascade.get("multi_agent_propagation"):
            reasons.append("missing_cascading_failures_propagation_markers")

    if l2_or_l3 and not trace.get("messages") and not trace.get("agent_steps"):
        reasons.append("empty_runtime_trace")

    return reasons
