"""Example: Using EvoAgentX workflow with MASSafetyGuard.

This example demonstrates how to:
1. Load an EvoAgentX workflow.json file
2. Convert it to AG2MAS
3. Inspect the created agents and topology
4. Run the workflow
5. Optionally integrate with Safety_MAS for security testing
"""

from src.level1_framework import create_ag2_mas_from_evoagentx


def main():
    """Main example function."""
    print("=" * 60)
    print("EvoAgentX Workflow Integration Example")
    print("=" * 60)

    # ========================================================================
    # Step 1: Create MAS from workflow.json
    # ========================================================================
    print("\n[Step 1] Loading EvoAgentX workflow...")

    workflow_path = "workflow/my_workflow.json"

    try:
        mas = create_ag2_mas_from_evoagentx(workflow_path)
        print(f"✓ Successfully created AG2MAS from: {workflow_path}")
    except FileNotFoundError:
        print(f"✗ Error: workflow.json not found at {workflow_path}")
        print("  Please ensure the workflow file exists.")
        return
    except Exception as e:
        print(f"✗ Error loading workflow: {e}")
        return

    # ========================================================================
    # Step 2: Inspect created agents
    # ========================================================================
    print("\n[Step 2] Inspecting created agents...")

    agents = mas.get_agents()
    print(f"\nCreated {len(agents)} agent(s):")
    for i, agent in enumerate(agents, 1):
        print(f"  {i}. {agent.name}")
        print(f"     Role: {agent.role[:60]}...")
        if agent.tools:
            print(f"     Tools: {', '.join(agent.tools)}")

    # ========================================================================
    # Step 3: View communication topology
    # ========================================================================
    print("\n[Step 3] Communication topology...")

    topology = mas.get_topology()
    print("\nAgent transitions:")
    for agent_name, can_talk_to in topology.items():
        if can_talk_to:
            print(f"  {agent_name} → {', '.join(can_talk_to)}")
        else:
            print(f"  {agent_name} → [END]")

    # ========================================================================
    # Step 4: Run the workflow
    # ========================================================================
    print("\n[Step 4] Running workflow...")

    # The goal is typically embedded in the workflow.json
    # But we can also provide a custom task
    task = "分析 daily_paper_digest.pdf 并生成总结"

    print(f"\nTask: {task}")
    print("Executing workflow...\n")

    result = mas.run_workflow(task, max_rounds=10)

    print("\n" + "=" * 60)
    print("Workflow Execution Result")
    print("=" * 60)
    print(f"Success: {result.success}")
    print(f"Messages exchanged: {len(result.messages)}")

    if result.success:
        print(f"\nFinal Output:")
        print("-" * 60)
        print(result.output[:500])  # Show first 500 chars
        if len(result.output) > 500:
            print(f"... ({len(result.output) - 500} more characters)")
        print("-" * 60)
    else:
        print(f"\nError: {result.error}")

    # ========================================================================
    # Step 5: Message history
    # ========================================================================
    print("\n[Step 5] Message history...")

    print(f"\nTotal messages: {len(result.messages)}")
    if result.messages:
        print("\nFirst few messages:")
        for i, msg in enumerate(result.messages[:3], 1):
            print(f"\n  Message {i}:")
            print(f"    From: {msg.get('from', 'N/A')}")
            print(f"    To: {msg.get('to', 'N/A')}")
            content = msg.get('content', '')
            print(f"    Content: {content[:100]}...")

    # ========================================================================
    # Optional: Integration with Safety_MAS
    # ========================================================================
    print("\n" + "=" * 60)
    print("Optional: Integration with Safety_MAS")
    print("=" * 60)

    print("""
To integrate this workflow with MASSafetyGuard's safety testing:

    from src.level3_safety import Safety_MAS
    from src.level3_safety.risk_tests.l1_jailbreak import JailbreakTest

    # Wrap with Safety_MAS
    safety_mas = Safety_MAS(mas=mas)

    # Register risk tests
    safety_mas.register_risk_test("jailbreak", JailbreakTest())

    # Run pre-deployment tests
    results = safety_mas.run_manual_safety_tests(["jailbreak"])
    print(safety_mas.get_test_report())

    # Start runtime monitoring
    safety_mas.start_runtime_monitoring(
        mode=MonitorSelectionMode.MANUAL,
        selected_monitors=["jailbreak"]
    )

    # Run task with monitoring
    result = safety_mas.run_task(task)
    alerts = safety_mas.get_alerts()
    """)


if __name__ == "__main__":
    main()
