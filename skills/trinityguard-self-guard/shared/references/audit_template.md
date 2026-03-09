# 审计模板

使用该模板产出单轮任务审计记录，字段需与 `audit_record.schema.json` 对齐。

## 必填字段

1. `session_id`
2. `trigger_reasons`
3. `preflight`
4. `runtime`
5. `output_guard`
6. `final_action`

## 模板

```json
{
  "session_id": "session-001",
  "trigger_reasons": ["sensitive_context", "tool_usage"],
  "preflight": {
    "risk_summary": ["prompt_injection_risk"],
    "sensitivity_state": "sensitive",
    "allowed_actions": ["read_only"],
    "blocked_actions": ["print_raw_secret"],
    "verification_requirements": ["need_multi_source_verification"],
    "preflight_decision": "downgrade"
  },
  "runtime": {
    "runtime_events": [{"type": "tool_call", "tool": "search"}],
    "alerts": [{"severity": "warning", "message": "single-source evidence"}],
    "suggested_actions": ["collect_second_source"],
    "trust_annotations": [
      {
        "source_id": "tool-1",
        "source_type": "tool_single_source",
        "confidence": "low",
        "reason": "only one tool source"
      }
    ],
    "runtime_decision": "downgrade"
  },
  "output_guard": {
    "leakage_detected": true,
    "redaction_applied": true,
    "confidence_level": "low",
    "safe_response": "已完成脱敏摘要。",
    "output_decision": "downgrade"
  },
  "final_action": "downgrade",
  "residual_risks": ["tool-derived conclusion not fully verified"],
  "audit_notes": ["explanatory request still passed output guard"]
}
```

## 校验规则

1. `runtime_decision = stop` 时，`final_action` 不能为 `allow`。
2. `leakage_detected = true` 时，`safe_response` 必须是脱敏内容。
3. 仅单工具来源时，`confidence_level` 不应为 `high`。
