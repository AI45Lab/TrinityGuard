# Local Installation

## One-line install (Codex)

```powershell
powershell -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\install_skill_local.ps1 -Target codex
```

## One-line install (Claude Code)

```powershell
powershell -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\install_skill_local.ps1 -Target claude
```

## One-line install (both)

```powershell
powershell -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\install_skill_local.ps1 -Target both
```

默认会自动执行 verify（AutoVerify）。如需跳过：

```powershell
powershell -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\install_skill_local.ps1 -Target codex -SkipVerify
```

## Verify install

```powershell
powershell -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\verify_install.ps1 -Target codex
```

```powershell
powershell -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\verify_install.ps1 -Target claude
```

## Log directory

Runtime self-guard logs and audit outputs are written under:
- `safety-guard-log/`

No self-guard artifacts are written to `tmp/` by default.
