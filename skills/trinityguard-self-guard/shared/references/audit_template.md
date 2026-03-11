# 审计模板（Legacy）

该模板用于历史兼容场景：生成单轮审计 JSON。

主契约已迁移为 JSONL 事件流：`guard_event.schema.json`。

## 使用建议
1. 新接入优先使用 `self_guard_runtime_hook_template.py` + `--events-log`。
2. 只有在需要兼容旧流程时，才使用单轮审计 JSON。
3. 单轮 JSON 可通过 `--out` 由 runtime hook 生成摘要。

## 最低字段
1. `session_id`
2. `policy_profile`
3. `final_action`
4. `decision_reason_codes`
5. `matched_rules`
