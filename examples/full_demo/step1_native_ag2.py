"""Step 1: Native AG2 Research Assistant System with Tool Calling.

This example demonstrates a 4-agent research assistant system:
- Coordinator: Orchestrates the research workflow
- Searcher: Searches for academic papers using search_papers tool
- Analyzer: Analyzes papers using read_paper and extract_keywords tools
- Summarizer: Summarizes findings using save_summary tool

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

from src.utils.llm_config import get_mas_llm_config
from tools import search_papers, read_paper, extract_keywords, save_summary


def create_research_assistant_mas():
    """Create a research assistant MAS with 4 agents and 4 tools.

    Returns:
        Tuple of (agents, group_chat, manager)
    """
    # Load LLM configuration
    config = get_mas_llm_config()
    llm_config = config.to_ag2_config()

    # Create Coordinator Agent
    coordinator = ConversableAgent(
        name="Coordinator",
        system_message="""You are the Coordinator in a research assistant team.

Your responsibilities:
1. Receive research requests from users
2. Break down the research task into clear steps
3. Delegate tasks to specialist agents:
   - Searcher: for finding papers
   - Analyzer: for reading and analyzing papers
   - Summarizer: for creating final summaries
4. Monitor progress and ensure all steps are completed
5. Present the final result to the user

When the research is complete and summary is saved, say "RESEARCH COMPLETE" to end the conversation.
Be clear and directive in your instructions to other agents.""",
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
4. Respond to requests from the Coordinator

Always use the search_papers tool when asked to find papers.
Format your responses clearly with paper IDs for easy reference.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # Create Analyzer Agent
    analyzer = ConversableAgent(
        name="Analyzer",
        system_message="""You are the Analyzer agent specialized in analyzing paper content.

Your responsibilities:
1. Use read_paper tool to read full paper content
2. Use extract_keywords tool to identify key themes and concepts
3. Synthesize findings from multiple papers
4. Identify common themes, risks, and recommendations
5. Respond to requests from the Coordinator

Always use the provided tools for reading and analyzing papers.
Provide clear, structured analysis with key findings highlighted.""",
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
4. Report the save status to the Coordinator

Always create well-structured, comprehensive summaries.
Use the save_summary tool to persist the results.""",
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

    # Create GroupChat with all agents
    agents = [user_proxy, coordinator, searcher, analyzer, summarizer]
    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=30,
        speaker_selection_method="auto",
        allow_repeat_speaker=False,
    )

    # Create GroupChatManager
    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
    )

    return agents, group_chat, manager, user_proxy


def main():
    """Run the research assistant system with a test case."""
    print("=" * 80)
    print("Research Assistant System - Native AG2 Implementation")
    print("=" * 80)
    print()

    # Create the MAS
    print("Creating research assistant system...")
    agents, group_chat, manager, user_proxy = create_research_assistant_mas()
    print(f"Created {len(agents)} agents: {[agent.name for agent in agents]}")
    print()

    # Test case
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

    # Start the research workflow
    print("Starting research workflow...")
    print("=" * 80)
    print()

    try:
        user_proxy.initiate_chat(
            manager,
            message=research_query,
            clear_history=True
        )

        print()
        print("=" * 80)
        print("Research workflow completed!")
        print("=" * 80)

    except Exception as e:
        print(f"\nError during research workflow: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
