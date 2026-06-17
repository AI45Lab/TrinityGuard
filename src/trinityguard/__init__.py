"""TrinityGuard public API façade for the v2 research prototype."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from .level1_framework.base import (
    AgentInfo,
    BaseMAS,
    MessageDeliveryDeniedError,
    MessageHookResult,
    WorkflowResult,
    normalize_message_hook_result,
)

try:
    __version__ = version("trinityguard")
except PackageNotFoundError:  # pragma: no cover - editable tree fallback
    __version__ = "2.0.0-dev"

_LAZY_EXPORTS = {
    "Safety_MAS": ".level3_safety.safety_mas",
    "MonitorSelectionMode": ".level3_safety.safety_mas_types",
    "PolicyConfig": ".runtime",
    "RuntimeProtectionSettings": ".runtime",
    "RuntimeProtector": ".runtime",
    "RuntimeRequest": ".runtime",
    "RuntimeDecision": ".runtime",
    "RuntimeEvent": ".runtime",
    "InMemoryEventSink": ".runtime",
    "JsonlEventSink": ".runtime",
}

__all__ = [
    "AgentInfo",
    "BaseMAS",
    "InMemoryEventSink",
    "JsonlEventSink",
    "MessageDeliveryDeniedError",
    "MessageHookResult",
    "MonitorSelectionMode",
    "PolicyConfig",
    "RuntimeDecision",
    "RuntimeEvent",
    "RuntimeProtectionSettings",
    "RuntimeProtector",
    "RuntimeRequest",
    "Safety_MAS",
    "WorkflowResult",
    "__version__",
    "normalize_message_hook_result",
]


def __getattr__(name: str) -> Any:
    """Lazily expose local research façade objects without importing optional adapters early."""

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
