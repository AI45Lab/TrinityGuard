#!/usr/bin/env python3
"""Verify a local TrinityGuard runtime report artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trinityguard.runtime.reporting import verify_runtime_report_artifact  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="Runtime report artifact JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = verify_runtime_report_artifact(args.artifact)
    except Exception as exc:  # noqa: BLE001 - CLI should turn verifier errors into exit code.
        print(f"runtime_report_artifact=invalid error={exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
