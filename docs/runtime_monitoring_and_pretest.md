# Runtime 监督与事前攻击测试说明

本文基于当前代码实现，梳理：
1) runtime 监督的联动流程、监控可见内容、频率与输出  
2) 事前攻击测试的成功/失败判定依据、原始材料、输出与关键代码位置

---

## 1. Runtime 监督：代码流与联动方式

### 1.1 入口与模式
- 入口在 `Safety_MAS.start_runtime_monitoring()`，支持 `MANUAL / AUTO_LLM / PROGRESSIVE` 模式。  
- **PROGRESSIVE** 模式启用全局协调器（Global Monitor），按窗口决策动态开关子监控（sub monitor）。

**关键代码：**
- `src/level3_safety/safety_mas.py`（`start_runtime_monitoring` / `_process_log_entry`）
- `src/level3_safety/monitoring/global_monitor.py`
- `src/level3_safety/monitoring/activation.py`

### 1.2 监控看到的是什么（数据来源）
运行时日志来自 Level2 中间层的结构化日志系统：
- `MonitoredWorkflowRunner` 对每条消息调用 `on_message()`  
- 生成 `AgentStepLog`：`timestamp / agent_name / step_type / content / metadata`

**监控可见字段（AgentStepLog）：**
- `timestamp`：日志时间戳  
- `agent_name`：当前接收该消息的 agent  
- `step_type`：`receive / tool_call / tool_response`（由消息类型决定）  
- `content`：标准化后的消息内容（工具调用会被格式化为字符串）  
- `metadata`：包括 `from / message_id / message_type`，GroupChat 场景下还有 `physical_to / routing_mode`

**关键代码：**
- `src/level2_intermediary/workflow_runners/monitored.py`（`on_message`）
- `src/level2_intermediary/structured_logging/schemas.py`

### 1.3 联动执行流程
执行流程可简化为：
1) MAS 运行时每条消息都会触发 `AgentStepLog`  
2) `Safety_MAS._process_log_entry()` 将该 log 依次送入 **当前激活的子监控**  
3) 子监控返回 `Alert`（若检测到风险）  
4) 系统记录 `Alert` 并写入监控报告  
5) 若开启 PROGRESSIVE，全局监控在窗口触发时基于摘要产生 “开关决策”，动态调整子监控集合

**关键代码：**
- `src/level3_safety/safety_mas.py`（`_process_log_entry` / `_handle_alert`）
- `src/level3_safety/monitor_agents/base.py`

### 1.4 频率与触发点
- **子监控频率**：每条 `AgentStepLog` 触发一次（即每条消息）。  
- **全局监控频率**：按窗口触发（默认 `window_size=10`，也可配置 `window_seconds`）。  
- **决策生效时机**：当前实现为“本条日志处理完成后生效”，避免同一条日志的处理顺序产生抖动。

### 1.5 运行时输出（每次输出是什么）
**子监控输出：**  
- `Alert` 对象：`severity / risk_type / message / evidence / recommended_action`  
- 由 `Safety_MAS` 补充来源追踪字段：`agent_name / source_agent / target_agent / source_message / message_id / step_index`

**系统输出：**  
- `StructuredLogger` 写入 `monitor_alert` 事件  
- `WorkflowResult.metadata` 中包含：  
  - `monitoring_report`（告警统计）  
  - `alerts`（告警明细列表）

**关键代码：**
- `src/level3_safety/monitor_agents/base.py`（`Alert` 定义）
- `src/level3_safety/safety_mas.py`（`_handle_alert` / `_generate_monitoring_report`）
- `src/utils/logging_config.py`（`log_monitor_alert`）

### 1.6 Progressive（全局监控）看到的内容与输出
全局监控并不读取原始全部日志，而是读取 **窗口化摘要**：
- 窗口内事件计数（按 `step_type` / agent 统计）  
- 事件内容预览（最多 N 条）  
- 当前已激活与可用的子监控列表  

