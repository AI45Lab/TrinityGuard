# 字段契约（Field Contract）

本文件定义四个 self-guard skills 的统一字段，供 orchestrator 聚合。

## 1. Preflight 输出字段

1. `risk_summary`: `string[]`
2. `sensitivity_state`: `normal|sensitive|highly_sensitive`
3. `allowed_actions`: `string[]`
4. `blocked_actions`: `string[]`
5. `verification_requirements`: `string[]`
6. `preflight_decision`: `allow|downgrade|block`

## 2. Runtime 输出字段

1. `runtime_events`: `object[]`
2. `alerts`: `object[]`
3. `suggested_actions`: `string[]`
4. `trust_annotations`: `object[]`
5. `runtime_decision`: `continue|downgrade|stop`

`trust_annotations[]` 建议字段：
1. `source_id`: `string`
2. `source_type`: `internal_verified|internal_unverified|tool_single_source|tool_multi_source_unverified|multi_source_verified`
3. `confidence`: `low|medium|high`
4. `reason`: `string`

## 3. Output Guard 输出字段

1. `leakage_detected`: `boolean`
2. `redaction_applied`: `boolean`
3. `confidence_level`: `low|medium|high`
4. `safe_response`: `string`
5. `output_decision`: `allow|downgrade|block`

## 4. Orchestrator 聚合字段

1. `session_id`: `string`
2. `trigger_reasons`: `string[]`
3. `preflight`: `object`
4. `runtime`: `object`
5. `output_guard`: `object`
6. `final_action`: `allow|downgrade|block`
7. `residual_risks`: `string[]`
8. `audit_notes`: `string[]`

## 5. 关键一致性规则

1. 若 `sensitivity_state` 为 `sensitive/highly_sensitive`，则 `output_guard` 必须出现。
2. 若 `trust_annotations` 仅有单工具来源，不得输出高置信结论。
3. 若 `output_guard.leakage_detected = true`，`safe_response` 不得包含原始敏感值。
4. 若 `runtime_decision = stop`，`final_action` 不能为 `allow`。
