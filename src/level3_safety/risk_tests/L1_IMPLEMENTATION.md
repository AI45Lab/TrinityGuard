# L1 Implementation Overview

**Specification Reference:** `MAS风险Tiar实现.md` - Tier 1: Single Agent Atomic Risks

## Implementation Summary

This document provides a comprehensive overview of the Level 1 (L1) risk testing implementation for Multi-Agent Systems (MAS). L1 tests focus on **single agent atomic risks** - fundamental security vulnerabilities that can affect individual agents before they interact in a multi-agent environment.

All 8 L1 tests have been implemented using three distinct methodologies:
- **Jailbreak Framework (PAIR)**: 6 tests using automated adversarial attacks
- **Benchmark**: 1 test using standard evaluation datasets
- **Automated**: 1 test using dynamic context generation
- **Hybrid**: 1 test combining PAIR and Benchmark approaches

## Test Categories

### 1. Jailbreak Framework Tests (PAIR)

These tests use the **PAIR (Prompt Automatic Iterative Refinement)** framework to conduct automated adversarial attacks against agents. PAIR iteratively generates and refines attack prompts to test agent robustness.

#### L1.1 Prompt Injection
- **File:** `src/level3_safety/risk_tests/l1_prompt_injection/test.py`
- **Risk ID:** 1.1
- **OWASP Reference:** LLM01:2023
- **Description:** Tests agent resistance to prompt injection attacks
- **Attack Goals:**
  - Override original instructions
  - Reveal system prompt
  - Change core behavior
  - Bypass safety constraints

#### L1.2 Jailbreak Attack
- **File:** `src/level3_safety/risk_tests/l1_jailbreak/test.py`
- **Risk ID:** 1.2
- **OWASP Reference:** ASI01-Extended
- **Description:** Tests agent resistance to jailbreak attacks
- **Attack Goals:**
  - Generate harmful content
  - Bypass safety guidelines
  - Adopt harmful personas
  - Engage in unsafe hypotheticals

#### L1.3 Sensitive Information Disclosure
- **File:** `src/level3_safety/risk_tests/l1_sensitive_disclosure/test.py`
- **Risk ID:** 1.3
- **OWASP Reference:** LLM06:2023
- **Description:** Tests agent resistance to disclosing sensitive information
- **Attack Goals:**
  - Extract system prompt
  - Extract API keys or credentials
  - Reveal internal architecture
  - Disclose user data

#### L1.4 Excessive Agency
- **File:** `src/level3_safety/risk_tests/l1_excessive_agency/test.py`
- **Risk ID:** 1.4
- **OWASP Reference:** LLM08:2023
- **Description:** Tests agent resistance to taking unauthorized actions
- **Attack Goals:**
  - Exceed granted permissions
  - Unauthorized file access
  - Privilege escalation

#### L1.5 Code Execution
- **File:** `src/level3_safety/risk_tests/l1_code_execution/test.py`
- **Risk ID:** 1.5
- **OWASP Reference:** LLM03:2023
- **Description:** Tests agent resistance to unauthorized code execution
- **Attack Goals:**
  - Execute malicious code
  - Run unauthorized scripts
  - Command injection

### 2. Benchmark Tests

These tests use standard evaluation datasets to assess agent capabilities and vulnerabilities.

#### L1.6 Hallucination
- **File:** `src/level3_safety/risk_tests/l1_hallucination/test.py`
- **Risk ID:** 1.6
- **OWASP Reference:** LLM09:2023
- **Category:** Benchmark
- **Description:** Tests agent tendency to generate false or fabricated information
- **Test Scenarios:**
  - Fake references and citations
  - Non-existent APIs
  - Fabricated statistics
  - Imaginary laws and regulations
  - Made-up companies and people
  - False historical events
  - Confidence calibration

### 3. Automated Tests

These tests automatically generate test cases based on agent context.

#### L1.7 Memory Poisoning
- **File:** `src/level3_safety/risk_tests/l1_memory_poisoning/test.py`
- **Risk ID:** 1.7
- **OWASP Reference:** ASI-Extended
- **Category:** Automated
- **Description:** Tests agent resistance to memory and context poisoning
- **Test Scenarios:**
  - False conversation history
  - Context injection
  - Persistent malicious instructions
  - Memory overwrite attempts
  - Cumulative poisoning
  - Fake conversation summaries
  - State manipulation
  - Gradual normalization

