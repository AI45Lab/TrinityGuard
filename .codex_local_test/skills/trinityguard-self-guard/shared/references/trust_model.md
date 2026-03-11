# 信息可信度模型

默认层级（低 -> 高）：

1. `tool_single_source`
2. `tool_multi_source_unverified`
3. `internal_unverified`
4. `internal_verified`
5. `multi_source_verified`

规则：

1. 单工具来源信息不得直接升级为高可信结论。
2. 工具多源一致也不高于 `internal_verified`，除非有独立内部证据。
3. 至少两类独立来源一致，且不存在冲突时，才能提升到 `multi_source_verified`。
4. 无法校验或出现冲突时必须显式表达不确定性。
5. 一旦上下文进入 `sensitive/highly_sensitive`，输出必须经过 output guard。
