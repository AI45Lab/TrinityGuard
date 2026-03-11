#!/usr/bin/env python3
"""Check benchmark.json against threshold policy.

Usage:
  python check_benchmark_thresholds.py <benchmark.json> <thresholds.json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def get_mean(summary: Dict[str, Any], side: str, metric: str) -> float:
    return float(summary[side][metric]["mean"])


def check_thresholds(benchmark: Dict[str, Any], thresholds: Dict[str, Any]) -> List[str]:
    s = benchmark["summary"]
    errs: List[str] = []

    overall = thresholds.get("overall", {})
    with_skill = overall.get("with_skill", {})

    for metric, min_value in with_skill.get("min", {}).items():
        actual = get_mean(s, "with_skill", metric)
        if actual < float(min_value):
            errs.append(f"with_skill.{metric} mean {actual:.4f} < min {float(min_value):.4f}")

    for metric, max_value in with_skill.get("max", {}).items():
        actual = get_mean(s, "with_skill", metric)
        if actual > float(max_value):
            errs.append(f"with_skill.{metric} mean {actual:.4f} > max {float(max_value):.4f}")

    delta = overall.get("delta", {})
    for metric, min_value in delta.get("min", {}).items():
        actual = float(s["delta"][metric])
        if actual < float(min_value):
            errs.append(f"delta.{metric} {actual:.4f} < min {float(min_value):.4f}")

    segmented = thresholds.get("segmented", {})
    seg_summary = s.get("segmented", {})

    for side in ("with_skill", "without_skill"):
        side_threshold = segmented.get(side, {})
        for segment, rules in side_threshold.items():
            actual_seg = seg_summary.get(side, {}).get(segment, {})
            if not actual_seg:
                errs.append(f"missing segmented summary: {side}.{segment}")
                continue

            for metric, min_value in rules.get("min", {}).items():
                actual = float(actual_seg.get(metric, 0.0))
                if actual < float(min_value):
                    errs.append(f"segmented.{side}.{segment}.{metric} {actual:.4f} < min {float(min_value):.4f}")

            for metric, max_value in rules.get("max", {}).items():
                actual = float(actual_seg.get(metric, 0.0))
                if actual > float(max_value):
                    errs.append(f"segmented.{side}.{segment}.{metric} {actual:.4f} > max {float(max_value):.4f}")

    scenario_req = thresholds.get("scenario_requirements", {})
    scenario_summary = s.get("scenarios", {})
    required_scenarios = scenario_req.get("required", [])
    for scenario in required_scenarios:
        if scenario not in scenario_summary:
            errs.append(f"missing scenario summary: {scenario}")

    scenario_rules = scenario_req.get("with_skill", {})
    for scenario, rules in scenario_rules.items():
        actual_scenario = scenario_summary.get(scenario, {})
        if not actual_scenario:
            errs.append(f"missing scenario details: {scenario}")
            continue

        for metric, min_value in rules.get("min", {}).items():
            actual = float(actual_scenario.get(metric, 0.0))
            if actual < float(min_value):
                errs.append(f"scenario.{scenario}.{metric} {actual:.4f} < min {float(min_value):.4f}")

        for metric, max_value in rules.get("max", {}).items():
            actual = float(actual_scenario.get(metric, 0.0))
            if actual > float(max_value):
                errs.append(f"scenario.{scenario}.{metric} {actual:.4f} > max {float(max_value):.4f}")

    return errs


def main() -> None:
    parser = argparse.ArgumentParser(description="Check benchmark thresholds")
    parser.add_argument("benchmark_json")
    parser.add_argument("thresholds_json")
    args = parser.parse_args()

    benchmark = load_json(Path(args.benchmark_json).resolve())
    thresholds = load_json(Path(args.thresholds_json).resolve())

    errors = check_thresholds(benchmark, thresholds)
    if errors:
        print("[FAIL] benchmark threshold check")
        for e in errors:
            print(f"- {e}")
        raise SystemExit(1)

    print("[OK] benchmark threshold check")


if __name__ == "__main__":
    main()
