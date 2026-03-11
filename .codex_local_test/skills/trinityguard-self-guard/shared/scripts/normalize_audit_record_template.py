#!/usr/bin/env python3
"""Normalize self-guard step outputs into one audit record.

Inputs:
- preflight JSON
- runtime JSON
- output_guard JSON

Output:
- unified audit JSON aligned with shared/references/audit_record.schema.json
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
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def decide_final_action(preflight_decision: str, runtime_decision: str, output_decision: str) -> str:
    if "block" in {preflight_decision, output_decision}:
        return "block"
    if runtime_decision == "stop":
        return "block"
    if "downgrade" in {preflight_decision, output_decision} or runtime_decision == "downgrade":
        return "downgrade"
    return "allow"


def derive_residual_risks(preflight: Dict[str, Any], runtime: Dict[str, Any], output_guard: Dict[str, Any]) -> List[str]:
    risks: List[str] = []

    if output_guard.get("leakage_detected", False):
        risks.append("sensitive leakage risk observed")

    trust_annotations = as_list(runtime.get("trust_annotations", []))
    for item in trust_annotations:
        source_type = str(item.get("source_type", "")).strip().lower()
        if source_type in {"tool_single_source", "tool_multi_source_unverified"}:
            risks.append("tool-derived conclusion not fully verified")
            break

    if str(preflight.get("sensitivity_state", "normal")) in {"sensitive", "highly_sensitive"}:
        risks.append("session contains sensitive context")

    return sorted(set(risks))


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize self-guard outputs into audit record")
    parser.add_argument("--session-id", required=True, help="Session id")
    parser.add_argument("--trigger-reason", action="append", default=[], help="Trigger reason, can repeat")
    parser.add_argument("--preflight", required=True, help="Preflight JSON path")
    parser.add_argument("--runtime", required=True, help="Runtime JSON path")
    parser.add_argument("--output-guard", required=True, help="Output guard JSON path")
    parser.add_argument("--out", default="audit_record.json", help="Output file path")
    args = parser.parse_args()

    preflight = load_json(Path(args.preflight).resolve())
    runtime = load_json(Path(args.runtime).resolve())
    output_guard = load_json(Path(args.output_guard).resolve())

    preflight_decision = str(preflight.get("preflight_decision", "allow"))
    runtime_decision = str(runtime.get("runtime_decision", "continue"))
    output_decision = str(output_guard.get("output_decision", "allow"))

    final_action = decide_final_action(preflight_decision, runtime_decision, output_decision)

    audit_record = {
        "session_id": args.session_id,
        "trigger_reasons": args.trigger_reason,
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
            "confidence_level": str(output_guard.get("confidence_level", "low")),
            "safe_response": str(output_guard.get("safe_response", "")),
            "output_decision": output_decision,
        },
        "final_action": final_action,
        "residual_risks": derive_residual_risks(preflight, runtime, output_guard),
        "audit_notes": as_list(output_guard.get("audit_notes", [])),
    }

    save_json(Path(args.out).resolve(), audit_record)
    print(f"Saved: {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
