#!/usr/bin/env python3
"""Normalize preflight/runtime/output results into one legacy audit record.

Legacy helper only. New integrations should prefer JSONL events:
shared/references/guard_event.schema.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def as_list(v: Any) -> List[Any]:
    if isinstance(v, list):
        return v
    if v is None:
        return []
    return [v]


def decide_final_action(preflight_decision: str, runtime_decision: str, output_decision: str) -> str:
    if preflight_decision == "block" or output_decision == "block":
        return "block"
    if runtime_decision == "stop":
        return "block"
    if preflight_decision == "downgrade" or runtime_decision == "downgrade" or output_decision == "downgrade":
        return "downgrade"
    return "allow"


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize self-guard outputs into legacy audit record")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output-guard", required=True)
    parser.add_argument("--out", default="audit_record.json", help="Output file path")
    args = parser.parse_args()

    preflight = load_json(Path(args.preflight).resolve())
    runtime = load_json(Path(args.runtime).resolve())
    output_guard = load_json(Path(args.output_guard).resolve())

    preflight_decision = str(preflight.get("preflight_decision", "allow"))
    runtime_decision = str(runtime.get("runtime_decision", "continue"))
    output_decision = str(output_guard.get("output_decision", "allow"))
    final_action = decide_final_action(preflight_decision, runtime_decision, output_decision)

    residual_risks: List[str] = []
    if bool(output_guard.get("leakage_detected", False)):
        residual_risks.append("privacy leakage risk observed")
    if any(str(x.get("source_type", "")).startswith("tool_") for x in as_list(runtime.get("trust_annotations", []))):
        residual_risks.append("tool-derived conclusion may be uncertain")
    if str(preflight.get("sensitivity_state", "normal")) in {"sensitive", "highly_sensitive"}:
        residual_risks.append("sensitive-context output requires strict guard")

    audit_record = {
        "session_id": str(args.session_id),
        "trigger_reasons": ["orchestrator_pipeline"],
        "preflight": {
            "risk_summary": as_list(preflight.get("risk_summary", [])),
            "sensitivity_state": str(preflight.get("sensitivity_state", "normal")),
            "allowed_actions": as_list(preflight.get("allowed_actions", [])),
            "blocked_actions": as_list(preflight.get("blocked_actions", [])),
            "verification_requirements": as_list(preflight.get("verification_requirements", [])),
            "preflight_decision": preflight_decision,
        },
        "runtime": {
            "runtime_events": as_list(runtime.get("runtime_events", [])),
            "alerts": as_list(runtime.get("alerts", [])),
            "suggested_actions": as_list(runtime.get("suggested_actions", [])),
            "trust_annotations": as_list(runtime.get("trust_annotations", [])),
            "runtime_decision": runtime_decision,
        },
        "output_guard": {
            "leakage_detected": bool(output_guard.get("leakage_detected", False)),
            "redaction_applied": bool(output_guard.get("redaction_applied", False)),
            "confidence_level": str(output_guard.get("confidence_level", "medium")),
            "safe_response": str(output_guard.get("safe_response", "")),
            "output_decision": output_decision,
        },
        "final_action": final_action,
        "residual_risks": sorted(set(residual_risks)),
        "audit_notes": as_list(output_guard.get("audit_notes", [])),
    }

    save_json(Path(args.out).resolve(), audit_record)


if __name__ == "__main__":
    main()
