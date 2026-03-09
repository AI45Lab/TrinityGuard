#!/usr/bin/env python3
"""Aggregate self-guard benchmark results from a simple iteration directory.

Directory convention (template):
  <iteration_dir>/
    eval-1/
      with_skill/
        grading.json
        timing.json
      without_skill/
        grading.json
        timing.json
    eval-2/
      ...

This script is intentionally lightweight and platform-agnostic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    # Use utf-8-sig to tolerate BOM from PowerShell-generated JSON files.
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def summarize(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "min": 0.0, "max": 0.0}
    n = len(values)
    mean = sum(values) / n
    return {"mean": mean, "min": min(values), "max": max(values)}


def parse_run(eval_dir: Path, configuration: str, tags_map: Dict[int, List[str]]) -> Dict[str, Any]:
    run_dir = eval_dir / configuration
    grading_path = run_dir / "grading.json"
    timing_path = run_dir / "timing.json"

    if not grading_path.exists():
        raise FileNotFoundError(f"Missing grading.json: {grading_path}")

    grading = load_json(grading_path)
    timing = load_json(timing_path) if timing_path.exists() else {}

    summary = grading.get("summary", {})
    expectations = grading.get("expectations", [])

    eval_id = safe_int(eval_dir.name.replace("eval-", ""), 0)
    return {
        "eval_id": eval_id,
        "eval_name": eval_dir.name,
        "configuration": configuration,
        "tags": tags_map.get(eval_id, []),
        "result": {
            "pass_rate": safe_float(summary.get("pass_rate", 0.0)),
            "passed": safe_int(summary.get("passed", 0)),
            "failed": safe_int(summary.get("failed", 0)),
            "total": safe_int(summary.get("total", 0)),
            "false_positives": safe_int(summary.get("false_positives", 0)),
            "false_negatives": safe_int(summary.get("false_negatives", 0)),
            "false_positive_rate": safe_float(summary.get("false_positive_rate", 0.0)),
            "false_negative_rate": safe_float(summary.get("false_negative_rate", 0.0)),
            "time_seconds": safe_float(timing.get("total_duration_seconds", 0.0)),
            "tokens": safe_int(timing.get("total_tokens", 0)),
        },
        "expectations": expectations,
    }


def load_tags_map(iteration_dir: Path) -> Dict[int, List[str]]:
    manifest_path = iteration_dir / "eval_manifest.json"
    if not manifest_path.exists():
        return {}
    manifest = load_json(manifest_path)
    evals = manifest.get("evals", [])
    tags_map: Dict[int, List[str]] = {}
    for item in evals:
        eval_id = safe_int(item.get("eval_id", 0), 0)
        if eval_id <= 0:
            continue
        tags = [str(t) for t in item.get("tags", [])]
        tags_map[eval_id] = tags
    return tags_map


def collect_runs(iteration_dir: Path) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    tags_map = load_tags_map(iteration_dir)
    for eval_dir in sorted(iteration_dir.glob("eval-*")):
        if not eval_dir.is_dir():
            continue
        for cfg in ("with_skill", "without_skill"):
            cfg_dir = eval_dir / cfg
            if cfg_dir.exists():
                runs.append(parse_run(eval_dir, cfg, tags_map))
    return runs


def build_summary(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, Dict[str, List[float]]] = {
        "with_skill": {
            "pass_rate": [],
            "false_positive_rate": [],
            "false_negative_rate": [],
            "time_seconds": [],
            "tokens": [],
        },
        "without_skill": {
            "pass_rate": [],
            "false_positive_rate": [],
            "false_negative_rate": [],
            "time_seconds": [],
            "tokens": [],
        },
    }

    for r in runs:
        cfg = r["configuration"]
        grouped[cfg]["pass_rate"].append(safe_float(r["result"]["pass_rate"]))
        grouped[cfg]["false_positive_rate"].append(safe_float(r["result"]["false_positive_rate"]))
        grouped[cfg]["false_negative_rate"].append(safe_float(r["result"]["false_negative_rate"]))
        grouped[cfg]["time_seconds"].append(safe_float(r["result"]["time_seconds"]))
        grouped[cfg]["tokens"].append(float(safe_int(r["result"]["tokens"])))

    with_skill = {
        "pass_rate": summarize(grouped["with_skill"]["pass_rate"]),
        "false_positive_rate": summarize(grouped["with_skill"]["false_positive_rate"]),
        "false_negative_rate": summarize(grouped["with_skill"]["false_negative_rate"]),
        "time_seconds": summarize(grouped["with_skill"]["time_seconds"]),
        "tokens": summarize(grouped["with_skill"]["tokens"]),
    }
    without_skill = {
        "pass_rate": summarize(grouped["without_skill"]["pass_rate"]),
        "false_positive_rate": summarize(grouped["without_skill"]["false_positive_rate"]),
        "false_negative_rate": summarize(grouped["without_skill"]["false_negative_rate"]),
        "time_seconds": summarize(grouped["without_skill"]["time_seconds"]),
        "tokens": summarize(grouped["without_skill"]["tokens"]),
    }

    delta = {
        "pass_rate": with_skill["pass_rate"]["mean"] - without_skill["pass_rate"]["mean"],
        "false_positive_rate": with_skill["false_positive_rate"]["mean"]
        - without_skill["false_positive_rate"]["mean"],
        "false_negative_rate": with_skill["false_negative_rate"]["mean"]
        - without_skill["false_negative_rate"]["mean"],
        "time_seconds": with_skill["time_seconds"]["mean"] - without_skill["time_seconds"]["mean"],
        "tokens": with_skill["tokens"]["mean"] - without_skill["tokens"]["mean"],
    }

    summary = {
        "with_skill": with_skill,
        "without_skill": without_skill,
        "delta": delta,
    }
    summary["segmented"] = build_segmented_summary(runs)
    return summary


def summarize_segment(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not runs:
        return {
            "count": 0,
            "pass_rate": 0.0,
            "false_positive_rate": 0.0,
            "false_negative_rate": 0.0,
        }
    n = len(runs)
    return {
        "count": n,
        "pass_rate": sum(safe_float(r["result"]["pass_rate"]) for r in runs) / n,
        "false_positive_rate": sum(safe_float(r["result"]["false_positive_rate"]) for r in runs) / n,
        "false_negative_rate": sum(safe_float(r["result"]["false_negative_rate"]) for r in runs) / n,
    }


def build_segmented_summary(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Dict[str, Dict[str, Any]]] = {"with_skill": {}, "without_skill": {}}
    for cfg in ("with_skill", "without_skill"):
        cfg_runs = [r for r in runs if r["configuration"] == cfg]
        for tag in ("benign", "adversarial"):
            tagged = [r for r in cfg_runs if tag in r.get("tags", [])]
            result[cfg][tag] = summarize_segment(tagged)
    return result


def maybe_validate_schema(benchmark: Dict[str, Any], schema_path: Path | None) -> Tuple[bool, str]:
    if schema_path is None or not schema_path.exists():
        return True, "schema not provided"

    try:
        import jsonschema  # type: ignore
    except Exception:
        return True, "jsonschema not installed, skipped"

    schema = load_json(schema_path)
    try:
        jsonschema.validate(instance=benchmark, schema=schema)
        return True, "schema validation passed"
    except Exception as e:
        return False, f"schema validation failed: {e}"


def write_markdown(path: Path, benchmark: Dict[str, Any], schema_note: str) -> None:
    s = benchmark["summary"]
    lines = [
        "# Benchmark Summary",
        "",
        f"- Skill: `{benchmark['metadata']['skill_name']}`",
        f"- Timestamp: `{benchmark['metadata']['timestamp']}`",
        f"- Schema: {schema_note}",
        "",
        "## Mean Metrics",
        "",
        f"- with_skill pass_rate: `{s['with_skill']['pass_rate']['mean']:.4f}`",
        f"- without_skill pass_rate: `{s['without_skill']['pass_rate']['mean']:.4f}`",
        f"- delta pass_rate: `{s['delta']['pass_rate']:.4f}`",
        "",
        f"- with_skill false_positive_rate: `{s['with_skill']['false_positive_rate']['mean']:.4f}`",
        f"- without_skill false_positive_rate: `{s['without_skill']['false_positive_rate']['mean']:.4f}`",
        f"- delta false_positive_rate: `{s['delta']['false_positive_rate']:.4f}`",
        "",
        f"- with_skill false_negative_rate: `{s['with_skill']['false_negative_rate']['mean']:.4f}`",
        f"- without_skill false_negative_rate: `{s['without_skill']['false_negative_rate']['mean']:.4f}`",
        f"- delta false_negative_rate: `{s['delta']['false_negative_rate']:.4f}`",
        "",
        f"- with_skill time_seconds: `{s['with_skill']['time_seconds']['mean']:.2f}`",
        f"- without_skill time_seconds: `{s['without_skill']['time_seconds']['mean']:.2f}`",
        f"- delta time_seconds: `{s['delta']['time_seconds']:.2f}`",
        "",
        f"- with_skill tokens: `{s['with_skill']['tokens']['mean']:.1f}`",
        f"- without_skill tokens: `{s['without_skill']['tokens']['mean']:.1f}`",
        f"- delta tokens: `{s['delta']['tokens']:.1f}`",
        "",
        "## Segmented Metrics",
        "",
        f"- with_skill benign: pass_rate=`{s['segmented']['with_skill']['benign']['pass_rate']:.4f}`, "
        f"fpr=`{s['segmented']['with_skill']['benign']['false_positive_rate']:.4f}`, "
        f"fnr=`{s['segmented']['with_skill']['benign']['false_negative_rate']:.4f}`",
        f"- without_skill benign: pass_rate=`{s['segmented']['without_skill']['benign']['pass_rate']:.4f}`, "
        f"fpr=`{s['segmented']['without_skill']['benign']['false_positive_rate']:.4f}`, "
        f"fnr=`{s['segmented']['without_skill']['benign']['false_negative_rate']:.4f}`",
        f"- with_skill adversarial: pass_rate=`{s['segmented']['with_skill']['adversarial']['pass_rate']:.4f}`, "
        f"fpr=`{s['segmented']['with_skill']['adversarial']['false_positive_rate']:.4f}`, "
        f"fnr=`{s['segmented']['with_skill']['adversarial']['false_negative_rate']:.4f}`",
        f"- without_skill adversarial: pass_rate=`{s['segmented']['without_skill']['adversarial']['pass_rate']:.4f}`, "
        f"fpr=`{s['segmented']['without_skill']['adversarial']['false_positive_rate']:.4f}`, "
        f"fnr=`{s['segmented']['without_skill']['adversarial']['false_negative_rate']:.4f}`",
        "",
        "## Runs",
        "",
    ]

    for run in benchmark["runs"]:
        r = run["result"]
        lines.append(
            f"- `{run['eval_name']}` `{run['configuration']}`: "
            f"pass_rate={r['pass_rate']:.4f}, fpr={r['false_positive_rate']:.4f}, "
            f"fnr={r['false_negative_rate']:.4f}, tags={run.get('tags', [])}, "
            f"time={r['time_seconds']:.2f}s, tokens={r['tokens']}"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate self-guard benchmark results")
    parser.add_argument("iteration_dir", help="Path to iteration directory")
    parser.add_argument("--skill-name", required=True, help="Skill name")
    parser.add_argument("--schema", default=None, help="Optional benchmark schema path")
    parser.add_argument("--out-json", default="benchmark.json", help="Output benchmark JSON filename")
    parser.add_argument("--out-md", default="benchmark.md", help="Output benchmark markdown filename")
    args = parser.parse_args()

    iteration_dir = Path(args.iteration_dir).resolve()
    if not iteration_dir.exists():
        raise FileNotFoundError(f"Iteration dir not found: {iteration_dir}")

    runs = collect_runs(iteration_dir)
    if not runs:
        raise RuntimeError(f"No runs found under: {iteration_dir}")

    benchmark = {
        "metadata": {
            "skill_name": args.skill_name,
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
            "configurations": ["with_skill", "without_skill"],
        },
        "runs": runs,
        "summary": build_summary(runs),
    }

    schema_path = Path(args.schema).resolve() if args.schema else None
    ok, schema_note = maybe_validate_schema(benchmark, schema_path)
    if not ok:
        raise RuntimeError(schema_note)

    out_json = iteration_dir / args.out_json
    out_md = iteration_dir / args.out_md
    out_json.write_text(json.dumps(benchmark, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(out_md, benchmark, schema_note)

    print(f"Saved: {out_json}")
    print(f"Saved: {out_md}")
    print(f"Schema: {schema_note}")


if __name__ == "__main__":
    main()
