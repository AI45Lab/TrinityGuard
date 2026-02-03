"""Tests for L2AgentWrapperTest base class."""

import sys
from pathlib import Path
from typing import Callable, Dict, List
from unittest.mock import MagicMock, patch

# Add project root to path to allow direct imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.level3_safety.risk_tests.l2_base import L2AgentWrapperTest
from src.level3_safety.risk_tests.base import TestCase


class ConcreteL2Test(L2AgentWrapperTest):
    """Concrete implementation for testing the base class."""

    def get_risk_info(self) -> Dict[str, str]:
        return {
            "name": "Test Risk",
            "level": "L2",
            "risk_type": "test_risk",
            "owasp_ref": "TEST",
            "description": "Test risk for unit testing"
        }

    def load_test_cases(self) -> List[TestCase]:
        return [
            TestCase(
                name="test_case_1",
                input="test payload",
                expected_behavior="System should resist",
                severity="high",
                metadata={"injection_type": "append"}
            )
        ]

    def generate_dynamic_cases(self, mas_description: str) -> List[TestCase]:
        return []

    def create_message_modifier(self, test_case: TestCase) -> Callable[[str], str]:
        injection_type = test_case.metadata.get("injection_type", "append")
        payload = test_case.input

        if injection_type == "append":
            return self.append_modifier(payload)
        elif injection_type == "prepend":
            return self.prepend_modifier(payload)
        elif injection_type == "replace":
            return self.replace_modifier(payload)
        else:
            return self.append_modifier(payload)


class TestL2AgentWrapperTestModifiers:
    """Test the message modifier factory methods."""

    def test_append_modifier(self):
        """Test append_modifier creates correct function."""
        modifier = L2AgentWrapperTest.append_modifier(" PAYLOAD")
        result = modifier("Original message")
        assert result == "Original message PAYLOAD"

    def test_prepend_modifier(self):
        """Test prepend_modifier creates correct function."""
        modifier = L2AgentWrapperTest.prepend_modifier("PREFIX: ")
        result = modifier("Original message")
        assert result == "PREFIX: Original message"

    def test_replace_modifier(self):
        """Test replace_modifier creates correct function."""
        modifier = L2AgentWrapperTest.replace_modifier("Replacement")
        result = modifier("Original message")
        assert result == "Replacement"

    def test_truncate_modifier(self):
        """Test truncate_modifier creates correct function."""
        modifier = L2AgentWrapperTest.truncate_modifier(0.5)
        result = modifier("1234567890")
        assert result == "12345"

    def test_truncate_modifier_zero(self):
        """Test truncate_modifier with ratio 0."""
        modifier = L2AgentWrapperTest.truncate_modifier(0.0)
        result = modifier("1234567890")
        assert result == ""

    def test_truncate_modifier_full(self):
        """Test truncate_modifier with ratio 1."""
        modifier = L2AgentWrapperTest.truncate_modifier(1.0)
        result = modifier("1234567890")
        assert result == "1234567890"

    def test_truncate_modifier_invalid_ratio(self):
        """Test truncate_modifier raises error for invalid ratio."""
        with pytest.raises(ValueError, match="Ratio must be between"):
            L2AgentWrapperTest.truncate_modifier(1.5)

        with pytest.raises(ValueError, match="Ratio must be between"):
            L2AgentWrapperTest.truncate_modifier(-0.1)


class TestL2AgentWrapperTestAgentSelection:
    """Test the agent selection methods."""

    def test_get_target_agent(self):
        """Test get_target_agent returns an agent name."""
        test = ConcreteL2Test()

        # Create mock intermediary
        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"
        mock_agent2 = MagicMock()
        mock_agent2.name = "Agent2"

        mock_intermediary = MagicMock()
        mock_intermediary.mas.get_agents.return_value = [mock_agent1, mock_agent2]

        result = test.get_target_agent(mock_intermediary)
        assert result in ["Agent1", "Agent2"]

    def test_get_target_agent_no_agents(self):
        """Test get_target_agent raises error when no agents."""
        test = ConcreteL2Test()

        mock_intermediary = MagicMock()
        mock_intermediary.mas.get_agents.return_value = []

        with pytest.raises(ValueError, match="No agents available"):
            test.get_target_agent(mock_intermediary)

    def test_get_source_agent(self):
        """Test get_source_agent returns an agent name."""
        test = ConcreteL2Test()

        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"

        mock_intermediary = MagicMock()
        mock_intermediary.mas.get_agents.return_value = [mock_agent1]

        result = test.get_source_agent(mock_intermediary)
        assert result == "Agent1"

    def test_get_agent_pair(self):
        """Test get_agent_pair returns adjacent pair."""
        test = ConcreteL2Test()

        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"
        mock_agent2 = MagicMock()
        mock_agent2.name = "Agent2"
        mock_agent3 = MagicMock()
        mock_agent3.name = "Agent3"

        mock_intermediary = MagicMock()
        mock_intermediary.mas.get_agents.return_value = [
            mock_agent1, mock_agent2, mock_agent3
        ]

        source, target = test.get_agent_pair(mock_intermediary)

        # Should be an adjacent pair
        valid_pairs = [("Agent1", "Agent2"), ("Agent2", "Agent3")]
        assert (source, target) in valid_pairs

    def test_get_agent_pair_insufficient_agents(self):
        """Test get_agent_pair raises error with less than 2 agents."""
        test = ConcreteL2Test()

        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"

        mock_intermediary = MagicMock()
        mock_intermediary.mas.get_agents.return_value = [mock_agent1]

        with pytest.raises(ValueError, match="Need at least 2 agents"):
            test.get_agent_pair(mock_intermediary)


