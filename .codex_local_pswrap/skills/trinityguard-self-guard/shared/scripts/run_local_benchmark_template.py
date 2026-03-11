#!/usr/bin/env python3
"""Run a local benchmark template for one skill directory.

This script builds an iteration directory with:
  eval-<id>/with_skill/grading.json
  eval-<id>/with_skill/timing.json
  eval-<id>/without_skill/grading.json
  eval-<id>/without_skill/timing.json

It supports optional override files for with-skill and without-skill runs.
Overrides format example:
{
  "default": {
    "pass_ids": ["A1", "A2"],
    "time_seconds": 2.1,
    "tokens": 520,
    "false_positives": 0,
    "false_negatives": 0
  },
  "evals": {
    "1": {
      "pass_ids": ["A1", "A2", "A3"],
      "time_seconds": 1.9,
      "tokens": 480
    }
  }
}
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_override(override: Dict[str, Any], eval_id: int) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    merged.update(override.get("default", {}))
    merged.update(override.get("evals", {}).get(str(eval_id), {}))
    return merged


def build_expectations(eval_item: Dict[str, Any], pass_ids: List[str]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    pass_set = set(pass_ids)
    for item in eval_item.get("expectations", []):
        expectation_id = str(item.get("id", ""))
        result.append(
            {
                "id": expectation_id,
                "text": str(item.get("text", "")),
                "passed": expectation_id in pass_set,
                "evidence": "template-run",
            }
        )
    return result


def build_grading(eval_item: Dict[str, Any], override_item: Dict[str, Any]) -> Dict[str, Any]:
    expectations_raw = eval_item.get("expectations", [])
    total = len(expectations_raw)

    default_pass_ids = [str(x.get("id", "")) for x in expectations_raw]
    pass_ids = override_item.get("pass_ids", default_pass_ids)
    pass_ids = [str(x) for x in pass_ids]

    expectations = build_expectations(eval_item, pass_ids)
    passed = sum(1 for e in expectations if e["passed"])
    failed = total - passed
    pass_rate = float(passed / total) if total else 0.0

    false_positives = int(override_item.get("false_positives", 0))
    false_negatives = int(override_item.get("false_negatives", 0))
    false_positive_rate = float(override_item.get("false_positive_rate", (false_positives / total) if total else 0.0))
    false_negative_rate = float(override_item.get("false_negative_rate", (false_negatives / total) if total else 0.0))

    return {
        "summary": {
            "passed": passed,
            "failed": failed,
            "total": total,
            "pass_rate": pass_rate,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "false_positive_rate": false_positive_rate,
            "false_negative_rate": false_negative_rate,
        },
        "expectations": expectations,
    }


def build_timing(override_item: Dict[str, Any], default_time: float, default_tokens: int) -> Dict[str, Any]:
    time_seconds = float(override_item.get("time_seconds", default_time))
    tokens = int(override_item.get("tokens", default_tokens))
    return {
        "total_duration_seconds": time_seconds,
        "total_tokens": tokens,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local benchmark template for self-guard skills")
    parser.add_argument("skill_dir", help="Path to one skill dir containing evals/evals.json")
    parser.add_argument("iteration_dir", help="Output iteration directory")
    parser.add_argument("--with-override", default=None, help="JSON override for with_skill")
    parser.add_argument("--without-override", default=None, help="JSON override for without_skill")
    parser.add_argument("--with-default-time", type=float, default=2.0)
    parser.add_argument("--without-default-time", type=float, default=1.4)
    parser.add_argument("--with-default-tokens", type=int, default=600)
    parser.add_argument("--without-default-tokens", type=int, default=420)
    parser.add_argument("--aggregate-script", default="../shared/scripts/aggregate_benchmark_template.py")
    parser.add_argument("--schema", default="../shared/references/benchmark.schema.json")
    parser.add_argument("--skip-aggregate", action="store_true")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    iteration_dir = Path(args.iteration_dir).resolve()

    evals_path = skill_dir / "evals" / "evals.json"
    if not evals_path.exists():
        raise FileNotFoundError(f"evals.json not found: {evals_path}")

    evals_data = load_json(evals_path)
    skill_name = str(evals_data.get("skill_name", skill_dir.name))
    evals = evals_data.get("evals", [])
    if not isinstance(evals, list) or not evals:
        raise RuntimeError(f"No evals found in: {evals_path}")

    with_override = load_json(Path(args.with_override).resolve()) if args.with_override else {}
    without_override = load_json(Path(args.without_override).resolve()) if args.without_override else {}

    for eval_item in evals:
        eval_id = int(eval_item.get("id", 0))
        if eval_id <= 0:
            raise ValueError(f"Invalid eval id: {eval_item.get('id')}")

        eval_dir = iteration_dir / f"eval-{eval_id}"

        with_item = get_override(with_override, eval_id)
        with_grading = build_grading(eval_item, with_item)
        with_timing = build_timing(with_item, args.with_default_time, args.with_default_tokens)
        save_json(eval_dir / "with_skill" / "grading.json", with_grading)
        save_json(eval_dir / "with_skill" / "timing.json", with_timing)

        without_item = get_override(without_override, eval_id)
        without_grading = build_grading(eval_item, without_item)
        without_timing = build_timing(without_item, args.without_default_time, args.without_default_tokens)
        save_json(eval_dir / "without_skill" / "grading.json", without_grading)
        save_json(eval_dir / "without_skill" / "timing.json", without_timing)

    eval_manifest = {
        "skill_name": skill_name,
        "evals": [
            {
                "eval_id": int(e.get("id", 0)),
                "tags": [str(t) for t in e.get("tags", [])],
            }
            for e in evals
        ],
    }
    save_json(iteration_dir / "eval_manifest.json", eval_manifest)

    print(f"Generated iteration runs under: {iteration_dir}")

    if args.skip_aggregate:
        return

    aggregate_script = (skill_dir / args.aggregate_script).resolve()
    if not aggregate_script.exists():
        raise FileNotFoundError(f"Aggregate script not found: {aggregate_script}")

    schema_path = (skill_dir / args.schema).resolve()

    cmd = [
        sys.executable,
        str(aggregate_script),
        str(iteration_dir),
        "--skill-name",
        skill_name,
        "--out-json",
        "benchmark.json",
        "--out-md",
        "benchmark.md",
    ]
    if schema_path.exists():
        cmd.extend(["--schema", str(schema_path)])

    subprocess.check_call(cmd)


if __name__ == "__main__":
    main()
