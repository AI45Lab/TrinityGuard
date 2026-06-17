"""Main Safety_MAS class for Level 3."""

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..level1_framework.base import BaseMAS, WorkflowResult
from ..level2_intermediary.execution import run_monitored_intermediary_workflow
from ..level2_intermediary.factory import create_intermediary
from ..level2_intermediary.structured_logging import AgentStepLog
from ..runtime import RuntimeProtectionSettings, RuntimeProtector
from ..runtime.integration import run_runtime_protected_workflow, runtime_log_task
from ..runtime.reporting import (
    build_runtime_report,
    export_runtime_report,
    runtime_metadata_to_decision,
)
from ..utils.logging_config import get_logger
from . import evaluation_orchestration, monitor_orchestration, safety_reports, test_orchestration
from .attacks.base import BaseRiskTest, TestResult
from .monitors_base_ref import Alert, BaseMonitorAgent
from .safety_mas_types import MonitorSelectionMode


def _runtime_trace_items(trace: dict[str, Any]) -> list[Any]:
    """Return trace rows that may carry runtime metadata."""

    items: list[Any] = []
    for key in ("messages", "agent_steps"):
        value = trace.get(key)
        if isinstance(value, list):
            items.extend(value)
    return items


def _runtime_metadata_from_trace_item(item: Any) -> Any:
    """Extract runtime metadata from a trace/log row."""

    if not isinstance(item, dict):
        return None
    runtime_metadata = item.get("runtime_protection")
    if isinstance(runtime_metadata, dict):
        return runtime_metadata
    metadata = item.get("metadata")
    if isinstance(metadata, dict):
        return metadata.get("runtime_protection")
    return None


