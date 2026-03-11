# TrinityGuard Self-Guard 安装与测试

## 1. 跨平台安装

前置条件：
1. Python 3.9+
2. 当前目录为仓库根目录

安装命令：

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target codex
```

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target claude
```

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target both
```

## 2. 验收命令

```bash
python skills/trinityguard-self-guard/install/verify_install.py --target codex --policy-profile balanced
```

```bash
python skills/trinityguard-self-guard/install/verify_install.py --target claude --policy-profile balanced
```

验收通过标准：
1. JSONL 存在且非空
2. 事件链路完整（`hook_start` 到 `hook_end`）
3. 存在 `final_decision` 且包含 `final_action/policy_profile/reason_codes/matched_rules/retention`

## 3. 手工排查命令

```bash
python skills/trinityguard-self-guard/shared/scripts/query_guard_events.py safety-guard-log/events/self_guard_events.jsonl --event-type final_decision --limit 20
```

## 4. 回归剧本

1. 显式泄露请求，期望 `block`
2. 隐式泄露请求，期望 `downgrade` 或 `block`
3. 单源高置信结论，期望 `downgrade`
4. 正常低风险请求，期望 `allow`

## 5. 一致性检查

```bash
python skills/trinityguard-self-guard/shared/scripts/validate_eval_assets_consistency.py skills/trinityguard-self-guard --strict
```
