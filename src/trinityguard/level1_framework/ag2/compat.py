"""AG2 版本兼容层 - 所有 AG2 私有 API 访问集中于此文件。

当 AG2 升级导致内部 API 变化时，只需修改此文件。
其他模块不应直接访问 agent._oai_messages、agent._function_map 等私有属性。
"""

from __future__ import annotations

from typing import Any

from ...utils.exceptions import TrinitySafetyError


class CompatibilityError(TrinitySafetyError):
    """AG2 版本不兼容导致的错误。"""


def get_agent_messages(agent: Any, partner: Any = None) -> list | dict:
    """获取 agent 的消息历史（兼容不同 AG2 版本）。"""
    if hasattr(agent, "_oai_messages"):
        if partner is not None:
            return agent._oai_messages.get(partner, [])
        return agent._oai_messages
    elif hasattr(agent, "chat_messages"):
        if partner is not None:
            return agent.chat_messages.get(partner, [])
        return agent.chat_messages
    raise CompatibilityError(
        f"Cannot access message history for agent '{getattr(agent, 'name', '?')}'. "
        f"Unsupported AG2 version or agent type: {type(agent).__name__}"
    )


def inject_message(agent: Any, partner: Any, message: dict) -> None:
    """向 agent 的消息历史注入一条消息。"""
    messages = get_agent_messages(agent)
    if isinstance(messages, dict):
        messages.setdefault(partner, []).append(message)
    elif isinstance(messages, list):
        messages.append(message)
    else:
        raise CompatibilityError(
            f"Unexpected message store type: {type(messages)} for agent "
            f"'{getattr(agent, 'name', '?')}'"
        )


def get_function_map(agent: Any) -> dict:
    """获取 agent 的工具注册表。"""
    if hasattr(agent, "_function_map"):
        return agent._function_map
    elif hasattr(agent, "tools") and isinstance(agent.tools, (list, dict)):
        if isinstance(agent.tools, dict):
            return agent.tools
        return {getattr(t, "name", str(t)): t for t in agent.tools}
    return {}


def update_system_message(agent: Any, new_message: str) -> bool:
    """更新 agent 的 system message。"""
    if hasattr(agent, "update_system_message"):
        agent.update_system_message(new_message)
        return True
    elif hasattr(agent, "system_message"):
        agent.system_message = new_message
        return True
    return False


def get_system_message(agent: Any) -> str:
    """获取 agent 当前的 system message。"""
    if hasattr(agent, "system_message"):
        return agent.system_message or ""
    return ""
