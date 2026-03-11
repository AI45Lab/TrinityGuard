# scripts 说明

此目录用于放置 self-guard 技能配套的辅助脚本模板。

## 已有脚本

1. `aggregate_benchmark_template.py`
- 用途：聚合 with-skill / without-skill 的评测结果，输出 benchmark JSON 与 Markdown 摘要。

2. `sensitivity_state_tracker_template.py`
- 用途：根据上下文事件更新会话级敏感状态（`normal/sensitive/highly_sensitive`），避免“解释型请求绕过安全守门”。

3. `verify_multi_source_template.py`
- 用途：对结论的来源做一致性检查，单一工具来源默认降级；多源独立一致才可提升可信度。

4. `normalize_audit_record_template.py`
- 用途：把 preflight/runtime/output_guard 的结果统一归并成标准审计记录。

5. `run_local_benchmark_template.py`
- 用途：从 `evals/evals.json` 生成本地迭代目录（with_skill/without_skill 的 grading/timing），并可直接调用聚合脚本产出 benchmark。

6. `validate_eval_assets_consistency.py`
- 用途：校验 `evals.json` 与 `eval_metadata_examples` 是否一致（id、prompt、断言数量、tags）。

7. `self_guard_runtime_hook_template.py`
- 用途：最小可用运行时接入层。输入任务 JSON，执行 preflight/runtime/output guard，输出审计记录并持久化会话敏感状态。
- 支持 `--policy` 加载策略配置。

8. `check_benchmark_thresholds.py`
- 用途：将 `benchmark.json` 与阈值策略做自动对比，作为回归门槛。

## 策略文件

位于 `../references/`：
1. `runtime_policy.strict.json`
2. `runtime_policy.balanced.json`
3. `runtime_policy.permissive.json`
4. `runtime_policy.template.json`（兼容旧路径）

## 快速命令

1. 评测资产一致性校验
```bash
python shared/scripts/validate_eval_assets_consistency.py . --strict
```

2. 生成并聚合某个技能的本地 benchmark（支持按 eval tags 输出 benign/adversarial 分层统计）
```bash
python shared/scripts/run_local_benchmark_template.py \
  trinityguard-output-privacy-guard \
  ../../safety-guard-log/benchmarks/output-privacy-iter-1
```

3. 运行最小 runtime hook 样例（strict）
```bash
python shared/scripts/self_guard_runtime_hook_template.py \
  shared/scripts/runtime_hook_input_example.json \
  --policy shared/references/runtime_policy.strict.json \
  --out ../../safety-guard-log/runtime_hook_audit.json
```

4. benchmark 阈值检查
```bash
python shared/scripts/check_benchmark_thresholds.py \
  ../../safety-guard-log/benchmarks/output-privacy-iter-1/benchmark.json \
  shared/references/benchmark_thresholds.template.json
```

## 设计原则

1. 脚本保持轻量、跨平台、零业务耦合。
2. 作为模板直接复用或二次改造，不依赖 TrinityGuard 源码。
3. 默认输出结构化 JSON，便于后续自动评估与审计（含误报/漏报指标）。
