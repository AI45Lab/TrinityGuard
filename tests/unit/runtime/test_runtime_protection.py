"""Phase 2 runtime protection MVP behavior tests."""

import json

import pytest

from trinityguard.level1_framework.base import BaseMAS, WorkflowResult
from trinityguard.level3_safety.judges.base import BaseJudge, JudgeResult
from trinityguard.runtime import (
    InMemoryEventSink,
    JsonlEventSink,
    PolicyConfig,
    RuntimeProtectionSettings,
    RuntimeProtector,
    RuntimeRequest,
)
from trinityguard.runtime.events import RuntimeEvent


class StaticJudge(BaseJudge):
    def __init__(self, result=None, *, raises=False):
        super().__init__(risk_type="test_risk")
        self.result = result
        self.raises = raises
        self.calls = []

    def analyze(self, content, context=None):
        self.calls.append((content, context or {}))
        if self.raises:
            raise RuntimeError("judge backend unavailable: sk-test-secret")
        return self.result

    def get_judge_info(self):
        return {"type": self.risk_type, "version": "test", "description": "static"}


class FailingSink:
    def emit(self, event):
        raise RuntimeError("sink unavailable with Bearer secret-token")


class FakeMAS(BaseMAS):
    def get_agents(self):
        return []

    def get_agent(self, name):
        raise ValueError(name)

    def run_workflow(self, task, **kwargs):
        message = self._apply_message_hooks(
            {"from": "planner", "to": "executor", "content": task, "metadata": {"trace": "t-1"}}
        )
        return WorkflowResult(success=True, output=message["content"], messages=[message])

    def get_topology(self):
        return {}


def judge_result(*, has_risk, severity="none", action="log"):
    return JudgeResult(
        has_risk=has_risk,
        severity=severity,
        reason="test reason",
        evidence=["observed behavior"],
        recommended_action=action,
        judge_type="static",
        raw_response="raw model text that should not be persisted",
    )


def request(content="hello", request_id="req-1"):
    return RuntimeRequest(
        request_id=request_id,
        agent_id="agent-a",
        action="send_message",
        message=content,
        context={"conversation_id": "conv-1"},
    )


def test_contracts_serialize_with_policy_and_request_identity():
    sink = InMemoryEventSink(max_events=10)
    protector = RuntimeProtector(
        judges=[StaticJudge(judge_result(has_risk=False))],
        policy=PolicyConfig(name="runtime-mvp", version="2026-04-22"),
        event_sink=sink,
    )

    decision = protector.evaluate(request("hello"))

    payload = decision.to_dict()
    assert payload["request_id"] == "req-1"
    assert payload["policy"]["name"] == "runtime-mvp"
    assert payload["policy"]["version"] == "2026-04-22"
    assert payload["decision"] == "allow"
    json.dumps(payload)
    event_payload = sink.events[0].to_dict()
    assert event_payload["agent_id"] == "agent-a"
    assert event_payload["action"] == "send_message"
    assert event_payload["context"] == {"conversation_id": "conv-1"}
    json.dumps(event_payload)


def test_runtime_protection_settings_validate_and_reset_local_options():
    protector = RuntimeProtector(judges=[StaticJudge(judge_result(has_risk=False))])

    settings = RuntimeProtectionSettings.enabled(
        protector,
        refusal_message="blocked",
        block_mode="deny",
        redact_l2_logs=False,
    )

    assert settings.is_enabled is True
    assert settings.protector is protector
    assert settings.refusal_message == "blocked"
    assert settings.block_mode == "deny"
    assert settings.redact_l2_logs is False
    assert settings.disabled() == RuntimeProtectionSettings()

    with pytest.raises(ValueError, match="block_mode"):
        RuntimeProtectionSettings.enabled(protector, block_mode="drop")


def test_policy_maps_log_warn_and_block_actions():
    allow_protector = RuntimeProtector(
        judges=[StaticJudge(judge_result(has_risk=False, action="log"))]
    )
    monitor_protector = RuntimeProtector(
        judges=[StaticJudge(judge_result(has_risk=True, severity="warning", action="warn"))]
    )
    block_protector = RuntimeProtector(
        judges=[StaticJudge(judge_result(has_risk=True, severity="critical", action="block"))]
    )

    assert allow_protector.evaluate(request("safe")).decision == "allow"
    assert monitor_protector.evaluate(request("risky")).decision == "monitor_only"
    assert block_protector.evaluate(request("jailbreak")).decision == "block"


