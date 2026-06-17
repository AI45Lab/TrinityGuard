"""Phase 2 Runtime Protection MVP façade.

This package provides local MVP runtime protection contracts and orchestration.
It is intentionally not a production deployment adapter and does not perform
Garak/OpenRT comparison work.
"""

from importlib import import_module
from typing import Any

from .adapter_contract import (
    MessageDeliveryDeniedError,
    MessageHookResult,
    normalize_message_hook_result,
)

_LAZY_EXPORTS = {
    "PolicyConfig": ".config",
    "RuntimeProtectionSettings": ".config",
    "load_policy_config": ".config",
    "RuntimeDecision": ".events",
    "RuntimeEvent": ".events",
    "RuntimeRequest": ".events",
    "RuntimeProtectedMonitoredRunner": ".integration",
    "runtime_log_task": ".integration",
    "run_runtime_protected_workflow": ".integration",
    "build_runtime_report": ".reporting",
    "build_phase3_readiness_report": ".phase3",
    "write_phase3_readiness_report": ".phase3",
    "RuntimeProtector": ".protection",
    "normalize_proxy_env_for_httpx": ".proxy",
    "export_runtime_report": ".reporting",
    "runtime_metadata_to_decision": ".reporting",
    "summarize_runtime_decisions": ".reporting",
    "verify_runtime_report_artifact": ".reporting",
    "InMemoryEventSink": ".sinks",
    "JsonlEventSink": ".sinks",
    "build_runtime_mvp_validation_report": ".validation",
}

__all__ = [
    "InMemoryEventSink",
    "JsonlEventSink",
    "MessageDeliveryDeniedError",
    "MessageHookResult",
    "PolicyConfig",
    "RuntimeProtectionSettings",
    "load_policy_config",
    "RuntimeDecision",
    "RuntimeEvent",
    "RuntimeProtectedMonitoredRunner",
    "RuntimeProtector",
    "RuntimeRequest",
    "build_runtime_report",
    "export_runtime_report",
    "runtime_metadata_to_decision",
    "runtime_log_task",
    "run_runtime_protected_workflow",
    "summarize_runtime_decisions",
    "verify_runtime_report_artifact",
    "build_runtime_mvp_validation_report",
    "build_phase3_readiness_report",
    "write_phase3_readiness_report",
    "normalize_message_hook_result",
    "normalize_proxy_env_for_httpx",
]


def __getattr__(name: str) -> Any:
    """Lazily expose runtime helpers without importing L1-dependent modules early."""

    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return public façade exports for interactive discovery."""

    return sorted(__all__)
