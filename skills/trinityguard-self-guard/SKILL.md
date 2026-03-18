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

## 默认日志布局（turn_dir）
默认日志根目录为 `./.codex/logs/`。

每轮会生成独立目录：
- `./.codex/logs/turns/YYYYMMDD_HHMMSS_<turn_id>/input.json`
- `./.codex/logs/turns/YYYYMMDD_HHMMSS_<turn_id>/result.json`

全局轻量索引：
- `./.codex/logs/index.jsonl`

会话状态仍单独存储：
- `./.codex/logs/.self_guard_state/`

## 推荐脚本（默认 turn_dir）

```bash
python shared/scripts/self_guard_runtime_hook_template.py \
  shared/scripts/runtime_hook_input_example.json \
  --policy shared/references/runtime_policy.template.json \
  --policy-profile balanced
```

可选：额外输出兼容 summary JSON。

```bash
python shared/scripts/self_guard_runtime_hook_template.py \
  shared/scripts/runtime_hook_input_example.json \
  --out ./.codex/logs/runtime_hook_summary.json
```

## legacy 兼容模式
如需历史全量事件流 JSONL：

```bash
python shared/scripts/self_guard_runtime_hook_template.py \
  shared/scripts/runtime_hook_input_example.json \
  --log-layout legacy \
  --events-log ./.codex/logs/self_guard_events.jsonl
```

## 强制落日志协议（必须执行）
1. 不允许只做文本判定而不运行脚本；每轮必须实际运行 runtime hook。
2. 输入 JSON 必须包含 `project_path`（当前项目绝对路径），避免路径漂移。
3. 最终回复必须给出最小证据：
   - `self_guard_final_action`
   - `self_guard_trace_id`
   - `self_guard_events_log`（可填 index 或 legacy events 实际路径）
4. 如果脚本执行失败或不可用，必须明确声明“未完成安全自检”，并采用保守输出策略。
