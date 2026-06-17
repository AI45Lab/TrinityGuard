"""Level 2 execution helper tests."""

from contextlib import contextmanager

from trinityguard.level1_framework.base import WorkflowResult
from trinityguard.level2_intermediary.base import RunMode
from trinityguard.level2_intermediary.execution import (
    run_monitored_intermediary_workflow,
    run_with_suppressed_ag2_output,
)


class RecordingIntermediary:
    def __init__(self):
        self.calls = []

    def run_workflow(self, task: str, **kwargs):
        self.calls.append({"task": task, "kwargs": kwargs})
        return WorkflowResult(success=True, output="ok", messages=[], metadata={})


def test_run_monitored_intermediary_workflow_sets_monitored_mode_and_suppresses_output(monkeypatch):
    suppress_calls = []

    @contextmanager
    def fake_suppress(*, suppress_all=False):
        suppress_calls.append(suppress_all)
        yield

    monkeypatch.setattr(
        "trinityguard.level2_intermediary.execution.suppress_ag2_tool_output",
        fake_suppress,
    )
    intermediary = RecordingIntermediary()
    stream_events = []

    result = run_monitored_intermediary_workflow(
        intermediary,
        "task",
        stream_callback=stream_events.append,
        silent=True,
    )

    assert result.output == "ok"
    assert suppress_calls == [True]
    assert intermediary.calls == [
        {
            "task": "task",
            "kwargs": {
                "mode": RunMode.MONITORED,
                "stream_callback": stream_events.append,
                "silent": True,
            },
        }
    ]


def test_run_with_suppressed_ag2_output_wraps_arbitrary_operation(monkeypatch):
    suppress_calls = []

    @contextmanager
    def fake_suppress(*, suppress_all=False):
        suppress_calls.append(suppress_all)
        yield

    monkeypatch.setattr(
        "trinityguard.level2_intermediary.execution.suppress_ag2_tool_output",
        fake_suppress,
    )
    calls = []

    def operation(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return "result"

    result = run_with_suppressed_ag2_output(operation, "intermediary", task="task")

    assert result == "result"
    assert suppress_calls == [True]
    assert calls == [{"args": ("intermediary",), "kwargs": {"task": "task"}}]
