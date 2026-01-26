"""MASSafetyGuard Full Demo - Complete Workflow Demonstration.

This script runs the complete MASSafetyGuard demonstration workflow:
- Step 1: AG2 Native MAS - Research assistant system with 4 agents and 4 tools
- Step 2: Level 1 Wrapper - AG2MAS unified interface testing
- Step 3: Level 2 Intermediary - Scaffolding interfaces for runtime manipulation
- Step 4: Level 3 Safety - Pre-deployment testing and runtime monitoring

Usage:
    python run_full_demo.py              # Run all steps
    python run_full_demo.py --all        # Run all steps (explicit)
    python run_full_demo.py --step 1     # Run only step 1
    python run_full_demo.py --step 2     # Run only step 2
    python run_full_demo.py --step 3     # Run only step 3
    python run_full_demo.py --step 4     # Run only step 4
    python run_full_demo.py --verbose    # Run with verbose output
    python run_full_demo.py --step 1 --step 2  # Run steps 1 and 2
"""

import sys
import argparse
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# Output Formatting Utilities
# ============================================================================

def print_banner(title: str, width: int = 80):
    """Print a prominent banner with title."""
    print()
    print("=" * width)
    print(title.center(width))
    print("=" * width)
    print()


def print_section(title: str, width: int = 80):
    """Print a section header."""
    print()
    print("-" * width)
    print(title)
    print("-" * width)
    print()


def print_step_header(step_num: int, title: str, width: int = 80):
    """Print a step header with step number."""
    print()
    print("=" * width)
    print(f"Step {step_num}: {title}")
    print("=" * width)
    print()


def print_step_result(success: bool, message: str = ""):
    """Print step completion status."""
    if success:
        print(f"[OK] {message}" if message else "[OK] Completed")
    else:
        print(f"[FAILED] {message}" if message else "[FAILED] Step failed")


def print_verbose(message: str, verbose: bool):
    """Print message only in verbose mode."""
    if verbose:
        print(f"  [VERBOSE] {message}")


# ============================================================================
# Step Execution Functions
# ============================================================================

def run_step1(verbose: bool = False) -> Dict[str, Any]:
    """Run Step 1: AG2 Native MAS.

    Creates and runs a native AG2 research assistant system with:
    - 4 agents: Coordinator, Searcher, Analyzer, Summarizer
    - 4 tools: search_papers, read_paper, extract_keywords, save_summary

    Args:
        verbose: Enable verbose output

    Returns:
        Dict with step results including success status and details
    """
    result = {
        "step": 1,
        "name": "AG2 Native MAS",
        "success": False,
        "start_time": time.time(),
        "details": {},
        "error": None
    }

    try:
        print_verbose("Importing step1_native_ag2 module...", verbose)
        from step1_native_ag2 import create_research_assistant_mas

        print("Creating research assistant MAS...")
        agents, group_chat, manager, user_proxy = create_research_assistant_mas()

        result["details"]["agents_created"] = len(agents)
        result["details"]["agent_names"] = [agent.name for agent in agents]

        print(f"Created {len(agents)} agents: {result['details']['agent_names']}")
        print()

        # Test case
        research_query = """Research multi-agent system safety risks.
Find the top 3 relevant papers and summarize the main findings.
Save the summary to 'step1_research_summary.txt'."""

        print("Research Query:")
        print("-" * 60)
        print(research_query)
        print("-" * 60)
        print()

        print("Starting research workflow...")
        print_verbose("Initiating chat with GroupChatManager...", verbose)

        user_proxy.initiate_chat(
            manager,
            message=research_query,
            clear_history=True
        )

        result["details"]["workflow_completed"] = True
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        result["details"]["traceback"] = traceback.format_exc()
        print(f"Error: {e}")
        if verbose:
            traceback.print_exc()

    result["end_time"] = time.time()
    result["duration"] = result["end_time"] - result["start_time"]

    return result


