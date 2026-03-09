# TrinityGuard Self Guard Skills

这是独立 skills 集合，不依赖修改 TrinityGuard 源码。

## 技能清单

1. `trinityguard-self-guard-orchestrator`
2. `trinityguard-preflight-selfcheck`
3. `trinityguard-runtime-selfmonitor`
4. `trinityguard-output-privacy-guard`

## 设计原则

1. 解释性回答与执行动作同等纳入安全监测。
2. 工具来源信息默认降级，需多源校验后再提升可信度。
3. 先边界、再执行、后输出、可审计。

## 快速安装（Codex / Claude Code）

1. Codex：
```powershell
powershell -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\install_skill_local.ps1 -Target codex
```

2. Claude Code：
```powershell
powershell -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\install_skill_local.ps1 -Target claude
```

3. 安装验收：
```powershell
powershell -ExecutionPolicy Bypass -File .\skills\trinityguard-self-guard\install\verify_install.ps1 -Target codex
```
