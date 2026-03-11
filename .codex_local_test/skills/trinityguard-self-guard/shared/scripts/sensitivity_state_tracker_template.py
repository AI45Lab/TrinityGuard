#!/usr/bin/env python3
"""Track session-level sensitivity state for self-guard workflows.

Input JSON (example):
{
  "current_state": "normal",
  "events": [
    {"type": "read_file", "tags": ["config"]},
    {"type": "read_secret", "tags": ["token"]}
  ]
}

Output JSON (example):
{
  "previous_state": "normal",
  "current_state": "highly_sensitive",
  "state_changed": true,
  "reasons": ["secret-like material observed"],
  "must_trigger_output_guard": true
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

STATE_ORDER = {"normal": 0, "sensitive": 1, "highly_sensitive": 2}
VALID_STATES = set(STATE_ORDER.keys())

SENSITIVE_EVENT_TYPES = {
    "read_config",
    "read_log",
    "read_file_sensitive",
    "read_db_export",
}

HIGHLY_SENSITIVE_EVENT_TYPES = {
    "read_secret",
    "read_credential",
    "read_private_pii",
    "read_key_material",
}

SENSITIVE_TAGS = {
    "password",
    "token",
    "secret",
    "api_key",
    "credential",
    "pii",
    "private",
}


def load_json(path: Path) -> Dict[str, Any]:
    # Use utf-8-sig to tolerate BOM from PowerShell-generated JSON files.
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_state(state: str) -> str:
    return state if state in VALID_STATES else "normal"


def elevate_state(current: str, candidate: str) -> str:
    return candidate if STATE_ORDER[candidate] > STATE_ORDER[current] else current


def evaluate_events(current_state: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    state = normalize_state(current_state)
    reasons: List[str] = []

    for event in events:
        event_type = str(event.get("type", "")).strip().lower()
        tags = [str(t).strip().lower() for t in event.get("tags", [])]

        if event_type in HIGHLY_SENSITIVE_EVENT_TYPES:
            state = elevate_state(state, "highly_sensitive")
            reasons.append(f"event {event_type} is highly sensitive")
            continue

        if event_type in SENSITIVE_EVENT_TYPES:
            state = elevate_state(state, "sensitive")
            reasons.append(f"event {event_type} is sensitive")

        if any(tag in SENSITIVE_TAGS for tag in tags):
            candidate = "highly_sensitive" if ("secret" in tags or "credential" in tags) else "sensitive"
            state = elevate_state(state, candidate)
            reasons.append("secret-like material observed")

    if not reasons:
        reasons.append("no new sensitive indicators")

    return {
        "current_state": state,
        "reasons": reasons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Track sensitivity state for self-guard")
    parser.add_argument("input_json", help="Path to input JSON")
    parser.add_argument("--out", default="-", help="Output file path, default stdout")
    args = parser.parse_args()

    data = load_json(Path(args.input_json).resolve())
    previous_state = normalize_state(str(data.get("current_state", "normal")))
    events = data.get("events", [])

    if not isinstance(events, list):
        raise ValueError("events must be a list")

    result = evaluate_events(previous_state, events)
    output = {
        "previous_state": previous_state,
        "current_state": result["current_state"],
        "state_changed": result["current_state"] != previous_state,
        "reasons": result["reasons"],
        "must_trigger_output_guard": result["current_state"] in {"sensitive", "highly_sensitive"},
    }

    if args.out == "-":
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        save_json(Path(args.out).resolve(), output)


if __name__ == "__main__":
    main()
