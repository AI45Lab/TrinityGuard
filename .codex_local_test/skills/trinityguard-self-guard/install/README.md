# Local Installation (Linux/macOS/Windows)

## Prerequisites

1. Python 3.9+ available as `python` (or `py -3` on Windows).
2. Local repo contains `skills/trinityguard-self-guard/`.

## Cross-platform one-line install

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

Default mode is `copy` and verify runs automatically.

## Common options

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target codex --mode copy --skip-verify
```

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target codex --mode link
```

## Verify install

```bash
python skills/trinityguard-self-guard/install/verify_install.py --target codex --policy-profile balanced
```

```bash
python skills/trinityguard-self-guard/install/verify_install.py --target claude --policy-profile balanced
```

## Default policy profile

- Recommended default: `balanced`
- You can override with `--policy-file` in verify/runtime calls.

## Expected verify signals

Audit must include:

- `final_action`
- `policy_profile`
- `decision_reason_codes`
- `matched_rules`
- `output_guard.redaction_summary`

## Windows compatibility (legacy commands)

These still work and now call the Python implementation internally:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\install_skill_local.ps1 -Target codex
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\verify_install.ps1 -Target codex
```

## Log directory

- Runtime self-guard logs: `safety-guard-log/`
- No default writes to `tmp/`
