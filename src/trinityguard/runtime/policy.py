"""Policy mapping from Level 3 judge results to runtime decisions."""

from __future__ import annotations

from typing import Any

from .config import SEVERITY_ORDER, PolicyConfig
from .events import RuntimeDecision, sanitize_error, sanitize_judge_result

_DECISION_RANK = {"allow": 0, "monitor_only": 1, "block": 2}


def _severity(result: dict[str, Any]) -> int:
    return SEVERITY_ORDER.get(str(result.get("severity", "none")), 0)


def _result_decision(result: dict[str, Any], policy: PolicyConfig) -> str:
    if not result.get("has_risk", False):
        return "allow"
    if policy.enforcement_mode == "monitor_only":
        return "monitor_only"
    if _severity(result) >= SEVERITY_ORDER[policy.block_severity_threshold]:
        return "block"
    action = str(result.get("recommended_action", "log"))
    if action == "block":
        return "block"
    if action == "warn" or result.get("has_risk", False):
        return "monitor_only"
    return "allow"


def decide_from_judge_results(
    *,
    request_id: str,
    policy: PolicyConfig,
    judge_results: list[Any],
    failures: list[BaseException | str] | None = None,
) -> RuntimeDecision:
    """Map judge outputs and failures into one runtime decision."""

    failures = failures or []
    sanitized_results = [sanitize_judge_result(result) for result in judge_results]

    if sanitized_results:
        decisions = [_result_decision(result, policy) for result in sanitized_results]
        final = max(decisions, key=lambda value: _DECISION_RANK[value])
        strongest = max(
            sanitized_results,
            key=lambda result: (
                _DECISION_RANK[_result_decision(result, policy)],
                _severity(result),
            ),
        )
        reason = strongest.get("reason") or f"Runtime policy mapped judge result to {final}."
        failure = "; ".join(filter(None, (sanitize_error(error) for error in failures))) or None
        return RuntimeDecision(
            request_id=request_id,
            policy=policy,
            decision=final,
            reason=reason,
            judge_results=sanitized_results,
            failure=failure,
        )

    if failures:
        failure_text = "; ".join(filter(None, (sanitize_error(error) for error in failures)))
        if policy.fail_mode == "closed":
            return RuntimeDecision(
                request_id=request_id,
                policy=policy,
                decision="block",
                reason="Runtime judge failed and policy fail_mode is closed.",
                failure=failure_text,
            )
        return RuntimeDecision(
            request_id=request_id,
            policy=policy,
            decision="allow",
            reason="Runtime judge failed and policy fail_mode is open.",
            failure=failure_text,
        )

    if policy.fail_mode == "closed":
        return RuntimeDecision(
            request_id=request_id,
            policy=policy,
            decision="block",
            reason="No runtime judge result was produced and policy fail_mode is closed.",
            failure="no_judge_result",
        )
    return RuntimeDecision(
        request_id=request_id,
        policy=policy,
        decision="allow",
        reason="No runtime judge result was produced and policy fail_mode is open.",
        failure="no_judge_result",
    )
