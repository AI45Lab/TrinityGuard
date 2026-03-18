# Local Installation (Codex)

## Prerequisites

1. Python 3.9+ available as `python`.
2. Local repo contains `skills/trinityguard-self-guard/`.

## Install

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target codex
```

Default mode is `copy`, and verify runs automatically.

## Verify

```bash
python skills/trinityguard-self-guard/install/verify_install.py --target codex --policy-profile balanced
```

Verify now includes:
1. `turn_dir` 主流程校验：`turns/*/input.json + result.json + index.jsonl`
2. `legacy` 兼容校验：`self_guard_events_legacy_verify.jsonl` 事件链完整

## Log outputs (default: turn_dir)

Primary outputs:
- `.codex/logs/turns/<timestamp_turn_id>/input.json`
- `.codex/logs/turns/<timestamp_turn_id>/result.json`
- `.codex/logs/index.jsonl`
- `.codex/logs/.self_guard_state/`

Optional compatibility summary (`--out`):
- `.codex/logs/<custom>.json`

## Legacy events mode

If you need full per-event JSONL stream:

```bash
python skills/trinityguard-self-guard/shared/scripts/self_guard_runtime_hook_template.py \
  <input_json> \
  --log-layout legacy \
  --events-log .codex/logs/self_guard_events.jsonl
```
