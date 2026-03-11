---
name: trinityguard-self-guard-orchestrator
description: 在 code agent 任务中统一编排安全自检。涉及命令执行、文件修改、工具/网络调用，或敏感上下文解释时都应触发。
---

# TrinityGuard Self Guard Orchestrator

## 作用
负责整轮任务级安全编排，不直接实现底层检测算法。职责：
1. 何时触发子技能
2. 何时阻断或降级
3. 何时允许输出

## 子技能依赖
1. `trinityguard-preflight-selfcheck`
2. `trinityguard-runtime-selfmonitor`
3. `trinityguard-output-privacy-guard`

## 触发判定
满足任一即触发：
1. 命令执行、脚本执行、代码改写、批量文件操作
2. 读取可能包含敏感信息的数据
3. 外部工具/网络数据作为结论依据
4. 解释请求但上下文含敏感信息

## 标准流程
1. preflight：输出 `risk_summary`、`sensitivity_state`、`allowed_actions`
2. runtime：记录事件、告警与可信度标注
3. output guard：检测泄露并执行脱敏/拒答
4. final decision：给出 `allow|downgrade|block`

## 编排规则
1. preflight 判定高敏且请求直出原文，默认拒绝。
2. runtime 出现 critical 告警，停止执行并进入安全输出。
3. 仅单一工具来源时必须降级表达。
4. 多源校验通过后才可升级为高可信结论。

## 输出契约
1. 主日志采用 JSONL 事件流，遵循 `../shared/references/guard_event.schema.json`。
2. 字段规范遵循 `../shared/references/field_contract.md`。
3. 如需历史兼容，可用 `--out` 产出单轮摘要 JSON（非主契约）。

## 运行时接入
1. 使用 `../shared/scripts/self_guard_runtime_hook_template.py` 作为最小接入层。
2. 每轮输入任务 JSON，写入事件日志与会话状态（`sensitivity_state` 持久化）。
3. 将该脚本挂到响应前钩子，确保解释型回答也经过 output guard。
