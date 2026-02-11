"""Deep Research Agent - AG2MAS Format Implementation

This script creates a MAS wrapper for DeepResearchAgent that properly
preserves its internal tools and workflow.

Usage:
    from tests.ag2_deepresearch.deep_research import create_deep_research_mas
    mas = create_deep_research_mas()
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from autogen import ConversableAgent
    from autogen.agents.experimental import DeepResearchAgent
except ImportError:
    try:
        from pyautogen import ConversableAgent
        from pyautogen.agents.experimental import DeepResearchAgent
    except ImportError:
        raise ImportError("AG2/AutoGen not installed. Install with: pip install ag2")

from src.level1_framework.ag2_wrapper import AG2MAS
from src.level1_framework.base import BaseMAS, WorkflowResult
from src.utils.llm_config import get_mas_llm_config


class DeepResearchMAS(BaseMAS):
    """Custom MAS wrapper for DeepResearchAgent.

    This wrapper preserves the DeepResearchAgent's native run() method
    and tools, instead of using GroupChat.
    """

    def __init__(self, deep_research_agent):
        """Initialize with a DeepResearchAgent.

        Args:
            deep_research_agent: DeepResearchAgent instance
        """
        super().__init__()
        self.agent = deep_research_agent
        self._agents = [deep_research_agent]

    def get_agents(self):
        """Get list of agent information."""
        from src.level1_framework.base import AgentInfo

        return [
            AgentInfo(
                name=self.agent.name,
                role="Deep Research Agent",
                system_message=getattr(self.agent, 'system_message', ''),
                description="Experimental deep research agent with tools",
                tools=getattr(self.agent, 'tools', None)
            )
        ]

    def get_agent(self, name: str):
        """Get a specific agent by name."""
        if name == self.agent.name:
            return self.agent
        raise ValueError(f"Agent '{name}' not found")

    def get_topology(self):
        """Get communication topology."""
        return {
            self.agent.name: []  # Single agent, no topology
        }

    def run_workflow(self, task: str, max_round: int = 10, **kwargs):
        """Run the deep research workflow using agent's native run() method.

        Args:
            task: Research topic/question
            max_round: Maximum rounds (passed as max_turns to agent.run())
            **kwargs: Additional parameters (ignored for now)

        Returns:
            WorkflowResult with the research output
        """
        from src.level1_framework.base import WorkflowResult

        try:
            # Use the native run() method with tools
            result = self.agent.run(
                message=task,
                tools=self.agent.tools,  # Pass the agent's tools
                max_turns=max_round,  # Use max_round as max_turns
                user_input=False,
                summary_method="reflection_with_llm",
            )

            # Convert to WorkflowResult
            output = ""
            if hasattr(result, 'summary'):
                output = result.summary
            elif hasattr(result, 'process'):
                result.process()
                output = str(result)
            else:
                output = str(result)

            return WorkflowResult(
                success=True,
                output=output,
                messages=[],
                metadata={"raw_result": str(result)}
            )

        except Exception as e:
            return WorkflowResult(
                success=False,
                output="",
                messages=[],
                error=str(e),
                metadata={}
            )


def create_deep_research_mas(silent: bool = True):
    """Create a Deep Research MAS wrapped for MASSafetyGuard.

    This creates a custom MAS wrapper that preserves DeepResearchAgent's
    native functionality including its internal tools.

    Args:
        silent: If True, suppress AG2 native console output

    Returns:
        Custom MAS wrapper (DeepResearchMAS) for DeepResearchAgent
    """
    config = get_mas_llm_config()
    llm_config = config.to_ag2_config()

    # Create DeepResearchAgent
    deep_research_agent = DeepResearchAgent(
        name="DeepResearchAgent",
        llm_config=llm_config,
    )

    # Wrap with custom MAS that preserves native run() method
    mas = DeepResearchMAS(deep_research_agent)

    return mas


def run_deep_research_native(agent, research_topic: str, max_turns: int = 2):
    """Run deep research using the agent's native run() method.

    This is equivalent to the original code:
        result = agent.run(
            message=first_message,
            tools=agent.tools,
            max_turns=2,
            user_input=False,
            summary_method="reflection_with_llm",
        )

    Args:
        agent: DeepResearchAgent instance
        research_topic: The topic to research
        max_turns: Maximum number of research turns

    Returns:
        Result from the deep research
    """
    print("=" * 80)
    print("Deep Research Agent - Native Mode")
    print("=" * 80)
    print()

    print(f"Research Topic: {research_topic}")
    print(f"Max Turns: {max_turns}")
    print()

    print("Starting deep research workflow...")
    print("=" * 80)
    print()

    try:
        # Use the native run() method with tools
        result = agent.run(
            message=research_topic,
            tools=agent.tools,
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
    """Main function - Demo of the MAS wrapper."""
    print("=" * 80)
    print("Deep Research Agent - AG2MAS Wrapper Demo")
    print("=" * 80)
    print()

    # Create the MAS
    print("Creating Deep Research MAS...")
    try:
        mas = create_deep_research_mas(silent=True)
        print("✓ MAS created successfully!")
        print()

        # Show agent info
        agents = mas.get_agents()
        print(f"Agent: {agents[0].name}")
        print(f"Role: {agents[0].role}")
        if agents[0].tools:
            print(f"Tools: {agents[0].tools}")
        print()
    except Exception as e:
        print(f"✗ Failed to create MAS: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test workflow
    print("=" * 80)
    print("Testing Workflow Execution")
    print("=" * 80)
    print()

    research_topic = "What are the latest developments in multi-agent system safety?"

    try:
        result = mas.run_workflow(research_topic, max_round=2)

        if result.success:
            print("\n✓ Workflow completed successfully!")
            print("\nOutput:")
            print(result.output)
        else:
            print(f"\n✗ Workflow failed: {result.error}")

    except Exception as e:
        print(f"\nError during workflow: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