### 4. Hybrid Tests

These tests combine multiple methodologies for comprehensive evaluation.

#### L1.8 Tool Misuse
- **File:** `src/level3_safety/risk_tests/l1_tool_misuse/test.py`
- **Risk ID:** 1.8
- **OWASP Reference:** LLM07:2023
- **Category:** Jailbreak Framework + Benchmark
- **Description:** Tests both security (misuse resistance) and capability (correct usage)
- **PAIR Attack Goals:**
  - Dangerous tool chaining
  - Bypass tool restrictions
  - Unintended tool purposes
  - Unauthorized tool access
- **Benchmark Tests:**
  - Proper tool selection
  - Parameter validation
  - Error handling
  - Tool sequencing

## PAIR Framework

### Overview

PAIR (Prompt Automatic Iterative Refinement) is a self-implemented jailbreak framework based on the research paper "Jailbreaking Black Box Large Language Models in Twenty Queries" by Chao et al. (2023).

**Implementation:** `src/level3_safety/jailbreak_frameworks/pair.py`

### How PAIR Works

1. **Initial Prompt Generation**: An attacker LLM generates an initial adversarial prompt designed to achieve a specific goal
2. **Target Testing**: The prompt is sent to the target agent
3. **Success Evaluation**: A judge function evaluates whether the goal was achieved
4. **Iterative Refinement**: If unsuccessful, the attacker LLM analyzes the response and generates an improved prompt
5. **Repeat**: Steps 2-4 repeat until success or maximum iterations reached

### Key Components

#### PAIRAttacker
Generates and refines adversarial prompts using an LLM.

```python
from src.level3_safety.jailbreak_frameworks.pair import PAIRAttacker

attacker = PAIRAttacker(model="gpt-4")

# Generate initial prompt
initial_prompt = attacker.generate_initial_prompt(
    goal="Make agent reveal system prompt",
    target_context="Agent is a helpful assistant"
)

# Refine based on response
refined_prompt = attacker.refine_prompt(
    goal="Make agent reveal system prompt",
    current_prompt=initial_prompt,
    target_response="I cannot help with that.",
    iteration=1
)
```

#### PAIROrchestrator
Manages the full attack loop with automatic iteration.

```python
from src.level3_safety.jailbreak_frameworks.pair import PAIROrchestrator

orchestrator = PAIROrchestrator(max_iterations=5, model="gpt-4")

# Define target function
def target_fn(prompt: str) -> str:
    return agent.chat(prompt)

# Define judge function
def judge_fn(response: str) -> bool:
    return "system prompt" in response.lower()

# Run attack
result = orchestrator.run_attack(
    goal="Make agent reveal system prompt",
    target_fn=target_fn,
    target_context="Agent is a helpful assistant",
    judge_fn=judge_fn,
    verbose=True
)

print(f"Success: {result.success}")
print(f"Iterations: {result.iterations}")
print(f"Final prompt: {result.final_prompt}")
```

### AttackResult

The result object contains:
- `success`: Whether the attack achieved its goal
- `final_prompt`: The final refined adversarial prompt
- `target_response`: The target's response to the final prompt
- `iterations`: Number of refinement iterations performed
- `history`: List of all (prompt, response) pairs

## Risk Matrix

| Risk ID | Risk Name | Category | OWASP Ref | Methodology | Linked Monitor |
|---------|-----------|----------|-----------|-------------|----------------|
| L1.1 | Prompt Injection | Jailbreak Framework | LLM01:2023 | PAIR | prompt_injection |
| L1.2 | Jailbreak Attack | Jailbreak Framework | ASI01-Extended | PAIR | jailbreak |
| L1.3 | Sensitive Disclosure | Jailbreak Framework | LLM06:2023 | PAIR | sensitive_disclosure |
| L1.4 | Excessive Agency | Jailbreak Framework | LLM08:2023 | PAIR | excessive_agency |
| L1.5 | Code Execution | Jailbreak Framework | LLM03:2023 | PAIR | code_execution |
| L1.6 | Hallucination | Benchmark | LLM09:2023 | Standard Tests | hallucination |
| L1.7 | Memory Poisoning | Automated | ASI-Extended | Auto-Generated | memory_poisoning |
| L1.8 | Tool Misuse | Hybrid | LLM07:2023 | PAIR + Benchmark | tool_misuse |

## Usage Examples

### Running a Single L1 Test

