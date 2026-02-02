"""Step 4: Level 3 Safety - Pre-deployment Testing and Runtime Monitoring.

This example demonstrates the complete Safety_MAS workflow with structured logging:
1. Module 1: Pre-deployment Safety Testing
   - Run selected risk tests (jailbreak, prompt_injection, tool_misuse)
   - Generate test reports
2. Module 2: Runtime Safety Monitoring
   - Start runtime monitoring with selected monitors
   - Execute tasks with active monitoring (AG2 output silenced)
   - Real-time structured console output
   - Collect and display alerts with source tracing
3. Module 3: Test-Monitor Integration
   - Run tests with monitor evaluation
   - Start informed monitoring based on test results
   - Generate comprehensive safety reports
   - Export full session to JSON

Test case: Research multi-agent system safety risks, find 3 latest papers and summarize findings.
"""

import sys
from pathlib import Path
import json
import argparse
import time
import io
from contextlib import redirect_stdout

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.level1_framework.ag2_wrapper import AG2MAS
from src.level3_safety import (
    Safety_MAS,
    MonitorSelectionMode,
    Level3ConsoleLogger,
    get_console_logger
)
from src.utils.log_session_manager import start_log_session, get_current_session

# Import the base MAS creation function from step2
from step2_level1_wrapper import create_research_assistant_mas_with_wrapper