def run_step2(verbose: bool = False) -> Dict[str, Any]:
    """Run Step 2: Level 1 Wrapper.

    Tests the AG2MAS wrapper interface:
    - get_agents() - Get all agent information
    - get_agent(name) - Get specific agent
    - get_topology() - Get communication topology
    - run_workflow(task) - Execute workflow

    Args:
        verbose: Enable verbose output

    Returns:
        Dict with step results including success status and details
    """
    result = {
        "step": 2,
        "name": "Level 1 Wrapper (AG2MAS)",
        "success": False,
        "start_time": time.time(),
        "details": {},
        "error": None
    }

    try:
        print_verbose("Importing step2_level1_wrapper module...", verbose)
        from step2_level1_wrapper import create_research_assistant_mas_with_wrapper, test_level1_interfaces

        print("Creating research assistant MAS with AG2MAS wrapper...")
        mas = create_research_assistant_mas_with_wrapper()
        print("AG2MAS wrapper created successfully!")
        print()

        # Test Level 1 interfaces
        print_verbose("Testing Level 1 interface methods...", verbose)
        test_level1_interfaces(mas)

        result["details"]["interfaces_tested"] = [
            "get_agents()",
            "get_agent(name)",
            "get_topology()"
        ]

        # Test run_workflow
        print_section("Testing run_workflow()")

        research_query = """Research multi-agent system safety risks.
Find the top 3 relevant papers and summarize the main findings.
Save the summary to 'step2_research_summary.txt'."""

        print("Research Query:")
        print("-" * 60)
        print(research_query)
        print("-" * 60)
        print()

        print("Executing workflow via AG2MAS interface...")
        workflow_result = mas.run_workflow(research_query, max_rounds=30)

        result["details"]["workflow_success"] = workflow_result.success
        result["details"]["messages_exchanged"] = len(workflow_result.messages)
        result["details"]["interfaces_tested"].append("run_workflow()")

        print()
        print(f"Workflow Success: {workflow_result.success}")
        print(f"Messages Exchanged: {len(workflow_result.messages)}")

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        result["details"]["traceback"] = traceback.format_exc()
        print(f"Error: {e}")
        if verbose:
            traceback.print_exc()

    result["end_time"] = time.time()
    result["duration"] = result["end_time"] - result["start_time"]

    return result


def run_step3(verbose: bool = False) -> Dict[str, Any]:
    """Run Step 3: Level 2 Intermediary.

    Tests the AG2Intermediary scaffolding interfaces:
    - agent_chat() - Direct point-to-point chat
    - simulate_agent_message() - Simulate inter-agent messages
    - inject_tool_call() - Inject tool calls (mock and real)
    - inject_memory() - Inject memory/context
    - broadcast_message() - Broadcast to multiple agents
    - spoof_identity() - Test identity spoofing
    - get_resource_usage() - Get resource statistics

    Args:
        verbose: Enable verbose output

    Returns:
        Dict with step results including success status and details
    """
    result = {
        "step": 3,
        "name": "Level 2 Intermediary (AG2Intermediary)",
        "success": False,
        "start_time": time.time(),
        "details": {},
        "error": None
    }

    try:
        print_verbose("Importing step3_level2_intermediary module...", verbose)
        from step3_level2_intermediary import (
            create_research_assistant_mas,
            test_agent_chat,
            test_simulate_agent_message,
            test_inject_tool_call,
            test_inject_memory,
            test_broadcast_message,
            test_spoof_identity,
            test_get_resource_usage
        )
        from src.level2_intermediary.ag2_intermediary import AG2Intermediary

        print("Creating research assistant MAS...")
        mas = create_research_assistant_mas()
        print("AG2MAS created successfully!")
        print()

        print("Creating AG2Intermediary instance...")
        intermediary = AG2Intermediary(mas)
        print("AG2Intermediary created successfully!")
        print()

        # Run all scaffolding interface tests
        interfaces_tested = []

        print_verbose("Running scaffolding interface tests...", verbose)

        # Test 1: agent_chat
        test_agent_chat(intermediary)
        interfaces_tested.append("agent_chat()")

        # Test 2: simulate_agent_message
        test_simulate_agent_message(intermediary)
        interfaces_tested.append("simulate_agent_message()")

        # Test 3: inject_tool_call
        test_inject_tool_call(intermediary)
        interfaces_tested.append("inject_tool_call()")

        # Test 4: inject_memory
        test_inject_memory(intermediary)
        interfaces_tested.append("inject_memory()")

        # Test 5: broadcast_message
        test_broadcast_message(intermediary)
        interfaces_tested.append("broadcast_message()")

        # Test 6: spoof_identity
        test_spoof_identity(intermediary)
        interfaces_tested.append("spoof_identity()")

        # Test 7: get_resource_usage
        test_get_resource_usage(intermediary)
        interfaces_tested.append("get_resource_usage()")

        result["details"]["interfaces_tested"] = interfaces_tested
        result["details"]["total_interfaces"] = len(interfaces_tested)
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        result["details"]["traceback"] = traceback.format_exc()
        print(f"Error: {e}")
        if verbose:
            traceback.print_exc()

    result["end_time"] = time.time()
    result["duration"] = result["end_time"] - result["start_time"]

    return result


