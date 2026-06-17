"""Canonical runtime adapter contract for L1 message delivery decisions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_HOOK_ACTIONS = {"allow", "replace", "deny"}
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9._-]{8,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(api[_-]?key|password|token|secret)\s*=\s*[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key|password|token|secret)\s*:\s*[^\s,;]+"),
]
_SECRET_KEY_PATTERN = re.compile(r"(?i)(api[_-]?key|authorization|password|token|secret)")


def _redact_hook_text(value: Any, *, max_length: int = 240) -> str:
    """Return secret-safe text for hook protocol evidence."""

    try:
        text = "" if value is None else str(value)
    except Exception:  # noqa: BLE001 - protocol evidence must not leak fallback values.
        text = "<unrepresentable redacted>"
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(_redact_hook_match, text)
    text = text.replace("\n", " ").replace("\r", " ")
    if len(text) > max_length:
        return f"{text[: max_length - 3]}..."
    return text


def _redact_hook_match(match: re.Match[str]) -> str:
    text = match.group(0)
    if "=" in text:
        return text.split("=", 1)[0] + "=<redacted>"
    if ":" in text:
        return text.split(":", 1)[0] + ": <redacted>"
    return "<redacted>"


def _redact_hook_value(value: Any) -> Any:
    """Recursively redact hook-result evidence without changing delivery payloads."""

    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            safe_key = _redact_hook_text(key, max_length=120)
            if _SECRET_KEY_PATTERN.search(str(key)):
                redacted[safe_key] = "<redacted>"
            else:
                redacted[safe_key] = _redact_hook_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_hook_value(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_hook_value(item) for item in value]
    return _redact_hook_text(value)


@dataclass(frozen=True)
class MessageHookResult:
    """Structured result from a Level 1 message hook.

    The legacy hook contract returns a modified message dict. This structured
    result preserves that behavior while also allowing adapters to distinguish
    a refusal replacement from a true deny-before-send decision.
    """

    action: str
    message: dict[str, Any]
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.action not in _HOOK_ACTIONS:
            raise ValueError(f"MessageHookResult.action must be one of {sorted(_HOOK_ACTIONS)}")

    @classmethod
    def allow(
        cls,
        message: dict[str, Any],
        *,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MessageHookResult:
        """Permit delivery of the message."""

        return cls("allow", message, reason=reason, metadata=dict(metadata or {}))

    @classmethod
    def replace(
        cls,
        message: dict[str, Any],
        *,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MessageHookResult:
        """Deliver a modified message."""

        return cls("replace", message, reason=reason, metadata=dict(metadata or {}))

    @classmethod
    def deny(
        cls,
        message: dict[str, Any],
        *,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MessageHookResult:
        """Deny delivery before the adapter sends the message."""

        return cls("deny", message, reason=reason, metadata=dict(metadata or {}))

    def to_dict(self) -> dict[str, Any]:
        """Return redacted hook evidence safe for local artifacts."""

        return {
            "action": self.action,
            "reason": _redact_hook_text(self.reason or ""),
            "message": _redact_hook_value(self.message),
            "metadata": _redact_hook_value(self.metadata),
        }


class MessageDeliveryDeniedError(Exception):
    """Raised by legacy dict-only hook application when a hook denies delivery."""

    def __init__(self, result: MessageHookResult) -> None:
        self.result = result
        super().__init__(_redact_hook_text(result.reason or "message delivery denied"))


def normalize_message_hook_result(raw: dict[str, Any] | MessageHookResult) -> MessageHookResult:
    """Normalize legacy dict hook returns into the structured hook protocol."""

    if isinstance(raw, MessageHookResult):
        return raw
    if isinstance(raw, dict):
        return MessageHookResult.replace(raw)
    raise TypeError("message hooks must return a dict or MessageHookResult")


__all__ = [
    "MessageDeliveryDeniedError",
    "MessageHookResult",
    "normalize_message_hook_result",
]
