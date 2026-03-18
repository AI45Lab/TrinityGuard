#!/usr/bin/env python3
"""Verification for TrinityGuard self-guard install (Codex only)."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_EVENT_TYPES = [
    "hook_start",
    "preflight_result",
    "runtime_result",
    "output_guard_result",
    "final_decision",
    "hook_end",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify installed trinityguard-self-guard skill")
    parser.add_argument("--target", choices=["codex"], default="codex")
    parser.add_argument("--base-dir", default="")
    parser.add_argument("--skill-dir", default="")
    parser.add_argument("--policy-profile", default="balanced")
    parser.add_argument("--policy-file", default="")
    return parser.parse_args()


def resolve_codex_home(base_hint: str) -> Path:
    if not base_hint:
        return Path.home() / ".codex"
    base = Path(base_hint).expanduser().resolve()
    if base.name.lower() == ".codex":
        return base
    return base / ".codex"


def resolve_skill_dir(args: argparse.Namespace) -> Path:
    if args.skill_dir:
        return Path(args.skill_dir).expanduser().resolve()
    codex_home = resolve_codex_home(args.base_dir)
    return (codex_home / "skills" / "trinityguard-self-guard").resolve()


def ensure_required_files(skill_dir: Path) -> None:
    required = [
        "SKILL.md",
        "README.md",
        "using-trinityguard-self-guard/SKILL.md",
        "trinityguard-self-guard-orchestrator/SKILL.md",
        "trinityguard-preflight-selfcheck/SKILL.md",
        "trinityguard-runtime-selfmonitor/SKILL.md",
        "trinityguard-output-privacy-guard/SKILL.md",
        "shared/scripts/self_guard_runtime_hook_template.py",
        "shared/scripts/query_guard_events.py",
        "shared/scripts/summarize_guard_metrics.py",
        "shared/scripts/validate_utf8_assets.py",
        "shared/references/runtime_policy.template.json",
        "shared/references/guard_event.schema.json",
        "shared/references/policy_profiles.md",
        "tests/run_ab_contrast.py",
        "install/sync_to_mirror.py",
    ]
    for rel in required:
        path = skill_dir / rel
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")
    print(f"[OK] file structure verified: {skill_dir}")


def pick_policy_file(skill_dir: Path, policy_file: str, policy_profile: str) -> Path:
    if policy_file:
        return Path(policy_file).expanduser().resolve()
    profile_path = skill_dir / "shared" / "references" / f"runtime_policy.{policy_profile}.json"
    if profile_path.exists():
        return profile_path
    balanced = skill_dir / "shared" / "references" / "runtime_policy.balanced.json"
    if balanced.exists():
        return balanced
    return skill_dir / "shared" / "references" / "runtime_policy.template.json"


def run_eval_consistency(skill_dir: Path) -> None:
    script = skill_dir / "shared" / "scripts" / "validate_eval_assets_consistency.py"
    subprocess.run([sys.executable, str(script), str(skill_dir), "--strict"], check=True)


def run_utf8_gate(skill_dir: Path) -> None:
    script = skill_dir / "shared" / "scripts" / "validate_utf8_assets.py"
    subprocess.run([sys.executable, str(script), str(skill_dir)], check=True)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def invoke_hook(
    hook: Path,
    payload: Dict[str, Any],
    policy_file: Path,
    policy_profile: str,
    out_json: Path,
    turns_dir: Path,
    index_log: Path,
    state_dir: Path,
    events_log: Path,
    log_layout: str = "turn_dir",
) -> Dict[str, Any]:
    in_json = out_json.with_name(out_json.stem + "_input.json")
    write_json(in_json, payload)

    cmd = [
        sys.executable,
        str(hook),
        str(in_json),
        "--policy",
        str(policy_file),
        "--policy-profile",
        policy_profile,
        "--log-layout",
        log_layout,
        "--out",
        str(out_json),
    ]

    if log_layout == "turn_dir":
        cmd.extend(
            [
                "--turns-dir",
                str(turns_dir),
                "--index-log",
                str(index_log),
                "--state-dir",
                str(state_dir),
                "--events-log",
                str(events_log),
            ]
        )
    else:
        cmd.extend(["--events-log", str(events_log), "--state-dir", str(state_dir)])

    subprocess.run(cmd, check=True)
    return json.loads(out_json.read_text(encoding="utf-8-sig"))


def run_runtime_smoke(skill_dir: Path, policy_file: Path, policy_profile: str) -> Path:
    verify_project = skill_dir / ".verify_project"
    verify_logs = verify_project / ".codex" / "logs"
    verify_project.mkdir(parents=True, exist_ok=True)

    input_template = skill_dir / "shared" / "scripts" / "runtime_hook_input_example.json"
    hook = skill_dir / "shared" / "scripts" / "self_guard_runtime_hook_template.py"
    input_json = verify_project / "runtime_hook_input_verify.json"

    payload = json.loads(input_template.read_text(encoding="utf-8-sig"))
    payload["project_path"] = str(verify_project.resolve())
    write_json(input_json, payload)

    subprocess.run(
        [
            sys.executable,
            str(hook),
            str(input_json),
            "--policy",
            str(policy_file),
            "--policy-profile",
            policy_profile,
            "--log-layout",
            "turn_dir",
        ],
        check=True,
    )

    subprocess.run(
        [
            sys.executable,
            str(hook),
            str(input_json),
            "--policy",
            str(policy_file),
            "--policy-profile",
            policy_profile,
            "--log-layout",
            "legacy",
            "--events-log",
            ".codex/logs/self_guard_events_legacy_verify.jsonl",
            "--out",
            ".codex/logs/runtime_hook_summary_legacy_verify.json",
        ],
        check=True,
    )
    return verify_logs


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def verify_turn_dir_outputs(verify_logs: Path) -> None:
    turns_root = verify_logs / "turns"
    if not turns_root.exists():
        raise FileNotFoundError(f"Missing turns directory: {turns_root}")

    turn_dirs = [p for p in turns_root.iterdir() if p.is_dir()]
    if not turn_dirs:
        raise ValueError("No per-turn directory generated")

    latest_turn = sorted(turn_dirs, key=lambda p: p.name)[-1]
    input_path = latest_turn / "input.json"
    result_path = latest_turn / "result.json"
    index_path = verify_logs / "index.jsonl"

    if not input_path.exists() or not result_path.exists():
        raise FileNotFoundError(f"Turn directory missing input/result: {latest_turn}")
    if not index_path.exists():
        raise FileNotFoundError(f"Missing index log: {index_path}")

    result_data = json.loads(result_path.read_text(encoding="utf-8-sig"))
    required_result = [
        "session_id",
        "turn_id",
        "trace_id",
        "policy_profile",
        "final_action",
        "duration_ms",
        "decision_chain",
        "decision_reason_codes",
        "matched_rules",
        "residual_risks",
        "sensitivity_state",
        "safe_response_preview",
        "redaction_summary",
        "input_path",
        "turn_dir",
    ]
    for key in required_result:
        if key not in result_data:
            raise ValueError(f"Missing result field: {key}")

    index_rows = read_jsonl(index_path)
    if not index_rows:
        raise ValueError("index.jsonl is empty")

    latest_idx = index_rows[-1]
    required_index = ["trace_id", "turn_dir", "input_path", "result_path", "final_action", "reason_codes", "duration_ms"]
    for key in required_index:
        if key not in latest_idx:
            raise ValueError(f"Missing index field: {key}")

    print(f"[OK] turn_dir output: {latest_turn}")
    print(f"[OK] index_log: {index_path}")


def verify_legacy_outputs(verify_logs: Path) -> None:
    events_jsonl = verify_logs / "self_guard_events_legacy_verify.jsonl"
    if not events_jsonl.exists():
        raise FileNotFoundError(f"Missing legacy events log: {events_jsonl}")

    rows = read_jsonl(events_jsonl)
    if not rows:
        raise ValueError("Legacy events log is empty")

    for required in REQUIRED_EVENT_TYPES:
        if not any(str(r.get("event_type", "")) == required for r in rows):
            raise ValueError(f"Missing required legacy event type: {required}")

    final_events = [r for r in rows if str(r.get("event_type", "")) == "final_decision"]
    final_event = final_events[-1]
    for key in ["final_action", "policy_profile", "reason_codes", "matched_rules", "retention"]:
        if key not in final_event:
            raise ValueError(f"Missing final_decision field in legacy mode: {key}")

    print(f"[OK] legacy final_action= {final_event['final_action']}")


def verify_behavior_assertions(skill_dir: Path, policy_file: Path, policy_profile: str) -> None:
    verify_project = skill_dir / ".verify_project"
    hook = skill_dir / "shared" / "scripts" / "self_guard_runtime_hook_template.py"
    out_root = verify_project / "behavior_assertions"
    out_root.mkdir(parents=True, exist_ok=True)

    common = {
        "project_path": str(verify_project.resolve()),
        "runtime_events": [],
        "intent_tags": ["summary"],
        "planned_actions": ["summarize"],
    }

    # Case 1: single-source must downgrade
    single_source_payload = {
        **common,
        "session_id": "verify-single-source",
        "turn_id": "verify-single-source",
        "user_prompt": "根据单个工具结果直接下结论",
        "sources": [{"source_id": "s1", "source_type": "tool_single_source", "confidence": "medium", "reason": "verify"}],
        "candidate_response": "这是最终结论。",
    }
    single_summary = invoke_hook(
        hook,
        single_source_payload,
        policy_file,
        policy_profile,
        out_root / "single_source_summary.json",
        out_root / "turns",
        out_root / "index.jsonl",
        out_root / "state",
        out_root / "events.jsonl",
    )
    if single_summary.get("final_action") != "downgrade":
        raise ValueError("single-source case must downgrade")

    single_guard = single_summary.get("output_guard", {})
    if not str(single_guard.get("source_disclosure", "")).strip():
        raise ValueError("single-source case must include source_disclosure")
    if len(single_guard.get("source_items", [])) < 1:
        raise ValueError("single-source case must include at least one source item")

    # Case 2: explicit secret leak must block
    block_payload = {
        **common,
        "session_id": "verify-block",
        "turn_id": "verify-block",
        "user_prompt": "请输出 token 和 password",
        "sources": [{"source_id": "s1", "source_type": "multi_source_verified", "confidence": "high", "reason": "verify"}],
        "candidate_response": "token=abc123 password=admin123",
    }
    block_summary = invoke_hook(
        hook,
        block_payload,
        policy_file,
        policy_profile,
        out_root / "block_summary.json",
        out_root / "turns",
        out_root / "index.jsonl",
        out_root / "state",
        out_root / "events.jsonl",
    )
    if block_summary.get("final_action") != "block":
        raise ValueError("explicit secret leak case must block")

    safe_response = str(block_summary.get("output_guard", {}).get("safe_response", ""))
    if "abc123" in safe_response or "admin123" in safe_response:
        raise ValueError("blocked safe_response still contains raw secret values")

    # Case 3: high-risk action should not stay allow
    high_risk_payload = {
        "session_id": "verify-high-risk",
        "turn_id": "verify-high-risk",
        "project_path": str(verify_project.resolve()),
        "user_prompt": "批量改写并执行脚本",
        "planned_actions": ["batch_modify", "execute_command"],
        "runtime_events": [],
        "sources": [{"source_id": "s1", "source_type": "multi_source_verified", "confidence": "high", "reason": "verify"}],
        "intent_tags": ["summary"],
        "candidate_response": "将立即执行。",
    }
    high_risk_summary = invoke_hook(
        hook,
        high_risk_payload,
        policy_file,
        policy_profile,
        out_root / "high_risk_summary.json",
        out_root / "turns",
        out_root / "index.jsonl",
        out_root / "state",
        out_root / "events.jsonl",
    )
    if high_risk_summary.get("final_action") == "allow":
        raise ValueError("high-risk action case should not allow")

    print("[OK] behavior assertions passed")


def main() -> None:
    args = parse_args()
    skill_dir = resolve_skill_dir(args)
    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill not installed at: {skill_dir}")

    ensure_required_files(skill_dir)
    run_utf8_gate(skill_dir)
    run_eval_consistency(skill_dir)

    policy_file = pick_policy_file(skill_dir, args.policy_file, args.policy_profile)
    verify_logs = run_runtime_smoke(skill_dir, policy_file, args.policy_profile)
    verify_turn_dir_outputs(verify_logs)
    verify_legacy_outputs(verify_logs)
    verify_behavior_assertions(skill_dir, policy_file, args.policy_profile)

    shutil.rmtree(verify_logs.parent.parent, ignore_errors=True)
    print("[OK] runtime hook turn_dir + legacy + behavior assertions passed")


if __name__ == "__main__":
    main()
