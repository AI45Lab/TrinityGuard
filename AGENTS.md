<INSTRUCTIONS>
- 不要新建 worktree 或 branch，直接在当前目录修改。
- 使用中文回答。

- 本仓库启用强制安全自检：无论用户是否主动提及安全，任何任务在对外给出最终回复前，都必须先执行一次 self-guard 检查。
- 强制检查脚本：`skills/trinityguard-self-guard/shared/scripts/self_guard_runtime_hook_template.py`。
- 策略文件：`skills/trinityguard-self-guard/shared/references/runtime_policy.template.json`。
- 执行要求：

  1) 每轮在形成候选回复后，构造输入并调用 runtime hook。
  2) 若 hook 输出 `final_action=block`，禁止直接输出原始候选回复，必须改为安全拒答/脱敏结果。
  3) 若 hook 输出 `final_action=downgrade`，必须降级表达并明确不确定性，不得给高置信结论。
  4) 仅当 hook 输出 `final_action=allow` 时，才可正常输出。
- 解释性回答也必须经过该流程，不允许因“只是解释/总结”而跳过。
- 若当前环境无法执行 hook（例如脚本不可用），必须在回复中明确说明“未完成安全自检”，并采取保守输出策略。
  `</INSTRUCTIONS>`
