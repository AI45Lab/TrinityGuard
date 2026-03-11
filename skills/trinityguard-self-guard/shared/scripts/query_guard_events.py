#!/usr/bin/env python3
"""Query TrinityGuard JSONL events with simple filters."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query self-guard JSONL events")
    parser.add_argument("events_log", help="Path to JSONL events file")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--turn-id", default="")
    parser.add_argument("--event-type", default="")
    parser.add_argument("--decision", default="")
    parser.add_argument("--reason-code", default="")
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args()


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def match_event(event: Dict[str, Any], args: argparse.Namespace) -> bool:
    if args.session_id and str(event.get("session_id", "")) != args.session_id:
        return False
    if args.turn_id and str(event.get("turn_id", "")) != args.turn_id:
        return False
    if args.event_type and str(event.get("event_type", "")) != args.event_type:
        return False
    if args.decision and str(event.get("decision", "")) != args.decision:
        return False
    if args.reason_code:
        reason_codes = {str(x) for x in event.get("reason_codes", [])}
        if args.reason_code not in reason_codes:
            return False
    return True


def render_summary(event: Dict[str, Any]) -> str:
    ts = str(event.get("ts", ""))
    ev = str(event.get("event_type", ""))
    decision = str(event.get("decision", ""))
    session = str(event.get("session_id", ""))
    turn = str(event.get("turn_id", ""))
    reasons = ",".join(event.get("reason_codes", []))
    return f"{ts} | {ev:20} | {decision:10} | {session}/{turn} | {reasons}"


def main() -> None:
    args = parse_args()
    path = Path(args.events_log).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Events log not found: {path}")

    matched: List[Dict[str, Any]] = []
    for event in read_jsonl(path):
        if match_event(event, args):
            matched.append(event)

    if not matched:
        print("No matching events.")
        return

    limit = max(1, args.limit)
    for event in matched[-limit:]:
        print(render_summary(event))


if __name__ == "__main__":
    main()
