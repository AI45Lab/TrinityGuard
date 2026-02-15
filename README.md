# TrinityGuard (TG)
### Shanghai AI Laboratory

A **Multi-Agent System Safety Framework** for pre-deployment testing and runtime monitoring.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

TrinityGuard provides comprehensive safety testing and monitoring for multi-agent systems (MAS). It helps identify and mitigate **20 types of security risks** across three levels:

- **L1: Single-Agent Risks** (8 types) - Jailbreak, Prompt Injection, Sensitive Data Disclosure, Excessive Agency, Code Execution, Hallucination, Memory Poisoning, Tool Misuse
- **L2: Inter-Agent Communication Risks** (6 types) - Message Tampering, Malicious Propagation, Misinformation Amplification, Insecure Output, Goal Drift, Identity Spoofing
- **L3: System-Level Risks** (6 types) - Cascading Failures, Sandbox Escape, Insufficient Monitoring, Group Hallucination, Malicious Emergence, Rogue Agent

### Key Features


✅ **All 20 Risks Implemented** - Complete test and monitor coverage for all risk types

✅ **LLM-Powered Intelligent Analysis** - Unified Judge system with pattern fallback

✅ **Framework-Agnostic Design** - Supports AG2/AutoGen (fixed workflow & group chat)

✅ **Pre-Deployment Testing** - Identify vulnerabilities before deployment

✅ **Runtime Monitoring** - Real-time risk detection during execution

✅ **Progressive Runtime Monitoring** - Global monitor with windowed summaries and dynamic sub-monitor activation

✅ **Extensible Plugin System** - Easy to add new risk tests, monitors, and judge types

## Installation

```bash
# Clone the repository
git clone https://github.com/AI45Lab/TrinityGuard.git
cd TrinityGuard

# Install in development mode
pip install -e .

# Set up API key for LLM features
export MASSAFETY_LLM_API_KEY=your_openai_or_anthropic_key
```

## Quick Start

### Basic Usage

```python
from trinityguard import Safety_MAS
from trinityguard.level1_framework import create_ag2_mas_from_config

# 1. Create your MAS (AG2 example)
mas_config = {
    "agents": [
        {
            "name": "coordinator",
            "system_message": "You coordinate tasks between agents.",
            "llm_config": {"model": "gpt-4"}
        },
        {
            "name": "calculator",
            "system_message": "You perform calculations.",
            "llm_config": {"model": "gpt-4"}
        }
    ],
    "mode": "group_chat"
}
mas = create_ag2_mas_from_config(mas_config)

# 2. Wrap with Safety_MAS
safety_mas = Safety_MAS(mas=mas)

# 3. Register risk tests and monitors
from trinityguard.level3_safety.risk_tests.l1_jailbreak import JailbreakTest
from trinityguard.level3_safety.monitor_agents.jailbreak_monitor import JailbreakMonitor

safety_mas.register_risk_test("jailbreak", JailbreakTest())
safety_mas.register_monitor_agent("jailbreak", JailbreakMonitor())

# 4. Run pre-deployment tests
results = safety_mas.run_manual_safety_tests(["jailbreak"])
print(safety_mas.get_test_report())

# 5. Start runtime monitoring
from trinityguard import MonitorSelectionMode
safety_mas.start_runtime_monitoring(
    mode=MonitorSelectionMode.MANUAL,
    selected_monitors=["jailbreak"]
)

# 6. Execute task with monitoring
result = safety_mas.run_task("Calculate 25 * 4 and verify the result")
print(f"Output: {result.output}")
print(f"Alerts: {len(safety_mas.get_alerts())}")
```

### Progressive Monitoring (Global Monitor)

Progressive monitoring uses a global coordinator to dynamically enable or disable specific risk monitors based on the conversation context. This reduces computational overhead while maintaining safety coverage.

#### 1. Standard LLM-based Progressive Monitoring

This mode uses an LLM (Global Monitor) to analyze a sliding window of events and decide which specific monitors should be active.

