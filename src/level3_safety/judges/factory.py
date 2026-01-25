"""Judge Factory for creating judge instances."""

import logging
from pathlib import Path
from typing import Dict, Type, Optional, Any

from .base import BaseJudge

logger = logging.getLogger(__name__)


class JudgeFactory:
    """Factory for creating and managing judge instances."""

    _registry: Dict[str, Type[BaseJudge]] = {}

    @classmethod
    def register(cls, judge_type: str, judge_class: Type[BaseJudge]):
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
        system_prompt: Optional[str] = None,
        system_prompt_file: Optional[Path] = None,
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
        """Create a judge with auto-loaded system_prompt from monitor directory.

        Args:
            risk_type: Risk type (e.g., "jailbreak", "prompt_injection")
            judge_type: Type of judge to create
            **kwargs: Additional arguments

        Returns:
            BaseJudge instance with system_prompt loaded from corresponding monitor
        """
        monitor_dir = Path(__file__).parent.parent / "monitor_agents" / f"{risk_type}_monitor"
        prompt_file = monitor_dir / "system_prompt.txt"

        if prompt_file.exists():
            logger.debug("Loading system_prompt from %s", prompt_file)
            return cls.create(
                risk_type=risk_type,
                judge_type=judge_type,
                system_prompt_file=prompt_file,
                **kwargs
            )
        else:
            logger.warning("No system_prompt.txt found for %s, using default", risk_type)
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
