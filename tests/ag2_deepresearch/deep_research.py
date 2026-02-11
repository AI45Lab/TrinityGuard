"""Deep Research Agent - AG2MAS Format Implementation

This script converts the DeepResearchAgent from AG2's experimental module
into AG2MAS format for safety testing and monitoring.

Original code uses:
    from autogen.agents.experimental import DeepResearchAgent
    from autogen import LLMConfig

Converted to AG2MAS format with:
    - AG2MAS wrapper for unified interface
    - Proper agent configuration
    - Tool registration
    - Workflow execution

Usage:
    python tests/ag2_deepresearch/deep_research.py
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from src.utils.llm_config import get_mas_llm_config

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager, register_function
    from autogen.agents.experimental import DeepResearchAgent
    from autogen import LLMConfig
except ImportError:
    try:
        from pyautogen import ConversableAgent, GroupChat, GroupChatManager, register_function
        from pyautogen.agents.experimental import DeepResearchAgent
        from pyautogen import LLMConfig
    except ImportError:
        raise ImportError("AG2/AutoGen not installed. Install with: pip install ag2")

from src.level1_framework.ag2_wrapper import AG2MAS
from src.utils.llm_config import get_mas_llm_config


def create_deep_research_mas(silent: bool = True):
    """Create a Deep Research MAS wrapped with AG2MAS.

    This function converts the DeepResearchAgent into AG2MAS format
    for compatibility with MASSafetyGuard testing and monitoring.

    Args:
        silent: If True, suppress AG2 native console output

    Returns:
        AG2MAS instance wrapping the deep research system
    """
    config = get_mas_llm_config()
    llm_config = config.to_ag2_config()

    # Create DeepResearchAgent
    deep_research_agent = DeepResearchAgent(
        name="DeepResearchAgent",
        llm_config=llm_config,
    )

    # Create a User Proxy agent to interact with DeepResearchAgent
    user_proxy = ConversableAgent(
        name="User",
        system_message="You are a user requesting deep research on various topics.",
        llm_config=None,  # User proxy doesn't need LLM
        human_input_mode="NEVER",
        is_termination_msg=lambda x: "RESEARCH COMPLETE" in x.get("content", "").upper() if x else False,
        silent=silent,
    )

    # Create a simple two-agent workflow
    # User → DeepResearchAgent → User (terminate)
    agents = [user_proxy, deep_research_agent]

    # Define allowed transitions
    allowed_transitions = {
        user_proxy: [deep_research_agent],
        deep_research_agent: [user_proxy],
    }

    # Create GroupChat
    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=10,
        allowed_or_disallowed_speaker_transitions=allowed_transitions,
        speaker_transitions_type="allowed",
        speaker_selection_method="auto",
    )

    # Create GroupChatManager
    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
        silent=silent,
    )

    # Wrap with AG2MAS - This is the Level 1 wrapper!
    mas = AG2MAS(
        agents=agents,
        group_chat=group_chat,
        manager=manager
    )

    return mas


def run_deep_research(mas: AG2MAS, research_topic: str, max_turns: int = 2):
    """Run deep research using the AG2MAS wrapped system.

    Args:
        mas: AG2MAS instance
        research_topic: The topic to research
        max_turns: Maximum number of research turns

    Returns:
        WorkflowResult containing the research output
    """
    print("=" * 80)
    print("Deep Research Agent - AG2MAS Format")
    print("=" * 80)
    print()

    print(f"Research Topic: {research_topic}")
    print(f"Max Turns: {max_turns}")
    print()

    print("Starting deep research workflow...")
    print("=" * 80)
    print()

    try:
        # Execute workflow using AG2MAS interface
        result = mas.run_workflow(
            task=research_topic,
            max_round=max_turns * 2 + 2  # Account for back-and-forth
        )

        print()
        print("=" * 80)
        print("#### DEEP RESEARCH RESULT ####")
        print("=" * 80)
        print(f"Success: {result.success}")
        print(f"Total messages: {len(result.messages)}")
        print()

        print("Research Output:")
        print("-" * 80)
        print(result.output)
        print("-" * 80)
        print()

        if result.error:
            print(f"Error: {result.error}")
            print()

        return result

    except Exception as e:
        print(f"\nError during deep research: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function - Original code converted to AG2MAS format.

    Original code:
        llm_config = LLMConfig(
            api_type="openai",
            model="gpt-5-nano",
            cache_seed=42,
            temperature=1,
            tools=[],
            timeout=120,
        )

        agent = DeepResearchAgent(
            name="DeepResearchAgent",
            llm_config=llm_config,
        )

        first_message = input("What would you like to research deeply?: ")

        result = agent.run(
            message=first_message,
            tools=agent.tools,
            max_turns=2,
            user_input=False,
            summary_method="reflection_with_llm",
        )

        print("#### DEEP RESEARCH RESULT ####")
        result.process()
        print(result.summary)

    Converted to AG2MAS format for safety testing compatibility.
    """
    print("=" * 80)
    print("Deep Research Agent - AG2MAS Wrapper Implementation")
    print("=" * 80)
    print()

    # Create the MAS with AG2MAS wrapper
    print("Creating Deep Research MAS with AG2MAS wrapper...")
    try:
        mas = create_deep_research_mas(silent=True)
        print("✓ AG2MAS wrapper created successfully!")
        print()
    except Exception as e:
        print(f"✗ Failed to create AG2MAS wrapper: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test the Level 1 interfaces
    print("=" * 80)
    print("Testing Level 1 Interface Methods")
    print("=" * 80)
    print()

    # Get agents
    agents = mas.get_agents()
    print(f"Total agents: {len(agents)}")
    for agent_info in agents:
        print(f"  - {agent_info.name} ({agent_info.role})")
    print()

    # Get topology
    topology = mas.get_topology()
    print("Communication topology:")
    for agent_name, can_talk_to in topology.items():
        print(f"  {agent_name} → {', '.join(can_talk_to)}")
    print()

    # Get research topic from user
    print("=" * 80)
    print("Research Query")
    print("=" * 80)

    # Use a default topic or get from user
    try:
        first_message = input("What would you like to research deeply?: ")
    except (EOFError, KeyboardInterrupt):
        # Default topic if running in non-interactive mode
        first_message = "What are the latest developments in multi-agent system safety?"
        print(f"Using default topic: {first_message}")

    print()

    # Run the deep research
    result = run_deep_research(
        mas=mas,
        research_topic=first_message,
        max_turns=2
    )

    if result and result.success:
        print("=" * 80)
        print("Deep Research Completed Successfully!")
        print("=" * 80)
    else:
        print("=" * 80)
        print("Deep Research Failed or Incomplete")
        print("=" * 80)


if __name__ == "__main__":
    main()
