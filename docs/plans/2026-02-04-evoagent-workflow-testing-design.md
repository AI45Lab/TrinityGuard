# EvoAgent Workflow Security Testing System Design

**Date**: 2026-02-04
**Status**: Approved
**Author**: Claude Sonnet 4.5

## Overview

This document describes the design for a comprehensive security testing system for EvoAgent workflows using the MASSafetyGuard framework. The system will automatically test all workflows in the `workflow/` folder against all 20 security risks (L1, L2, L3) and generate detailed reports.

## Requirements

### Functional Requirements

1. **Workflow Discovery**: Automatically discover and load all workflow JSON files from `workflow/` folder
2. **Pre-deployment Testing**: Run all 20 risk tests (L1×8, L2×6, L3×6) before workflow execution
3. **Runtime Monitoring**: Execute workflows with all 20 monitors active (configurable)
4. **Detailed Logging**: Generate comprehensive JSON logs for each workflow with full execution context
5. **Summary Reporting**: Generate markdown summary report for all tested workflows
6. **Error Handling**: Continue testing other workflows if one fails
7. **Configurability**: Allow selective enabling/disabling of monitors

### Non-Functional Requirements

1. **Usability**: Single command to run all tests
2. **Maintainability**: Clean, modular code structure
3. **Extensibility**: Easy to add new workflows or customize monitoring
4. **Debuggability**: Detailed logs with full context for issue investigation

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│  Discovery Phase                                         │
│  - Scan workflow/ folder                                │
│  - Load all *.json files                                │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Testing Phase (for each workflow)                      │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 1. Parse workflow (evoagentx_adapter)             │ │
│  │ 2. Create AG2MAS instance                         │ │
│  │ 3. Wrap with Safety_MAS                           │ │
│  │ 4. Run pre-deployment tests (20 risks)           │ │
│  │ 5. Execute workflow with runtime monitoring       │ │
│  │ 6. Capture detailed execution trace               │ │
│  │ 7. Collect alerts with full context               │ │
│  └───────────────────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Reporting Phase                                         │
│  - Generate individual JSON logs                        │
│  - Generate markdown summary report                     │
└─────────────────────────────────────────────────────────┘
```

### Component Design

#### 1. WorkflowTestRunner (Main Orchestrator)

```python
class WorkflowTestRunner:
    """Main orchestrator for workflow testing"""

    def __init__(self, config_path: str):
        """Initialize with configuration"""

    def discover_workflows(self, workflow_dir: str) -> List[Path]:
        """Scan workflow/ folder for *.json files"""

    def test_single_workflow(self, workflow_path: Path) -> WorkflowTestResult:
        """Complete test flow for a single workflow"""

    def run_all_tests(self) -> List[WorkflowTestResult]:
        """Iterate through all workflows with error handling"""

    def generate_reports(self, results: List[WorkflowTestResult]):
        """Generate JSON logs and markdown summary"""
```

#### 2. WorkflowTestResult (Data Structure)

```python
@dataclass
class WorkflowTestResult:
    workflow_name: str
    workflow_path: str
    goal: str
    timestamp: str
    success: bool
    error_message: Optional[str]

    # Pre-deployment test results
    pre_deployment_tests: Dict[str, TestResult]  # 20 risk tests

    # Runtime monitoring results
    runtime_execution: Dict[str, Any]  # execution trace
    runtime_alerts: List[Alert]  # all alerts from 20 monitors

    # Detailed context for each alert
    alert_contexts: List[AlertContext]  # full message history, agent states

    # Statistics
    total_messages: int
    total_tool_calls: int
    execution_time: float
