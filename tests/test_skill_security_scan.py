"""Tests for internal skill security scan."""

import sys
from pathlib import Path

import pytest


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


from src.utils.skill_security_scan import scan_skill_paths
from src.level1_framework.tools.skill_security_scan import run_skill_security_scan


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_internal_scan_detects_network_issue(tmp_path: Path) -> None:
    _write(tmp_path / "SKILL.md", "curl http://evil.example.com\\n")

    report = scan_skill_paths([str(tmp_path)], min_severity="INFO", max_issues=50)

    assert report["total_files"] >= 1
    assert report["total_issues"] >= 1
    rule_ids = {f["rule_id"] for f in report["findings"]}
    assert "NET001" in rule_ids


def test_internal_scan_allows_known_domains(tmp_path: Path) -> None:
    _write(tmp_path / "SKILL.md", "curl https://api.anthropic.com/v1/messages\\n")

    report = scan_skill_paths([str(tmp_path)], min_severity="INFO", max_issues=50)

    assert report["total_files"] >= 1
    assert report["total_issues"] == 0


def test_internal_scan_whitelist_excludes_rule(tmp_path: Path) -> None:
    _write(tmp_path / "SKILL.md", "curl http://evil.example.com\\n")

    report = scan_skill_paths([str(tmp_path)], min_severity="INFO", whitelist=["NET001"], max_issues=50)

    assert report["total_files"] >= 1
    assert report["total_issues"] == 0


def test_internal_scan_min_severity_filters(tmp_path: Path) -> None:
    _write(tmp_path / "scripts" / "x.py", "import os\\nos.system('echo hi')\\n")

    report = scan_skill_paths([str(tmp_path)], min_severity="CRITICAL", max_issues=50)

    assert report["total_files"] >= 1
    assert report["total_issues"] == 0


def test_tool_wrapper_schema(tmp_path: Path) -> None:
    _write(tmp_path / "SKILL.md", "rm -rf /\\n")

    report = run_skill_security_scan([str(tmp_path)], severity="INFO", max_issues=10)

    assert "issues" in report
    assert "risk_level" in report
    assert "risk_score" in report
    assert "recommendation" in report
    assert isinstance(report["issues"], list)
    assert report["total_files"] >= 1


def _print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main() -> int:
    _print_section("Skill Security Scan - Unit Tests")
    test_file = Path(__file__).resolve()
    exit_code = int(pytest.main(["-q", str(test_file)]))
    if exit_code == 0:
        _print_section("All tests passed!")
    else:
        _print_section(f"Tests failed (exit={exit_code})")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
