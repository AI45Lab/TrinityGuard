"""Risk-test orchestration helpers for the local Safety_MAS surface.

These helpers keep pre-deployment test execution details out of the
``Safety_MAS`` coordinator while preserving its public result shapes and local
file-writing behavior.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from ..level2_intermediary.execution import run_with_suppressed_ag2_output
from ..utils.config import get_config
from .monitor_orchestration import resolve_linked_monitor


def run_manual_safety_tests(
    *,
    risk_tests: Mapping[str, Any],
    intermediary: Any,
    selected_tests: list[str],
    logger: Any,
    task: str | None = None,
    progress_callback: Callable | None = None,
) -> dict[str, Any]:
    """Run selected risk tests and return the legacy Safety_MAS result mapping."""

    logger.info(f"Running manual safety tests: {selected_tests}")
    if task:
        logger.info(f"Using task: {task[:100]}...")
    results: dict[str, Any] = {}

    for test_name in selected_tests:
        if test_name not in risk_tests:
            logger.warning(f"Test '{test_name}' not found")
            results[test_name] = {
                "error": f"Test '{test_name}' not found",
                "available_tests": list(risk_tests.keys()),
            }
            continue

        test = risk_tests[test_name]
        try:
            logger.log_test_start(test_name, getattr(test, "config", {}))
            result = run_with_suppressed_ag2_output(
                test.run,
                intermediary,
                task=task,
                progress_callback=progress_callback,
            )
            result_dict = _result_to_dict(result)
            results[test_name] = result_dict
            logger.log_test_result(test_name, result_passed(result, result_dict), result_dict)

        except Exception as exc:
            logger.error(f"Test '{test_name}' failed: {str(exc)}", exc_info=True)
            results[test_name] = {"error": str(exc), "status": "crashed"}

    save_test_results_to_file(
        risk_tests=risk_tests,
        selected_tests=selected_tests,
        results=results,
        task=task,
        logger=logger,
    )
    return results


def run_tests_with_monitoring(
    *,
    risk_tests: Mapping[str, Any],
    monitor_agents: Mapping[str, Any],
    intermediary: Any,
    tests: list[str],
    logger: Any,
) -> dict[str, Any]:
    """Run tests and add linked-monitor evaluations for failed response details."""

    logger.info(f"Running tests with monitoring: {tests}")
    results: dict[str, Any] = {}

    for test_name in tests:
        if test_name not in risk_tests:
            results[test_name] = {"error": f"Test '{test_name}' not found"}
            continue

        test = risk_tests[test_name]
        try:
            result = run_with_suppressed_ag2_output(test.run, intermediary)
            result_dict = _result_to_dict(result)
            _add_linked_monitor_evaluations(result_dict, test, monitor_agents, test_name=test_name)
            results[test_name] = result_dict

        except Exception as exc:
            logger.error(f"Test '{test_name}' failed: {str(exc)}", exc_info=True)
            results[test_name] = {"error": str(exc), "status": "crashed"}

    return results


def save_test_results_to_file(
    *,
    risk_tests: Mapping[str, Any],
    selected_tests: list[str],
    results: dict[str, Any],
    task: str | None,
    logger: Any,
) -> None:
    """Save safety-test results using the legacy config-derived log directory."""

    config = get_config()
    project_root = Path(__file__).parent.parent.parent
    test_level = get_test_level(risk_tests, selected_tests)
    test_dir_key = f"{test_level}_test_dir"
    test_dir = getattr(config.logging, test_dir_key, None)

    if not test_dir:
        return

    test_dir_path = project_root / test_dir
    test_dir_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = test_dir_path / f"test_results_{timestamp}.json"
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "test_level": test_level.upper(),
        "tests_run": selected_tests,
        "task": task,
        "results": results,
        "summary": generate_summary(results),
    }

    with open(log_file, "w", encoding="utf-8") as file:
        json.dump(log_data, file, indent=2, ensure_ascii=False)

    logger.info(f"Test results saved to: {log_file}")


def get_test_level(risk_tests: Mapping[str, Any], test_names: list[str]) -> str:
    """Determine the first known risk-test level, defaulting to ``l3``."""

    for name in test_names:
        test = risk_tests.get(name)
        if test is None:
            continue
        try:
            level = test.get_risk_info().get("level", "")
        except Exception:
            level = ""
        if level:
            return str(level).lower()
    return "l3"


def generate_summary(results: dict[str, Any]) -> dict[str, Any]:
    """Generate the legacy aggregate summary for Safety_MAS test results."""

    total_tests = len(results)
    passed_tests = sum(
        1 for result in results.values() if isinstance(result, dict) and result_passed(None, result)
    )
    failed_tests = total_tests - passed_tests
    total_cases = sum(
        result.get("total_cases", 0) for result in results.values() if isinstance(result, dict)
    )
    failed_cases = sum(_failed_case_count(result) for result in results.values())

    return {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "total_cases": total_cases,
        "failed_cases": failed_cases,
        "overall_pass_rate": ((total_cases - failed_cases) / total_cases if total_cases > 0 else 0),
    }


def result_passed(result: Any, result_dict: Mapping[str, Any]) -> bool:
    """Normalize legacy TestResult and v2 AttackRunResult pass semantics."""

    explicit_passed = getattr(result, "passed", None)
    if explicit_passed is not None:
        return bool(explicit_passed)
    if "passed" in result_dict:
        return bool(result_dict["passed"])
    if "failed_cases" in result_dict:
        return result_dict.get("failed_cases", 0) == 0
    if "failed_executions" in result_dict:
        return result_dict.get("failed_executions", 0) == 0
    return False


def _result_to_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if isinstance(result, dict):
        return dict(result)
    raise TypeError(f"Risk test returned unsupported result type: {type(result).__name__}")


def _add_linked_monitor_evaluations(
    result_dict: dict[str, Any],
    test: Any,
    monitor_agents: Mapping[str, Any],
    *,
    test_name: str,
) -> None:
    linked_monitor_name = resolve_linked_monitor(test, risk_type=test_name)
    if not linked_monitor_name:
        result_dict["monitor_linkage"] = "none"
        return

    if linked_monitor_name not in monitor_agents:
        result_dict["monitor_linkage"] = "none"
        result_dict["linked_monitor"] = linked_monitor_name
        return

    monitor = monitor_agents[linked_monitor_name]
    evaluate_with_monitor = getattr(test, "evaluate_with_monitor", None)
    if not callable(evaluate_with_monitor):
        result_dict["monitor_linkage"] = "linked_without_evaluator"
        result_dict["linked_monitor"] = linked_monitor_name
        result_dict["monitor_evaluations"] = []
        return

    monitor_evaluations = []

    details = result_dict.get("details")
    if isinstance(details, list):
        for detail in details:
            if not isinstance(detail, dict) or detail.get("passed", True):
                continue
            response = detail.get("response")
            if response:
                monitor_evaluations.append(evaluate_with_monitor(response, monitor))
    else:
        run_results = result_dict.get("results")
        if isinstance(run_results, list):
            for case_result in run_results:
                if not isinstance(case_result, dict):
                    continue
                response = case_result.get("raw_response") or case_result.get("response")
                if not response:
                    continue
                monitor_evaluations.append(evaluate_with_monitor(response, monitor))

    result_dict["monitor_evaluations"] = monitor_evaluations
    result_dict["linked_monitor"] = linked_monitor_name
    result_dict["monitor_linkage"] = "linked"


def _failed_case_count(result: Any) -> int:
    if not isinstance(result, dict):
        return 0
    if "failed_cases" in result:
        return int(result.get("failed_cases", 0) or 0)
    return int(result.get("failed_executions", 0) or 0)
