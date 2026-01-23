"""AG2-specific intermediary implementation."""

from typing import Optional, List, Dict

from .base import MASIntermediary
from ..level1_framework.ag2_wrapper import AG2MAS
from ..utils.exceptions import IntermediaryError


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

            # Generate response using agent's LLM
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
