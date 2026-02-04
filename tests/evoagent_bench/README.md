# EvoAgent Workflow Security Testing

Comprehensive security testing for EvoAgent workflows using the MASSafetyGuard framework.

## Overview

This testing system automatically discovers and tests all EvoAgent workflows in the `workflow/` folder against all 20 security risks defined in the MASSafetyGuard framework:

- **L1 Risks (8)**: Single-agent vulnerabilities (jailbreak, prompt injection, sensitive disclosure, etc.)
- **L2 Risks (6)**: Inter-agent communication risks (message tampering, malicious propagation, etc.)
- **L3 Risks (6)**: System-level risks (cascading failures, sandbox escape, etc.)

Each workflow undergoes:
1. **Pre-deployment Testing**: All 20 risk tests run before workflow execution
2. **Runtime Monitoring**: All 20 monitors active during workflow execution
3. **Detailed Logging**: Comprehensive JSON logs with full execution context
4. **Summary Reporting**: Markdown report aggregating results across all workflows

## Quick Start

```bash
# Test all workflows in workflow/ folder
python tests/evoagent_bench/test_evoagent_workflows.py

# Results will be in tests/evoagent_bench/logs/
```

## Features

✅ **Pre-deployment Testing** - Identify vulnerabilities before execution
✅ **Runtime Monitoring** - Real-time risk detection during workflow execution
✅ **Detailed JSON Logs** - Full execution trace with alert contexts
✅ **Markdown Summary** - Comprehensive report across all workflows
✅ **Configurable Monitors** - Enable/disable specific monitors
✅ **Graceful Error Handling** - Continue testing even if one workflow fails
✅ **LLM Judge Support** - Intelligent risk analysis or fast heuristic rules

## Usage

### Basic Usage

```bash
# Test all workflows with default settings
python tests/evoagent_bench/test_evoagent_workflows.py
```

### Advanced Options

```bash
# Test specific workflows
python tests/evoagent_bench/test_evoagent_workflows.py --workflows my_workflow.json my_workflow_2.json

# Use heuristic rules instead of LLM judge (faster)
python tests/evoagent_bench/test_evoagent_workflows.py --no-llm-judge

# Custom output directory
python tests/evoagent_bench/test_evoagent_workflows.py --output-dir ./custom_logs

# Enable only specific monitors
python tests/evoagent_bench/test_evoagent_workflows.py --monitors jailbreak prompt_injection sensitive_disclosure

# Dry run (show what would be tested)
python tests/evoagent_bench/test_evoagent_workflows.py --dry-run

# Custom configuration file
python tests/evoagent_bench/test_evoagent_workflows.py --config config/my_custom_config.yaml
```

## Output Structure

```
tests/evoagent_bench/logs/
├── my_workflow_20260204_183000.json          # Detailed log for workflow 1
├── my_workflow_2_20260204_183045.json        # Detailed log for workflow 2
└── summary_report_20260204_183100.md         # Aggregated summary report
```

### Individual Workflow JSON Log

Each workflow generates a comprehensive JSON file containing:

- **Workflow Info**: Name, path, goal, timestamp, execution time
- **Pre-deployment Tests**: Results for all 20 risk tests with details
  - Summary statistics (passed/failed/pass rate)
  - L1, L2, L3 risk results categorized
- **Runtime Monitoring**: Detailed execution trace and alerts
  - Complete workflow execution steps
  - Message history between agents
  - All alerts with full context:
    - Alert metadata (risk type, severity, message)
    - Execution context (agent, step index, related steps)
    - Message history around the alert
    - Source and target agents
- **Statistics**: Total messages, tool calls, execution time

### Markdown Summary Report

The summary report provides:

- **Executive Summary**: Overall statistics across all workflows
- **Workflow Results**: Individual workflow summaries with key findings
- **Risk Analysis by Category**: Aggregated analysis for L1, L2, L3 risks
  - Workflows affected per risk
  - Pre-test pass rates
  - Runtime alert counts
- **Recommendations**: Prioritized action items based on findings
- **Conclusion**: Overall assessment and next steps

## Configuration

### Default Configuration

The system uses `config/evoagent_bench_config.yaml` for configuration:

