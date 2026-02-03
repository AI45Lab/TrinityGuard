"""AG2 (AutoGen) framework wrapper implementation."""

from typing import List, Dict, Any, Optional, Callable
import time

try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager
except ImportError:
    try:
        from pyautogen import ConversableAgent, GroupChat, GroupChatManager
    except ImportError:
        raise ImportError(
            "AG2/AutoGen not installed. Install with: pip install ag2"
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
        self._hooks_installed = False

    def _setup_message_interception(self):
        """Set up message interception for all agents."""
        for agent_name, agent in self._agents.items():
            self._wrap_agent_send(agent, agent_name)

    def _wrap_agent_send(self, agent: ConversableAgent, agent_name: str):
        """Wrap a single agent's send method for interception.

        Args:
            agent: The agent to wrap
            agent_name: Name of the agent (captured for closure)
        """
        original_send = agent.send
        mas_ref = self  # Capture reference to self

        def send_wrapper(message, recipient, request_reply=None, silent=False):
            # Normalize message to dict
            if isinstance(message, str):
                msg_dict = {"content": message}
            else:
                msg_dict = message.copy() if isinstance(message, dict) else {"content": str(message)}

            # Build hook message format with full message info
            hook_msg = {
                "from": agent_name,
                "to": recipient.name if hasattr(recipient, 'name') else str(recipient),
                "content": msg_dict.get("content", ""),
                "tool_calls": msg_dict.get("tool_calls", None),
                "tool_responses": msg_dict.get("tool_responses", None),
                "function_call": msg_dict.get("function_call", None),
                "name": msg_dict.get("name", None),
                "role": msg_dict.get("role", None),
            }

            # Apply message hooks
            modified_hook_msg = mas_ref._apply_message_hooks(hook_msg)

            # Update message with modified content
            if isinstance(message, str):
                modified_message = modified_hook_msg["content"]
            else:
                modified_message = msg_dict
                modified_message["content"] = modified_hook_msg["content"]

            # Log message
            mas_ref._message_history.append({
                "from": agent_name,
                "to": hook_msg["to"],
                "content": modified_hook_msg["content"],
                "timestamp": time.time()
            })

            # Call original send with modified message
            return original_send(modified_message, recipient, request_reply, silent)

        agent.send = send_wrapper

    def register_message_hook(self, hook: Callable[[Dict], Dict]):
        """Register a hook to intercept/modify messages.

        Args:
            hook: Function that takes a message dict and returns modified message dict
        """
        if not self._hooks_installed:
            self._setup_message_interception()
            self._hooks_installed = True
        self._message_hooks.append(hook)

    def get_agents(self) -> List[AgentInfo]:
        """Return list of all agents in the system."""
        agent_infos = []
        for name, agent in self._agents.items():
            agent_infos.append(AgentInfo(
                name=name,
                role=getattr(agent, 'system_message', 'agent')[:50] if hasattr(agent, 'system_message') else 'agent',
                system_prompt=agent.system_message if hasattr(agent, 'system_message') else None,
                tools=[]
            ))
        return agent_infos

    def get_agent(self, name: str) -> ConversableAgent:
        """Get a specific agent by name."""
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found. Available agents: {list(self._agents.keys())}")
        return self._agents[name]

    def run_workflow(self, task: str, **kwargs) -> WorkflowResult:
        """Execute the MAS workflow with given task.

        Args:
            task: Task description
            **kwargs: Additional parameters including:
                - max_rounds: Maximum conversation rounds
                - silent: If True, suppress AG2 native console output (default: False)
        """
        self.logger.log_workflow_start(task, "ag2_group_chat")
        self._message_history.clear()

        try:
            if self._manager and self._group_chat:
                result = self._run_group_chat(task, **kwargs)
            else:
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
        silent = kwargs.get('silent', False)

        # Find user_proxy or use first agent as initiator
        initiator = None
        for agent in self._agents.values():
            if 'proxy' in agent.name.lower() or 'user' in agent.name.lower():
                initiator = agent
                break
        if initiator is None:
            initiator = list(self._agents.values())[0]

        # Initiate group chat with silent mode
        chat_result = initiator.initiate_chat(
            self._manager,
            message=task,
            max_turns=max_rounds,
            silent=silent  # 关闭 AG2 原生输出
        )

        # Extract output from chat history
        output = self._extract_final_output_from_chat(chat_result)

        return WorkflowResult(
            success=True,
            output=output,
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

        silent = kwargs.get('silent', False)
        agents_list = list(self._agents.values())
        initiator = agents_list[0]
        receiver = agents_list[1]

        chat_result = initiator.initiate_chat(
            receiver,
            message=task,
            max_turns=kwargs.get('max_rounds', 10),
            silent=silent  # 关闭 AG2 原生输出
        )

        output = self._extract_final_output_from_chat(chat_result)

        return WorkflowResult(
            success=True,
            output=output,
            messages=self._message_history,
            metadata={
                "mode": "direct",
                "rounds": len(self._message_history)
            }
        )

    def _extract_final_output_from_chat(self, chat_result) -> str:
        """Extract final output from AG2 chat result."""
        # Try to get from chat_result
        if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
            last_msg = chat_result.chat_history[-1]
            return last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

        # Fallback to message history
        if self._message_history:
            return self._message_history[-1].get("content", "")

        return ""

    def get_topology(self) -> Dict:
        """Return the communication topology."""
        if self._group_chat:
            # Check if there are explicit speaker transitions defined
            if hasattr(self._group_chat, 'allowed_or_disallowed_speaker_transitions') and \
               self._group_chat.allowed_or_disallowed_speaker_transitions:
                # Use the explicitly defined transitions
                transitions = self._group_chat.allowed_or_disallowed_speaker_transitions
                topology = {}
                for from_agent, to_agents in transitions.items():
                    from_name = from_agent.name if hasattr(from_agent, 'name') else str(from_agent)
                    to_names = [a.name if hasattr(a, 'name') else str(a) for a in to_agents]
                    topology[from_name] = to_names
                return topology
            else:
                # Default: fully connected (all agents can talk to all others)
                agent_names = list(self._agents.keys())
                return {name: [n for n in agent_names if n != name] for name in agent_names}
        else:
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

        # Optional tool registration per-agent.
        # Supported formats:
        #   "tools": ["skill_security_scan"]
        #   "tools": [{"tool": "skill_security_scan", "name": "...", "description": "..."}]
        tools = agent_config.get("tools") or []
        if tools:
            if not agent_config.get("llm_config"):
                raise ValueError(
                    f"Agent '{agent_config['name']}' has tools configured but llm_config is disabled. "
                    "Tool registration for LLM requires llm_config."
                )

            for tool_entry in tools:
                if isinstance(tool_entry, str):
                    tool_id = tool_entry
                    tool_params = {}
                elif isinstance(tool_entry, dict):
                    tool_id = tool_entry.get("tool") or tool_entry.get("id") or tool_entry.get("name")
                    tool_params = tool_entry
                else:
                    continue

                if tool_id == "skill_security_scan":
                    from .tools.skill_security_scan import attach_skill_security_scan_tool

                    attach_skill_security_scan_tool(
                        assistant_agent=agent,
                        name=tool_params.get("name", "skill_security_scan"),
                        description=tool_params.get("description"),
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
