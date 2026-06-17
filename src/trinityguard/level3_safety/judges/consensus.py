"""多 Judge 共识机制 - 多次采样 + 多数投票。

通过多次独立调用 LLM Judge 并取多数投票来提高评判一致性和可靠性。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base import BaseJudge, JudgeResult

if TYPE_CHECKING:
    from .llm_judge import LLMJudge

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ["none", "info", "warning", "critical"]


class ConsensusJudge(BaseJudge):
    """多次采样 + 多数投票的 Judge。"""

    def __init__(self, base_judge: LLMJudge, n_samples: int = 3):
        self.base_judge = base_judge
        self.n_samples = n_samples

    def analyze(self, content: str, context: dict | None = None) -> JudgeResult | None:
        results: list[JudgeResult] = []
        for i in range(self.n_samples):
            r = self.base_judge.analyze(content, context)
            if r is not None:
                results.append(r)

        if not results:
            logger.warning(
                "ConsensusJudge: all %d samples failed, returning None", self.n_samples
            )
            return None

        # 多数投票决定 has_risk
        risk_votes = [r.has_risk for r in results]
        has_risk = sum(risk_votes) > len(risk_votes) / 2

        # severity 只从与多数一致的结果中取，避免 has_risk=False + severity=critical 的矛盾
        majority_results = [r for r in results if r.has_risk == has_risk]
        representative = max(
            majority_results,
            key=lambda r: SEVERITY_ORDER.index(r.severity)
            if r.severity in SEVERITY_ORDER
            else 0,
        )

        return JudgeResult(
            has_risk=has_risk,
            severity=representative.severity,
            reason=(
                f"Consensus ({sum(risk_votes)}/{len(results)} voted risk): "
                f"{representative.reason}"
            ),
            evidence=[e for r in majority_results for e in r.evidence],
            recommended_action=representative.recommended_action,
        )
