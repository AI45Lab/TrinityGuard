---
name: trinityguard-self-guard-orchestrator
description: 在 code agent 任务中统一编排安全自检。凡涉及命令执行、文件修改、外部工具调用，或上下文含敏感信息（即便用户仅要求解释/总结），都要触发本技能，按 preflight -> runtime -> output-privacy-guard -> audit 流程执行。
---

# TrinityGuard Self Guard Orchestrator

## 作用

负责“整轮任务级”安全编排，不直接做底层检测算法。它的职责是决定：

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
2. 读取配置、日志、数据库导出等可能含敏感信息的数据
3. 外部工具/网络数据作为结论依据
4. 用户只要求解释，但解释内容来自敏感上下文

## 标准流程

1. 调用 preflight：生成 `risk_summary`、`sensitivity_state`、`allowed_actions`。
2. 进入 runtime：记录关键事件、告警和可信度标注。
3. 每次对外输出前调用 output guard：检测泄露并执行脱敏/拒答。
4. 输出审计摘要：触发点、处置动作、残余风险。

## 编排决策规则

1. 若 preflight 判定 `highly_sensitive` 且请求包含“直接输出原文”，默认拒绝直出。
2. 若 runtime 出现 `critical` 告警，停止继续执行并转入安全输出。
3. 若结论仅来自 `tool_single_source`，输出必须降级表达，不给确定性定论。
4. 仅当多源校验通过时，才可升级为“高可信”结论。

## 审计输出模板

```markdown
## Self-Guard Audit Summary
- sensitivity_state: <normal|sensitive|highly_sensitive>
- risk_summary: <...>
- key_events:
  - <event>
- alerts:
  - <severity>: <message>
- output_guard:
  - leakage_detected: <true|false>
  - redaction_applied: <true|false>
- confidence:
  - level: <low|medium|high>
  - basis: <internal_verified/tool_single_source/multi_source_verified>
- final_action: <allow|downgrade|block>
```

## 字段协议与归并

1. 输出字段必须遵循 `../shared/references/field_contract.md`。
2. preflight/runtime/output_guard 三段结果建议通过 `../shared/scripts/normalize_audit_record_template.py` 归并为统一审计记录。
3. 归并结果应满足 `../shared/references/audit_record.schema.json`。

## 运行时接入模板

1. 建议使用 `../shared/scripts/self_guard_runtime_hook_template.py` 作为最小接入层。
2. 每轮输入任务 JSON，输出标准 audit record，并写入会话状态（`sensitivity_state` 持久化）。
3. 将该脚本挂到 agent 的响应前钩子，确保解释型回答也经过 output guard。
