"""Runtime protection policy configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"none": 0, "info": 1, "warning": 2, "critical": 3}
VALID_DECISIONS = {"allow", "monitor_only", "block"}
VALID_ENFORCEMENT_MODES = {"enforce", "monitor_only"}
VALID_FAIL_MODES = {"open", "closed"}
VALID_BLOCK_MODES = {"replace", "deny"}


@dataclass(frozen=True)
class PolicyConfig:
    """Configuration for the runtime protection MVP policy.

    The MVP keeps policy intentionally small: it maps existing Level 3
    ``JudgeResult`` output into allow/monitor/block decisions and controls
    failure behavior. Production rollout controls are intentionally out of
    scope for Phase 2 MVP.
    """

    name: str = "trinityguard-runtime-mvp"
    version: str = "phase2-mvp"
    enforcement_mode: str = "enforce"
    fail_mode: str = "open"
    block_severity_threshold: str = "critical"
    enabled_checks: tuple[str, ...] = field(default_factory=tuple)
    include_raw_payloads: bool = False
    max_events: int = 100
    fail_closed_on_sink_error: bool = False
    judge_timeout_seconds: float | None = None
    circuit_breaker_failure_threshold: int | None = None

    def __post_init__(self) -> None:
        if self.enforcement_mode not in VALID_ENFORCEMENT_MODES:
            raise ValueError(
                f"PolicyConfig.enforcement_mode must be one of {sorted(VALID_ENFORCEMENT_MODES)}"
            )
        if self.fail_mode not in VALID_FAIL_MODES:
            raise ValueError(f"PolicyConfig.fail_mode must be one of {sorted(VALID_FAIL_MODES)}")
        if self.block_severity_threshold not in SEVERITY_ORDER:
            raise ValueError(
                f"PolicyConfig.block_severity_threshold must be one of {sorted(SEVERITY_ORDER)}"
            )
        if self.max_events < 1:
            raise ValueError("PolicyConfig.max_events must be >= 1")
        if self.judge_timeout_seconds is not None and self.judge_timeout_seconds <= 0:
            raise ValueError("PolicyConfig.judge_timeout_seconds must be > 0")
        if (
            self.circuit_breaker_failure_threshold is not None
            and self.circuit_breaker_failure_threshold < 1
        ):
            raise ValueError("PolicyConfig.circuit_breaker_failure_threshold must be >= 1")
        if not isinstance(self.enabled_checks, tuple):
            object.__setattr__(self, "enabled_checks", tuple(self.enabled_checks))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable policy descriptor."""

        return {
            "name": self.name,
            "version": self.version,
            "enforcement_mode": self.enforcement_mode,
            "fail_mode": self.fail_mode,
            "block_severity_threshold": self.block_severity_threshold,
            "enabled_checks": list(self.enabled_checks),
            "include_raw_payloads": self.include_raw_payloads,
            "max_events": self.max_events,
            "fail_closed_on_sink_error": self.fail_closed_on_sink_error,
            "judge_timeout_seconds": self.judge_timeout_seconds,
            "circuit_breaker_failure_threshold": self.circuit_breaker_failure_threshold,
        }


def load_policy_config(source: str | Path | dict[str, Any]) -> PolicyConfig:
    """Load a PolicyConfig from a JSON file path or mapping."""

    if isinstance(source, (str, Path)):
        data = json.loads(Path(source).read_text(encoding="utf-8"))
    else:
        data = dict(source)

    valid_keys = set(PolicyConfig.__dataclass_fields__)
    unknown = sorted(set(data) - valid_keys)
    if unknown:
        raise ValueError(f"Unknown PolicyConfig keys: {unknown}")
    return PolicyConfig(**data)


@dataclass(frozen=True)
class RuntimeProtectionSettings:
    """Local RuntimeProtector wiring settings for orchestrators.

    This is not production adapter configuration. It only captures the local
    Phase 2/4 runtime wrapper options that higher-level orchestrators pass into
    RuntimeProtectedMonitoredRunner.
    """

    protector: Any | None = None
    refusal_message: str | None = None
    block_mode: str = "replace"
    redact_l2_logs: bool = True

    def __post_init__(self) -> None:
        if self.block_mode not in VALID_BLOCK_MODES:
            raise ValueError(f"block_mode must be one of {sorted(VALID_BLOCK_MODES)}")

    @property
    def is_enabled(self) -> bool:
        """Whether runtime protection is currently configured."""

        return self.protector is not None

    @classmethod
    def enabled(
        cls,
        protector: Any,
        *,
        refusal_message: str | None = None,
        block_mode: str = "replace",
        redact_l2_logs: bool = True,
    ) -> RuntimeProtectionSettings:
        """Build enabled local runtime protection settings."""

        return cls(
            protector=protector,
            refusal_message=refusal_message,
            block_mode=block_mode,
            redact_l2_logs=redact_l2_logs,
        )

    def disabled(self) -> RuntimeProtectionSettings:
        """Return default disabled local runtime protection settings."""

        return RuntimeProtectionSettings()
