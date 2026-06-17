"""Phase 3 production-boundary readiness validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .validation import build_runtime_mvp_validation_report

REPORT_TYPE = "trinityguard.phase3_readiness.v1"
REQUIRED_NON_GOALS = [
    "production deployment",
    "production telemetry",
    "Garak/OpenRT comparison",
]
TRACKS = [
    ("adapter_contract", "adapter_contract_path"),
    ("production_boundary_plan", "production_boundary_path"),
    ("external_comparison_plan", "external_comparison_path"),
]


def build_phase3_readiness_report(
    phase2_summary: str | Path | dict[str, Any],
    *,
    unit_tests_passed: bool,
    phase1_minset_ready: bool,
    phase1_extension_ready: bool,
    adapter_contract_path: str | Path,
    production_boundary_path: str | Path,
    external_comparison_path: str | Path,
) -> dict[str, Any]:
    """Validate the Phase 3 production-boundary package.

    Phase 3 readiness is deliberately not production readiness. This gate checks
    that the adapter contract and production-adjacent planning artifacts exist,
    that the Phase 2 local runtime MVP gate is ready, and that non-goals remain
    explicit.
    """

    paths = {
        "adapter_contract_path": Path(adapter_contract_path),
        "production_boundary_path": Path(production_boundary_path),
        "external_comparison_path": Path(external_comparison_path),
    }
    blocking: list[str] = []
    completed_tracks: list[str] = []

    phase2_report = build_runtime_mvp_validation_report(
        phase2_summary,
        unit_tests_passed=unit_tests_passed,
        phase1_minset_ready=phase1_minset_ready,
        phase1_extension_ready=phase1_extension_ready,
    )
    if not phase2_report["runtime_mvp_ready"]:
        blocking.append("phase2_runtime_mvp_gate")

    for track, key in TRACKS:
        path = paths[key]
        if not _document_satisfies_phase3_boundary(path):
            blocking.append(track)
            continue
        completed_tracks.append(track)

    return {
        "report_type": REPORT_TYPE,
        "phase3_ready": not blocking,
        "production_ready": False,
        "blocking_criteria": sorted(set(blocking)),
        "completed_tracks": completed_tracks,
        "phase2_runtime_mvp_ready": phase2_report["runtime_mvp_ready"],
        "phase2_validated_artifacts": phase2_report["validated_artifacts"],
        "unit_tests_passed": bool(unit_tests_passed),
        "phase1_minset_ready": bool(phase1_minset_ready),
        "phase1_extension_ready": bool(phase1_extension_ready),
        "non_goals": REQUIRED_NON_GOALS,
        "artifact_paths": {key: str(path) for key, path in paths.items()},
    }


def write_phase3_readiness_report(report: dict[str, Any], output_path: str | Path) -> None:
    """Write the Phase 3 readiness report as JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _document_satisfies_phase3_boundary(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    required = [
        "Phase 3",
        "not production-ready",
        "production deployment",
        "Garak/OpenRT comparison",
    ]
    return all(item in text for item in required)
