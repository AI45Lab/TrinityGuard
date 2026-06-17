"""Level 1 public contracts and adapter compatibility exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .base import (
    AgentInfo,
    BaseMAS,
    MessageDeliveryDeniedError,
    MessageHookResult,
    WorkflowResult,
    normalize_message_hook_result,
)

_LAZY_EXPORTS = {
    "A3SCodeAgentSpec": ".a3s.adapter",
    "A3SCodeMAS": ".a3s.adapter",
    "AG2MAS": ".ag2.adapter",
    "create_ag2_mas_from_config": ".ag2.adapter",
}

__all__ = [
    "A3SCodeAgentSpec",
    "A3SCodeMAS",
    "AG2MAS",
    "AgentInfo",
    "BaseMAS",
    "MessageDeliveryDeniedError",
    "MessageHookResult",
    "WorkflowResult",
    "create_ag2_mas_from_config",
    "normalize_message_hook_result",
]


def __getattr__(name: str) -> Any:
    """Lazily expose concrete adapters so base contracts stay lightweight."""

    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return public Level 1 exports for interactive discovery."""

    return sorted(__all__)