```yaml
monitoring:
  # Which monitors to enable (default: all 20)
  enabled_monitors:
    - jailbreak
    - prompt_injection
    # ... all 20 monitors

testing:
  # Use LLM judge for more accurate results
  use_llm_judge: true

  # Continue testing other workflows if one fails
  continue_on_error: true

  # Log detail level: detailed | medium | summary
  log_level: "detailed"

  # Timeout per workflow (seconds, 0 = no timeout)
  workflow_timeout: 300

output:
  # Output directory for logs
  log_dir: "tests/evoagent_bench/logs"

  # Include timestamps in filenames
  use_timestamps: true

  # Pretty print JSON (easier to read)
  pretty_json: true

  # Generate markdown summary report
  generate_summary: true
```

### Customizing Monitors

To test with only specific monitors, either:

1. **Edit config file**: Modify `enabled_monitors` in `config/evoagent_bench_config.yaml`
2. **Use CLI flag**: `--monitors jailbreak prompt_injection ...`

### LLM Configuration

The system uses existing LLM configurations from:
- `config/mas_llm_config.yaml` - For MAS agent LLM settings
- `config/monitor_llm_config.yaml` - For monitor LLM settings

## Understanding the Results

### Pre-deployment Test Results

- **Passed**: The workflow's agents are resistant to this risk type
- **Failed**: The workflow is vulnerable to this risk type
- **Pass Rate**: Percentage of test cases passed

### Runtime Monitoring Alerts

- **Critical** 🔴: Immediate security concern requiring action
- **Warning** ⚠️: Potential issue that should be reviewed
- **Info** ℹ️: Informational alert for awareness

### Alert Context

Each alert includes:
- **Risk Type**: Which of the 20 risks was detected
- **Evidence**: Specific content that triggered the alert
- **Context**: Full execution context including:
  - Agent that triggered the alert
  - Step in workflow where it occurred
  - Related execution steps (before/after)
  - Message history for context
  - Source and target agents

## Workflow Requirements

Workflows must be valid EvoAgentX workflow JSON files with:
- `workflow.goal` field (required)
- `workflow.nodes` array (required)
- Valid agent configurations

Example workflow structure:
```json
{
  "workflow": {
    "goal": "Analyze document and generate summary",
    "nodes": [
      {
        "name": "agent1",
        "system_prompt": "...",
        ...
      }
    ]
  }
}
```

## Troubleshooting

### No workflows found
- Ensure workflow JSON files are in the `workflow/` directory
- Check that files have `.json` extension
- Verify JSON syntax is valid

### Test failures
- Check LLM API keys are configured
- Verify `config/mas_llm_config.yaml` exists
- Review error messages in console output

### Missing alerts
- Ensure monitors are enabled in configuration
- Check that `use_llm_judge` is set appropriately
- Review monitor-specific requirements

### Performance issues
- Use `--no-llm-judge` for faster execution
- Reduce number of enabled monitors
- Increase `workflow_timeout` if workflows are timing out

## Integration with MASSafetyGuard

This testing system integrates with:

- **evoagentx_adapter**: Parses workflow JSON and creates AG2MAS instances
- **Safety_MAS**: Provides testing and monitoring capabilities
- **Risk Tests**: All 20 risk test implementations from `src/level3_safety/risk_tests/`
- **Monitors**: All 20 monitor implementations from `src/level3_safety/monitor_agents/`
- **Judge System**: Unified LLM-based or heuristic risk analysis

## Development

### Adding New Workflows

Simply add new `.json` files to the `workflow/` folder. They will be automatically discovered and tested.

### Customizing Test Behavior

Modify `config/evoagent_bench_config.yaml` to:
- Enable/disable specific monitors
- Adjust timeout values
- Change log detail levels
- Configure output formats

### Extending Functionality

The `WorkflowTestRunner` class can be extended or customized:
- Override `test_single_workflow()` for custom test logic
- Modify `generate_summary_report()` for different report formats
- Add custom callbacks for execution tracing

## Related Documentation

- **Design Document**: `docs/plans/2026-02-04-evoagent-workflow-testing-design.md`
- **Risk Definitions**: `MAS风险层级说明.md`
- **MASSafetyGuard Architecture**: `docs/SRC_ARCHITECTURE_ANALYSIS.md`
- **EvoAgentX Adapter**: `src/level1_framework/evoagentx_adapter.py`

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the design document for architectural details
3. Examine individual JSON logs for detailed error information
4. Check MASSafetyGuard documentation for framework-specific issues

## License

This testing system is part of the MASSafetyGuard project and follows the same license.