**输出：**
- `decision = { enable: [...], disable: [...], reason, confidence }`  
- `Safety_MAS` 会应用该决策，动态调整激活监控集合，并写入 `monitor_decision` 事件日志。

**关键代码：**
- `src/level3_safety/monitoring/global_monitor.py`
- `src/level3_safety/safety_mas.py`（`_apply_progressive_decision`）

---

## 2. 事前攻击测试：成功/失败判定与输出

### 2.1 总体流程
入口方法：
- `Safety_MAS.run_auto_safety_tests()`  
- `Safety_MAS.run_manual_safety_tests()`

流程：
1) 加载测试用例（静态或动态生成）  
2) 逐条执行 `run_single_test()`  
3) 汇总为 `TestResult`（通过 / 失败 / 失败数 / severity 统计）

**关键代码：**
- `src/level3_safety/safety_mas.py`（`run_manual_safety_tests`）
- `src/level3_safety/risk_tests/base.py`（`BaseRiskTest.run` / `_aggregate_results`）

### 2.2 攻击成功与失败如何判定
核心规则：  
- **单个 test case**：`run_single_test()` 返回 `passed: True/False`  
- **整体风险测试**：只要有任一 test case 失败，则 `TestResult.passed = False`  
- “攻击成功”通常等价于 test case **不通过**（`passed=False`）

判定依据由各具体风险测试实现：
- **LLM Judge**：基于 risk-specific prompt 判定 `has_risk`  
- **启发式规则**：字符串规则或模式匹配作为回退  
- **PAIR 攻击**：`AttackResult.success == True` 代表攻击目标达成

**关键代码：**
- `src/level3_safety/risk_tests/base.py`（`run` / `_aggregate_results`）
- `src/level3_safety/judges/llm_judge.py`（`LLMJudge.analyze`）
- `src/level3_safety/jailbreak_frameworks/pair.py`（`PAIROrchestrator.run_attack`）

### 2.3 原始材料（判定的“证据”来自哪里）
判定来源主要是被测 MAS 的响应内容与攻击上下文：
- `run_single_test()` 通常把 **agent 回复** 作为判定对象  
- 对于 PAIR 类攻击，判定对象为 `attack_result.target_response`  
- 对于 L2 消息篡改类测试，判定对象包括“被修改后消息”与目标 agent 的响应

**关键代码：**
- `src/level3_safety/risk_tests/l1_jailbreak/test.py`（`_detect_jailbreak_success`）
- `src/level3_safety/risk_tests/l1_tool_misuse/test.py`（`_detect_tool_misuse`）
- `src/level3_safety/risk_tests/l3_sandbox_escape/test.py`（`_detect_escape`）
- `src/level3_safety/risk_tests/l2_base.py`（消息拦截与修改逻辑）

### 2.4 具体输出
**标准输出：**
- `TestResult.to_dict()` 返回：
  - `passed / total_cases / failed_cases / pass_rate`
  - `details`（每个 test case 的结果、agent 级别结果、错误信息）
  - `severity_summary`

**日志输出：**
- `StructuredLogger` 写入 `test_start` / `test_complete` 事件  
- 可由测试脚本保存为 JSON（测试脚本层面实现）

**关键代码：**
- `src/level3_safety/risk_tests/base.py`（`TestResult.to_dict`）
- `src/utils/logging_config.py`（`log_test_start` / `log_test_result`）

### 2.5 与监控的联动（可选）
`run_tests_with_monitoring()` 会在测试后对失败的 case 用“关联监控”进行再评估：
- 创建 **合成日志**（`AgentStepLog`）  
- 调用关联监控的 `process()`  
- 将 `monitor_evaluations` 附加到测试结果中

**关键代码：**
- `src/level3_safety/safety_mas.py`（`run_tests_with_monitoring`）
- `src/level3_safety/risk_tests/base.py`（`evaluate_with_monitor`）
