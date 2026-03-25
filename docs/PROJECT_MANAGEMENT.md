# TrinityGuard 项目管理总文档

> **一站式项目导航**。本文档是项目的管理中枢，提供项目全貌、文档地图和团队协作规范。

---

## 项目概览

| 项目 | 内容 |
|------|------|
| **名称** | TrinityGuard — 多智能体系统统一安全框架 |
| **当前版本** | v0.1.0 (Alpha) |
| **GitHub** | https://github.com/AI45Lab/TrinityGuard |
| **技术报告** | `Technical_Report_TrinityGuard_260316.pdf` |
| **状态** | 核心功能已完成，开源准备阶段 |

**一句话描述**：TrinityGuard 是面向多智能体系统 (MAS) 的统一安全框架，提供涵盖 20 种风险的**事前安全测试**与**运行时监控**能力，当前以 AG2/AutoGen 为主要底层框架。

---

## 文档地图

### 核心文档（必读）

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目入口 | `README.md` | 功能介绍、快速开始、安装指南 |
| **静态设计** | `docs/DESIGN.md` | 架构、组件、接口的权威设计说明 |
| **实现进度** | `docs/PROGRESS.md` | 当前功能完成状态、已知问题、下一步计划 |
| Agent 规范 | `AGENTS.md` | 对 Claude Code 等 Agent 的强制安全自检规范 |

### 架构设计文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 系统架构分析 | `docs/architecture/src_architecture.md` | 三层架构的源码级深度分析 |
| 风险分类体系 | `docs/architecture/risk_taxonomy.md` | 20 种 MAS 风险的完整分类与说明 |
| 运行时监控设计 | `docs/architecture/runtime_monitoring.md` | 运行时监控架构、三种监控模式详解 |

### 使用指南

| 文档 | 路径 | 说明 |
|------|------|------|
| L1 风险测试指南 | `docs/guides/l1_usage_guide.md` | 8 种单智能体风险的快速测试方法 |
| AG2 固定工作流 | `docs/guides/ag2_fixed_workflow.md` | 确定性工作流的设计与使用 |
| AG2 消息格式 | `docs/guides/ag2_message_format.md` | AG2 消息存储机制与 role 分配规则 |
| 日志系统指南 | `docs/guides/logging_guide.md` | Level3 结构化日志的使用与扩展 |

### 技术分析文档

| 文档 | 路径 | 说明 |
|------|------|------|
| Level1 框架分析 | `docs/analysis/level1_framework_analysis.md` | AG2MAS 包装层的深度解析 |
| Level2 中介层分析 | `docs/analysis/level2_intermediary_analysis.md` | 框架无关接口与工作流执行器 |
| 测试流程说明 | `docs/analysis/testing_flow_explanation.md` | 三层架构中数据流的完整说明 |
| 消息篡改测试解读 | `docs/analysis/message_tampering_test_report_explained.md` | 典型风险测试的案例分析 |
| 直接覆盖示例 | `docs/analysis/direct_override_example.md` | 提示词注入的完整执行流程 |

### 调研文档

| 文档 | 路径 | 说明 |
|------|------|------|
| Agent 安全 Skills 调研 | `docs/survey/agent_safety_skills_survey.md` | Claude Code Skills 的安全实现方案 |
| LLM 调研 | `docs/survey/gpt_survey.md` / `gemini_survey_1.md` | 不同 LLM 的特性与选型建议 |

### TrinitySkills 文档

| 文档 | 路径 | 说明 |
|------|------|------|
| Skills 概览 | `docs/TrinitySkills/README.md` | 独立于代码库的 Claude Code Skills 方案 |
| Skills 架构 | `docs/TrinitySkills/architecture.md` | Skills 的结构、触发链路、事件模型 |
| Skills 测试 | `docs/TrinitySkills/testing.md` | 安装、验收测试、回归测试说明 |

### 历史归档文档

