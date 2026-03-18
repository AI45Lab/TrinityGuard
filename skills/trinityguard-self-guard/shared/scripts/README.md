# Shared Scripts

Reusable scripts for runtime guard execution, validation, and reporting.

## Runtime scripts

1. `self_guard_runtime_hook_template.py`
2. `query_guard_events.py`
3. `summarize_guard_metrics.py`

## Quality gates

1. `validate_utf8_assets.py`
2. `validate_eval_assets_consistency.py`

## Benchmark helpers

1. `run_local_benchmark_template.py`
2. `aggregate_benchmark_template.py`
3. `check_benchmark_thresholds.py`

## Common commands

```bash
python skills/trinityguard-self-guard/shared/scripts/self_guard_runtime_hook_template.py   skills/trinityguard-self-guard/shared/scripts/runtime_hook_input_example.json   --policy skills/trinityguard-self-guard/shared/references/runtime_policy.balanced.json
```

```bash
python skills/trinityguard-self-guard/shared/scripts/summarize_guard_metrics.py   .codex/logs/index.jsonl
```
