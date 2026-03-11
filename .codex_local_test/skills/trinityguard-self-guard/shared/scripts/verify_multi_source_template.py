#!/usr/bin/env python3
"""Verify claim reliability with multi-source consistency rules.

Input JSON (example):
{
  "claim": "service A is down",
  "sources": [
    {"source_id": "tool_1", "kind": "tool", "independent": true, "supports_claim": true},
    {"source_id": "tool_2", "kind": "tool", "independent": true, "supports_claim": true},
    {"source_id": "memory_1", "kind": "internal_verified", "independent": true, "supports_claim": true}
  ]
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

TRUST_RANK = {
    "tool_single_source": 0,
    "tool_multi_source_unverified": 1,
    "internal_unverified": 2,
    "internal_verified": 3,
    "multi_source_verified": 4,
}


def load_json(path: Path) -> Dict[str, Any]:
    # Use utf-8-sig to tolerate BOM from PowerShell-generated JSON files.
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def classify_source(source: Dict[str, Any]) -> str:
    kind = str(source.get("kind", "tool")).strip().lower()
    if kind in {"internal_verified", "internal_unverified", "tool"}:
        return kind
    return "tool"


def assess_claim(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    supports = [s for s in sources if bool(s.get("supports_claim", False))]
    independent_supports = [s for s in supports if bool(s.get("independent", False))]

    kinds = [classify_source(s) for s in supports]
    has_internal_verified = "internal_verified" in kinds
    has_internal_unverified = "internal_unverified" in kinds
    tool_support_count = sum(1 for k in kinds if k == "tool")

    if has_internal_verified and len(independent_supports) >= 2:
        trust_tier = "multi_source_verified"
        confidence = "high"
        decision = "allow"
        reason = "internal verified evidence plus independent corroboration"
    elif has_internal_verified:
        trust_tier = "internal_verified"
        confidence = "medium"
        decision = "allow"
        reason = "internal verified evidence exists"
    elif has_internal_unverified and len(independent_supports) >= 2:
        trust_tier = "internal_unverified"
        confidence = "medium"
        decision = "downgrade"
        reason = "no internal verified source, keep uncertainty statement"
    elif tool_support_count >= 2 and len(independent_supports) >= 2:
        trust_tier = "tool_multi_source_unverified"
        confidence = "medium"
        decision = "downgrade"
        reason = "tool-only corroboration, still lower than internal verified"
    elif tool_support_count >= 1:
        trust_tier = "tool_single_source"
        confidence = "low"
        decision = "downgrade"
        reason = "single tool source must not produce high-confidence conclusion"
    else:
        trust_tier = "tool_single_source"
        confidence = "low"
        decision = "block"
        reason = "no supporting source"

    return {
        "trust_tier": trust_tier,
        "confidence": confidence,
        "decision": decision,
        "reason": reason,
        "supporting_sources": [s.get("source_id") for s in supports],
        "independent_support_count": len(independent_supports),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify claim with multi-source trust policy")
    parser.add_argument("input_json", help="Path to input JSON")
    parser.add_argument("--out", default="-", help="Output path, default stdout")
    args = parser.parse_args()

    data = load_json(Path(args.input_json).resolve())
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("sources must be a list")

    assessment = assess_claim(sources)
    output = {
        "claim": data.get("claim", ""),
        "assessment": assessment,
        "trust_rank": TRUST_RANK[assessment["trust_tier"]],
    }

    if args.out == "-":
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        save_json(Path(args.out).resolve(), output)


if __name__ == "__main__":
    main()
