---
name: trinityguard-output-privacy-guard
description: 在输出前执行隐私与敏感泄露守门。只要上下文含敏感信息，即使用户仅要求解释/总结，也必须触发本技能。对未多源校验的工具结论默认降级表达。
---

# TrinityGuard Output Privacy Guard

## 作用

作为最终输出前的强制闸门，防止“解释性回答泄露”。

## 输入

1. 待输出文本
2. sensitivity_state
3. trust_annotations
4. 是否完成多源校验

## 输出

1. `leakage_detected`
2. `redaction_applied`
3. `confidence_level`
4. `safe_response`
5. `output_decision`（allow|downgrade|block）

## 必检项

1. 凭证、密钥、隐私字段
2. 敏感上下文的复述与重构泄露
3. 单来源工具结论是否被过度确定化表达
4. 多源校验状态

## 处置规则

1. 命中敏感泄露：脱敏或 `block`。
2. 未完成多源校验：`downgrade`，输出不确定性提示。
3. 多源一致且无敏感泄露：可 `allow`。

## 输出模板

```markdown
## Output Guard Result
- output_decision: <allow|downgrade|block>
- leakage_detected: <true|false>
- redaction_applied: <true|false>
- confidence_level: <low|medium|high>
- safe_response: <final text to user>
```

## 推荐脚本调用

1. 若 `trust_annotations` 中存在单工具来源结论，先调用 `../shared/scripts/verify_multi_source_template.py`。
2. 当结论未达 `multi_source_verified` 时，`output_decision` 默认不应为 `allow`。
