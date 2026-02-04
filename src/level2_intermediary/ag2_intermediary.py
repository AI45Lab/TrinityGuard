"""AG2-specific intermediary implementation."""

import time
from typing import Optional, List, Dict

from .base import MASIntermediary, RunMode
from ..level1_framework.ag2_wrapper import AG2MAS
from ..utils.exceptions import IntermediaryError
from ..utils.ag2_io_filter import suppress_ag2_tool_output


class AG2Intermediary(MASIntermediary):
    """AG2-specific intermediary implementation."""

    def __init__(self, mas: AG2MAS):
        """Initialize AG2 intermediary.

        Args:
            mas: AG2MAS instance
        """
        if not isinstance(mas, AG2MAS):
            raise IntermediaryError(f"Expected AG2MAS instance, got {type(mas)}")
        super().__init__(mas)
        # Track resource usage
        self._api_call_counts: Dict[str, int] = {}
        self._start_time = time.time()

    def agent_chat(self, agent_name: str, message: str,
                   history: Optional[List] = None) -> str:
        """Direct point-to-point chat with an AG2 agent.

        Args:
            agent_name: Name of agent to chat with
            message: Message to send
            history: Optional conversation history

        Returns:
            Agent's response
        """
        try:
            agent = self.mas.get_agent(agent_name)

            # Generate response using agent's LLM, suppressing AG2 verbose tool output
            with suppress_ag2_tool_output():
                if hasattr(agent, 'generate_reply'):
                    messages = history or []
                    messages.append({"role": "user", "content": message})
                    reply = agent.generate_reply(messages=messages)

                    if isinstance(reply, dict):
                        return reply.get("content", str(reply))
                    return str(reply)
                else:
                    raise IntermediaryError(f"Agent {agent_name} does not support generate_reply")

        except Exception as e:
            raise IntermediaryError(f"Failed to chat with agent {agent_name}: {str(e)}")

    def run_workflow(self, task: str, mode: RunMode = RunMode.BASIC, **kwargs):
        """Execute workflow while suppressing AG2 verbose tool output."""
        with suppress_ag2_tool_output():
            return super().run_workflow(task, mode=mode, **kwargs)

    def simulate_agent_message(self, from_agent: str, to_agent: str,
                               message: str) -> Dict:
        """Simulate a message from one AG2 agent to another.

        Args:
            from_agent: Source agent name
            to_agent: Target agent name
            message: Message content

        Returns:
            Dict with response details
        """
        try:
            sender = self.mas.get_agent(from_agent)
            receiver = self.mas.get_agent(to_agent)

            # Send message
            sender.send(
                message={"content": message},
                recipient=receiver,
                request_reply=True
            )

            # Get response from receiver's last message
            if hasattr(receiver, 'last_message'):
                response = receiver.last_message()
                return {
                    "from": from_agent,
                    "to": to_agent,
                    "message": message,
                    "response": response.get("content", "") if isinstance(response, dict) else str(response),
                    "success": True
                }
            else:
                return {
                    "from": from_agent,
                    "to": to_agent,
                    "message": message,
                    "response": None,
                    "success": False,
                    "error": "Could not retrieve response"
                }

        except Exception as e:
            return {
                "from": from_agent,
                "to": to_agent,
                "message": message,
                "response": None,
                "success": False,
                "error": str(e)
            }

    def inject_tool_call(self, agent_name: str, tool_name: str,
                         params: Dict, mock: bool = False) -> Dict:
        """Simulate or execute a tool call for an AG2 agent.

        Args:
            agent_name: Name of agent to execute tool call
            tool_name: Name of the tool to call
            params: Parameters for the tool call
            mock: If True, simulate the call without real execution

        Returns:
            Dict with tool call result
        """
        try:
            agent = self.mas.get_agent(agent_name)
            self._api_call_counts[agent_name] = self._api_call_counts.get(agent_name, 0) + 1

            if mock:
                # Mock mode: return simulated result
                return {
                    "agent": agent_name,
                    "tool": tool_name,
                    "params": params,
                    "success": True,
                    "result": f"[MOCK] Tool {tool_name} called with {params}",
                    "mock": True
                }

            # Real execution: check if agent has registered tools
            if hasattr(agent, '_function_map') and tool_name in agent._function_map:
                func = agent._function_map[tool_name]
                result = func(**params)
                return {
                    "agent": agent_name,
                    "tool": tool_name,
                    "params": params,
                    "success": True,
                    "result": result,
                    "mock": False
                }
            else:
                return {
                    "agent": agent_name,
                    "tool": tool_name,
                    "params": params,
                    "success": False,
                    "error": f"Tool {tool_name} not found for agent {agent_name}",
                    "mock": False
                }

        except Exception as e:
            return {
                "agent": agent_name,
                "tool": tool_name,
                "params": params,
                "success": False,
                "error": str(e),
                "mock": mock
            }

    def inject_memory(self, agent_name: str, memory_content: str,
                      memory_type: str = "context", mock: bool = False) -> bool:
        """Inject memory/context into an AG2 agent.

        Args:
            agent_name: Name of agent to inject memory into
            memory_content: Content to inject
            memory_type: Type of memory (context, system, etc.)
            mock: If True, simulate without real injection

        Returns:
            True if successful, False otherwise
        """
        try:
            agent = self.mas.get_agent(agent_name)

            if mock:
                # Mock mode: just validate agent exists
                return True

            # Real injection: add to agent's context/memory
            if memory_type == "system":
                # Inject as system message
                if hasattr(agent, 'update_system_message'):
                    current_system = getattr(agent, 'system_message', '')
                    agent.update_system_message(f"{current_system}\n{memory_content}")
                    return True
            elif memory_type == "context":
                # Inject as context message in chat history
                if hasattr(agent, '_oai_messages'):
                    agent._oai_messages.setdefault(agent, []).append({
                        "role": "system",
                        "content": memory_content
                    })
                    return True

            return False

        except Exception as e:
            return False

    def broadcast_message(self, from_agent: str, to_agents: List[str],
                          message: str, mock: bool = False) -> Dict[str, Dict]:
        """Broadcast a message from one AG2 agent to multiple agents.

        Args:
            from_agent: Source agent name
            to_agents: List of target agent names
            message: Message content
            mock: If True, simulate without real broadcast

        Returns:
            Dict mapping agent names to their responses
        """
        results = {}

        for to_agent in to_agents:
            if mock:
                results[to_agent] = {
                    "from": from_agent,
                    "to": to_agent,
                    "message": message,
                    "response": f"[MOCK] Response from {to_agent}",
                    "success": True,
                    "mock": True
                }
            else:
                # Real broadcast using simulate_agent_message
                result = self.simulate_agent_message(from_agent, to_agent, message)
                result["mock"] = False
                results[to_agent] = result

        return results

    def spoof_identity(self, real_agent: str, spoofed_agent: str,
                       to_agent: str, message: str, mock: bool = False) -> Dict:
        """Send a message with spoofed identity for testing.

        Args:
            real_agent: Actual sender agent name
            spoofed_agent: Claimed sender agent name
            to_agent: Target agent name
            message: Message content
            mock: If True, simulate without real message

        Returns:
            Dict with response and detection results
        """
        try:
            if mock:
                return {
                    "real_sender": real_agent,
                    "spoofed_sender": spoofed_agent,
                    "to": to_agent,
                    "message": message,
                    "success": True,
                    "mock": True,
                    "detected": False
                }

            # Real spoofing: send message claiming to be from spoofed_agent
            receiver = self.mas.get_agent(to_agent)

            # Craft spoofed message
            spoofed_message = {
                "content": message,
                "name": spoofed_agent,  # Claim to be spoofed_agent
                "role": "assistant"
            }

            # Try to inject the spoofed message
            if hasattr(receiver, '_oai_messages'):
                # Add to receiver's chat history as if from spoofed_agent
                spoofed_sender = self.mas.get_agent(spoofed_agent)
                receiver._oai_messages.setdefault(spoofed_sender, []).append(spoofed_message)

            # Get response from receiver
            if hasattr(receiver, 'generate_reply'):
                messages = [{"role": "user", "content": message}]
                reply = receiver.generate_reply(messages=messages)
                response_content = reply.get("content", str(reply)) if isinstance(reply, dict) else str(reply)
            else:
                response_content = None

            return {
                "real_sender": real_agent,
                "spoofed_sender": spoofed_agent,
                "to": to_agent,
                "message": message,
                "response": response_content,
                "success": True,
                "mock": False,
                "detected": False  # Detection logic would be in monitor
            }

        except Exception as e:
            return {
                "real_sender": real_agent,
                "spoofed_sender": spoofed_agent,
                "to": to_agent,
                "message": message,
                "response": None,
                "success": False,
                "error": str(e),
                "mock": mock,
                "detected": False
            }

    def get_resource_usage(self, agent_name: Optional[str] = None) -> Dict:
        """Get resource usage statistics for AG2 agents.

        Args:
            agent_name: Specific agent name, or None for all agents

        Returns:
            Dict with resource usage (cpu, memory, api_calls, etc.)
        """
        import psutil
        import os

        # Get current process stats
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()

        elapsed_time = time.time() - self._start_time

        if agent_name:
            # Get stats for specific agent
            return {
                "agent": agent_name,
                "api_calls": self._api_call_counts.get(agent_name, 0),
                "elapsed_time": elapsed_time,
                "process_memory_mb": memory_info.rss / (1024 * 1024),
                "cpu_percent": cpu_percent
            }
        else:
            # Get aggregate stats for all agents
            agents = self.mas.get_agents()
            agent_stats = {}
            for agent in agents:
                agent_stats[agent.name] = {
                    "api_calls": self._api_call_counts.get(agent.name, 0)
                }

            return {
                "total_api_calls": sum(self._api_call_counts.values()),
                "elapsed_time": elapsed_time,
                "process_memory_mb": memory_info.rss / (1024 * 1024),
                "cpu_percent": cpu_percent,
                "agents": agent_stats
            }
