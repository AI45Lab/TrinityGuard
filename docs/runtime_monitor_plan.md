# Runtime Monitor 扩展实现计划（外部 MAS 接入）

## 1. 背景与目标

当前 Runtime Monitoring 依赖 `Safety_MAS.run_task()` 内部链路（L1/L2 hook + `AgentStepLog`）。
这导致外部已运行 MAS（不经过 TrinityGuard 封装）无法直接接入监控。

本计划扩展两条接入路径：

1. 文件流模式：实时监控外部日志文件并转换为 `AgentStepLog` 进行风险分析。
2. 服务化模式：部署常驻监控服务，MAS 通过 HTTP/gRPC 上传过程日志并获取实时分析结果。

目标：在不强制替换外部 MAS 执行框架的前提下，复用现有 Monitor 体系与告警格式。

---

## 2. 总体设计原则

- 统一事件模型：所有外部输入先转换为内部标准事件（兼容 `AgentStepLog`）。
- 统一分析引擎：复用现有 `BaseMonitorAgent`、`GlobalMonitorAgent`、`apply_monitor_decision`。
- 输入输出解耦：采集（file/service）与分析（engine）分离，便于单测和后续接更多来源（Kafka、Webhook）。
- 会话隔离：每个 `session_id` 独立状态（active monitors、window、alerts）。
- 可回放：原始输入和标准化事件都可落盘，支持事后审计。

---

## 3. 方案一：实时日志文件监控

### 3.1 适用场景

- 外部 MAS 已经把运行日志写入文件（jsonl、plain text、框架日志）。
- 不能改动 MAS 代码，或只能做很小改动（只加日志字段）。

### 3.2 架构

```text
Log File Tailer -> Parser/Normalizer -> RuntimeMonitorEngine -> Alerts/Report Sink
```

核心模块建议：

- `src/level3_safety/external_ingest/file_tailer.py`
  - 负责 tail -f、文件轮转检测、断点续读（offset 持久化）。
- `src/level3_safety/external_ingest/parsers/*.py`
  - 按格式解析日志并映射成标准事件。
- `src/level3_safety/external_ingest/normalizer.py`
  - 输出统一结构（兼容 `AgentStepLog` 字段）。
- `src/level3_safety/runtime_engine.py`
  - 无需 `run_task`，直接 `ingest(event, session_id)` 并返回增量告警。

### 3.3 最小可用日志协议（建议）

外部日志最少字段：

```json
{
  "timestamp": 1700000000.0,
  "session_id": "workflow-123",
  "from": "planner",
  "to": "executor",
  "step_type": "receive",
  "content": "...",
  "metadata": {"message_id": "m-1"}
}
```

兼容策略：

- 缺 `step_type` 时默认 `receive`。
- 缺 `timestamp` 时使用采集时间。
- 缺 `session_id` 时按文件名/进程生成。

### 3.4 关键实现点

- 增量读取：保存 `(inode, offset)`，支持重启恢复。
- 文件轮转：检测 inode 变化后自动切换新文件。
- 背压控制：解析失败和高频写入要有缓冲队列与限流。
- 解析容错：坏行进入 dead-letter 文件，不阻塞主链路。

### 3.5 产出接口

- CLI 方式：
  - `python -m trinityguard.external_monitor.file --config config/external_file_monitor.yaml`
- SDK 方式：
  - `FileMonitorRunner.start()`
  - `FileMonitorRunner.get_session_report(session_id)`

### 3.6 测试计划

- 单元测试
  - parser 映射正确性
  - tailer 轮转与断点续读
  - malformed 行容错
- 集成测试
  - 用 `tests/fixtures/logs/*.jsonl` 回放，验证告警数与风险类型
- 压测
  - 目标吞吐（如 500~2000 events/s）下监控延迟与内存占用

---

## 4. 方案二：持久化监控服务（API）

### 4.1 适用场景

- 外部 MAS 可调用 HTTP/gRPC。
- 需要多实例/多会话统一监控、集中告警与可观测性。

### 4.2 架构

```text
MAS Client -> Monitor API Service -> Session RuntimeEngine -> Alert Store / Callback
```

建议组件：

- `src/server/app.py`（FastAPI 优先，后续可扩展 gRPC）
- `src/server/session_manager.py`（session 生命周期与状态）
- `src/server/schemas.py`（Pydantic 请求响应模型）
- `src/server/auth.py`（API key/HMAC，可选）

### 4.3 API 草案

1. `POST /v1/sessions`
- 创建会话并配置监控模式。

2. `POST /v1/sessions/{session_id}/events`
- 批量上传事件（标准化前或标准化后都可）。
- 返回：本批次新增 alerts、当前 active monitors、风险摘要。

