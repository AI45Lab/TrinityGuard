"""Math Solver MAS - A 3-agent system for mathematical calculations.

This example demonstrates a multi-agent system with:
- Coordinator: Receives tasks and delegates to specialists
- Calculator: Performs mathematical calculations
- Verifier: Double-checks and verifies results
"""

from typing import Optional, List

try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager
except ImportError:
    try:
        from pyautogen import ConversableAgent, GroupChat, GroupChatManager
    except ImportError:
        raise ImportError("AG2/AutoGen not installed. Install with: pip install ag2")

from ..ag2_wrapper import AG2MAS
from ...utils.llm_config import get_llm_config, LLMConfig


def create_math_solver_mas(config: Optional[LLMConfig] = None) -> AG2MAS:
    """Create a Math Solver MAS instance.

    Args:
        config: Optional LLMConfig. If not provided, loads from llm_config.yaml

    Returns:
        AG2MAS instance with 4 agents: user_proxy, coordinator, calculator, verifier
    """
    if config is None:
        config = get_llm_config()

    llm_config = config.to_ag2_config()

    # Create Coordinator Agent
    coordinator = ConversableAgent(
        name="coordinator",
        system_message="""You are a coordinator agent in a math solving team.
Your role is to:
1. Receive mathematical problems from users
2. Break down complex problems into steps
3. Delegate calculations to the calculator agent
4. Request verification from the verifier agent
5. Compile and present the final answer

Always be clear about what you're asking other agents to do.
When you have the final verified answer, say "FINAL ANSWER: [result]" to end the conversation.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # Create Calculator Agent
    calculator = ConversableAgent(
        name="calculator",
        system_message="""You are a calculator agent specialized in mathematical computations.
Your role is to:
1. Perform arithmetic calculations accurately
2. Show your work step by step
3. Handle basic operations: +, -, *, /, ^, sqrt, etc.
4. Report results clearly

Always double-check your calculations before responding.
Format: "Calculation: [expression] = [result]"
""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # Create Verifier Agent
    verifier = ConversableAgent(
        name="verifier",
        system_message="""You are a verifier agent responsible for checking mathematical results.
Your role is to:
1. Verify calculations performed by the calculator
2. Check for arithmetic errors
3. Confirm or reject results with explanation
4. Suggest corrections if errors are found

Be thorough but concise in your verification.
Format: "Verification: [CORRECT/INCORRECT] - [explanation]"
""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # Create UserProxy for initiating conversations
    user_proxy = ConversableAgent(
        name="user_proxy",
        system_message="You represent the user. Pass tasks to the coordinator.",
        llm_config=False,  # No LLM for user proxy
        human_input_mode="NEVER",
        is_termination_msg=lambda x: "FINAL ANSWER" in x.get("content", "").upper() if x else False,
    )

    # Create GroupChat
    agents = [user_proxy, coordinator, calculator, verifier]
    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=12,
        speaker_selection_method="round_robin",
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


class MathSolverMAS(AG2MAS):
    """Convenience class for Math Solver MAS with additional methods."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize Math Solver MAS.

        Args:
            config: Optional LLMConfig
        """
        mas = create_math_solver_mas(config)
        # Copy attributes from created MAS
        super().__init__(
            agents=list(mas._agents.values()),
            group_chat=mas._group_chat,
            manager=mas._manager
        )

    def solve(self, problem: str, **kwargs) -> str:
        """Solve a math problem.

        Args:
            problem: The math problem to solve
            **kwargs: Additional arguments for run_workflow

        Returns:
            The solution string
        """
        result = self.run_workflow(problem, **kwargs)
        return result.output
