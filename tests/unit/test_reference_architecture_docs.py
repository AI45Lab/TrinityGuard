"""Guard current reference docs against stale v1 architecture paths."""

from pathlib import Path


def test_src_architecture_reference_names_current_canonical_paths():
    text = Path("docs/reference/src_architecture.md").read_text()

    assert "Current canonical paths" in text
    assert "src/trinityguard/level1_framework/ag2/adapter.py" in text
    assert "src/trinityguard/level2_intermediary/runners/" in text
    assert "src/trinityguard/level3_safety/attacks/" in text
    assert "src/trinityguard/runtime/" in text
    assert "ag2_wrapper.py    # AG2框架具体实现" not in text
    assert "risk_tests/" not in text
    assert "monitor_agents/" not in text


def test_runtime_monitoring_reference_warns_runtime_scope_is_research_prototype():
    text = Path("docs/reference/runtime_monitoring.md").read_text()

    assert "Research prototype scope" in text
    assert "src/trinityguard/level3_safety/safety_mas.py" in text
    assert "src/trinityguard/runtime/" in text
    assert "src/level3_safety" not in text
    assert "production deployment" in text


def test_src_architecture_reference_mentions_phase4_owner_helpers():
    text = Path("docs/reference/src_architecture.md").read_text()

    assert "Phase 4 owner helpers" in text
    assert "src/trinityguard/level3_safety/test_orchestration.py" in text
    assert "src/trinityguard/level3_safety/monitor_orchestration.py" in text
    assert "src/trinityguard/level3_safety/safety_reports.py" in text
    assert "Safety_MAS 创建 MonitoredInterceptingRunner" not in text
    assert "self._create_intermediary(mas)" not in text


def test_runtime_monitoring_reference_mentions_monitor_orchestration_boundary():
    text = Path("docs/reference/runtime_monitoring.md").read_text()

    assert "src/trinityguard/level3_safety/monitor_orchestration.py" in text
    assert "monitor orchestration" in text.lower()
