---
name: trinityguard-self-guard
description: TrinityGuard 自监控安全总入口。用于让 code agent 在每轮任务中自动执行 preflight、runtime、output guard 与审计归并。凡涉及命令执行、文件修改、工具/网络调用、或解释型回答引用敏感上下文时都应触发本技能。
---

# TrinityGuard Self-Guard (Root Skill)

本技能是 `trinityguard-self-guard` 技能包的根入口，用于统一编排子技能：

1. `trinityguard-self-guard-orchestrator`
2. `trinityguard-preflight-selfcheck`
3. `trinityguard-runtime-selfmonitor`
4. `trinityguard-output-privacy-guard`

## 执行要求

1. 每轮对外输出前必须先执行一次自检流程。
2. 自检流程顺序：`preflight -> runtime -> output guard -> audit`。
3. 若结果为 `block`：禁止直出原始候选回复，必须拒答或脱敏。
4. 若结果为 `downgrade`：必须降级表达并声明不确定性。
5. 解释型回答也必须经过 output guard，不允许绕过。

## 推荐脚本

使用 `shared/scripts/self_guard_runtime_hook_template.py` 作为最小可用接入层：

```bash
python shared/scripts/self_guard_runtime_hook_template.py \
  shared/scripts/runtime_hook_input_example.json \
  --policy shared/references/runtime_policy.template.json \
  --out ./safety-guard-log/runtime_hook_audit.json
```
