# TrinityGuard Usage Guide

This guide covers installation, the `Safety_MAS` API, real API smoke runs, AG2
demo execution, and runtime protection.

## 1. Install

TrinityGuard requires Python 3.10+.

```bash
cd /home/kai/Projects/TrinityGuard-Dev
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If you only want to inspect the package surface:

```bash
PYTHONPATH=src python - <<'PY'
import trinityguard
print(trinityguard.__version__)
print(trinityguard.__all__)
PY
```

## 2. Configure Provider Credentials

Real API examples need provider credentials, network access, and quota.

```bash
cp .env.example .env
# Fill in OpenAI / Anthropic or compatible provider settings.
```

Do not commit `.env` or raw run outputs.

## 3. Wrap A MAS With `Safety_MAS`

The deterministic in-process MAS is useful for checking the public API before
connecting a real framework adapter.

```python
from trinityguard import Safety_MAS
from trinityguard.level3_safety.fixtures.local_mas import LocalThreeAgentMAS

mas = LocalThreeAgentMAS()
safety = Safety_MAS(mas)

result = safety.run_task("Check this multi-agent workflow")
print(result.success)
print(result.output)

report = safety.get_comprehensive_report()
print(report["summary"])
```

`Safety_MAS.run_task(...)` observes and reports by default. Runtime protection is
only active after you explicitly enable it.

## 4. Run Real API Smoke

`examples/minset_real_api.py` calls a configured target model and judge model,
then writes redacted artifacts under the selected output directory.

```bash
PYTHONPATH=src python examples/minset_real_api.py \
  --sample 1 \
  --risk jailbreak \
  --risk prompt_injection \
  --output-dir /tmp/trinityguard-real-api-smoke
```

Useful output files include redacted manifests, case results, judge verdicts,
and aggregate metrics. Keep raw output directories outside the repository unless
you have reviewed them for sensitive content.

## 5. Run The AG2 Real API Demo

```bash
PYTHONPATH=src python demos/ag2_real_api/run_demo.py \
  --scenarios precheck,runtime \
  --max-round 2 \
  --output-root /tmp/trinityguard-ag2-real-api-recheck
```

The demo records a redacted run manifest, provider settings summary,
predeployment rows, runtime events, and a runtime report.

If a provider content filter blocks a target request, TrinityGuard records that
as provider-blocked safe/refusal evidence. That is distinct from a judge-backed
verdict.

## 6. Enable Runtime Protection

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

For a CLI example that writes runtime event/report artifacts:

```bash
python examples/runtime_protection_mvp.py \
  --output /tmp/trinityguard-runtime/events.jsonl \
  --report-output /tmp/trinityguard-runtime/runtime-report.json

python examples/verify_runtime_report_artifact.py \
  /tmp/trinityguard-runtime/runtime-report.json
```

## 7. Architecture Links

- [Public API Contract](../contracts/public-api-v1.md)
- [Runtime Adapter Contract](../contracts/runtime-adapter-contract-v1.md)
- [Source Architecture Reference](../reference/src_architecture.md)
- [Runtime Monitoring Reference](../reference/runtime_monitoring.md)
- [Risk Taxonomy](../reference/risk_taxonomy.md)

## 8. Local Validation

```bash
PYTHONPATH=src pytest -q tests/unit tests/integration
ruff check <touched-python-files>
git diff --check
```
