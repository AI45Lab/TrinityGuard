# Local Installation (Linux/macOS/Windows)

## Prerequisites

1. Python 3.9+ available as `python`.
2. Local repo contains `skills/trinityguard-self-guard/`.

## Install

### Codex

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target codex
```

### Claude Code

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target claude
```

### Both

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target both
```

Default mode is `copy`, and verify runs automatically.

## Verify

```bash
python skills/trinityguard-self-guard/install/verify_install.py --target codex --policy-profile balanced
```

```bash
python skills/trinityguard-self-guard/install/verify_install.py --target claude --policy-profile balanced
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
- `safety-guard-log/events/self_guard_events.jsonl`

Optional summary JSON (only when passing `--out`):
- `safety-guard-log/<custom>.json`

## Query logs

```bash
python skills/trinityguard-self-guard/shared/scripts/query_guard_events.py safety-guard-log/events/self_guard_events.jsonl --event-type final_decision --limit 10
```
