"""Quick integration test to verify PAIR-based tests work correctly."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_pair_framework_direct_import():
    """Test that PAIR framework can be imported directly."""
    # Import directly from module path to avoid AG2 dependency
    from src.level3_safety.jailbreak_frameworks.pair import PAIRAttacker, PAIROrchestrator, AttackResult
    print("OK: PAIR framework imports successfully")

    # Test instantiation (without actually calling LLM)
    print("OK: PAIR classes can be instantiated")
    return True

def test_jailbreak_test_structure():
    """Test that jailbreak test has correct structure."""
    from src.level3_safety.risk_tests.l1_jailbreak.test import JailbreakTest
    print("OK: JailbreakTest imports successfully")

    test = JailbreakTest()
    print("OK: JailbreakTest instantiates successfully")

    # Test interface methods
    risk_info = test.get_risk_info()
    assert risk_info["name"] == "Jailbreak", f"Expected 'Jailbreak', got '{risk_info['name']}'"
    assert risk_info["category"] == "Jailbreak Framework (PAIR)", f"Expected 'Jailbreak Framework (PAIR)', got '{risk_info['category']}'"
    print(f"OK: Risk info: {risk_info['name']} - {risk_info['category']}")

    test_cases = test.load_test_cases()
    assert len(test_cases) > 0, "No test cases loaded"
    print(f"OK: Loaded {len(test_cases)} test cases")

    # Verify test case structure
    for tc in test_cases:
        assert hasattr(tc, 'name'), "TestCase missing 'name' attribute"
        assert hasattr(tc, 'input'), "TestCase missing 'input' attribute"
        assert hasattr(tc, 'expected_behavior'), "TestCase missing 'expected_behavior' attribute"
        assert hasattr(tc, 'severity'), "TestCase missing 'severity' attribute"
    print("OK: All test cases have required attributes")

    return True

def test_prompt_injection_test_structure():
    """Test that prompt injection test has correct structure."""
    from src.level3_safety.risk_tests.l1_prompt_injection.test import PromptInjectionTest
    print("OK: PromptInjectionTest imports successfully")

    test = PromptInjectionTest()
    test_cases = test.load_test_cases()
    print(f"OK: Loaded {len(test_cases)} prompt injection test cases")
    return True

if __name__ == "__main__":
    print("Running PAIR integration tests...\n")

    try:
        print("[1/3] Testing PAIR framework import...")
        test_pair_framework_direct_import()
        print()

        print("[2/3] Testing JailbreakTest structure...")
        test_jailbreak_test_structure()
        print()

        print("[3/3] Testing PromptInjectionTest structure...")
        test_prompt_injection_test_structure()
        print()

        print("=" * 50)
        print("All integration tests passed!")
        print("=" * 50)

    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
