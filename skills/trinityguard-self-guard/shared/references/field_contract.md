# 字段契约（Field Contract）

本文件定义 TrinityGuard self-guard 的核心字段契约。

## 1. 事件日志主契约（推荐）
主输出是 JSONL，每行一个事件，参考：`guard_event.schema.json`。

每条事件至少包含：
1. `ts`
2. `trace_id`
3. `session_id`
4. `turn_id`
5. `policy_profile`
6. `event_type`
7. `risk_level`
8. `decision`
9. `reason_codes`
10. `matched_rules`

`event_type` 取值：
1. `hook_start`
2. `preflight_result`
3. `runtime_result`
4. `output_guard_result`
5. `final_decision`
6. `hook_end`
7. `hook_error`

## 2. final_decision 事件扩展字段
1. `final_action`: `allow|downgrade|block`
2. `retention`: 分级留存摘要
3. `residual_risks`: `string[]`
4. `audit_notes`: `string[]`

## 3. output_guard 摘要字段
1. `output_guard.safe_response`: 面向用户的最终安全输出
2. `output_guard.source_disclosure`: 单源降级时的来源附录文本
3. `output_guard.source_items`: `[{source_id, source_type, confidence, reason}]`

## 4. 关键一致性规则
1. 若 `runtime_result.decision = stop`，则最终 `final_action` 不能为 `allow`。
2. 若检测到泄露且为高敏会话，最终动作应为 `block` 或更严格策略。
3. 对单一工具来源结论，至少应触发降级或不确定性提示。
4. 若 `output_decision=downgrade` 且原因码包含 `OG_SINGLE_SOURCE_DOWNGRADE`，必须输出 `source_disclosure` 且 `source_items` 至少一条（无来源时需明确“来源信息缺失”）。

## 5. 兼容说明
历史单轮审计 JSON 仍可通过 `--out` 生成摘要；完整契约以 JSONL 事件为准。
