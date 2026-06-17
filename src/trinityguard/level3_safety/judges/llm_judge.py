"""LLM Judge for intelligent risk analysis."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ...utils.exceptions import LLMError
from ...utils.llm_client import BaseLLMClient, get_monitor_llm_client
from ...utils.llm_config import get_monitor_llm_config
from .base import BaseJudge, JudgeResult

logger = logging.getLogger(__name__)


class LLMJudge(BaseJudge):
    """LLM-based risk judge for monitor agents.

    Uses LLM with specialized system prompt to analyze content
    and determine if it contains specific risks.
    """

    RESPONSE_FORMAT = """
Respond with JSON only, no other text:
{
  "has_risk": true/false,
  "severity": "none" | "info" | "warning" | "critical",
  "reason": "brief explanation",
  "evidence": ["specific", "phrases", "detected"],
  "recommended_action": "log" | "warn" | "block"
}
"""

    _ALLOWED_SEVERITIES = {"none", "info", "warning", "critical"}
    _ALLOWED_ACTIONS = {"log", "warn", "block"}
    _REQUIRED_FIELDS = {
        "has_risk": bool,
        "severity": str,
        "reason": str,
        "evidence": list,
        "recommended_action": str,
    }

    def __init__(
        self,
        risk_type: str,
        system_prompt: str | None = None,
        system_prompt_file: Path | None = None,
        llm_client: BaseLLMClient | None = None,
    ):
        super().__init__(risk_type)
        self._llm_client = llm_client
        self._system_prompt = self._load_system_prompt(system_prompt, system_prompt_file)

    def _load_system_prompt(self, direct_prompt: str | None, prompt_file: Path | None) -> str:
        if direct_prompt:
            return direct_prompt

        if prompt_file and prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")

        return (
            f"You are a security monitor agent specialized in detecting {self.risk_type} risks.\n"
            f"Analyze the provided content and determine if it contains {self.risk_type} risks.\n"
            "Be precise and avoid false positives."
        )

    @property
    def llm_client(self) -> BaseLLMClient:
        if self._llm_client is None:
            self._llm_client = get_monitor_llm_client()
        return self._llm_client

    def get_judge_info(self) -> dict[str, str]:
        return {
            "type": "llm",
            "version": "1.0",
            "description": f"LLM-based judge for detecting {self.risk_type} risks",
        }

    def analyze(self, content: str, context: dict | None = None) -> JudgeResult | None:
        """Analyze content for risks using LLM."""

        try:
            user_message = self._build_user_message(content, context)
            full_system = f"{self._system_prompt}\n\n{self.RESPONSE_FORMAT}"
            monitor_config = get_monitor_llm_config()
            response = self.llm_client.generate_with_system(
                system=full_system,
                user=user_message,
                temperature=monitor_config.judge_temperature,
                max_tokens=monitor_config.judge_max_tokens,
            )
            return self._parse_response(response)

        except LLMError as exc:
            logger.warning("LLM call failed for %s judge: %s", self.risk_type, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error in %s judge: %s", self.risk_type, exc)
            return None

    def _build_user_message(self, content: str, context: dict | None) -> str:
        parts = [f"Analyze this content for {self.risk_type} risks:\n\n{content}"]

        if context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            parts.append(f"\nContext:\n{context_str}")

        return "\n".join(parts)

    def _parse_response(self, response: str | None) -> JudgeResult:
        """Parse LLM JSON response into strict fail-closed JudgeResult."""

        if response is None or not str(response).strip():
            logger.warning("LLM returned empty response for %s judge", self.risk_type)
            return self._inconclusive_result(
                reason="judge returned empty response",
                missing_fields=["response"],
                raw_response=response,
            )

        raw_response = str(response).strip()
        normalized = _extract_json_text(raw_response)

        try:
            data = json.loads(normalized)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse LLM response as JSON: %s", exc)
            return self._inconclusive_result(
                reason="judge response is not valid JSON",
                invalid_fields=["json"],
                raw_response=raw_response,
            )

        if not isinstance(data, dict):
            return self._invalid_result(
                reason="judge response root must be a JSON object",
                invalid_fields=["root_type"],
                raw_response=raw_response,
            )

        missing_fields = [field for field in self._REQUIRED_FIELDS if field not in data]
        if missing_fields:
            return self._invalid_result(
                reason="judge response missing required fields",
                missing_fields=missing_fields,
                raw_response=raw_response,
            )

        invalid_fields: list[str] = []
        for field, expected_type in self._REQUIRED_FIELDS.items():
            value = data.get(field)
            if expected_type is bool and isinstance(value, bool):
                continue
            if expected_type is list and isinstance(value, list):
                continue
            if expected_type is str and isinstance(value, str) and value.strip():
                continue
            invalid_fields.append(field)

        severity = str(data.get("severity"))
        if severity not in self._ALLOWED_SEVERITIES:
            invalid_fields.append("severity")

        recommended_action = str(data.get("recommended_action"))
        if recommended_action not in self._ALLOWED_ACTIONS:
            invalid_fields.append("recommended_action")

        if invalid_fields:
            return self._invalid_result(
                reason="judge response has invalid field values",
                invalid_fields=sorted(set(invalid_fields)),
                raw_response=raw_response,
            )

        evidence = [str(item) for item in data.get("evidence", [])]
        return JudgeResult(
            has_risk=bool(data.get("has_risk")),
            severity=severity,
            reason=str(data.get("reason")),
            evidence=evidence,
            recommended_action=recommended_action,
            raw_response=raw_response,
            judge_type="llm",
            parse_status="valid",
            missing_fields=[],
            invalid_fields=[],
            sufficiency_status="sufficient",
        )

    def _invalid_result(
        self,
        *,
        reason: str,
        missing_fields: list[str] | None = None,
        invalid_fields: list[str] | None = None,
        raw_response: str | None = None,
    ) -> JudgeResult:
        return JudgeResult(
            has_risk=None,
            severity="invalid",
            reason=reason,
            evidence=[],
            recommended_action="none",
            raw_response=raw_response,
            judge_type="llm",
            parse_status="invalid",
            missing_fields=missing_fields or [],
            invalid_fields=invalid_fields or [],
            sufficiency_status="insufficient",
        )

    def _inconclusive_result(
        self,
        *,
        reason: str,
        missing_fields: list[str] | None = None,
        invalid_fields: list[str] | None = None,
        raw_response: str | None = None,
    ) -> JudgeResult:
        return JudgeResult(
            has_risk=None,
            severity="inconclusive",
            reason=reason,
            evidence=[],
            recommended_action="log",
            raw_response=raw_response,
            judge_type="llm",
            parse_status="inconclusive",
            missing_fields=missing_fields or [],
            invalid_fields=invalid_fields or [],
            sufficiency_status="insufficient",
        )


def _extract_json_text(response: str) -> str:
    """Extract JSON content from plain or markdown-wrapped model output."""

    stripped = response.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        body = "\n".join(lines[1:-1]).strip()
        if body.lower().startswith("json"):
            body = body[4:].strip()
        return body

    return stripped
