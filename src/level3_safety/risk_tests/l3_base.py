"""L3 Base Test Class with Logging Support.

This module provides the base class for all L3 (System-Level Emergent) risk tests
with built-in logging capabilities similar to L1 and L2 tests.
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional

from .base import BaseRiskTest, TestCase


class L3BaseTest(BaseRiskTest):
    """Base class for L3 risk tests with logging support.

    This class extends BaseRiskTest to provide:
    - Automatic test log saving to files
    - Structured log format consistent with L1/L2 tests
    - Configurable log directory and options

    Subclasses should call _save_test_logs() in their run_single_test()
    implementation to enable logging.

    Attributes:
        config: Configuration dictionary with test parameters including:
            - log_dir: Directory for test logs (default: "logs/l3_tests")
            - save_logs: Whether to save logs to file (default: True)
    """

    def __init__(self):
        """Initialize L3 Base Test with logging configuration."""
        super().__init__()
        self.config.update({
            "log_dir": "logs/l3_tests",  # Directory for L3 test logs
            "save_logs": True,           # Enable log saving by default
        })

    def _save_test_logs(
        self,
        test_case: TestCase,
        results: Dict,
        agent_name: Optional[str] = None,
        task_used: Optional[str] = None,
        additional_data: Optional[Dict] = None
    ) -> Optional[str]:
        """Save detailed test logs to file.

        Creates a JSON log file with:
        - Test case info (name, severity, expected behavior)
        - Test results (passed, details, errors)
        - Agent information
        - Task executed
        - Additional test-specific data

        Args:
            test_case: The test case being executed
            results: Results from test execution
            agent_name: Name of the agent being tested (optional)
            task_used: The task that was executed (optional)
            additional_data: Additional test-specific data to include (optional)

        Returns:
            Path to the log file, or None if saving failed

        Example:
            >>> log_file = self._save_test_logs(
            ...     test_case=test_case,
            ...     results=results,
            ...     agent_name="TestAgent",
            ...     task_used="Test cascading failures",
            ...     additional_data={"cascade_depth": 3, "propagation_trace": [...]}
            ... )
        """
        # Check if logging is enabled
        if not self.config.get("save_logs", True):
            return None

        try:
            # Determine log directory
            log_dir = Path(self.config.get("log_dir", "logs/l3_tests"))
            if not log_dir.is_absolute():
                # Project root is 4 levels up from this file (src/level3_safety/risk_tests/l3_base.py)
                project_root = Path(__file__).parent.parent.parent.parent
                log_dir = project_root / log_dir
            log_dir.mkdir(parents=True, exist_ok=True)

            # Generate log filename
            risk_info = self.get_risk_info()
            risk_type = risk_info.get("risk_type", "unknown")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"{risk_type}_{test_case.name}_{timestamp}.json"

            # Build log data structure
            log_data = {
                "test_info": {
                    "risk_type": risk_type,
                    "risk_id": risk_info.get("risk_id", "unknown"),
                    "risk_level": risk_info.get("level", "L3"),
                    "test_case": test_case.name,
                    "severity": test_case.severity,
                    "expected_behavior": test_case.expected_behavior,
                    "test_input": test_case.input,
                    "timestamp": timestamp,
                    "category": risk_info.get("category", "System-Level Risk"),
                },
                "test_config": {
                    "agent_name": agent_name,
                    "task": task_used,
                    "test_metadata": test_case.metadata if test_case.metadata else {},
                },
                "results": {
                    "passed": results.get("passed", False),
                    "error": results.get("error"),
                    "details": results.get("details", {}),
                    # Include agent-specific results if available
                    "agent_results": results.get("agent_results", {}),
                    # Include failure analysis if available
                    "failure_analysis": results.get("failure_analysis", {}),
                },
            }

            # Add additional test-specific data
            if additional_data:
                log_data["additional_data"] = additional_data

            # Write log file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False, default=str)

            return str(log_file)

        except Exception as e:
            # Log saving failed, but don't fail the test
            # Could log this error to the main logger if needed
            return None

    def _save_cascade_test_logs(
        self,
        test_case: TestCase,
        results: Dict,
        agent_name: str,
        cascade_trace: list,
        task_used: Optional[str] = None
    ) -> Optional[str]:
        """Save detailed logs for cascading failure tests.

        This is a specialized version of _save_test_logs for tests involving
        cascading failures and propagation analysis.

        Args:
            test_case: The test case being executed
            results: Results from test execution
            agent_name: Name of the agent being tested
            cascade_trace: List of cascade propagation steps
            task_used: The task that was executed (optional)

        Returns:
            Path to the log file, or None if saving failed
        """
        additional_data = {
            "cascade_analysis": {
                "depth": len(cascade_trace),
                "trace": cascade_trace,
            }
        }

        return self._save_test_logs(
            test_case=test_case,
            results=results,
            agent_name=agent_name,
            task_used=task_used,
            additional_data=additional_data
        )

    def _save_emergence_test_logs(
        self,
        test_case: TestCase,
        results: Dict,
        agent_names: list,
        emergence_analysis: Dict,
        task_used: Optional[str] = None
    ) -> Optional[str]:
        """Save detailed logs for emergence tests.

        This is a specialized version of _save_test_logs for tests involving
        emergent behaviors (group hallucination, malicious emergence, etc.).

        Args:
            test_case: The test case being executed
            results: Results from test execution
            agent_names: List of agent names involved in the test
            emergence_analysis: Analysis of emergent behavior
            task_used: The task that was executed (optional)

        Returns:
            Path to the log file, or None if saving failed
        """
        additional_data = {
            "emergence_analysis": emergence_analysis,
            "agents_involved": agent_names,
        }

        return self._save_test_logs(
            test_case=test_case,
            results=results,
            agent_name=", ".join(agent_names),
            task_used=task_used,
            additional_data=additional_data
        )
