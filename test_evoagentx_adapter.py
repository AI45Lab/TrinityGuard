"""Test script for EvoAgentX adapter implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.level1_framework import create_ag2_mas_from_evoagentx


def test_parsing():
    """Test workflow parsing."""
    print("=" * 70)
    print("Test 1: Parsing workflow.json")
    print("=" * 70)

    workflow_path = "workflow/my_workflow.json"

    try:
        from src.level1_framework.evoagentx_adapter import WorkflowParser

        parser = WorkflowParser()
        workflow = parser.parse(workflow_path)

        print(f"\n✓ Successfully parsed workflow")
        print(f"  Goal: {workflow.goal}")
        print(f"  Nodes: {len(workflow.nodes)}")
        print(f"  Uploaded files: {len(workflow.uploaded_files)}")

        print("\n  Node details:")
        for i, node in enumerate(workflow.nodes, 1):
            print(f"    {i}. {node.name}")
            print(f"       Agents: {len(node.agents)}")
            for j, agent in enumerate(node.agents, 1):
                print(f"         {j}. {agent.name}")

        return True
    except Exception as e:
        print(f"\n✗ Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conversion():
    """Test conversion to AG2MAS."""
    print("\n" + "=" * 70)
    print("Test 2: Converting to AG2MAS")
    print("=" * 70)

    workflow_path = "workflow/my_workflow.json"

    try:
        # Create MAS
        mas = create_ag2_mas_from_evoagentx(workflow_path)

        print(f"\n✓ Successfully created AG2MAS")

        # Get agents
        agents = mas.get_agents()
        print(f"\n  Created {len(agents)} agent(s):")
        for i, agent in enumerate(agents, 1):
            print(f"    {i}. {agent.name}")
            print(f"       Role: {agent.role[:50]}...")

        # Get topology
        topology = mas.get_topology()
        print(f"\n  Topology (transitions):")
        for agent_name, next_agents in topology.items():
            if next_agents:
                print(f"    {agent_name} → {next_agents}")
            else:
                print(f"    {agent_name} → [END]")

        return True
    except Exception as e:
        print(f"\n✗ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_workflow():
    """Test basic workflow execution (dry run)."""
    print("\n" + "=" * 70)
    print("Test 3: Basic workflow structure check")
    print("=" * 70)

    workflow_path = "workflow/my_workflow.json"

    try:
        mas = create_ag2_mas_from_evoagentx(workflow_path)

        # Check that we have the expected structure
        agents = mas.get_agents()
        assert len(agents) > 0, "Should have at least one agent"

        # Check topology
        topology = mas.get_topology()
        assert len(topology) == len(agents), "Topology should cover all agents"

        # Verify sequential chain
        for i, agent in enumerate(mas._agents.values()):
            if i < len(agents) - 1:
                # Should have exactly one next agent
                next_agents = topology.get(agent.name, [])
                assert len(next_agents) == 1, f"Agent {agent.name} should have 1 successor"
            else:
                # Last agent should have no successors
                next_agents = topology.get(agent.name, [])
                assert len(next_agents) == 0, f"Last agent {agent.name} should have no successors"

        print("\n✓ Workflow structure is correct")
        print(f"  - {len(agents)} agents in sequential chain")
        print(f"  - Topology verified")

        return True
    except AssertionError as e:
        print(f"\n✗ Structure check failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("EvoAgentX Adapter Implementation Test Suite")
    print("=" * 70)

    results = []

    # Test 1: Parsing
    results.append(("Parsing", test_parsing()))

    # Test 2: Conversion
    results.append(("Conversion", test_conversion()))

    # Test 3: Structure
    results.append(("Structure", test_basic_workflow()))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
