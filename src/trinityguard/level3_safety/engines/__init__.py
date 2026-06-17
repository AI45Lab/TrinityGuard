"""Reusable attack engines and optional external engine adapters."""

from .openrt_adapter import (
    NonAuthoritativeInlineJudge,
    OpenRTSimulationEngine,
    OpenRTUnavailableError,
    TrinityGuardTargetModel,
    build_openrt_attack,
    default_openrt_execution_mode,
    load_openrt_attack_class,
    normalize_openrt_result,
)

__all__ = [
    "NonAuthoritativeInlineJudge",
    "OpenRTUnavailableError",
    "OpenRTSimulationEngine",
    "TrinityGuardTargetModel",
    "build_openrt_attack",
    "default_openrt_execution_mode",
    "load_openrt_attack_class",
    "normalize_openrt_result",
]
