# MASSafetyGuard

**Multi-Agent System Safety Framework** for pre-deployment testing and runtime monitoring.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

MASSafetyGuard provides comprehensive safety testing and monitoring for multi-agent systems (MAS). It helps identify and mitigate 20 types of security risks across three levels:

- **L1: Single-Agent Risks** (8 types) - Jailbreak, Prompt Injection, Sensitive Data Disclosure, etc.
- **L2: Inter-Agent Communication Risks** (6 types) - Message Tampering, Malicious Propagation, etc.
- **L3: System-Level Risks** (6 types) - Cascading Failures, Group Hallucination, etc.

### Key Features

✅ **Framework-Agnostic Design** - Currently supports AG2/AutoGen, extensible to LangGraph and others
✅ **Pre-Deployment Testing** - Identify vulnerabilities before deployment
✅ **Runtime Monitoring** - Real-time risk detection during execution
✅ **Extensible Plugin System** - Easy to add new risk tests and monitors
✅ **LLM-Powered Analysis** - Intelligent test generation and risk detection

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

MASSafetyGuard uses a 3-layer architecture:

```
┌─────────────────────────────────────────┐
│   Level 3: Safety_MAS Layer             │
│   - Risk Test Library (20 types)        │
│   - Monitor Agent Repository            │
│   - Safety_MAS orchestration            │
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
│   - Message hook system                 │
│   - Agent access                        │
└─────────────────────────────────────────┘
```

## Implemented Risks

### Currently Available

| Risk | Level | Test | Monitor | Status |
|------|-------|------|---------|--------|
| **Jailbreak** | L1 | ✅ | ✅ | Complete |
| **Message Tampering** | L2 | ✅ | ✅ | Complete |

### Coming Soon

- Cascading Failures (L3)
- Prompt Injection (L1)
- Malicious Propagation (L2)
- Group Hallucination (L3)
- And 15 more...

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
- **Risk Definitions**: `MAS风险层级说明.md`

## Project Structure

```
MASSafetyGuard/
├── src/
│   ├── level1_framework/      # MAS framework wrappers
│   ├── level2_intermediary/   # Framework-agnostic interface
│   ├── level3_safety/         # Safety tests and monitors
│   └── utils/                 # Configuration, logging, LLM client
├── tests/                     # Unit and integration tests
├── examples/                  # Usage examples
├── docs/                      # Documentation
└── config/                    # Configuration files
```

## Development

### Running Tests

```bash
pytest tests/
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

**Status**: Alpha - Active Development
**Version**: 0.1.0
**Last Updated**: 2026-01-23
