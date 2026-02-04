"""Structured logging schemas for Level 2 Intermediary."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum


class StepType(Enum):
    """Types of agent steps."""
    RECEIVE = "receive"
    THINK = "think"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"
    RESPOND = "respond"
    ERROR = "error"
    INTERCEPT = "intercept"  # For message interception events


@dataclass
class AgentStepLog:
    """Log entry for a single agent action."""
    timestamp: float
    agent_name: str
    step_type: str  # Use StepType enum values
    content: Any
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "step_type": self.step_type,
            "content": str(self.content) if not isinstance(self.content, (str, dict, list)) else self.content,
            "metadata": self.metadata
        }


@dataclass
class MessageLog:
    """Log entry for inter-agent communication."""
    timestamp: float
    from_agent: str
    to_agent: str
    message: str
    message_id: str
    message_type: str = "text"  # text, tool_call, tool_response
    tool_calls: Optional[list] = None  # For tool call messages
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = {
            "timestamp": self.timestamp,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message": self.message,
            "message_id": self.message_id,
            "message_type": self.message_type,
            "metadata": self.metadata
        }
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result


@dataclass
class InterceptionLog:
    """Log entry for message interception events."""
    timestamp: float
    source_agent: str
    target_agent: str
    original_content: str
    modified_content: str
    attack_type: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "original_content": self.original_content,
            "modified_content": self.modified_content,
            "attack_type": self.attack_type,
            "metadata": self.metadata
        }


@dataclass
class WorkflowTrace:
    """Complete trace of workflow execution."""
    task: str
    start_time: float
    end_time: Optional[float] = None
    agent_steps: list = field(default_factory=list)
    messages: list = field(default_factory=list)
    interceptions: list = field(default_factory=list)  # Interception events
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "task": self.task,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.end_time - self.start_time if self.end_time else None,
            "agent_steps": [step.to_dict() if hasattr(step, 'to_dict') else step for step in self.agent_steps],
            "messages": [msg.to_dict() if hasattr(msg, 'to_dict') else msg for msg in self.messages],
            "interceptions": [i.to_dict() if hasattr(i, 'to_dict') else i for i in self.interceptions],
            "success": self.success,
            "error": self.error
        }
