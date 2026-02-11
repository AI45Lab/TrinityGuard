"""Deep Research Agent - Direct Implementation (No AG2MAS wrapper)

This script uses DeepResearchAgent directly without AG2MAS wrapper,
since DeepResearchAgent has its own specialized workflow and tools.

For safety testing with MASSafetyGuard, you would wrap this with
Safety_MAS after the agent is created.

Usage:
    python tests/ag2_deepresearch/deep_research_direct.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from autogen.agents.experimental import DeepResearchAgent
    from autogen import LLMConfig
except ImportError:
    try:
        from pyautogen.agents.experimental import DeepResearchAgent
        from pyautogen import LLMConfig
    except ImportError:
        raise ImportError("AG2/AutoGen not installed. Install with: pip install ag2")

from src.utils.llm_config import get_mas_llm_config


def create_deep_research_agent():
    """Create a DeepResearchAgent instance.

    Returns:
        DeepResearchAgent instance
    """
    config = get_mas_llm_config()
    llm_config = config.to_ag2_config()

    # Create DeepResearchAgent
    deep_research_agent = DeepResearchAgent(
        name="DeepResearchAgent",
        llm_config=llm_config,
    )

    return deep_research_agent


def run_deep_research(agent, research_topic: str, max_turns: int = 2):
    """Run deep research using the agent's native run() method.

    Args:
        agent: DeepResearchAgent instance
        research_topic: The topic to research
        max_turns: Maximum number of research turns

    Returns:
        Result from the deep research
    """
    print("=" * 80)
    print("Deep Research Agent - Direct Mode")
    print("=" * 80)
    print()

    print(f"Research Topic: {research_topic}")
    print(f"Max Turns: {max_turns}")
    print()

    print("Starting deep research workflow...")
    print("=" * 80)
    print()

    try:
        # Use the native run() method
        result = agent.run(
            message=research_topic,
            tools=agent.tools,  # Pass the agent's tools
            max_turns=max_turns,
            user_input=False,
            summary_method="reflection_with_llm",
        )

        print()
        print("=" * 80)
        print("#### DEEP RESEARCH RESULT ####")
        print("=" * 80)
        print()

        # Process and display the result
        if hasattr(result, 'process'):
            result.process()
            if hasattr(result, 'summary'):
                print("Summary:")
                print(result.summary)
        else:
            print("Result:", result)

        print()
        print("=" * 80)

        return result

    except Exception as e:
        print(f"\nError during deep research: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function - Equivalent to original code."""
    print("=" * 80)
    print("Deep Research Agent - Direct Implementation")
    print("=" * 80)
    print()
    print("This is equivalent to the original code:")
    print("  agent = DeepResearchAgent(name='DeepResearchAgent', llm_config=llm_config)")
    print("  result = agent.run(message=first_message, tools=agent.tools, ...)")
    print()
    print("=" * 80)
    print()

    # Create the agent
    print("Creating Deep Research Agent...")
    try:
        agent = create_deep_research_agent()
        print("✓ Deep Research Agent created successfully!")

        # Show agent info
        print(f"Agent: {agent.name}")
        if hasattr(agent, 'tools'):
            print(f"Tools: {agent.tools}")
        print()
    except Exception as e:
        print(f"✗ Failed to create agent: {e}")
        import traceback
        traceback.print_exc()
        return

    # Get research topic
    print("=" * 80)
    print("Research Query")
    print("=" * 80)

    try:
        first_message = input("What would you like to research deeply?: ")
    except (EOFError, KeyboardInterrupt):
        first_message = "What are the latest developments in multi-agent system safety?"
        print(f"Using default topic: {first_message}")

    print()

    # Run the deep research
    result = run_deep_research(
        agent=agent,
        research_topic=first_message,
        max_turns=2
    )

    if result:
        print("\n✓ Deep Research Completed!")
    else:
        print("\n✗ Deep Research Failed or Incomplete")


if __name__ == "__main__":
    main()
