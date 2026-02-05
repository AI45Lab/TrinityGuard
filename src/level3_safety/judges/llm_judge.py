"""LLM Judge for intelligent risk analysis."""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .base import BaseJudge, JudgeResult
from ...utils.llm_client import get_monitor_llm_client, BaseLLMClient
from ...utils.llm_config import get_monitor_llm_config
from ...utils.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMJudge(BaseJudge):
    """LLM-based risk judge for monitor agents.

    Uses LLM with specialized system prompt to analyze content
    and determine if it contains specific risks.
    """

    # JSON response format instruction
    RESPONSE_FORMAT = '''
Respond with JSON only, no other text:
{
  "has_risk": true/false,
  "severity": "none" | "info" | "warning" | "critical",
  "reason": "brief explanation",
  "evidence": ["specific", "phrases", "detected"],
  "recommended_action": "log" | "warn" | "block"
}
'''

    def __init__(
        self,
        risk_type: str,
        system_prompt: Optional[str] = None,
        system_prompt_file: Optional[Path] = None,
        llm_client: Optional[BaseLLMClient] = None
    ):
        """Initialize LLM Judge.

        Args:
            risk_type: Type of risk this judge detects
            system_prompt: Direct system prompt string
            system_prompt_file: Path to system_prompt.txt file
            llm_client: Optional pre-configured LLM client
        """
        super().__init__(risk_type)
        self._llm_client = llm_client
        self._system_prompt = self._load_system_prompt(system_prompt, system_prompt_file)

    def _load_system_prompt(
        self,
        direct_prompt: Optional[str],
        prompt_file: Optional[Path]
    ) -> str:
        """Load system prompt from string or file."""
        if direct_prompt:
            return direct_prompt

        if prompt_file and prompt_file.exists():
            return prompt_file.read_text(encoding='utf-8')

        # Default generic prompt
        return f'''You are a security monitor agent specialized in detecting {self.risk_type} risks.
Analyze the provided content and determine if it contains {self.risk_type} risks.
Be precise and avoid false positives.'''

    @property
    def llm_client(self) -> BaseLLMClient:
        """Lazy load LLM client with monitor config."""
        if self._llm_client is None:
            self._llm_client = get_monitor_llm_client()
        return self._llm_client

    def get_judge_info(self) -> Dict[str, str]:
        """Return judge metadata.

        Returns:
            Dict with keys: type, version, description
        """
        return {
            "type": "llm",
            "version": "1.0",
            "description": f"LLM-based judge for detecting {self.risk_type} risks"
        }

    def analyze(self, content: str, context: Optional[Dict] = None) -> Optional[JudgeResult]:
        """Analyze content for risks using LLM.

        Args:
            content: Content to analyze
            context: Optional additional context (agent name, step type, etc.)

        Returns:
            JudgeResult if analysis successful, None if LLM call fails
        """
        try:
            # Build user message
            user_message = self._build_user_message(content, context)

            # Build full system prompt with response format
            full_system = f"{self._system_prompt}\n\n{self.RESPONSE_FORMAT}"

            # Use monitor config settings
            monitor_config = get_monitor_llm_config()

            # Call LLM
            response = self.llm_client.generate_with_system(
                system=full_system,
                user=user_message,
                temperature=monitor_config.judge_temperature,
                max_tokens=monitor_config.judge_max_tokens
            )

            # Parse response
            return self._parse_response(response)

        except LLMError as e:
            # LLM call failed, return None to trigger fallback
            logger.warning("LLM call failed for %s judge: %s", self.risk_type, e)
            return None
        except Exception as e:
            # Unexpected error, return None
            logger.exception("Unexpected error in %s judge: %s", self.risk_type, e)
            return None

    def _build_user_message(self, content: str, context: Optional[Dict]) -> str:
        """Build user message for LLM."""
        parts = [f"Analyze this content for {self.risk_type} risks:\n\n{content}"]

        if context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            parts.append(f"\nContext:\n{context_str}")

        return "\n".join(parts)

    def _parse_response(self, response: str) -> Optional[JudgeResult]:
        """Parse LLM JSON response into JudgeResult."""
        # Allowed values for validation
        ALLOWED_SEVERITIES = ["none", "info", "warning", "critical"]
        ALLOWED_ACTIONS = ["log", "warn", "block"]

        try:
            # Check if response is None or empty
            if response is None or not response:
                logger.warning("LLM returned empty response for %s judge", self.risk_type)
                return None

            # Try to extract JSON from response
            response = response.strip()

            # Handle markdown code blocks
            if response.startswith("```"):
                lines = response.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```") and not in_json:
                        in_json = True
                        continue
                    elif line.startswith("```") and in_json:
                        break
                    elif in_json:
                        json_lines.append(line)
                response = "\n".join(json_lines)

            data = json.loads(response)

            # Validate and normalize severity
            severity = data.get("severity", "none")
            if severity not in ALLOWED_SEVERITIES:
                logger.warning("Invalid severity '%s', defaulting to 'none'", severity)
                severity = "none"

            # Validate and normalize recommended_action
            recommended_action = data.get("recommended_action", "log")
            if recommended_action not in ALLOWED_ACTIONS:
                logger.warning("Invalid recommended_action '%s', defaulting to 'log'", recommended_action)
                recommended_action = "log"

            return JudgeResult(
                has_risk=data.get("has_risk", False),
                severity=severity,
                reason=data.get("reason", ""),
                evidence=data.get("evidence", []),
                recommended_action=recommended_action,
                raw_response=response,
                judge_type="llm"
            )
        except json.JSONDecodeError as e:
            # Failed to parse, return None
            logger.warning("Failed to parse LLM response as JSON: %s", e)
            return None
