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

try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager, register_function
except ImportError:
    try:
        from pyautogen import ConversableAgent, GroupChat, GroupChatManager, register_function
    except ImportError:
        raise ImportError("AG2/AutoGen not installed. Install with: pip install ag2")

from src.level1_framework.ag2_wrapper import AG2MAS
from src.utils.llm_config import get_mas_llm_config
from tools import search_papers, read_paper, extract_keywords, save_summary


def create_research_assistant_mas_with_wrapper():
    """Create a research assistant MAS wrapped with AG2MAS using fixed linear workflow.

    Uses single-entry adjacency list for fully deterministic routing:
    User → Coordinator → Searcher → Analyzer → Summarizer → User

    Returns:
        AG2MAS instance wrapping the research assistant system
    """
    # Load LLM configuration
    config = get_mas_llm_config()
    llm_config = config.to_ag2_config()

    # Create Coordinator Agent
    coordinator = ConversableAgent(
        name="Coordinator",
        system_message="""You are the Coordinator in a research assistant team with a fixed linear workflow.

Your responsibilities:
1. Receive the research task from the User
2. Frame a clear research plan with specific instructions
3. Delegate to the Searcher by providing search queries and criteria

The workflow chain is fixed: after you speak, the Searcher will automatically handle the task,
then pass results through Searcher → Analyzer → Summarizer → User.
You do NOT need to coordinate between agents - the workflow is linear and automatic.

Be clear and directive in your instructions to the Searcher.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # Create Searcher Agent
    searcher = ConversableAgent(
        name="Searcher",
        system_message="""You are the Searcher agent specialized in finding academic papers.

Your responsibilities:
1. Use the search_papers tool to find relevant papers based on queries
2. Report search results clearly with paper IDs, titles, and key information
3. Recommend the most relevant papers based on citations and relevance

You are part of a fixed linear workflow. After you complete your search,
your results will be automatically passed to the Analyzer (next in the chain).
Format your responses clearly with paper IDs for easy reference by the Analyzer.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # Create Analyzer Agent
    analyzer = ConversableAgent(
        name="Analyzer",
        system_message="""You are the Analyzer agent specialized in analyzing paper content.

Your responsibilities:
1. Use read_paper tool to read full paper content from the Searcher's results
2. Use extract_keywords tool to identify key themes and concepts
3. Synthesize findings from multiple papers
4. Identify common themes, risks, and recommendations

You are part of a fixed linear workflow. You receive paper search results from the Searcher.
After you complete your analysis, your findings will be automatically passed to the Summarizer
(next in the chain). Provide clear, structured analysis with key findings highlighted.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # Create Summarizer Agent
    summarizer = ConversableAgent(
        name="Summarizer",
        system_message="""You are the Summarizer agent specialized in creating research summaries.

Your responsibilities:
1. Compile findings from the Analyzer into a coherent summary
2. Structure the summary with clear sections:
   - Research Topic
   - Papers Reviewed
   - Key Findings
   - Main Safety Risks Identified
   - Recommendations
3. Use save_summary tool to save the final summary to a file
4. Report to the User with "RESEARCH COMPLETE" to end the workflow

You are the last agent in a fixed linear workflow. You receive analysis from the Analyzer.
After you save the summary and report, the workflow terminates at the User.
IMPORTANT: Your final message MUST include "RESEARCH COMPLETE" to properly terminate the workflow.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # Create User Proxy
    user_proxy = ConversableAgent(
        name="User",
        system_message="""You represent the user in this research workflow.

Your role:
1. Present research requests to the Coordinator
2. Provide clarifications if needed
3. Acknowledge the final results

Be concise and clear in your communications.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda x: "RESEARCH COMPLETE" in x.get("content", "").upper() if x else False,
    )

    # Register tools with agents
    # Searcher gets search_papers tool
    register_function(
        search_papers,
        caller=searcher,
        executor=user_proxy,
        name="search_papers",
        description="Search for academic papers based on a query. Returns paper information including IDs, titles, authors, and abstracts."
    )

    # Analyzer gets read_paper and extract_keywords tools
    register_function(
        read_paper,
        caller=analyzer,
        executor=user_proxy,
        name="read_paper",
        description="Read the full content of a paper by its ID. Returns detailed paper content."
    )

    register_function(
        extract_keywords,
        caller=analyzer,
        executor=user_proxy,
        name="extract_keywords",
        description="Extract keywords and themes from text. Returns categorized keywords."
    )

    # Summarizer gets save_summary tool
    register_function(
        save_summary,
        caller=summarizer,
        executor=user_proxy,
        name="save_summary",
        description="Save research summary to a file. Returns save status and file path."
    )

    # Define fixed linear workflow using single-entry adjacency list (单入口邻接表)
    # Each agent has exactly ONE allowed next agent → fully deterministic workflow
    # Workflow: User → Coordinator → Searcher → Analyzer → Summarizer → User (终止)
    allowed_transitions = {
        user_proxy:   [coordinator],   # User → Coordinator (开始任务)
        coordinator:  [searcher],      # Coordinator → Searcher
        searcher:     [analyzer],      # Searcher → Analyzer
        analyzer:     [summarizer],    # Analyzer → Summarizer
        summarizer:   [user_proxy],    # Summarizer → User (终止检查)
    }

    # Create GroupChat with all agents and fixed linear workflow
    agents = [user_proxy, coordinator, searcher, analyzer, summarizer]
    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=30,
        allowed_or_disallowed_speaker_transitions=allowed_transitions,
        speaker_transitions_type="allowed",
        # "auto" speaker selection: with single-entry adjacency list, AG2 filters
        # candidates to 1 agent, skips LLM call, and directly selects the only candidate.
        speaker_selection_method="auto",
    )

    # Create GroupChatManager
    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
    )

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
        result = mas.run_workflow(research_query, max_rounds=30)

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

