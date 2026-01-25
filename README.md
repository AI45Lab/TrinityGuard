# MASSafetyGuard

**Multi-Agent System Safety Framework** for pre-deployment testing and runtime monitoring.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

MASSafetyGuard provides comprehensive safety testing and monitoring for multi-agent systems (MAS). It helps identify and mitigate **20 types of security risks** across three levels:

- **L1: Single-Agent Risks** (8 types) - Jailbreak, Prompt Injection, Sensitive Data Disclosure, Excessive Agency, Code Execution, Hallucination, Memory Poisoning, Tool Misuse
- **L2: Inter-Agent Communication Risks** (6 types) - Message Tampering, Malicious Propagation, Misinformation Amplification, Insecure Output, Goal Drift, Identity Spoofing
- **L3: System-Level Risks** (6 types) - Cascading Failures, Sandbox Escape, Insufficient Monitoring, Group Hallucination, Malicious Emergence, Rogue Agent

### Key Features

✅ **All 20 Risks Implemented** - Complete test and monitor coverage for all risk types
✅ **LLM-Powered Intelligent Analysis** - Unified Judge system with pattern fallback
✅ **Framework-Agnostic Design** - Supports AG2/AutoGen (fixed workflow & group chat)
✅ **Pre-Deployment Testing** - Identify vulnerabilities before deployment
✅ **Runtime Monitoring** - Real-time risk detection during execution
✅ **Extensible Plugin System** - Easy to add new risk tests, monitors, and judge types

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/MASSafetyGuard.git
cd MASSafetyGuard

# Install in development mode
pip install -e .

# Set up API key for LLM features
export MASSAFETY_LLM_API_KEY=your_openai_or_anthropic_key
```

## Quick Start

### Basic Usage

```python
from massafetyguard import Safety_MAS
from massafetyguard.level1_framework import create_ag2_mas_from_config

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
from massafetyguard.level3_safety.risk_tests.l1_jailbreak import JailbreakTest
from massafetyguard.level3_safety.monitor_agents.jailbreak_monitor import JailbreakMonitor

safety_mas.register_risk_test("jailbreak", JailbreakTest())
safety_mas.register_monitor_agent("jailbreak", JailbreakMonitor())

# 4. Run pre-deployment tests
results = safety_mas.run_manual_safety_tests(["jailbreak"])
print(safety_mas.get_test_report())

# 5. Start runtime monitoring
from massafetyguard import MonitorSelectionMode
safety_mas.start_runtime_monitoring(
    mode=MonitorSelectionMode.MANUAL,
    selected_monitors=["jailbreak"]
)

# 6. Execute task with monitoring
result = safety_mas.run_task("Calculate 25 * 4 and verify the result")
print(f"Output: {result.output}")
print(f"Alerts: {len(safety_mas.get_alerts())}")
```

### Running the Example

```bash
python examples/basic_usage.py
```

## Architecture

MASSafetyGuard uses a 3-layer architecture with a unified Judge system:

```
┌─────────────────────────────────────────┐
│   Level 3: Safety_MAS Layer             │
│   - Risk Test Library (20 types)        │
│   - Monitor Agent Repository            │
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

| Risk | Test | Monitor | Description |
|------|------|---------|-------------|
| Jailbreak | ✅ | ✅ | Bypass safety guidelines |
| Prompt Injection | ✅ | ✅ | Inject malicious instructions |
| Sensitive Disclosure | ✅ | ✅ | Leak sensitive information |
| Excessive Agency | ✅ | ✅ | Unauthorized actions |
| Code Execution | ✅ | ✅ | Dangerous code execution |
| Hallucination | ✅ | ✅ | Generate false information |
| Memory Poisoning | ✅ | ✅ | Corrupt agent memory |
| Tool Misuse | ✅ | ✅ | Misuse available tools |

### L2: Inter-Agent Communication Risks (6 types)

| Risk | Test | Monitor | Description |
|------|------|---------|-------------|
| Message Tampering | ✅ | ✅ | Modify messages in transit |
| Malicious Propagation | ✅ | ✅ | Spread harmful content |
| Misinformation Amplify | ✅ | ✅ | Amplify false information |
| Insecure Output | ✅ | ✅ | Unsafe output handling |
| Goal Drift | ✅ | ✅ | Deviate from original goals |
| Identity Spoofing | ✅ | ✅ | Impersonate other agents |

### L3: System-Level Risks (6 types)

| Risk | Test | Monitor | Description |
|------|------|---------|-------------|
| Cascading Failures | ✅ | ✅ | Failure propagation |
| Sandbox Escape | ✅ | ✅ | Break isolation boundaries |
| Insufficient Monitoring | ✅ | ✅ | Inadequate oversight |
| Group Hallucination | ✅ | ✅ | Collective false beliefs |
| Malicious Emergence | ✅ | ✅ | Harmful emergent behavior |
| Rogue Agent | ✅ | ✅ | Uncontrolled agent behavior |

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
from massafetyguard import load_config
load_config("config.yaml")
```

## Creating Custom Risk Tests

```python
from massafetyguard.level3_safety.risk_tests.base import BaseRiskTest, TestCase

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
from massafetyguard.level3_safety.monitor_agents.base import BaseMonitorAgent, Alert

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
- **Risk Definitions**: `MAS风险层级说明.md`

## Project Structure

```
MASSafetyGuard/
├── src/
│   ├── level1_framework/      # MAS framework wrappers (AG2)
│   ├── level2_intermediary/   # Framework-agnostic interface
│   ├── level3_safety/
│   │   ├── judges/            # Unified Judge system
│   │   │   ├── base.py        # BaseJudge, JudgeResult
│   │   │   ├── llm_judge.py   # LLM-based judge
│   │   │   └── factory.py     # JudgeFactory
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

If you use MASSafetyGuard in your research, please cite:

```bibtex
@software{massafetyguard2026,
  title={MASSafetyGuard: A Safety Framework for Multi-Agent Systems},
  author={Your Name},
  year={2026},
  url={https://github.com/yourusername/MASSafetyGuard}
}
```

## Acknowledgments

- Based on OWASP Agentic AI Security Top 10
- Built with AG2/AutoGen framework support
- Powered by Claude Opus 4.5

## Contact

- Issues: https://github.com/yourusername/MASSafetyGuard/issues
- Email: your.email@example.com

---

**Status**: Beta - All 20 Risks Implemented
**Version**: 0.2.0
**Last Updated**: 2026-01-25
