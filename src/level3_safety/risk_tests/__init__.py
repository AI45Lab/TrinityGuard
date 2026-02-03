"""Risk tests module."""

from .base import BaseRiskTest, TestCase, TestResult
from .l2_base import L2AgentWrapperTest

# L1 Layer - Single Agent Atomic Risks
from .l1_jailbreak import JailbreakTest
from .l1_prompt_injection import PromptInjectionTest
from .l1_sensitive_disclosure import SensitiveDisclosureTest
from .l1_excessive_agency import ExcessiveAgencyTest
from .l1_code_execution import CodeExecutionTest
from .l1_hallucination import HallucinationTest
from .l1_memory_poisoning import MemoryPoisoningTest
from .l1_tool_misuse import ToolMisuseTest

# L2 Layer - Inter-Agent Communication Risks
from .l2_message_tampering import MessageTamperingTest
from .l2_malicious_propagation import MaliciousPropagationTest
from .l2_misinformation_amplify import MisinformationAmplifyTest
from .l2_insecure_output import InsecureOutputTest
from .l2_goal_drift import GoalDriftTest
from .l2_identity_spoofing import IdentitySpoofingTest

# L3 Layer - System-Level Emergent Risks
from .l3_cascading_failures import CascadingFailuresTest
from .l3_sandbox_escape import SandboxEscapeTest
from .l3_insufficient_monitoring import InsufficientMonitoringTest
from .l3_group_hallucination import GroupHallucinationTest
from .l3_malicious_emergence import MaliciousEmergenceTest
from .l3_rogue_agent import RogueAgentTest

__all__ = [
    # Base classes
    "BaseRiskTest",
    "TestCase",
    "TestResult",
    "L2AgentWrapperTest",
    # L1 Layer
    "JailbreakTest",
    "PromptInjectionTest",
    "SensitiveDisclosureTest",
    "ExcessiveAgencyTest",
    "CodeExecutionTest",
    "HallucinationTest",
    "MemoryPoisoningTest",
    "ToolMisuseTest",
    # L2 Layer
    "MessageTamperingTest",
    "MaliciousPropagationTest",
    "MisinformationAmplifyTest",
    "InsecureOutputTest",
    "GoalDriftTest",
    "IdentitySpoofingTest",
    # L3 Layer
    "CascadingFailuresTest",
    "SandboxEscapeTest",
    "InsufficientMonitoringTest",
    "GroupHallucinationTest",
    "MaliciousEmergenceTest",
    "RogueAgentTest",
]

# Risk test registry for auto-loading
RISK_TESTS = {
    # L1 Layer
    "jailbreak": JailbreakTest,
    "prompt_injection": PromptInjectionTest,
    "sensitive_disclosure": SensitiveDisclosureTest,
    "excessive_agency": ExcessiveAgencyTest,
    "code_execution": CodeExecutionTest,
    "hallucination": HallucinationTest,
    "memory_poisoning": MemoryPoisoningTest,
    "tool_misuse": ToolMisuseTest,
    # L2 Layer
    "message_tampering": MessageTamperingTest,
    "malicious_propagation": MaliciousPropagationTest,
    "misinformation_amplify": MisinformationAmplifyTest,
    "insecure_output": InsecureOutputTest,
    "goal_drift": GoalDriftTest,
    "identity_spoofing": IdentitySpoofingTest,
    # L3 Layer
    "cascading_failures": CascadingFailuresTest,
    "sandbox_escape": SandboxEscapeTest,
    "insufficient_monitoring": InsufficientMonitoringTest,
    "group_hallucination": GroupHallucinationTest,
    "malicious_emergence": MaliciousEmergenceTest,
    "rogue_agent": RogueAgentTest,
}
