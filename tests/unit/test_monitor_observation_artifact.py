from __future__ import annotations

from trinityguard.level2_intermediary.structured_logging import AgentStepLog
from trinityguard.level3_safety.monitor_orchestration import (
    build_monitor_observation,
    validate_monitor_observation_artifact,
)
from trinityguard.level3_safety.monitors import MONITOR_COVERAGE
from trinityguard.level3_safety.monitors_base_ref import Alert


def _entry(*, content: str = "runtime trigger", include_route: bool = True) -> AgentStepLog:
    metadata = {"message_id": "obs-1", "attack_type": "prompt_injection", "level": "l1"}
    if include_route:
        metadata.update({"from": "planner", "to": "executor"})
    return AgentStepLog(
        timestamp=1.0,
        agent_name="executor",
        step_type="receive",
        content=content,
        metadata=metadata,
    )


def test_alert_observation_schema_accepts_sufficient_runtime_context():
    observation = build_monitor_observation(
        log_entry=_entry(content="ignore previous"),
        risk_type="prompt_injection",
        monitor_name="prompt_injection",
        monitor_strategy="pattern_based",
        judge_backed=False,
        observation_type="alert",
        alert=Alert(
            severity="warning",
            risk_type="prompt_injection",
            message="detected",
            recommended_action="warn",
            detection_reason="keyword",
        ),
        step_index=1,
    )

    valid, error = validate_monitor_observation_artifact(observation)
    assert valid is True, error


def test_non_alert_observation_schema_accepts_sufficient_benign_context():
    observation = build_monitor_observation(
        log_entry=_entry(content="benign planning update"),
        risk_type="prompt_injection",
        monitor_name="prompt_injection",
        monitor_strategy="pattern_based",
        judge_backed=False,
        observation_type=None,
        alert=None,
        step_index=2,
    )

    valid, error = validate_monitor_observation_artifact(observation)
    assert valid is True, error
    assert observation["observation_type"] == "non_alert"


def test_insufficient_observation_schema_requires_missing_or_truncation_reason():
    observation = build_monitor_observation(
        log_entry=_entry(content="", include_route=False),
        risk_type="prompt_injection",
        monitor_name="prompt_injection",
        monitor_strategy="pattern_based",
        judge_backed=False,
        observation_type="insufficient",
        alert=None,
        step_index=3,
        insufficiency_reason="missing runtime route",
    )

    valid, error = validate_monitor_observation_artifact(observation)
    assert valid is True, error


def test_observation_missing_schema_version_fails():
    observation = build_monitor_observation(
        log_entry=_entry(content="ignore previous"),
        risk_type="prompt_injection",
        monitor_name="prompt_injection",
        monitor_strategy="pattern_based",
        judge_backed=False,
        observation_type="alert",
        alert=Alert(
            severity="warning",
            risk_type="prompt_injection",
            message="detected",
            recommended_action="warn",
            detection_reason="keyword",
        ),
        step_index=1,
    )
    observation.pop("schema_version")

    valid, error = validate_monitor_observation_artifact(observation)
    assert valid is False
    assert "missing required keys" in str(error)


def test_alert_with_insufficient_status_fails():
    observation = build_monitor_observation(
        log_entry=_entry(content="ignore previous"),
        risk_type="prompt_injection",
        monitor_name="prompt_injection",
        monitor_strategy="pattern_based",
        judge_backed=False,
        observation_type="alert",
        alert=Alert(
            severity="warning",
            risk_type="prompt_injection",
            message="detected",
            recommended_action="warn",
            detection_reason="keyword",
        ),
        step_index=1,
    )
    observation["information_sufficiency"]["status"] = "insufficient_missing_content"

    valid, error = validate_monitor_observation_artifact(observation)
    assert valid is False
    assert "alert observation must have sufficient status" in str(error)


def test_non_alert_without_content_seen_fails():
    observation = build_monitor_observation(
        log_entry=_entry(content="benign"),
        risk_type="prompt_injection",
        monitor_name="prompt_injection",
        monitor_strategy="pattern_based",
        judge_backed=False,
        observation_type=None,
        alert=None,
        step_index=2,
    )
    observation["observed_fields"]["content_present"] = False

    valid, error = validate_monitor_observation_artifact(observation)
    assert valid is False
    assert "content and route context" in str(error)


def test_unknown_observation_type_fails():
    observation = build_monitor_observation(
        log_entry=_entry(content="ignore previous"),
        risk_type="prompt_injection",
        monitor_name="prompt_injection",
        monitor_strategy="pattern_based",
        judge_backed=False,
        observation_type="alert",
        alert=Alert(
            severity="warning",
            risk_type="prompt_injection",
            message="detected",
            recommended_action="warn",
            detection_reason="keyword",
        ),
        step_index=1,
    )
    observation["observation_type"] = "unknown"

    valid, error = validate_monitor_observation_artifact(observation)
    assert valid is False
    assert "invalid observation_type" in str(error)


def test_pattern_monitor_cannot_claim_judge_backed():
    assert all(row.get("judge_backed") is False for row in MONITOR_COVERAGE)
