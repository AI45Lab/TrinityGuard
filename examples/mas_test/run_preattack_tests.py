#!/usr/bin/env python3
"""
Multi-Agent System Pre-Attack Safety Testing Script

Runs all pre-deployment (事前) safety tests against a selected MAS
and stores results in structured JSON format.

Supported MAS targets:
    - financial:    Financial Analysis MAS
    - game_design:  Game Design Agent Team MAS

Usage:
    # Run all tests on default MAS (financial)
    python run_preattack_tests.py

    # Run all tests on game design MAS
    python run_preattack_tests.py --mas game_design

    # Run specific tests
    python run_preattack_tests.py --mas game_design --tests jailbreak,prompt_injection

    # Run by layer
    python run_preattack_tests.py --mas game_design --layer l1

    # Custom task
    python run_preattack_tests.py --mas financial --task "Analyze TSLA stock performance"

    # Specify output directory
    python run_preattack_tests.py --log-dir ./my_logs
"""

import sys
import os
import json
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone

# =============================================================================
# Path Setup
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # MASSafetyGuard root
# SCRIPT_DIR must be FIRST so local src/ (game_design_mas, financial_mas) is found.
# The setup.py files internally handle importing from PROJECT_ROOT's src/ package.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# =============================================================================
# MAS Registry
# =============================================================================

MAS_REGISTRY = {
    "financial": {
        "display_name": "Financial Analysis MAS",
        "module": "financial_mas.setup",  # Import as top-level package
        "create_func": "create_financial_mas",
        "task_func": "get_default_task",
        "source": "build-with-ag2/financial-analysis",
        "log_subdir": "financial_mas",
    },
    "game_design": {
        "display_name": "Game Design Agent Team MAS",
        "module": "game_design_mas.setup",  # Import as top-level package
        "create_func": "create_game_design_mas",
        "task_func": "get_default_task",
        "source": "build-with-ag2/game-design-agent-team",
        "log_subdir": "game_design_mas",
    },
}

# =============================================================================
# Test Layer Definitions
# =============================================================================

L1_TESTS = [
    "jailbreak",
    "prompt_injection",
    "sensitive_disclosure",
    "excessive_agency",
    "code_execution",
    "hallucination",
    "memory_poisoning",
    "tool_misuse",
]

L2_TESTS = [
    "message_tampering",
    "malicious_propagation",
    "misinformation_amplify",
    "insecure_output",
    "goal_drift",
    "identity_spoofing",
]

L3_TESTS = [
    "cascading_failures",
    "sandbox_escape",
    "insufficient_monitoring",
    "group_hallucination",
    "malicious_emergence",
    "rogue_agent",
]

ALL_TESTS = L1_TESTS + L2_TESTS + L3_TESTS


def get_layer_name(test_name: str) -> str:
    """Get the layer name for a given test."""
    if test_name in L1_TESTS:
        return "L1"
    elif test_name in L2_TESTS:
        return "L2"
    elif test_name in L3_TESTS:
        return "L3"
    return "Unknown"


# =============================================================================
# MAS Loading
# =============================================================================

def load_mas_module(mas_key: str):
    """Dynamically load a MAS setup module from the registry.

    Args:
        mas_key: Key from MAS_REGISTRY (e.g., 'financial', 'game_design')

    Returns:
        Tuple of (create_mas_func, get_default_task_func, mas_info_dict)
    """
    if mas_key not in MAS_REGISTRY:
        available = ", ".join(MAS_REGISTRY.keys())
        raise ValueError(f"Unknown MAS: '{mas_key}'. Available: {available}")

    info = MAS_REGISTRY[mas_key]
    import importlib
    module = importlib.import_module(info["module"])
    create_func = getattr(module, info["create_func"])
    task_func = getattr(module, info["task_func"])

    return create_func, task_func, info


# =============================================================================
# Result Management
# =============================================================================

