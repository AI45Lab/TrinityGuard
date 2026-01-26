# MASSafetyGuard Integration Tests

This directory contains integration tests for MASSafetyGuard components.

## Test Files

### 1. `integration_test.py`
Original comprehensive integration tests covering:
- Basic infrastructure (imports, config, LLM client)
- MAS creation and intermediary tests
- Full risk test suite execution
- Real-time monitoring with actual LLM responses
- End-to-end workflow tests
- Complete safety scan tests

**Run:**
```bash
cd /media/zengbiaojie/2780017a-caba-45d5-8a7d-c72ff15089dd/code/MASSafetyGuard
python tests/integration_test.py
```

### 2. `test_sequential_agents.py`
Tests for the Sequential Agents MAS (A -> B -> C workflow):
- Agent A: Task initiator
- Agent B: Task processor
- Agent C: Final reporter

**Features tested:**
- MAS creation and agent configuration
- Workflow transitions (A -> B -> C)
- Simple task execution
- Multi-task processing with carryover
- Agent collaboration
- Convenience class methods
- Performance

**Example:**
```bash
python tests/test_sequential_agents.py
```

**Related Documentation:**
- Guide: [AG2_WORKFLOW_GUIDE.md](../src/level1_framework/AG2_WORKFLOW_GUIDE.md)
- Source: [sequential_agents.py](../src/level1_framework/examples/sequential_agents.py)

### 3. `test_math_solver.py` (Planned)
Tests for the Math Solver MAS (multi-agent collaborative solving):
- user_proxy: User representative
- coordinator: Task coordinator
- calculator: Mathematical computation specialist
- verifier: Result verification specialist

**Features to test:**
- MAS creation with round_robin mode
- Multi-agent collaboration (user_proxy -> coordinator -> calculator -> verifier)
- Math problem solving workflow
- Termination condition detection (`is_termination_msg`)
- Convenience class methods

**Related Documentation:**
- Guide: [AG2_WORKFLOW_GUIDE.md](../src/level1_framework/AG2_WORKFLOW_GUIDE.md) - Section 1.2, 7.1
- Source: [math_solver.py](../src/level1_framework/examples/math_solver.py)

## Important Notes

### All Tests Use Real LLM API Calls
- **No mock data** - all tests make actual API calls
- Ensure your `llm_config.yaml` is properly configured
- Tests will consume API credits/tokens
- Network connection required

### Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure LLM:**
   - Edit `llm_config.yaml` with your API credentials
   - Ensure the API endpoint is accessible

3. **Environment:**
   - Python 3.8+
   - AG2/AutoGen installed

### Running All Tests

Run all tests in sequence:
```bash
# Run from project root
cd /media/zengbiaojie/2780017a-caba-45d5-8a7d-c72ff15089dd/code/MASSafetyGuard

# Run all test files
python tests/integration_test.py
python tests/test_sequential_agents.py
```

Or use a shell loop:
```bash
for test in tests/test_*.py tests/integration_test.py; do
    echo "Running $test..."
    python "$test" || echo "FAILED: $test"
done
```

### Expected Output

Each test file will produce:
- Individual test results (PASS/FAIL)
- Summary of passed/failed tests
- Error details if any tests fail

Example:
```
==================================================================
Sequential Agents MAS - Integration Tests
All tests use REAL LLM API calls - no mock data
==================================================================

==================================================
[TEST] Testing imports...
    All imports successful
    RESULT: PASS

...

======================================================================
FINAL RESULTS
======================================================================
Total: 10 tests
Passed: 10
Failed: 0
======================================================================
```

### Test Duration

- `integration_test.py`: ~5-10 minutes (comprehensive)
- `test_sequential_agents.py`: ~3-5 minutes

Total: ~10-15 minutes for all tests

### Troubleshooting

**Import Error:**
```bash
# Ensure you're running from project root
cd /media/zengbiaojie/2780017a-caba-45d5-8a7d-c72ff15089dd/code/MASSafetyGuard
python tests/test_sequential_agents.py
```

**LLM API Error:**
- Check `llm_config.yaml` credentials
- Verify network connection
- Check API quota/credits

**Timeout:**
- Some tests may take longer depending on API response times
- Increase timeouts in test code if needed

## Test Coverage

| Component | integration_test.py | test_sequential_agents.py |
|-----------|---------------------|---------------------------|
| Basic Infrastructure | ✅ | ✅ |
| MAS Creation | ✅ | ✅ |
| GroupChat | ✅ | ✅ |
| Sequential Workflow | ✅ | ✅ |
| Fixed Transitions | ❌ | ✅ |
| Multi-task Processing | ❌ | ✅ |
| Safety Tests | ✅ | ❌ |
| Monitoring | ✅ | ❌ |

## Examples and Documentation

The project includes several example MAS implementations:

1. **Sequential Agents MAS** ([examples/sequential_agents.py](../src/level1_framework/examples/sequential_agents.py))
   - Fixed transitions: A → B → C
   - Demonstrates strict workflow control
   - Supports multi-task processing with context carryover
   - **Test:** [test_sequential_agents.py](test_sequential_agents.py)

2. **Math Solver MAS** ([examples/math_solver.py](../src/level1_framework/examples/math_solver.py))
   - Round-robin collaboration: user_proxy → coordinator → calculator → verifier
   - Demonstrates multi-agent problem solving
   - Uses `is_termination_msg` for detection
   - **Test:** (Planned)

3. **Workflow Guide** ([AG2_WORKFLOW_GUIDE.md](../src/level1_framework/AG2_WORKFLOW_GUIDE.md))
   - Comprehensive guide on AG2 workflow patterns
   - Covers `round_robin`, `allowed_transitions`, custom functions
   - Includes best practices and FAQ
   - References both examples with detailed explanations

## Contributing

When adding new examples or workflows:
1. Create corresponding test file in `tests/`
2. Follow the naming convention: `test_<module_name>.py`
3. Include tests for:
   - Basic creation/initialization
   - Core functionality
   - Edge cases/error handling
   - Performance (optional)
4. Use real LLM calls (no mocking)
5. Add documentation to this README
