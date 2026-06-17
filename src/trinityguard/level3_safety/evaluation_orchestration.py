"""First-class judge-backed pre-deployment evaluation orchestration."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .attacks.base import AttackRunResult
from .judges.base import BaseJudge
from .judges.evaluation import AttackEvaluationReport, evaluate_attack_run_result

SCHEMA_VERSION = "trinityguard.predeployment_evaluation.v1"


def run_predeployment_evaluation(
    *,
    risk_tests: dict[str, Any],
    intermediary: Any,
    selected_tests: list[str] | None = None,
    judge: BaseJudge | dict[str, BaseJudge] | None = None,
    task: str | None = None,
    progress_callback: Any | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run selected attacks and return raw + judge-backed vulnerability reports.

    Raw ``AttackRunResult`` artifacts remain separate from judge-backed
    ``AttackEvaluationReport`` artifacts so execution success cannot be confused
    with safety pass/fail status.
    """

    selected = selected_tests or list(risk_tests)
    raw_results: dict[str, AttackRunResult] = {}
    reports: dict[str, AttackEvaluationReport] = {}
    rows: list[dict[str, Any]] = []

    for index, name in enumerate(selected, start=1):
        attack = risk_tests.get(name)
        if attack is None:
            rows.append(_missing_row(name, "risk test is not registered"))
            continue
        if progress_callback:
            progress_callback(index, len(selected))

        run_kwargs = dict(kwargs)
        if task is not None:
            run_kwargs["task"] = task
        run_result = attack.run(intermediary, **run_kwargs)
        raw_results[name] = run_result

        selected_judge = _judge_for(name, judge)
        if selected_judge is None:
            rows.append(_missing_row(name, "judge is not configured"))
            continue

        cases_by_name = {case.name: case for case in _safe_load_cases(attack)}
        report = evaluate_attack_run_result(
            run_result,
            judge=selected_judge,
            cases_by_name=cases_by_name,
        )
        reports[name] = report
        rows.extend(_report_rows(report))

    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_id": str(uuid4()),
        "raw_attack_results": {name: result.to_dict() for name, result in raw_results.items()},
        "evaluation_reports": {name: report.to_dict() for name, report in reports.items()},
        "report_rows": rows,
        "summary": _summary(rows),
    }


def _judge_for(name: str, judge: BaseJudge | dict[str, BaseJudge] | None) -> BaseJudge | None:
    if isinstance(judge, dict):
        return judge.get(name) or judge.get("default")
    return judge


def _safe_load_cases(attack: Any) -> list[Any]:
    loader = getattr(attack, "load_cases", None)
    if not callable(loader):
        return []
    try:
        return list(loader())
    except Exception:
        return []


def _missing_row(risk: str, reason: str) -> dict[str, Any]:
    return {
        "risk": risk,
        "entity": "unknown",
        "case_name": "missing",
        "judge_backed": False,
        "has_risk": None,
        "severity": "inconclusive",
        "recommended_action": "log",
        "inconclusive": True,
        "error": reason,
        "evidence_refs": {},
        "provider_blocked": False,
        "provider_block_reason": None,
    }


def _report_rows(report: AttackEvaluationReport) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for verdict in report.verdicts:
        package = verdict.evidence_package
        rows.append(
            {
                "risk": verdict.attack_type,
                "tier": report.level.upper(),
                "entity": package.target_entity if package else "unknown",
                "case_name": verdict.case_name,
                "judge_backed": (
                    not verdict.inconclusive
                    and not verdict.provider_blocked
                    and verdict.judge_type != "unknown"
                ),
                "has_risk": verdict.has_risk,
                "severity": verdict.severity,
                "recommended_action": verdict.recommended_action,
                "inconclusive": verdict.inconclusive,
                "error": verdict.error,
                "judge_type": verdict.judge_type,
                "evidence_refs": package.payload_refs if package else {},
                "sufficiency_status": verdict.sufficiency_status,
                "provider_blocked": verdict.provider_blocked,
                "provider_block_reason": verdict.provider_block_reason,
            }
        )
    return rows


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    inconclusive = sum(1 for row in rows if row.get("inconclusive") is True)
    judge_backed = sum(1 for row in rows if row.get("judge_backed") is True)
    provider_blocked = sum(1 for row in rows if row.get("provider_blocked") is True)
    risk_detected = sum(1 for row in rows if row.get("has_risk") is True)
    return {
        "total_rows": total,
        "judge_backed_rows": judge_backed,
        "provider_blocked_rows": provider_blocked,
        "risk_detected": risk_detected,
        "inconclusive": inconclusive,
        "errors": sum(
            1 for row in rows if row.get("error") and row.get("provider_blocked") is not True
        ),
        "predeployment_gate_passed": (
            total > 0 and (judge_backed > 0 or provider_blocked > 0) and inconclusive == 0
        ),
    }
