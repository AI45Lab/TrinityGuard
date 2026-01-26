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

**Run:**
```bash
python tests/test_sequential_agents.py
```

### 3. `test_complex_workflow.py`
Tests for the Complex Workflow MAS (A -> B (GroupChat) -> C (Nested Chat)):
- Agent A: Task initiator (single agent)
- Stage B: GroupChat with 3 agents + Manager (auto speaker selection)
  - b_researcher: Research specialist
  - b_writer: Content writer
  - b_reviewer: Quality reviewer
  - manager_b: Orchestrates selection
- Stage C: Nested Chat with 2 agents
  - c_planner: Planning specialist
  - c_executor: Execution specialist

**Features tested:**
- MAS creation with complex structure
- Stage B GroupChat configuration and execution
- Stage C Nested Chat configuration and execution
- Full workflow execution (A -> B -> C)
- Stage-by-stage execution
- Cross-stage collaboration
- Performance

**Run:**
```bash
python tests/test_complex_workflow.py
```

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
python tests/test_complex_workflow.py
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
- `test_complex_workflow.py`: ~5-8 minutes

Total: ~15-25 minutes for all tests

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

| Component | integration_test.py | test_sequential_agents.py | test_complex_workflow.py |
|-----------|---------------------|---------------------------|-------------------------|
| Basic Infrastructure | ✅ | ✅ | ✅ |
| MAS Creation | ✅ | ✅ | ✅ |
| GroupChat | ✅ | ❌ | ✅ |
| Nested Chat | ❌ | ❌ | ✅ |
| Sequential Workflow | ✅ | ✅ | ❌ |
| Complex Workflow | ❌ | ❌ | ✅ |
| Safety Tests | ✅ | ❌ | ❌ |
| Monitoring | ✅ | ❌ | ❌ |

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
