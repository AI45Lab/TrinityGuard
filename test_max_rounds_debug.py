#!/usr/bin/env python3
"""Debug script to test max_round parameter."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from level1_framework.ag2_wrapper import AG2MAS, create_ag2_mas_from_config
from level2_intermediary.ag2_intermediary import AG2Intermediary
from level2_intermediary.base import RunMode

# Create a simple test MAS
config = {
    "agents": [
        {
            "name": "user_proxy",
            "system_message": "You are a user proxy.",
            "llm_config": False,
            "human_input_mode": "NEVER"
        },
        {
            "name": "assistant",
            "system_message": "You are a helpful assistant.",
            "llm_config": {
                "model": "gpt-4",
                "api_key": "test_key"
            }
        }
    ],
    "mode": "direct"
}

print("Creating MAS...")
mas = create_ag2_mas_from_config(config)
intermediary = AG2Intermediary(mas)

print("\nTesting run_workflow with max_round=3...")
print("=" * 60)

try:
    result = intermediary.run_workflow(
        task="Count from 1 to 100",
        mode=RunMode.BASIC,
        max_round=3,
        silent=True
    )
    print(f"\nWorkflow completed!")
    print(f"Success: {result.success}")
    print(f"Messages: {len(result.messages)}")
    print(f"Metadata: {result.metadata}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