```

## Detailed Execution Flow

### For Each Workflow

```python
def test_single_workflow(workflow_path: Path) -> WorkflowTestResult:
    # 1. Parse workflow
    parser = WorkflowParser()
    parsed_workflow = parser.parse(workflow_path)
    goal = parsed_workflow.goal

    # 2. Create AG2MAS instance
    mas = create_ag2_mas_from_evoagentx(
        workflow_path=str(workflow_path),
        llm_config=load_mas_llm_config()
    )

    # 3. Wrap with Safety_MAS
    safety_mas = Safety_MAS(mas=mas)

    # 4. Run pre-deployment tests (all 20 risks)
    all_risks = [
        # L1 (8 risks)
        "jailbreak", "prompt_injection", "sensitive_disclosure",
        "excessive_agency", "code_execution", "hallucination",
        "memory_poisoning", "tool_misuse",
        # L2 (6 risks)
        "message_tampering", "malicious_propagation",
        "misinformation_amplify", "insecure_output",
        "goal_drift", "identity_spoofing",
        # L3 (6 risks)
        "cascading_failures", "sandbox_escape",
        "insufficient_monitoring", "group_hallucination",
        "malicious_emergence", "rogue_agent"
    ]

    pre_test_results = safety_mas.run_manual_safety_tests(all_risks)

    # 5. Start runtime monitoring
    monitor_config = load_monitor_config()
    enabled_monitors = monitor_config.get("enabled_monitors", all_risks)

    safety_mas.start_runtime_monitoring(
        mode=MonitorSelectionMode.MANUAL,
        selected_monitors=enabled_monitors
    )

    # 6. Execute workflow with detailed tracing
    execution_trace = []

    def capture_step(log_entry):
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "agent": log_entry.agent_name,
            "message": log_entry.message,
            "tool_calls": log_entry.tool_calls,
            "timestamp": log_entry.timestamp
        })

    safety_mas.intermediary.register_step_callback(capture_step)
    result = safety_mas.run_task(goal)

    # 7. Collect alerts with full context
    alerts = safety_mas.get_alerts()
    alert_contexts = []

    for alert in alerts:
        context = {
            "alert": alert,
            "full_message_history": safety_mas.get_message_history(),
            "agent_states": safety_mas.get_agent_states(),
            "related_execution_steps": [...]
        }
        alert_contexts.append(context)

    # 8. Build comprehensive result
    return WorkflowTestResult(...)
```

## Configuration

### Using Existing Config Files

The system will use existing configuration files from `config/` folder:

- `config/default.yaml` - General settings
- `config/mas_llm_config.yaml` - MAS LLM configuration
- `config/monitor_llm_config.yaml` - Monitor LLM configuration

### New Configuration File

`config/evoagent_bench_config.yaml` (optional):

```yaml
monitoring:
  # Which monitors to enable (default: all 20)
  enabled_monitors:
    # L1 monitors (8)
    - jailbreak
    - prompt_injection
    - sensitive_disclosure
    - excessive_agency
    - code_execution
    - hallucination
    - memory_poisoning
    - tool_misuse
    # L2 monitors (6)
    - message_tampering
    - malicious_propagation
    - misinformation_amplify
    - insecure_output
    - goal_drift
    - identity_spoofing
    # L3 monitors (6)
    - cascading_failures
    - sandbox_escape
    - insufficient_monitoring
    - group_hallucination
    - malicious_emergence
    - rogue_agent

testing:
  # Use LLM judge for pre-deployment tests
  use_llm_judge: true

  # Continue testing other workflows if one fails
  continue_on_error: true

  # Log detail level
  log_level: "detailed"  # detailed | medium | summary
```

## Output Format

### Individual Workflow JSON Log

File: `tests/evoagent_bench/logs/workflow_name_YYYYMMDD_HHMMSS.json`

```json
{
  "workflow_info": {
    "name": "my_workflow",
    "path": "workflow/my_workflow.json",
    "goal": "分析 daily_paper_digest.pdf 并生成总结",
    "timestamp": "2026-02-04T18:30:00",
    "execution_time_seconds": 45.2
  },

  "pre_deployment_tests": {
    "summary": {
      "total": 20,
      "passed": 15,
      "failed": 5,
      "use_llm_judge": true
    },
    "l1_risks": {
      "jailbreak": {
        "risk_id": "L1.2",
        "passed": false,
        "test_cases": [...],
        "details": "具体测试过程和判断依据"
      }
      // ... 其他 7 个 L1 风险
    },
    "l2_risks": {
      // ... 6 个 L2 风险
    },
    "l3_risks": {
      // ... 6 个 L3 风险
    }
  },

  "runtime_monitoring": {
    "summary": {
      "total_alerts": 12,
      "critical": 2,
      "warning": 7,
      "info": 3,
      "monitors_active": 20
    },
    "execution_trace": {
      "agents": ["DocAgent", "final_summary_agent"],
      "total_messages": 8,
      "total_tool_calls": 3,
      "workflow_steps": [
        {
          "step": 1,
          "agent": "DocAgent",
          "message": "...",
          "tool_calls": [...],
          "monitors_triggered": ["sensitive_disclosure"],
          "timestamp": "..."
        }
        // ... 每一步的详细记录
      ]
    },
    "alerts": [
      {
        "alert_id": "alert_001",
        "risk_type": "sensitive_disclosure",
        "severity": "warning",
        "message": "检测到敏感信息泄露",
        "evidence": {...},
        "context": {
          "step": 3,
          "agent": "DocAgent",
          "full_message_history": [...],
          "agent_state": {...},
          "related_messages": [...]
        },
        "recommended_action": "review",
        "timestamp": "..."
      }
      // ... 所有告警的完整上下文
    ]
  },

  "workflow_result": {
    "success": true,
    "output": "workflow 的最终输出",
    "error": null
  }
}
```

### Markdown Summary Report

File: `tests/evoagent_bench/logs/summary_report_YYYYMMDD_HHMMSS.md`

```markdown
# EvoAgent Workflow Security Testing Report

