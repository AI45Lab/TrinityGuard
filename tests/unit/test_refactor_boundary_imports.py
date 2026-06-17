"""Refactor-mainline boundary checks for legacy compatibility imports."""

from pathlib import Path

SRC = Path("src/trinityguard")
LEGACY_IMPORTS = [
    "level1_framework.ag2_wrapper",
    "utils.ag2_io_filter",
]
ALLOWED = {
    Path("src/trinityguard/level1_framework/ag2_wrapper.py"),
    Path("src/trinityguard/utils/ag2_io_filter.py"),
}


def test_internal_code_uses_canonical_ag2_imports_not_legacy_shims():
    offenders = []
    for path in SRC.rglob("*.py"):
        if path in ALLOWED:
            continue
        text = path.read_text()
        for legacy in LEGACY_IMPORTS:
            if legacy in text:
                offenders.append(f"{path}:{legacy}")

    assert offenders == []


def test_legacy_shims_are_marked_as_deprecated_compatibility_exports():
    for path in ALLOWED:
        text = path.read_text().lower()
        assert "compatibility" in text
        assert "deprecated" in text


def test_level1_hook_protocol_is_marked_as_runtime_contract_compatibility_export():
    text = Path("src/trinityguard/level1_framework/base.py").read_text().lower()

    assert "runtime.adapter_contract" in text
    assert "compatibility re-export" in text


def test_internal_code_imports_hook_protocol_from_runtime_adapter_contract():
    protocol_names = (
        "MessageHookResult",
        "MessageDeliveryDeniedError",
        "normalize_message_hook_result",
    )
    allowed_paths = {
        Path("src/trinityguard/level1_framework/base.py"),
        Path("src/trinityguard/runtime/adapter_contract.py"),
    }
    offenders = []

    for path in SRC.rglob("*.py"):
        if path in allowed_paths:
            continue
        lines = path.read_text().splitlines()
        for line in lines:
            if "level1_framework.base import" not in line and "from ..base import" not in line:
                continue
            for name in protocol_names:
                if name in line:
                    offenders.append(f"{path}:{name}")

    assert offenders == []


def test_safety_mas_uses_runtime_protected_workflow_helper_not_runner_constructor():
    text = Path("src/trinityguard/level3_safety/safety_mas.py").read_text()

    assert "run_runtime_protected_workflow" in text
    assert "RuntimeProtectedMonitoredRunner" not in text


def test_safety_mas_uses_level2_monitored_helper_not_runmode_details():
    text = Path("src/trinityguard/level3_safety/safety_mas.py").read_text()

    assert "run_monitored_intermediary_workflow" in text
    assert "RunMode" not in text
    assert "intermediary.run_workflow" not in text


def test_safety_mas_uses_level2_suppression_helper_not_ag2_io_filter():
    safety_mas_text = Path("src/trinityguard/level3_safety/safety_mas.py").read_text()
    orchestration_text = Path("src/trinityguard/level3_safety/test_orchestration.py").read_text()

    assert "run_with_suppressed_ag2_output" in orchestration_text
    assert "run_with_suppressed_ag2_output" not in safety_mas_text
    assert "suppress_ag2_tool_output" not in safety_mas_text
    assert "suppress_ag2_tool_output" not in orchestration_text


def test_safety_mas_uses_level2_intermediary_factory_not_concrete_intermediaries():
    text = Path("src/trinityguard/level3_safety/safety_mas.py").read_text()

    assert "create_intermediary" in text
    assert "AG2Intermediary" not in text
    assert "LocalMASIntermediary" not in text
    assert "_create_intermediary" not in text


def test_safety_mas_does_not_import_ag2_or_concrete_intermediary_modules():
    lines = Path("src/trinityguard/level3_safety/safety_mas.py").read_text().splitlines()
    forbidden_import_fragments = (
        "level1_framework.ag2",
        "level2_intermediary.ag2_intermediary",
        "level2_intermediary.local_intermediary",
    )
    offenders = [
        line
        for line in lines
        if line.startswith(("from ", "import "))
        and any(fragment in line for fragment in forbidden_import_fragments)
    ]

    assert offenders == []