| 目录/文件 | 路径 | 说明 |
|-----------|------|------|
| 归档说明 | `docs/archive/README.md` | 归档内容的背景和使用指引 |
| 早期设计规范 | `docs/archive/original_design_spec.md` | 项目启动时的初始设计文档 |
| 实现计划 (13份) | `docs/archive/plans/` | 各功能模块的详细实现计划 |
| 解决方案记录 (11份) | `docs/archive/solutions/` | 开发过程中的具体问题解决方案 |
| 项目汇报 | `docs/archive/project_report_2026.md` | 2026 年初的项目进展汇报 |

---

## 源代码结构

```
src/
├── level1_framework/        # MAS 框架适配层
│   ├── base.py              # BaseMAS 抽象接口
│   ├── ag2_wrapper.py       # AG2/AutoGen 包装实现
│   └── evoagentx_adapter.py # EvoAgentX 框架适配器
│
├── level2_intermediary/     # 框架无关中间层
│   ├── base.py              # MASIntermediary 抽象接口
│   ├── ag2_intermediary.py  # AG2 具体实现
│   ├── structured_logging/  # 结构化日志系统
│   └── workflow_runners/    # 工作流执行器 (基础/拦截/监控/组合)
│
├── level3_safety/           # 安全测试与监控层
│   ├── safety_mas.py        # Safety_MAS 主协调器
│   ├── judges/              # Judge Factory (LLM 判定系统)
│   ├── risk_tests/          # 20 种风险测试库
│   ├── monitor_agents/      # 20 个运行时监控器
│   └── monitoring/          # 全局监控与渐进式激活
│
└── utils/                   # 工具与配置模块
    ├── config.py            # 配置管理
    ├── llm_client.py        # LLM 客户端 (OpenAI/Anthropic)
    └── log_session_manager.py
```

---

## 测试与示例

```
tests/
├── level3_safety/           # L3 安全测试套件
│   ├── test_all_l1_risks.py
│   ├── test_all_l2_risks.py
│   ├── test_all_l3_risks.py
│   ├── test_pair.py / test_pair_integration.py
│   └── test_global_monitor.py
├── evoagent_bench/          # EvoAgent 基准测试
├── integration_test.py
└── test_*.py                # 单元测试

examples/
├── basic_usage.py           # 基础使用示例
├── example_usage.py         # 完整使用示例
├── full_demo/               # 分步完整演示 (step0~step4)
└── mas_test/                # 真实 MAS 应用示例
    ├── src/financial_mas/   # 金融分析 MAS
    ├── src/deep_research_mas/
    ├── src/travel_planner_mas/
    └── src/game_design_mas/
```

---

## 配置系统

```
config/
├── default.yaml             # 全局默认配置
├── mas_llm_config.yaml      # 被测 MAS 的 LLM 配置
├── monitor_llm_config.yaml  # 监控器/Judge 的 LLM 配置
└── evoagent_bench_config.yaml
```

**快速开始**：复制 `config/default.yaml`，填写 API Key 环境变量，运行 `examples/basic_usage.py`。

---

## 开发规范

- **语言**：Python 3.9+
- **包管理**：`pip install -e .`（开发模式）
- **测试**：`pytest tests/`
- **分支策略**：直接在 `master` 分支提交（当前阶段）
- **Agent 规范**：所有 Claude Code 操作须遵循 `AGENTS.md` 中的安全自检流程

---

## 项目里程碑

| 时间 | 里程碑 |
|------|--------|
| 2026-01 | 三层架构设计与 L1/L2/L3 基础框架实现 |
| 2026-01 | LLM Judge Factory 与 20 种风险测试库完成 |
| 2026-02 | 渐进式运行时监控 (Progressive Mode) 实现 |
| 2026-02 | PAIR 框架集成、EvoAgentX 适配器完成 |
| 2026-03 | 技术报告发布 (TrinityGuard_260316.pdf) |
| 当前 | 文档整理、开源准备、Skills 化探索 |

详细历史记录参见 `docs/PROGRESS.md` 与 `docs/archive/`。