def run_step4(verbose: bool = False) -> Dict[str, Any]:
    """Run Step 4: Level 3 Safety.

    Tests the Safety_MAS framework:
    - Module 1: Pre-deployment safety testing
    - Module 2: Runtime safety monitoring
    - Module 3: Test-monitor integration

    Args:
        verbose: Enable verbose output

    Returns:
        Dict with step results including success status and details
    """
    result = {
        "step": 4,
        "name": "Level 3 Safety (Safety_MAS)",
        "success": False,
        "start_time": time.time(),
        "details": {},
        "error": None
    }

    try:
        print_verbose("Importing step4_level3_safety module...", verbose)
        from step4_level3_safety import (
            create_research_assistant_mas,
            module1_pre_deployment_testing,
            module2_runtime_monitoring,
            module3_test_monitor_integration
        )
        from src.level3_safety import Safety_MAS

        print("Creating research assistant MAS...")
        mas = create_research_assistant_mas()
        print(f"MAS created with {len(mas.get_agents())} agents")
        print()

        print("Creating Safety_MAS wrapper...")
        safety_mas = Safety_MAS(mas)
        print(f"Safety_MAS created successfully")
        print(f"  Available risk tests: {len(safety_mas.risk_tests)}")
        print(f"  Available monitors: {len(safety_mas.monitor_agents)}")
        print()

        result["details"]["risk_tests_available"] = len(safety_mas.risk_tests)
        result["details"]["monitors_available"] = len(safety_mas.monitor_agents)

        modules_completed = []

        # Module 1: Pre-deployment Testing
        print_verbose("Running Module 1: Pre-deployment Testing...", verbose)
        try:
            test_results = module1_pre_deployment_testing(safety_mas)
            result["details"]["module1_tests_run"] = len(test_results)
            modules_completed.append("Module 1: Pre-deployment Testing")
        except Exception as e:
            print(f"Module 1 error: {e}")
            result["details"]["module1_error"] = str(e)

        # Module 2: Runtime Monitoring
        print_verbose("Running Module 2: Runtime Monitoring...", verbose)
        try:
            alerts = module2_runtime_monitoring(safety_mas)
            result["details"]["module2_alerts"] = len(alerts)
            modules_completed.append("Module 2: Runtime Monitoring")
        except Exception as e:
            print(f"Module 2 error: {e}")
            result["details"]["module2_error"] = str(e)

        # Module 3: Test-Monitor Integration
        print_verbose("Running Module 3: Test-Monitor Integration...", verbose)
        try:
            comprehensive_report = module3_test_monitor_integration(safety_mas)
            result["details"]["module3_report_generated"] = bool(comprehensive_report)
            modules_completed.append("Module 3: Test-Monitor Integration")
        except Exception as e:
            print(f"Module 3 error: {e}")
            result["details"]["module3_error"] = str(e)

        result["details"]["modules_completed"] = modules_completed
        result["success"] = len(modules_completed) > 0

    except Exception as e:
        result["error"] = str(e)
        result["details"]["traceback"] = traceback.format_exc()
        print(f"Error: {e}")
        if verbose:
            traceback.print_exc()

    result["end_time"] = time.time()
    result["duration"] = result["end_time"] - result["start_time"]

    return result


# ============================================================================
# Report Generation
# ============================================================================

def generate_final_report(results: List[Dict[str, Any]], total_duration: float) -> str:
    """Generate a comprehensive final test report.

    Args:
        results: List of step results
        total_duration: Total execution time in seconds

    Returns:
        Formatted report string
    """
    report_lines = []

    # Header
    report_lines.append("=" * 80)
    report_lines.append("MASSafetyGuard Full Demo - Final Test Report".center(80))
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Total Execution Time: {total_duration:.2f} seconds")
    report_lines.append("")

    # Summary
    report_lines.append("-" * 80)
    report_lines.append("SUMMARY")
    report_lines.append("-" * 80)

    total_steps = len(results)
    successful_steps = sum(1 for r in results if r["success"])
    failed_steps = total_steps - successful_steps

    report_lines.append(f"Total Steps Executed: {total_steps}")
    report_lines.append(f"Successful Steps: {successful_steps}")
    report_lines.append(f"Failed Steps: {failed_steps}")
    report_lines.append(f"Success Rate: {(successful_steps/total_steps*100) if total_steps > 0 else 0:.1f}%")
    report_lines.append("")

    # Step Details
    report_lines.append("-" * 80)
    report_lines.append("STEP DETAILS")
    report_lines.append("-" * 80)

    for result in results:
        step_num = result["step"]
        step_name = result["name"]
        success = result["success"]
        duration = result.get("duration", 0)
        status = "[OK]" if success else "[FAILED]"

        report_lines.append("")
        report_lines.append(f"Step {step_num}: {step_name}")
        report_lines.append(f"  Status: {status}")
        report_lines.append(f"  Duration: {duration:.2f} seconds")

        # Add step-specific details
        details = result.get("details", {})
        if details:
            report_lines.append("  Details:")
            for key, value in details.items():
                if key != "traceback":  # Skip traceback in summary
                    if isinstance(value, list):
                        report_lines.append(f"    {key}: {', '.join(str(v) for v in value)}")
                    else:
                        report_lines.append(f"    {key}: {value}")

        if result.get("error"):
            report_lines.append(f"  Error: {result['error']}")

    # Verification Checklist
    report_lines.append("")
    report_lines.append("-" * 80)
    report_lines.append("VERIFICATION CHECKLIST")
    report_lines.append("-" * 80)

    checklist_items = [
        ("Step 1: AG2 Native MAS", "4 agents created and workflow executed"),
        ("Step 2: Level 1 Wrapper", "AG2MAS interface methods tested"),
        ("Step 3: Level 2 Intermediary", "7 scaffolding interfaces tested"),
        ("Step 4: Level 3 Safety", "Pre-deployment testing and runtime monitoring")
    ]

    for i, (step_name, description) in enumerate(checklist_items, 1):
        step_result = next((r for r in results if r["step"] == i), None)
        if step_result:
            status = "[OK]" if step_result["success"] else "[FAILED]"
        else:
            status = "[SKIPPED]"
        report_lines.append(f"  {status} {step_name}: {description}")

    # Overall Assessment
    report_lines.append("")
    report_lines.append("-" * 80)
    report_lines.append("OVERALL ASSESSMENT")
    report_lines.append("-" * 80)

    if successful_steps == total_steps:
        assessment = "ALL TESTS PASSED - MASSafetyGuard demonstration completed successfully"
    elif successful_steps >= total_steps * 0.75:
        assessment = "MOSTLY PASSED - Most steps completed successfully with some issues"
    elif successful_steps >= total_steps * 0.5:
        assessment = "PARTIAL SUCCESS - Some steps completed, review failed steps"
    else:
        assessment = "NEEDS ATTENTION - Multiple steps failed, review errors"

    report_lines.append(f"  {assessment}")
    report_lines.append("")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)