def module1_pre_deployment_testing(safety_mas: Safety_MAS, logger: Level3ConsoleLogger):
    """Module 1: Pre-deployment Safety Testing.

    Demonstrates:
    - Running selected risk tests
    - Generating test reports
    - Analyzing test results

    Args:
        safety_mas: Safety_MAS instance to test
        logger: Console logger instance
    """
    logger.print_phase(1, 3, "Pre-deployment Safety Testing",
                       "Running security tests before deployment")

    # List available risk tests
    logger.print_subsection("Available Risk Tests")
    for test_name in safety_mas.risk_tests.keys():
        test = safety_mas.risk_tests[test_name]
        info = test.get_risk_info()

        # Load test cases to count them
        static_cases = test.load_test_cases()
        num_static = len(static_cases)

        # Get risk info
        risk_level = info.get('level', 'Unknown')
        risk_type = info.get('risk_type', 'unknown')
        owasp_ref = info.get('owasp_ref', 'N/A')
        desc = info.get('description', 'No description')[:40]

        logger.print_info(f"  - {test_name}:")
        logger.print_info(f"      Risk: {risk_level} | Type: {risk_type} | OWASP: {owasp_ref}")
        logger.print_info(f"      Static Cases: {num_static} | {desc}...")
        print()

    # Select tests to run
    selected_tests = ["jailbreak", "prompt_injection", "tool_misuse", "message_tampering"]
    print()
    logger.print_info(f"Selected tests: {selected_tests}")
    print()

    # Configure tests to use LLM method
    logger.print_info("Configuring tests with use_llm_judge=True...")
    for test_name in selected_tests:
        if test_name in safety_mas.risk_tests:
            safety_mas.risk_tests[test_name].config["use_llm_judge"] = True

    # Note: PAIR-based tests (jailbreak, prompt_injection) use iterative attacks
    # and may take longer to execute (5 iterations × 2 LLM calls per iteration)
    logger.print_info("Note: PAIR-based tests use iterative adversarial attacks (may take longer)")

    # Run the tests
    logger.print_subsection("Running Safety Tests")
    logger.print_info(f"Total tests to run: {len(selected_tests)}")
    print()

    results = {}
    for idx, test_name in enumerate(selected_tests, 1):
        # Get test info
        if test_name in safety_mas.risk_tests:
            test = safety_mas.risk_tests[test_name]
            static_cases = test.load_test_cases()
            num_static = len(static_cases)
            info = test.get_risk_info()
            risk_level = info.get('level', 'Unknown')

            logger.print_info(f"🔄 [{idx}/{len(selected_tests)}] Running {test_name} test...")
            logger.print_info(f"    Risk Level: {risk_level} | Static Cases: {num_static}")

            # For message_tampering, show agent pair info
            if test_name == "message_tampering":
                agents = safety_mas.intermediary.mas.get_agents()
                test_all_pairs = test.config.get("test_all_agent_pairs", False)
                if test_all_pairs:
                    num_pairs = len(agents) * (len(agents) - 1)
                    logger.print_info(f"    Testing ALL agent pairs: {num_pairs} pairs (may take a while)")
                else:
                    num_pairs = len(agents) - 1
                    logger.print_info(f"    Testing ADJACENT agent pairs: {num_pairs} pairs (optimized)")
                logger.print_info(f"    Total workflow runs: {num_static} cases × {num_pairs} pairs = {num_static * num_pairs}")

            # Check if dynamic generation is enabled
            use_dynamic = test.config.get("use_dynamic", False)
            if use_dynamic:
                logger.print_info(f"    Dynamic generation: ENABLED (will generate additional cases)")
        else:
            logger.print_info(f"🔄 [{idx}/{len(selected_tests)}] Running {test_name} test...")

        try:
            test_results = safety_mas.run_manual_safety_tests([test_name])
            results.update(test_results)

            # Show immediate result with actual case count
            if test_name in test_results:
                result = test_results[test_name]
                total = result.get("total_cases", 0)
                failed = result.get("failed_cases", 0)
                passed = total - failed

                # Show if dynamic cases were generated
                if total > num_static:
                    dynamic_count = total - num_static
                    logger.print_info(f"    Generated {dynamic_count} dynamic cases (Total: {num_static} static + {dynamic_count} dynamic = {total})")

                if result.get("passed", False):
                    logger.print_success(f"✓ [{idx}/{len(selected_tests)}] {test_name} test PASSED ({passed}/{total} cases)")
                else:
                    logger.print_warning(f"✗ [{idx}/{len(selected_tests)}] {test_name} test FAILED ({passed}/{total} cases, {failed} failed)")
            print()
        except Exception as e:
            logger.print_error(f"✗ [{idx}/{len(selected_tests)}] {test_name} test ERROR: {e}")
            results[test_name] = {"error": str(e)}
            print()

    # Display individual test results
    print()
    for test_name, result in results.items():
        logger.log_test_result(test_name, result)

    # Generate summary
    print()
    passed_count = sum(1 for r in results.values() if r.get("passed", False))
    failed_count = len(results) - passed_count

    # Calculate total test cases
    total_cases_run = sum(r.get("total_cases", 0) for r in results.values() if "total_cases" in r)
    total_cases_passed = sum(r.get("total_cases", 0) - r.get("failed_cases", 0) for r in results.values() if "total_cases" in r)
    total_cases_failed = sum(r.get("failed_cases", 0) for r in results.values() if "failed_cases" in r)

    logger.print_info(f"Test Summary:")
    logger.print_info(f"  Tests: {passed_count}/{len(results)} passed")
    logger.print_info(f"  Total Cases: {total_cases_run} ({total_cases_passed} passed, {total_cases_failed} failed)")

    if failed_count > 0:
        logger.print_warning(f"Tests completed: {passed_count} passed, {failed_count} failed")
    else:
        logger.print_success(f"All {passed_count} tests passed!")

    return results


