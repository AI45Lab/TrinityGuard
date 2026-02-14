"""AG2 tool wrapper: internal "skill security scan".

This tool is implemented inside TrinityGuard (offline static scan). It scans
local "skill" directories/files for risky patterns (network exfiltration,
dangerous commands, sensitive file access, etc.) and returns a structured
report with issues + risk level/score.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from ...utils.skill_security_scan import scan_skill_paths


def run_skill_security_scan(
    paths: Optional[Sequence[str]] = None,
    *,
    severity: str = "INFO",
    rules: Optional[str] = None,
    whitelist: Optional[Sequence[str]] = None,
    max_issues: int = 200,
) -> Dict[str, Any]:
    """Run the internal skill security scan and return a report dict.

    Args:
        paths: Paths to scan. If empty/None, scans common default locations.
        severity: Minimum severity to include (CRITICAL|HIGH|WARNING|INFO).
        rules: Optional rules YAML file path.
        whitelist: Optional list of rule IDs to ignore.
        max_issues: Stop after collecting this many issues (limits tool output).

    Returns:
        Dict report containing: issues, summary, risk_score, risk_level, total_files, etc.
    """
    report = scan_skill_paths(
        paths,
        rules_file=rules,
        whitelist=whitelist,
        min_severity=severity,
        max_issues=max_issues,
    )

    issues = report.pop("findings", [])

    # Keep "issues" naming for tool consumers.
    report["issues"] = issues
    report["issues_total"] = report.get("total_issues", len(issues))
    report["issues_truncated"] = bool(max_issues >= 0 and len(issues) >= max_issues)

    recommendation_map = {
        "CRITICAL": "DO_NOT_USE",
        "HIGH": "NOT_RECOMMENDED",
        "MEDIUM": "REVIEW_NEEDED",
        "LOW": "USE_WITH_CAUTION",
        "SAFE": "SAFE",
    }
    report["recommendation"] = recommendation_map.get(report.get("risk_level", "SAFE"), "UNKNOWN")

    report.setdefault("tool_meta", {})
    report["tool_meta"].update(
        {
            "scan_id": f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "min_severity": severity,
            "rules_file": rules,
            "whitelist": list(whitelist or []),
        }
    )

    return report


def attach_skill_security_scan_tool(
    assistant_agent: Any,
    *,
    executor_agent: Optional[Any] = None,
    name: str = "skill_security_scan",
    description: Optional[str] = None,
) -> None:
    """Attach the skill-security-scan tool to AG2 agents.

    Typical pattern:
      - assistant_agent: has llm_config (can decide to call tools)
      - executor_agent: can execute tools (may have llm_config=False)

    If executor_agent is None, registers execution on assistant_agent as well.
    """
    description = description or (
        "Scan local 'skill' directories/files for security risks (offline static scan). "
        "Input paths are local filesystem paths. Returns a report with issues and risk score/level."
    )

    executor = executor_agent or assistant_agent

    def _tool(
        paths: Optional[List[str]] = None,
        severity: str = "INFO",
        rules: Optional[str] = None,
        whitelist: Optional[List[str]] = None,
        max_issues: int = 200,
    ) -> Dict[str, Any]:
        return run_skill_security_scan(
            paths or [],
            severity=severity,
            rules=rules,
            whitelist=whitelist,
            max_issues=max_issues,
        )

    tool = executor.register_for_execution(name=name, description=description, serialize=False)(_tool)
    assistant_agent.register_for_llm(name=name, description=description)(tool)
