"""L1 Base Test Class with Logging Support.

This module provides the base class for all L1 (Single-Agent) risk tests
with built-in logging capabilities similar to L2 tests.
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional

from .base import BaseRiskTest, TestCase


class L1BaseTest(BaseRiskTest):
    """Base class for L1 risk tests with logging support.

    This class extends BaseRiskTest to provide:
    - Automatic test log saving to files
    - Structured log format consistent with L2 tests
    - Configurable log directory and options

    Subclasses should call _save_test_logs() in their run_single_test()
    implementation to enable logging.

    Attributes:
        config: Configuration dictionary with test parameters including:
            - log_dir: Directory for test logs (default: "logs/l1_tests")
            - save_logs: Whether to save logs to file (default: True)
    """

    def __init__(self):
        """Initialize L1 Base Test with logging configuration."""
        super().__init__()
        self.config.update({
            "log_dir": "logs/l1_tests",  # Directory for L1 test logs
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
            ...     agent_name="Coordinator",
            ...     task_used="Test jailbreak resistance",
            ...     additional_data={"pair_iterations": 5, "attack_history": [...]}
            ... )
        """
        # Check if logging is enabled
        if not self.config.get("save_logs", True):
            return None

        try:
            # Determine log directory
            log_dir = Path(self.config.get("log_dir", "logs/l1_tests"))
            if not log_dir.is_absolute():
                # Project root is 4 levels up from this file (src/level3_safety/risk_tests/l1_base.py)
                project_root = Path(__file__).parent.parent.parent.parent
                log_dir = project_root / log_dir
            log_dir.mkdir(parents=True, exist_ok=True)

            risk_info = self.get_risk_info()
            risk_type = risk_info.get("risk_type", "unknown")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"{risk_type}_{test_case.name}_{timestamp}.json"

            execution = {
                "workflow_success": results.get("error") is None,
                "workflow_error": results.get("error"),
                "agent_results": results.get("agent_results", {}),
                "final_output": results.get("response") or results.get("response_preview"),
                "artifacts": additional_data or {},
            }
            decision = self._build_decision_block(
                results,
                attack_attempted=True,
                attack_succeeded=results.get("attack_succeeded"),
                judge_result=results.get("judge_result"),
                reason=results.get("error") or test_case.expected_behavior,
            )
            log_data = self._build_log_record(
                test_case=test_case,
                results=results,
                task_used=task_used,
                execution=execution,
                judge_result=results.get("judge_result"),
                decision=decision,
                agent_scope={"agent_name": agent_name},
            )

            # Write log file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False, default=str)

            return str(log_file)

        except Exception as e:
            # Log saving failed, but don't fail the test
            # Could log this error to the main logger if needed
            return None

    def _save_pair_test_logs(
        self,
        test_case: TestCase,
        results: Dict,
        agent_name: str,
        attack_history: list,
        task_used: Optional[str] = None
    ) -> Optional[str]:
        """Save detailed logs for PAIR framework tests.

        This is a specialized version of _save_test_logs for tests using
        the PAIR (Prompt Automatic Iterative Refinement) framework.

        Args:
            test_case: The test case being executed
            results: Results from test execution
            agent_name: Name of the agent being tested
            attack_history: List of attack iterations from PAIR framework
            task_used: The task that was executed (optional)

        Returns:
            Path to the log file, or None if saving failed
        """
        additional_data = {
            "pair_framework": {
                "iterations": len(attack_history),
                "attack_history": attack_history,
            }
        }

        return self._save_test_logs(
            test_case=test_case,
            results=results,
            agent_name=agent_name,
            task_used=task_used,
            additional_data=additional_data
        )

    def _save_benchmark_test_logs(
        self,
        test_case: TestCase,
        results: Dict,
        agent_name: str,
        benchmark_results: Dict,
        task_used: Optional[str] = None
    ) -> Optional[str]:
        """Save detailed logs for benchmark tests.

        This is a specialized version of _save_test_logs for benchmark-based tests
        (e.g., hallucination tests using standard datasets).

        Args:
            test_case: The test case being executed
            results: Results from test execution
            agent_name: Name of the agent being tested
            benchmark_results: Detailed benchmark evaluation results
            task_used: The task that was executed (optional)

        Returns:
            Path to the log file, or None if saving failed
        """
        additional_data = {
            "benchmark": benchmark_results
        }

        return self._save_test_logs(
            test_case=test_case,
            results=results,
            agent_name=agent_name,
            task_used=task_used,
            additional_data=additional_data
        )
