# Install and Verify Guide (Codex)

## Prerequisites

1. Python 3.9+
2. local path contains `skills/trinityguard-self-guard/`

## Install

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target codex
```

## Verify

```bash
python skills/trinityguard-self-guard/install/verify_install.py --target codex --policy-profile balanced
```

Verification covers:

1. required file structure
2. UTF-8 asset gate
3. `turn_dir` output integrity
4. `legacy` compatibility checks
5. behavior assertions for block/downgrade and source disclosure

## Real A/B contrast

```bash
python skills/trinityguard-self-guard/tests/run_ab_contrast.py   --policy-profile balanced   --runner-cmd "python skills/trinityguard-self-guard/tests/real_runner_example.py"
```

Default output: `.codex/logs/self_guard_tests/ab/`

## Policy matrix

```bash
python skills/trinityguard-self-guard/tests/run_policy_matrix.py   --runner-cmd "python skills/trinityguard-self-guard/tests/real_runner_example.py"
```

Default output: `.codex/logs/self_guard_tests/policy_matrix/`

## Mirror sync

```bash
python skills/trinityguard-self-guard/install/sync_to_mirror.py
python skills/trinityguard-self-guard/install/sync_to_mirror.py --check-only
```

## Fallback for non-writable log directory

```bash
python skills/trinityguard-self-guard/shared/scripts/self_guard_runtime_hook_template.py   <input_json>   --turns-dir .codex/logs/fallback/turns   --index-log .codex/logs/fallback/index.jsonl   --state-dir .codex/logs/fallback/state   --events-log .codex/logs/fallback/events.jsonl
```
