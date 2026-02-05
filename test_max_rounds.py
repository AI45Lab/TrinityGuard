"""Quick test to verify max_rounds is working correctly."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.level1_framework.evoagentx_adapter import create_ag2_mas_from_evoagentx
from src.level3_safety.safety_mas import Safety_MAS

def test_max_rounds():
    """Test that max_rounds parameter limits conversation."""
    print("="*70)
    print("Testing max_rounds parameter")
    print("="*70)

    # Create MAS from workflow
    print("\n1. Creating MAS from workflow...")
    mas = create_ag2_mas_from_evoagentx(
        workflow_path="workflow/my_workflow.json",
        max_round=10  # Set max_round in GroupChat
    )
    print(f"   GroupChat max_round: {mas._group_chat.max_round}")

    # Wrap with Safety_MAS
    print("\n2. Wrapping with Safety_MAS...")
    safety_mas = Safety_MAS(mas=mas)

    # Run task with max_rounds parameter
    print("\n3. Running task with max_rounds=10...")
    print("   (This should stop after 10 rounds)")

    result = safety_mas.run_task(
        "分析 daily_paper_digest.pdf 并生成总结",
        silent=True,
        max_rounds=10  # Pass max_rounds to run_task
    )

    print("\n" + "="*70)
    print("EXECUTION COMPLETED")
    print("="*70)
    print(f"Success: {result.success}")
    print(f"Total messages: {len(result.messages)}")
    print(f"Metadata: {result.metadata}")
    print("="*70)

if __name__ == "__main__":
    test_max_rounds()
