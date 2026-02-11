"""Deep Research Agent - Single Agent Implementation

This script uses DeepResearchAgent directly without wrapping in GroupChat,
since DeepResearchAgent has its own internal workflow and tools.

Usage:
    python tests/ag2_deepresearch/deep_research_single.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from autogen.agents.experimental import DeepResearchAgent
    from autogen import LLMConfig, UserProxyAgent
except ImportError:
    try:
        from pyautogen.agents.experimental import DeepResearchAgent
        from pyautogen import LLMConfig, UserProxyAgent
    except ImportError:
        raise ImportError("AG2/AutoGen not installed. Install with: pip install ag2")

from src.level1_framework.ag2_wrapper import AG2MAS
from src.utils.llm_config import get_mas_llm_config


def create_deep_research_mas(silent: bool = True):
    """Create a Deep Research Agent wrapped with AG2MAS.

    Note: DeepResearchAgent is a special experimental agent with its own
    internal workflow and tools. We add a UserProxyAgent to satisfy AG2MAS's
    requirement of at least 2 agents.

    Args:
        silent: If True, suppress AG2 native console output

    Returns:
        AG2MAS instance wrapping the deep research agent
    """
    config = get_mas_llm_config()
    llm_config = config.to_ag2_config()

    # Create DeepResearchAgent
    deep_research_agent = DeepResearchAgent(
        name="DeepResearchAgent",
        llm_config=llm_config,
    )

    # Create a UserProxyAgent to satisfy AG2MAS's minimum 2-agent requirement
    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
        code_execution_config=False,
    )

    # Wrap agents with AG2MAS
    mas = AG2MAS(
        agents=[user_proxy, deep_research_agent],
        group_chat=None,
        manager=None
    )

    return mas


def run_deep_research(mas: AG2MAS, research_topic: str, max_turns: int = 2):
    """Run deep research using the native agent.run() method.

    Since DeepResearchAgent has its own specialized run() method,
    we use it directly instead of the generic run_workflow().

    Args:
        mas: AG2MAS instance
        research_topic: The topic to research
        max_turns: Maximum number of research turns

    Returns:
        Result from the deep research
    """
    print("=" * 80)
    print("Deep Research Agent - Single Agent Mode")
    print("=" * 80)
    print()

    print(f"Research Topic: {research_topic}")
    print(f"Max Turns: {max_turns}")
    print()

    print("Starting deep research workflow...")
    print("=" * 80)
    print()

    try:
        # Get the DeepResearchAgent
        deep_research_agent = mas.get_agent("DeepResearchAgent")

        # Use the native run() method with tools
        result = deep_research_agent.run(
            message=research_topic,
            tools=deep_research_agent.tools,  # Pass the agent's tools
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
    """Main function."""
    print("=" * 80)
    print("Deep Research Agent - Single Agent Mode")
    print("=" * 80)
    print()

    # Create the MAS
    print("Creating Deep Research Agent...")
    try:
        mas = create_deep_research_mas(silent=True)
        print("✓ Deep Research Agent created successfully!")
        print()
    except Exception as e:
        print(f"✗ Failed to create agent: {e}")
        import traceback
        traceback.print_exc()
        return

    # Show agent info
    agents = mas.get_agents()
    print(f"Agent: {agents[0].name}")
    if hasattr(agents[0], 'tools'):
        print(f"Tools: {[t for t in agents[0].tools]}")
    print()

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
        mas=mas,
        research_topic=first_message,
        max_turns=2
    )

    if result:
        print("Deep Research Completed!")
    else:
        print("Deep Research Failed or Incomplete")


if __name__ == "__main__":
    main()
