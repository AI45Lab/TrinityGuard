"""
EvoAgent Workflow Security Testing

This script provides comprehensive security testing for EvoAgent workflows using
the MASSafetyGuard framework. It tests all workflows in the workflow/ folder
against all 20 security risks (L1, L2, L3) and generates detailed reports.

Usage:
    # Run all workflows with full monitoring
    python tests/evoagent_bench/test_evoagent_workflows.py

    # Run specific workflows
    python tests/evoagent_bench/test_evoagent_workflows.py --workflows my_workflow.json

    # Disable LLM judge (faster, use heuristics)
    python tests/evoagent_bench/test_evoagent_workflows.py --no-llm-judge

    # Custom output directory
    python tests/evoagent_bench/test_evoagent_workflows.py --output-dir ./custom_logs

    # Specify which monitors to enable
    python tests/evoagent_bench/test_evoagent_workflows.py --monitors jailbreak prompt_injection

    # Dry run (show what would be tested without running)
    python tests/evoagent_bench/test_evoagent_workflows.py --dry-run
"""

import sys
import argparse
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import traceback
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.level1_framework.evoagentx_adapter import create_ag2_mas_from_evoagentx
from src.level3_safety.safety_mas import Safety_MAS, MonitorSelectionMode
from src.utils.logging_config import get_logger


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class WorkflowTestResult:
    """Complete test result for a single workflow"""
    workflow_name: str
    workflow_path: str
    goal: str
    timestamp: str
    success: bool
    error_message: Optional[str] = None

    # Pre-deployment test results
    pre_deployment_tests: Dict[str, Any] = field(default_factory=dict)

    # Runtime monitoring results
    runtime_execution: Dict[str, Any] = field(default_factory=dict)
    runtime_alerts: List[Dict[str, Any]] = field(default_factory=list)

    # Statistics
    total_messages: int = 0
    total_tool_calls: int = 0
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


# =============================================================================
# Main Test Runner
# =============================================================================

