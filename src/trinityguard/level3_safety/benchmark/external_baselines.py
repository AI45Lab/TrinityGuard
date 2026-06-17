"""Readiness checks for external baseline frameworks."""

from __future__ import annotations

import importlib.util
from enum import Enum
from pathlib import Path
from typing import Any

from ..engines.openrt_adapter import load_openrt_attack_class


class BaselineStatus(Enum):
    """External baseline readiness state."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


def build_readiness_report(
    *,
    openrt_root: str | Path = "OpenRT",
    openrt_methods: list[str] | None = None,
) -> dict[str, Any]:
    """Build a no-side-effect readiness report for Garak and OpenRT."""
    methods = openrt_methods or ["direct_attack", "pair_attack", "crescendo"]
    garak_status = _check_garak()
    openrt_methods_report = {
        method: _check_openrt_method(method, openrt_root=openrt_root) for method in methods
    }
    any_openrt_ready = any(
        item["status"] == BaselineStatus.AVAILABLE.value for item in openrt_methods_report.values()
    )
    ready = garak_status["status"] == BaselineStatus.AVAILABLE.value or any_openrt_ready
    return {
        "garak": garak_status,
        "openrt": {
            "root": str(openrt_root),
            "methods": openrt_methods_report,
        },
        "summary": {
            "ready": ready,
            "note": (
                "At least one external baseline is importable."
                if ready
                else "No external baseline is currently runnable; do not claim comparison results."
            ),
        },
    }


def _check_garak() -> dict[str, str]:
    if importlib.util.find_spec("garak") is None:
        return {
            "status": BaselineStatus.UNAVAILABLE.value,
            "reason": "Python package 'garak' is not installed.",
        }
    return {"status": BaselineStatus.AVAILABLE.value, "reason": "Python package importable."}


def _check_openrt_method(method_name: str, *, openrt_root: str | Path) -> dict[str, str]:
    try:
        attack_cls = load_openrt_attack_class(method_name, openrt_root=openrt_root)
    except Exception as exc:
        return {
            "status": BaselineStatus.UNAVAILABLE.value,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    try:
        _smoke_construct_openrt_attack(attack_cls, method_name)
    except Exception as exc:
        return {
            "status": BaselineStatus.UNAVAILABLE.value,
            "reason": f"constructor smoke failed: {type(exc).__name__}: {exc}",
        }
    return {
        "status": BaselineStatus.AVAILABLE.value,
        "reason": f"Loaded {attack_cls.__name__}; constructor smoke passed.",
    }


def _smoke_construct_openrt_attack(attack_cls: type, method_name: str) -> None:
    """Instantiate a known OpenRT attack with inert fakes to catch constructor drift."""
    model = _FakeOpenRTModel()
    judge = _FakeOpenRTJudge()
    kwargs: dict[str, Any] = {"model": model, "verbose": False}
    if method_name == "direct_attack":
        kwargs["judge"] = None
    elif method_name == "pair_attack":
        kwargs.update({"attacker_model": model, "judge": judge, "max_iterations": 1})
    elif method_name == "crescendo":
        kwargs.update(
            {
                "attack_model": model,
                "judge": judge,
                "max_turns": 1,
                "max_backtracks": 0,
            }
        )
    else:
        kwargs["judge"] = judge
    attack_cls(**kwargs)


class _FakeOpenRTModel:
    """Minimal no-network model shape used only for OpenRT constructor smoke."""

    def query(self, *args: Any, **kwargs: Any) -> str:
        return "constructor-smoke-response"

    def set_system_message(self, message: str) -> None:
        self.system_message = message

    def reset_conversation(self) -> None:
        return None

    def remove_last_turn(self) -> None:
        return None

    def get_conversation_history(self) -> list[dict[str, str]]:
        return []


class _FakeOpenRTJudge:
    """Minimal no-network judge shape used only for OpenRT constructor smoke."""

    def evaluate_response(self, query: str, response: str) -> tuple[float, str]:
        return 0.0, "constructor-smoke"

    def is_query_successful(self, query: str, response: str) -> bool:
        return False
