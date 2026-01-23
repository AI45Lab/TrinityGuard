"""Base classes for monitor agents in Level 3."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from ...level2_intermediary.structured_logging import AgentStepLog


@dataclass
class Alert:
    """Security alert from a monitor."""
    severity: str  # "info", "warning", "critical"
    risk_type: str
    message: str
    evidence: Dict = field(default_factory=dict)
    recommended_action: str = "log"  # "log", "warn", "block"
    timestamp: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "severity": self.severity,
            "risk_type": self.risk_type,
            "message": self.message,
            "evidence": self.evidence,
            "recommended_action": self.recommended_action,
            "timestamp": self.timestamp
        }


class BaseMonitorAgent(ABC):
    """Abstract base class for runtime monitors."""

    def __init__(self):
        self.config: Dict = {}
        self.state: Dict = {}  # Stateful monitoring

    @abstractmethod
    def get_monitor_info(self) -> Dict[str, str]:
        """Return monitor metadata (name, risk_type, description).

        Returns:
            Dict with keys: name, risk_type, description
        """
        pass

    @abstractmethod
    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process a log entry and return alert if risk detected.

        Args:
            log_entry: Structured log from workflow execution

        Returns:
            Alert if risk detected, None otherwise
        """
        pass

    def reset(self):
        """Reset monitor state (called between workflow runs)."""
        self.state = {}

    def configure(self, config: Dict):
        """Configure monitor with custom settings.

        Args:
            config: Configuration dict
        """
        self.config.update(config)
