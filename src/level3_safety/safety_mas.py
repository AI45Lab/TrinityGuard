"""Main Safety_MAS class for Level 3."""

from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path
import importlib
import time

from ..level1_framework.base import BaseMAS, WorkflowResult
from ..level1_framework.ag2_wrapper import AG2MAS
from ..level2_intermediary.base import MASIntermediary, RunMode
from ..level2_intermediary.ag2_intermediary import AG2Intermediary
from ..level2_intermediary.structured_logging import AgentStepLog
from .risk_tests.base import BaseRiskTest, TestResult
from .monitor_agents.base import BaseMonitorAgent, Alert
from ..utils.exceptions import MASSafetyError
from ..utils.logging_config import get_logger


class MonitorSelectionMode(Enum):
    """How to select which monitors to activate."""
    MANUAL = "manual"
    AUTO_LLM = "auto_llm"
    PROGRESSIVE = "progressive"


class Safety_MAS:
    """Main safety wrapper for MAS systems."""

    def __init__(self, mas: BaseMAS):
        """Initialize safety wrapper around a MAS instance.

        Args:
            mas: Level 1 MAS instance (e.g., AG2MAS)
        """
        self.mas = mas
        self.intermediary = self._create_intermediary(mas)
        self.risk_tests: Dict[str, BaseRiskTest] = {}
        self.monitor_agents: Dict[str, BaseMonitorAgent] = {}
        self._active_monitors: List[BaseMonitorAgent] = []
        self._test_results: Dict[str, TestResult] = {}
        self._alerts: List[Alert] = []
        self.logger = get_logger("Safety_MAS")

        # Load available risk tests and monitors
        self._load_risk_tests()
        self._load_monitor_agents()

    def _create_intermediary(self, mas: BaseMAS) -> MASIntermediary:
        """Auto-detect and create appropriate intermediary for the MAS type.

        Args:
            mas: Level 1 MAS instance

        Returns:
            Appropriate MASIntermediary instance

        Raises:
            MASSafetyError: If MAS type is not supported
        """
        if isinstance(mas, AG2MAS):
            return AG2Intermediary(mas)
        # Future: elif isinstance(mas, LangGraphMAS): ...
        else:
            raise MASSafetyError(f"Unsupported MAS type: {type(mas)}")

    def _load_risk_tests(self):
        """Discover and load all risk test plugins."""
        # For now, we'll manually register available tests
        # In the future, this could scan the risk_tests directory
        self.logger.info("Loading risk tests...")
        # Tests will be registered as they're implemented
        pass

    def _load_monitor_agents(self):
        """Discover and load all monitor agent plugins."""
        # For now, we'll manually register available monitors
        # In the future, this could scan the monitor_agents directory
        self.logger.info("Loading monitor agents...")
        # Monitors will be registered as they're implemented
        pass

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

    def run_auto_safety_tests(self, task_description: Optional[str] = None) -> Dict[str, Any]:
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

    def run_manual_safety_tests(self, selected_tests: List[str]) -> Dict[str, Any]:
        """Run specific safety tests.

        Args:
            selected_tests: List of test names (e.g., ["jailbreak", "message_tampering"])

        Returns:
            Dict of test results
        """
        self.logger.info(f"Running manual safety tests: {selected_tests}")
        results = {}

        for test_name in selected_tests:
            if test_name not in self.risk_tests:
                self.logger.warning(f"Test '{test_name}' not found")
                results[test_name] = {
                    "error": f"Test '{test_name}' not found",
                    "available_tests": list(self.risk_tests.keys())
                }
                continue

            try:
                test = self.risk_tests[test_name]
                self.logger.log_test_start(test_name, test.config)

                result = test.run(self.intermediary)
                results[test_name] = result.to_dict()

                self.logger.log_test_result(test_name, result.passed, result.to_dict())

            except Exception as e:
                self.logger.error(f"Test '{test_name}' failed: {str(e)}", exc_info=True)
                results[test_name] = {
                    "error": str(e),
                    "status": "crashed"
                }

        self._test_results = results
        return results

    def get_test_report(self) -> str:
        """Generate human-readable test report.

        Returns:
            Formatted test report string
        """
        if not self._test_results:
            return "No test results available. Run tests first."

        report_lines = ["=" * 60, "MAS Safety Test Report", "=" * 60, ""]

        for test_name, result in self._test_results.items():
            if "error" in result:
                report_lines.append(f"❌ {test_name}: ERROR - {result['error']}")
                continue

            passed = result.get("passed", False)
            total = result.get("total_cases", 0)
            failed = result.get("failed_cases", 0)
            pass_rate = result.get("pass_rate", 0) * 100

            status = "✅ PASSED" if passed else "❌ FAILED"
            report_lines.append(f"{status} {test_name}")
            report_lines.append(f"  Cases: {total}, Failed: {failed}, Pass Rate: {pass_rate:.1f}%")

            severity_summary = result.get("severity_summary", {})
            if any(severity_summary.values()):
                report_lines.append(f"  Severity: {severity_summary}")

            report_lines.append("")

        report_lines.append("=" * 60)
        return "\n".join(report_lines)

    # === Runtime Monitoring API ===

    def start_runtime_monitoring(self,
                                 mode: MonitorSelectionMode = MonitorSelectionMode.MANUAL,
                                 selected_monitors: Optional[List[str]] = None):
        """Configure runtime monitoring.

        Args:
            mode: How to select monitors (MANUAL, AUTO_LLM, PROGRESSIVE)
            selected_monitors: List of monitor names (required for MANUAL mode)

        Raises:
            ValueError: If MANUAL mode without selected_monitors
        """
        self.logger.info(f"Starting runtime monitoring in {mode.value} mode")

        if mode == MonitorSelectionMode.MANUAL:
            if not selected_monitors:
                raise ValueError("selected_monitors required for MANUAL mode")
            self._active_monitors = [
                self.monitor_agents[m] for m in selected_monitors
                if m in self.monitor_agents
            ]
            self.logger.info(f"Activated {len(self._active_monitors)} monitors")

        elif mode == MonitorSelectionMode.AUTO_LLM:
            # Future: Use LLM to select appropriate monitors
            self._active_monitors = list(self.monitor_agents.values())
            self.logger.info(f"Auto-selected {len(self._active_monitors)} monitors")

        elif mode == MonitorSelectionMode.PROGRESSIVE:
            # Future: Start with meta-monitor that activates others as needed
            self._active_monitors = list(self.monitor_agents.values())
            self.logger.info("Progressive monitoring activated")

        # Reset all monitors
        for monitor in self._active_monitors:
            monitor.reset()

    def run_task(self, task: str, **kwargs) -> WorkflowResult:
        """Execute MAS task with active monitoring.

        Args:
            task: Task description
            **kwargs: Additional parameters

        Returns:
            WorkflowResult with monitoring data attached
        """
        self.logger.log_workflow_start(task, "monitored")
        self._alerts.clear()
        start_time = time.time()

        # Create stream callback for monitoring
        def stream_callback(log_entry: AgentStepLog):
            self._process_log_entry(log_entry)

        try:
            # Run workflow with monitoring
            result = self.intermediary.run_workflow(
                task,
                mode=RunMode.MONITORED,
                stream_callback=stream_callback
            )

            # Post-execution analysis
            monitoring_report = self._generate_monitoring_report()
            result.metadata['monitoring_report'] = monitoring_report
            result.metadata['alerts'] = [alert.to_dict() for alert in self._alerts]

            duration = time.time() - start_time
            self.logger.log_workflow_end(success=result.success, duration=duration)

            return result

        except Exception as e:
            self.logger.error(f"Task execution failed: {str(e)}", exc_info=True)
            raise

    def _process_log_entry(self, log_entry: AgentStepLog):
        """Feed log entry to all active monitors.

        Args:
            log_entry: Log entry to process
        """
        for monitor in self._active_monitors:
            try:
                alert = monitor.process(log_entry)
                if alert:
                    alert.timestamp = time.time()
                    self._handle_alert(alert)
            except Exception as e:
                self.logger.error(f"Monitor {monitor.get_monitor_info()['name']} failed: {str(e)}")

    def _handle_alert(self, alert: Alert):
        """Handle an alert from a monitor.

        Args:
            alert: Alert to handle
        """
        self._alerts.append(alert)
        self.logger.log_monitor_alert(alert.to_dict())

        # Take action based on recommended_action
        if alert.recommended_action == "block":
            self.logger.error(f"CRITICAL ALERT: {alert.message}")
            # Future: Implement workflow blocking
        elif alert.recommended_action == "warn":
            self.logger.warning(f"WARNING: {alert.message}")

    def _generate_monitoring_report(self) -> Dict:
        """Generate monitoring report from collected alerts.

        Returns:
            Dict with monitoring summary
        """
        return {
            "total_alerts": len(self._alerts),
            "alerts_by_severity": {
                "info": sum(1 for a in self._alerts if a.severity == "info"),
                "warning": sum(1 for a in self._alerts if a.severity == "warning"),
                "critical": sum(1 for a in self._alerts if a.severity == "critical")
            },
            "alerts_by_risk": {},  # Could group by risk_type
            "alerts": [alert.to_dict() for alert in self._alerts]
        }

    def get_alerts(self) -> List[Alert]:
        """Get all alerts from last run.

        Returns:
            List of Alert objects
        """
        return self._alerts
