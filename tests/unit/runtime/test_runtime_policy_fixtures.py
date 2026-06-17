"""Runtime policy fixture loading tests."""

from pathlib import Path

import pytest

from trinityguard.runtime import PolicyConfig
from trinityguard.runtime.config import load_policy_config

FIXTURE_DIR = Path("config/runtime_policies")


def test_runtime_policy_fixtures_load_into_policy_config():
    expected = {
        "runtime-mvp-default.json": {"fail_mode": "open", "enforcement_mode": "enforce"},
        "runtime-mvp-monitor-only.json": {"enforcement_mode": "monitor_only"},
        "runtime-mvp-fail-closed.json": {"fail_mode": "closed"},
        "runtime-mvp-warning-block.json": {"block_severity_threshold": "warning"},
        "runtime-mvp-resilient-local.json": {
            "judge_timeout_seconds": 0.001,
            "circuit_breaker_failure_threshold": 2,
        },
    }

    for filename, assertions in expected.items():
        policy = load_policy_config(FIXTURE_DIR / filename)
        assert isinstance(policy, PolicyConfig)
        for field, value in assertions.items():
            assert getattr(policy, field) == value


def test_load_policy_config_accepts_mapping_and_rejects_unknown_keys():
    policy = load_policy_config({"name": "inline", "fail_mode": "closed"})
    assert policy.name == "inline"
    assert policy.fail_mode == "closed"

    with pytest.raises(ValueError, match="Unknown PolicyConfig keys"):
        load_policy_config({"name": "bad", "unexpected": True})
