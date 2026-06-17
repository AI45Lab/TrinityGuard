from __future__ import annotations

from trinityguard.level2_intermediary.structured_logging import AgentStepLog
from trinityguard.level3_safety.judges.base import BaseJudge, JudgeResult
from trinityguard.level3_safety.monitor_orchestration import (
    build_monitor_observation,
    summarize_golden_monitor_observations,
    validate_monitor_observation_artifact,
)
from trinityguard.level3_safety.monitors.judge_backed import JudgeBackedRiskMonitor


class SpyJudge(BaseJudge):
    def __init__(self, result: JudgeResult | None = None, exc: Exception | None = None):
        super().__init__("message_tampering")
        self.result = result
        self.exc = exc
        self.calls = []

    def analyze(self, content: str, context: dict | None = None):
        self.calls.append((content, context))
        if self.exc:
            raise self.exc
        return self.result

    def get_judge_info(self):
        return {"type": "spy", "version": "1", "description": "spy"}


def _entry(content="tampered content", *, source="planner", target="executor"):
    return AgentStepLog(
        timestamp=1.0,
        agent_name=target,
        step_type="receive",
        content=content,
        metadata={"from": source, "to": target, "message_id": "m1"},
    )


def test_judge_backed_monitor_calls_judge_and_emits_alert_with_invocation_evidence():
    judge = SpyJudge(
        JudgeResult(True, "warning", "risk", ["tampered"], "warn", judge_type="fixture")
    )
    monitor = JudgeBackedRiskMonitor("message_tampering", judge=judge)

    alert = monitor.process(_entry())

    assert judge.calls
    assert alert is not None
    assert alert.evidence["judge_invocation_id"]
    assert alert.evidence["judge_call_count"] == 1
    assert judge.calls[0][1]["runtime_event"]["message_id"] == "m1"


def test_judge_backed_monitor_non_alert_and_insufficient_paths_are_observable():
    benign_judge = SpyJudge(JudgeResult(False, "none", "safe", [], "log", judge_type="fixture"))
    monitor = JudgeBackedRiskMonitor("message_tampering", judge=benign_judge)
    assert monitor.process(_entry("benign handoff")) is None
    assert monitor.last_judge_result["has_risk"] is False

    failing = JudgeBackedRiskMonitor("message_tampering", judge=SpyJudge(exc=RuntimeError("boom")))
    assert failing.process(_entry("tampered")) is None
    assert failing.last_insufficiency_reason.startswith("judge failure")


def test_judge_backed_observation_requires_real_invocation_evidence():
    judge = SpyJudge(
        JudgeResult(True, "warning", "risk", ["tampered"], "warn", judge_type="fixture")
    )
    monitor = JudgeBackedRiskMonitor("message_tampering", judge=judge)
    entry = _entry()
    alert = monitor.process(entry)
    observation = build_monitor_observation(
        log_entry=entry,
        risk_type="message_tampering",
        monitor_name="message_tampering",
        monitor_strategy="judge_backed",
        judge_backed=True,
        observation_type="alert",
        alert=alert,
        step_index=1,
    )
    ok, reason = validate_monitor_observation_artifact(observation)
    assert ok, reason

    broken = dict(observation)
    broken["evidence_refs"] = {"runtime_event_hash": "sha256:abc"}
    ok, reason = validate_monitor_observation_artifact(broken)
    assert not ok
    assert "judge invocation" in reason


def test_judge_backed_non_alert_observation_uses_invocation_metadata():
    monitor = JudgeBackedRiskMonitor(
        "message_tampering",
        judge=SpyJudge(JudgeResult(False, "none", "safe", [], "log", judge_type="fixture")),
    )
    entry = _entry("benign handoff")

    alert = monitor.process(entry)
    observation = build_monitor_observation(
        log_entry=entry,
        risk_type="message_tampering",
        monitor_name="message_tampering",
        monitor_strategy="judge_backed",
        judge_backed=True,
        observation_type=None,
        alert=alert,
        step_index=1,
        judge_metadata=monitor.last_observation_metadata,
    )

    ok, reason = validate_monitor_observation_artifact(observation)
    assert ok, reason
    assert observation["observation_type"] == "non_alert"
    assert observation["evidence_refs"]["judge_invocation_id"]
    assert observation["evidence_refs"]["judge_call_count"] == 1


def test_judge_backed_insufficient_golden_trace_allows_not_invoked_call_count():
    monitor = JudgeBackedRiskMonitor(
        "message_tampering",
        judge=SpyJudge(JudgeResult(True, "warning", "risk", [], "warn", judge_type="fixture")),
    )
    entry = _entry("", source=None)

    alert = monitor.process(entry)
    observation = build_monitor_observation(
        log_entry=entry,
        risk_type="message_tampering",
        monitor_name="message_tampering",
        monitor_strategy="judge_backed",
        judge_backed=True,
        observation_type="insufficient",
        alert=alert,
        step_index=1,
        insufficiency_reason=monitor.last_insufficiency_reason,
        judge_metadata=monitor.last_observation_metadata,
        golden_expectation={
            "case_id": "message_tampering-insufficient",
            "expected_observation_type": "insufficient",
            "source": "unit_golden_trace",
        },
    )

    ok, reason = validate_monitor_observation_artifact(observation)
    assert ok, reason
    assert observation["evidence_refs"]["judge_invocation_id"].startswith("not_invoked:")
    assert observation["evidence_refs"]["judge_call_count"] == 0


def test_golden_monitor_summary_requires_exact_judge_backed_outcomes():
    artifacts = []
    for observation_type, result, content in (
        (
            "alert",
            JudgeResult(True, "warning", "risk", ["tampered"], "warn", judge_type="fixture"),
            "tampered message",
        ),
        (
            "non_alert",
            JudgeResult(False, "none", "safe", [], "log", judge_type="fixture"),
            "benign handoff",
        ),
    ):
        monitor = JudgeBackedRiskMonitor("message_tampering", judge=SpyJudge(result))
        entry = _entry(content)
        alert = monitor.process(entry)
        artifacts.append(
            build_monitor_observation(
                log_entry=entry,
                risk_type="message_tampering",
                monitor_name="message_tampering",
                monitor_strategy="judge_backed",
                judge_backed=True,
                observation_type=observation_type if observation_type == "alert" else None,
                alert=alert,
                step_index=1,
                judge_metadata=monitor.last_observation_metadata,
                golden_expectation={
                    "case_id": f"message_tampering-{observation_type}",
                    "expected_observation_type": observation_type,
                    "source": "unit_golden_trace",
                },
            )
        )

    monitor = JudgeBackedRiskMonitor(
        "message_tampering",
        judge=SpyJudge(JudgeResult(True, "warning", "risk", [], "warn", judge_type="fixture")),
    )
    entry = _entry("", source=None)
    alert = monitor.process(entry)
    artifacts.append(
        build_monitor_observation(
            log_entry=entry,
            risk_type="message_tampering",
            monitor_name="message_tampering",
            monitor_strategy="judge_backed",
            judge_backed=True,
            observation_type="insufficient",
            alert=alert,
            step_index=1,
            insufficiency_reason=monitor.last_insufficiency_reason,
            judge_metadata=monitor.last_observation_metadata,
            golden_expectation={
                "case_id": "message_tampering-insufficient",
                "expected_observation_type": "insufficient",
                "source": "unit_golden_trace",
            },
        )
    )

    metrics = summarize_golden_monitor_observations(
        artifacts,
        required_risks=["message_tampering"],
    )

    assert metrics["passed"] is True
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["per_risk"]["message_tampering"]["judge_backed_samples"] == 3
