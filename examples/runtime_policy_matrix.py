#!/usr/bin/env python3
"""Run the local academic runtime policy fixture matrix."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trinityguard.level1_framework.base import BaseMAS, WorkflowResult  # noqa: E402
from trinityguard.level3_safety.judges.base import BaseJudge, JudgeResult  # noqa: E402
from trinityguard.level3_safety.safety_mas import Safety_MAS  # noqa: E402
from trinityguard.runtime import InMemoryEventSink, RuntimeProtector, RuntimeRequest  # noqa: E402
from trinityguard.runtime.config import load_policy_config  # noqa: E402
from trinityguard.runtime.events import payload_hash  # noqa: E402
from trinityguard.runtime.reporting import (  # noqa: E402
    build_runtime_report,
    export_runtime_report,
    verify_runtime_report_artifact,
)

POLICY_FILES = [
    "runtime-mvp-default.json",
    "runtime-mvp-monitor-only.json",
    "runtime-mvp-fail-closed.json",
    "runtime-mvp-warning-block.json",
    "runtime-mvp-resilient-local.json",
]
NON_GOALS = ["production deployment", "Garak/OpenRT comparison"]


class MatrixJudge(BaseJudge):
    """Offline judge for local policy matrix scenarios."""

    def __init__(self, scenario: str) -> None:
        super().__init__(risk_type=scenario)
        self.scenario = scenario

    def analyze(self, content: str, context: dict | None = None) -> JudgeResult | None:
        if self.scenario == "error":
            raise RuntimeError("matrix judge failed TOKEN=matrix-secret")
        if self.scenario == "slow":
            time.sleep(0.02)
            return JudgeResult(False, "none", "slow safe", [], "log", judge_type="matrix")
        if self.scenario == "warning":
            return JudgeResult(
                True, "warning", "warning risk", [content], "warn", judge_type="matrix"
            )
        if self.scenario == "risky":
            return JudgeResult(
                True, "critical", "critical risk", [content], "block", judge_type="matrix"
            )
        return JudgeResult(False, "none", "safe", [content], "log", judge_type="matrix")

    def get_judge_info(self) -> dict[str, str]:
        return {"type": self.risk_type, "version": "matrix", "description": self.scenario}


class MatrixDenyMAS(BaseMAS):
    """Offline deny-aware MAS for block-mode coverage."""

    def get_agents(self):
        return []

    def get_agent(self, name):
        raise ValueError(name)

    def run_workflow(self, task: str, **kwargs) -> WorkflowResult:
        hook_result = self._apply_message_hooks_with_result(
            {"from": "matrix", "to": "target", "content": task}
        )
        if hook_result.action == "deny":
            return WorkflowResult(
                success=False,
                output=None,
                messages=[],
                metadata={"delivery_denied": hook_result.to_dict()},
                error=hook_result.reason,
            )
        return WorkflowResult(
            success=True,
            output=hook_result.message["content"],
            messages=[hook_result.message],
            metadata={},
        )

    def get_topology(self):
        return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policies-dir", type=Path, default=Path("config/runtime_policies"))
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    policy_summaries = []
    for policy_file in POLICY_FILES:
        policy_path = args.policies_dir / policy_file
        policy = load_policy_config(policy_path)
        report = _run_policy(policy.name, policy)
        artifact_path = args.output_dir / policy.name / "runtime-report.json"
        artifact = export_runtime_report(
            report, artifact_path, source=f"policy-matrix {policy.name}"
        )
        verified = verify_runtime_report_artifact(artifact_path)
        policy_summaries.append(
            {
                "policy_name": policy.name,
                "artifact": str(artifact_path),
                "summary": verified["summary"],
                "artifact_type": artifact["artifact_type"],
                "block_mode": verified["block_mode"] or "replace",
            }
        )

    policy = load_policy_config(args.policies_dir / "runtime-mvp-default.json")
    deny_report = _run_deny_mode_policy(policy)
    deny_artifact_path = args.output_dir / "runtime-mvp-deny-local" / "runtime-report.json"
    deny_artifact = export_runtime_report(
        deny_report, deny_artifact_path, source="policy-matrix runtime-mvp-deny-local"
    )
    deny_verified = verify_runtime_report_artifact(deny_artifact_path)
    policy_summaries.append(
        {
            "policy_name": "runtime-mvp-deny-local",
            "artifact": str(deny_artifact_path),
            "summary": deny_verified["summary"],
            "artifact_type": deny_artifact["artifact_type"],
            "block_mode": deny_verified["block_mode"],
        }
    )

    coverage = _coverage(policy_summaries)
    summary = {
        "matrix_type": "trinityguard.runtime_policy_matrix.v1",
        "total_artifacts": len(policy_summaries),
        "total_policies": len(POLICY_FILES),
        "verified_artifacts": len(policy_summaries),
        "runtime_mvp_ready": _runtime_mvp_ready(coverage, policy_summaries),
        "coverage": coverage,
        "non_goals": NON_GOALS,
        "policies": policy_summaries,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("runtime_policy_matrix=ok")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def _run_policy(policy_name: str, policy) -> dict[str, Any]:
    scenarios = _scenarios_for_policy(policy_name)
    decisions = []
    if policy_name == "runtime-mvp-resilient-local":
        protector = RuntimeProtector(
            judges=[MatrixJudge("slow")],
            policy=policy,
            event_sink=InMemoryEventSink(max_events=10),
        )
        for index in range(3):
            decisions.append(_evaluate(protector, f"slow-{index}", "slow TOKEN=matrix-secret"))
    else:
        for scenario in scenarios:
            protector = RuntimeProtector(
                judges=[MatrixJudge(scenario)],
                policy=policy,
                event_sink=InMemoryEventSink(max_events=10),
            )
            decisions.append(_evaluate(protector, scenario, f"{scenario} TOKEN=matrix-secret"))
    return build_runtime_report(
        enabled=True,
        policy={"name": policy.name, "version": policy.version},
        block_mode="replace",
        decisions=decisions,
    )


def _run_deny_mode_policy(policy) -> dict[str, Any]:
    safety = Safety_MAS(MatrixDenyMAS())
    protector = RuntimeProtector(
        judges=[MatrixJudge("risky")],
        policy=policy,
        event_sink=InMemoryEventSink(max_events=10),
    )
    safety.enable_runtime_protection(protector, block_mode="deny")
    safety.run_task("risky TOKEN=matrix-secret")
    return safety.get_comprehensive_report()["runtime_protection"]


def _scenarios_for_policy(policy_name: str) -> list[str]:
    if policy_name == "runtime-mvp-default":
        return ["safe", "risky"]
    if policy_name == "runtime-mvp-monitor-only":
        return ["risky"]
    if policy_name == "runtime-mvp-fail-closed":
        return ["error"]
    if policy_name == "runtime-mvp-warning-block":
        return ["warning"]
    return ["safe"]


def _evaluate(protector: RuntimeProtector, request_id: str, content: str) -> dict[str, Any]:
    decision = protector.evaluate(
        RuntimeRequest(
            request_id=request_id,
            agent_id="matrix-agent",
            action="matrix-evaluate",
            message=content,
        )
    )
    return {
        "request_id": request_id,
        "decision": decision.decision,
        "permitted": decision.permitted,
        "reason": decision.reason,
        "policy": {"name": protector.policy.name, "version": protector.policy.version},
        "payload_ref": f"sha256:{payload_hash(content)}",
        "delivery_action": "replace" if decision.decision == "block" else "allow",
        "failure": decision.failure or "",
        "sink_error": decision.sink_error or "",
    }


def _coverage(policy_summaries: list[dict[str, Any]]) -> dict[str, list[str]]:
    decisions = set()
    block_modes = set()
    failure_modes = set()
    for item in policy_summaries:
        summary = item["summary"]
        decisions.update(
            decision
            for decision in ("allow", "monitor_only", "block")
            if summary.get(decision, 0) > 0
        )
        if item.get("block_mode"):
            block_modes.add(item["block_mode"])
        if summary.get("failures", 0) > 0:
            if item["policy_name"] == "runtime-mvp-fail-closed":
                failure_modes.add("fail_closed")
            else:
                failure_modes.add("fail_open")
    return {
        "decisions": sorted(decisions),
        "block_modes": sorted(block_modes),
        "failure_modes": sorted(failure_modes),
    }


def _runtime_mvp_ready(
    coverage: dict[str, list[str]], policy_summaries: list[dict[str, Any]]
) -> bool:
    return (
        len(policy_summaries) == 6
        and set(coverage["decisions"]) == {"allow", "monitor_only", "block"}
        and set(coverage["block_modes"]) == {"replace", "deny"}
        and set(coverage["failure_modes"]) == {"fail_open", "fail_closed"}
    )


if __name__ == "__main__":
    raise SystemExit(main())