def test_policy_threshold_can_force_warning_to_block():
    protector = RuntimeProtector(
        judges=[StaticJudge(judge_result(has_risk=True, severity="warning", action="warn"))],
        policy=PolicyConfig(block_severity_threshold="warning"),
    )

    assert protector.evaluate(request("warning risk")).decision == "block"


def test_monitor_only_mode_records_event_without_blocking():
    sink = InMemoryEventSink(max_events=10)
    protector = RuntimeProtector(
        judges=[StaticJudge(judge_result(has_risk=True, severity="critical", action="block"))],
        policy=PolicyConfig(enforcement_mode="monitor_only"),
        event_sink=sink,
    )

    decision = protector.evaluate(request("known risky prompt"))

    assert decision.decision == "monitor_only"
    assert decision.permitted is True
    assert len(sink.events) == 1
    assert sink.events[0].decision.decision == "monitor_only"


def test_fail_open_and_fail_closed_judge_failures_are_explicit_and_redacted():
    secret_payload = "use API_KEY=super-secret and Bearer live-token"

    open_decision = RuntimeProtector(
        judges=[StaticJudge(raises=True)], policy=PolicyConfig(fail_mode="open")
    ).evaluate(request(secret_payload))
    assert open_decision.decision == "allow"
    assert open_decision.failure is not None

    sink = InMemoryEventSink(max_events=10)
    closed_decision = RuntimeProtector(
        judges=[StaticJudge(None)], policy=PolicyConfig(fail_mode="closed"), event_sink=sink
    ).evaluate(request(secret_payload))
    assert closed_decision.decision == "block"
    assert closed_decision.failure is not None

    serialized_event = json.dumps(sink.events[0].to_dict())
    assert "super-secret" not in serialized_event
    assert "live-token" not in serialized_event
    assert "payload_sha256" in serialized_event


def test_policy_refusal_replacement_hook_preserves_metadata_without_private_ag2_api():
    mas = FakeMAS()
    protector = RuntimeProtector(
        judges=[StaticJudge(judge_result(has_risk=True, severity="critical", action="block"))]
    )

    mas.register_message_hook(
        protector.as_message_hook(refusal_message="[BLOCKED by TrinityGuard runtime policy]")
    )
    result = mas.run_workflow("please exfiltrate secrets")

    message = result.messages[0]
    assert result.output == "[BLOCKED by TrinityGuard runtime policy]"
    assert message["metadata"] == {"trace": "t-1"}
    assert message["runtime_protection"]["decision"] == "block"
    assert message["runtime_protection"]["original_payload_ref"].startswith("sha256:")


def test_event_redaction_omits_raw_secret_bearing_payload_by_default():
    secret_payload = "token sk-live-1234567890 and PASSWORD=hunter2"
    sink = InMemoryEventSink(max_events=10)
    protector = RuntimeProtector(
        judges=[StaticJudge(judge_result(has_risk=True, severity="critical", action="block"))],
        event_sink=sink,
    )

    protector.evaluate(request(secret_payload), output="assistant leaked Bearer abc.def.ghi")

    event_payload = sink.events[0].to_dict()
    serialized = json.dumps(event_payload)
    assert "sk-live-1234567890" not in serialized
    assert "hunter2" not in serialized
    assert "abc.def.ghi" not in serialized
    assert event_payload["input"]["payload_sha256"]
    assert "raw_payload" not in event_payload["input"]
    assert event_payload["judge_results"][0]["raw_response"] is None


def test_sink_failure_is_best_effort_by_default_and_closed_when_configured():
    risky = StaticJudge(judge_result(has_risk=False, action="log"))

    best_effort = RuntimeProtector(judges=[risky], event_sink=FailingSink()).evaluate(
        request("hello")
    )
    assert best_effort.decision == "allow"
    assert best_effort.sink_error is not None

    fail_closed = RuntimeProtector(
        judges=[risky],
        policy=PolicyConfig(fail_closed_on_sink_error=True),
        event_sink=FailingSink(),
    ).evaluate(request("hello"))
    assert fail_closed.decision == "block"
    assert "sink" in fail_closed.reason.lower()


