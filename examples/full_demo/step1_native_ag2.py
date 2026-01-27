"""Step 1: Native AG2 Research Assistant System with Fixed Linear Workflow.

This example demonstrates a 4-agent research assistant system with a fully deterministic
linear workflow using single-entry adjacency list:

  User → Coordinator → Searcher → Analyzer → Summarizer → User (terminate)

Each agent has exactly ONE allowed next agent, so AG2 skips LLM-based speaker selection
and directly routes to the only candidate. This makes the workflow fully deterministic.

Agents:
- Coordinator: Receives task from User, frames research plan, delegates to Searcher
- Searcher: Searches for academic papers using search_papers tool, passes to Analyzer
- Analyzer: Analyzes papers using read_paper and extract_keywords tools, passes to Summarizer
- Summarizer: Summarizes findings using save_summary tool, reports to User

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
    """Create a research assistant MAS with fixed linear workflow.

    Uses single-entry adjacency list for fully deterministic routing:
    User → Coordinator → Searcher → Analyzer → Summarizer → User

    Returns:
        Tuple of (agents, group_chat, manager, user_proxy)
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
4. After the tool returns success, IMMEDIATELY respond with a termination message

You are the last agent in a fixed linear workflow. You receive analysis from the Analyzer.

CRITICAL TERMINATION PROTOCOL (MANDATORY):
When you receive the tool execution result from save_summary:
- You MUST immediately generate a text response
- This response MUST contain the exact phrase "RESEARCH COMPLETE" (in uppercase)
- This is NOT optional - the workflow CANNOT terminate without this message
- Even if the tool succeeded, you MUST still send this termination message

REQUIRED RESPONSE FORMAT after tool execution:
"The research summary has been successfully saved to [filename]. RESEARCH COMPLETE."

IMPORTANT: After calling save_summary, you will receive a tool response. When you see this response, you MUST generate the termination message above. Do NOT remain silent after the tool response!""",
        llm_config=llm_config,
        human_input_mode="NEVER",
        max_consecutive_auto_reply=2,  # Allow Summarizer to reply after tool execution
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
    # 注意: 为了保持线性工作流的简洁性，让每个智能体自己执行工具 (caller = executor)
    # 这样工具执行不会打断工作流，allowed_transitions 可以保持简单的线性结构

    # Searcher gets search_papers tool
    register_function(
        search_papers,
        caller=searcher,
        executor=searcher,  # 自己执行工具，不打断工作流
        name="search_papers",
        description="Search for academic papers based on a query. Returns paper information including IDs, titles, authors, and abstracts."
    )

    # Analyzer gets read_paper and extract_keywords tools
    register_function(
        read_paper,
        caller=analyzer,
        executor=analyzer,  # 自己执行工具，不打断工作流
        name="read_paper",
        description="Read the full content of a paper by its ID. Returns detailed paper content."
    )

    register_function(
        extract_keywords,
        caller=analyzer,
        executor=analyzer,  # 自己执行工具，不打断工作流
        name="extract_keywords",
        description="Extract keywords and themes from text. Returns categorized keywords."
    )

    # Summarizer gets save_summary tool
    register_function(
        save_summary,
        caller=summarizer,
        executor=summarizer,  # 自己执行工具，不打断工作流
        name="save_summary",
        description="Save research summary to a file. Returns save status and file path."
    )

    # Define fixed linear workflow using single-entry adjacency list (单入口邻接表)
    # Each agent has exactly ONE allowed next agent → fully deterministic workflow
    # Workflow: User → Coordinator → Searcher → Analyzer → Summarizer → User (终止)
    # Note: Summarizer can also transition to itself to allow sending termination message after tool execution
    allowed_transitions = {
        user_proxy:   [coordinator],   # User → Coordinator (开始任务)
        coordinator:  [searcher],      # Coordinator → Searcher
        searcher:     [analyzer],      # Searcher → Analyzer
        analyzer:     [summarizer],    # Analyzer → Summarizer
        summarizer:   [summarizer, user_proxy],    # Summarizer → Summarizer (工具执行后继续) 或 User (终止检查)
    }

    # Create GroupChat with all agents and fixed linear workflow
    agents = [user_proxy, coordinator, searcher, analyzer, summarizer]
    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=10,
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

    return agents, group_chat, manager, user_proxy


def main():
    """Run the research assistant system with a test case."""
    print("=" * 80)
    print("Research Assistant System - Native AG2 Fixed Linear Workflow")
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
