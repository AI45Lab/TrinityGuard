#!/usr/bin/env python3
"""Validate the local Phase 2 runtime MVP evidence bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trinityguard.runtime.validation import build_runtime_mvp_validation_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--unit-tests-passed", action="store_true")
    parser.add_argument("--phase1-minset-ready", action="store_true")
    parser.add_argument("--phase1-extension-ready", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_runtime_mvp_validation_report(
        args.summary,
        unit_tests_passed=args.unit_tests_passed,
        phase1_minset_ready=args.phase1_minset_ready,
        phase1_extension_ready=args.phase1_extension_ready,
    )
    if report["runtime_mvp_ready"]:
        print("runtime_mvp_validation=ready")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    print("runtime_mvp_validation=blocked", file=sys.stderr)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
