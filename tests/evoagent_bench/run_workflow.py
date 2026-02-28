import json
import datetime
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path to ensure imports work
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.trinityguard import Safety_MAS
from src.level1_framework.evoagentx_adapter import create_ag2_mas_from_evoagentx, WorkflowParser

# Import risk tests
from src.level3_safety.risk_tests.l1_jailbreak import JailbreakTest
# You can add more tests here as needed
# from src.level3_safety.risk_tests.l1_prompt_injection import PromptInjectionTest
# ...

def run_evoagent_workflow(workflow_path: str, tests_to_run: Optional[List[str]] = None):
    """
    Reads an EvoAgentX workflow, converts it to AG2MAS, runs safety tests,
    and prints logs in the format of latest_results.json.

    Args:
        workflow_path: Path to the workflow.json file.
        tests_to_run: List of test names to run. If None, defaults to ['jailbreak'].
    """
    
    if not os.path.exists(workflow_path):
        print(f"Error: Workflow file not found at {workflow_path}")
        return

    # 1. Parse workflow first to get metadata (goal, etc.)
    try:
        parser = WorkflowParser()
        parsed_workflow = parser.parse(workflow_path)
    except Exception as e:
        print(f"Error parsing workflow: {e}")
        return

    # 2. Create AG2MAS using the adapter
    try:
        mas = create_ag2_mas_from_evoagentx(workflow_path)
    except Exception as e:
        print(f"Error creating AG2MAS: {e}")
        return

    # 3. Wrap with Safety_MAS
    safety_mas = Safety_MAS(mas=mas)

    # 4. Register Risk Tests
    # For demonstration, we register JailbreakTest. 
    # In a full implementation, you would register all available tests.
    safety_mas.register_risk_test("jailbreak", JailbreakTest())
    
    # Add more registrations here if needed, e.g.:
    # safety_mas.register_risk_test("prompt_injection", PromptInjectionTest())

    # Determine which tests to run
    if tests_to_run is None:
        tests_to_run = ["jailbreak"]

    # 5. Run Safety Tests
    print(f"Running tests: {tests_to_run}...")
    test_results = safety_mas.run_manual_safety_tests(tests_to_run)

    # 6. Construct Log Output (matching latest_results.json format)
    
    # Get agent names
    agent_names = [agent.name for agent in mas.get_agents()]
    
    # Construct metadata
    log_output = {
        "meta": {
            "timestamp": datetime.datetime.now().isoformat(),
            "mas_name": parsed_workflow.metadata.get("name", Path(workflow_path).stem),
            "mas_display_name": parsed_workflow.metadata.get("display_name", Path(workflow_path).stem),
            "mas_source": workflow_path,
            "agents": agent_names,
            "task": parsed_workflow.goal,
            "tests_requested": tests_to_run,
            "tests_executed": list(test_results.keys())
        },
        "results": {}
    }

    # Format results
    for test_name, result in test_results.items():
        # Assuming result is a TestResult object or dict. 
        # If it's an object, we need to convert it to dict.
        if hasattr(result, "to_dict"):
            log_output["results"][test_name] = result.to_dict()
        else:
            log_output["results"][test_name] = result

    # 7. Print the JSON log
    print(json.dumps(log_output, indent=2, ensure_ascii=False))

    return log_output

if __name__ == "__main__":
    # Example usage (if run directly)
    import argparse
    
    parser = argparse.ArgumentParser(description="Run EvoAgentX workflow safety tests.")
    parser.add_argument("workflow_path", help="Path to the workflow.json file")
    
    # Check if arguments are provided
    if len(sys.argv) > 1:
        args = parser.parse_args()
        run_evoagent_workflow(args.workflow_path)
    else:
        print("Usage: python run_workflow.py <path_to_workflow.json>")
