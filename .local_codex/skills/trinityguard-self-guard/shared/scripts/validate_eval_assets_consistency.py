#!/usr/bin/env python3
"""Validate consistency between evals.json and eval_metadata_examples.

Checks:
1. every eval id in evals.json has matching eval-<id>.json
2. no extra eval-<id>.json outside evals.json ids
3. metadata prompt equals eval prompt
4. metadata assertions length equals eval expectations length
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def collect_eval_ids(evals: List[Dict[str, Any]]) -> Set[int]:
    ids: Set[int] = set()
    for e in evals:
        eval_id = int(e.get("id", 0))
        if eval_id <= 0:
            raise ValueError(f"Invalid eval id in evals.json: {e.get('id')}")
        if eval_id in ids:
            raise ValueError(f"Duplicate eval id in evals.json: {eval_id}")
        ids.add(eval_id)
    return ids


def validate_one_skill(skill_dir: Path) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    evals_path = skill_dir / "evals" / "evals.json"
    meta_dir = skill_dir / "evals" / "eval_metadata_examples"

    if not evals_path.exists():
        return False, [f"missing evals.json: {evals_path}"]
    if not meta_dir.exists():
        return False, [f"missing eval_metadata_examples: {meta_dir}"]

    evals_data = load_json(evals_path)
    evals = evals_data.get("evals", [])
    if not isinstance(evals, list):
        return False, [f"invalid evals list: {evals_path}"]

    valid_tags = {"benign", "adversarial"}

    for eval_item in evals:
        tags = eval_item.get("tags", [])
        eval_id = int(eval_item.get("id", 0))
        if not isinstance(tags, list) or not tags:
            issues.append(f"missing or invalid tags for eval-{eval_id}")
            continue
        invalid = [t for t in tags if str(t) not in valid_tags]
        if invalid:
            issues.append(f"invalid tags for eval-{eval_id}: {invalid}")

    eval_ids = collect_eval_ids(evals)

    meta_files = list(meta_dir.glob("eval-*.json"))
    meta_ids: Set[int] = set()

    for path in meta_files:
        stem = path.stem
        try:
            meta_id = int(stem.replace("eval-", ""))
        except Exception:
            issues.append(f"invalid metadata filename: {path}")
            continue

        meta_ids.add(meta_id)
        meta = load_json(path)
        if int(meta.get("eval_id", 0)) != meta_id:
            issues.append(f"eval_id mismatch in {path.name}")

        eval_item = next((x for x in evals if int(x.get("id", 0)) == meta_id), None)
        if eval_item is None:
            issues.append(f"metadata has extra eval id {meta_id} in {path.name}")
            continue

        prompt = str(eval_item.get("prompt", "")).strip()
        if str(meta.get("prompt", "")).strip() != prompt:
            issues.append(f"prompt mismatch for eval-{meta_id}")

        expected_count = len(eval_item.get("expectations", []))
        assertion_count = len(meta.get("assertions", []))
        if expected_count != assertion_count:
            issues.append(
                f"assertion count mismatch for eval-{meta_id}: "
                f"expectations={expected_count}, assertions={assertion_count}"
            )

    missing_meta = sorted(eval_ids - meta_ids)
    extra_meta = sorted(meta_ids - eval_ids)
    for i in missing_meta:
        issues.append(f"missing metadata file eval-{i}.json")
    for i in extra_meta:
        issues.append(f"extra metadata file eval-{i}.json")

    return len(issues) == 0, issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate eval assets consistency")
    parser.add_argument("skills_root", help="Root folder that contains skill subfolders")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any skill has issues")
    args = parser.parse_args()

    root = Path(args.skills_root).resolve()
    if not root.exists():
        raise FileNotFoundError(f"skills root not found: {root}")

    skill_dirs = [p for p in root.iterdir() if p.is_dir() and (p / "evals" / "evals.json").exists()]
    if not skill_dirs:
        raise RuntimeError(f"no skill dirs with evals.json under: {root}")

    any_issue = False
    for skill_dir in sorted(skill_dirs):
        ok, issues = validate_one_skill(skill_dir)
        if ok:
            print(f"[OK] {skill_dir.name}")
            continue

        any_issue = True
        print(f"[FAIL] {skill_dir.name}")
        for issue in issues:
            print(f"  - {issue}")

    if any_issue and args.strict:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
