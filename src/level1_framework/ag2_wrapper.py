"""AG2 (AutoGen) framework wrapper implementation."""

from typing import List, Dict, Any, Optional
import json

try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager
except ImportError:
    # Fallback for pyautogen package name
    try:
        from pyautogen import ConversableAgent, GroupChat, GroupChatManager
    except ImportError:
        raise ImportError(
            "AG2/AutoGen not installed. Install with: pip install pyautogen"
        )

from .base import BaseMAS, AgentInfo, WorkflowResult
from ..utils.exceptions import MASFrameworkError
from ..utils.logging_config import get_logger


class AG2MAS(BaseMAS):
    """AG2 (AutoGen) framework wrapper."""

    def __init__(self, agents: List[ConversableAgent],
                 group_chat: Optional[GroupChat] = None,
                 manager: Optional[GroupChatManager] = None):
        """Initialize AG2 MAS wrapper.

        Args:
            agents: List of AG2 ConversableAgent instances
            group_chat: Optional GroupChat instance
            manager: Optional GroupChatManager instance
        """
        super().__init__()
        self.logger = get_logger("AG2MAS")
        self._agents = {agent.name: agent for agent in agents}
        self._group_chat = group_chat
        self._manager = manager
        self._message_history: List[Dict] = []

        # Register message interception
        self._setup_message_interception()

    def _setup_message_interception(self):
        """Set up message interception for all agents."""
        for agent in self._agents.values():
            # Store original send method
            original_send = agent.send

            # Create wrapper that applies hooks
            def send_wrapper(message: Dict, recipient: ConversableAgent,
                           request_reply: bool = None, silent: bool = False):
                # Apply message hooks
                modified_message = self._apply_message_hooks(message)

                # Log message
                self._message_history.append({
                    "from": agent.name,
                    "to": recipient.name,
                    "content": modified_message.get("content", ""),
                    "timestamp": self._get_timestamp()
                })

                # Call original send with modified message
                return original_send(modified_message, recipient, request_reply, silent)

            # Replace send method
            agent.send = send_wrapper

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()

    def get_agents(self) -> List[AgentInfo]:
        """Return list of all agents in the system."""
        agent_infos = []
        for name, agent in self._agents.items():
            agent_infos.append(AgentInfo(
                name=name,
                role=getattr(agent, 'role', 'agent'),
                system_prompt=agent.system_message if hasattr(agent, 'system_message') else None,
                tools=[]  # AG2 tools would need to be extracted from agent config
            ))
        return agent_infos

    def get_agent(self, name: str) -> ConversableAgent:
        """Get a specific agent by name."""
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found. Available agents: {list(self._agents.keys())}")
        return self._agents[name]

    def run_workflow(self, task: str, **kwargs) -> WorkflowResult:
        """Execute the MAS workflow with given task."""
        self.logger.log_workflow_start(task, "ag2_group_chat")
        self._message_history.clear()

        try:
            if self._manager and self._group_chat:
                # Use group chat mode
                result = self._run_group_chat(task, **kwargs)
            else:
                # Use direct agent-to-agent mode
                result = self._run_direct(task, **kwargs)

            self.logger.log_workflow_end(success=True, duration=0.0)
            return result

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
            return WorkflowResult(
                success=False,
                output=None,
                messages=self._message_history,
                error=str(e)
            )

    def _run_group_chat(self, task: str, **kwargs) -> WorkflowResult:
        """Run workflow using GroupChat."""
        max_rounds = kwargs.get('max_rounds', 10)

        # Initiate group chat
        user_proxy = list(self._agents.values())[0]  # Use first agent as initiator
        user_proxy.initiate_chat(
            self._manager,
            message=task,
            max_turns=max_rounds
        )

        # Extract result from chat history
        chat_result = self._manager.chat_messages if hasattr(self._manager, 'chat_messages') else []

        return WorkflowResult(
            success=True,
            output=self._extract_final_output(chat_result),
            messages=self._message_history,
            metadata={
                "mode": "group_chat",
                "rounds": len(self._message_history)
            }
        )

    def _run_direct(self, task: str, **kwargs) -> WorkflowResult:
        """Run workflow using direct agent-to-agent communication."""
        if len(self._agents) < 2:
            raise MASFrameworkError("Direct mode requires at least 2 agents")

        agents_list = list(self._agents.values())
        initiator = agents_list[0]
        receiver = agents_list[1]

        # Initiate conversation
        initiator.initiate_chat(
            receiver,
            message=task,
            max_turns=kwargs.get('max_rounds', 10)
        )

        return WorkflowResult(
            success=True,
            output=self._extract_final_output(self._message_history),
            messages=self._message_history,
            metadata={
                "mode": "direct",
                "rounds": len(self._message_history)
            }
        )

    def _extract_final_output(self, messages: List[Dict]) -> str:
        """Extract final output from message history."""
        if not messages:
            return ""
        # Return last message content
        last_msg = messages[-1]
        return last_msg.get("content", "")

    def get_topology(self) -> Dict:
        """Return the communication topology."""
        if self._group_chat:
            # In group chat, all agents can talk to all agents
            agent_names = list(self._agents.keys())
            return {name: [n for n in agent_names if n != name] for name in agent_names}
        else:
            # In direct mode, topology is sequential
            agent_names = list(self._agents.keys())
            topology = {}
            for i, name in enumerate(agent_names):
                if i < len(agent_names) - 1:
                    topology[name] = [agent_names[i + 1]]
                else:
                    topology[name] = []
            return topology


def create_ag2_mas_from_config(config: Dict) -> AG2MAS:
    """Create AG2MAS instance from configuration dict.

    Args:
        config: Configuration dict with agent definitions

    Returns:
        AG2MAS instance

    Example config:
        {
            "agents": [
                {
                    "name": "coordinator",
                    "system_message": "You are a coordinator agent.",
                    "llm_config": {"model": "gpt-4"}
                }
            ],
            "mode": "group_chat"  # or "direct"
        }
    """
    agents = []
    for agent_config in config.get("agents", []):
        agent = ConversableAgent(
            name=agent_config["name"],
            system_message=agent_config.get("system_message", ""),
            llm_config=agent_config.get("llm_config", False),
            human_input_mode=agent_config.get("human_input_mode", "NEVER")
        )
        agents.append(agent)

    if config.get("mode") == "group_chat" and len(agents) > 2:
        group_chat = GroupChat(
            agents=agents,
            messages=[],
            max_round=config.get("max_rounds", 10)
        )
        manager = GroupChatManager(
            groupchat=group_chat,
            llm_config=config.get("manager_llm_config", agents[0].llm_config)
        )
        return AG2MAS(agents=agents, group_chat=group_chat, manager=manager)
    else:
        return AG2MAS(agents=agents)
