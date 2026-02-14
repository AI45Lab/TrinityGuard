"""Travel Planner MAS Standalone Test Runner

Quickly test the travel planner MAS without the safety framework.

Usage:
    # Run with default parameters
    python run_travel_planner_demo.py

    # Custom trip details
    python run_travel_planner_demo.py --destination "Paris" --days 3
"""

import sys
import os
import argparse
from pathlib import Path

# Set UTF-8 encoding for Windows console (must be set before importing AG2)
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Force UTF-8 for console output
    try:
        import locale
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except (ImportError, AttributeError):
        pass  # Fallback if codecs module doesn't work as expected

# Path setup - SCRIPT_DIR first for local src/, then PROJECT_ROOT
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # TrinityGuard root
script_dir_str = str(SCRIPT_DIR)
project_root_str = str(PROJECT_ROOT)
# Add SCRIPT_DIR first (for local src.travel_planner_mas)
if script_dir_str not in sys.path:
    sys.path.insert(0, script_dir_str)
# Add PROJECT_ROOT second (for src.level1_framework in setup.py)
if project_root_str not in sys.path:
    sys.path.insert(1, project_root_str)


def main():
    # Set UTF-8 encoding for Windows console
    import sys
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(
        description="Travel Planner Agent Team - Standalone Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_travel_planner_demo.py
    python run_travel_planner_demo.py --destination "Paris" --days 3
        """
    )

    # Trip parameters
    parser.add_argument("--destination", "-d", default="Rome",
                        help="Destination city")
    parser.add_argument("--days", "-n", type=int, default=3,
                        help="Number of days")
    parser.add_argument("--budget", type=float, default=5000,
                        help="Budget in USD")
    parser.add_argument("--interests", nargs="+", default=["food", "history"],
                        help="Interests (food, history, etc.)")

    args = parser.parse_args()

    # Banner
    print()
    print("=" * 70)
    print("   Travel Planner Agent Team - Standalone Demo")
    print("=" * 70)
    print()
    print(f"  Destination: {args.destination}")
    print(f"  Days: {args.days}")
    print(f"  Budget: ${args.budget:,.2f}")
    print(f"  Interests: {', '.join(args.interests)}")
    print()
    print("=" * 70)
    print()

    # Import MAS creation function
    try:
        from examples.mas_test.src.travel_planner_mas import create_travel_planner_mas
    except ImportError as e:
        print(f"Error importing travel planner: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Create MAS
    print("[1/2] Creating Travel Planner MAS...")
    # Use absolute path import to avoid namespace conflicts
    import importlib.util
    setup_path = SCRIPT_DIR / "src" / "travel_planner_mas" / "setup.py"
    spec = importlib.util.spec_from_file_location("travel_planner_mas_setup", str(setup_path))
    setup_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup_module)
    create_travel_planner_mas = setup_module.create_travel_planner_mas
    mas = create_travel_planner_mas()

    agents = mas.get_agents()
    print(f"      Created MAS with {len(agents)} agents: {[a.name for a in agents]}")

    # Run workflow
    print("[3/4] Running travel planning workflow...")
    task = (
        f"I want to go to {args.destination} for {args.days} days. "
        f"My interests are {', '.join(args.interests)}. "
        f"My budget is ${args.budget:,.2f}."
    )

    import time as time_module

    # Import AG2 output filter
    try:
        from src.utils.ag2_io_filter import suppress_ag2_tool_output
    except ImportError:
        # Fallback if ag2_io_filter is not available
        from contextlib import nullcontext
        suppress_ag2_tool_output = lambda **kwargs: nullcontext()

    start = time_module.time()

    with suppress_ag2_tool_output(suppress_all=True):
        result = mas.run_workflow(task, silent=True)

    elapsed = time_module.time() - start

    # Print results
    print()
    print("=" * 70)
    print("TRAVEL PLAN RESULT")
    print("=" * 70)
    print()
    # Handle Unicode encoding for Windows console
    if result.output:
        try:
            print(result.output)
        except UnicodeEncodeError:
            # Fallback: encode with errors='replace'
            print(result.output.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
    else:
        print("(No output)")
    print()
    print(f"Completed in {elapsed:.1f} seconds")
    print("=" * 70)
    print()

    # Success/Failure
    if result.success:
        try:
            print("Status: SUCCESS")
        except UnicodeEncodeError:
            print("Status: SUCCESS")
        sys.exit(0)
    else:
        print(f"Status: FAILED - {result.error or 'Unknown error'}")
        sys.exit(1)


if __name__ == "__main__":
    main()
