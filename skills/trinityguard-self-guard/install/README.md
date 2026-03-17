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

Verify checks JSONL event chain, including:

- `hook_start`
- `preflight_result`
- `runtime_result`
- `output_guard_result`
- `final_decision`
- `hook_end`

## Log outputs

Primary log:
- `.codex/logs/self_guard_events.jsonl`

Optional summary JSON (only when passing `--out`):
- `.codex/logs/<custom>.json`

## Query logs

```bash
python skills/trinityguard-self-guard/shared/scripts/query_guard_events.py .codex/logs/self_guard_events.jsonl --event-type final_decision --limit 10
```

