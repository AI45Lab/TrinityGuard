"""Public API and compatibility-surface contract tests."""

from pathlib import Path


def test_top_level_exports_local_research_facade_without_ag2_import_requirement():
    import trinityguard as tg
    from trinityguard.level1_framework.base import BaseMAS, WorkflowResult
    from trinityguard.level3_safety.safety_mas import Safety_MAS
    from trinityguard.level3_safety.safety_mas_types import MonitorSelectionMode
    from trinityguard.runtime import RuntimeProtector

    assert tg.Safety_MAS is Safety_MAS
    assert tg.MonitorSelectionMode is MonitorSelectionMode
    assert tg.BaseMAS is BaseMAS
    assert tg.WorkflowResult is WorkflowResult
    assert tg.RuntimeProtector is RuntimeProtector
    assert "Safety_MAS" in tg.__all__
    assert "AG2MAS" not in tg.__all__


def test_level1_framework_exports_base_contracts_and_marks_ag2_lazy_compatibility():
    import trinityguard.level1_framework as level1
    from trinityguard.level1_framework.a3s.adapter import A3SCodeMAS
    from trinityguard.level1_framework.base import BaseMAS, MessageHookResult, WorkflowResult

    assert level1.BaseMAS is BaseMAS
    assert level1.WorkflowResult is WorkflowResult
    assert level1.MessageHookResult is MessageHookResult
    assert level1.A3SCodeMAS is A3SCodeMAS
    assert "A3SCodeMAS" in level1.__all__
    assert "AG2MAS" in level1.__all__
    assert "create_ag2_mas_from_config" in level1.__all__
    assert "AG2MAS" not in level1.__dict__


def test_level3_safety_exports_compatibility_facade_and_base_types():
    import trinityguard.level3_safety as level3
    from trinityguard.level3_safety.attacks.base import AttackCase, BaseAttack
    from trinityguard.level3_safety.monitors_base_ref import Alert, BaseMonitorAgent
    from trinityguard.level3_safety.safety_mas import Safety_MAS
    from trinityguard.level3_safety.safety_mas_types import MonitorSelectionMode

    assert level3.Safety_MAS is Safety_MAS
    assert level3.MonitorSelectionMode is MonitorSelectionMode
    assert level3.BaseAttack is BaseAttack
    assert level3.AttackCase is AttackCase
    assert level3.Alert is Alert
    assert level3.BaseMonitorAgent is BaseMonitorAgent


def test_public_api_contract_document_defines_canonical_and_compatibility_paths():
    text = Path("docs/contracts/public-api-v1.md").read_text(encoding="utf-8")

    required = [
        "TrinityGuard Public API Contract v1",
        "from trinityguard import Safety_MAS, MonitorSelectionMode",
        "from trinityguard.level1_framework.base import BaseMAS, WorkflowResult",
        "from trinityguard.runtime.adapter_contract import MessageHookResult",
        "trinityguard.level1_framework.ag2_wrapper",
        "trinityguard.utils.ag2_io_filter",
        "deprecated compatibility",
        "not production deployment",
        "not CI/release",
        "not Garak/OpenRT comparison",
    ]
    for phrase in required:
        assert phrase in text


def test_readme_links_public_api_contract():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "docs/contracts/public-api-v1.md" in text
