from __future__ import annotations

from trinityguard.level3_safety.attacks.adaptive import (
    ADAPTIVE_COVERAGE,
    ADAPTIVE_PROVENANCE_LEVELS,
    validate_adaptive_provenance,
)
from trinityguard.level3_safety.attacks.registry import ATTACKS
from trinityguard.level3_safety.benchmark.validation import MINSET_RISK_LEVELS


def test_adaptive_coverage_matrix_records_static_fixture_and_live_optional_provenance():
    rows = {row["risk"]: row for row in ADAPTIVE_COVERAGE}

    assert set(rows) == set(ATTACKS)
    for risk in MINSET_RISK_LEVELS:
        row = rows[risk]
        assert row["static_corpus"] is True
        assert row["adaptive_mode"] == "fixture"
        assert row["fixture_coverage"] is True
        assert row["live_llm_optional"] is True
        assert row["provenance_recorded"] is True
        assert row["strong_alignment_provenance"] == "fixture_adaptive"
        assert row["recorded_live_coverage"] is False
        assert row["validated_live_coverage"] is False
        assert set(row["provenance_levels"]) == {
            "static_only",
            "fixture_adaptive",
            "live_llm_optional",
        }


def test_adaptive_provenance_validator_distinguishes_strong_levels():
    assert ADAPTIVE_PROVENANCE_LEVELS == (
        "static_only",
        "fixture_adaptive",
        "recorded_live_adaptive",
        "live_llm_optional",
        "validated_live",
    )

    ok, reasons = validate_adaptive_provenance(
        ADAPTIVE_COVERAGE,
        required_level="recorded_live_adaptive",
        required_risks=list(MINSET_RISK_LEVELS),
    )
    assert ok is False
    assert any(reason.endswith(":recorded_live_adaptive") for reason in reasons)

    upgraded = [
        {
            **row,
            "recorded_live_coverage": True,
            "strong_alignment_provenance": "recorded_live_adaptive",
            "provenance_levels": [
                *row["provenance_levels"],
                "recorded_live_adaptive",
            ],
        }
        if row["risk"] in MINSET_RISK_LEVELS
        else row
        for row in ADAPTIVE_COVERAGE
    ]

    assert validate_adaptive_provenance(
        upgraded,
        required_level="recorded_live_adaptive",
        required_risks=list(MINSET_RISK_LEVELS),
    ) == (True, [])