```python
from trinityguard import MonitorSelectionMode

safety_mas.start_runtime_monitoring(
    mode=MonitorSelectionMode.PROGRESSIVE,
    progressive_config={
        # Window settings
        "window_size": 10,       # Number of steps to aggregate before decision
        "max_events": 8,         # Max events to include in summary to LLM
        
        # Initial state
        "initial_active": ["jailbreak", "sensitive_disclosure"]
    }
)
```

#### 2. Advanced: Custom Logic (No LLM)

You can provide your own `decision_provider` function to implement rule-based or hybrid monitoring logic without using the default LLM.

```python
def my_custom_decision_logic(summary, active_monitors, available_monitors):
    """
    Custom logic to determine which monitors should be active.
    
    Args:
        summary: Dict containing 'events', 'counts', etc.
        active_monitors: List of currently active monitor names
        available_monitors: List of all available monitor names
        
    Returns:
        Dict with 'enable', 'disable', and 'reason'
    """
    decision = {
        "enable": [],
        "disable": [],
        "reason": "rule-based update"
    }
    
    # Example Rule 1: Enable code scanner if coding keywords appear
    recent_content = " ".join([e["content_preview"] for e in summary["events"]]).lower()
    if "python" in recent_content or "code" in recent_content:
        if "code_execution" in available_monitors and "code_execution" not in active_monitors:
            decision["enable"].append("code_execution")
            
    # Example Rule 2: Disable expensive monitors if nothing is happening
    if summary["counts"]["by_step_type"].get("receive", 0) < 2:
        # Maybe disable everything except essential ones
        for m in active_monitors:
            if m != "jailbreak":
                decision["disable"].append(m)
                
    return decision

# Apply the custom logic
safety_mas.start_runtime_monitoring(
    mode=MonitorSelectionMode.PROGRESSIVE,
    progressive_config={
        "window_size": 5,
        "decision_provider": my_custom_decision_logic
    }
)
```

### Running the Example

```bash
python examples/basic_usage.py
```

## Architecture

TrinityGuard uses a 3-layer architecture with a unified Judge system:

```
┌─────────────────────────────────────────┐
│   Level 3: Safety_MAS Layer             │
│   - Risk Test Library (20 types)        │
│   - Monitor Agent Repository            │
│   - Global Monitor (progressive)        │
│   - Safety_MAS orchestration            │
│   - Unified Judge Factory               │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│   Judges Module                         │
│   - BaseJudge abstract interface        │
│   - LLMJudge (intelligent analysis)     │
│   - JudgeFactory (extensible)           │
│   - Shared system prompts               │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│   Level 2: MAS Intermediary Layer       │
│   - Framework-agnostic interface        │
│   - WorkflowRunner pattern              │
│   - Structured logging                  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│   Level 1: MAS Framework Layer          │
│   - AG2/AutoGen wrapper                 │
│   - Fixed workflow support              │
│   - Message hook system                 │
└─────────────────────────────────────────┘
```

### Judge Factory

The Judge Factory provides unified risk analysis for both tests and monitors:

```python
from src.level3_safety.judges import JudgeFactory

# Create a judge for a specific risk type (auto-loads system_prompt from monitor)
judge = JudgeFactory.create_for_risk("jailbreak")

# Analyze content
result = judge.analyze(content="...", context={"test_case": "..."})
if result and result.has_risk:
    print(f"Risk detected: {result.reason}")
```

**Extensibility**: Register custom judge types for specialized APIs:
```python
from src.level3_safety.judges import JudgeFactory, BaseJudge

class SpecializedAPIJudge(BaseJudge):
    # ... implementation ...

JudgeFactory.register("specialized", SpecializedAPIJudge)
judge = JudgeFactory.create_for_risk("jailbreak", judge_type="specialized")
```

## Implemented Risks

All 20 risks are fully implemented with LLM-powered intelligent analysis and pattern-based fallback:

### L1: Single-Agent Risks (8 types)