class WorkflowTestRunner:
    """Main orchestrator for workflow testing"""

    def __init__(self, config_path: str):
        """Initialize with configuration

        Args:
            config_path: Path to configuration file
        """
        self.logger = get_logger("WorkflowTestRunner")
        self.config = self._load_config(config_path)

        # Extract configuration
        self.use_llm_judge = self.config.get("testing", {}).get("use_llm_judge", True)
        self.continue_on_error = self.config.get("testing", {}).get("continue_on_error", True)
        self.log_level = self.config.get("testing", {}).get("log_level", "detailed")
        self.workflow_timeout = self.config.get("testing", {}).get("workflow_timeout", 300)

        self.output_config = self.config.get("output", {})
        self.log_dir = Path(self.output_config.get("log_dir", "tests/evoagent_bench/logs"))
        self.use_timestamps = self.output_config.get("use_timestamps", True)
        self.pretty_json = self.output_config.get("pretty_json", True)
        self.generate_summary = self.output_config.get("generate_summary", True)

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Initialized WorkflowTestRunner")
        self.logger.info(f"Log directory: {self.log_dir}")
        self.logger.info(f"Use LLM judge: {self.use_llm_judge}")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary
        """
        config_file = Path(config_path)

        if not config_file.exists():
            self.logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._get_default_config()

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.logger.info(f"Loaded configuration from: {config_path}")
        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration

        Returns:
            Default configuration dictionary
        """
        return {
            "monitoring": {
                "enabled_monitors": self._get_all_risk_names()
            },
            "testing": {
                "use_llm_judge": True,
                "continue_on_error": True,
                "log_level": "detailed",
                "workflow_timeout": 300
            },
            "output": {
                "log_dir": "tests/evoagent_bench/logs",
                "use_timestamps": True,
                "pretty_json": True,
                "generate_summary": True
            }
        }

    def _get_all_risk_names(self) -> List[str]:
        """Get all 20 risk names

        Returns:
            List of all risk names
        """
        return [
            # L1 (8 risks)
            "jailbreak", "prompt_injection", "sensitive_disclosure",
            "excessive_agency", "code_execution", "hallucination",
            "memory_poisoning", "tool_misuse",
            # L2 (6 risks)
            "message_tampering", "malicious_propagation",
            "misinformation_amplify", "insecure_output",
            "goal_drift", "identity_spoofing",
            # L3 (6 risks)
            "cascading_failures", "sandbox_escape",
            "insufficient_monitoring", "group_hallucination",
            "malicious_emergence", "rogue_agent"
        ]

    def _filter_risks_by_level(self, risk_levels: List[str]) -> List[str]:
        """Filter risks by level (L1, L2, L3)

        Args:
            risk_levels: List of risk levels to include (e.g., ["L2", "L3"])

        Returns:
            List of risk names matching the specified levels
        """
        all_risks = self._get_all_risk_names()

        # Define risk level mappings
        l1_risks = all_risks[0:8]   # First 8 are L1
        l2_risks = all_risks[8:14]  # Next 6 are L2
        l3_risks = all_risks[14:20] # Last 6 are L3

        filtered_risks = []
        for level in risk_levels:
            level_upper = level.upper()
            if level_upper == "L1":
                filtered_risks.extend(l1_risks)
            elif level_upper == "L2":
                filtered_risks.extend(l2_risks)
            elif level_upper == "L3":
                filtered_risks.extend(l3_risks)

        return filtered_risks

    def _get_related_steps(self, execution_trace: List[Dict], step_index: int, context_window: int = 3) -> List[Dict]:
        """Get execution steps around a specific step index

        Args:
            execution_trace: Full execution trace
            step_index: Index of the step where alert was triggered
            context_window: Number of steps before and after to include

        Returns:
            List of related execution steps
        """
        if step_index < 0 or not execution_trace:
            return []

        start_idx = max(0, step_index - context_window)
        end_idx = min(len(execution_trace), step_index + context_window + 1)

        return execution_trace[start_idx:end_idx]

    def _format_pre_test_results(self, pre_test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Format pre-deployment test results for JSON output

        Args:
            pre_test_results: Raw test results from Safety_MAS

        Returns:
            Formatted test results with summary
        """
        # Calculate summary statistics
        total_tests = len(pre_test_results)
        passed_tests = sum(1 for r in pre_test_results.values()
                          if isinstance(r, dict) and r.get("passed", False))
        failed_tests = total_tests - passed_tests

        # Categorize by risk level
        l1_results = {k: v for k, v in pre_test_results.items()
                     if k in ["jailbreak", "prompt_injection", "sensitive_disclosure",
                             "excessive_agency", "code_execution", "hallucination",
                             "memory_poisoning", "tool_misuse"]}

        l2_results = {k: v for k, v in pre_test_results.items()
                     if k in ["message_tampering", "malicious_propagation",
                             "misinformation_amplify", "insecure_output",
                             "goal_drift", "identity_spoofing"]}

        l3_results = {k: v for k, v in pre_test_results.items()
                     if k in ["cascading_failures", "sandbox_escape",
                             "insufficient_monitoring", "group_hallucination",
                             "malicious_emergence", "rogue_agent"]}

        return {
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "use_llm_judge": self.use_llm_judge
            },
            "l1_risks": l1_results,
            "l2_risks": l2_results,
            "l3_risks": l3_results
        }

    def discover_workflows(self, workflow_dir: str, specific_workflows: Optional[List[str]] = None) -> List[Path]:
        """Discover workflow JSON files

        Args:
            workflow_dir: Directory containing workflow files
            specific_workflows: Optional list of specific workflow filenames to test

        Returns:
            List of workflow file paths
        """
        workflow_path = Path(workflow_dir)

        if not workflow_path.exists():
            self.logger.error(f"Workflow directory not found: {workflow_dir}")
            return []

        if specific_workflows:
            # Test only specific workflows
            workflows = [workflow_path / wf for wf in specific_workflows if (workflow_path / wf).exists()]
            self.logger.info(f"Testing specific workflows: {[wf.name for wf in workflows]}")
        else:
            # Discover all JSON files
            workflows = list(workflow_path.glob("*.json"))
            self.logger.info(f"Discovered {len(workflows)} workflows in {workflow_dir}")

        return workflows

    def test_single_workflow(
        self,
        workflow_path: Path,
        enabled_monitors: Optional[List[str]] = None,
        risk_levels: Optional[List[str]] = None
    ) -> WorkflowTestResult:
        """Test a single workflow with pre-deployment tests and runtime monitoring

        Args:
            workflow_path: Path to workflow JSON file
            enabled_monitors: Optional list of monitors to enable
            risk_levels: Optional list of risk levels to test (e.g., ["L2", "L3"])
                        If None, tests all risks

        Returns:
            WorkflowTestResult with comprehensive test data
        """
        workflow_name = workflow_path.stem
        timestamp = datetime.now().isoformat()
        start_time = time.time()

        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"Testing workflow: {workflow_name}")
        self.logger.info(f"{'='*70}")

        try:
            # Step 1: Parse workflow and extract goal
            self.logger.info("Step 1: Parsing workflow...")
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)

            goal = workflow_data.get("workflow", {}).get("goal", "")
            self.logger.info(f"Goal: {goal}")

            # Step 2: Create AG2MAS instance
            self.logger.info("Step 2: Creating AG2MAS instance...")
            mas = create_ag2_mas_from_evoagentx(
                workflow_path=str(workflow_path),
                max_round=5
            )

            # Step 3: Wrap with Safety_MAS
            self.logger.info("Step 3: Wrapping with Safety_MAS...")
            safety_mas = Safety_MAS(mas=mas)

            # Step 4: Run pre-deployment tests
            self.logger.info("Step 4: Running pre-deployment tests...")

            # Determine which risks to test
            if risk_levels:
                all_risks = self._filter_risks_by_level(risk_levels)
                self.logger.info(f"  Testing risk levels: {', '.join(risk_levels)} ({len(all_risks)} risks)")
            else:
                all_risks = self._get_all_risk_names()
                self.logger.info(f"  Testing all risk levels (20 risks)")

            total_risks = len(all_risks)

            pre_test_results = {}
            for idx, risk in enumerate(all_risks, 1):
                try:
                    # Progress indicator
                    progress_pct = (idx / total_risks) * 100
                    self.logger.info(f"  [{idx}/{total_risks}] ({progress_pct:.0f}%) Testing {risk}...")

                    # Define progress callback for test cases
                    def test_case_progress(current, total, status='running'):
                        if status == 'starting':
                            # Print test case starting message
                            print(f"\r    Test case {current}/{total}: Starting (running workflow)...", end='', flush=True)
                        elif status == 'completed':
                            # Print test case completion
                            print(f"\r    Test case {current}/{total}: Completed                      ", end='', flush=True)
                        elif status == 'error':
                            # Print test case error
                            print(f"\r    Test case {current}/{total}: Error                          ", end='', flush=True)

                    result = safety_mas.run_manual_safety_tests([risk], progress_callback=test_case_progress)

                    # Print newline after test cases complete
                    print()  # Move to next line after progress

                    pre_test_results[risk] = result
                except Exception as e:
                    print()  # Ensure newline on error
                    self.logger.error(f"  Error testing {risk}: {str(e)}")
                    pre_test_results[risk] = {
                        "error": str(e),
                        "passed": False
                    }

            # Step 5: Start runtime monitoring
            self.logger.info("Step 5: Starting runtime monitoring...")
            if enabled_monitors is None:
                enabled_monitors = self.config.get("monitoring", {}).get("enabled_monitors", all_risks)

            self.logger.info(f"  Enabled monitors: {len(enabled_monitors)}")

            safety_mas.start_runtime_monitoring(
                mode=MonitorSelectionMode.MANUAL,
                selected_monitors=enabled_monitors
            )

            # Step 6: Execute workflow with detailed tracing
            self.logger.info(f"Step 6: Executing workflow with goal: {goal}")
            self.logger.info(f"  (Max 10 rounds of conversation, monitoring in progress...)")
            execution_trace = []
            message_history = []
            conversation_rounds = 0

            # Capture execution steps via callback
            def capture_step(log_entry):
                """Capture each execution step"""
                nonlocal conversation_rounds

                step_data = {
                    "step": len(execution_trace) + 1,
                    "timestamp": log_entry.timestamp,
                    "agent": log_entry.agent_name,
                    "step_type": log_entry.step_type,
                    "content": str(log_entry.content) if log_entry.content else "",
                    "metadata": log_entry.metadata
                }
                execution_trace.append(step_data)

                # Track conversation rounds (count agent responses)
                if log_entry.step_type == "respond":
                    conversation_rounds += 1
                    # Print directly to console
                    print(f"  >>> Round {conversation_rounds}/10 - Agent: {log_entry.agent_name}")
                    self.logger.info(f"  >>> Round {conversation_rounds}/10 - Agent: {log_entry.agent_name}")

                # Log progress every few steps
                if len(execution_trace) % 5 == 0:
                    self.logger.info(f"  ... {len(execution_trace)} execution steps completed")

                # Also track messages for context
                if log_entry.step_type in ["receive", "respond"]:
                    message_history.append({
                        "agent": log_entry.agent_name,
                        "content": str(log_entry.content),
                        "timestamp": log_entry.timestamp
                    })

            # Register callback if intermediary supports it
            # Note: This may need adjustment based on actual intermediary API
            try:
                if hasattr(safety_mas.intermediary, 'register_step_callback'):
                    safety_mas.intermediary.register_step_callback(capture_step)
            except Exception as e:
                self.logger.warning(f"Could not register step callback: {str(e)}")

            # Execute workflow with max_round limit and timeout
            workflow_exec_start = time.time()
            self.logger.info(f"  🚀 Starting workflow execution...")

            # Print to console directly (bypass logger)
            print(f"\n{'='*70}")
            print(f"WORKFLOW EXECUTION STARTED: {workflow_name}")
            print(f"Goal: {goal}")
            print(f"Max rounds: 10")
            print(f"{'='*70}\n")

            try:
                result = safety_mas.run_task(goal, silent=True, max_round=10)
            except Exception as e:
                print(f"\n{'!'*70}")
                print(f"WORKFLOW EXECUTION ERROR: {str(e)}")
                print(f"{'!'*70}\n")
                raise

            workflow_exec_time = time.time() - workflow_exec_start

            # Print completion to console directly
            print(f"\n{'='*70}")
            print(f"🏁 WORKFLOW EXECUTION COMPLETED: {workflow_name}")
            print(f"{'='*70}")
            print(f"Execution time: {workflow_exec_time:.2f}s")
            print(f"Conversation rounds: {conversation_rounds}")
            print(f"Total execution steps: {len(execution_trace)}")
            print(f"Total messages: {len(message_history)}")
            print(f"{'='*70}\n")

            self.logger.info(f"\n  {'='*60}")
            self.logger.info(f"  🏁 WORKFLOW EXECUTION COMPLETED")
            self.logger.info(f"  {'='*60}")
            self.logger.info(f"  Execution time: {workflow_exec_time:.2f}s")
            self.logger.info(f"  Conversation rounds: {conversation_rounds}/10")
            self.logger.info(f"  Total execution steps: {len(execution_trace)}")
            self.logger.info(f"  Total messages: {len(message_history)}")
            self.logger.info(f"  {'='*60}\n")

            # Step 7: Collect alerts with full context
            self.logger.info("Step 7: Collecting alerts with full context...")
            alerts = safety_mas.get_alerts()

            # Count alerts by severity
            critical_count = sum(1 for a in alerts if a.severity == "critical")
            warning_count = sum(1 for a in alerts if a.severity == "warning")
            info_count = sum(1 for a in alerts if a.severity == "info")

            self.logger.info(f"  Total alerts: {len(alerts)} "
                           f"(Critical: {critical_count}, Warning: {warning_count}, Info: {info_count})")

            # Convert alerts to dictionaries with full context
            alert_dicts = []
            for i, alert in enumerate(alerts):
                # Build comprehensive alert context
                alert_context = {
                    "alert_id": f"alert_{i+1:03d}",
                    "risk_type": alert.risk_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "evidence": alert.evidence if hasattr(alert, 'evidence') else {},
                    "recommended_action": alert.recommended_action,
                    "timestamp": alert.timestamp if hasattr(alert, 'timestamp') else timestamp,

                    # Additional context fields
                    "context": {
                        "agent_name": alert.agent_name if hasattr(alert, 'agent_name') else "unknown",
                        "step_index": alert.step_index if hasattr(alert, 'step_index') else -1,
                        "source_agent": alert.source_agent if hasattr(alert, 'source_agent') else "",
                        "target_agent": alert.target_agent if hasattr(alert, 'target_agent') else "",
                        "source_message": alert.source_message if hasattr(alert, 'source_message') else "",

                        # Include relevant execution steps around this alert
                        "related_steps": self._get_related_steps(
                            execution_trace,
                            alert.step_index if hasattr(alert, 'step_index') else -1
                        ),

                        # Include message history for context
                        "message_history": message_history[-10:] if message_history else []
                    }
                }
                alert_dicts.append(alert_context)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Calculate statistics
            total_messages = len(message_history)
            total_tool_calls = sum(1 for step in execution_trace if step.get("step_type") == "tool_call")

            # Categorize alerts by severity
            alert_summary = {
                "total": len(alert_dicts),
                "critical": sum(1 for a in alert_dicts if a["severity"] == "critical"),
                "warning": sum(1 for a in alert_dicts if a["severity"] == "warning"),
                "info": sum(1 for a in alert_dicts if a["severity"] == "info")
            }

            # Build comprehensive result
            test_result = WorkflowTestResult(
                workflow_name=workflow_name,
                workflow_path=str(workflow_path),
                goal=goal,
                timestamp=timestamp,
                success=True,
                pre_deployment_tests=self._format_pre_test_results(pre_test_results),
                runtime_execution={
                    "workflow_steps": execution_trace,
                    "message_history": message_history,
                    "result": str(result.output) if result and hasattr(result, 'output') else str(result),
                    "success": result.success if result and hasattr(result, 'success') else True
                },
                runtime_alerts=alert_dicts,
                total_messages=total_messages,
                total_tool_calls=total_tool_calls,
                execution_time=execution_time
            )

            # Summary of test results
            pre_summary = test_result.pre_deployment_tests.get("summary", {})
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"✅ Workflow test completed successfully in {execution_time:.2f}s")
            self.logger.info(f"{'='*70}")
            self.logger.info(f"Pre-deployment: {pre_summary.get('passed', 0)}/{pre_summary.get('total', 0)} tests passed")
            self.logger.info(f"Runtime alerts: {len(alert_dicts)} total "
                           f"({critical_count} critical, {warning_count} warning, {info_count} info)")
            self.logger.info(f"{'='*70}\n")

            return test_result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error testing workflow: {str(e)}\n{traceback.format_exc()}"
            self.logger.error(error_msg)

            return WorkflowTestResult(
                workflow_name=workflow_name,
                workflow_path=str(workflow_path),
                goal="",
                timestamp=timestamp,
                success=False,
                error_message=error_msg,
                execution_time=execution_time
            )

    def run_all_tests(
        self,
        workflow_dir: str = "workflow",
        specific_workflows: Optional[List[str]] = None,
        enabled_monitors: Optional[List[str]] = None,
        risk_levels: Optional[List[str]] = None
    ) -> List[WorkflowTestResult]:
        """Run tests for all workflows

        Args:
            workflow_dir: Directory containing workflow files
            specific_workflows: Optional list of specific workflows to test
            enabled_monitors: Optional list of monitors to enable
            risk_levels: Optional list of risk levels to test (e.g., ["L2", "L3"])

        Returns:
            List of WorkflowTestResult objects
        """
        workflows = self.discover_workflows(workflow_dir, specific_workflows)

        if not workflows:
            self.logger.error("No workflows found to test")
            return []

        total_workflows = len(workflows)
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"Starting tests for {total_workflows} workflow(s)")
        if risk_levels:
            self.logger.info(f"Risk levels: {', '.join(risk_levels)}")
        self.logger.info(f"{'='*70}\n")

        results = []

        for idx, workflow_path in enumerate(workflows, 1):
            # Overall progress
            overall_progress = (idx / total_workflows) * 100
            self.logger.info(f"\n{'#'*70}")
            self.logger.info(f"WORKFLOW {idx}/{total_workflows} ({overall_progress:.0f}%): {workflow_path.name}")
            self.logger.info(f"{'#'*70}")

            result = self.test_single_workflow(workflow_path, enabled_monitors, risk_levels)
            results.append(result)

            # Save individual JSON log immediately
            self.save_workflow_log(result)

            # Show completion status
            status_icon = "✅" if result.success else "❌"
            self.logger.info(f"\n{status_icon} Workflow {idx}/{total_workflows} completed in {result.execution_time:.2f}s")

            if not result.success and not self.continue_on_error:
                self.logger.error("Stopping due to error (continue_on_error=False)")
                break

        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"All tests completed: {len(results)}/{total_workflows} workflows tested")
        self.logger.info(f"{'='*70}\n")

        return results

    def save_workflow_log(self, result: WorkflowTestResult):
        """Save individual workflow test result to JSON

        Args:
            result: WorkflowTestResult to save
        """
        if self.use_timestamps:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{result.workflow_name}_{timestamp_str}.json"
        else:
            filename = f"{result.workflow_name}.json"

        filepath = self.log_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            if self.pretty_json:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            else:
                json.dump(result.to_dict(), f, ensure_ascii=False)

        self.logger.info(f"Saved workflow log: {filepath}")

    def generate_summary_report(self, results: List[WorkflowTestResult]):
        """Generate comprehensive markdown summary report

        Args:
            results: List of WorkflowTestResult objects
        """
        if not self.generate_summary:
            return

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"summary_report_{timestamp_str}.md"
        filepath = self.log_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            # Header
            f.write("# EvoAgent Workflow Security Testing Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Executive Summary
            f.write("## Executive Summary\n\n")
            total_workflows = len(results)
            successful = sum(1 for r in results if r.success)
            failed = total_workflows - successful
            total_time = sum(r.execution_time for r in results)

            f.write(f"- **Total Workflows Tested**: {total_workflows}\n")
            f.write(f"- **Successful**: {successful}\n")
            f.write(f"- **Failed**: {failed}\n")
            f.write(f"- **Total Execution Time**: {total_time:.2f}s\n\n")

            # Calculate aggregate statistics
            total_alerts = sum(len(r.runtime_alerts) for r in results if r.success)
            total_critical = sum(sum(1 for a in r.runtime_alerts if a["severity"] == "critical")
                               for r in results if r.success)
            total_warning = sum(sum(1 for a in r.runtime_alerts if a["severity"] == "warning")
                              for r in results if r.success)
            total_info = sum(sum(1 for a in r.runtime_alerts if a["severity"] == "info")
                           for r in results if r.success)

            f.write(f"- **Total Runtime Alerts**: {total_alerts}\n")
            f.write(f"  - Critical: {total_critical}\n")
            f.write(f"  - Warning: {total_warning}\n")
            f.write(f"  - Info: {total_info}\n\n")

            # Workflow Results
            f.write("## Workflow Results\n\n")

            for i, result in enumerate(results, 1):
                status = "✅" if result.success else "❌"
                f.write(f"### {i}. {result.workflow_name} {status}\n\n")
                f.write(f"- **Goal**: {result.goal}\n")
                f.write(f"- **Status**: {'Success' if result.success else 'Failed'}\n")
                f.write(f"- **Execution Time**: {result.execution_time:.2f}s\n")

                if result.success:
                    # Pre-deployment test summary
                    pre_summary = result.pre_deployment_tests.get("summary", {})
                    f.write(f"- **Pre-deployment Tests**: {pre_summary.get('passed', 0)}/{pre_summary.get('total', 0)} passed ")
                    f.write(f"({pre_summary.get('pass_rate', 0):.1f}%)\n")

                    # Runtime monitoring summary
                    alert_count = len(result.runtime_alerts)
                    critical_count = sum(1 for a in result.runtime_alerts if a["severity"] == "critical")
                    warning_count = sum(1 for a in result.runtime_alerts if a["severity"] == "warning")
                    info_count = sum(1 for a in result.runtime_alerts if a["severity"] == "info")

                    f.write(f"- **Runtime Alerts**: {alert_count} ")
                    f.write(f"({critical_count} critical, {warning_count} warning, {info_count} info)\n")

                    # Key risks detected
                    if result.runtime_alerts:
                        f.write(f"\n**Key Risks Detected**:\n")
                        # Group alerts by risk type
                        risk_groups = {}
                        for alert in result.runtime_alerts:
                            risk_type = alert["risk_type"]
                            if risk_type not in risk_groups:
                                risk_groups[risk_type] = []
                            risk_groups[risk_type].append(alert)

                        for risk_type, alerts in sorted(risk_groups.items()):
                            severity_icon = "🔴" if any(a["severity"] == "critical" for a in alerts) else "⚠️"
                            f.write(f"- {severity_icon} {risk_type}: {len(alerts)} alert(s)\n")

                    # Failed pre-deployment tests
                    failed_tests = []
                    for category in ["l1_risks", "l2_risks", "l3_risks"]:
                        risks = result.pre_deployment_tests.get(category, {})
                        for risk_name, risk_result in risks.items():
                            if isinstance(risk_result, dict) and not risk_result.get("passed", True):
                                failed_tests.append(risk_name)

                    if failed_tests:
                        f.write(f"\n**Failed Pre-deployment Tests**:\n")
                        for test in failed_tests:
                            f.write(f"- {test}\n")

                    # Link to detailed log
                    log_filename = f"{result.workflow_name}_{datetime.fromisoformat(result.timestamp).strftime('%Y%m%d_%H%M%S')}.json"
                    f.write(f"\n[📄 Detailed Log]({log_filename})\n")

                else:
                    f.write(f"- **Error**: {result.error_message[:200]}...\n")

                f.write("\n---\n\n")

            # Risk Analysis by Category
            f.write("## Risk Analysis by Category\n\n")

            # Analyze each risk type across all workflows
            all_risk_names = self._get_all_risk_names()

            # L1 Risks
            f.write("### L1 Risks (Single-Agent)\n\n")
            f.write("| Risk | Workflows Affected | Pre-test Pass Rate | Runtime Alerts |\n")
            f.write("|------|-------------------|-------------------|----------------|\n")

            l1_risks = all_risk_names[:8]
            for risk in l1_risks:
                workflows_affected = sum(1 for r in results if r.success and
                                       any(a["risk_type"] == risk for a in r.runtime_alerts))
                total_alerts = sum(sum(1 for a in r.runtime_alerts if a["risk_type"] == risk)
                                 for r in results if r.success)

                # Calculate pre-test pass rate
                passed = sum(1 for r in results if r.success and
                           r.pre_deployment_tests.get("l1_risks", {}).get(risk, {}).get("passed", False))
                total = sum(1 for r in results if r.success)
                pass_rate = (passed / total * 100) if total > 0 else 0

                f.write(f"| {risk} | {workflows_affected}/{total} ({workflows_affected/total*100:.0f}%) | ")
                f.write(f"{pass_rate:.0f}% | {total_alerts} |\n")

            # L2 Risks
            f.write("\n### L2 Risks (Inter-Agent)\n\n")
            f.write("| Risk | Workflows Affected | Pre-test Pass Rate | Runtime Alerts |\n")
            f.write("|------|-------------------|-------------------|----------------|\n")

            l2_risks = all_risk_names[8:14]
            for risk in l2_risks:
                workflows_affected = sum(1 for r in results if r.success and
                                       any(a["risk_type"] == risk for a in r.runtime_alerts))
                total_alerts = sum(sum(1 for a in r.runtime_alerts if a["risk_type"] == risk)
                                 for r in results if r.success)

                passed = sum(1 for r in results if r.success and
                           r.pre_deployment_tests.get("l2_risks", {}).get(risk, {}).get("passed", False))
                total = sum(1 for r in results if r.success)
                pass_rate = (passed / total * 100) if total > 0 else 0

                f.write(f"| {risk} | {workflows_affected}/{total} ({workflows_affected/total*100:.0f}%) | ")
                f.write(f"{pass_rate:.0f}% | {total_alerts} |\n")

            # L3 Risks
            f.write("\n### L3 Risks (System-Level)\n\n")
            f.write("| Risk | Workflows Affected | Pre-test Pass Rate | Runtime Alerts |\n")
            f.write("|------|-------------------|-------------------|----------------|\n")

            l3_risks = all_risk_names[14:]
            for risk in l3_risks:
                workflows_affected = sum(1 for r in results if r.success and
                                       any(a["risk_type"] == risk for a in r.runtime_alerts))
                total_alerts = sum(sum(1 for a in r.runtime_alerts if a["risk_type"] == risk)
                                 for r in results if r.success)

                passed = sum(1 for r in results if r.success and
                           r.pre_deployment_tests.get("l3_risks", {}).get(risk, {}).get("passed", False))
                total = sum(1 for r in results if r.success)
                pass_rate = (passed / total * 100) if total > 0 else 0

                f.write(f"| {risk} | {workflows_affected}/{total} ({workflows_affected/total*100:.0f}%) | ")
                f.write(f"{pass_rate:.0f}% | {total_alerts} |\n")

            # Recommendations
            f.write("\n## Recommendations\n\n")

            # Find most common risks
            risk_counts = {}
            for result in results:
                if result.success:
                    for alert in result.runtime_alerts:
                        risk_type = alert["risk_type"]
                        risk_counts[risk_type] = risk_counts.get(risk_type, 0) + 1

            if risk_counts:
                sorted_risks = sorted(risk_counts.items(), key=lambda x: x[1], reverse=True)

                f.write("### High Priority\n\n")
                for i, (risk, count) in enumerate(sorted_risks[:3], 1):
                    f.write(f"{i}. **{risk}**: Detected {count} times across workflows. ")
                    f.write(f"Review and implement mitigation strategies.\n\n")

                if len(sorted_risks) > 3:
                    f.write("### Medium Priority\n\n")
                    for i, (risk, count) in enumerate(sorted_risks[3:6], 1):
                        f.write(f"{i}. **{risk}**: Detected {count} times. Monitor and address as needed.\n\n")

            # Conclusion
            f.write("## Conclusion\n\n")
            if total_critical > 0:
                f.write(f"The testing identified {total_critical} critical security concerns that require immediate attention. ")
            if total_warning > 0:
                f.write(f"Additionally, {total_warning} warnings were raised that should be reviewed. ")

            f.write("Detailed logs for each workflow are available in the individual JSON files.\n")

        self.logger.info(f"Generated summary report: {filepath}")

    def show_test_plan(self, workflow_dir: str, specific_workflows: Optional[List[str]] = None):
        """Show what would be tested without running (dry run)

        Args:
            workflow_dir: Directory containing workflow files
            specific_workflows: Optional list of specific workflows to test
        """
        workflows = self.discover_workflows(workflow_dir, specific_workflows)

        print("\n" + "="*70)
        print("  DRY RUN - Test Plan")
        print("="*70)
        print(f"\nWorkflows to test: {len(workflows)}")

        for i, workflow_path in enumerate(workflows, 1):
            print(f"\n{i}. {workflow_path.name}")
            print(f"   Path: {workflow_path}")

            try:
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
                goal = workflow_data.get("workflow", {}).get("goal", "N/A")
                print(f"   Goal: {goal}")
            except Exception as e:
                print(f"   Error reading workflow: {str(e)}")

        print(f"\nPre-deployment tests per workflow: 20 risks")
        print(f"Runtime monitors per workflow: {len(self.config.get('monitoring', {}).get('enabled_monitors', []))}")
        print(f"Use LLM judge: {self.use_llm_judge}")
        print(f"Continue on error: {self.continue_on_error}")
        print(f"Output directory: {self.log_dir}")
        print("\n" + "="*70)


# =============================================================================
# CLI
# =============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test EvoAgent workflows with MASSafetyGuard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--workflow-dir",
        default="workflow",
        help="Directory containing workflow JSON files (default: workflow/)"
    )

    parser.add_argument(
        "--workflows",
        nargs="+",
        help="Specific workflow files to test (default: all)"
    )

    parser.add_argument(
        "--output-dir",
        help="Output directory for logs (overrides config)"
    )

    parser.add_argument(
        "--monitors",
        nargs="+",
        help="Specific monitors to enable (default: all 20)"
    )

    parser.add_argument(
        "--risk-levels",
        nargs="+",
        choices=["L1", "L2", "L3", "l1", "l2", "l3"],
        help="Risk levels to test (e.g., L2 L3). Default: all levels"
    )

    parser.add_argument(
        "--no-llm-judge",
        action="store_true",
        help="Use heuristic rules instead of LLM judge (faster)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be tested without running"
    )

    parser.add_argument(
        "--config",
        default="config/evoagent_bench_config.yaml",
        help="Configuration file (default: config/evoagent_bench_config.yaml)"
    )

    args = parser.parse_args()

    # Create runner
    runner = WorkflowTestRunner(args.config)

    # Override config with CLI arguments
    if args.output_dir:
        runner.log_dir = Path(args.output_dir)
        runner.log_dir.mkdir(parents=True, exist_ok=True)

    if args.no_llm_judge:
        runner.use_llm_judge = False

    # Dry run or actual run
    if args.dry_run:
        runner.show_test_plan(args.workflow_dir, args.workflows)
    else:
        print("\n" + "="*70)
        print("  EvoAgent Workflow Security Testing")
        print("="*70)

        results = runner.run_all_tests(
            workflow_dir=args.workflow_dir,
            specific_workflows=args.workflows,
            enabled_monitors=args.monitors,
            risk_levels=args.risk_levels
        )

        # Generate summary report
        runner.generate_summary_report(results)

        print("\n" + "="*70)
        print(f"✅ Testing complete!")
        print(f"Results saved to: {runner.log_dir}")
        print(f"Total workflows tested: {len(results)}")
        print(f"Successful: {sum(1 for r in results if r.success)}")
        print(f"Failed: {sum(1 for r in results if not r.success)}")
        print("="*70 + "\n")


if __name__ == "__main__":
    main()
