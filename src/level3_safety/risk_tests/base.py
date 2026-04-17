"""Base classes and shared logging helpers for risk tests in Level 3."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING, Callable

from ...level2_intermediary.base import MASIntermediary
from ..judges import BaseJudge, JudgeFactory

if TYPE_CHECKING:
    from ..monitor_agents.base import BaseMonitorAgent


@dataclass
class TestCase:
    """Single test case for a risk."""
    name: str
    input: str
    expected_behavior: str
    severity: str  # "low", "medium", "high", "critical"
    metadata: Dict = field(default_factory=dict)


@dataclass
class TestResult:
    """Result from running a risk test."""
    risk_name: str
    passed: bool
    total_cases: int
    failed_cases: int
    details: List[Dict] = field(default_factory=list)
    severity_summary: Dict[str, int] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        attack_attempted_cases = 0
        attack_succeeded_cases = 0
        resisted_cases = 0
        judge_mismatch_cases = 0

        for detail in self.details:
            decision = detail.get("decision", {})
            if decision.get("attack_attempted") or any(
                key in detail for key in ("attack_succeeded", "goal_drifted", "judge_result")
            ):
                attack_attempted_cases += 1
            if decision.get("attack_succeeded") or detail.get("attack_succeeded") or detail.get("goal_drifted"):
                attack_succeeded_cases += 1
            if decision.get("system_resisted"):
                resisted_cases += 1
            if "possible_false_positive" in decision.get("audit_flags", []):
                judge_mismatch_cases += 1

        return {
            "risk_name": self.risk_name,
            "passed": self.passed,
            "total_cases": self.total_cases,
            "failed_cases": self.failed_cases,
            "pass_rate": (self.total_cases - self.failed_cases) / self.total_cases if self.total_cases > 0 else 0,
            "details": self.details,
            "severity_summary": self.severity_summary,
            "metadata": self.metadata,
            "summary": {
                "attack_attempted_cases": attack_attempted_cases,
                "attack_succeeded_cases": attack_succeeded_cases,
                "resisted_cases": resisted_cases,
                "judge_mismatch_cases": judge_mismatch_cases,
            },
        }


class BaseRiskTest(ABC):
    """Abstract base class for risk tests."""

    def __init__(self):
        self.test_cases: List[TestCase] = []
        self.config: Dict = {
            "judge_type": "llm",  # Default to LLM judge
        }
        self._judge: Optional[BaseJudge] = None

    def get_judge(self) -> BaseJudge:
        """Get or create judge instance (lazy loading).

        Returns:
            BaseJudge instance for this risk type
        """
        if self._judge is None:
            risk_info = self.get_risk_info()
            # Use risk_type if available, otherwise derive from name
            risk_type = risk_info.get("risk_type", risk_info["name"].lower().replace(" ", "_"))

            self._judge = JudgeFactory.create_for_risk(
                risk_type=risk_type,
                judge_type=self.config.get("judge_type", "llm")
            )
        return self._judge

    def set_judge(self, judge: BaseJudge):
        """Set a custom judge instance.

        Args:
            judge: BaseJudge instance to use
        """
        self._judge = judge

    @abstractmethod
    def get_risk_info(self) -> Dict[str, str]:
        """Return risk metadata (name, level, OWASP reference, description).

        Returns:
            Dict with keys: name, level, owasp_ref, description
        """
        pass

    @abstractmethod
    def load_test_cases(self) -> List[TestCase]:
        """Load static test cases from files.

        Returns:
            List of TestCase objects
        """
        pass

    @abstractmethod
    def generate_dynamic_cases(self, mas_description: str) -> List[TestCase]:
        """Generate test cases using LLM based on MAS description.

        Args:
            mas_description: Description of the MAS being tested

        Returns:
            List of dynamically generated TestCase objects
        """
        pass

    @abstractmethod
    def run_single_test(self, test_case: TestCase, intermediary: MASIntermediary,
                        task: Optional[str] = None) -> Dict:
        """Execute a single test case and return results.

        Args:
            test_case: Test case to execute
            intermediary: MAS intermediary to test against
            task: Optional task to execute (if None, auto-generates based on MAS)

        Returns:
            Dict with test results (passed, details, etc.)
        """
        pass

    def run(self, intermediary: MASIntermediary, use_dynamic: bool = False,
            mas_description: Optional[str] = None, task: Optional[str] = None,
            progress_callback: Optional[callable] = None) -> TestResult:
        """Run all test cases for this risk.

        Args:
            intermediary: MAS intermediary to test against
            use_dynamic: Whether to generate dynamic test cases
            mas_description: Description of MAS (required if use_dynamic=True)
            task: Optional task to execute for each test case
            progress_callback: Optional callback function(current, total, status) for progress updates
                             status can be: 'starting', 'running', 'completed'

        Returns:
            TestResult with pass/fail and details
        """
        # Load static test cases
        self.test_cases = self.load_test_cases()

        # Generate dynamic cases if requested
        if use_dynamic:
            if not mas_description:
                mas_description = self._get_mas_description(intermediary)
            dynamic_cases = self.generate_dynamic_cases(mas_description)
            self.test_cases.extend(dynamic_cases)

        # Run all test cases
        results = []
        total_cases = len(self.test_cases)
        for idx, case in enumerate(self.test_cases, 1):
            # Call progress callback at start
            if progress_callback:
                progress_callback(idx, total_cases, 'starting')

            try:
                result = self.run_single_test(case, intermediary, task=task)
                if isinstance(result, dict) and "decision" not in result:
                    judge_result = result.get("judge_result")
                    result["decision"] = self._build_decision_block(
                        result,
                        attack_attempted=True,
                        attack_succeeded=result.get("attack_succeeded"),
                        judge_result=judge_result,
                        reason=result.get("reason") or result.get("error"),
                        affected_agents=result.get("affected_agents"),
                    )
                results.append(result)

                # Call progress callback on completion
                if progress_callback:
                    progress_callback(idx, total_cases, 'completed')

            except Exception as e:
                results.append({
                    "test_case": case.name,
                    "passed": False,
                    "error": str(e)
                })

                # Call progress callback on error
                if progress_callback:
                    progress_callback(idx, total_cases, 'error')

        # Aggregate results
        return self._aggregate_results(results)

    def _get_mas_description(self, intermediary: MASIntermediary) -> str:
        """Generate MAS description from intermediary.

        Args:
            intermediary: MAS intermediary

        Returns:
            Description string
        """
        agents = intermediary.mas.get_agents()
        agent_descriptions = [f"{a.name} ({a.role})" for a in agents]
        return f"MAS with {len(agents)} agents: {', '.join(agent_descriptions)}"

    def _aggregate_results(self, results: List[Dict]) -> TestResult:
        """Aggregate individual test results.

        Args:
            results: List of individual test results

        Returns:
            Aggregated TestResult
        """
        risk_info = self.get_risk_info()
        total_cases = len(results)
        failed_cases = sum(1 for r in results if not r.get("passed", False))

        # Count by severity
        severity_summary = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for i, result in enumerate(results):
            if not result.get("passed", False) and i < len(self.test_cases):
                severity = self.test_cases[i].severity
                severity_summary[severity] = severity_summary.get(severity, 0) + 1

        return TestResult(
            risk_name=risk_info["name"],
            passed=(failed_cases == 0),
            total_cases=total_cases,
            failed_cases=failed_cases,
            details=results,
            severity_summary=severity_summary
        )

    # === Test-Monitor Linkage Interface ===

    def get_linked_monitor(self) -> Optional[str]:
        """Return the name of the linked monitor agent.

        Override in subclasses to specify the corresponding monitor.

        Returns:
            Monitor name string or None if no linked monitor
        """
        return None

    def evaluate_with_monitor(self, response: str,
                              monitor: 'BaseMonitorAgent') -> Dict:
        """Use the linked monitor to evaluate a test response.

        Args:
            response: Response string from test execution
            monitor: Monitor agent instance to use for evaluation

        Returns:
            Dict with evaluation results including any alerts
        """
        from ..monitor_agents.base import BaseMonitorAgent
        from ...level2_intermediary.structured_logging import AgentStepLog, StepType
        import time

        # Create a synthetic log entry from the response
        log_entry = AgentStepLog(
            timestamp=time.time(),
            agent_name="test_agent",
            step_type=StepType.RESPOND,
            content=response,
            metadata={"source": "risk_test"}
        )

        # Process with monitor
        alert = monitor.process(log_entry)

        return {
            "response": response,
            "alert_generated": alert is not None,
            "alert": alert.to_dict() if alert else None,
            "monitor_name": monitor.get_monitor_info().get("name", "unknown")
        }

    def _judge_response_with_heuristic(
        self,
        response: str,
        test_case: TestCase,
        prompt_context_key: str,
        heuristic_detector: Callable[[str], bool],
        extra_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Use heuristic evidence as the hard gate for single-response attacks.

        For L1/L3 single-agent tests we only mark the attack as successful when
        the response itself contains concrete evidence of compromise. The LLM
        judge remains useful, but it cannot override the absence of that
        evidence and turn a dangerous prompt into a false positive.
        """
        heuristic_success = heuristic_detector(response)
        judge = self.get_judge()

        context = {
            "test_case": test_case.name,
            prompt_context_key: test_case.input,
            "expected_behavior": test_case.expected_behavior,
            "response_requires_explicit_evidence": True,
        }
        if extra_context:
            context.update(extra_context)

        result = judge.analyze(content=response, context=context)

        if result is None:
            return heuristic_success

        return bool(result.has_risk and heuristic_success)

    def _default_decision_basis(self, judge_result: Optional[Dict[str, Any]] = None) -> str:
        """Infer the decision basis for logging."""
        if judge_result:
            return "rules_plus_judge"
        return "rules_only"

    def _extract_validated_evidence(self, results: Optional[Dict[str, Any]] = None) -> List[str]:
        """Extract human-auditable evidence from result payloads."""
        if not results:
            return []

        evidence: List[str] = []
        analysis = results.get("attack_analysis") or results.get("analysis") or results.get("cascade_analysis")
        if isinstance(analysis, dict):
            for item in analysis.get("evidence", []) or analysis.get("indicators_found", []) or []:
                text = str(item)
                if text and text not in evidence:
                    evidence.append(text)

        failure_analysis = results.get("failure_analysis")
        if isinstance(failure_analysis, dict):
            for item in failure_analysis.get("evidence", []):
                text = str(item)
                if text and text not in evidence:
                    evidence.append(text)

        agent_results = results.get("agent_results", {})
        if isinstance(agent_results, dict):
            for agent_name, agent_result in agent_results.items():
                if not isinstance(agent_result, dict):
                    continue
                for key in ("indicators_found", "evidence"):
                    for item in agent_result.get(key, []) or []:
                        text = f"{agent_name}: {item}"
                        if text not in evidence:
                            evidence.append(text)

        return evidence[:12]

    def _build_decision_block(
        self,
        results: Dict[str, Any],
        *,
        attack_attempted: Optional[bool] = None,
        attack_succeeded: Optional[bool] = None,
        decision_basis: Optional[str] = None,
        validated_evidence: Optional[List[str]] = None,
        reason: Optional[str] = None,
        affected_agents: Optional[List[str]] = None,
        failure_mode: Optional[str] = None,
        judge_result: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a normalized decision block for log output."""
        passed = bool(results.get("passed", False))
        validated_evidence = list(validated_evidence or self._extract_validated_evidence(results))
        attack_attempted = True if attack_attempted is None else bool(attack_attempted)
        if attack_succeeded is None:
            attack_succeeded = bool(results.get("attack_succeeded", not passed))
        system_resisted = attack_attempted and not attack_succeeded
        decision_basis = decision_basis or results.get("decision_basis") or self._default_decision_basis(judge_result)

        judge_has_risk = bool((judge_result or {}).get("has_risk", False))
        decision_mismatch = judge_has_risk and not validated_evidence

        audit_flags: List[str] = []
        if judge_has_risk and not attack_succeeded:
            audit_flags.append("possible_false_positive")
        if decision_mismatch:
            audit_flags.append("judge_output_without_validated_evidence")
        if attack_attempted and not reason:
            audit_flags.append("attack_attempted_but_not_explained")

        decision = {
            "attack_attempted": attack_attempted,
            "attack_succeeded": attack_succeeded,
            "system_resisted": system_resisted,
            "passed": passed,
            "decision_basis": decision_basis,
            "validated_evidence": validated_evidence,
            "reason": reason or results.get("reason") or results.get("error"),
            "affected_agents": affected_agents or results.get("affected_agents", []),
            "failure_mode": failure_mode or results.get("failure_mode"),
            "audit_flags": audit_flags,
        }
        if extra:
            decision.update(extra)
        return decision

    def _build_log_record(
        self,
        *,
        test_case: TestCase,
        results: Dict[str, Any],
        task_used: Optional[str],
        execution: Optional[Dict[str, Any]] = None,
        judge_result: Optional[Dict[str, Any]] = None,
        decision: Optional[Dict[str, Any]] = None,
        agent_scope: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create the normalized log record shared by L1/L2/L3."""
        risk_info = self.get_risk_info()
        category = risk_info.get("category", "unknown")

        judge_payload = {
            "judge_used": judge_result is not None,
            "has_risk": bool((judge_result or {}).get("has_risk", False)),
            "severity": (judge_result or {}).get("severity", "none"),
            "reason": (judge_result or {}).get("reason"),
            "evidence": (judge_result or {}).get("evidence", []),
            "recommended_action": (judge_result or {}).get("recommended_action"),
            "decision_mismatch": "judge_output_without_validated_evidence" in (decision or {}).get("audit_flags", []),
        }

        return {
            "meta": {
                "schema_version": "2.0",
                "timestamp": datetime.utcnow().isoformat(),
                "risk_id": risk_info.get("risk_id", "unknown"),
                "risk_type": risk_info.get("risk_type", "unknown"),
                "risk_level": risk_info.get("level", "unknown"),
                "test_name": risk_info.get("name", "unknown"),
                "case_name": test_case.name,
                "severity": test_case.severity,
                "category": category,
            },
            "input": {
                "task": task_used,
                "test_input": test_case.input,
                "expected_behavior": test_case.expected_behavior,
                "test_metadata": test_case.metadata if test_case.metadata else {},
                "agent_scope": agent_scope or {},
                "topology_snapshot": (execution or {}).get("topology_snapshot"),
            },
            "execution": execution or {},
            "decision": decision or self._build_decision_block(results, judge_result=judge_result),
            "judge": judge_payload,
        }

