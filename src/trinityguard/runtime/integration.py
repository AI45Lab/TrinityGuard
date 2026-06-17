"""Local L1/L2 integration helpers for runtime protection MVP."""

from __future__ import annotations

from typing import Any

from trinityguard.level1_framework.base import BaseMAS, WorkflowResult
from trinityguard.level2_intermediary.runners.monitored import MonitoredWorkflowRunner

from .adapter_contract import MessageHookResult
from .config import RuntimeProtectionSettings
from .events import redact_text
from .protection import RuntimeProtector


def runtime_log_task(settings: RuntimeProtectionSettings, task: str) -> str:
    """Return the workflow-start task text safe for local runtime logging."""

    return redact_text(task) if settings.is_enabled else task


def run_runtime_protected_workflow(
    mas: BaseMAS,
    settings: RuntimeProtectionSettings,
    task: str,
    *,
    stream_callback=None,
    **kwargs: Any,
) -> WorkflowResult:
    """Run a local workflow through runtime protection settings.

    This helper keeps higher-level orchestrators from constructing the local
    RuntimeProtectedMonitoredRunner directly. It is still an offline/local
    integration path, not a production adapter.
    """

    if not settings.is_enabled or settings.protector is None:
        raise ValueError("runtime protection settings must be enabled")
    runner = RuntimeProtectedMonitoredRunner(
        mas,
        settings.protector,
        refusal_message=settings.refusal_message,
        block_mode=settings.block_mode,
        redact_l2_logs=settings.redact_l2_logs,
        stream_callback=stream_callback,
    )
    return runner.run(task, **kwargs)


class RuntimeProtectedMonitoredRunner(MonitoredWorkflowRunner):
    """Monitored L2 runner that applies runtime protection before logging.

    The runner keeps Phase 2.1 local and offline: it composes the existing L1
    dict hook contract with the existing L2 monitored runner, logs redacted
    content by default, and returns the protected message to the workflow. It is
    not a production deployment adapter.
    """

    def __init__(
        self,
        mas: BaseMAS,
        protector: RuntimeProtector,
        *,
        refusal_message: str | None = None,
        block_mode: str = "replace",
        redact_l2_logs: bool = True,
        stream_callback=None,
    ) -> None:
        super().__init__(mas, stream_callback)
        self.protector = protector
        self._runtime_hook = protector.as_message_hook_result(
            refusal_message=refusal_message,
            block_mode=block_mode,
        )
        self.redact_l2_logs = redact_l2_logs

    def run(self, task: str, **kwargs: Any) -> WorkflowResult:
        """Execute workflow with runtime protection and redacted L2 trace task."""

        run_task = self.pre_run_hook(task)
        trace_task = redact_text(run_task) if self.redact_l2_logs else run_task
        self.log_writer.start_trace(trace_task)
        self.mas.register_message_hook(self.on_message)

        try:
            result = self.mas.run_workflow(run_task, **kwargs)
            trace = self.log_writer.end_trace(success=result.success, error=result.error)
            self.logs = trace.agent_steps
            result.metadata["trace"] = trace.to_dict()
            result.metadata["logs"] = [log.to_dict() for log in self.logs]
            return self.post_run_hook(result)
        except Exception as exc:
            trace = self.log_writer.end_trace(success=False, error=redact_text(exc))
            self.logs = trace.agent_steps
            raise
        finally:
            self.mas.clear_message_hooks()

    def on_message(self, message: dict[str, Any]) -> MessageHookResult:
        """Apply runtime protection, log a redacted copy, return protected message."""

        hook_result = self._runtime_hook(message)
        protected_message = hook_result.message
        log_message = dict(protected_message)
        if self.redact_l2_logs:
            log_message["content"] = redact_text(log_message.get("content"))
        super().on_message(log_message)
        self._attach_runtime_metadata_to_current_trace(protected_message)
        return hook_result

    def _attach_runtime_metadata_to_current_trace(self, message: dict[str, Any]) -> None:
        runtime_metadata = message.get("runtime_protection")
        trace = self.log_writer.current_trace
        if not runtime_metadata or trace is None:
            return
        if trace.messages:
            trace.messages[-1].metadata["runtime_protection"] = runtime_metadata
        if trace.agent_steps:
            trace.agent_steps[-1].metadata["runtime_protection"] = runtime_metadata
