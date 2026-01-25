"""Monitor agents module."""

from .base import BaseMonitorAgent, Alert

# Re-export from judges module for backward compatibility
from ..judges import LLMJudge, JudgeResult

# L1 Layer - Single Agent Atomic Monitors
from .jailbreak_monitor import JailbreakMonitor
from .prompt_injection_monitor import PromptInjectionMonitor
from .sensitive_disclosure_monitor import SensitiveDisclosureMonitor
from .excessive_agency_monitor import ExcessiveAgencyMonitor
from .code_execution_monitor import CodeExecutionMonitor
from .hallucination_monitor import HallucinationMonitor
from .memory_poisoning_monitor import MemoryPoisoningMonitor
from .tool_misuse_monitor import ToolMisuseMonitor

# L2 Layer - Inter-Agent Communication Monitors
from .message_tampering_monitor import MessageTamperingMonitor
from .malicious_propagation_monitor import MaliciousPropagationMonitor
from .misinformation_amplify_monitor import MisinformationAmplifyMonitor
from .insecure_output_monitor import InsecureOutputMonitor
from .goal_drift_monitor import GoalDriftMonitor
from .identity_spoofing_monitor import IdentitySpoofingMonitor

# L3 Layer - System-Level Emergent Monitors
from .cascading_failures_monitor import CascadingFailuresMonitor
from .sandbox_escape_monitor import SandboxEscapeMonitor
from .insufficient_monitoring_monitor import InsufficientMonitoringMonitor
from .group_hallucination_monitor import GroupHallucinationMonitor
from .malicious_emergence_monitor import MaliciousEmergenceMonitor
from .rogue_agent_monitor import RogueAgentMonitor

__all__ = [
    # Base classes
    "BaseMonitorAgent",
    "Alert",
    "LLMJudge",
    "JudgeResult",
    # L1 Layer
    "JailbreakMonitor",
    "PromptInjectionMonitor",
    "SensitiveDisclosureMonitor",
    "ExcessiveAgencyMonitor",
    "CodeExecutionMonitor",
    "HallucinationMonitor",
    "MemoryPoisoningMonitor",
    "ToolMisuseMonitor",
    # L2 Layer
    "MessageTamperingMonitor",
    "MaliciousPropagationMonitor",
    "MisinformationAmplifyMonitor",
    "InsecureOutputMonitor",
    "GoalDriftMonitor",
    "IdentitySpoofingMonitor",
    # L3 Layer
    "CascadingFailuresMonitor",
    "SandboxEscapeMonitor",
    "InsufficientMonitoringMonitor",
    "GroupHallucinationMonitor",
    "MaliciousEmergenceMonitor",
    "RogueAgentMonitor",
]

# Monitor registry for auto-loading
MONITORS = {
    # L1 Layer
    "jailbreak": JailbreakMonitor,
    "prompt_injection": PromptInjectionMonitor,
    "sensitive_disclosure": SensitiveDisclosureMonitor,
    "excessive_agency": ExcessiveAgencyMonitor,
    "code_execution": CodeExecutionMonitor,
    "hallucination": HallucinationMonitor,
    "memory_poisoning": MemoryPoisoningMonitor,
    "tool_misuse": ToolMisuseMonitor,
    # L2 Layer
    "message_tampering": MessageTamperingMonitor,
    "malicious_propagation": MaliciousPropagationMonitor,
    "misinformation_amplify": MisinformationAmplifyMonitor,
    "insecure_output": InsecureOutputMonitor,
    "goal_drift": GoalDriftMonitor,
    "identity_spoofing": IdentitySpoofingMonitor,
    # L3 Layer
    "cascading_failures": CascadingFailuresMonitor,
    "sandbox_escape": SandboxEscapeMonitor,
    "insufficient_monitoring": InsufficientMonitoringMonitor,
    "group_hallucination": GroupHallucinationMonitor,
    "malicious_emergence": MaliciousEmergenceMonitor,
    "rogue_agent": RogueAgentMonitor,
}