class Safety_MAS:  # noqa: N801
    """Main safety wrapper for MAS systems."""

    def __init__(self, mas: BaseMAS):
        """Initialize safety wrapper around a MAS instance.

        Args:
            mas: Level 1 MAS instance (e.g., AG2MAS)
        """
        self.mas = mas
        self.intermediary = create_intermediary(mas)
        self.risk_tests: dict[str, BaseRiskTest] = {}
        self.monitor_agents: dict[str, BaseMonitorAgent] = {}
        self._active_monitors: list[BaseMonitorAgent] = []
        self._active_monitor_names: set = set()
        self._global_monitor: Any | None = None
        self._test_results: dict[str, TestResult] = {}
        self._predeployment_evaluation: dict[str, Any] | None = None
        self._alerts: list[Alert] = []
        self._observations: list[dict[str, Any]] = []
        self._step_counter: int = 0  # 用于追踪步骤序号
        self._runtime_settings = RuntimeProtectionSettings()
        self._runtime_decisions: list[dict[str, Any]] = []
        self.logger = get_logger("Safety_MAS")

        # Load available risk tests and monitors
        self._load_risk_tests()
        self._load_monitor_agents()

    def _load_risk_tests(self):
        """Discover and load all risk test plugins."""
        self.logger.info("Loading risk tests...")

        # Import risk test registry
        try:
            from .attacks import RISK_TESTS

            for name, test_class in RISK_TESTS.items():
                try:
                    test_instance = test_class()
                    self.risk_tests[name] = test_instance
                    self.logger.info(f"Loaded risk test: {name}")
                except Exception as e:
                    self.logger.warning(f"Failed to load risk test '{name}': {str(e)}")

            self.logger.info(f"Loaded {len(self.risk_tests)} risk tests total")

        except ImportError as e:
            self.logger.warning(f"Failed to import risk tests: {str(e)}")

    def _load_monitor_agents(self):
        """Discover and load all monitor agent plugins."""
        self.logger.info("Loading monitor agents...")

        # Import monitor registry
        try:
            from .monitors import MONITORS

            for name, monitor_class in MONITORS.items():
                try:
                    monitor_instance = monitor_class()
                    self.monitor_agents[name] = monitor_instance
                    self.logger.info(f"Loaded monitor agent: {name}")
                except Exception as e:
                    self.logger.warning(f"Failed to load monitor '{name}': {str(e)}")

            self.logger.info(f"Loaded {len(self.monitor_agents)} monitor agents total")

        except ImportError as e:
            self.logger.warning(f"Failed to import monitor agents: {str(e)}")

    def register_risk_test(self, name: str, test: BaseRiskTest):
        """Manually register a risk test.

        Args:
            name: Test name
            test: BaseRiskTest instance
        """
        self.risk_tests[name] = test
        self.logger.info(f"Registered risk test: {name}")

    def register_monitor_agent(self, name: str, monitor: BaseMonitorAgent):
        """Manually register a monitor agent.

        Args:
            name: Monitor name
            monitor: BaseMonitorAgent instance
        """
        self.monitor_agents[name] = monitor
        self.logger.info(f"Registered monitor agent: {name}")

    # === Pre-deployment Testing API ===

    def run_auto_safety_tests(self, task_description: str | None = None) -> dict[str, Any]:
        """Automatically select and run relevant safety tests.

        Args:
            task_description: Optional description of MAS purpose for LLM-based selection

        Returns:
            Dict of test results: {test_name: TestResult}
        """
        self.logger.info("Running auto safety tests...")

        # For now, run all available tests
        # In the future, use LLM to select relevant tests based on task_description
        selected_tests = list(self.risk_tests.keys())

        if not selected_tests:
            self.logger.warning("No risk tests available")
            return {}

        return self.run_manual_safety_tests(selected_tests)

    def run_manual_safety_tests(
        self, selected_tests: list[str], task: str = None, progress_callback: Callable | None = None
    ) -> dict[str, Any]:
        """Run specific safety tests.

        Args:
            selected_tests: List of test names (e.g., ["jailbreak", "message_tampering"])
            task: Optional task to execute for each test (if None, auto-generates)
            progress_callback: Optional callback function(current, total) for test case progress

        Returns:
            Dict of test results
        """
        results = test_orchestration.run_manual_safety_tests(
            risk_tests=self.risk_tests,
            intermediary=self.intermediary,
            selected_tests=selected_tests,
            logger=self.logger,
            task=task,
            progress_callback=progress_callback,
        )
        self._test_results = results
        return results

    def run_predeployment_evaluation(
        self,
        selected_tests: list[str] | None = None,
        *,
        judge: Any | None = None,
        task: str | None = None,
        progress_callback: Callable | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run first-class judge-backed pre-deployment evaluation.

        Safety_MAS intentionally remains a thin façade; attack execution, judge
        invocation, and report aggregation are owned by evaluation_orchestration.
        """

        result = evaluation_orchestration.run_predeployment_evaluation(
            risk_tests=self.risk_tests,
            intermediary=self.intermediary,
            selected_tests=selected_tests,
            judge=judge,
            task=task,
            progress_callback=progress_callback,
            **kwargs,
        )
        self._predeployment_evaluation = result
        return result

    def _save_test_results_to_file(
        self,
        selected_tests: list[str],
        results: dict[str, Any],
        task: str = None,
    ):
        """Save test results to log file based on test level.

        Args:
            selected_tests: List of test names that were run
            results: Test results dictionary
            task: Optional task that was used for testing
        """
        test_orchestration.save_test_results_to_file(
            risk_tests=self.risk_tests,
            selected_tests=selected_tests,
            results=results,
            task=task,
            logger=self.logger,
        )

    def _get_test_level(self, test_names: list[str]) -> str:
        """Determine test level (l1, l2, l3) from test names.

        Reads the level from each registered test's get_risk_info()["level"] field.
        Falls back to "l3" if the test is not found or the level field is missing.

        Args:
            test_names: List of test names

        Returns:
            Test level string (e.g., "l1", "l2", "l3")
        """
        return test_orchestration.get_test_level(self.risk_tests, test_names)

    def _generate_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary from test results.

        Args:
            results: Test results dictionary

        Returns:
            Summary dictionary
        """
        return test_orchestration.generate_summary(results)

    def get_test_report(self) -> str:
        """Generate human-readable test report.

        Returns:
            Formatted test report string
        """
        return safety_reports.build_test_report(self._test_results)

    # === Runtime Protection API ===

    def enable_runtime_protection(
        self,
        protector: RuntimeProtector,
        *,
        refusal_message: str | None = None,
        block_mode: str = "replace",
        redact_l2_logs: bool = True,
    ):
        """Enable the local Phase 2 runtime protection path for run_task.

        This composes RuntimeProtector with the existing L1 hook and L2 monitored
        runner contracts. It is a local integration path, not a production
        deployment adapter.
        """
        self._runtime_settings = RuntimeProtectionSettings.enabled(
            protector,
            refusal_message=refusal_message,
            block_mode=block_mode,
            redact_l2_logs=redact_l2_logs,
        )
        self.logger.info("Runtime protection enabled")

    def disable_runtime_protection(self):
        """Disable the local runtime protection path."""
        self._runtime_settings = self._runtime_settings.disabled()
        self.logger.info("Runtime protection disabled")

    # === Runtime Monitoring API ===

    def start_runtime_monitoring(
        self,
        mode: MonitorSelectionMode = MonitorSelectionMode.MANUAL,
        selected_monitors: list[str] | None = None,
        progressive_config: dict[str, Any] | None = None,
    ):
        """Configure runtime monitoring.

        Args:
            mode: How to select monitors (MANUAL, AUTO_LLM, PROGRESSIVE)
            selected_monitors: List of monitor names (required for MANUAL mode)
            progressive_config: Optional config for PROGRESSIVE mode

        Raises:
            ValueError: If MANUAL mode without selected_monitors
        """
        selection = monitor_orchestration.configure_runtime_monitoring(
            mode=mode,
            monitor_agents=self.monitor_agents,
            selected_monitors=selected_monitors,
            progressive_config=progressive_config,
            logger=self.logger,
        )
        self._active_monitors = selection.active_monitors
        self._active_monitor_names = selection.active_monitor_names
        self._global_monitor = selection.global_monitor

    def run_task(self, task: str, **kwargs) -> WorkflowResult:
        """Execute MAS task with active monitoring.

        Args:
            task: Task description
            **kwargs: Additional parameters including:
                - max_round: Maximum conversation rounds
                - silent: If True, suppress AG2 native console output

        Returns:
            WorkflowResult with monitoring data attached
        """
        runtime_settings = self._runtime_settings
        log_task = runtime_log_task(runtime_settings, task)
        self.logger.log_workflow_start(log_task, "monitored")
        self._alerts.clear()
        self._observations.clear()
        self._step_counter = 0  # 重置步骤计数器
        start_time = time.time()

        # Create stream callback for monitoring
        def stream_callback(log_entry: AgentStepLog):
            self._process_log_entry(log_entry)

        try:
            # Run workflow with monitoring.
            if runtime_settings.is_enabled:
                result = run_runtime_protected_workflow(
                    self.mas,
                    runtime_settings,
                    task,
                    stream_callback=stream_callback,
                    **kwargs,
                )
            else:
                result = run_monitored_intermediary_workflow(
                    self.intermediary,
                    task,
                    stream_callback=stream_callback,
                    **kwargs,
                )

            # Post-execution analysis
            if runtime_settings.is_enabled:
                self._record_runtime_decisions(result)
            monitoring_report = self._generate_monitoring_report()
            result.metadata["monitoring_report"] = monitoring_report
            result.metadata["alerts"] = [alert.to_dict() for alert in self._alerts]
            result.metadata["runtime_protection"] = self._runtime_report()

            duration = time.time() - start_time
            self.logger.log_workflow_end(success=result.success, duration=duration)

            return result

        except Exception as e:
            self.logger.error(f"Task execution failed: {str(e)}", exc_info=True)
            raise

    def _record_runtime_decisions(self, result: WorkflowResult) -> None:
        """Record redacted runtime decisions from a workflow result."""

        seen: set[tuple[Any, Any, Any]] = set()

        def record_once(runtime_metadata: Any) -> None:
            if not isinstance(runtime_metadata, dict) or not runtime_metadata:
                return
            key = (
                runtime_metadata.get("request_id"),
                runtime_metadata.get("original_payload_ref"),
                runtime_metadata.get("delivery_action"),
            )
            if key in seen:
                return
            seen.add(key)
            self._record_runtime_metadata(runtime_metadata)

        for message in result.messages:
            runtime_metadata = (
                message.get("runtime_protection") if isinstance(message, dict) else None
            )
            record_once(runtime_metadata)

        denied_metadata = result.metadata.get("delivery_denied", {}).get("message", {})
        if isinstance(denied_metadata, dict):
            record_once(denied_metadata.get("runtime_protection"))

        trace = result.metadata.get("trace")
        if isinstance(trace, dict):
            for item in _runtime_trace_items(trace):
                record_once(_runtime_metadata_from_trace_item(item))

        logs = result.metadata.get("logs")
        if isinstance(logs, list):
            for item in logs:
                record_once(_runtime_metadata_from_trace_item(item))

    def _record_runtime_metadata(self, runtime_metadata: Any) -> None:
        """Record one redacted runtime metadata row if present."""

        if not isinstance(runtime_metadata, dict) or not runtime_metadata:
            return
        self._runtime_decisions.append(runtime_metadata_to_decision(runtime_metadata))

    def export_runtime_report(self, output_path: str | Path, *, source: str = "Safety_MAS"):
        """Export the current local runtime-protection report as a JSON artifact."""

        return export_runtime_report(self._runtime_report(), output_path, source=source)

    def _runtime_report(self) -> dict[str, Any]:
        """Return stable runtime-protection report metadata."""

        policy = None
        runtime_settings = self._runtime_settings
        if runtime_settings.protector is not None:
            policy = {
                "name": runtime_settings.protector.policy.name,
                "version": runtime_settings.protector.policy.version,
            }

        return build_runtime_report(
            enabled=runtime_settings.is_enabled,
            policy=policy,
            block_mode=runtime_settings.block_mode if runtime_settings.is_enabled else None,
            decisions=self._runtime_decisions,
        )

    def _process_log_entry(self, log_entry: AgentStepLog):
        """Feed log entry to all active monitors.

        Args:
            log_entry: Log entry to process
        """
        state = monitor_orchestration.process_log_entry(
            log_entry=log_entry,
            monitor_agents=self.monitor_agents,
            active_monitors=self._active_monitors,
            active_monitor_names=self._active_monitor_names,
            global_monitor=self._global_monitor,
            alerts=self._alerts,
            observations=self._observations,
            step_counter=self._step_counter,
            logger=self.logger,
        )
        self._active_monitors = state.active_monitors
        self._active_monitor_names = state.active_monitor_names
        self._step_counter = state.step_counter

    def _handle_alert(self, alert: Alert):
        """Handle an alert from a monitor.

        Args:
            alert: Alert to handle
        """
        monitor_orchestration.handle_alert(alert, alerts=self._alerts, logger=self.logger)

    def _generate_monitoring_report(self) -> dict:
        """Generate monitoring report from collected alerts.

        Returns:
            Dict with monitoring summary
        """
        return monitor_orchestration.generate_monitoring_report(self._alerts, self._observations)

    def get_alerts(self) -> list[Alert]:
        """Get all alerts from last run.

        Returns:
            List of Alert objects
        """
        return self._alerts

    # === Test-Monitor Linkage API ===

    def run_tests_with_monitoring(self, tests: list[str]) -> dict[str, Any]:
        """Run tests and use linked monitors to evaluate test responses.

        This method runs the specified tests and for each test that has
        a linked monitor, uses the monitor to provide additional evaluation.

        Args:
            tests: List of test names to run

        Returns:
            Dict with test results and monitor evaluations
        """
        results = test_orchestration.run_tests_with_monitoring(
            risk_tests=self.risk_tests,
            monitor_agents=self.monitor_agents,
            intermediary=self.intermediary,
            tests=tests,
            logger=self.logger,
        )
        self._test_results = results
        return results

    def start_informed_monitoring(self, test_results: dict[str, Any] | None = None):
        """Start monitoring with context from pre-deployment test results.

        This method configures monitors with information about known
        vulnerabilities discovered during testing, allowing them to
        provide more accurate risk assessment.

        Args:
            test_results: Results from run_tests_with_monitoring or
                         run_manual_safety_tests. If None, uses stored results.
        """
        test_results = test_results or self._test_results
        selection = monitor_orchestration.start_informed_monitoring(
            risk_tests=self.risk_tests,
            monitor_agents=self.monitor_agents,
            test_results=test_results,
            logger=self.logger,
        )
        self._active_monitors = selection.active_monitors
        self._active_monitor_names = selection.active_monitor_names
        self._global_monitor = selection.global_monitor

    def _apply_progressive_decision(self, decision: dict[str, Any]):
        """Apply global monitor decision to active monitors."""
        selection = monitor_orchestration.apply_progressive_monitor_decision(
            monitor_agents=self.monitor_agents,
            active_monitor_names=self._active_monitor_names,
            decision=decision,
            logger=self.logger,
        )
        self._active_monitors = selection.active_monitors
        self._active_monitor_names = selection.active_monitor_names

    def get_risk_profiles(self) -> dict[str, dict]:
        """Get risk profiles from all active monitors.

        Returns:
            Dict mapping monitor names to their risk profiles
        """
        return monitor_orchestration.get_risk_profiles(self._active_monitors)

    def get_comprehensive_report(self) -> dict[str, Any]:
        """Generate a comprehensive report combining test results and monitoring data.

        Returns:
            Dict with complete safety assessment
        """
        return safety_reports.build_comprehensive_report(
            test_results=self._test_results,
            risk_profiles=self.get_risk_profiles(),
            alerts=self._alerts,
            runtime_protection=self._runtime_report(),
            active_monitor_count=len(self._active_monitors),
        )
