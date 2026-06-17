from __future__ import annotations

from trinityguard.level3_safety.attacks.adaptive import ADAPTIVE_COVERAGE, generate_adaptive_cases
from trinityguard.level3_safety.attacks.base import AttackCase
from trinityguard.level3_safety.attacks.registry import ATTACKS


def test_adaptive_coverage_matrix_lists_all_risks_with_static_retained():
    assert set(ATTACKS).issubset({row["risk"] for row in ADAPTIVE_COVERAGE})
    assert all(row["static_corpus"] for row in ADAPTIVE_COVERAGE)
    assert all(row["fixture_coverage"] for row in ADAPTIVE_COVERAGE)


def test_fixture_adaptive_generation_is_deterministic_and_records_provenance():
    seed = AttackCase("seed", "Test prompt", "refuse", "warning", {"source": "unit"})

    first = generate_adaptive_cases("jailbreak", "l1", [seed], max_cases=2, mode="fixture")
    second = generate_adaptive_cases("jailbreak", "l1", [seed], max_cases=2, mode="fixture")

    assert [case.to_dict() if hasattr(case, "to_dict") else case.__dict__ for case in first] == [
        case.to_dict() if hasattr(case, "to_dict") else case.__dict__ for case in second
    ]
    assert len(first) == 2
    assert first[0].metadata["provenance"] == "adaptive_fixture"
    assert "jailbreak" in first[0].attack_input.lower()


def test_live_llm_mode_is_opt_in_and_skips_without_generator():
    seed = AttackCase("seed", "Test prompt", "refuse", "warning")

    assert generate_adaptive_cases("jailbreak", "l1", [seed], mode="live_llm") == []
