"""Summaries for external baseline smoke evidence.

This module intentionally reports smoke evidence separately from publication-grade
comparison readiness. A complete OpenRT smoke matrix plus a completed Garak smoke
report is useful progress, but it is not enough to mark the benchmark comparison
or risk validation gates complete.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .aggregate import validate_benchmark_result

REQUIRED_GARAK_ENTRIES = ("init", "attempt", "eval", "completion", "digest")
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)(authorization|bearer)[\"']?\s*[:=]\s*[\"']?[^\"'\s,}]+"),
)


def build_external_baseline_summary(
    *,
    openrt_artifacts: dict[tuple[str, str], str | Path],
    garak_report: str | Path | None,
    expected_methods: list[str],
    expected_risks: list[str],
) -> dict[str, Any]:
    """Build a non-overclaiming summary of OpenRT and Garak smoke evidence."""
    openrt = _summarize_openrt_artifacts(
        openrt_artifacts=openrt_artifacts,
        expected_methods=expected_methods,
        expected_risks=expected_risks,
    )
    garak = _summarize_garak_report(garak_report)
    return {
        "openrt": openrt,
        "garak": garak,
        "gates": {
            "comparison_ready": False,
            "reason": (
                "External baseline artifacts are smoke-level evidence only; "
                "do not mark Garak/OpenRT comparison complete until a planned "
                "publication-grade comparison report and reproducibility gate exist."
            ),
        },
    }


def write_external_baseline_summary(
    *,
    output_path: str | Path,
    openrt_artifacts: dict[tuple[str, str], str | Path],
    garak_report: str | Path | None,
    expected_methods: list[str],
    expected_risks: list[str],
) -> dict[str, Any]:
    """Build and write an external baseline summary JSON file."""
    summary = build_external_baseline_summary(
        openrt_artifacts=openrt_artifacts,
        garak_report=garak_report,
        expected_methods=expected_methods,
        expected_risks=expected_risks,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def build_publication_readiness_report(
    *,
    summary: dict[str, Any],
    reproducibility_checks: dict[str, bool],
    min_openrt_cases_per_cell: int,
    min_garak_probes: int,
) -> dict[str, Any]:
    """Evaluate whether baseline evidence is ready for publication-grade comparison.

    The current smoke lane is expected to fail this gate until it has more than
    one case per OpenRT risk/method cell and a complete reproducibility manifest.
    """
    openrt_artifacts = summary.get("openrt", {}).get("artifacts", [])
    observed_min_cases = min(
        (int(artifact.get("total_cases", 0)) for artifact in openrt_artifacts),
        default=0,
    )
    garak_probes = summary.get("garak", {}).get("probes", [])
    criteria = {
        "openrt_matrix_complete": _criterion(
            bool(summary.get("openrt", {}).get("matrix_complete", False)),
            "OpenRT smoke matrix is complete."
            if summary.get("openrt", {}).get("matrix_complete", False)
            else "OpenRT smoke matrix is incomplete.",
        ),
        "openrt_min_cases": _criterion(
            observed_min_cases >= min_openrt_cases_per_cell,
            (
                f"minimum observed cases per cell: {observed_min_cases}; "
                f"required: {min_openrt_cases_per_cell}"
            ),
        ),
        "garak_report_complete": _criterion(
            bool(summary.get("garak", {}).get("smoke_report_complete", False)),
            "Garak smoke report is complete."
            if summary.get("garak", {}).get("smoke_report_complete", False)
            else "Garak smoke report is missing or incomplete.",
        ),
        "garak_probe_coverage": _criterion(
            len(garak_probes) >= min_garak_probes,
            f"observed probes: {len(garak_probes)}; required: {min_garak_probes}",
        ),
    }
    criteria.update(_reproducibility_criteria(reproducibility_checks))
    blocking = [name for name, item in criteria.items() if not item["passed"]]
    return {
        "publication_ready": not blocking,
        "blocking_criteria": blocking,
        "criteria": criteria,
    }


def render_publication_readiness_markdown(report: dict[str, Any]) -> str:
    """Render a concise markdown readiness report for human review."""
    status = "READY" if report.get("publication_ready") else "NOT READY"
    lines = [
        "# External Baseline Publication Readiness",
        "",
        f"Publication readiness: {status}",
        "",
        "## Criteria",
        "",
    ]
    for name, criterion in report.get("criteria", {}).items():
        marker = "PASS" if criterion.get("passed") else "BLOCKED"
        lines.append(f"- {marker}: `{name}` — {criterion.get('evidence', '')}")
    lines.extend(["", "## Blocking criteria", ""])
    blockers = report.get("blocking_criteria") or []
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def write_publication_readiness_report(
    *,
    output_json_path: str | Path,
    output_markdown_path: str | Path,
    summary: dict[str, Any],
    reproducibility_checks: dict[str, bool],
    min_openrt_cases_per_cell: int,
    min_garak_probes: int,
) -> dict[str, Any]:
    """Build and write JSON plus markdown publication-readiness reports."""
    report = build_publication_readiness_report(
        summary=summary,
        reproducibility_checks=reproducibility_checks,
        min_openrt_cases_per_cell=min_openrt_cases_per_cell,
        min_garak_probes=min_garak_probes,
    )
    json_path = Path(output_json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    markdown_path = Path(output_markdown_path)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_publication_readiness_markdown(report), encoding="utf-8")
    return report


def build_reproduction_command_manifest(
    *,
    required_env: list[str],
    steps: list[dict[str, Any]],
    artifacts: dict[str, str],
) -> dict[str, Any]:
    """Build a sanitized manifest describing how to reproduce local evidence."""
    return {
        "schema_version": 1,
        "required_env": list(required_env),
        "steps": steps,
        "artifacts": dict(artifacts),
    }


def validate_reproduction_command_manifest(
    manifest: dict[str, Any],
    *,
    required_step_ids: list[str],
    required_artifact_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Validate reproduction command manifest completeness and secret hygiene."""
    observed_step_ids = [
        str(step.get("id", "")) for step in manifest.get("steps", []) if isinstance(step, dict)
    ]
    missing_step_ids = [
        step_id for step_id in required_step_ids if step_id not in observed_step_ids
    ]
    artifacts = manifest.get("artifacts", {})
    observed_artifact_ids = set(artifacts) if isinstance(artifacts, dict) else set()
    missing_artifact_ids = [
        artifact_id
        for artifact_id in (required_artifact_ids or [])
        if artifact_id not in observed_artifact_ids
    ]
    secret_like_findings = _secret_like_findings(manifest)
    return {
        "passed": not missing_step_ids and not missing_artifact_ids and not secret_like_findings,
        "missing_step_ids": missing_step_ids,
        "missing_artifact_ids": missing_artifact_ids,
        "secret_like_findings": secret_like_findings,
    }


