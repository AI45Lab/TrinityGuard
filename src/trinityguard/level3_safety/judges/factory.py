"""Judge Factory for creating judge instances."""

import logging
from pathlib import Path
from typing import Any

import yaml

from .base import BaseJudge

logger = logging.getLogger(__name__)


class JudgeFactory:
    """Factory for creating and managing judge instances."""

    _registry: dict[str, type[BaseJudge]] = {}

    @classmethod
    def register(cls, judge_type: str, judge_class: type[BaseJudge]):
        """Register a judge type.

        Args:
            judge_type: Type identifier (e.g., "llm", "specialized_api")
            judge_class: Judge class to register
        """
        cls._registry[judge_type] = judge_class
        logger.debug("Registered judge type: %s", judge_type)

    @classmethod
    def list_types(cls) -> list:
        """List all registered judge types."""
        return list(cls._registry.keys())

    @classmethod
    def create(
        cls,
        risk_type: str,
        judge_type: str = "llm",
        system_prompt: str | None = None,
        system_prompt_file: Path | None = None,
        **kwargs: Any
    ) -> BaseJudge:
        """Create a judge instance.

        Args:
            risk_type: Risk type this judge detects
            judge_type: Type of judge to create (default: "llm")
            system_prompt: Direct system prompt string
            system_prompt_file: Path to system_prompt.txt
            **kwargs: Additional arguments for specific judge types

        Returns:
            BaseJudge instance

        Raises:
            ValueError: If judge_type is not registered
        """
        if judge_type not in cls._registry:
            available = ", ".join(cls._registry.keys()) or "none"
            raise ValueError(f"Unknown judge type: {judge_type}. Available: {available}")

        judge_class = cls._registry[judge_type]
        return judge_class(
            risk_type=risk_type,
            system_prompt=system_prompt,
            system_prompt_file=system_prompt_file,
            **kwargs
        )

    @classmethod
    def create_for_risk(
        cls,
        risk_type: str,
        judge_type: str = "llm",
        **kwargs: Any
    ) -> BaseJudge:
        """Create a judge with auto-loaded system_prompt from judges/prompts YAML.

        Looks for judges/prompts/{risk_type}.yaml, parses the YAML structure and
        extracts the ``system_prompt`` field to pass to the judge.

        YAML structure expected:
            risk_type: jailbreak
            system_prompt: |
              ...
            few_shot_examples:
              - input: "..."
                expected: {has_risk: true, ...}
            severity_criteria:
              critical: "..."

        Args:
            risk_type: Risk type (e.g., "jailbreak", "prompt_injection")
            judge_type: Type of judge to create
            **kwargs: Additional arguments

        Returns:
            BaseJudge instance with system_prompt loaded from YAML prompt file
        """
        prompts_dir = Path(__file__).parent / "prompts"
        prompt_file = prompts_dir / f"{risk_type}.yaml"

        if prompt_file.exists():
            logger.debug("Loading system_prompt from %s", prompt_file)
            try:
                with open(prompt_file, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                system_prompt = data.get("system_prompt", "")
                return cls.create(
                    risk_type=risk_type,
                    judge_type=judge_type,
                    system_prompt=system_prompt,
                    **kwargs
                )
            except Exception as exc:
                logger.warning("Failed to parse %s: %s. Using default prompt.", prompt_file, exc)
        else:
            logger.warning("No prompt YAML found for %s at %s, using default", risk_type, prompt_file)

        return cls.create(
            risk_type=risk_type,
            judge_type=judge_type,
            **kwargs
        )


def _register_default_judges():
    """Register built-in judge types."""
    from .llm_judge import LLMJudge
    JudgeFactory.register("llm", LLMJudge)


# Auto-register on module import
_register_default_judges()
