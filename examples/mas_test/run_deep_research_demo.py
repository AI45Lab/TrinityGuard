#!/usr/bin/env python3
"""
Deep Research Agent — Standalone Test Runner

Quickly test the deep research MAS without the safety framework.
Allows custom research topics or uses defaults.

Usage:
    # Run with default topic
    python run_deep_research_demo.py

    # Custom research topic
    python run_deep_research_demo.py --topic "What are the latest advances in AI?"

    # Adjust research depth
    python run_deep_research_demo.py --turns 3

    # Save output to file
    python run_deep_research_demo.py --save research_output.md
"""

import sys
import argparse
import time
from pathlib import Path

# Path setup — SCRIPT_DIR first so local src/ is found for setup modules
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # MASSafetyGuard root
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def main():
    parser = argparse.ArgumentParser(
        description="Deep Research Agent — Standalone Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_deep_research_demo.py
    python run_deep_research_demo.py --topic "Explain quantum computing"
    python run_deep_research_demo.py --turns 3 --save result.md
        """
    )

    # Research parameters
    parser.add_argument("--topic", "-t",
                        default="What are the current challenges and opportunities in artificial intelligence development?",
                        help="Research topic/question")
    parser.add_argument("--turns", type=int, default=3,
                        help="Maximum research turns (default: 3)")
    parser.add_argument("--summary-method",
                        choices=["reflection_with_llm", "last", "none"],
                        default="reflection_with_llm",
                        help="Summary method for research results")

    # Output options
    parser.add_argument("--save", type=str, default=None,
                        help="Save output to a markdown file")
    parser.add_argument("--silent", action="store_true",
                        help="Suppress native agent output (only show final results)")

    args = parser.parse_args()

    # Banner
    print()
    print("=" * 70)
    print("   🔍 Deep Research Agent — Demo Run")
    print("=" * 70)
    print()
    print(f"  Topic:        {args.topic[:70]}{'...' if len(args.topic) > 70 else ''}")
    print(f"  Max Turns:     {args.turns}")
    print(f"  Summary Method: {args.summary_method}")
    print()

    # Create MAS
    print("[1/3] Creating Deep Research MAS...")
    from src.deep_research_mas.setup import create_deep_research_mas
    mas = create_deep_research_mas()
    agents = mas.get_agents()
    print(f"      Created MAS with {len(agents)} agents: {[a.name for a in agents]}")
    print()

    # Run workflow
    print("[2/3] Running deep research...")
    print("-" * 70)
    start_time = time.time()

    result = mas.run_workflow(
        args.topic,
        max_turns=args.turns,
        summary_method=args.summary_method,
        silent=args.silent,
    )

    elapsed = time.time() - start_time
    print("-" * 70)
    print()

    # Extract results
    print(f"[3/3] Done! ({elapsed:.1f}s)")
    print()

    if result.success:
        print("=" * 70)
        print("   📋 Research Summary")
        print("=" * 70)
        print()

        output = result.output or ""
        print(output)

        # Save to file if requested
        if args.save:
            save_path = Path(args.save)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"# Deep Research Report\n\n")
                f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**Topic:** {args.topic}\n\n")
                f.write(f"**Parameters:**\n")
                f.write(f"- Max Turns: {args.turns}\n")
                f.write(f"- Summary Method: {args.summary_method}\n\n")
                f.write("---\n\n")
                f.write(output)
            print(f"\n💾 Saved to: {save_path}")

        # Print metadata
        if result.metadata:
            print()
            print("=" * 70)
            print("   📊 Metadata")
            print("=" * 70)
            for key, value in result.metadata.items():
                if key != "elapsed":
                    print(f"  {key}: {value}")
            print("=" * 70)

    else:
        print(f"❌ Research failed: {result.error}")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
