"""
Demo: Use TrinityGuard's internal skill security scan as an AG2 tool.

Run:
  source .venv/bin/activate
  python examples/skill_security_scan_tool_demo.py
"""

import sys
import os
from pathlib import Path


# Ensure project root is on sys.path when running this file directly.
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main():
    from autogen import ConversableAgent

    from src.level1_framework.tools.skill_security_scan import attach_skill_security_scan_tool
    from src.utils.llm_config import get_mas_llm_config

    want_llm_summary = os.getenv("SKILL_SCAN_LLM_SUMMARY", "0") == "1"
    # Tool registration for LLM requires llm_config, even if we won't call the LLM in this demo.
    llm_config = get_mas_llm_config().to_ag2_config()

    assistant = ConversableAgent(
        name="assistant",
        system_message=(
            "You are a security reviewer. When asked to scan a skill directory, "
            "use the tool skill_security_scan and summarize the risk."
        ),
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # Executor can be LLM-disabled; it only runs the tool.
    executor = ConversableAgent(
        name="executor",
        system_message="You execute local tools and return results.",
        llm_config=False,
        human_input_mode="NEVER",
    )

    attach_skill_security_scan_tool(
        assistant_agent=assistant,
        executor_agent=executor,
    )

    target = os.getenv("SKILL_SCAN_TARGET", str(project_root / "examples" / "sample_skill"))
    print(f"Scanning target: {target}")

    # Deterministic demo: call executor's function map directly (no LLM involved).
    report = executor._function_map["skill_security_scan"](paths=[target], severity="INFO", max_issues=20)
    print("\n=== Scan Result (summary) ===")
    print(f"risk_level: {report.get('risk_level')}")
    print(f"risk_score: {report.get('risk_score')}")
    print(f"total_files: {report.get('total_files')}")
    print(f"total_issues: {report.get('total_issues')}")
    print(f"recommendation: {report.get('recommendation')}")
    print(f"issues_truncated: {report.get('issues_truncated')}")

    # Optional: let the LLM read the report and summarize (will call your LLM backend).
    if want_llm_summary:
        prompt = (
            "Summarize this security scan report. "
            "Highlight the most critical issues (if any) and give a recommendation.\n\n"
            f"{report}"
        )
        executor.initiate_chat(assistant, message=prompt, max_turns=2, silent=True)


if __name__ == "__main__":
    main()