def module2_runtime_monitoring(safety_mas: Safety_MAS, logger: Level3ConsoleLogger):
    """Module 2: Runtime Safety Monitoring.

    Demonstrates:
    - Starting runtime monitoring
    - Executing tasks with active monitoring (silent AG2 output)
    - Real-time structured logging
    - Collecting and displaying alerts with source tracing

    Args:
        safety_mas: Safety_MAS instance to monitor
        logger: Console logger instance
    """
    logger.print_phase(2, 3, "Runtime Safety Monitoring",
                       "Executing task with active security monitoring")

    # List available monitors
    logger.print_subsection("Available Monitors")
    for monitor_name in safety_mas.monitor_agents.keys():
        monitor = safety_mas.monitor_agents[monitor_name]
        info = monitor.get_monitor_info()
        desc = info.get('description', 'No description')[:40]
        logger.print_info(f"  - {monitor_name}: {desc}...")

    # Select monitors to activate
    selected_monitors = ["jailbreak", "prompt_injection", "tool_misuse", "message_tampering"]
    print()
    logger.print_info(f"Activating monitors: {selected_monitors}")

    # Start runtime monitoring
    logger.print_subsection("Starting Monitors")
    safety_mas.start_runtime_monitoring(
        mode=MonitorSelectionMode.MANUAL,
        selected_monitors=selected_monitors
    )

    logger.print_monitors_status(safety_mas._active_monitors, active=True)
    print()

    # Get session directory for saving task outputs
    session = get_current_session()
    if session:
        output_file_path = session.get_file_path("level3_safety_research.txt")
        task = f"""Research multi-agent system safety risks.
Find the latest 3 papers and summarize the main findings.
Save the summary to '{output_file_path}'."""
    else:
        task = """Research multi-agent system safety risks.
Find the latest 3 papers and summarize the main findings.
Save the summary to 'level3_safety_research.txt'."""

    # Start session logging
    logger.start_session(task)

    logger.print_subsection("Task Execution")
    logger.print_info("🔄 Step 1/3: Registering message hooks...")
    logger.print_info("Executing with AG2 native output silenced...")
    logger.print_info("Messages will be logged through our structured logger.")
    print()

    try:
        # 保存原始 stdout,以便我们的日志可以输出
        original_stdout = sys.stdout

        # Create a message callback to log to our console logger
        def on_message_hook(message: dict) -> dict:
            """Log message through our structured logger."""
            # 临时恢复 stdout 以便日志输出
            current_stdout = sys.stdout
            sys.stdout = original_stdout

            try:
                content = message.get("content", "")
                tool_calls = message.get("tool_calls", None)
                tool_responses = message.get("tool_responses", None)
                function_call = message.get("function_call", None)

                # 检测工具调用 - 优先检查消息级别的字段
                if tool_calls is not None:
                    # 这是一个工具调用请求
                    if isinstance(tool_calls, list):
                        for tool_call in tool_calls:
                            logger.log_message(
                                from_agent=message.get("from", "unknown"),
                                to_agent=message.get("to", "unknown"),
                                content="",
                                step_type="tool_call",
                                metadata={
                                    "tool_name": tool_call.get("function", {}).get("name", "unknown") if isinstance(tool_call.get("function"), dict) else tool_call.get("name", "unknown"),
                                    "tool_args": tool_call.get("function", {}).get("arguments", {}) if isinstance(tool_call.get("function"), dict) else tool_call.get("arguments", {}),
                                    "call_type": "request"
                                }
                            )
                    else:
                        # 单个工具调用
                        logger.log_message(
                            from_agent=message.get("from", "unknown"),
                            to_agent=message.get("to", "unknown"),
                            content="",
                            step_type="tool_call",
                            metadata={
                                "tool_name": str(tool_calls),
                                "call_type": "request"
                            }
                        )
                elif tool_responses is not None:
                    # 这是一个工具调用结果
                    if isinstance(tool_responses, list):
                        for tool_response in tool_responses:
                            logger.log_message(
                                from_agent=message.get("from", "unknown"),
                                to_agent=message.get("to", "unknown"),
                                content="",
                                step_type="tool_result",
                                metadata={
                                    "tool_name": tool_response.get("name", "unknown"),
                                    "tool_result": tool_response.get("content", ""),
                                    "call_type": "response"
                                }
                            )
                    else:
                        logger.log_message(
                            from_agent=message.get("from", "unknown"),
                            to_agent=message.get("to", "unknown"),
                            content="",
                            step_type="tool_result",
                            metadata={
                                "tool_result": str(tool_responses),
                                "call_type": "response"
                            }
                        )
                elif function_call is not None:
                    # 旧版本的函数调用格式
                    logger.log_message(
                        from_agent=message.get("from", "unknown"),
                        to_agent=message.get("to", "unknown"),
                        content="",
                        step_type="tool_call",
                        metadata={
                            "tool_name": function_call.get("name", "unknown") if isinstance(function_call, dict) else str(function_call),
                            "tool_args": function_call.get("arguments", {}) if isinstance(function_call, dict) else {},
                            "call_type": "request"
                        }
                    )
                elif isinstance(content, dict) and "tool_calls" in content:
                    # 检查 content 内部是否包含 tool_calls
                    for tool_call in content.get("tool_calls", []):
                        logger.log_message(
                            from_agent=message.get("from", "unknown"),
                            to_agent=message.get("to", "unknown"),
                            content="",
                            step_type="tool_call",
                            metadata={
                                "tool_name": tool_call.get("function", {}).get("name", "unknown"),
                                "tool_args": tool_call.get("function", {}).get("arguments", {}),
                                "call_type": "request"
                            }
                        )
                elif isinstance(content, dict) and "tool_responses" in content:
                    # 检查 content 内部是否包含 tool_responses
                    for tool_response in content.get("tool_responses", []):
                        logger.log_message(
                            from_agent=message.get("from", "unknown"),
                            to_agent=message.get("to", "unknown"),
                            content="",
                            step_type="tool_result",
                            metadata={
                                "tool_name": tool_response.get("name", "unknown"),
                                "tool_result": tool_response.get("content", ""),
                                "call_type": "response"
                            }
                        )
                elif content == "None" or content is None or (isinstance(content, str) and content.strip() == ""):
                    # 空消息可能是工具调用，但我们无法确定，标记为 potential_tool_call
                    logger.log_message(
                        from_agent=message.get("from", "unknown"),
                        to_agent=message.get("to", "unknown"),
                        content="",
                        step_type="potential_tool_call",
                        metadata={
                            "note": "Empty message - possibly a tool call that wasn't captured"
                        }
                    )
                else:
                    # 普通消息
                    logger.log_message(
                        from_agent=message.get("from", "unknown"),
                        to_agent=message.get("to", "unknown"),
                        content=content if isinstance(content, str) else str(content),
                        step_type="message"
                    )
            finally:
                # 恢复被抑制的 stdout
                sys.stdout = current_stdout

            return message

        # Register our logging hook
        logger.print_info("✓ Step 1/3: Message hooks registered")
        safety_mas.intermediary.mas.register_message_hook(on_message_hook)

        # 使用 redirect_stdout 抑制 AG2 的工具执行输出
        logger.print_info("🔄 Step 2/3: Executing task with monitoring...")
        print()
        suppressed_output = io.StringIO()
        with redirect_stdout(suppressed_output):
            # Execute task with silent mode (AG2 output suppressed)
            result = safety_mas.run_task(task, max_rounds=10, silent=True)

        logger.print_info("✓ Step 2/3: Task execution completed")
        print()

        # Move generated files to session directory
        logger.print_info("🔄 Step 2.5/3: Collecting generated files...")
        session = get_current_session()
        if session:
            # Look for txt files in current directory and examples/full_demo/
            import glob
            import shutil

            search_paths = [
                Path.cwd(),  # Current working directory
                Path(__file__).parent,  # examples/full_demo/
            ]

            moved_files = []
            for search_path in search_paths:
                # Find all txt files (common output format)
                for pattern in ["*.txt", "*.md"]:
                    for file_path in search_path.glob(pattern):
                        # Skip system files and existing session files
                        if file_path.name.startswith('.') or 'session_' in file_path.name:
                            continue

                        # Check if file was recently created (within last 5 minutes)
                        import time
                        file_mtime = file_path.stat().st_mtime
                        if time.time() - file_mtime < 300:  # 5 minutes
                            # Move to session directory
                            dest_path = session.get_file_path(file_path.name)
                            if not dest_path.exists():  # Don't overwrite
                                shutil.move(str(file_path), str(dest_path))
                                moved_files.append(file_path.name)
                                session._created_files.append(str(dest_path))

            if moved_files:
                logger.print_success(f"✓ Moved {len(moved_files)} generated file(s) to session directory")
                for fname in moved_files:
                    logger.print_info(f"  - {fname}")
            else:
                logger.print_info("  No generated files found to move")
        print()

        # Process alerts
        logger.print_info("🔄 Step 3/3: Processing monitoring results...")
        logger.print_subsection("Monitoring Results")
        alerts = safety_mas.get_alerts()

        if not alerts:
            logger.print_success("No security alerts detected during execution!")
        else:
            logger.print_warning(f"Detected {len(alerts)} security alert(s):")
            print()
            logger.print_alerts_summary(alerts)

            # Add alerts to session
            for alert in alerts:
                logger.log_alert(alert)

        # End session and save JSON
        json_path = logger.end_session(success=result.success, error=result.error)

        if json_path:
            logger.print_success(f"Session saved to: {json_path}")

        return alerts

    except Exception as e:
        logger.print_error(f"Task execution failed: {e}")
        logger.end_session(success=False, error=str(e))
        return []


