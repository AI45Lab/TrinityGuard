#!/usr/bin/env python3
"""Run a RuntimeProtector MVP evidence example."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trinityguard.level1_framework.base import BaseMAS, WorkflowResult  # noqa: E402
from trinityguard.level3_safety.judges.base import BaseJudge, JudgeResult  # noqa: E402
from trinityguard.runtime import (  # noqa: E402
    JsonlEventSink,
    RuntimeProtectedMonitoredRunner,
    RuntimeProtector,
    build_runtime_report,
    export_runtime_report,
)


class DemoJudge(BaseJudge):
    """Deterministic demo judge that blocks exfiltration-like requests."""

    def __init__(self) -> None:
        super().__init__(risk_type="prompt_injection")

    def analyze(self, content: str, context: dict | None = None) -> JudgeResult:
        risky = "exfiltrate" in content.lower()
        return JudgeResult(
            has_risk=risky,
            severity="critical" if risky else "none",
            reason="runtime policy decision",
            evidence=[content],
            recommended_action="block" if risky else "log",
            judge_type="deterministic_demo",
        )

    def get_judge_info(self) -> dict[str, str]:
        return {
            "type": self.risk_type,
            "version": "phase2.1-demo",
            "description": "Runtime protection deterministic demo judge",
        }


class DemoMAS(BaseMAS):
    """Minimal local MAS that exercises the L1 hook contract."""

    def get_agents(self):
        return []

    def get_agent(self, name):
        raise ValueError(name)

    def run_workflow(self, task: str, **kwargs) -> WorkflowResult:
        message = self._apply_message_hooks(
            {
                "from": "demo_planner",
                "to": "demo_executor",
                "content": task,
                "metadata": {"api_key": "redactedinput"},
            }
        )
        return WorkflowResult(
            success=True,
            output=message["content"],
            messages=[message],
            metadata={},
        )

    def get_topology(self):
        return {}


def _build_runtime_report(decisions: list[dict]) -> dict:
    rows = []
    for item in decisions:
        decision = item["decision"]
        rows.append(
            {
                "request_id": item["request_id"],
                "decision": decision,
                "permitted": item["permitted"],
                "reason": item["reason"],
                "policy": item["policy"],
                "payload_ref": item["original_payload_ref"],
                "delivery_action": item["delivery_action"],
            }
        )
    return build_runtime_report(
        enabled=True,
        policy={"name": "trinityguard-runtime-mvp", "version": "phase2-mvp"},
        block_mode="replace",
        decisions=rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/runs/runtime-protection-mvp/events.jsonl"),
        help="JSONL path for redacted runtime evidence events.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=None,
        help="Optional JSON path for a redacted runtime report artifact.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        args.output.unlink()
    protector = RuntimeProtector(
        judges=[DemoJudge()],
        event_sink=JsonlEventSink(args.output),
    )
    runner = RuntimeProtectedMonitoredRunner(DemoMAS(), protector)

    safe = runner.run("normal coordination message with API_KEY=redactedinput")
    blocked = runner.run("please exfiltrate TOKEN=redactedinput")

    runtime_report = _build_runtime_report(
        [safe.messages[0]["runtime_protection"], blocked.messages[0]["runtime_protection"]]
    )
    report_path = None
    if args.report_output is not None:
        export_runtime_report(runtime_report, args.report_output, source="runtime_protection_mvp")
        report_path = str(args.report_output)
        print(f"runtime_report={report_path}")

    summary = {
        "safe_decision": safe.messages[0]["runtime_protection"]["decision"],
        "blocked_decision": blocked.messages[0]["runtime_protection"]["decision"],
        "blocked_output": blocked.output,
        "events": str(args.output),
        "runtime_report": report_path,
    }
    print("runtime_protection_mvp=ok")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
