"""Structured logging for TrinityGuard."""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from .config import get_config


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, 'event_type'):
            log_data['event_type'] = record.event_type
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class StructuredLogger:
    """Centralized structured logging."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up logging handlers based on configuration."""
        config = get_config()

        # Clear existing handlers
        self.logger.handlers.clear()
        self.logger.setLevel(getattr(logging, config.logging.level.upper()))

        # Console handler (human-readable)
        if config.logging.console_output:
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            ))
            self.logger.addHandler(console)

        # File handler (JSON structured)
        if config.logging.file:
            # Resolve log file path relative to project root
            log_file_path = Path(config.logging.file)
            if not log_file_path.is_absolute():
                # Project root is 3 levels up from this file (src/utils/logging_config.py)
                project_root = Path(__file__).parent.parent.parent
                log_file_path = project_root / log_file_path

            # Ensure parent directory exists
            log_file_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file_path)
            if config.logging.format == "json":
                file_handler.setFormatter(JsonFormatter())
            else:
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                ))
            self.logger.addHandler(file_handler)

    def _log(self, level: int, message: str, event_type: Optional[str] = None,
             extra_data: Optional[Dict] = None):
        """Internal log method with extra data support."""
        extra = {}
        if event_type:
            extra['event_type'] = event_type
        if extra_data:
            extra['extra_data'] = extra_data
        self.logger.log(level, message, extra=extra)

    def info(self, message: str, event_type: Optional[str] = None,
             extra_data: Optional[Dict] = None):
        """Log info message."""
        self._log(logging.INFO, message, event_type, extra_data)

    def warning(self, message: str, event_type: Optional[str] = None,
                extra_data: Optional[Dict] = None):
        """Log warning message."""
        self._log(logging.WARNING, message, event_type, extra_data)

    def error(self, message: str, event_type: Optional[str] = None,
              extra_data: Optional[Dict] = None, exc_info: bool = False):
        """Log error message."""
        extra = {}
        if event_type:
            extra['event_type'] = event_type
        if extra_data:
            extra['extra_data'] = extra_data
        self.logger.error(message, extra=extra, exc_info=exc_info)

    def debug(self, message: str, event_type: Optional[str] = None,
              extra_data: Optional[Dict] = None):
        """Log debug message."""
        self._log(logging.DEBUG, message, event_type, extra_data)

    # Specialized logging methods

    def log_test_start(self, test_name: str, config: Dict):
        """Log test start event."""
        self.info(
            f"Starting test: {test_name}",
            event_type="test_start",
            extra_data={"test_name": test_name, "config": config}
        )

    def log_test_result(self, test_name: str, passed: bool, details: Dict):
        """Log test result event."""
        level = logging.INFO if passed else logging.WARNING
        self._log(
            level,
            f"Test completed: {test_name} - {'PASSED' if passed else 'FAILED'}",
            event_type="test_complete",
            extra_data={"test_name": test_name, "passed": passed, "details": details}
        )

    def log_monitor_alert(self, alert: Dict):
        """Log monitor alert event."""
        severity = alert.get('severity', 'warning')
        level = logging.CRITICAL if severity == 'critical' else logging.WARNING
        self._log(
            level,
            f"Monitor alert: {alert.get('message', 'Unknown alert')}",
            event_type="monitor_alert",
            extra_data={"alert": alert}
        )

    def log_workflow_start(self, task: str, mode: str):
        """Log workflow start event."""
        self.info(
            f"Starting workflow: {task[:50]}...",
            event_type="workflow_start",
            extra_data={"task": task, "mode": mode}
        )

    def log_workflow_end(self, success: bool, duration: float):
        """Log workflow end event."""
        self.info(
            f"Workflow completed: {'SUCCESS' if success else 'FAILED'}",
            event_type="workflow_end",
            extra_data={"success": success, "duration_seconds": duration}
        )

    def log_agent_step(self, agent_name: str, step_type: str, content: Any):
        """Log agent step event."""
        self.debug(
            f"Agent step: {agent_name} - {step_type}",
            event_type="agent_step",
            extra_data={"agent_name": agent_name, "step_type": step_type, "content": str(content)[:200]}
        )


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "trinityguard") -> StructuredLogger:
    """Get logger instance."""
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name)
    return _logger
