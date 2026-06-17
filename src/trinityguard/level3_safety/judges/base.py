"""Base classes for judge implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JudgeResult:
    """Result from judge analysis."""

    has_risk: bool | None
    severity: str  # "none", "info", "warning", "critical", "inconclusive", "invalid"
    reason: str
    evidence: list[str]
    recommended_action: str  # "log", "warn", "block", "none"
    raw_response: str | None = None
    judge_type: str = "unknown"
    parse_status: str = "valid"  # valid | invalid | inconclusive
    missing_fields: list[str] = field(default_factory=list)
    invalid_fields: list[str] = field(default_factory=list)
    sufficiency_status: str = "sufficient"  # sufficient | insufficient

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_risk": self.has_risk,
            "severity": self.severity,
            "reason": self.reason,
            "evidence": self.evidence,
            "recommended_action": self.recommended_action,
            "judge_type": self.judge_type,
            "parse_status": self.parse_status,
            "missing_fields": list(self.missing_fields),
            "invalid_fields": list(self.invalid_fields),
            "sufficiency_status": self.sufficiency_status,
        }


class BaseJudge(ABC):
    """Abstract base class for all judge implementations."""

    def __init__(self, risk_type: str):
        self.risk_type = risk_type

    @abstractmethod
    def analyze(self, content: str, context: dict | None = None) -> JudgeResult | None:
        """Analyze content for risks.

        Args:
            content: Content to analyze
            context: Optional additional context

        Returns:
            JudgeResult if analysis successful, None if failed
        """
        pass

    @abstractmethod
    def get_judge_info(self) -> dict[str, str]:
        """Return judge metadata.

        Returns:
            Dict with keys: type, version, description
        """
        pass
