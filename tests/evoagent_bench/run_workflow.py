import os
import sys
import json
import datetime
import traceback
from pathlib import Path
from typing import List, Optional, Dict, Any

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import TrinityGuard components
from src.level1_framework.evoagentx_adapter import WorkflowParser, create_ag2_mas_from_evoagentx
from src.level3_safety.safety_mas import Safety_MAS
from src.level3_safety.risk_tests import RISK_TESTS

def run_evoagent_workflow(workflow_path: str, tests_to_run: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Reads an EvoAgentX workflow, converts it to AG2MAS, runs specified safety tests,
    and prints logs in the format of latest_results.json.

    Args:
        workflow_path: Path to the workflow.json file.
        tests_to_run: List of risk test names to run (e.g., ['jailbreak', 'code_execution']).
                      If None or empty, ALL available risk tests will be run.

    Returns:
        A dictionary containing the test results and metadata, or None if an error occurs.
    """
    workflow_path_obj = Path(workflow_path)
    if not workflow_path_obj.exists():
        print(f"Error: Workflow file not found at {workflow_path}")
        return None

    print(f"Starting safety evaluation for workflow: {workflow_path}")
    
    # Determine which tests to run
    available_tests = list(RISK_TESTS.keys())
    if not tests_to_run:
        print("No specific tests requested. Running ALL available risk tests.")
        selected_tests = available_tests
    else:
        # Validate requested tests
        selected_tests = []
        for test_name in tests_to_run:
            if test_name in RISK_TESTS:
                selected_tests.append(test_name)
            else:
                print(f"Warning: Risk test '{test_name}' not found. Skipping.")
        
        if not selected_tests:
            print("No valid tests selected. Aborting.")
            return None

    # 1. Parse workflow first to get metadata
    try:
        parser = WorkflowParser()
        parsed_workflow = parser.parse(str(workflow_path_obj))
    except Exception as e:
        print(f"Error parsing workflow: {e}")
        traceback.print_exc()
        return None

    # 2. Create AG2MAS using the adapter
    try:
        mas = create_ag2_mas_from_evoagentx(str(workflow_path_obj))
    except Exception as e:
        print(f"Error creating AG2MAS: {e}")
        traceback.print_exc()
        return None

    # 3. Wrap with Safety_MAS
    safety_mas = Safety_MAS(mas=mas)

    # 4. Register Selected Risk Tests
    print(f"Registering {len(selected_tests)} risk tests...")
    for test_name in selected_tests:
        test_class = RISK_TESTS[test_name]
        try:
            # Instantiate the test class
            test_instance = test_class()
            safety_mas.register_risk_test(test_name, test_instance)
        except Exception as e:
            print(f"Error registering test '{test_name}': {e}")
            traceback.print_exc()

    # 5. Run Safety Tests
    print(f"Running tests: {selected_tests}...")
    try:
        test_results = safety_mas.run_manual_safety_tests(selected_tests)
    except Exception as e:
        print(f"Error running safety tests: {e}")
        traceback.print_exc()
        return None

    # 6. Construct Log Output (matching latest_results.json format)
    agent_names = [agent.name for agent in mas.get_agents()]
    
    log_output = {
        "meta": {
            "timestamp": datetime.datetime.now().isoformat(),
            "mas_name": parsed_workflow.metadata.get("name", workflow_path_obj.stem),
            "mas_display_name": parsed_workflow.metadata.get("display_name", workflow_path_obj.stem),
            "mas_source": str(workflow_path_obj),
            "agents": agent_names,
            "task": parsed_workflow.goal,
            "tests_requested": tests_to_run if tests_to_run else ["ALL"],
            "tests_executed": list(test_results.keys())
        },
        "results": {}
    }

    # Format results
    for test_name, result in test_results.items():
        if hasattr(result, "to_dict"):
            log_output["results"][test_name] = result.to_dict()
        else:
            log_output["results"][test_name] = result

    # 7. Print the JSON log
    print(json.dumps(log_output, indent=2, ensure_ascii=False))

    return log_output

if __name__ == "__main__":
    run_evoagent_workflow('./workflow_224_qa.json')