# ============================================================================
# Main Entry Point
# ============================================================================

def parse_arguments():
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="MASSafetyGuard Full Demo - Complete Workflow Demonstration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_full_demo.py              # Run all steps
    python run_full_demo.py --all        # Run all steps (explicit)
    python run_full_demo.py --step 1     # Run only step 1
    python run_full_demo.py --step 2     # Run only step 2
    python run_full_demo.py --step 3     # Run only step 3
    python run_full_demo.py --step 4     # Run only step 4
    python run_full_demo.py --step 1 --step 2  # Run steps 1 and 2
    python run_full_demo.py --verbose    # Run with verbose output
        """
    )

    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3, 4],
        action="append",
        dest="steps",
        help="Run specific step(s). Can be specified multiple times."
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all steps (default behavior)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output mode"
    )

    return parser.parse_args()


def main():
    """Main entry point for the full demo."""
    args = parse_arguments()

    # Determine which steps to run
    if args.steps:
        steps_to_run = sorted(set(args.steps))
    else:
        # Default: run all steps
        steps_to_run = [1, 2, 3, 4]

    verbose = args.verbose

    # Print banner
    print_banner("MASSafetyGuard Full Demo")

    print("This demonstration showcases the complete MASSafetyGuard workflow:")
    print("  Step 1: AG2 Native MAS - Research assistant with 4 agents and 4 tools")
    print("  Step 2: Level 1 Wrapper - AG2MAS unified interface")
    print("  Step 3: Level 2 Intermediary - Scaffolding interfaces")
    print("  Step 4: Level 3 Safety - Pre-deployment testing and runtime monitoring")
    print()
    print(f"Steps to run: {steps_to_run}")
    print(f"Verbose mode: {'Enabled' if verbose else 'Disabled'}")
    print()

    # Track results
    results = []
    total_start_time = time.time()

    # Step execution mapping
    step_functions = {
        1: ("AG2 Native MAS", run_step1),
        2: ("Level 1 Wrapper (AG2MAS)", run_step2),
        3: ("Level 2 Intermediary (AG2Intermediary)", run_step3),
        4: ("Level 3 Safety (Safety_MAS)", run_step4)
    }

    # Execute selected steps
    for step_num in steps_to_run:
        step_name, step_func = step_functions[step_num]

        print_step_header(step_num, step_name)

        try:
            result = step_func(verbose=verbose)
            results.append(result)

            print()
            print_step_result(result["success"], f"Step {step_num} completed in {result['duration']:.2f}s")

        except Exception as e:
            error_result = {
                "step": step_num,
                "name": step_name,
                "success": False,
                "error": str(e),
                "duration": 0,
                "details": {"traceback": traceback.format_exc()}
            }
            results.append(error_result)
            print_step_result(False, f"Step {step_num} failed: {e}")
            if verbose:
                traceback.print_exc()

    # Calculate total duration
    total_duration = time.time() - total_start_time

    # Generate and print final report
    print()
    report = generate_final_report(results, total_duration)
    print(report)

    # Return exit code based on results
    all_success = all(r["success"] for r in results)
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
