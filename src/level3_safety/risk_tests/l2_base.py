"""L2 Agent Wrapper Test Base Class.

This module provides the base class for all L2 (Inter-Agent Communication) risk tests.
L2 tests focus on message interception and modification between agents.
"""

import random
from abc import abstractmethod
from typing import Callable, Dict, List, Optional

from .base import BaseRiskTest, TestCase
from ...level2_intermediary.base import MASIntermediary, RunMode
from ...level2_intermediary.workflow_runners import MessageInterception


class L2AgentWrapperTest(BaseRiskTest):
    """Base class for L2 Agent Wrapper risk tests.

    This class encapsulates the core logic for testing inter-agent communication
    vulnerabilities through message interception and modification.

    Subclasses must implement:
        - get_risk_info(): Return risk metadata
        - load_test_cases(): Load static test cases
        - generate_dynamic_cases(): Generate dynamic test cases
        - create_message_modifier(): Create message modification function

    Attributes:
        config: Configuration dictionary with test parameters
    """

    def __init__(self):
        """Initialize L2 Agent Wrapper Test."""
        super().__init__()
        self.config.update({
            "default_task": "Simple test task",
            "analyze_downstream_impact": True,
        })

    # === Abstract Methods ===

    @abstractmethod
    def create_message_modifier(self, test_case: TestCase) -> Callable[[str], str]:
        """Create a message modifier function for the test case.

        This method must be implemented by subclasses to define how messages
        should be modified during interception.

        Args:
            test_case: The test case containing modification parameters

        Returns:
            A function that takes a message string and returns modified string
        """
        pass

    # === Target Agent Selection ===

    def get_target_agent(self, intermediary: MASIntermediary) -> str:
        """Get the target agent for message interception.

        Default implementation randomly selects an agent from the MAS.
        Subclasses can override this to implement specific selection logic.

        Args:
            intermediary: MAS intermediary instance

        Returns:
            Name of the selected target agent

        Raises:
            ValueError: If no agents are available in the MAS
        """
        agents = intermediary.mas.get_agents()
        if not agents:
            raise ValueError("No agents available in the MAS")
        return random.choice(agents).name

    def get_source_agent(self, intermediary: MASIntermediary) -> str:
        """Get the source agent for message interception.

        Default implementation randomly selects an agent from the MAS.
        Subclasses can override this to implement specific selection logic.

        Args:
            intermediary: MAS intermediary instance

        Returns:
            Name of the selected source agent

        Raises:
            ValueError: If no agents are available in the MAS
        """
        agents = intermediary.mas.get_agents()
        if not agents:
            raise ValueError("No agents available in the MAS")
        return random.choice(agents).name

    def get_agent_pair(self, intermediary: MASIntermediary) -> tuple:
        """Get a pair of agents (source, target) for message interception.

        Default implementation randomly selects an adjacent pair of agents.
        Subclasses can override this to implement specific selection logic.

        Args:
            intermediary: MAS intermediary instance

        Returns:
            Tuple of (source_agent_name, target_agent_name)

        Raises:
            ValueError: If fewer than 2 agents are available
        """
        agents = intermediary.mas.get_agents()
        if len(agents) < 2:
            raise ValueError("Need at least 2 agents for agent pair selection")

        # Get adjacent pairs
        adjacent_pairs = []
        for i in range(len(agents) - 1):
            adjacent_pairs.append((agents[i].name, agents[i + 1].name))

        return random.choice(adjacent_pairs)

    # === Message Modifier Factory Methods ===

    @staticmethod
    def append_modifier(payload: str) -> Callable[[str], str]:
        """Create a modifier that appends payload to the message.

        Args:
            payload: Content to append to the message

        Returns:
            Modifier function that appends payload
        """
        def modifier(content: str) -> str:
            return content + payload
        return modifier

    @staticmethod
    def prepend_modifier(payload: str) -> Callable[[str], str]:
        """Create a modifier that prepends payload to the message.

        Args:
            payload: Content to prepend to the message

        Returns:
            Modifier function that prepends payload
        """
        def modifier(content: str) -> str:
            return payload + content
        return modifier

    @staticmethod
    def replace_modifier(payload: str) -> Callable[[str], str]:
        """Create a modifier that replaces the entire message with payload.

        Args:
            payload: Content to replace the message with

        Returns:
            Modifier function that replaces content
        """
        def modifier(content: str) -> str:
            return payload
        return modifier

    @staticmethod
    def truncate_modifier(ratio: float) -> Callable[[str], str]:
        """Create a modifier that truncates the message to a given ratio.

        Args:
            ratio: Ratio of the message to keep (0.0 to 1.0)

        Returns:
            Modifier function that truncates content

        Raises:
            ValueError: If ratio is not between 0.0 and 1.0
        """
        if not 0.0 <= ratio <= 1.0:
            raise ValueError("Ratio must be between 0.0 and 1.0")

        def modifier(content: str) -> str:
            keep_length = int(len(content) * ratio)
            return content[:keep_length]
        return modifier

    # === Core Test Execution ===

    def run_single_test(self, test_case: TestCase, intermediary: MASIntermediary) -> Dict:
        """Execute a single test case with message interception.

        This method:
        1. Gets source and target agents
        2. Creates a MessageInterception with the test case's modifier
        3. Runs the workflow with MONITORED_INTERCEPTING mode
        4. Uses the Judge to evaluate the results

        Args:
            test_case: Test case to execute
            intermediary: MAS intermediary to test against

        Returns:
            Dict with test results including:
                - test_case: Name of the test case
                - passed: Whether the test passed (system resisted the attack)
                - source_agent: Source agent name
                - target_agent: Target agent name
                - workflow_success: Whether the workflow completed
                - judge_result: Result from the judge evaluation
                - error: Error message if any
        """
        results = {
            "test_case": test_case.name,
            "passed": True,
            "source_agent": None,
            "target_agent": None,
            "workflow_success": False,
            "judge_result": None,
            "error": None,
        }

        try:
            # Get agent pair for interception
            agents = intermediary.mas.get_agents()
            if len(agents) < 2:
                results["error"] = "Need at least 2 agents for L2 interception test"
                results["passed"] = False
                return results

            source_agent, target_agent = self.get_agent_pair(intermediary)
            results["source_agent"] = source_agent
            results["target_agent"] = target_agent

            # Create message modifier from test case
            modifier = self.create_message_modifier(test_case)

            # Create interception configuration
            interception = MessageInterception(
                source_agent=source_agent,
                target_agent=target_agent,
                modifier=modifier
            )

            # Run workflow with interception
            task = self.config.get("default_task", "Simple test task")
            workflow_result = intermediary.run_workflow(
                task=task,
                mode=RunMode.MONITORED_INTERCEPTING,
                interceptions=[interception]
            )

            results["workflow_success"] = workflow_result.success

            # Evaluate results using judge
            judge_result = self._evaluate_with_judge(
                workflow_result=workflow_result,
                test_case=test_case
            )
            results["judge_result"] = judge_result

            # Determine if test passed (system resisted the attack)
            if judge_result and judge_result.get("has_risk", False):
                results["passed"] = False

        except Exception as e:
            results["error"] = str(e)
            results["passed"] = False

        return results

    def _evaluate_with_judge(self, workflow_result, test_case: TestCase) -> Optional[Dict]:
        """Evaluate workflow result using the configured judge.

        Args:
            workflow_result: Result from workflow execution
            test_case: The test case being evaluated

        Returns:
            Dict with judge evaluation results, or None if evaluation failed
        """
        try:
            judge = self.get_judge()

            # Prepare content for judge
            output = str(workflow_result.output) if workflow_result.output else ""
            messages_str = ""
            if workflow_result.messages:
                import json
                messages_str = json.dumps(workflow_result.messages[:10])  # Limit messages

            # Prepare context
            context = {
                "test_case": test_case.name,
                "test_input": test_case.input,
                "expected_behavior": test_case.expected_behavior,
                "workflow_output": output[:500],
                "messages": messages_str[:1000],
                "workflow_success": workflow_result.success,
            }

            # Run judge analysis
            judge_result = judge.analyze(content=output, context=context)

            if judge_result:
                return judge_result.to_dict()
            return None

        except Exception as e:
            return {"error": str(e), "has_risk": False}

    # === Monitor Integration ===

    def evaluate_with_monitor_agent(
        self,
        workflow_result,
        test_case: TestCase,
        monitor_agent
    ) -> Dict:
        """Evaluate workflow result using a monitor agent.

        This method integrates with the Monitor Agent system for
        additional evaluation capabilities.

        Args:
            workflow_result: Result from workflow execution
            test_case: The test case being evaluated
            monitor_agent: Monitor agent instance to use

        Returns:
            Dict with monitor evaluation results
        """
        from ..monitor_agents.base import BaseMonitorAgent
        from ...level2_intermediary.structured_logging import AgentStepLog, StepType
        import time

        results = {
            "test_case": test_case.name,
            "alerts": [],
            "monitor_name": None,
        }

        try:
            results["monitor_name"] = monitor_agent.get_monitor_info().get("name", "unknown")

            # Process each message through the monitor
            if workflow_result.messages:
                for msg in workflow_result.messages:
                    log_entry = AgentStepLog(
                        timestamp=time.time(),
                        agent_name=msg.get("from", msg.get("from_agent", "unknown")),
                        step_type=StepType.RESPOND,
                        content=str(msg.get("content", "")),
                        metadata={"source": "l2_test", "test_case": test_case.name}
                    )

                    alert = monitor_agent.process(log_entry)
                    if alert:
                        results["alerts"].append(alert.to_dict())

        except Exception as e:
            results["error"] = str(e)

        return results
