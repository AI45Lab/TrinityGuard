"""
Deep Research MAS Setup for Safety Testing

Constructs the deep-research-agent MAS using the experimental DeepResearchAgent
from autogen.agents.experimental for use with TrinityGuard framework.

Note: Requires autogen >= 0.9.7 (not pyautogen).

Agents:
    - deep_research_agent: Experimental research agent with multi-turn reasoning
    - user_proxy: User proxy agent (code execution disabled for safety testing)
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import time

import yaml

try:
    from autogen import ConversableAgent, UserProxyAgent
except ImportError:
    try:
        from pyautogen import ConversableAgent, UserProxyAgent
    except ImportError:
        raise ImportError("AG2/AutoGen not installed. Install with: uv pip install autogen")

try:
    from autogen.agents.experimental import DeepResearchAgent
except ImportError:
    raise ImportError("DeepResearchAgent not available. Requires autogen >= 0.9.7")

# Add project root to path (ensure it's FIRST to avoid shadowing by local src/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()
project_root_str = str(PROJECT_ROOT)
# Remove any local mas_test path that would shadow the project src
mas_test_dir = str(Path(__file__).parent.parent)
while mas_test_dir in sys.path:
    sys.path.remove(mas_test_dir)
# Remove and re-add PROJECT_ROOT at front
while project_root_str in sys.path:
    sys.path.remove(project_root_str)
sys.path.insert(0, project_root_str)

# Import AG2MAS from project framework
try:
    from src.level1_framework.ag2_wrapper import AG2MAS
    from src.level1_framework.base import AgentInfo, WorkflowResult
except ImportError as e:
    print(f"Error importing AG2MAS: {e}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"sys.path: {sys.path[:5]}")
    raise

from src.utils.logging_config import get_logger


# ============================================================================
# Custom DeepResearchMAS Adapter (inherits AG2MAS for Safety_MAS compatibility)
# ============================================================================

class DeepResearchMAS(AG2MAS):
    """Custom adapter for DeepResearchAgent that inherits AG2MAS.

    This allows Safety_MAS to recognize it as a valid MAS type.
    DeepResearchAgent uses .run() instead of initiate_chat(), so we override
    run_workflow() to handle this difference.
    """

    def __init__(self, research_agent: DeepResearchAgent, user_proxy: UserProxyAgent):
        """Initialize DeepResearchMAS adapter.

        Args:
            research_agent: The DeepResearchAgent instance
            user_proxy: The UserProxyAgent instance
        """
        # Initialize AG2MAS with minimal agents (for compatibility)
        # We pass agents but won't use standard GroupChat
        super().__init__(
            agents=[research_agent, user_proxy],
            group_chat=None,  # Not using GroupChat for DeepResearchAgent
            manager=None
        )
        self.logger = get_logger("DeepResearchMAS")
        self._research_agent = research_agent
        self._user_proxy = user_proxy

    def get_agents(self) -> List[AgentInfo]:
        """Return list of all agents in the system."""
        return [
            AgentInfo(
                name=self._research_agent.name,
                role="Deep Research Agent",
                system_prompt=getattr(self._research_agent, 'system_message', ''),
                tools=[]
            ),
            AgentInfo(
                name=self._user_proxy.name,
                role="User Proxy",
                system_prompt="",  # UserProxyAgent doesn't have system_message
                tools=[]
            )
        ]

    def run_workflow(self, task: str, **kwargs) -> WorkflowResult:
        """Execute deep research workflow.

        Args:
            task: Research question/topic
            **kwargs: Additional parameters:
                - max_turns: Maximum research turns (default: 5)
                - summary_method: Method for summarizing (default: "reflection_with_llm")
                - silent: If True, suppress native output (has no effect on DeepResearchAgent)
        """
        self.logger.log_workflow_start(task, "deep_research")
        self._message_history.clear()

        start_time = time.time()

        try:
            # DeepResearchAgent uses .run() with specific parameters
            max_turns = kwargs.get('max_turns', 5)
            summary_method = kwargs.get('summary_method', 'reflection_with_llm')

            self.logger.info(f"Running deep research with max_turns={max_turns}")

            # Run deep research agent
            result = self._research_agent.run(
                message=task,
                tools=self._research_agent.tools,
                max_turns=max_turns,
                user_input=False,  # No human input during safety testing
                summary_method=summary_method,
            )

            # Process and extract results
            if hasattr(result, 'process'):
                result.process()

            # Extract summary/content
            output = ""
            if hasattr(result, 'summary'):
                output = result.summary
            elif hasattr(result, 'result'):
                output = str(result.result)
            else:
                output = str(result)

            # Create synthetic message history for safety framework
            self._message_history.append({
                "from": self._user_proxy.name,
                "to": self._research_agent.name,
                "content": task,
                "timestamp": start_time
            })

            # Try to extract conversation from result if available
            if hasattr(result, 'chat_history'):
                for msg in result.chat_history:
                    self._message_history.append(msg)
            else:
                self._message_history.append({
                    "from": self._research_agent.name,
                    "to": self._user_proxy.name,
                    "content": output,
                    "timestamp": time.time()
                })

            elapsed = time.time() - start_time
            self.logger.log_workflow_end(success=True, duration=elapsed)

            return WorkflowResult(
                success=True,
                output=output,
                messages=self._message_history,
                metadata={
                    "mode": "deep_research",
                    "max_turns": max_turns,
                    "summary_method": summary_method,
                    "elapsed": elapsed
                }
            )

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"Deep research workflow failed: {str(e)}", exc_info=True)
            return WorkflowResult(
                success=False,
                output=None,
                messages=self._message_history,
                error=str(e),
                metadata={"elapsed": elapsed}
            )


# ============================================================================
# LLM Config Loading
# ============================================================================

def load_llm_config_from_yaml() -> Dict[str, Any]:
    """Load LLM configuration from project's mas_llm_config.yaml.

    Returns:
        AG2-compatible LLM config dict (for autogen >= 0.9.7)
    """
    config_path = PROJECT_ROOT / "config" / "mas_llm_config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"LLM config not found: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Return config dict compatible with AG2 0.9+
    return {
        "model": config.get("model", "gpt-4o-mini"),
        "api_key": config.get("api_key"),
        "base_url": config.get("base_url"),
        "temperature": config.get("temperature", 1),
        "timeout": 120,
    }


# ============================================================================
# MAS Construction
# ============================================================================

def create_deep_research_mas(llm_config_override: Optional[Dict] = None) -> DeepResearchMAS:
    """Create Deep Research MAS wrapped for TrinityGuard.

    This creates a DeepResearchAgent and wraps it in our custom adapter
    (which inherits AG2MAS) to work with the safety testing framework.

    Args:
        llm_config_override: Optional config dict to override defaults

    Returns:
        DeepResearchMAS instance ready for Safety_MAS wrapping
    """
    llm_config = llm_config_override or load_llm_config_from_yaml()

    # --- Create DeepResearchAgent ---
    # Note: DeepResearchAgent accepts config dict in newer autogen versions
    deep_research_agent = DeepResearchAgent(
        name="deep_research_agent",
        llm_config=llm_config,
    )

    # --- Create UserProxy ---
    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
        code_execution_config=False,  # Disabled for safety testing
    )

    # --- Wrap in custom adapter (inherits AG2MAS) ---
    mas = DeepResearchMAS(
        research_agent=deep_research_agent,
        user_proxy=user_proxy,
    )

    return mas


def get_default_task() -> str:
    """Return default deep research task for testing.

    Returns:
        Default task string
    """
    return (
        "Research and analyze the current state of quantum computing development. "
        "Focus on recent breakthroughs in 2024-2025, major players in the industry, "
        "and potential applications. Provide a comprehensive summary with key findings."
    )


# ============================================================================
# Standalone Test
# ============================================================================

if __name__ == "__main__":
    # Quick test: verify MAS construction
    print("Creating Deep Research MAS...")
    mas = create_deep_research_mas()
    agents = mas.get_agents()
    print(f"Created MAS with {len(agents)} agents:")
    for agent in agents:
        print(f"  - {agent.name}: {agent.role}")
    print(f"Topology: {mas.get_topology()}")
    print(f"\nDefault task: {get_default_task()[:80]}...")

    # Optional: Run a quick test
    print("\n" + "=" * 70)
    print("Running quick test...")
    print("=" * 70)

    task = "What are the main benefits and risks of artificial intelligence?"
    result = mas.run_workflow(task, max_turns=2, summary_method="reflection_with_llm")

    if result.success:
        print("\n" + "=" * 70)
        print("RESEARCH RESULT")
        print("=" * 70)
        print(result.output)
        print("\n" + "=" * 70)
        print(f"Completed in {result.metadata.get('elapsed', 0):.1f}s")
        print("=" * 70)
    else:
        print(f"\nError: {result.error}")

    print("\nMAS construction successful!")
