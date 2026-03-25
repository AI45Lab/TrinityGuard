# 历史归档文档

> 本目录存放开发过程中产生的历史性文档，包括早期实现计划、解决方案记录、中间阶段报告等。这些文档反映了项目的演进脉络，但不代表当前的设计状态。
>
> **当前设计请参考 `docs/DESIGN.md`，实现状态请参考 `docs/PROGRESS.md`。**

---

## 目录结构

```
archive/
├── README.md                          # 本文件：归档说明
│
├── original_design_spec.md            # 项目最初设计规范
├── risk_tier_implementation_notes.md  # 早期风险分层实现笔记
├── project_report_2026.md             # 2026年初项目汇报文档
├── pair_integration_verification.md   # PAIR框架集成验证记录
├── runtime_monitor_plan.md            # 运行时监控扩展规划
├── runtime_flow_demo.md               # 运行时监控流程演示记录
│
├── plans/                             # 各功能模块实现计划（共13份）
├── solutions/                         # 具体问题解决方案记录（共11份）
├── design/                            # 早期设计草案
└── todo/                              # 历史待办项
```

---

## 归档内容说明

### 顶层文件

| 文件 | 时间 | 内容说明 |
|------|------|---------|
| `original_design_spec.md` | 2026-01 初 | 项目启动时的初始设计文档，包含三层架构的原始构想、接口定义草案，是整个项目的设计起点 |
| `risk_tier_implementation_notes.md` | 2026-02 | 20 种风险 Tier 分层方式的实现思路笔记，当前分类体系已稳定，见 `docs/architecture/risk_taxonomy.md` |
| `project_report_2026.md` | 2026-03 | 面向内部汇报的项目进展文档，包含核心价值主张、已完成功能概述、技术创新点 |
| `pair_integration_verification.md` | 2026-02 | PAIR 框架与 L2 接口兼容性验证的完整记录，该功能已完成集成 |
| `runtime_monitor_plan.md` | 2026-02 | 运行时监控的外部 MAS 接入方案规划（服务化、文件流等模式），属于中期规划 |
| `runtime_flow_demo.md` | 2026-02 | 以 Jailbreak 攻击为例的完整监控数据流演示，适合理解监控系统内部机制 |

### plans/ 目录（早期实现计划）

这些文档是各功能模块**开发前**编写的设计计划，按时间顺序记录了项目的演进节奏：

| 文件 | 对应功能 | 完成状态 |
|------|---------|---------|
| `2026-01-23-mas-safety-framework-design.md` | 三层架构总体设计 | ✅ 已实现 |
| `2026-01-23-implementation-plan.md` | 初期实施计划总纲 | ✅ 已完成 |
| `2026-01-23-real-llm-integration-design.md` | 真实 LLM 集成设计 | ✅ 已实现 |
| `2026-01-23-real-llm-integration-implementation.md` | LLM 集成实施步骤 | ✅ 已完成 |
| `2026-01-25-judge-factory-design.md` | Judge 工厂模式设计 | ✅ 已实现 |
| `2026-01-25-judge-factory-impl.md` | Judge 工厂实施计划 | ✅ 已完成 |
| `2026-01-25-llm-judge-monitors.md` | 监控器 LLM 升级计划 | ✅ 已完成 |
| `2026-01-26-full-demo-test.md` | 完整端到端演示计划 | ✅ 已完成 |
| `2026-01-26-separate-llm-config-design.md` | 双配置分离设计 | ✅ 已实现 |
| `2026-01-26-separate-llm-config-impl.md` | 双配置分离实施 | ✅ 已完成 |
| `2026-01-28-evoagentx-adapter-design.md` | EvoAgentX 适配器设计 | ✅ 基础完成 |
| `2026-02-02-rewrite-l1-with-pair.md` | PAIR 框架集成计划 | ✅ 已完成 |
| `2026-02-03-tier2-risk-tests.md` | L2 六种风险测试计划 | ✅ 已完成 |
| `2026-02-04-evoagent-workflow-testing-design.md` | EvoAgent 工作流测试设计 | ✅ 已完成 |
| `2026-02-10-progressive-runtime-monitoring.md` | 渐进式监控计划 | ✅ 已完成 |
| `To-skills-plan.md` | TrinitySkills 化方案 | 🔄 进行中 |

### solutions/ 目录（问题解决方案记录）

记录开发过程中遇到的具体技术问题及其解决方案，对理解代码实现细节有参考价值：

| 文件 | 解决的问题 |
|------|---------|
| `UNIFIED_LOG_MANAGEMENT.md` | 统一日志管理的设计与实现 |
| `detailed_log_format.md` | AgentStepLog 数据结构的最终形态 |
| `detailed_log_improvement_summary.md` | 从简单日志到结构化日志的演进过程 |
| `test_log_saving_feature.md` | 测试日志持久化功能的实现 |
| `chat_manager_recipient_solution.md` | AG2 chat_manager 接收方解析的解决方案 |
| `IMPLEMENTATION_SUMMARY.md` | chat_manager 解析功能的实现总结 |
| `COMPLETION_SUMMARY.md` | 日志系统完成阶段总结 |
| `test_all_l1_risks_summary.md` | L1 风险测试体系建立的过程记录 |
| `test_all_l1_risks_improvement.md` | L1 测试代码优化过程 |
| `test_all_l1_risks_final_summary.md` | L1 测试体系验收总结 |
| `test_scripts_improvement_summary.md` | 测试脚本 CLI 化改进记录 |

### design/ 目录

| 文件 | 说明 |
|------|------|
| `runtime_monitor_metrics_design.md` | 运行时监控前端仪表盘的指标设计草案（未实现，待开发） |

### todo/ 目录

| 文件 | 说明 |
|------|------|
| `level1_evoagentx_improvements.md` | EvoAgentX 适配器的待完善功能清单（DocAgent 支持、高级 Agent 转移等） |

---

## 使用建议

- 如果你想**了解某个功能的设计原理**，查阅 `plans/` 中对应的设计文档
- 如果你想**调试某个具体问题**，查阅 `solutions/` 中的解决方案记录
- 如果你想**了解项目整体演进历史**，按时间顺序阅读 `plans/` 中的文档
- 如果你想**了解当前实现状态**，请访问 `docs/PROGRESS.md`（不在本目录）
