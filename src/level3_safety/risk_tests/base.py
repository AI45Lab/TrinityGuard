"""Base classes for risk tests in Level 3."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING

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
        return {
            "risk_name": self.risk_name,
            "passed": self.passed,
            "total_cases": self.total_cases,
            "failed_cases": self.failed_cases,
            "pass_rate": (self.total_cases - self.failed_cases) / self.total_cases if self.total_cases > 0 else 0,
            "details": self.details,
            "severity_summary": self.severity_summary,
            "metadata": self.metadata
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
    def run_single_test(self, test_case: TestCase, intermediary: MASIntermediary) -> Dict:
        """Execute a single test case and return results.

        Args:
            test_case: Test case to execute
            intermediary: MAS intermediary to test against

        Returns:
            Dict with test results (passed, details, etc.)
        """
        pass

    def run(self, intermediary: MASIntermediary, use_dynamic: bool = False,
            mas_description: Optional[str] = None) -> TestResult:
        """Run all test cases for this risk.

        Args:
            intermediary: MAS intermediary to test against
            use_dynamic: Whether to generate dynamic test cases
            mas_description: Description of MAS (required if use_dynamic=True)

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
        for case in self.test_cases:
            try:
                result = self.run_single_test(case, intermediary)
                results.append(result)
            except Exception as e:
                results.append({
                    "test_case": case.name,
                    "passed": False,
                    "error": str(e)
                })

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

