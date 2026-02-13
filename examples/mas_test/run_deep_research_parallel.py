#!/usr/bin/env python3
"""
Parallel Deep Research Test Runner - Quick test deep_research MAS with 20 concurrent tasks

Usage:
    # Run 20 parallel tasks (faster)
    python run_deep_research_parallel.py
    # Run with custom task count
    python run_deep_research_parallel.py --tasks 10
"""

import sys
import os
from pathlib import Path

# Path setup
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # MASSafetyGuard root

# Add SCRIPT_DIR first for local imports
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Add PROJECT_ROOT second
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Deep Research Agent - Parallel Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_deep_research_parallel.py
    python run_deep_research_parallel.py --tasks 10
        """
    )

    # Task count (default: 20)
    parser.add_argument("--tasks", "-n", type=int, default=20,
                       help="Number of parallel test tasks (default: 20)")

    # Max turns per task (optional, for quick testing)
    parser.add_argument("--turns", "-t", type=int, default=None,
                       help="Max research turns per task (default: from MAS config)")

    args = parser.parse_args()

    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
        except (ImportError, AttributeError):
            pass  # Fallback if codecs module doesn't work

    print()
    print("=" * 70)
    print("   Deep Research Agent - Parallel Test Runner")
    print("=" * 70)
    print()
    print(f"  Tasks: {args.tasks}")
    print(f"  Max turns per task: {args.turns if args.turns else '(from MAS config)'}")
    print()

    # Import deep_research module
    try:
        from src.deep_research_mas import create_deep_research_mas
        mas = create_deep_research_mas()
        agents = mas.get_agents()
        print(f"[1/2] Creating Deep Research MAS...")
        print(f"      Created MAS with {len(agents)} agents: {[a.name for a in agents]}")
    except ImportError as e:
        print(f"[ERROR] Failed to import: {e}")
        sys.exit(1)

    # Import concurrent.futures for parallel execution
    import concurrent.futures

    # Test tasks
    task = "What are the current challenges and opportunities in artificial intelligence development?"

    # Define a single test function
    def run_single_test(test_id, task_str, turns):
        """Run a single deep_research test."""
        try:
            print(f"[{test_id+1:2}/{args.tasks}] Running: {task_str[:60]}...")
            from time import time
            start = time.time()

            # Run MAS workflow
            if args.turns:
                result = mas.run_workflow(task, max_turns=args.turns)
            else:
                result = mas.run_workflow(task)

            elapsed = time.time() - start

            if result.success:
                print(f"[{test_id+1:2}/{args.tasks}] ✓ Completed in {elapsed:.1f}s")
            else:
                print(f"[{test_id+1:2}/{args.tasks}] ✗ Failed: {result.error or 'Unknown error'}")

            return elapsed

        except Exception as e:
            print(f"[{test_id+1:2}/{args.tasks}] ✗ Failed with exception: {str(e)}")
            return 0

    # Run all tests in parallel
    print(f"[2/2] Running {args.tasks} tests in parallel...")

    from time import time
    start_time = time.time()

    # Create thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.tasks) as executor:
        # Submit all test tasks
        future_to_test_id = {executor.submit(run_single_test, i, task, args.turns or 5): i for i in range(args.tasks)}

        # Wait for all to complete (with as_completed for handling Ctrl+C)
        try:
            results = []
            for future in concurrent.futures.as_completed(future_to_test_id.values()):
                test_id = future_to_test_id[future]
                try:
                    elapsed = future.result()
                    results.append((test_id, elapsed, future.exception() if future.exception() else None))
                except concurrent.futures.TimeoutError:
                    results.append((test_id, -1, TimeoutError()))
        except KeyboardInterrupt:
            print("\n[!] Interrupted by user. Partial results...")
            # Cancel pending futures
            for future in future_to_test_id.values():
                if not future.done():
                    future.cancel()

        except Exception as e:
            print(f"[!] Error during parallel execution: {str(e)}")

    total_elapsed = time.time() - start_time

    # Process results
    completed_tests = sum(1 for r in results if r[0] >= 0)
    total_failed = sum(1 for r in results if r[0] < 0)
    total_timeout = sum(1 for r in results if r[0] == -1)

    print()
    print("=" * 70)
    print(f"  Total Time: {total_elapsed:.1f}s")
    print("=" * 70)
    print()

    # Summary by status
    print(f"  Completed: {completed_tests}/{args.tasks}")
    print(f"  Failed: {total_failed}/{args.tasks}")
    print(f" Timeout: {total_timeout}/{args.tasks}")
    print()

    # Success/Fail
    if total_failed == 0 and total_timeout == 0:
        print("Status: SUCCESS - All tests passed!")
        sys.exit(0)
    else:
        print(f"Status: PARTIAL - Some tests failed or timed out")
        sys.exit(1)