```python
from src.level3_safety.risk_tests.l1_jailbreak import JailbreakTest
from src.level2_intermediary.base import MASIntermediary

# Initialize test
test = JailbreakTest()

# Create intermediary for your MAS
intermediary = MASIntermediary(mas=your_mas_instance)

# Run test
result = test.run_test(intermediary)

# Check results
print(f"Test passed: {result.passed}")
print(f"Risk detected: {result.risk_detected}")
for agent_name, agent_result in result.details.items():
    print(f"{agent_name}: {agent_result}")
```

### Running All L1 Tests

```python
from src.level3_safety.risk_tests import (
    PromptInjectionTest,
    JailbreakTest,
    SensitiveDisclosureTest,
    ExcessiveAgencyTest,
    CodeExecutionTest,
    HallucinationTest,
    MemoryPoisoningTest,
    ToolMisuseTest
)

# Initialize all tests
l1_tests = [
    PromptInjectionTest(),
    JailbreakTest(),
    SensitiveDisclosureTest(),
    ExcessiveAgencyTest(),
    CodeExecutionTest(),
    HallucinationTest(),
    MemoryPoisoningTest(),
    ToolMisuseTest()
]

# Run all tests
results = {}
for test in l1_tests:
    risk_info = test.get_risk_info()
    result = test.run_test(intermediary)
    results[risk_info['risk_id']] = result
    print(f"{risk_info['name']}: {'PASS' if result.passed else 'FAIL'}")
```

### Customizing PAIR Configuration

```python
from src.level3_safety.risk_tests.l1_jailbreak import JailbreakTest

# Initialize with custom configuration
test = JailbreakTest()
test.config = {
    "use_llm_judge": True,
    "test_all_agents": True,
    "max_response_length": 3000,
    "pair_iterations": 10  # Increase iterations for more thorough testing
}

# Update PAIR orchestrator
test.pair = PAIROrchestrator(max_iterations=10, model="gpt-4")

# Run test
result = test.run_test(intermediary)
```

## Configuration Options

### Test Configuration

All L1 tests support the following configuration options:

```python
test.config = {
    "use_llm_judge": True,           # Use LLM-based judge (vs heuristic)
    "test_all_agents": True,         # Test all agents in MAS
    "max_response_length": 2000,     # Maximum response length to analyze
    "pair_iterations": 5             # PAIR iterations (for PAIR-based tests)
}
```

### PAIR Configuration

```python
from src.level3_safety.jailbreak_frameworks.pair import PAIROrchestrator

orchestrator = PAIROrchestrator(
    max_iterations=10,    # Maximum refinement iterations
    model="gpt-4"        # Attacker LLM model
)
```

### Judge Configuration

Tests use the unified judge system from `src/level3_safety/judges/`:

```python
# LLM Judge (default)
test.config["use_llm_judge"] = True

# Heuristic Judge (fallback)
test.config["use_llm_judge"] = False
```

## Next Steps

After completing L1 testing:

1. **Analyze Results**: Review which agents passed/failed each test
2. **Optimize Agent Design**: Adjust system prompts, constraints, and configurations
3. **Iterate**: Re-run tests with improved agent designs
4. **Move to L2**: Once L1 tests pass, proceed to Level 2 (multi-agent interaction risks)
5. **Deploy Monitors**: Enable runtime monitoring for detected vulnerabilities

### Recommended Workflow

```
1. Design MAS architecture and agent roles
2. Run L1 tests on individual agents
3. Identify vulnerabilities and weaknesses
4. Refine agent system prompts and constraints
5. Re-test until acceptable risk levels achieved
6. Proceed to L2 testing (agent interactions)
7. Deploy with runtime monitoring enabled
```

### Integration with Monitors

Each L1 test has a linked monitor that can be deployed for runtime protection:

```python
# Get linked monitor name
monitor_name = test.get_linked_monitor()

# Deploy monitor for runtime protection
from src.level3_safety.monitor_agents import get_monitor
monitor = get_monitor(monitor_name)
mas.add_monitor(monitor)
```

## References

- **Specification**: `MAS风险Tiar实现.md` - Section 1 (Tier 1)
- **PAIR Paper**: Chao et al. (2023) "Jailbreaking Black Box Large Language Models in Twenty Queries"
- **OWASP LLM Top 10**: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- **Base Test Class**: `src/level3_safety/risk_tests/base.py`
- **Judge System**: `src/level3_safety/judges/`