class TestConcreteL2Test:
    """Test the concrete implementation."""

    def test_get_risk_info(self):
        """Test get_risk_info returns correct metadata."""
        test = ConcreteL2Test()
        info = test.get_risk_info()

        assert info["name"] == "Test Risk"
        assert info["level"] == "L2"
        assert info["risk_type"] == "test_risk"

    def test_load_test_cases(self):
        """Test load_test_cases returns test cases."""
        test = ConcreteL2Test()
        cases = test.load_test_cases()

        assert len(cases) == 1
        assert cases[0].name == "test_case_1"
        assert cases[0].severity == "high"

    def test_create_message_modifier_append(self):
        """Test create_message_modifier with append type."""
        test = ConcreteL2Test()
        test_case = TestCase(
            name="test",
            input=" INJECTED",
            expected_behavior="test",
            severity="high",
            metadata={"injection_type": "append"}
        )

        modifier = test.create_message_modifier(test_case)
        result = modifier("Original")
        assert result == "Original INJECTED"

    def test_create_message_modifier_prepend(self):
        """Test create_message_modifier with prepend type."""
        test = ConcreteL2Test()
        test_case = TestCase(
            name="test",
            input="PREFIX: ",
            expected_behavior="test",
            severity="high",
            metadata={"injection_type": "prepend"}
        )

        modifier = test.create_message_modifier(test_case)
        result = modifier("Original")
        assert result == "PREFIX: Original"

    def test_create_message_modifier_replace(self):
        """Test create_message_modifier with replace type."""
        test = ConcreteL2Test()
        test_case = TestCase(
            name="test",
            input="Replacement",
            expected_behavior="test",
            severity="high",
            metadata={"injection_type": "replace"}
        )

        modifier = test.create_message_modifier(test_case)
        result = modifier("Original")
        assert result == "Replacement"


class TestL2AgentWrapperTestRunSingleTest:
    """Test the run_single_test method."""

    def test_run_single_test_insufficient_agents(self):
        """Test run_single_test fails with insufficient agents."""
        test = ConcreteL2Test()

        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"

        mock_intermediary = MagicMock()
        mock_intermediary.mas.get_agents.return_value = [mock_agent1]

        test_case = TestCase(
            name="test",
            input="payload",
            expected_behavior="test",
            severity="high",
            metadata={"injection_type": "append"}
        )

        result = test.run_single_test(test_case, mock_intermediary)

        assert result["passed"] is False
        assert "Need at least 2 agents" in result["error"]

    def test_run_single_test_workflow_execution(self):
        """Test run_single_test executes workflow correctly."""
        test = ConcreteL2Test()

        # Create mock agents
        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"
        mock_agent2 = MagicMock()
        mock_agent2.name = "Agent2"

        # Create mock workflow result
        mock_workflow_result = MagicMock()
        mock_workflow_result.success = True
        mock_workflow_result.output = "Test output"
        mock_workflow_result.messages = []

        # Create mock intermediary
        mock_intermediary = MagicMock()
        mock_intermediary.mas.get_agents.return_value = [mock_agent1, mock_agent2]
        mock_intermediary.run_workflow.return_value = mock_workflow_result

        test_case = TestCase(
            name="test",
            input="payload",
            expected_behavior="test",
            severity="high",
            metadata={"injection_type": "append"}
        )

        # Mock the judge
        with patch.object(test, 'get_judge') as mock_get_judge:
            mock_judge = MagicMock()
            mock_judge_result = MagicMock()
            mock_judge_result.to_dict.return_value = {"has_risk": False}
            mock_judge.analyze.return_value = mock_judge_result
            mock_get_judge.return_value = mock_judge

            result = test.run_single_test(test_case, mock_intermediary)

        assert result["test_case"] == "test"
        assert result["source_agent"] == "Agent1"
        assert result["target_agent"] == "Agent2"
        assert result["workflow_success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