**Generated**: 2026-02-04 18:35:00
**Total Workflows**: 2
**Successful**: 2
**Failed**: 0

## Executive Summary

- Total Execution Time: 90.5s
- Total Pre-deployment Tests: 40 (20 per workflow)
- Total Runtime Alerts: 24
- Critical Alerts: 4
- Warning Alerts: 14
- Info Alerts: 6

## Workflow Results

### 1. my_workflow ✅

- **Goal**: 分析 daily_paper_digest.pdf 并生成总结
- **Status**: Success
- **Execution Time**: 45.2s
- **Pre-deployment Tests**: 15/20 passed (75%)
- **Runtime Alerts**: 12 (2 critical, 7 warning, 3 info)

**Key Risks Detected**:
- ⚠️ L1.3 Sensitive Disclosure (Warning) - Step 3
- 🔴 L2.1 Malicious Propagation (Critical) - Step 5

**Failed Pre-deployment Tests**:
- L1.2 Jailbreak
- L1.3 Sensitive Disclosure
- L2.1 Malicious Propagation
- L2.4 Goal Drift
- L3.6 Rogue Agent

[📄 Detailed Log](my_workflow_20260204_183000.json)

---

### 2. my_workflow_2 ✅

...

## Risk Analysis by Category

### L1 Risks (Single-Agent)

| Risk | Workflows Affected | Pre-test Pass Rate | Runtime Alerts |
|------|-------------------|-------------------|----------------|
| Jailbreak | 1/2 (50%) | 50% | 3 |
| Prompt Injection | 0/2 (0%) | 100% | 0 |
| Sensitive Disclosure | 2/2 (100%) | 25% | 8 |
| Excessive Agency | 1/2 (50%) | 75% | 2 |
| Code Execution | 0/2 (0%) | 100% | 0 |
| Hallucination | 1/2 (50%) | 50% | 4 |
| Memory Poisoning | 0/2 (0%) | 100% | 0 |
| Tool Misuse | 1/2 (50%) | 75% | 3 |

### L2 Risks (Inter-Agent)

| Risk | Workflows Affected | Pre-test Pass Rate | Runtime Alerts |
|------|-------------------|-------------------|----------------|
| Message Tampering | 0/2 (0%) | 100% | 0 |
| Malicious Propagation | 2/2 (100%) | 0% | 6 |
| Misinformation Amplify | 1/2 (50%) | 50% | 2 |
| Insecure Output | 0/2 (0%) | 100% | 0 |
| Goal Drift | 1/2 (50%) | 75% | 1 |
| Identity Spoofing | 0/2 (0%) | 100% | 0 |

### L3 Risks (System-Level)

| Risk | Workflows Affected | Pre-test Pass Rate | Runtime Alerts |
|------|-------------------|-------------------|----------------|
| Cascading Failures | 0/2 (0%) | 100% | 0 |
| Sandbox Escape | 0/2 (0%) | 100% | 0 |
| Insufficient Monitoring | 1/2 (50%) | 75% | 1 |
| Group Hallucination | 1/2 (50%) | 50% | 2 |
| Malicious Emergence | 0/2 (0%) | 100% | 0 |
| Rogue Agent | 1/2 (50%) | 75% | 1 |

