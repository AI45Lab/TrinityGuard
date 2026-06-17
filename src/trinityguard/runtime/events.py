"""Runtime protection event records and redaction helpers."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any

from .config import PolicyConfig

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9._-]{8,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(authorization\s*:\s*)bearer\s+[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(api[_-]?key|password|token|secret)\s*=\s*[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key|password|token|secret)\s*:\s*[^\s,;]+"),
]


def _safe_text(value: Any) -> str:
    try:
        return "" if value is None else str(value)
    except Exception:  # noqa: BLE001 - redaction must never leak via fallback formatting.
        return "<unrepresentable redacted>"


def _redact_match(match: re.Match[str]) -> str:
    text = match.group(0)
    if "=" in text:
        return text.split("=", 1)[0] + "=<redacted>"
    if ":" in text:
        return text.split(":", 1)[0] + ": <redacted>"
    return "<redacted>"


def redact_text(value: Any, *, max_length: int = 160) -> str:
    """Return a bounded, redacted text summary safe for event evidence."""

    text = _safe_text(value)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(_redact_match, text)
    text = text.replace("\n", " ").replace("\r", " ")
    if len(text) > max_length:
        text = f"{text[: max_length - 3]}..."
    return text


_SECRET_KEY_PATTERN = re.compile(r"(?i)(api[_-]?key|authorization|password|token|secret)")


def redact_mapping(mapping: dict[str, Any]) -> dict[str, str]:
    """Redact mapping values, treating secret-like keys as sensitive."""

    redacted: dict[str, str] = {}
    for key, value in mapping.items():
        text_key = redact_text(key, max_length=120)
        if _SECRET_KEY_PATTERN.search(_safe_text(key)):
            redacted[text_key] = "<redacted>"
        else:
            redacted[text_key] = redact_text(value)
    return redacted


def payload_hash(value: Any) -> str:
    """Return a stable SHA-256 hash for replay/ref evidence."""

    return hashlib.sha256(_safe_text(value).encode("utf-8")).hexdigest()


def payload_summary(value: Any, *, include_raw: bool = False) -> dict[str, Any]:
    """Build a redacted payload evidence summary.

    Raw payloads are not included unless explicitly requested by policy. Even
    opt-in raw fields are redacted to avoid accidental secret persistence in
    local MVP artifacts.
    """

    digest = payload_hash(value)
    summary: dict[str, Any] = {
        "summary": redact_text(value),
        "payload_sha256": digest,
        "payload_ref": f"sha256:{digest}",
    }
    if include_raw:
        summary["raw_payload"] = redact_text(value, max_length=10_000)
    return summary


def sanitize_error(error: BaseException | str | None) -> str | None:
    """Return a secret-safe error string."""

    if error is None:
        return None
    return redact_text(error, max_length=300)


def sanitize_judge_result(result: Any) -> dict[str, Any]:
    """Return redacted, serializable judge evidence."""

    if hasattr(result, "to_dict"):
        payload = dict(result.to_dict())
    else:
        payload = dict(result or {})
    payload["reason"] = redact_text(payload.get("reason", ""), max_length=300)
    payload["evidence"] = [
        redact_text(item, max_length=300) for item in payload.get("evidence", [])
    ]
    payload["raw_response"] = None
    return payload


@dataclass(frozen=True)
class RuntimeRequest:
    """A framework-neutral runtime protection request."""

    request_id: str
    agent_id: str
    action: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, policy: PolicyConfig | None = None) -> dict[str, Any]:
        include_raw = policy.include_raw_payloads if policy else False
        return {
            "request_id": self.request_id,
            "agent_id": redact_text(self.agent_id),
            "action": redact_text(self.action),
            "message": payload_summary(self.message, include_raw=include_raw),
            "context": redact_mapping(self.context),
            "metadata": redact_mapping(self.metadata),
        }


@dataclass(frozen=True)
class RuntimeDecision:
    """Structured runtime policy decision."""

    request_id: str
    policy: PolicyConfig
    decision: str
    reason: str
    judge_results: list[dict[str, Any]] = field(default_factory=list)
    failure: str | None = None
    sink_error: str | None = None

    @property
    def permitted(self) -> bool:
        """Whether the protected operation may continue."""

        return self.decision != "block"

    def with_sink_error(self, error: BaseException | str) -> RuntimeDecision:
        """Return a copy annotated with a secret-safe sink error."""

        return RuntimeDecision(
            request_id=self.request_id,
            policy=self.policy,
            decision=self.decision,
            reason=self.reason,
            judge_results=self.judge_results,
            failure=self.failure,
            sink_error=sanitize_error(error),
        )

    def blocked_by_sink_error(self, error: BaseException | str) -> RuntimeDecision:
        """Return a fail-closed copy caused by event sink failure."""

        return RuntimeDecision(
            request_id=self.request_id,
            policy=self.policy,
            decision="block",
            reason=(
                "Blocked because runtime event sink failed and policy is "
                "fail-closed on sink errors."
            ),
            judge_results=self.judge_results,
            failure=self.failure,
            sink_error=sanitize_error(error),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "policy": {"name": self.policy.name, "version": self.policy.version},
            "decision": self.decision,
            "permitted": self.permitted,
            "reason": redact_text(self.reason, max_length=500),
            "judge_results": self.judge_results,
            "failure": self.failure,
            "sink_error": self.sink_error,
        }


@dataclass(frozen=True)
class RuntimeEvent:
    """Redacted-by-default monitoring/evidence event for a runtime decision."""

    request_id: str
    timestamp: float
    policy: PolicyConfig
    agent_id: str
    action: str
    metadata: dict[str, Any]
    context: dict[str, Any]
    input: dict[str, Any]
    output: dict[str, Any] | None
    judge_results: list[dict[str, Any]]
    decision: RuntimeDecision

    @classmethod
    def from_decision(
        cls,
        *,
        request: RuntimeRequest,
        decision: RuntimeDecision,
        output: Any = None,
    ) -> RuntimeEvent:
        include_raw = decision.policy.include_raw_payloads
        return cls(
            request_id=request.request_id,
            timestamp=time.time(),
            policy=decision.policy,
            agent_id=redact_text(request.agent_id),
            action=redact_text(request.action),
            metadata=redact_mapping(request.metadata),
            context=redact_mapping(request.context),
            input=payload_summary(request.message, include_raw=include_raw),
            output=payload_summary(output, include_raw=include_raw) if output is not None else None,
            judge_results=decision.judge_results,
            decision=decision,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "policy": {"name": self.policy.name, "version": self.policy.version},
            "agent_id": redact_text(self.agent_id),
            "action": redact_text(self.action),
            "metadata": self.metadata,
            "context": self.context,
            "input": self.input,
            "output": self.output,
            "judge_results": self.judge_results,
            "decision": self.decision.to_dict(),
        }
