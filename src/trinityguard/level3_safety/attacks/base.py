"""Base interfaces for Level 3 attack generation.

The v2 architecture keeps attack execution separate from judging.  Attack
classes load declared cases, send attack inputs to a target MAS through the
intermediary, and return raw responses for later evaluation by judges.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import yaml


@dataclass(frozen=True)
class AttackCase:
    """Single declared attack case loaded from ``datasets/``."""

    name: str
    attack_input: str
    expected_behavior: str
    severity: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def input(self) -> str:
        """Legacy alias for older risk-test code."""
        return self.attack_input


@dataclass
class AttackCaseResult:
    """Raw result of executing one attack case.

    ``execution_success`` describes whether the framework call completed.  It
    is not a safety verdict; judge code evaluates ``raw_response`` later.
    """

    attack_type: str
    case_name: str
    attack_input: str
    target_agent: str | None
    raw_response: str | None
    execution_success: bool
    expected_behavior: str
    severity: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the case result to a JSON-serializable dictionary."""
        data: dict[str, Any] = {
            "attack_type": self.attack_type,
            "case_name": self.case_name,
            "attack_input": self.attack_input,
            "target_agent": self.target_agent,
            "raw_response": self.raw_response,
            "execution_success": self.execution_success,
            "expected_behavior": self.expected_behavior,
            "severity": self.severity,
            "metadata": self.metadata,
        }
        if self.error:
            data["error"] = self.error
        return data


@dataclass
class AttackRunResult:
    """Aggregate result for one attack run across one or more cases."""

    attack_type: str
    level: str
    results: list[AttackCaseResult]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_cases(self) -> int:
        """Number of cases executed."""
        return len(self.results)

    @property
    def failed_executions(self) -> int:
        """Number of cases that crashed or failed to execute."""
        return sum(1 for result in self.results if not result.execution_success)

    def to_dict(self) -> dict[str, Any]:
        """Convert the run result to a JSON-serializable dictionary."""
        return {
            "attack_type": self.attack_type,
            "level": self.level,
            "total_cases": self.total_cases,
            "failed_executions": self.failed_executions,
            "results": [result.to_dict() for result in self.results],
            "metadata": self.metadata,
        }


class BaseAttack(ABC):
    """Base class for attack generators.

    Subclasses normally set ``risk_type`` and ``level`` and can override
    ``run_case`` when the attack needs something other than direct L1
    ``agent_chat`` execution.
    """

    risk_type: ClassVar[str]
    level: ClassVar[str]

    def __init__(self, dataset_path: str | Path | None = None):
        self.dataset_path = Path(dataset_path) if dataset_path else self.default_dataset_path()

    @classmethod
    def default_dataset_path(cls) -> Path:
        """Return the default static-case YAML path for this attack."""
        project_root = Path(__file__).resolve().parents[4]
        return project_root / "datasets" / cls.level / cls.risk_type / "static_cases.yaml"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for this attack implementation."""
        return {
            "risk_type": self.risk_type,
            "level": self.level,
            "dataset_path": str(self.dataset_path),
        }

    def load_cases(self, path: str | Path | None = None) -> list[AttackCase]:
        """Load static attack cases from a YAML dataset file."""
        case_path = Path(path) if path else self.dataset_path
        with case_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        raw_cases = data.get("test_cases")
        if not isinstance(raw_cases, list):
            raise ValueError(f"Attack dataset {case_path} must contain a 'test_cases' list")

        return [self._case_from_mapping(raw_case, case_path) for raw_case in raw_cases]

    def run(
        self,
        intermediary: Any,
        cases: list[AttackCase] | None = None,
        target_agent: str | None = None,
        **kwargs: Any,
    ) -> AttackRunResult:
        """Execute attack cases and return raw responses without judging them."""
        selected_cases = cases if cases is not None else self.load_cases()
        selected_agent = target_agent or self.select_target_agent(intermediary)
        results: list[AttackCaseResult] = []

        for case in selected_cases:
            try:
                results.append(self.run_case(intermediary, case, selected_agent, **kwargs))
            except Exception as exc:
                results.append(
                    AttackCaseResult(
                        attack_type=self.risk_type,
                        case_name=case.name,
                        attack_input=case.attack_input,
                        target_agent=selected_agent,
                        raw_response=None,
                        execution_success=False,
                        expected_behavior=case.expected_behavior,
                        severity=case.severity,
                        error=str(exc),
                        metadata=case.metadata,
                    )
                )

        return AttackRunResult(
            attack_type=self.risk_type,
            level=self.level,
            results=results,
            metadata={"dataset_path": str(self.dataset_path)},
        )

    def run_case(
        self,
        intermediary: Any,
        case: AttackCase,
        target_agent: str,
        **kwargs: Any,
    ) -> AttackCaseResult:
        """Run one direct prompt attack case against one target agent."""
        response = intermediary.agent_chat(
            target_agent,
            case.attack_input,
            history=kwargs.get("history"),
        )
        return AttackCaseResult(
            attack_type=self.risk_type,
            case_name=case.name,
            attack_input=case.attack_input,
            target_agent=target_agent,
            raw_response=response,
            execution_success=True,
            expected_behavior=case.expected_behavior,
            severity=case.severity,
            metadata=case.metadata,
        )

    def select_target_agent(self, intermediary: Any) -> str:
        """Select the default target agent for L1 direct-prompt attacks."""
        agents = intermediary.mas.get_agents()
        if not agents:
            raise ValueError("Cannot run attack: target MAS has no agents")
        return agents[0].name

    def _case_from_mapping(self, raw_case: Any, path: Path) -> AttackCase:
        if not isinstance(raw_case, dict):
            raise ValueError(f"Attack dataset {path} contains a non-mapping case: {raw_case!r}")

        required = ("name", "input", "expected_behavior", "severity")
        missing = [key for key in required if key not in raw_case]
        if missing:
            raise ValueError(f"Attack dataset {path} case is missing keys: {missing}")

        metadata = raw_case.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValueError(f"Attack dataset {path} case {raw_case['name']} has invalid metadata")

        return AttackCase(
            name=str(raw_case["name"]),
            attack_input=str(raw_case["input"]),
            expected_behavior=str(raw_case["expected_behavior"]),
            severity=str(raw_case["severity"]),
            metadata=metadata,
        )


# Compatibility aliases for the partially migrated v1 risk-test surface.
TestCase = AttackCase
TestResult = AttackRunResult
BaseRiskTest = BaseAttack
