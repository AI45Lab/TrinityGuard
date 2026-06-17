from __future__ import annotations

from trinityguard.level2_intermediary.base import RunMode
from trinityguard.level2_intermediary.factory import create_intermediary
from trinityguard.level3_safety.fixtures.local_mas import (
    LocalMultiAgentMAS,
    RepresentativeLocalMAS,
    build_representative_runtime_effect_matrix,
)


def test_local_mas_fixture_emits_route_complete_events_from_monitored_runner():
    mas = LocalMultiAgentMAS()
    intermediary = create_intermediary(mas)

    result = intermediary.run_workflow("Assess cascading failure risk", mode=RunMode.MONITORED)

    trace = result.metadata["trace"]
    messages = trace["messages"]
    steps = trace["agent_steps"]
    routes = [(row["from_agent"], row["to_agent"]) for row in messages]
    assert ("planner", "executor") in routes
    assert ("executor", "reviewer") in routes
    assert any(step["step_type"] == "tool_call" for step in steps)
    assert result.metadata["local_mas_fixture"]["trace_source"] == "monitored_runner"


def test_local_mas_fixture_applies_hooks_to_each_transition():
    mas = LocalMultiAgentMAS()
    seen: list[tuple[str, str]] = []

    def hook(message: dict) -> dict:
        seen.append((message["from"], message["to"]))
        message = dict(message)
        message["content"] = f"{message['content']} [hooked]"
        return message

    mas.register_message_hook(hook)
    result = mas.run_workflow("Trace the route")

    assert seen[:2] == [("planner", "executor"), ("executor", "reviewer")]
    assert all(
        "[hooked]" in message["content"] for message in result.messages if message.get("content")
    )
    assert result.metadata["local_mas_fixture"]["hooked_transition_count"] >= 2


def test_representative_local_mas_fixture_emits_rt1_rt2_rt3_matrix_rows():
    mas = RepresentativeLocalMAS()
    intermediary = create_intermediary(mas)

    result = intermediary.run_workflow(
        "Build representative paper-alignment runtime evidence",
        mode=RunMode.MONITORED,
    )
    matrix = build_representative_runtime_effect_matrix(result.metadata["trace"])

    assert matrix["passed"] is True
    rows_by_tier = {row["tier"]: row for row in matrix["rows"]}
    assert rows_by_tier["RT1"]["granularity"] == "agent"
    assert rows_by_tier["RT1"]["target_entity"] == "executor"
    assert rows_by_tier["RT2"]["granularity"] == "channel"
    assert rows_by_tier["RT2"]["source_channel"] == "planner.executor"
    assert rows_by_tier["RT2"]["target_channel"] == "executor.reviewer"
    assert rows_by_tier["RT2"]["downstream_consumed"] is True
    assert rows_by_tier["RT3"]["granularity"] == "trajectory"
    assert rows_by_tier["RT3"]["multi_hop_propagation"] is True
    assert rows_by_tier["RT3"]["trajectory_id"] == "representative-trajectory-1"
    assert all(row["trace_artifact_ref"].startswith("sha256:") for row in matrix["rows"])


def test_representative_runtime_effect_matrix_fails_closed_for_empty_trace():
    matrix = build_representative_runtime_effect_matrix(
        {"messages": [], "agent_steps": [], "interceptions": []}
    )

    assert matrix["passed"] is False
    assert set(matrix["missing_tiers"]) == {"RT1", "RT2", "RT3"}
