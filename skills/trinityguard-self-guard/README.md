# TrinityGuard Self-Guard Skills

This package provides a production-oriented self-guard workflow for agent responses.

## Source of truth

- Authoritative implementation: `skills/trinityguard-self-guard`
- Mirror distribution target: `TrinitySafeSkills/trinityguard-self-guard` (read-only)

## Skill set

1. `using-trinityguard-self-guard`
2. `trinityguard-self-guard-orchestrator`
3. `trinityguard-preflight-selfcheck`
4. `trinityguard-runtime-selfmonitor`
5. `trinityguard-output-privacy-guard`

## Core behavior

- run guard checks before final user-facing output
- enforce block/downgrade/allow decisions with traceability
- expose source disclosure for single-source downgrade cases
- support both `turn_dir` and `legacy` log layouts

## Quick start

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target codex
python skills/trinityguard-self-guard/install/verify_install.py --target codex --policy-profile balanced
```

## Real A/B contrast (release gate)

```bash
python skills/trinityguard-self-guard/tests/run_ab_contrast.py   --policy-profile balanced   --runner-cmd "python skills/trinityguard-self-guard/tests/real_runner_example.py"
```

Default output: `.codex/logs/self_guard_tests/ab/`

## Policy matrix

```bash
python skills/trinityguard-self-guard/tests/run_policy_matrix.py   --runner-cmd "python skills/trinityguard-self-guard/tests/real_runner_example.py"
```

Default output: `.codex/logs/self_guard_tests/policy_matrix/`

## Metrics

```bash
python skills/trinityguard-self-guard/shared/scripts/summarize_guard_metrics.py   .codex/logs/index.jsonl
```

## Mirror sync

```bash
python skills/trinityguard-self-guard/install/sync_to_mirror.py
python skills/trinityguard-self-guard/install/sync_to_mirror.py --check-only
```
