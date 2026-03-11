# Evals Guide: trinityguard-self-guard-orchestrator

本目录用于 skill-creator 评测输入。

## 文件说明

1. evals.json
- 测试提示词与预期结果主文件。

2. eval_metadata_examples/
- 示例格式，供后续在 iteration 工作目录生成 eval_metadata.json 时参考。

## 映射规则

- evals.json 的 expectations 可直接映射为 eval_metadata.json 的 ssertions。
- eval_name 建议使用可读名称，避免 eval-0 这类无语义名称。