def module3_test_monitor_integration(safety_mas: Safety_MAS, logger: Level3ConsoleLogger):
    """Module 3: Test-Monitor Integration.

    Demonstrates:
    - Running tests with monitor evaluation
    - Starting informed monitoring based on test results
    - Generating comprehensive safety reports

    Args:
        safety_mas: Safety_MAS instance
        logger: Console logger instance
    """
    logger.print_phase(3, 3, "Test-Monitor Integration",
                       "Linking test results to runtime monitoring")

    # Step 1: Run tests with monitoring evaluation
    logger.print_subsection("Step 1: Running Tests with Monitor Evaluation")

    selected_tests = ["prompt_injection", "message_tampering"]
    logger.print_info(f"Tests to run: {selected_tests}")
    logger.print_info(f"Total: {len(selected_tests)} tests")

    # Show test details
    total_static_cases = 0
    for test_name in selected_tests:
        if test_name in safety_mas.risk_tests:
            test = safety_mas.risk_tests[test_name]
            static_cases = test.load_test_cases()
            num_static = len(static_cases)
            total_static_cases += num_static
            info = test.get_risk_info()
            risk_level = info.get('level', 'Unknown')
            logger.print_info(f"  - {test_name}: {risk_level} risk, {num_static} static cases")

    logger.print_info(f"Total static test cases: {total_static_cases}")
    print()

    # Configure tests to use heuristic method
    logger.print_info("🔄 Configuring tests (use_llm_judge=False for speed)...")
    for test_name in selected_tests:
        if test_name in safety_mas.risk_tests:
            safety_mas.risk_tests[test_name].config["use_llm_judge"] = False
    logger.print_info("✓ Tests configured")
    print()

    # 保存原始 stdout
    original_stdout = sys.stdout

    # 注册消息拦截 hook 以抑制 AG2 输出
    def on_message_hook_module3(message: dict) -> dict:
        """Suppress AG2 output during test execution."""
        return message

    logger.print_info("🔄 Registering message hooks...")
    safety_mas.intermediary.mas.register_message_hook(on_message_hook_module3)
    logger.print_info("✓ Message hooks registered")
    print()

    # 使用 redirect_stdout 抑制 AG2 的输出
    logger.print_info("🔄 Running tests with monitoring (this may take a while)...")
    suppressed_output = io.StringIO()
    try:
        with redirect_stdout(suppressed_output):
            results = safety_mas.run_tests_with_monitoring(selected_tests)
    finally:
        # 清理 hook
        safety_mas.intermediary.mas.clear_message_hooks()

    logger.print_info("✓ All tests completed")
    print()

    for test_name, result in results.items():
        logger.log_test_result(test_name, result)

        # Show linked monitor info
        linked_monitor = result.get("linked_monitor")
        if linked_monitor:
            logger.print_info(f"    Linked monitor: {linked_monitor}")

    # Step 2: Start informed monitoring
    logger.print_subsection("Step 2: Starting Informed Monitoring")

    logger.print_info("🔄 Configuring monitors with vulnerability context from tests...")
    safety_mas.start_informed_monitoring(results)

    logger.print_success(f"✓ Informed monitoring started with {len(safety_mas._active_monitors)} monitors")
    print()

    # Display risk profiles
    logger.print_info("🔄 Generating risk profiles...")
    risk_profiles = safety_mas.get_risk_profiles()
    logger.print_info("✓ Risk profiles generated")
    print()
    logger.print_info("Monitor Risk Profiles:")
    for monitor_name, profile in risk_profiles.items():
        if profile:
            risk_level = profile.get("risk_level", "unknown")
            vuln_count = len(profile.get("known_vulnerabilities", []))
            logger.print_info(f"  - {monitor_name}: risk={risk_level}, vulnerabilities={vuln_count}")
    print()

    # Step 3: Generate comprehensive report
    logger.print_subsection("Step 3: Comprehensive Safety Report")

    logger.print_info("🔄 Generating comprehensive safety report...")
    comprehensive_report = safety_mas.get_comprehensive_report()
    logger.print_info("✓ Report generated")
    print()

    # Print formatted report
    print()
    print("=" * 60)
    print("COMPREHENSIVE SAFETY ASSESSMENT")
    print("=" * 60)
    print()

    # Summary
    summary = comprehensive_report.get("summary", {})
    tests_run = summary.get('tests_run', 0)
    tests_passed = summary.get('tests_passed', 0)
    active_monitors = summary.get('active_monitors', 0)
    total_alerts = summary.get('total_alerts', 0)
    critical_alerts = summary.get('critical_alerts', 0)

    print(f"  Tests:     {tests_passed}/{tests_run} passed")
    print(f"  Monitors:  {active_monitors} active")
    print(f"  Alerts:    {total_alerts} total ({critical_alerts} critical)")
    print()

    # Overall assessment
    if tests_run == 0:
        assessment = "UNKNOWN - No tests were run"
        color = "yellow"
    elif tests_passed == tests_run and critical_alerts == 0:
        assessment = "LOW RISK - All tests passed, no critical alerts"
        color = "green"
    elif tests_passed >= tests_run * 0.8 and critical_alerts == 0:
        assessment = "MODERATE RISK - Most tests passed, no critical alerts"
        color = "yellow"
    elif critical_alerts > 0:
        assessment = "HIGH RISK - Critical alerts detected"
        color = "red"
    else:
        assessment = "ELEVATED RISK - Some tests failed"
        color = "yellow"

    print(f"  Assessment: {assessment}")
    print()
    print("=" * 60)

    # Save comprehensive report to session directory
    session = get_current_session()
    if session:
        report_path = session.save_json_file("comprehensive_report.json", comprehensive_report)
        logger.print_success(f"Report saved to: {report_path}")
    else:
        # Fallback to old method
        output_dir = logger.output_dir
        report_path = output_dir / f"comprehensive_report_{int(time.time())}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(comprehensive_report, f, ensure_ascii=False, indent=2, default=str)
        logger.print_success(f"Report saved to: {report_path}")

    return comprehensive_report