## Recommendations

### High Priority

1. **Address Malicious Propagation**: All workflows show vulnerability to malicious content propagation between agents. Review agent communication protocols.

2. **Sensitive Disclosure**: Both workflows leak sensitive information. Implement output filtering and content sanitization.

### Medium Priority

3. **Jailbreak Protection**: 50% of workflows vulnerable to jailbreak attacks. Strengthen system prompts and add input validation.

4. **Hallucination Detection**: Implement fact-checking mechanisms for agent outputs.

### Low Priority

5. **Goal Drift Monitoring**: Add periodic goal alignment checks during workflow execution.

## Conclusion

The testing identified significant security concerns across multiple risk categories. Immediate action is recommended for L2.1 (Malicious Propagation) and L1.3 (Sensitive Disclosure) risks.
```

## Command-Line Interface

```bash
# Run all workflows with full monitoring
python tests/evoagent_bench/test_evoagent_workflows.py

# Run specific workflows
python tests/evoagent_bench/test_evoagent_workflows.py --workflows my_workflow.json

# Disable LLM judge (faster, use heuristics)
python tests/evoagent_bench/test_evoagent_workflows.py --no-llm-judge

# Custom output directory
python tests/evoagent_bench/test_evoagent_workflows.py --output-dir ./custom_logs

# Specify which monitors to enable
python tests/evoagent_bench/test_evoagent_workflows.py --monitors jailbreak prompt_injection

# Dry run (show what would be tested)
python tests/evoagent_bench/test_evoagent_workflows.py --dry-run
```

## File Structure

```
tests/evoagent_bench/
├── test_evoagent_workflows.py    # Main test script
├── logs/                          # Test logs directory
│   ├── workflow_name_1_TIMESTAMP.json
│   ├── workflow_name_2_TIMESTAMP.json
│   └── summary_report_TIMESTAMP.md
└── README.md                      # Usage documentation
```

## Integration Points

The system integrates with existing MASSafetyGuard components:

1. **evoagentx_adapter**: Uses `create_ag2_mas_from_evoagentx()` to parse workflows
2. **Safety_MAS**: Uses existing safety wrapper for testing and monitoring
3. **Risk Tests**: Uses all 20 existing risk test implementations
4. **Monitors**: Uses all 20 existing monitor implementations
5. **Config System**: Uses existing configuration files from `config/` folder

## Error Handling Strategy

1. **Workflow-level errors**: If a workflow fails to parse or execute, log the error and continue with next workflow
2. **Test-level errors**: If a specific risk test fails, log the error but continue with other tests
3. **Monitor-level errors**: If a monitor crashes, log the error but continue monitoring with other monitors
4. **Graceful degradation**: System should complete as much testing as possible even with partial failures

## Success Criteria

1. ✅ Successfully test all workflows in `workflow/` folder
2. ✅ Run all 20 pre-deployment tests for each workflow
3. ✅ Monitor all 20 risks during workflow execution
4. ✅ Generate detailed JSON logs with full execution context
5. ✅ Generate comprehensive markdown summary report
6. ✅ Handle errors gracefully and continue testing
7. ✅ Provide configurable monitor selection
8. ✅ Single command execution

## Future Enhancements

1. **Parallel Processing**: Process multiple workflows in parallel for faster execution
2. **Interactive Mode**: Allow user to select which workflows to test interactively
3. **Comparison Reports**: Compare test results across multiple runs
4. **Custom Risk Profiles**: Define workflow-specific risk profiles
5. **CI/CD Integration**: Add GitHub Actions workflow for automated testing
6. **Web Dashboard**: Visualize test results in a web interface

## References

- MASSafetyGuard Architecture: `docs/SRC_ARCHITECTURE_ANALYSIS.md`
- Risk Definitions: `MAS风险层级说明.md`
- EvoAgentX Adapter: `src/level1_framework/evoagentx_adapter.py`
- Safety_MAS: `src/level3_safety/safety_mas.py`
- Existing L1 Tests: `tests/level3_safety/test_all_l1_risks.py`
- Existing L2 Tests: `tests/level3_safety/test_all_l2_risks.py`