def write_reproduction_command_manifest(
    *,
    output_path: str | Path,
    required_env: list[str],
    steps: list[dict[str, Any]],
    artifacts: dict[str, str],
) -> dict[str, Any]:
    """Build, validate for JSON serialization, and write a command manifest."""
    manifest = build_reproduction_command_manifest(
        required_env=required_env,
        steps=steps,
        artifacts=artifacts,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def summarize_openrt_simulation_benchmark(
    benchmark_path: str | Path,
    *,
    expected_modes: list[str],
    expected_risks: list[str],
) -> dict[str, Any]:
    """Summarize the formal OpenRT simulation benchmark aggregate gate."""
    path = Path(benchmark_path)
    if not path.is_file():
        return {
            "benchmark_path": str(path),
            "schema_valid": False,
            "matrix_complete": False,
            "total_results": 0,
            "total_cases": 0,
            "missing": [
                {"mode": mode, "risk": risk} for mode in expected_modes for risk in expected_risks
            ],
            "secret_like_findings": [],
            "error": "benchmark file is missing",
        }

    try:
        benchmark = _read_json(path)
        validate_benchmark_result(benchmark)
    except Exception as exc:
        return {
            "benchmark_path": str(path),
            "schema_valid": False,
            "matrix_complete": False,
            "total_results": 0,
            "total_cases": 0,
            "missing": [],
            "secret_like_findings": _secret_like_findings(path.read_text(encoding="utf-8")),
            "error": str(exc),
        }

    results = benchmark.get("results", [])
    expected_cells = {(mode, risk) for mode in expected_modes for risk in expected_risks}
    observed_cells: set[tuple[str, str]] = set()
    invalid_results: list[dict[str, str]] = []
    total_cases = 0

    for result in results:
        if not isinstance(result, dict):
            continue
        attack_engine = result.get("attack_engine")
        mode = attack_engine.get("mode") if isinstance(attack_engine, dict) else None
        risk = result.get("attack_type")
        if isinstance(mode, str) and isinstance(risk, str):
            observed_cells.add((mode, risk))
        cases = result.get("cases", [])
        if isinstance(cases, list):
            total_cases += len(cases)
            if not _result_has_valid_openrt_engine_metadata(result):
                invalid_results.append({"mode": str(mode), "risk": str(risk)})

    missing = [
        {"mode": mode, "risk": risk} for mode, risk in sorted(expected_cells - observed_cells)
    ]
    secret_like_findings = _secret_like_findings(benchmark)
    return {
        "benchmark_path": str(path),
        "schema_valid": True,
        "matrix_complete": not missing and not invalid_results,
        "total_results": len(results),
        "total_cases": total_cases,
        "missing": missing,
        "invalid_results": invalid_results,
        "secret_like_findings": secret_like_findings,
    }


def build_openrt_simulation_readiness_report(
    *,
    simulation_benchmark: dict[str, Any],
    reproducibility_checks: dict[str, bool],
    min_total_cases: int,
) -> dict[str, Any]:
    """Evaluate whether the OpenRT simulation benchmark evidence is reproducible."""
    aggregate_passed = (
        bool(simulation_benchmark.get("schema_valid", False))
        and bool(simulation_benchmark.get("matrix_complete", False))
        and not simulation_benchmark.get("secret_like_findings")
    )
    criteria = {
        "openrt_simulation_benchmark_aggregate": _criterion(
            aggregate_passed,
            (
                "OpenRT simulation benchmark aggregate is schema-valid, matrix-complete, "
                "and secret-clean."
                if aggregate_passed
                else (
                    "OpenRT simulation benchmark aggregate is incomplete, invalid, "
                    "or not secret-clean."
                )
            ),
        ),
        "openrt_simulation_min_cases": _criterion(
            int(simulation_benchmark.get("total_cases", 0)) >= min_total_cases,
            (
                f"observed total cases: {int(simulation_benchmark.get('total_cases', 0))}; "
                f"required: {min_total_cases}"
            ),
        ),
    }
    criteria.update(_reproducibility_criteria(reproducibility_checks))
    blocking = [name for name, item in criteria.items() if not item["passed"]]
    return {
        "simulation_ready": not blocking,
        "blocking_criteria": blocking,
        "criteria": criteria,
    }


def _summarize_openrt_artifacts(
    *,
    openrt_artifacts: dict[tuple[str, str], str | Path],
    expected_methods: list[str],
    expected_risks: list[str],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    by_method: dict[str, dict[str, Any]] = {
        method: _empty_method_summary() for method in expected_methods
    }
    totals = {
        "total_artifacts": 0,
        "conclusive_artifacts": 0,
        "risk_detected": 0,
        "by_severity": {},
    }

    for method in expected_methods:
        for risk in expected_risks:
            artifact_path = openrt_artifacts.get((method, risk))
            if artifact_path is None or not Path(artifact_path).is_dir():
                missing.append({"method": method, "risk": risk})
                continue
            row = _summarize_openrt_artifact(Path(artifact_path), expected_method=method)
            row.update({"method": method, "risk": risk, "run_dir": str(artifact_path)})
            rows.append(row)
            _add_openrt_row(totals, row)
            _add_openrt_row(by_method[method], row)

    expected_count = len(expected_methods) * len(expected_risks)
    matrix_complete = (
        not missing
        and totals["total_artifacts"] == expected_count
        and totals["conclusive_artifacts"] == expected_count
    )
    return {
        **totals,
        "expected_artifacts": expected_count,
        "matrix_complete": matrix_complete,
        "missing": missing,
        "by_method": by_method,
        "artifacts": rows,
    }


def _summarize_openrt_artifact(path: Path, *, expected_method: str) -> dict[str, Any]:
    _require_files(path)
    metrics = _read_json(path / "metrics.json")
    manifest = _read_json(path / "manifest.json")
    method = manifest.get("openrt_method")
    if method != expected_method:
        raise ValueError(f"artifact method mismatch for {path}: {method} != {expected_method}")
    if not manifest.get("baseline_evidence", False):
        raise ValueError(f"artifact is not marked as baseline evidence: {path}")
    total_cases = int(metrics.get("total_cases", 0))
    conclusive_cases = int(metrics.get("conclusive_cases", 0))
    return {
        "total_cases": total_cases,
        "conclusive_cases": conclusive_cases,
        "conclusive": total_cases > 0 and total_cases == conclusive_cases,
        "risk_detected": int(metrics.get("risk_detected", 0)),
        "inconclusive": int(metrics.get("inconclusive", 0)),
        "risk_rate": metrics.get("risk_rate"),
        "by_severity": dict(metrics.get("by_severity", {})),
    }


def _summarize_garak_report(report_path: str | Path | None) -> dict[str, Any]:
    if report_path is None:
        return {
            "report_path": None,
            "smoke_report_complete": False,
            "entry_counts": {},
            "probes": [],
            "detectors": [],
        }
    path = Path(report_path)
    if not path.is_file():
        return {
            "report_path": str(path),
            "smoke_report_complete": False,
            "entry_counts": {},
            "probes": [],
            "detectors": [],
        }

    entry_counts: dict[str, int] = {}
    probes: set[str] = set()
    detectors: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        entry_type = str(record.get("entry_type", ""))
        entry_counts[entry_type] = entry_counts.get(entry_type, 0) + 1
        if probe := record.get("probe_classname"):
            probes.add(str(probe))
        if detector := record.get("detector"):
            detectors.add(str(detector))

    complete = all(entry_counts.get(entry, 0) > 0 for entry in REQUIRED_GARAK_ENTRIES)
    return {
        "report_path": str(path),
        "smoke_report_complete": complete,
        "entry_counts": entry_counts,
        "probes": sorted(probes),
        "detectors": sorted(detectors),
    }


def _require_files(path: Path) -> None:
    required = {
        "raw_results.jsonl",
        "judge_verdicts.jsonl",
        "metrics.json",
        "manifest.json",
        "run.log",
    }
    missing = sorted(name for name in required if not (path / name).is_file())
    if missing:
        raise ValueError(f"OpenRT artifact missing required files: {path}: {missing}")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _empty_method_summary() -> dict[str, Any]:
    return {
        "total_artifacts": 0,
        "conclusive_artifacts": 0,
        "risk_detected": 0,
        "by_severity": {},
    }


def _add_openrt_row(summary: dict[str, Any], row: dict[str, Any]) -> None:
    summary["total_artifacts"] += 1
    if row["conclusive"]:
        summary["conclusive_artifacts"] += 1
    summary["risk_detected"] += row["risk_detected"]
    for severity, count in row["by_severity"].items():
        summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + count


def _result_has_valid_openrt_engine_metadata(result: dict[str, Any]) -> bool:
    attack_engine = result.get("attack_engine")
    if not isinstance(attack_engine, dict):
        return False
    if attack_engine.get("final_verdict_authority") != "trinityguard_judge":
        return False

    cases = result.get("cases", [])
    if not isinstance(cases, list) or not cases:
        return False
    for case in cases:
        if not isinstance(case, dict):
            return False
        engine_metadata = case.get("engine_metadata")
        if not isinstance(engine_metadata, dict):
            return False
        openrt_metadata = engine_metadata.get("openrt")
        if not isinstance(openrt_metadata, dict):
            return False
    return True


def _criterion(passed: bool, evidence: str) -> dict[str, Any]:
    return {"passed": passed, "evidence": evidence}


def _reproducibility_criteria(checks: dict[str, bool]) -> dict[str, dict[str, Any]]:
    labels = {
        "pip_check": "isolated external-baseline environment pip check",
        "artifact_verification": "all expected artifacts passed verification",
        "secret_scan": "artifact secret-like content scan",
        "command_manifest": "commands/configs needed to reproduce all runs are recorded",
    }
    return {
        f"reproducibility_{name}": _criterion(bool(checks.get(name, False)), label)
        for name, label in labels.items()
    }


def _secret_like_findings(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            findings.extend(_secret_like_findings(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_secret_like_findings(item, f"{path}[{index}]"))
    elif isinstance(value, str) and any(pattern.search(value) for pattern in SECRET_PATTERNS):
        findings.append(path)
    return findings
