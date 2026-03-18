# TrinityGuard Self Guard Skills

独立 skills 集合，不依赖修改 TrinityGuard 主体源码。

## Skills
1. `trinityguard-self-guard-orchestrator`
2. `trinityguard-preflight-selfcheck`
3. `trinityguard-runtime-selfmonitor`
4. `trinityguard-output-privacy-guard`

## Design principles
1. 解释型回答与执行动作同等纳入安全监测。
2. 工具来源信息默认降级，需多源校验后再提升可信度。
3. 先边界、再执行、后输出，全程可审计。

## Quick install

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target codex
```

## Verification

```bash
python skills/trinityguard-self-guard/install/verify_install.py --target codex --policy-profile balanced
```

## Primary log contract (default: turn_dir)

默认输出按“每轮目录”组织：
- `.codex/logs/turns/<timestamp_turn_id>/input.json`
- `.codex/logs/turns/<timestamp_turn_id>/result.json`
- `.codex/logs/index.jsonl`（轻量全局索引）

会话状态：
- `.codex/logs/.self_guard_state/`

## Legacy compatibility

如需历史全量事件流，使用：

```bash
python skills/trinityguard-self-guard/shared/scripts/self_guard_runtime_hook_template.py \
  <input_json> \
  --log-layout legacy \
  --events-log .codex/logs/self_guard_events.jsonl
```
