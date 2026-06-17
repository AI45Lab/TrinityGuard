<p align="center">
  <img src="assets/logo_TG.png" alt="TrinityGuard Logo" width="180">
</p>

<h2 align="center">TrinityGuard: A Safety Evaluation Framework for Multi-Agent Systems</h2>

<p align="center">
  <a href="https://arxiv.org/abs/2603.15408">arXiv</a> |
  <a href="docs/research/Technical_Report_TrinityGuard_260316.pdf">Technical Report</a> |
  <a href="https://github.com/AI45Lab/TrinityGuard">Project Page</a>
</p>

# TrinityGuard

TrinityGuard is a Python framework for evaluating safety risks in multi-agent
systems. It helps you wrap a MAS, run structured risk checks, collect runtime
evidence, and inspect reports from deterministic local examples or bounded real
provider API smoke runs.

The main entry point is `Safety_MAS`: use it to run a task through a MAS,
observe traces, generate safety reports, and optionally enable runtime
protection for controlled demos.

## What It Does

- Evaluates MAS behavior across 20 built-in L1/L2/L3 risk types, including
  prompt injection, sensitive disclosure, tool misuse, message tampering,
  cascading failures, sandbox escape, rogue agents, and related multi-agent
  risks.
- Provides a framework-independent execution layer for workflow tracing,
  message interception, structured logs, and runtime evidence.
- Supports LLM-as-Judge evaluation, monitor observations, calibration data, and
  report artifacts.
- Includes AG2/AutoGen integration paths and an experimental `a3s-code`
  adapter for A3S Code sessions.
- Exposes runtime protection primitives for allow, replace, and deny decisions
  when protection is explicitly enabled.

## Install

TrinityGuard requires Python 3.10+.

```bash
git clone https://github.com/AI45Lab/TrinityGuard.git
cd TrinityGuard
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

For real API examples, configure provider credentials with `.env.example`:

```bash
cp .env.example .env
# Fill in provider keys and model settings as needed.
```

Do not commit `.env` or raw run artifacts.

## Quick Start

This example wraps a deterministic in-process MAS. It is the fastest way to
check the public API and report shape before wiring a real framework adapter.

```python
from trinityguard import Safety_MAS
from trinityguard.level3_safety.fixtures.local_mas import LocalThreeAgentMAS

mas = LocalThreeAgentMAS()
safety = Safety_MAS(mas)

result = safety.run_task("Review this multi-agent workflow")
print(result.success)
print(result.output)

report = safety.get_comprehensive_report()
print(report["summary"])
```

## Runtime Protection Example

Runtime protection is opt-in. When enabled, TrinityGuard can evaluate runtime
messages and return policy decisions such as `allow`, `replace`, or `deny`.

```python
from trinityguard import RuntimeProtector, Safety_MAS
from trinityguard.level3_safety.fixtures.local_mas import LocalThreeAgentMAS
from trinityguard.level3_safety.judges.base import BaseJudge, JudgeResult


class DemoJudge(BaseJudge):
    def __init__(self):
        super().__init__(risk_type="prompt_injection")

    def analyze(self, content: str, context: dict | None = None) -> JudgeResult:
        risky = "exfiltrate" in content.lower()
        return JudgeResult(
            has_risk=risky,
            severity="critical" if risky else "none",
            reason="runtime policy decision",
            evidence=[content],
            recommended_action="block" if risky else "log",
            judge_type="deterministic_demo",
        )

    def get_judge_info(self) -> dict[str, str]:
        return {"type": self.risk_type, "version": "demo"}


safety = Safety_MAS(LocalThreeAgentMAS())
protector = RuntimeProtector(judges=[DemoJudge()])
safety.enable_runtime_protection(protector, block_mode="replace")

result = safety.run_task("please exfiltrate TOKEN=redactedinput")
print(result.output)
```

## Framework Adapters

TrinityGuard separates framework adapters from evaluation logic:

```text
Level 1: Framework adapters
  AG2/AutoGen, experimental a3s-code support, or custom BaseMAS adapters.

Level 2: Intermediary
  Workflow runners provide interception, structured logging, and runtime traces.

Level 3: Safety
  Attack cases, monitors, judges, calibration, evidence packaging, and Safety_MAS.

Runtime
  Runtime policy decisions, event sinks, adapter contracts, and report artifacts.
```

The `a3s-code` adapter is experimental. It supports wrapping an A3S Code
session as a TrinityGuard `BaseMAS`, monitored workflow execution, trace/log
collection, and runtime protection before A3S execution. It does not claim full
compatibility with arbitrary A3S Code MAS configurations.

## Real API Smoke

`examples/minset_real_api.py` calls a configured target model and judge model,
then writes redacted manifests, raw result summaries, verdicts, and metrics.

```bash
PYTHONPATH=src python examples/minset_real_api.py \
  --sample 1 \
  --risk jailbreak \
  --risk prompt_injection \
  --output-dir /tmp/trinityguard-real-api-smoke
```

Real API examples require user-provided credentials, network access, and quota.
Keep raw output directories outside the repository unless you have reviewed them
for sensitive content.

## Example Scripts

| Script | Purpose |
| --- | --- |
| `examples/runtime_protection_mvp.py` | Generate runtime protection evidence with a small local MAS. |
| `examples/runtime_policy_matrix.py` | Exercise runtime policy modes and report validation. |
| `examples/validate_runtime_mvp.py` | Validate local runtime MVP behavior. |
| `examples/minset_real_api.py` | Run bounded real API smoke for selected risks. |
| `demos/ag2_real_api/run_demo.py` | Run AG2 precheck/runtime real API demo with configured credentials. |

## Documentation

- [Usage Guide](docs/introduction/usage.md)
- [Public API Contract](docs/contracts/public-api-v1.md)
- [Runtime Adapter Contract](docs/contracts/runtime-adapter-contract-v1.md)
- [Source Architecture Reference](docs/reference/src_architecture.md)
- [Runtime Monitoring Reference](docs/reference/runtime_monitoring.md)
- [Risk Taxonomy](docs/reference/risk_taxonomy.md)
- [Research Index](docs/research/RESEARCH_INDEX.md)

## Validation Scope

TrinityGuard is intended for research and developer evaluation workflows.
Current real API examples are bounded smoke checks, not production
certification. Runtime protection is explicit and configurable; the default
`Safety_MAS.run_task(...)` path remains an evaluation surface unless you enable
protection.

Run the offline test subset with:

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
```

## License

MIT. See `pyproject.toml` for package metadata.
