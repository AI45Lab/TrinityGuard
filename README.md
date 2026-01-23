# MASSafetyGuard

Multi-Agent System Safety Framework for pre-deployment testing and runtime monitoring.

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from massafetyguard import Safety_MAS
from massafetyguard.level1_framework import AG2MAS

# Create your MAS
mas = AG2MAS(config="your_config.yaml")

# Wrap with safety
safety_mas = Safety_MAS(mas=mas)

# Run pre-deployment tests
results = safety_mas.run_auto_safety_tests()

# Start runtime monitoring
safety_mas.start_runtime_monitoring(mode="auto_llm")

# Execute task with monitoring
result = safety_mas.run_task("Your task here")
```

## Documentation

See `docs/plans/2026-01-23-mas-safety-framework-design.md` for full design documentation.

## License

MIT
