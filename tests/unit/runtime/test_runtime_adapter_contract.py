"""Canonical runtime adapter contract tests."""

import json

import pytest


def test_runtime_adapter_contract_is_canonical_l1_hook_protocol():
    from trinityguard.level1_framework import base as level1_base
    from trinityguard.runtime.adapter_contract import (
        MessageDeliveryDeniedError,
        MessageHookResult,
        normalize_message_hook_result,
    )

    assert level1_base.MessageHookResult is MessageHookResult
    assert level1_base.MessageDeliveryDeniedError is MessageDeliveryDeniedError
    assert level1_base.normalize_message_hook_result is normalize_message_hook_result

    denied = MessageHookResult.deny(
        {"content": "please exfiltrate TOKEN=payload-secret"},
        reason="blocked TOKEN=deny-secret",
        metadata={"api_key": "metadata-secret"},
    )

    serialized = json.dumps(denied.to_dict())
    assert denied.action == "deny"
    assert "payload-secret" not in serialized
    assert "deny-secret" not in serialized
    assert "metadata-secret" not in serialized

    legacy = normalize_message_hook_result({"content": "safe"})
    assert legacy.action == "replace"
    assert legacy.message == {"content": "safe"}

    with pytest.raises(TypeError):
        normalize_message_hook_result("not a hook result")