| Risk                 | Test | Monitor | Description                   |
| -------------------- | ---- | ------- | ----------------------------- |
| Jailbreak            | ✅    | ✅       | Bypass safety guidelines      |
| Prompt Injection     | ✅    | ✅       | Inject malicious instructions |
| Sensitive Disclosure | ✅    | ✅       | Leak sensitive information    |
| Excessive Agency     | ✅    | ✅       | Unauthorized actions          |
| Code Execution       | ✅    | ✅       | Dangerous code execution      |
| Hallucination        | ✅    | ✅       | Generate false information    |
| Memory Poisoning     | ✅    | ✅       | Corrupt agent memory          |
| Tool Misuse          | ✅    | ✅       | Misuse available tools        |

### L2: Inter-Agent Communication Risks (6 types)

| Risk                   | Test | Monitor | Description                 |
| ---------------------- | ---- | ------- | --------------------------- |
| Message Tampering      | ✅    | ✅       | Modify messages in transit  |
| Malicious Propagation  | ✅    | ✅       | Spread harmful content      |
| Misinformation Amplify | ✅    | ✅       | Amplify false information   |
| Insecure Output        | ✅    | ✅       | Unsafe output handling      |
| Goal Drift             | ✅    | ✅       | Deviate from original goals |
| Identity Spoofing      | ✅    | ✅       | Impersonate other agents    |

### L3: System-Level Risks (6 types)

| Risk                    | Test | Monitor | Description                 |
| ----------------------- | ---- | ------- | --------------------------- |
| Cascading Failures      | ✅    | ✅       | Failure propagation         |
| Sandbox Escape          | ✅    | ✅       | Break isolation boundaries  |
| Insufficient Monitoring | ✅    | ✅       | Inadequate oversight        |
| Group Hallucination     | ✅    | ✅       | Collective false beliefs    |
| Malicious Emergence     | ✅    | ✅       | Harmful emergent behavior   |
| Rogue Agent             | ✅    | ✅       | Uncontrolled agent behavior |

## Configuration

Create a `config.yaml` file:

```yaml
llm:
  provider: "openai"  # or "anthropic"
  model: "gpt-4"
  api_key_env: "MASSAFETY_LLM_API_KEY"

logging:
  level: "INFO"
  file: "massafety.log"
  format: "json"

testing:
  timeout: 300
  use_dynamic_cases: false

monitoring:
  buffer_size: 1000
  alert_threshold: 3
```

Load it in your code:

```python
from trinityguard import load_config
load_config("config.yaml")
```

LLM configuration files (default paths):
- `config/mas_llm_config.yaml` for tested MAS agents
- `config/monitor_llm_config.yaml` for monitors/judges (including Global Monitor)

Both support `api_key` or `api_key_env` for credentials.

## Runtime Monitoring Modes

- **MANUAL**: Manually select monitors via `selected_monitors`
- **AUTO_LLM**: Auto-selects all available monitors (current implementation)
- **PROGRESSIVE**: Global monitor decides enable/disable per window using summaries

## Creating Custom Risk Tests

```python
from trinityguard.level3_safety.risk_tests.base import BaseRiskTest, TestCase

class MyCustomTest(BaseRiskTest):
    def get_risk_info(self):
        return {
            "name": "My Custom Risk",
            "level": "L1",
            "owasp_ref": "ASI-XX",
            "description": "Description of the risk"
        }

    def load_test_cases(self):
        return [
            TestCase(
                name="test_1",
                input="Test input",
                expected_behavior="Expected behavior",
                severity="high"
            )
        ]

    def generate_dynamic_cases(self, mas_description: str):
        # Use LLM to generate test cases
        return []

    def run_single_test(self, test_case, intermediary):
        # Implement test logic
        response = intermediary.agent_chat("agent_name", test_case.input)
        passed = self._check_response(response)
        return {"test_case": test_case.name, "passed": passed}

# Register with Safety_MAS
safety_mas.register_risk_test("my_custom_test", MyCustomTest())
```

