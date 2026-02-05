"""Step 2: Level 1 Wrapper - Using AG2MAS to wrap native AG2 implementation.

This example demonstrates wrapping the research assistant system with Level 1 AG2MAS,
using a fully deterministic linear workflow via single-entry adjacency list:

  User → Coordinator → Searcher → Analyzer → Summarizer → User (terminate)

- Wraps with AG2MAS class for unified interface
- Tests all Level 1 interface methods:
  * get_agents() - Get all agent information
  * get_agent(name) - Get specific agent
  * get_topology() - Get communication topology
  * run_workflow(task) - Execute workflow

Test case: Research multi-agent system safety risks, find 3 latest papers and summarize findings.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.level1_framework.ag2_wrapper import AG2MAS

# Import the base MAS creation function from step1
from step1_native_ag2 import create_research_assistant_mas


def create_research_assistant_mas_with_wrapper():
    """Create a research assistant MAS wrapped with AG2MAS using fixed linear workflow.

    Uses single-entry adjacency list for fully deterministic routing:
    User → Coordinator → Searcher → Analyzer → Summarizer → User

    Returns:
        AG2MAS instance wrapping the research assistant system
    """
    # Reuse the base MAS creation from step1 with silent mode enabled
    agents, group_chat, manager, user_proxy = create_research_assistant_mas(silent=True)

    # Wrap with AG2MAS - This is the Level 1 wrapper!
    mas = AG2MAS(
        agents=agents,
        group_chat=group_chat,
        manager=manager
    )

    return mas


def test_level1_interfaces(mas: AG2MAS):
    """Test all Level 1 interface methods.

    Args:
        mas: AG2MAS instance to test
    """
    print("=" * 80)
    print("Testing Level 1 Interface Methods")
    print("=" * 80)
    print()

    # Test 1: get_agents()
    print("=" * 80)
    print("Test 1: get_agents() - Get all agent information")
    print("=" * 80)
    agents = mas.get_agents()
    print(f"Total agents: {len(agents)}")
    print()
    for i, agent_info in enumerate(agents, 1):
        print(f"Agent {i}: {agent_info.name}")
        print(f"  Role: {agent_info.role}")
        print(f"  Tools: {agent_info.tools if agent_info.tools else 'None'}")
        print(f"  System Prompt (first 100 chars): {agent_info.system_prompt[:100] if agent_info.system_prompt else 'None'}...")
        print()

    # Test 2: get_agent(name)
    print("=" * 80)
    print("Test 2: get_agent(name) - Get specific agent")
    print("=" * 80)
    test_agent_name = "Coordinator"
    print(f"Getting agent: {test_agent_name}")
    try:
        agent = mas.get_agent(test_agent_name)
        print(f"Success! Retrieved agent: {agent.name}")
        print(f"  Type: {type(agent).__name__}")
        print(f"  Has system_message: {hasattr(agent, 'system_message')}")
        print()
    except ValueError as e:
        print(f"Error: {e}")
        print()

    # Test 3: get_topology()
    print("=" * 80)
    print("Test 3: get_topology() - Get communication topology")
    print("=" * 80)
    topology = mas.get_topology()
    print("Communication topology (who can talk to whom):")
    print()
    for agent_name, can_talk_to in topology.items():
        print(f"{agent_name} can communicate with:")
        for target in can_talk_to:
            print(f"  - {target}")
        print()

    print("=" * 80)
    print("Level 1 Interface Tests Completed!")
    print("=" * 80)
    print()


def main():
    """Run the Level 1 wrapper demonstration."""
    print("=" * 80)
    print("Research Assistant System - Level 1 AG2MAS Wrapper")
    print("=" * 80)
    print()

    # Create the MAS with Level 1 wrapper
    print("Creating research assistant system with AG2MAS wrapper...")
    mas = create_research_assistant_mas_with_wrapper()
    print("AG2MAS wrapper created successfully!")
    print()

    # Test all Level 1 interfaces
    test_level1_interfaces(mas)

    # Test 4: run_workflow() - Execute the actual research task
    print("=" * 80)
    print("Test 4: run_workflow(task) - Execute research workflow")
    print("=" * 80)
    print()

    research_query = """研究多智能体系统的安全风险，找出最新的3篇相关论文并总结主要发现。

Please:
1. Search for papers about multi-agent system safety risks
2. Select the top 3 most relevant papers
3. Read and analyze each paper
4. Extract key findings and safety risks
5. Create a comprehensive summary
6. Save the summary to 'mas_safety_research_summary.txt'"""

    print("Research Query:")
    print("-" * 80)
    print(research_query)
    print("-" * 80)
    print()

    print("Starting workflow execution...")
    print("=" * 80)
    print()

    try:
        # Execute workflow using Level 1 interface
        result = mas.run_workflow(research_query, max_round=8)

        print()
        print("=" * 80)
        print("Workflow Execution Result")
        print("=" * 80)
        print(f"Success: {result.success}")
        print(f"Total messages exchanged: {len(result.messages)}")
        print(f"Metadata: {result.metadata}")
        if result.error:
            print(f"Error: {result.error}")
        print()

        print("Final Output:")
        print("-" * 80)
        print(result.output)
        print("-" * 80)
        print()

        print("=" * 80)
        print("Level 1 Wrapper Demonstration Completed!")
        print("=" * 80)

    except Exception as e:
        print(f"\nError during workflow execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