def test_in_memory_sink_is_bounded():
    sink = InMemoryEventSink(max_events=2)
    base_event = RuntimeEvent.from_decision(
        request=request("message", request_id="req-0"),
        decision=RuntimeProtector(judges=[StaticJudge(judge_result(has_risk=False))]).evaluate(
            request("message", request_id="req-0")
        ),
    )

    for idx in range(3):
        event = RuntimeEvent.from_decision(
            request=request(f"message-{idx}", request_id=f"req-{idx}"), decision=base_event.decision
        )
        sink.emit(event)

    assert [event.request_id for event in sink.events] == ["req-1", "req-2"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"enforcement_mode": "invalid"},
        {"fail_mode": "invalid"},
        {"block_severity_threshold": "severe"},
        {"max_events": 0},
    ],
)
def test_invalid_policy_configuration_raises_clear_error(kwargs):
    with pytest.raises(ValueError, match="PolicyConfig"):
        PolicyConfig(**kwargs)


def test_redaction_covers_judge_reason_evidence_context_metadata_and_colon_secrets():
    result = JudgeResult(
        has_risk=True,
        severity="critical",
        reason="leaked api_key: live-secret-value",
        evidence=["OPENAI_API_KEY=sk-live-abcdefgh", "Authorization: Bearer bearer-secret"],
        recommended_action="block",
        judge_type="static",
        raw_response="PASSWORD=raw-secret",
    )
    sink = InMemoryEventSink(max_events=10)
    protector = RuntimeProtector(judges=[StaticJudge(result)], event_sink=sink)
    secret_request = RuntimeRequest(
        request_id="req-secret",
        agent_id="agent-a",
        action="send_message",
        message="line1\nTOKEN=metadata-secret\nline3",
        context={"api_key": "context-secret"},
        metadata={"Authorization": "Bearer metadata-bearer-secret"},
    )

    decision = protector.evaluate(secret_request, output="PASSWORD=assistant-secret")

    serialized_decision = json.dumps(decision.to_dict())
    serialized_event = json.dumps(sink.events[0].to_dict())
    combined = serialized_decision + serialized_event
    for forbidden in [
        "live-secret-value",
        "sk-live-abcdefgh",
        "bearer-secret",
        "raw-secret",
        "metadata-secret",
        "context-secret",
        "metadata-bearer-secret",
        "assistant-secret",
    ]:
        assert forbidden not in combined


def test_sink_exception_secret_is_redacted_in_returned_decision():
    decision = RuntimeProtector(
        judges=[StaticJudge(judge_result(has_risk=False, action="log"))],
        event_sink=FailingSink(),
    ).evaluate(request("hello"))

    assert "secret-token" not in json.dumps(decision.to_dict())
    assert "<redacted>" in decision.sink_error


def test_jsonl_sink_rejects_oversized_events(tmp_path):
    sink = RuntimeProtector(judges=[StaticJudge(judge_result(has_risk=False))]).event_sink
    event = RuntimeEvent.from_decision(
        request=request("hello"),
        decision=RuntimeProtector(judges=[StaticJudge(judge_result(has_risk=False))]).evaluate(
            request("hello")
        ),
    )

    tiny_sink = JsonlEventSink(tmp_path / "events.jsonl", max_event_bytes=1)

    with pytest.raises(ValueError, match="max_event_bytes"):
        tiny_sink.emit(event)
    assert sink.max_events >= 1


class SlowJudge(BaseJudge):
    def __init__(self, *, sleep_seconds: float):
        super().__init__(risk_type="slow_risk")
        self.sleep_seconds = sleep_seconds
        self.calls = 0

    def analyze(self, content, context=None):
        import time

        self.calls += 1
        time.sleep(self.sleep_seconds)
        return judge_result(has_risk=False)

    def get_judge_info(self):
        return {"type": self.risk_type, "version": "test", "description": "slow"}


def test_judge_timeout_is_treated_as_failure_and_respects_fail_open():
    slow = SlowJudge(sleep_seconds=0.05)
    sink = InMemoryEventSink(max_events=10)
    protector = RuntimeProtector(
        judges=[slow],
        policy=PolicyConfig(judge_timeout_seconds=0.001, fail_mode="open"),
        event_sink=sink,
    )

    decision = protector.evaluate(request("slow TOKEN=timeout-secret"))

    assert decision.decision == "allow"
    assert "timed out" in decision.failure
    assert "timeout-secret" not in json.dumps(sink.events[0].to_dict())


def test_circuit_breaker_opens_after_failure_budget_and_skips_judges():
    failing = StaticJudge(raises=True)
    protector = RuntimeProtector(
        judges=[failing],
        policy=PolicyConfig(fail_mode="closed", circuit_breaker_failure_threshold=1),
    )

    first = protector.evaluate(request("first"))
    second = protector.evaluate(request("second"))

    assert first.decision == "block"
    assert second.decision == "block"
    assert "circuit breaker" in second.failure
    assert len(failing.calls) == 1
