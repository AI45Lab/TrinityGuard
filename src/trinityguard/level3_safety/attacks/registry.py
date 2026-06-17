"""攻击注册表 - 手动注册所有 20 个攻击类型。

添加新攻击只需：
1. 在对应 l1/l2/l3 子目录创建模块
2. 在此文件添加一行 import + 一行注册
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseAttack

from .l1.code_execution import CodeExecutionAttack
from .l1.excessive_agency import ExcessiveAgencyAttack
from .l1.hallucination import HallucinationAttack
from .l1.jailbreak import JailbreakAttack
from .l1.memory_poisoning import MemoryPoisoningAttack
from .l1.prompt_injection import PromptInjectionAttack
from .l1.sensitive_disclosure import SensitiveDisclosureAttack
from .l1.tool_misuse import ToolMisuseAttack
from .l2.goal_drift import GoalDriftAttack
from .l2.identity_spoofing import IdentitySpoofingAttack
from .l2.insecure_output import InsecureOutputAttack
from .l2.malicious_propagation import MaliciousPropagationAttack
from .l2.message_tampering import MessageTamperingAttack
from .l2.misinformation_amplify import MisinformationAmplifyAttack
from .l3.cascading_failures import CascadingFailuresAttack
from .l3.group_hallucination import GroupHallucinationAttack
from .l3.insufficient_monitoring import InsufficientMonitoringAttack
from .l3.malicious_emergence import MaliciousEmergenceAttack
from .l3.rogue_agent import RogueAgentAttack
from .l3.sandbox_escape import SandboxEscapeAttack

# Phase 1 最小集合先注册空位，实现后逐步替换

ATTACKS: dict[str, type[BaseAttack] | None] = {
    # L1: 单 Agent 攻击
    "jailbreak": JailbreakAttack,
    "prompt_injection": PromptInjectionAttack,
    "sensitive_disclosure": SensitiveDisclosureAttack,
    "excessive_agency": ExcessiveAgencyAttack,
    "code_execution": CodeExecutionAttack,
    "hallucination": HallucinationAttack,
    "memory_poisoning": MemoryPoisoningAttack,
    "tool_misuse": ToolMisuseAttack,
    # L2: Agent 间攻击
    "message_tampering": MessageTamperingAttack,
    "malicious_propagation": MaliciousPropagationAttack,
    "misinformation_amplify": MisinformationAmplifyAttack,
    "insecure_output": InsecureOutputAttack,
    "goal_drift": GoalDriftAttack,
    "identity_spoofing": IdentitySpoofingAttack,
    # L3: 系统级攻击
    "cascading_failures": CascadingFailuresAttack,
    "sandbox_escape": SandboxEscapeAttack,
    "insufficient_monitoring": InsufficientMonitoringAttack,
    "group_hallucination": GroupHallucinationAttack,
    "malicious_emergence": MaliciousEmergenceAttack,
    "rogue_agent": RogueAgentAttack,
}


def get_attack(name: str) -> type[BaseAttack]:
    """获取攻击类。未实现的攻击会抛出 NotImplementedError。"""
    if name not in ATTACKS:
        raise KeyError(f"Unknown attack: {name}. Available: {list(ATTACKS.keys())}")
    attack_cls = ATTACKS[name]
    if attack_cls is None:
        raise NotImplementedError(
            f"Attack '{name}' is registered but not yet implemented. "
            f"Complete the research in docs/research/attacks/ first."
        )
    return attack_cls


def list_attacks(implemented_only: bool = False) -> list[str]:
    """列出所有已注册的攻击名称。"""
    if implemented_only:
        return [k for k, v in ATTACKS.items() if v is not None]
    return list(ATTACKS.keys())
