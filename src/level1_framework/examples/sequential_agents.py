"""Sequential Agents MAS - A pure sequential A -> B -> C workflow.

This example demonstrates a simple multi-agent system with:
- Agent A: Task initiator and coordinator
- Agent B: Task processor
- Agent C: Final reporter and summarizer

All agents are independent and work in a sequential chain.
"""

from typing import Optional

try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager
except ImportError:
    try:
        from pyautogen import ConversableAgent, GroupChat, GroupChatManager
    except ImportError:
        raise ImportError("AG2/AutoGen not installed. Install with: pip install ag2")

from ..ag2_wrapper import AG2MAS
from ...utils.llm_config import get_mas_llm_config, MASLLMConfig


def create_sequential_agents_mas(config: Optional[MASLLMConfig] = None) -> AG2MAS:
    """Create a Sequential Agents MAS instance with A -> B -> C workflow.

    Args:
        config: Optional MASLLMConfig. If not provided, loads from mas_llm_config.yaml

    Returns:
        AG2MAS instance with 3 sequential agents: agent_a, agent_b, agent_c
    """
    if config is None:
        config = get_mas_llm_config()

    llm_config = config.to_ag2_config()

    # ==================== Agent A: Task Initiator ====================
    agent_a = ConversableAgent(
        name="agent_a",
        system_message="""You are Agent A, the task initiator.

Your role is to:
1. Receive tasks from users
2. Analyze and understand the requirements
3. Pass the task to Agent B for processing
4. Keep track of the overall workflow

Be clear and concise when delegating tasks.
When the task is complete, say "WORKFLOW COMPLETE" to end the conversation.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # ==================== Agent B: Task Processor ====================
    agent_b = ConversableAgent(
        name="agent_b",
        system_message="""You are Agent B, the task processor.

Your role is to:
1. Receive tasks from Agent A
2. Process and analyze the task
3. Perform necessary work or calculations
4. Pass the results to Agent C for final reporting
5. If you need more information, ask Agent A

Be thorough in your processing.
When done, clearly state "PROCESSED: [brief summary]" before passing to Agent C.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # ==================== Agent C: Final Reporter ====================
    agent_c = ConversableAgent(
        name="agent_c",
        system_message="""You are Agent C, the final reporter and summarizer.

Your role is to:
1. Receive processed results from Agent B
2. Review and validate the work
3. Create a clear, well-structured summary
4. Present the final report to Agent A
5. Ensure the output is actionable and clear

Format your reports as:
========================================
FINAL REPORT
========================================
Summary: [2-3 sentence overview]
Details: [key findings or results]
Recommendations: [if applicable]
========================================

After presenting your report, say "TASK COMPLETE".""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # ==================== Define Sequential Workflow ====================
    # Fixed transitions: A -> B -> C
    allowed_transitions = {
        agent_a: [agent_b],  # A can only speak to B
        agent_b: [agent_c],  # B can only speak to C
        agent_c: [agent_a],  # C reports back to A
    }

    # Create GroupChat with sequential constraints
    agents = [agent_a, agent_b, agent_c]
    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=15,
        allowed_or_disallowed_speaker_transitions=allowed_transitions,
        speaker_transitions_type="allowed",  # These are allowed transitions
    )

    # Create GroupChatManager
    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
    )

    return AG2MAS(
        agents=agents,
        group_chat=group_chat,
        manager=manager
    )


class SequentialAgentsMAS(AG2MAS):
    """Convenience class for Sequential Agents MAS with additional methods."""

    def __init__(self, config: Optional[MASLLMConfig] = None):
        """Initialize Sequential Agents MAS.

        Args:
            config: Optional LLMConfig
        """
        mas = create_sequential_agents_mas(config)
        # Copy attributes from created MAS
        super().__init__(
            agents=list(mas._agents.values()),
            group_chat=mas._group_chat,
            manager=mas._manager
        )

    def process_task(self, task: str, **kwargs) -> str:
        """Process a task through the sequential A -> B -> C workflow.

        Args:
            task: The task description to process
            **kwargs: Additional arguments for run_workflow

        Returns:
            The final output string from Agent C
        """
        result = self.run_workflow(task, **kwargs)
        return result.output

    def process_task_with_carryover(self, tasks: list[str], **kwargs) -> list:
        """Process multiple tasks sequentially with carryover.

        Each task benefits from the context and results of previous tasks.

        Args:
            tasks: List of task descriptions to process in sequence
            **kwargs: Additional arguments for initiate_chats

        Returns:
            List of ChatResult objects from each task
        """
        agent_a = self.get_agent("agent_a")
        agent_b = self.get_agent("agent_b")
        agent_c = self.get_agent("agent_c")

        # Build chat queue for sequential execution
        chat_queue = []
        for i, task in enumerate(tasks):
            # First task: A -> B
            chat_queue.append({
                "sender": agent_a,
                "recipient": agent_b,
                "message": task,
                "summary_method": "last_msg",
            })

            # Then: B -> C (with carryover from previous tasks)
            chat_queue.append({
                "sender": agent_b,
                "recipient": agent_c,
                "message": f"Process and report on task {i+1}",
                "summary_method": "last_msg",
                # Carryover is automatically handled by initiate_chats
            })

        # Execute all chats sequentially
        return agent_a.initiate_chats(chat_queue, **kwargs)


# ==================== Example Usage ====================
if __name__ == "__main__":
    # Example 1: Simple sequential task
    print("=" * 60)
    print("Example 1: Simple Sequential Task")
    print("=" * 60)

    mas = SequentialAgentsMAS()
    result = mas.process_task(
        "Analyze the benefits of renewable energy and provide recommendations"
    )
    print(f"\nFinal Result:\n{result}\n")

    # Example 2: Multiple tasks with carryover
    print("=" * 60)
    print("Example 2: Multiple Tasks with Carryover")
    print("=" * 60)

    tasks = [
        "Research solar energy advantages",
        "Research wind energy advantages",
        "Compare both and recommend the best option"
    ]

    results = mas.process_task_with_carryover(tasks)
    for i, res in enumerate(results):
        print(f"\n--- Task {i+1} Result ---")
        print(res.summary)
