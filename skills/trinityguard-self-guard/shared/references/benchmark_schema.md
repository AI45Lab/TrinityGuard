# Benchmark Schema 说明

该文件对应 `benchmark.schema.json`，用于规范 self-guard skills 的聚合评测输出。

## 目标

1. 统一 with-skill / without-skill 对比结构
2. 支持按 eval 维度回溯断言结果
3. 支持后续自动可视化与回归检查
4. 纳入误报/漏报指标（FPR/FNR）用于安全质量评估

## 指标说明

1. `pass_rate`: 断言通过率
2. `false_positive_rate`: 误报率（本应放行却被拦截/降级）
3. `false_negative_rate`: 漏报率（本应拦截却被放行）
4. `time_seconds`: 时间开销
5. `tokens`: token 开销

## 场景分层

1. 每个 eval 可通过 `tags` 标注为 `benign` 或 `adversarial`。
2. 聚合结果在 `summary.segmented` 中输出分层统计。
3. 推荐重点关注：
- benign 的 `false_positive_rate`
- adversarial 的 `false_negative_rate`

## 使用建议

1. 聚合脚本输出 JSON 后先做 schema 校验
2. 校验通过再用于生成 markdown 或 HTML 报告
3. 关键字段缺失时直接标记 benchmark 失败
