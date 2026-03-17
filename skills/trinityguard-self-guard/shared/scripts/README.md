# scripts 说明

该目录放置 self-guard 的可复用脚本。

## 核心脚本

1. `self_guard_runtime_hook_template.py`
- 运行 preflight/runtime/output guard。
- 主输出为 JSONL 事件流（`--events-log`）。
- 可选输出单轮摘要 JSON（`--out`）。

2. `query_guard_events.py`
- 按 `session_id/turn_id/event_type/decision/reason_code` 过滤 JSONL 日志。

3. `validate_eval_assets_consistency.py`
- 校验各 skill 的 `evals.json` 与 `eval_metadata_examples` 是否一致。

4. `run_local_benchmark_template.py`
- 运行本地 benchmark，并产出性能与质量统计。

5. `aggregate_benchmark_template.py`
- 聚合 benchmark 结果到单一 JSON/Markdown 摘要。

## 常用命令

```bash
python shared/scripts/self_guard_runtime_hook_template.py \
  shared/scripts/runtime_hook_input_example.json \
  --policy shared/references/runtime_policy.balanced.json \
  --events-log ../../.codex/logs/self_guard_events.jsonl
```

```bash
python shared/scripts/query_guard_events.py \
  ../../.codex/logs/self_guard_events.jsonl \
  --event-type final_decision --limit 20
```

```bash
python shared/scripts/validate_eval_assets_consistency.py . --strict
```

