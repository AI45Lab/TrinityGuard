#!/usr/bin/env python3
"""
Game Design Agent Team — Standalone Test Runner

Quickly test the game design MAS without the safety framework.
Allows custom game parameters or uses defaults.

Usage:
    # Run with defaults
    python run_game_design_demo.py

    # Custom game concept
    python run_game_design_demo.py --vibe "Cyberpunk city" --type Strategy --goal "Build an empire"

    # Quick mode (shorter output)
    python run_game_design_demo.py --quick
"""

import sys
import argparse
import time
from pathlib import Path

# Path setup — SCRIPT_DIR first so local src/ is found for setup modules
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # TrinityGuard root
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def build_task(args) -> str:
    """Build a task string from CLI arguments."""
    return (
        f"Create a game concept with the following details:\n"
        f"- Background Vibe: {args.vibe}\n"
        f"- Game Type: {args.type}\n"
        f"- Game Goal: {args.goal}\n"
        f"- Target Audience: {args.audience}\n"
        f"- Player Perspective: {args.perspective}\n"
        f"- Multiplayer Support: {args.multiplayer}\n"
        f"- Art Style: {args.art_style}\n"
        f"- Target Platforms: {args.platforms}\n"
        f"- Development Time: {args.dev_time} months\n"
        f"- Budget: ${args.budget:,}\n"
        f"- Core Mechanics: {args.mechanics}\n"
        f"- Mood/Atmosphere: {args.mood}\n"
        f"- Inspiration: {args.inspiration}\n"
        f"- Unique Features: {args.features}\n"
        f"- Detail Level: {'Medium' if args.quick else 'High'}\n\n"
        f"Each agent should contribute their specialized perspective to create "
        f"a comprehensive game design document."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Game Design Agent Team — Standalone Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_game_design_demo.py
    python run_game_design_demo.py --vibe "Sci-fi space opera" --type Action
    python run_game_design_demo.py --quick
        """
    )

    # Game parameters
    parser.add_argument("--vibe", default="Epic fantasy with dragons",
                        help="Background vibe/setting")
    parser.add_argument("--type", default="RPG",
                        choices=["RPG", "Action", "Adventure", "Puzzle",
                                 "Strategy", "Simulation", "Platform", "Horror"],
                        help="Game type")
    parser.add_argument("--goal", default="Save the kingdom from eternal winter",
                        help="Game goal")
    parser.add_argument("--audience", default="Young Adults (18-25)",
                        help="Target audience")
    parser.add_argument("--perspective", default="Third Person",
                        choices=["First Person", "Third Person", "Top Down",
                                 "Side View", "Isometric"],
                        help="Player perspective")
    parser.add_argument("--multiplayer", default="Online Multiplayer",
                        choices=["Single Player Only", "Local Co-op",
                                 "Online Multiplayer", "Both Local and Online"],
                        help="Multiplayer support")
    parser.add_argument("--art-style", default="Stylized",
                        choices=["Realistic", "Cartoon", "Pixel Art", "Stylized",
                                 "Low Poly", "Anime", "Hand-drawn"],
                        help="Art style")
    parser.add_argument("--platforms", default="PC, PlayStation",
                        help="Target platforms (comma-separated)")
    parser.add_argument("--dev-time", type=int, default=12,
                        help="Development time in months")
    parser.add_argument("--budget", type=int, default=10000,
                        help="Budget in USD")
    parser.add_argument("--mechanics", default="Combat, Exploration, Crafting",
                        help="Core mechanics (comma-separated)")
    parser.add_argument("--mood", default="Epic, Mysterious",
                        help="Mood/atmosphere")
    parser.add_argument("--inspiration", default="The Witcher, Skyrim",
                        help="Inspiration games")
    parser.add_argument("--features", default="Dynamic weather system affecting gameplay",
                        help="Unique features")

    # Run options
    parser.add_argument("--quick", action="store_true",
                        help="Request shorter, more concise output")
    parser.add_argument("--silent", action="store_true",
                        help="Suppress AG2 internal output (only show final results)")
    parser.add_argument("--save", type=str, default=None,
                        help="Save output to a markdown file")

    args = parser.parse_args()

    task = build_task(args)

    # Banner
    print()
    print("=" * 70)
    print("   🎮 Game Design Agent Team — Demo Run")
    print("=" * 70)
    print()
    print(f"  Vibe:        {args.vibe}")
    print(f"  Game Type:   {args.type}")
    print(f"  Goal:        {args.goal}")
    print(f"  Audience:    {args.audience}")
    print(f"  Perspective: {args.perspective}")
    print(f"  Art Style:   {args.art_style}")
    print(f"  Platforms:   {args.platforms}")
    print()

    # Create MAS
    print("[1/3] Creating Game Design MAS...")
    from src.game_design_mas.setup import create_game_design_mas
    mas = create_game_design_mas()
    agents = mas.get_agents()
    print(f"      Created {len(agents)} agents: {[a.name for a in agents]}")
    print()

    # Run workflow
    print("[2/3] Running agent collaboration...")
    print("-" * 70)
    start_time = time.time()

    result = mas.run_workflow(task, silent=args.silent)

    elapsed = time.time() - start_time
    print("-" * 70)
    print()

    # Extract results
    print(f"[3/3] Done! ({elapsed:.1f}s)")
    print()

    if result.success:
        # Try to extract individual agent outputs from chat history
        output = result.output or ""

        # Also check message history for richer output
        if hasattr(result, 'metadata') and result.metadata:
            print(f"  Messages exchanged: {result.metadata.get('rounds', 'N/A')}")

        print()
        print("=" * 70)
        print("   📋 Game Design Document")
        print("=" * 70)
        print()

        # If we have the chat result with agent messages, display them
        if result.messages:
            for msg in result.messages:
                content = msg.get("content", "")
                sender = msg.get("from", "unknown")
                if content and content.strip() and sender != "user_proxy":
                    print(f"{'─' * 70}")
                    print(f"  📝 {sender}")
                    print(f"{'─' * 70}")
                    print(content)
                    print()
        elif output:
            print(output)
        else:
            print("No output captured. Try running without --silent.")

        # Save to file if requested
        if args.save:
            save_path = Path(args.save)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"# Game Design Document\n\n")
                f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**Parameters:**\n")
                f.write(f"- Vibe: {args.vibe}\n")
                f.write(f"- Type: {args.type}\n")
                f.write(f"- Goal: {args.goal}\n\n")
                f.write("---\n\n")
                if result.messages:
                    for msg in result.messages:
                        content = msg.get("content", "")
                        sender = msg.get("from", "unknown")
                        if content and content.strip() and sender != "user_proxy":
                            f.write(f"### {sender}\n\n{content}\n\n---\n\n")
                elif output:
                    f.write(output)
            print(f"\n💾 Saved to: {save_path}")

    else:
        print(f"❌ Workflow failed: {result.error}")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
