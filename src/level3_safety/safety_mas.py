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
from .monitoring import GlobalMonitorAgent, apply_monitor_decision
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
        self._active_monitor_names: set = set()
        self._global_monitor: Optional[GlobalMonitorAgent] = None
        self._test_results: Dict[str, TestResult] = {}
        self._alerts: List[Alert] = []
        self._step_counter: int = 0  # 用于追踪步骤序号
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
        self.logger.info("Loading risk tests...")

        # Import risk test registry
        try:
            from .risk_tests import RISK_TESTS

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
            from .monitor_agents import MONITORS

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

    def run_manual_safety_tests(self, selected_tests: List[str], task: str = None,
                                progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Run specific safety tests.

        Args:
            selected_tests: List of test names (e.g., ["jailbreak", "message_tampering"])
            task: Optional task to execute for each test (if None, auto-generates)
            progress_callback: Optional callback function(current, total) for test case progress

        Returns:
            Dict of test results
        """
        self.logger.info(f"Running manual safety tests: {selected_tests}")
        if task:
            self.logger.info(f"Using task: {task[:100]}...")
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

                result = test.run(self.intermediary, task=task, progress_callback=progress_callback)
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
                                 selected_monitors: Optional[List[str]] = None,
                                 progressive_config: Optional[Dict[str, Any]] = None):
        """Configure runtime monitoring.

        Args:
            mode: How to select monitors (MANUAL, AUTO_LLM, PROGRESSIVE)
            selected_monitors: List of monitor names (required for MANUAL mode)
            progressive_config: Optional config for PROGRESSIVE mode

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
            self._active_monitor_names = {m for m in selected_monitors if m in self.monitor_agents}
            self.logger.info(f"Activated {len(self._active_monitors)} monitors")
            self._global_monitor = None

        elif mode == MonitorSelectionMode.AUTO_LLM:
            # Future: Use LLM to select appropriate monitors
            self._active_monitors = list(self.monitor_agents.values())
            self._active_monitor_names = set(self.monitor_agents.keys())
            self.logger.info(f"Auto-selected {len(self._active_monitors)} monitors")
            self._global_monitor = None

        elif mode == MonitorSelectionMode.PROGRESSIVE:
            progressive_config = progressive_config or {}
            initial_active = progressive_config.get("initial_active")
            if initial_active is None:
                initial_active = selected_monitors or []

            self._active_monitor_names = {m for m in initial_active if m in self.monitor_agents}
            self._active_monitors = [
                self.monitor_agents[m] for m in self.monitor_agents
                if m in self._active_monitor_names
            ]

            decision_provider = progressive_config.get("decision_provider")
            config = {k: v for k, v in progressive_config.items() if k not in ("decision_provider", "initial_active")}

            self._global_monitor = GlobalMonitorAgent(
                available_monitors=list(self.monitor_agents.keys()),
                config=config,
                decision_provider=decision_provider
            )
            self._global_monitor.reset()
            self.logger.info("Progressive monitoring activated")

        # Reset all monitors
        for monitor in self._active_monitors:
            monitor.reset()

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
        self.logger.log_workflow_start(task, "monitored")
        self._alerts.clear()
        self._step_counter = 0  # 重置步骤计数器
        start_time = time.time()

        # Create stream callback for monitoring
        def stream_callback(log_entry: AgentStepLog):
            self._process_log_entry(log_entry)

        try:
            # Run workflow with monitoring
            result = self.intermediary.run_workflow(
                task,
                mode=RunMode.MONITORED,
                stream_callback=stream_callback,
                **kwargs  # 传递 silent 等参数
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
        self._step_counter += 1

        for monitor in self._active_monitors:
            try:
                alert = monitor.process(log_entry)
                if alert:
                    # 填充 Alert 的来源追踪字段
                    alert.timestamp = time.time()
                    alert.agent_name = log_entry.agent_name
                    alert.step_index = self._step_counter

                    # 从 log_entry.metadata 提取消息来源信息
                    metadata = log_entry.metadata or {}
                    alert.source_agent = metadata.get("from", log_entry.agent_name)
                    alert.target_agent = metadata.get("to", "")
                    alert.message_id = metadata.get("message_id", "")

                    # 提取触发检测的消息内容
                    content = log_entry.content
                    if isinstance(content, dict):
                        alert.source_message = content.get("content", str(content))
                    else:
                        alert.source_message = str(content) if content else ""

                    self._handle_alert(alert)
            except Exception as e:
                self.logger.error(f"Monitor {monitor.get_monitor_info()['name']} failed: {str(e)}")

        if self._global_monitor is not None:
            decision = self._global_monitor.ingest(
                log_entry,
                active_monitors=sorted(self._active_monitor_names)
            )
            if decision:
                self._apply_progressive_decision(decision)

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

    # === Test-Monitor Linkage API ===

    def run_tests_with_monitoring(self, tests: List[str]) -> Dict[str, Any]:
        """Run tests and use linked monitors to evaluate test responses.

        This method runs the specified tests and for each test that has
        a linked monitor, uses the monitor to provide additional evaluation.

        Args:
            tests: List of test names to run

        Returns:
            Dict with test results and monitor evaluations
        """
        self.logger.info(f"Running tests with monitoring: {tests}")
        results = {}

        for test_name in tests:
            if test_name not in self.risk_tests:
                results[test_name] = {"error": f"Test '{test_name}' not found"}
                continue

            test = self.risk_tests[test_name]

            # Run the test
            try:
                test_result = test.run(self.intermediary)
                result_dict = test_result.to_dict()

                # Check for linked monitor
                linked_monitor_name = test.get_linked_monitor()
                if linked_monitor_name and linked_monitor_name in self.monitor_agents:
                    monitor = self.monitor_agents[linked_monitor_name]

                    # Use monitor to evaluate failed test cases
                    monitor_evaluations = []
                    for detail in result_dict.get("details", []):
                        if not detail.get("passed", True):
                            response = detail.get("response", "")
                            if response:
                                evaluation = test.evaluate_with_monitor(response, monitor)
                                monitor_evaluations.append(evaluation)

                    result_dict["monitor_evaluations"] = monitor_evaluations
                    result_dict["linked_monitor"] = linked_monitor_name

                results[test_name] = result_dict

            except Exception as e:
                self.logger.error(f"Test '{test_name}' failed: {str(e)}", exc_info=True)
                results[test_name] = {"error": str(e), "status": "crashed"}

        self._test_results = results
        return results

    def start_informed_monitoring(self, test_results: Optional[Dict[str, Any]] = None):
        """Start monitoring with context from pre-deployment test results.

        This method configures monitors with information about known
        vulnerabilities discovered during testing, allowing them to
        provide more accurate risk assessment.

        Args:
            test_results: Results from run_tests_with_monitoring or
                         run_manual_safety_tests. If None, uses stored results.
        """
        self.logger.info("Starting informed monitoring...")

        test_results = test_results or self._test_results

        if not test_results:
            self.logger.warning("No test results available for informed monitoring. "
                              "Run tests first or pass test_results parameter.")
            # Fall back to standard monitoring
            self._active_monitors = list(self.monitor_agents.values())
            for monitor in self._active_monitors:
                monitor.reset()
            return

        # Activate all monitors and set test context
        self._active_monitors = []
        self._active_monitor_names = set()

        for monitor_name, monitor in self.monitor_agents.items():
            monitor.reset()

            # Find linked test results
            for test_name, result in test_results.items():
                test = self.risk_tests.get(test_name)
                if test and test.get_linked_monitor() == monitor_name:
                    # Set test context for this monitor
                    if isinstance(result, dict) and "error" not in result:
                        monitor.set_test_context(result)
                        self.logger.info(f"Monitor '{monitor_name}' configured with "
                                       f"test context from '{test_name}'")

            self._active_monitors.append(monitor)
            self._active_monitor_names.add(monitor_name)

        self.logger.info(f"Informed monitoring started with {len(self._active_monitors)} monitors")
        self._global_monitor = None

    def _apply_progressive_decision(self, decision: Dict[str, Any]):
        """Apply global monitor decision to active monitors."""
        new_active, info = apply_monitor_decision(
            available=self.monitor_agents,
            active_names=self._active_monitor_names,
            decision=decision
        )

        if new_active != self._active_monitor_names:
            self._active_monitor_names = new_active
            self._active_monitors = [
                self.monitor_agents[m] for m in self.monitor_agents
                if m in self._active_monitor_names
            ]

        self.logger.info(
            "Global monitor decision applied",
            event_type="monitor_decision",
            extra_data={
                "decision": decision,
                "change": info,
                "active_monitors": sorted(self._active_monitor_names)
            }
        )

    def get_risk_profiles(self) -> Dict[str, Dict]:
        """Get risk profiles from all active monitors.

        Returns:
            Dict mapping monitor names to their risk profiles
        """
        profiles = {}
        for monitor in self._active_monitors:
            info = monitor.get_monitor_info()
            profiles[info.get("name", "unknown")] = monitor.get_risk_profile()
        return profiles

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report combining test results and monitoring data.

        Returns:
            Dict with complete safety assessment
        """
        from ..utils.message_utils import resolve_nested_messages

        report = {
            "test_results": self._test_results,
            "risk_profiles": self.get_risk_profiles(),
            "alerts": [alert.to_dict() for alert in self._alerts],
            "summary": {
                "tests_run": len(self._test_results),
                "tests_passed": sum(
                    1 for r in self._test_results.values()
                    if isinstance(r, dict) and r.get("passed", False)
                ),
                "active_monitors": len(self._active_monitors),
                "total_alerts": len(self._alerts),
                "critical_alerts": sum(1 for a in self._alerts if a.severity == "critical")
            }
        }

        # 解析报告中嵌套的所有 chat_manager 接收方
        report = resolve_nested_messages(report)

        return report