3. `GET /v1/sessions/{session_id}/alerts`
- 拉取告警（支持 cursor 分页）。

4. `GET /v1/sessions/{session_id}/report`
- 拉取阶段性/最终报告。

5. `POST /v1/sessions/{session_id}/close`
- 关闭会话并冻结报告。

### 4.4 会话状态模型

每个 session 至少维护：

- `active_monitor_names`
- `global_monitor_window`
- `alerts`
- `last_event_ts`
- `context`（可选：任务描述、业务标签）

存储层建议分阶段：

- Phase 1：进程内内存（快速落地）。
- Phase 2：Redis（多实例共享状态）。
- Phase 3：PostgreSQL/对象存储（审计与长期报表）。

### 4.5 客户端接入方式

- 同步拉取：MAS 每发送一批事件后立即拿分析结果。
- 异步推送：服务通过 webhook 推送 critical alerts。
- SDK 封装：`TrinityGuardMonitorClient`，隐藏重试、批量、签名。

### 4.6 安全与可靠性

- 鉴权：API Key 或 HMAC 签名。
- 幂等：`event_id` 去重，防重复上报。
- 限流：按 client/session 做 QPS 限制。
- 超时降级：LLM judge 超时时回退规则检测（已有能力可复用）。
- 审计：关键告警和决策写入结构化日志。

### 4.7 测试计划

- API 合约测试（schema + 错误码）
- 会话并发测试（多 session 隔离）
- 容错测试（重复 event、乱序 event、空批次）
- E2E 测试（模拟 MAS 客户端持续上传）

---

## 5. 统一改造点（两种方案共用）

### 5.1 抽离分析引擎

将 `Safety_MAS._process_log_entry()` 的核心逻辑抽成可复用引擎，例如：

- `RuntimeMonitorEngine.ingest(log_entry, session_id) -> List[Alert]`
- `RuntimeMonitorEngine.get_report(session_id) -> Dict`

`Safety_MAS.run_task()` 改为此引擎的一个调用方，而非唯一入口。

### 5.2 新增外部事件 schema

建议新增：

- `ExternalEvent`（输入宽松）
- `NormalizedEvent`（内部严格）

并提供：

- `event_to_agent_step_log(normalized_event) -> AgentStepLog`

### 5.3 配置扩展

建议新增配置文件：

- `config/external_file_monitor.yaml`
- `config/monitor_service.yaml`

包含：

- monitor 选择模式
- progressive 参数（window_size/max_events）
- parser 类型
- sink（stdout/file/http callback）

---

## 6. 分阶段实施里程碑

### Milestone 1（1~2 天）

- 抽离 `RuntimeMonitorEngine`（单会话）
- 保持 `Safety_MAS` 兼容
- 增加基础单测

交付：

- `Safety_MAS` 与新引擎并行可用
- 现有测试不回归

### Milestone 2（2~3 天）

- 文件监控 MVP（jsonl）
- 支持断点续读 + 基本轮转
- CLI 启动方式

交付：

- 可对外部日志文件实时产出 alerts

### Milestone 3（3~5 天）

- FastAPI 服务 MVP
- session 创建、事件上传、告警查询、报告查询
- 简单鉴权 + 限流

交付：

- 外部 MAS 通过 HTTP 接入运行时监控

### Milestone 4（2~4 天）

- 稳定性增强（幂等、重试、观测指标）
- 文档与示例（client demo + deployment）

交付：

- 可持续部署的监控服务版本

---

## 7. 风险与应对

1. 日志格式高度异构
- 应对：parser 插件化 + 明确最小协议 + 死信队列。

2. 高吞吐导致监控延迟
- 应对：批处理 ingest、异步队列、progressive 动态启停降低开销。

3. LLM 成本与稳定性
- 应对：规则优先过滤 + LLM 仅用于高风险候选 + 超时 fallback。

4. 多会话状态膨胀
- 应对：TTL 清理、分层存储、冷会话归档。

---

## 8. 推荐落地顺序

1. 先做方案一（文件监控）
- 改造面小，最快验证“外部 MAS 可接入”目标。

2. 再做方案二（服务化）
- 复用同一 `RuntimeMonitorEngine`，仅替换输入通道与状态管理。

3. 最后统一 SDK 与运维能力
- 提供标准客户端、部署清单、监控面板指标。

---

## 9. 验收标准

- 外部 MAS 不经 `Safety_MAS.run_task()` 也能触发现有 monitors 告警。
- 两种入口（file/service）都可输出统一的 alerts/report 结构。
- 在至少一个真实示例（如 `examples/mas_test`）完成端到端联调。
- 关键路径具备自动化测试（单测 + 集成 + 基础压测）。
