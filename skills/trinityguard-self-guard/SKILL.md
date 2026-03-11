---
name: trinityguard-self-guard
description: TrinityGuard 自监控安全总入口。用于让 code agent 在每轮任务中执行 preflight、runtime、output guard，并输出可追踪审计事件。
---

# TrinityGuard Self-Guard (Root Skill)

本技能是 `trinityguard-self-guard` 技能包根入口，统一编排：
1. `trinityguard-self-guard-orchestrator`
2. `trinityguard-preflight-selfcheck`
3. `trinityguard-runtime-selfmonitor`
4. `trinityguard-output-privacy-guard`

## 执行要求
1. 每轮对外输出前必须执行一次自检流程。
2. 流程顺序：`preflight -> runtime -> output guard -> final decision`。
3. 若结果为 `block`：禁止输出原始候选回复，必须拒答或脱敏。
4. 若结果为 `downgrade`：必须降级表达并声明不确定性。
5. 解释型回答也必须经过 output guard。

## 推荐脚本

```bash
python shared/scripts/self_guard_runtime_hook_template.py \
  shared/scripts/runtime_hook_input_example.json \
  --policy shared/references/runtime_policy.template.json \
  --events-log ./safety-guard-log/events/self_guard_events.jsonl
```

可选：输出单轮摘要 JSON。

```bash
python shared/scripts/self_guard_runtime_hook_template.py \
  shared/scripts/runtime_hook_input_example.json \
  --out ./safety-guard-log/runtime_hook_summary.json
```