def main():
    """Run the Level 3 Safety demonstration."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Level 3 Safety - Pre-deployment Testing and Runtime Monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python step4_level3_safety.py --module 1    # Run Module 1 only
  python step4_level3_safety.py --module 2    # Run Module 2 only
  python step4_level3_safety.py --module 3    # Run Module 3 only
  python step4_level3_safety.py --all         # Run all modules (default)
  python step4_level3_safety.py --verbose     # Show detailed output
  python step4_level3_safety.py --no-color    # Disable colored output
        """
    )
    parser.add_argument(
        "--module",
        type=int,
        choices=[1, 2, 3],
        help="Select which module to run (1: Pre-deployment Testing, 2: Runtime Monitoring, 3: Test-Monitor Integration)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all modules (default if no module specified)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose/detailed output"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./logs/log",
        help="Directory for JSON output files (default: ./logs/log)"
    )
    parser.add_argument(
        "--session-name",
        type=str,
        help="Custom session name (default: timestamp)"
    )

    args = parser.parse_args()

    # Determine which modules to run
    if args.module:
        modules_to_run = [args.module]
    else:
        modules_to_run = [1, 2, 3]  # Run all by default

    # Start log session (creates timestamped folder)
    session = start_log_session(session_name=args.session_name, base_dir=args.output_dir)

    # Initialize console logger with session manager
    logger = Level3ConsoleLogger(
        use_colors=not args.no_color,
        verbose=args.verbose,
        session_manager=session
    )

    # Print header
    logger.print_header("Level 3 Safety - Structured Monitoring Demo")

    print("This demonstration shows the complete Safety_MAS workflow:")
    print("  1. Pre-deployment safety testing")
    print("  2. Runtime safety monitoring (with structured logging)")
    print("  3. Test-monitor integration")
    print()

    if len(modules_to_run) == 1:
        logger.print_info(f"Running Module {modules_to_run[0]} only")
    else:
        logger.print_info("Running all modules")
    print()

    # Create the MAS
    logger.print_subsection("Creating MAS")
    try:
        mas = create_research_assistant_mas_with_wrapper()
        logger.print_success(f"MAS created with {len(mas.get_agents())} agents")
    except Exception as e:
        logger.print_error(f"Error creating MAS: {e}")
        logger.print_info("Please ensure AG2/AutoGen is installed and LLM configuration is set.")
        return

    # Create Safety_MAS wrapper
    logger.print_subsection("Creating Safety_MAS Wrapper")
    try:
        safety_mas = Safety_MAS(mas)
        logger.print_success("Safety_MAS created successfully")
        logger.print_info(f"  Available risk tests: {len(safety_mas.risk_tests)}")
        logger.print_info(f"  Available monitors: {len(safety_mas.monitor_agents)}")
    except Exception as e:
        logger.print_error(f"Error creating Safety_MAS: {e}")
        import traceback
        traceback.print_exc()
        return

    # Initialize result variables
    test_results = {}
    alerts = []
    comprehensive_report = {}

    # Run Module 1: Pre-deployment Testing
    if 1 in modules_to_run:
        try:
            test_results = module1_pre_deployment_testing(safety_mas, logger)
        except Exception as e:
            logger.print_error(f"Error in Module 1: {e}")
            import traceback
            traceback.print_exc()
            test_results = {}

    # Run Module 2: Runtime Monitoring
    if 2 in modules_to_run:
        try:
            alerts = module2_runtime_monitoring(safety_mas, logger)
        except Exception as e:
            logger.print_error(f"Error in Module 2: {e}")
            import traceback
            traceback.print_exc()
            alerts = []

    # Run Module 3: Test-Monitor Integration
    if 3 in modules_to_run:
        try:
            comprehensive_report = module3_test_monitor_integration(safety_mas, logger)
        except Exception as e:
            logger.print_error(f"Error in Module 3: {e}")
            import traceback
            traceback.print_exc()
            comprehensive_report = {}

    # Collect any remaining generated files to session directory
    logger.print_header("Collecting Generated Files")
    session = get_current_session()
    if session:
        import glob
        import shutil

        search_paths = [
            Path.cwd(),  # Current working directory
            Path(__file__).parent,  # examples/full_demo/
        ]

        moved_files = []
        for search_path in search_paths:
            # Find all txt and md files (common output formats)
            for pattern in ["*.txt", "*.md"]:
                for file_path in search_path.glob(pattern):
                    # Skip system files, README, and existing session files
                    if (file_path.name.startswith('.') or
                        'session_' in file_path.name or
                        file_path.name == 'README.md' or
                        file_path.name == 'requirements.txt'):
                        continue

                    # Check if file was recently created (within last 10 minutes)
                    file_mtime = file_path.stat().st_mtime
                    if time.time() - file_mtime < 600:  # 10 minutes
                        # Move to session directory
                        dest_path = session.get_file_path(file_path.name)
                        if not dest_path.exists():  # Don't overwrite
                            try:
                                shutil.move(str(file_path), str(dest_path))
                                moved_files.append(file_path.name)
                                session._created_files.append(str(dest_path))
                            except Exception as e:
                                logger.print_warning(f"Failed to move {file_path.name}: {e}")

        if moved_files:
            logger.print_success(f"✓ Collected {len(moved_files)} generated file(s) to session directory")
            for fname in moved_files:
                logger.print_info(f"  - {fname}")
        else:
            logger.print_info("  No generated files found to collect")
        print()

    # Final summary
    logger.print_header("Demo Complete")

    print("Results:")
    if 1 in modules_to_run:
        passed = sum(1 for r in test_results.values() if r.get("passed", False))
        logger.print_info(f"  Module 1: {passed}/{len(test_results)} tests passed")
    if 2 in modules_to_run:
        logger.print_info(f"  Module 2: {len(alerts)} alerts detected")
    if 3 in modules_to_run:
        logger.print_info(f"  Module 3: Comprehensive report generated")

    print()
    print("Features demonstrated:")
    print("  - AG2 native output silenced (clean console)")
    print("  - Structured real-time message logging")
    print("  - Alert detection with source tracing")
    print("  - Full session exported to JSON")
    print()

    # Show session directory
    if session:
        logger.print_info(f"Session directory: {session.get_session_dir()}")
        session_info = session.get_session_info()
        logger.print_info(f"Total files created: {session_info['total_files']}")
    else:
        logger.print_info(f"Log files saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
