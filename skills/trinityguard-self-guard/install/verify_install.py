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
        "trinityguard-self-guard-orchestrator/SKILL.md",
        "trinityguard-preflight-selfcheck/SKILL.md",
        "trinityguard-runtime-selfmonitor/SKILL.md",
        "trinityguard-output-privacy-guard/SKILL.md",
        "shared/scripts/self_guard_runtime_hook_template.py",
        "shared/scripts/query_guard_events.py",
        "shared/references/runtime_policy.template.json",
        "shared/references/guard_event.schema.json",
    ]
    for rel in required:
        path = skill_dir / rel
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")
    print(f"[OK] file structure verified: {skill_dir}")


def pick_policy_file(skill_dir: Path, policy_file: str) -> Path:
    if policy_file:
        return Path(policy_file).expanduser().resolve()
    balanced = skill_dir / "shared" / "references" / "runtime_policy.balanced.json"
    if balanced.exists():
        return balanced
    return skill_dir / "shared" / "references" / "runtime_policy.template.json"


def run_eval_consistency(skill_dir: Path) -> None:
    script = skill_dir / "shared" / "scripts" / "validate_eval_assets_consistency.py"
    subprocess.run([sys.executable, str(script), str(skill_dir), "--strict"], check=True)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_runtime_smoke(skill_dir: Path, policy_file: Path, policy_profile: str) -> Path:
    verify_project = skill_dir / ".verify_project"
    verify_dir = verify_project / ".codex" / "logs"
    verify_project.mkdir(parents=True, exist_ok=True)

    input_template = skill_dir / "shared" / "scripts" / "runtime_hook_input_example.json"
    hook = skill_dir / "shared" / "scripts" / "self_guard_runtime_hook_template.py"
    input_json = verify_project / "runtime_hook_input_verify.json"
    summary_json = ".codex/logs/runtime_hook_summary.json"

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
            "--out",
            summary_json,
        ],
        check=True,
    )
    return verify_dir


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def verify_events_fields(verify_dir: Path) -> None:
    events_jsonl = verify_dir / "self_guard_events.jsonl"
    if not events_jsonl.exists():
        raise FileNotFoundError(f"Missing events log: {events_jsonl}")

    rows = read_jsonl(events_jsonl)
    if not rows:
        raise ValueError("Events log is empty")

    for required in REQUIRED_EVENT_TYPES:
        if not any(str(r.get("event_type", "")) == required for r in rows):
            raise ValueError(f"Missing required event type: {required}")

    final_events = [r for r in rows if str(r.get("event_type", "")) == "final_decision"]
    if not final_events:
        raise ValueError("Missing final_decision event")

    final_event = final_events[-1]
    required_top = ["final_action", "policy_profile", "reason_codes", "matched_rules", "retention"]
    for key in required_top:
        if key not in final_event:
            raise ValueError(f"Missing final_decision field: {key}")

    print(f"[OK] final_action= {final_event['final_action']}")
    print(f"[OK] policy_profile= {final_event['policy_profile']}")
    print(f"[OK] reason_codes_count= {len(final_event.get('reason_codes', []))}")


def main() -> None:
    args = parse_args()
    skill_dir = resolve_skill_dir(args)
    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill not installed at: {skill_dir}")

    ensure_required_files(skill_dir)
    run_eval_consistency(skill_dir)
    verify_dir = run_runtime_smoke(skill_dir, pick_policy_file(skill_dir, args.policy_file), args.policy_profile)
    verify_events_fields(verify_dir)
    shutil.rmtree(verify_dir.parent.parent, ignore_errors=True)
    print("[OK] runtime hook JSONL smoke test passed")


if __name__ == "__main__":
    main()
