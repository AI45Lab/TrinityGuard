"""EvoAgentX workflow adapter for MASSafetyGuard.

This module provides functionality to convert EvoAgentX workflow.json files
into AG2MAS instances that conform to the BaseMAS interface.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional

try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager
except ImportError:
    try:
        from pyautogen import ConversableAgent, GroupChat, GroupChatManager
    except ImportError:
        raise ImportError(
            "AG2/AutoGen not installed. Install with: pip install ag2"
        )

from .ag2_wrapper import AG2MAS
from ..utils.logging_config import get_logger


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class AgentConfig:
    """Agent definition from original_nodes in workflow.json."""
    name: str
    description: str
    inputs: List[Dict] = field(default_factory=list)
    outputs: List[Dict] = field(default_factory=list)
    prompt: str = ""


@dataclass
class WorkflowNode:
    """Workflow node from original_nodes in workflow.json."""
    name: str
    description: str
    inputs: List[Dict] = field(default_factory=list)
    outputs: List[Dict] = field(default_factory=list)
    reason: str = ""
    agents: List[AgentConfig] = field(default_factory=list)
    status: str = "pending"


@dataclass
class ParsedWorkflow:
    """Complete workflow parsing result."""
    goal: str
    nodes: List[WorkflowNode] = field(default_factory=list)
    uploaded_files: Dict[str, str] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


# ============================================================================
# Parser
# ============================================================================

class WorkflowParser:
    """Parse and validate EvoAgentX workflow.json files."""

    def __init__(self):
        self.logger = get_logger("WorkflowParser")

    def parse(self, json_path: str) -> ParsedWorkflow:
        """Parse workflow.json file into structured representation.

        Args:
            json_path: Path to workflow.json file

        Returns:
            ParsedWorkflow object with structured workflow data

        Raises:
            FileNotFoundError: If json_path doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        self.logger.info(f"Parsing workflow from: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        workflow_data = data.get("workflow", {})
        exec_context = data.get("execution_context", {})

        # Extract goal (prefer workflow.goal, fallback to execution_context.goal)
        goal = workflow_data.get("goal", exec_context.get("goal", ""))

        # Parse original_nodes
        nodes = self._parse_original_nodes(workflow_data.get("original_nodes", []))

        # Extract uploaded_files
        uploaded_files = workflow_data.get("uploaded_files", {})

        # Extract metadata
        metadata = data.get("metadata", {})

        parsed = ParsedWorkflow(
            goal=goal,
            nodes=nodes,
            uploaded_files=uploaded_files,
            metadata=metadata
        )

        self.logger.info(f"Parsed workflow with {len(nodes)} nodes, goal: {goal[:50]}...")
        return parsed

    def _parse_original_nodes(self, nodes_data: List[Dict]) -> List[WorkflowNode]:
        """Parse original_nodes section from workflow.json.

        Args:
            nodes_data: List of node dictionaries from original_nodes

        Returns:
            List of WorkflowNode objects
        """
        nodes = []

        for node_data in nodes_data:
            # Parse agents for this node
            agents = []
            for agent_data in node_data.get("agents", []):
                agent_config = AgentConfig(
                    name=agent_data.get("name", ""),
                    description=agent_data.get("description", ""),
                    inputs=agent_data.get("inputs", []),
                    outputs=agent_data.get("outputs", []),
                    prompt=agent_data.get("prompt", "")
                )
                agents.append(agent_config)

            # Create WorkflowNode
            node = WorkflowNode(
                name=node_data.get("name", ""),
                description=node_data.get("description", ""),
                inputs=node_data.get("inputs", []),
                outputs=node_data.get("outputs", []),
                reason=node_data.get("reason", ""),
                agents=agents,
                status=node_data.get("status", "pending")
            )
            nodes.append(node)

            self.logger.debug(f"Parsed node '{node.name}' with {len(agents)} agent(s)")

        return nodes


# ============================================================================
# Converter
# ============================================================================

class WorkflowToAG2Converter:
    """Convert ParsedWorkflow to AG2MAS instance."""

    def __init__(self, llm_config: Optional[Dict] = None, max_round: int = 10):
        """Initialize converter with LLM configuration.

        Args:
            llm_config: Optional LLM config dict for AG2 agents.
                       If None, uses default from MASLLMConfig.
            max_round: Maximum number of conversation rounds (default: 10)
        """
        self.logger = get_logger("EvoAgentXConverter")
        self.llm_config = llm_config or self._get_default_llm_config()
        self.max_round = max_round

    def convert(self, workflow: ParsedWorkflow) -> AG2MAS:
        """Convert ParsedWorkflow to AG2MAS instance.

        Args:
            workflow: Parsed workflow data

        Returns:
            AG2MAS instance ready for execution

        Raises:
            ValueError: If workflow has no nodes or agents
        """
        self.logger.info(f"Converting workflow: {workflow.goal[:50]}...")

        # 1. Create agents from nodes
        agents = self._create_agents_from_nodes(workflow.nodes)

        if not agents:
            raise ValueError("Workflow must contain at least one agent")

        # 2. Build sequential transitions
        transitions = self._build_sequential_transitions(agents)

        # 3. Create GroupChat with transitions
        group_chat = GroupChat(
            agents=agents,
            messages=[],
            max_round=self.max_round,  # Use configured max_round
            allowed_or_disallowed_speaker_transitions=transitions,
            speaker_transitions_type="allowed"
        )

        # 4. Create GroupChatManager
        manager = GroupChatManager(
            groupchat=group_chat,
            llm_config=self.llm_config
        )

        # 5. Create and return AG2MAS
        mas = AG2MAS(agents=agents, group_chat=group_chat, manager=manager)

        self.logger.info(f"Created AG2MAS with {len(agents)} agents")
        return mas

    def _create_agents_from_nodes(
        self,
        nodes: List[WorkflowNode]
    ) -> List[ConversableAgent]:
        """Extract and create all agents from workflow nodes.

        Args:
            nodes: List of WorkflowNode objects

        Returns:
            List of ConversableAgent instances
        """
        agents = []

        for node in nodes:
            for agent_config in node.agents:
                # Create ConversableAgent using agent's prompt as system_message
                agent = ConversableAgent(
                    name=agent_config.name,
                    system_message=agent_config.prompt,
                    llm_config=self.llm_config,
                    human_input_mode="NEVER",
                    is_termination_msg=lambda x: isinstance(x, dict) and
                                                 x.get("content", "").strip().upper().endswith("TERMINATE")
                )
                agents.append(agent)

                self.logger.info(f"Created agent: {agent_config.name}")

        return agents

    def _build_sequential_transitions(
        self,
        agents: List[ConversableAgent]
    ) -> Dict[ConversableAgent, List[ConversableAgent]]:
        """Build sequential speaker transitions: A → B → C → ...

        Args:
            agents: List of agents in sequential order

        Returns:
            Dict mapping each agent to its allowed next speakers
        """
        transitions = {}

        # Build chain: agents[i] → agents[i+1]
        for i in range(len(agents) - 1):
            transitions[agents[i]] = [agents[i + 1]]

        # Last agent has no transitions (workflow ends)
        transitions[agents[-1]] = []

        self.logger.debug(f"Built sequential transitions for {len(agents)} agents")
        return transitions

    def _get_default_llm_config(self) -> Dict:
        """Get default LLM configuration from MASSafetyGuard utils.

        Returns:
            LLM config dict for AG2
        """
        try:
            from ..utils.llm_config import get_mas_llm_config
            default_config = get_mas_llm_config()
            return default_config.to_ag2_config()
        except Exception as e:
            self.logger.warning(f"Failed to load MASLLMConfig: {e}")
            # Fallback to basic config
            return {"model": "gpt-4"}


# ============================================================================
# Convenience Function
# ============================================================================

def create_ag2_mas_from_evoagentx(
    workflow_path: str,
    llm_config: Optional[Dict] = None,
    max_round: int = 10
) -> AG2MAS:
    """Create AG2MAS instance from EvoAgentX workflow.json file.

    This is the main entry point for converting EvoAgentX workflows to
    MASSafetyGuard's BaseMAS interface.

    Args:
        workflow_path: Path to workflow.json file
        llm_config: Optional LLM config dict. If None, uses MASLLMConfig default.
        max_round: Maximum number of conversation rounds (default: 10)

    Returns:
        AG2MAS instance ready for use with Safety_MAS

    Raises:
        FileNotFoundError: If workflow_path doesn't exist
        ValueError: If workflow is invalid or has no agents

    Example:
        >>> mas = create_ag2_mas_from_evoagentx("workflow/my_workflow.json")
        >>> safety_mas = Safety_MAS(mas=mas)
        >>> result = safety_mas.run_task("Analyze the document")
        >>> print(result.output)
    """
    logger = get_logger("create_ag2_mas_from_evoagentx")
    logger.info(f"Creating AG2MAS from EvoAgentX workflow: {workflow_path}")

    # Parse workflow
    parser = WorkflowParser()
    workflow = parser.parse(workflow_path)

    # Convert to AG2MAS
    converter = WorkflowToAG2Converter(llm_config, max_round)
    mas = converter.convert(workflow)

    logger.info("Successfully created AG2MAS from EvoAgentX workflow")
    return mas