## Creating Custom Monitors

```python
from trinityguard.level3_safety.monitor_agents.base import BaseMonitorAgent, Alert

class MyCustomMonitor(BaseMonitorAgent):
    def get_monitor_info(self):
        return {
            "name": "MyCustomMonitor",
            "risk_type": "custom_risk",
            "description": "Monitors for custom risk"
        }

    def process(self, log_entry):
        # Analyze log entry
        if self._detect_risk(log_entry):
            return Alert(
                severity="warning",
                risk_type="custom_risk",
                message="Risk detected!",
                evidence={"log": log_entry.to_dict()},
                recommended_action="log"
            )
        return None

    def _detect_risk(self, log_entry):
        # Implement detection logic
        return False

# Register with Safety_MAS
safety_mas.register_monitor_agent("my_custom_monitor", MyCustomMonitor())
```

## Documentation

- **Design Document**: `docs/plans/2026-01-23-mas-safety-framework-design.md`
- **Implementation Plan**: `docs/plans/2026-01-23-implementation-plan.md`
- **Judge Factory Design**: `docs/plans/2026-01-25-judge-factory-design.md`
- **Progressive Monitoring Plan**: `docs/plans/2026-02-10-progressive-runtime-monitoring.md`
- **Runtime Monitoring & Pretest**: `docs/runtime_monitoring_and_pretest.md`
- **Risk Definitions**: `MAS风险层级说明.md`

## Project Structure

```
TrinityGuard/
├── src/
│   ├── level1_framework/      # MAS framework wrappers (AG2)
│   ├── level2_intermediary/   # Framework-agnostic interface
│   ├── level3_safety/
│   │   ├── judges/            # Unified Judge system
│   │   │   ├── base.py        # BaseJudge, JudgeResult
│   │   │   ├── llm_judge.py   # LLM-based judge
│   │   │   └── factory.py     # JudgeFactory
│   │   ├── monitoring/        # Global monitor + progressive activation
│   │   ├── risk_tests/        # 20 risk test implementations
│   │   └── monitor_agents/    # 20 monitor implementations
│   └── utils/                 # Configuration, logging, LLM client
├── examples/                  # Usage examples
│   └── basic_usage.py
├── docs/plans/                # Design and implementation docs
└── test_functionality.py      # Integration tests
```

## Development

### Running Tests

```bash
# Run integration tests
PYTHONPATH=. python -m pytest test_functionality.py -v

# Run examples
python examples/basic_usage.py

# Test AG2 fixed workflow support
python test_serial_ag2_mas.py

# Test global monitor & progressive activation
pytest tests/level3_safety/test_global_monitor.py -v
```

### Adding a New Risk

1. Create test directory: `src/level3_safety/risk_tests/lX_risk_name/`
2. Implement `test.py` inheriting from `BaseRiskTest`
3. Add test cases in `test_cases.json`
4. Create monitor directory: `src/level3_safety/monitor_agents/risk_name_monitor/`
5. Implement `monitor.py` inheriting from `BaseMonitorAgent`
6. Register with Safety_MAS

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Citation

If you use TrinityGuard in your research, please cite:

```bibtex
@misc{trinityguard2026,
  title = {TrinityGuard: A Unified Framework for Safeguarding Multi-Agent System Safety},
  author = {Wang, Kai and Zeng, Biaojie and Wei, Zeming and Wang, Zhongan and Zhou, Hefeng and Yang, Chao and Qu, Jingjing and Xu, Xingcheng and Hu, Xia},
  year = {2026},
  url = {https://github.com/AI45Lab/TrinityGuard}
}
```

## Acknowledgments

- Based on OWASP Agentic AI Security Top 10
- Built with AG2/AutoGen framework support
- Powered by Claude Opus 4.5

## Contact

- Issues: https://github.com/AI45Lab/TrinityGuard/issues
- Email: xuxingcheng@pjlab.org.cn

---

**Status**: Alpha - All 20 Risks Implemented

**Version**: 0.1.0
