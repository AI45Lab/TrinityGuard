"""Aggregate real API smoke artifacts into benchmark result JSON."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

RISK_LEVELS = {
    "jailbreak": "L1",
    "prompt_injection": "L1",
    "sensitive_disclosure": "L1",
    "excessive_agency": "L1",
    "code_execution": "L1",
    "hallucination": "L1",
    "memory_poisoning": "L1",
    "tool_misuse": "L1",
    "message_tampering": "L2",
    "malicious_propagation": "L2",
    "misinformation_amplify": "L2",
    "insecure_output": "L2",
    "goal_drift": "L2",
    "identity_spoofing": "L2",
    "cascading_failures": "L3",
    "sandbox_escape": "L3",
    "insufficient_monitoring": "L3",
    "group_hallucination": "L3",
    "malicious_emergence": "L3",
    "rogue_agent": "L3",
}


def aggregate_smoke_runs(run_dirs: list[Path]) -> dict[str, Any]:
    """Aggregate conclusive smoke artifact directories into benchmark JSON."""
    results = []
    total_cases = 0
    total_risk = 0
    by_level_counts = {"L1": [0, 0], "L2": [0, 0], "L3": [0, 0]}
    first_manifest: dict[str, Any] = {}

    for run_dir in run_dirs:
        manifest = _read_json(run_dir / "manifest.json")
        if not first_manifest:
            first_manifest = manifest
        raw_records = _read_jsonl(run_dir / "raw_results.jsonl")
        verdict_records = _read_jsonl(run_dir / "judge_verdicts.jsonl")
        verdict_by_case = {record["case_name"]: record for record in verdict_records}

        if not raw_records:
            raise ValueError(f"{run_dir} has no raw records")
        risk = raw_records[0]["risk"]
        level = RISK_LEVELS.get(risk)
        if level is None:
            raise ValueError(f"Unknown risk level for {risk}")
        attack_engine = _attack_engine_from_manifest(manifest)

        cases = []
        risk_detected = 0
        by_severity = {"critical": 0, "warning": 0, "info": 0}
        for raw in raw_records:
            verdict = verdict_by_case.get(raw["case_name"])
            if verdict is None:
                raise ValueError(f"Missing verdict for {raw['case_name']} in {run_dir}")
            if verdict.get("has_risk") is None or verdict.get("severity") == "inconclusive":
                raise ValueError(f"Cannot aggregate inconclusive verdict in {run_dir}")
            has_risk = bool(verdict["has_risk"])
            severity = str(verdict.get("severity", "none"))
            risk_detected += int(has_risk)
            total_risk += int(has_risk)
            if severity in by_severity:
                by_severity[severity] += 1
            case_result = {
                "case_id": raw["case_name"],
                "attack_input": raw["attack_input"],
                "agent_response": raw["raw_response"],
                "judge_verdict": {
                    "has_risk": has_risk,
                    "severity": severity,
                    "reason": verdict.get("reason", ""),
                    "consensus_votes": "single-smoke-judge",
                },
                "target_agent": raw.get("target_agent") or "",
            }
            engine_metadata = _engine_metadata_from_raw(raw)
            if engine_metadata:
                case_result["engine_metadata"] = engine_metadata
            cases.append(case_result)

        total_cases += len(cases)
        by_level_counts[level][0] += risk_detected
        by_level_counts[level][1] += len(cases)
        attack_result = {
            "attack_type": risk,
            "level": level,
            "cases": cases,
            "summary": {
                "total_cases": len(cases),
                "risk_detected": risk_detected,
                "attack_success_rate": risk_detected / len(cases) if cases else 0.0,
                "by_severity": by_severity,
            },
        }
        if attack_engine:
            attack_result["attack_engine"] = attack_engine
        results.append(attack_result)

    benchmark = {
        "run_id": str(uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "trinityguard_version": "2.0.0-dev",
        "mas_config": {
            "framework": "real_api_smoke",
            "agents": [
                {
                    "name": "assistant",
                    "role": "real_api_target",
                    "model": first_manifest.get("target_model", "unknown"),
                }
            ],
            "mode": "direct",
        },
        "llm_config": {
            "mas_model": first_manifest.get("target_model", "unknown"),
            "judge_model": first_manifest.get("judge_model", "unknown"),
            "judge_consensus_n": 1,
        },
        "results": results,
        "overall_summary": {
            "total_attacks": len(results),
            "total_cases": total_cases,
            "overall_risk_rate": total_risk / total_cases if total_cases else 0.0,
            "by_level": {
                level: counts[0] / counts[1] if counts[1] else 0.0
                for level, counts in by_level_counts.items()
            },
            "total_cost_usd": 0.0,
            "total_duration_seconds": 0.0,
        },
    }
    validate_benchmark_result(benchmark)
    return benchmark


def validate_benchmark_result(result: dict[str, Any]) -> None:
    """Validate the project benchmark schema subset without external dependencies."""
    required_top = {
        "run_id",
        "timestamp",
        "trinityguard_version",
        "mas_config",
        "llm_config",
        "results",
        "overall_summary",
    }
    _require_keys(result, required_top, "benchmark")
    if not isinstance(result["results"], list):
        raise ValueError("benchmark.results must be a list")
    for idx, attack_result in enumerate(result["results"]):
        _require_keys(
            attack_result, {"attack_type", "level", "cases", "summary"}, f"results[{idx}]"
        )
        if attack_result["level"] not in {"L1", "L2", "L3"}:
            raise ValueError(f"invalid level in results[{idx}]")
        attack_engine = attack_result.get("attack_engine")
        if attack_engine is not None:
            _require_keys(
                attack_engine,
                {"mode", "method", "evidence_scope", "final_verdict_authority"},
                f"results[{idx}].attack_engine",
            )
            if attack_engine["mode"] not in {
                "static",
                "openrt_direct",
                "openrt_pair",
                "openrt_crescendo",
            }:
                raise ValueError(f"invalid attack_engine.mode in results[{idx}]")
            if attack_engine["final_verdict_authority"] != "trinityguard_judge":
                raise ValueError(f"invalid attack_engine.final_verdict_authority in results[{idx}]")
        for case_idx, case in enumerate(attack_result["cases"]):
            _require_keys(
                case,
                {"case_id", "attack_input", "agent_response", "judge_verdict"},
                f"results[{idx}].cases[{case_idx}]",
            )
            verdict = case["judge_verdict"]
            _require_keys(verdict, {"has_risk", "severity", "reason"}, "judge_verdict")
            if not isinstance(verdict["has_risk"], bool):
                raise ValueError("judge_verdict.has_risk must be boolean")
            if verdict["severity"] not in {"none", "info", "warning", "critical"}:
                raise ValueError("judge_verdict.severity is invalid")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _attack_engine_from_manifest(manifest: dict[str, Any]) -> dict[str, Any] | None:
    method = manifest.get("openrt_method")
    if not isinstance(method, str) or not method:
        return None
    return {
        "mode": _openrt_mode(method),
        "method": method,
        "evidence_scope": _simulation_evidence_scope(manifest),
        "final_verdict_authority": "trinityguard_judge",
    }


def _engine_metadata_from_raw(raw: dict[str, Any]) -> dict[str, Any] | None:
    metadata = raw.get("metadata")
    if not isinstance(metadata, dict):
        return None
    openrt_metadata = metadata.get("openrt")
    if not isinstance(openrt_metadata, dict):
        return None
    return {"openrt": openrt_metadata}


def _openrt_mode(method: str) -> str:
    method_modes = {
        "direct_attack": "openrt_direct",
        "pair_attack": "openrt_pair",
        "crescendo": "openrt_crescendo",
    }
    return method_modes.get(method, f"openrt_{method}")


def _simulation_evidence_scope(manifest: dict[str, Any]) -> str:
    evidence_scope = manifest.get("evidence_scope")
    if isinstance(evidence_scope, str) and evidence_scope:
        return evidence_scope.replace("baseline", "simulation")
    return "simulation_smoke_candidate"


def _require_keys(mapping: dict[str, Any], keys: set[str], label: str) -> None:
    missing = keys - set(mapping)
    if missing:
        raise ValueError(f"{label} missing required keys: {sorted(missing)}")
