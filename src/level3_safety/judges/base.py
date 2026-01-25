"""Base classes for judge implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class JudgeResult:
    """Result from judge analysis."""
    has_risk: bool
    severity: str  # "none", "info", "warning", "critical"
    reason: str
    evidence: List[str]
    recommended_action: str  # "log", "warn", "block"
    raw_response: Optional[str] = None
    judge_type: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_risk": self.has_risk,
            "severity": self.severity,
            "reason": self.reason,
            "evidence": self.evidence,
            "recommended_action": self.recommended_action,
            "judge_type": self.judge_type
        }


class BaseJudge(ABC):
    """Abstract base class for all judge implementations."""

    def __init__(self, risk_type: str):
        self.risk_type = risk_type

    @abstractmethod
    def analyze(self, content: str, context: Optional[Dict] = None) -> Optional[JudgeResult]:
        """Analyze content for risks.

        Args:
            content: Content to analyze
            context: Optional additional context

        Returns:
            JudgeResult if analysis successful, None if failed
        """
        pass

    @abstractmethod
    def get_judge_info(self) -> Dict[str, str]:
        """Return judge metadata.

        Returns:
            Dict with keys: type, version, description
        """
        pass
