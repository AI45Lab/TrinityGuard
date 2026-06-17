from __future__ import annotations

from trinityguard.level3_safety.judges.llm_judge import LLMJudge


def _judge() -> LLMJudge:
    return LLMJudge("jailbreak", system_prompt="fixture")


def test_missing_has_risk_is_invalid_not_false():
    result = _judge()._parse_response(
        '{"severity":"none","reason":"x","evidence":[],"recommended_action":"log"}'
    )

    assert result.parse_status == "invalid"
    assert result.has_risk is None
    assert "has_risk" in result.missing_fields


def test_missing_evidence_is_invalid_not_empty_list():
    result = _judge()._parse_response(
        '{"has_risk":false,"severity":"none","reason":"x","recommended_action":"log"}'
    )

    assert result.parse_status == "invalid"
    assert result.has_risk is None
    assert "evidence" in result.missing_fields


def test_invalid_severity_is_invalid_not_none():
    result = _judge()._parse_response(
        '{"has_risk":false,"severity":"low","reason":"x","evidence":[],"recommended_action":"log"}'
    )

    assert result.parse_status == "invalid"
    assert result.has_risk is None
    assert "severity" in result.invalid_fields


def test_invalid_recommended_action_is_invalid_not_log():
    result = _judge()._parse_response(
        '{"has_risk":false,"severity":"none","reason":"x","evidence":[],"recommended_action":"allow"}'
    )

    assert result.parse_status == "invalid"
    assert result.has_risk is None
    assert "recommended_action" in result.invalid_fields


def test_empty_response_is_inconclusive():
    result = _judge()._parse_response("")

    assert result.parse_status == "inconclusive"
    assert result.has_risk is None
    assert result.severity == "inconclusive"


def test_non_json_response_is_inconclusive():
    result = _judge()._parse_response("not-json")

    assert result.parse_status == "inconclusive"
    assert result.has_risk is None


def test_markdown_wrapped_complete_json_parses_strictly():
    result = _judge()._parse_response(
        """```json
{"has_risk":true,"severity":"critical","reason":"x","evidence":["k"],"recommended_action":"block"}
```"""
    )

    assert result.parse_status == "valid"
    assert result.has_risk is True
    assert result.severity == "critical"


def test_complete_valid_json_returns_judge_result_with_diagnostics():
    result = _judge()._parse_response(
        '{"has_risk":false,"severity":"none","reason":"safe","evidence":[],"recommended_action":"log"}'
    )

    assert result.parse_status == "valid"
    assert result.sufficiency_status == "sufficient"
    assert result.missing_fields == []
    assert result.invalid_fields == []
    assert result.has_risk is False
