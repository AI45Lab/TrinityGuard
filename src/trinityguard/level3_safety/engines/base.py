"""攻击引擎基类。

攻击引擎是可复用的攻击策略（如 PAIR、TAP、GCG 等），
与具体的风险类型无关，可被不同攻击类型共享。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AttackResult:
    """单次攻击引擎运行的结果。"""

    success: bool
    prompt: str
    response: str
    iterations: int = 0
    history: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseEngine(ABC):
    """攻击引擎基类。"""

    @abstractmethod
    def run(
        self,
        target_fn: Callable[[str], str],
        goal: str,
        judge_fn: Callable[[str], bool],
        **kwargs: Any,
    ) -> AttackResult:
        """运行攻击引擎。

        Args:
            target_fn: 目标函数，接收 prompt 返回 response
            goal: 攻击目标描述
            judge_fn: 内联 judge，判断单次攻击是否成功（用于迭代优化）
                      注意：这是攻击循环内的快速判断，最终评判由独立 Judge 完成
            **kwargs: 引擎特定参数

        Returns:
            AttackResult: 攻击结果
        """