def save_results(results: dict, log_dir: Path, timestamp: str):
    """Save test results to JSON files.

    Creates two files:
        - preattack_results_<timestamp>.json: Full detailed results
        - preattack_summary_<timestamp>.json: Summary report

    Args:
        results: Full test results dict
        log_dir: Directory to save results
        timestamp: Timestamp string for filename
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    # Save full results
    results_file = log_dir / f"preattack_results_{timestamp}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n📁 Full results saved to: {results_file}")

    # Create and save summary
    summary = create_summary(results)
    summary_file = log_dir / f"preattack_summary_{timestamp}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"📁 Summary saved to: {summary_file}")

    # Also save a latest symlink/copy for easy access
    latest_results = log_dir / "latest_results.json"
    latest_summary = log_dir / "latest_summary.json"
    with open(latest_results, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    with open(latest_summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)


def create_summary(results: dict) -> dict:
    """Create a summary report from full results.

    Args:
        results: Full test results dict

    Returns:
        Summary dict with pass/fail counts and per-layer breakdown
    """
    test_results = results.get("results", {})

    # Count results by layer
    layer_summary = {"L1": {"total": 0, "passed": 0, "failed": 0, "error": 0},
                     "L2": {"total": 0, "passed": 0, "failed": 0, "error": 0},
                     "L3": {"total": 0, "passed": 0, "failed": 0, "error": 0}}

    test_summaries = []

    for test_name, result in test_results.items():
        layer = get_layer_name(test_name)
        layer_summary[layer]["total"] += 1

        if "error" in result and "passed" not in result:
            layer_summary[layer]["error"] += 1
            status = "ERROR"
        elif result.get("passed", False):
            layer_summary[layer]["passed"] += 1
            status = "PASSED"
        else:
            layer_summary[layer]["failed"] += 1
            status = "FAILED"

        test_summaries.append({
            "test_name": test_name,
            "layer": layer,
            "status": status,
            "total_cases": result.get("total_cases", 0),
            "failed_cases": result.get("failed_cases", 0),
            "pass_rate": result.get("pass_rate", 0),
        })

    total_tests = sum(s["total"] for s in layer_summary.values())
    total_passed = sum(s["passed"] for s in layer_summary.values())
    total_failed = sum(s["failed"] for s in layer_summary.values())
    total_error = sum(s["error"] for s in layer_summary.values())

    return {
        "meta": results.get("meta", {}),
        "overall": {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "error": total_error,
            "pass_rate": total_passed / total_tests if total_tests > 0 else 0,
        },
        "by_layer": layer_summary,
        "tests": test_summaries,
    }


# =============================================================================
# Console Output
# =============================================================================

def print_banner(mas_name: str):
    """Print a startup banner."""
    print()
    print("=" * 70)
    print(f"   {mas_name} Pre-Attack Safety Testing")
    print("   MASSafetyGuard Framework")
    print("=" * 70)
    print()


def print_test_report(results: dict):
    """Print a formatted test report to console.

    Args:
        results: Full test results dict
    """
    test_results = results.get("results", {})

    print()
    print("=" * 70)
    print("   Pre-Attack Test Report")
    print("=" * 70)
    print()

    # Group by layer
    for layer_name, layer_tests in [("L1 - Single Agent Risks", L1_TESTS),
                                      ("L2 - Inter-Agent Communication Risks", L2_TESTS),
                                      ("L3 - System-Level Emergent Risks", L3_TESTS)]:
        print(f"  {layer_name}")
        print("  " + "-" * 60)

        for test_name in layer_tests:
            if test_name not in test_results:
                continue

            result = test_results[test_name]

            if "error" in result and "passed" not in result:
                icon = "⚠️ "
                status = f"ERROR: {result['error'][:50]}"
            elif result.get("passed", False):
                icon = "✅"
                total = result.get("total_cases", 0)
                status = f"PASSED ({total} cases)"
            else:
                icon = "❌"
                total = result.get("total_cases", 0)
                failed = result.get("failed_cases", 0)
                pass_rate = result.get("pass_rate", 0) * 100
                status = f"FAILED ({failed}/{total} failed, {pass_rate:.0f}% pass rate)"

            print(f"    {icon} {test_name:<30s} {status}")

        print()

    # Overall summary
    summary = create_summary(results)
    overall = summary["overall"]

    print("  " + "=" * 60)
    print(f"  Overall: {overall['passed']}/{overall['total_tests']} passed, "
          f"{overall['failed']} failed, {overall['error']} errors")
    print(f"  Pass Rate: {overall['pass_rate'] * 100:.1f}%")
    print("  " + "=" * 60)
    print()


# =============================================================================
# Main Test Runner
# =============================================================================

def run_preattack_tests(
    mas_key: str = "financial",
    tests: list = None,
    task: str = None,
    log_dir: Path = None,
    verbose: bool = False,
) -> dict:
    """Run pre-attack safety tests on a selected MAS.

    Args:
        mas_key: MAS identifier from MAS_REGISTRY
        tests: List of test names to run (None = all tests)
        task: Task description for the MAS
        log_dir: Directory for JSON result storage
        verbose: Enable verbose output

    Returns:
        Full results dict
    """
    import importlib
    # Must import from PROJECT_ROOT's src/, not local src/
    project_root_str = str(PROJECT_ROOT)
    inserted_project_root = False
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
        inserted_project_root = True
    elif sys.path[0] != project_root_str:
        # Ensure it's first for this import
        sys.path.insert(0, project_root_str)
        inserted_project_root = True

    _cached_src = sys.modules.pop("src", None)
    _cached_keys = [k for k in sys.modules if k.startswith("src.")]
    _cached_mods = {k: sys.modules.pop(k) for k in _cached_keys}
    try:
        _safety = importlib.import_module("src.level3_safety")
        Safety_MAS = _safety.Safety_MAS
    finally:
        # Restore module cache
        if _cached_src is not None:
            sys.modules["src"] = _cached_src
        sys.modules.update(_cached_mods)
        # Restore sys.path
        if inserted_project_root and sys.path[0] == project_root_str:
            sys.path.pop(0)

    # Load MAS module
    # Ensure SCRIPT_DIR/src is in sys.path so we can import as top-level package and avoid 'src' collision
    local_src = str(SCRIPT_DIR / "src")
    if local_src not in sys.path:
        sys.path.insert(0, local_src)
    
    # Also add SCRIPT_DIR just in case
    script_dir_str = str(SCRIPT_DIR)
    if script_dir_str not in sys.path:
        sys.path.insert(1, script_dir_str)

    create_mas, get_default_task, mas_info = load_mas_module(mas_key)

    # Defaults
    if tests is None:
        tests = ALL_TESTS
    if task is None:
        task = get_default_task()
    if log_dir is None:
        log_dir = SCRIPT_DIR / "logs" / mas_info["log_subdir"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print_banner(mas_info["display_name"])

    # --- Step 1: Create MAS ---
    print(f"[1/4] Creating {mas_info['display_name']}...")
    try:
        from src.utils.ag2_io_filter import suppress_ag2_tool_output
        with suppress_ag2_tool_output(suppress_all=True):
            mas = create_mas()
        agents = mas.get_agents()
        agent_names = [a.name for a in agents]
        print(f"      Created MAS with {len(agents)} agents: {agent_names}")
    except Exception as e:
        print(f"      ❌ Failed to create MAS: {e}")
        return {"error": str(e)}

    # --- Step 2: Wrap with Safety_MAS ---
    print("[2/4] Initializing Safety_MAS wrapper...")
    try:
        safety_mas = Safety_MAS(mas)
        available_tests = list(safety_mas.risk_tests.keys())
        print(f"      Loaded {len(safety_mas.risk_tests)} risk tests")
        print(f"      Loaded {len(safety_mas.monitor_agents)} monitor agents")

        # Validate requested tests
        valid_tests = [t for t in tests if t in available_tests]
        invalid_tests = [t for t in tests if t not in available_tests]

        if invalid_tests:
            print(f"      ⚠️  Skipping unavailable tests: {invalid_tests}")

        if not valid_tests:
            print("      ❌ No valid tests to run!")
            return {"error": "No valid tests to run"}

        print(f"      Will run {len(valid_tests)} tests: {valid_tests}")
    except Exception as e:
        print(f"      ❌ Failed to initialize Safety_MAS: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

    # --- Step 3: Run Tests ---
    print(f"[3/4] Running {len(valid_tests)} pre-attack tests...")
    print(f"      Task: {task[:80]}...")
    print()

    start_time = time.time()

    # Progress tracking
    def progress_callback(current, total, status):
        if status == 'completed':
            print(f"        Case {current}/{total} completed")
        elif status == 'error':
            print(f"        Case {current}/{total} error!")

    test_results = {}
    for i, test_name in enumerate(valid_tests, 1):
        layer = get_layer_name(test_name)
        print(f"  [{i}/{len(valid_tests)}] Running {layer} test: {test_name}...")

        try:
            result = safety_mas.run_manual_safety_tests(
                [test_name],
                task=task,
                progress_callback=progress_callback if verbose else None,
            )
            if test_name in result:
                test_results[test_name] = result[test_name]
                passed = result[test_name].get("passed", False)
                icon = "✅" if passed else "❌"
                total_cases = result[test_name].get("total_cases", 0)
                failed_cases = result[test_name].get("failed_cases", 0)
                print(f"         {icon} {test_name}: {'PASSED' if passed else 'FAILED'} "
                      f"({total_cases} cases, {failed_cases} failed)")
            else:
                test_results[test_name] = result.get(test_name, {"error": "No result returned"})
                print(f"         ⚠️  {test_name}: No result returned")

        except Exception as e:
            test_results[test_name] = {"error": str(e), "status": "crashed"}
            print(f"         ❌ {test_name}: CRASHED - {str(e)[:60]}")
            if verbose:
                import traceback
                traceback.print_exc()

    elapsed = time.time() - start_time

    # --- Step 4: Save Results ---
    print(f"\n[4/4] Saving results (elapsed: {elapsed:.1f}s)...")

    full_results = {
        "meta": {
            "timestamp": datetime.now().isoformat(),
            "mas_name": mas_key,
            "mas_display_name": mas_info["display_name"],
            "mas_source": mas_info["source"],
            "agents": agent_names,
            "task": task,
            "tests_requested": tests,
            "tests_executed": valid_tests,
            "elapsed_seconds": round(elapsed, 2),
        },
        "results": test_results,
    }

    save_results(full_results, log_dir, timestamp)

    # Print report
    print_test_report(full_results)

    return full_results


# =============================================================================
# CLI
# =============================================================================

def parse_args():
    """Parse command line arguments."""
    available_mas = ", ".join(MAS_REGISTRY.keys())

    parser = argparse.ArgumentParser(
        description="Multi-Agent System Pre-Attack Safety Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Supported MAS targets: {available_mas}

Examples:
    python run_preattack_tests.py                                # Run all tests (financial MAS)
    python run_preattack_tests.py --mas game_design              # Run all tests (game design MAS)
    python run_preattack_tests.py --mas game_design --layer l1   # Run L1 tests only
    python run_preattack_tests.py --tests jailbreak              # Run single test
    python run_preattack_tests.py --layer l2 --verbose           # Run L2 with verbose output
    python run_preattack_tests.py --task "Analyze TSLA"          # Custom task
        """
    )

    parser.add_argument(
        "--mas",
        type=str,
        choices=list(MAS_REGISTRY.keys()),
        default="financial",
        help=f"MAS target to test (default: financial). Available: {available_mas}"
    )

    parser.add_argument(
        "--tests",
        type=str,
        default=None,
        help="Comma-separated list of test names (e.g., jailbreak,prompt_injection)"
    )

    parser.add_argument(
        "--layer",
        type=str,
        choices=["l1", "l2", "l3", "all"],
        default="all",
        help="Run tests from specific layer (default: all)"
    )

    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Custom task for the MAS (default: MAS-specific default task)"
    )

    parser.add_argument(
        "--log-dir",
        type=str,
        default=None,
        help="Directory for JSON result storage (default: logs/<mas_name>/)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with per-case progress"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Determine which tests to run
    if args.tests:
        tests = [t.strip() for t in args.tests.split(",")]
    elif args.layer == "l1":
        tests = L1_TESTS
    elif args.layer == "l2":
        tests = L2_TESTS
    elif args.layer == "l3":
        tests = L3_TESTS
    else:
        tests = ALL_TESTS

    # Log directory
    log_dir = Path(args.log_dir) if args.log_dir else None

    # Run tests
    results = run_preattack_tests(
        mas_key=args.mas,
        tests=tests,
        task=args.task,
        log_dir=log_dir,
        verbose=args.verbose,
    )

    # Exit code based on results
    if "error" in results and "results" not in results:
        sys.exit(1)

    test_results = results.get("results", {})
    failed = sum(
        1 for r in test_results.values()
        if not r.get("passed", False) and "error" not in r
    )
    errored = sum(
        1 for r in test_results.values()
        if "error" in r and "passed" not in r
    )

    if failed > 0 or errored > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
