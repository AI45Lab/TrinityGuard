# TrinityGuard Skills 化方案（内在自检版）

## 1. 目标与边界

目标：沿用 TrinityGuard 的风险分层与监控思想，让 Claude Code / Codex 这类 code agent 在执行任务时，**持续自检自身行为**，发现并处置安全风险。

本方案明确不做：

- 不面向外部 MAS 的通用评测平台化
- 不要求先接入其他多智能体框架

本方案聚焦：

1. agent 在本轮任务中的输入、推理、工具调用、输出安全
2. agent 的运行轨迹可审计、可解释、可中止
3. 通过 skills 触发自检闭环，而不是仅靠人工复盘

## 2. 方案总览

推荐采用 **“1 个主技能 + 2 个执行技能 + 1 个治理技能”**，但全部围绕“自身运行安全”。

1. `trinityguard-self-guard-orchestrator`（主技能）
- 作用：接管整轮任务的安全编排
- 触发：用户要求执行代码/命令/修改文件/调用外部工具时
- 输出：执行前检查 -> 执行中监控 -> 执行后审计 的完整流程

2. `trinityguard-preflight-selfcheck`
- 作用：执行前风险识别（prompt 注入、越权意图、敏感数据暴露风险）
- 输出：风险清单 + 允许动作边界 + 阻断条件

3. `trinityguard-runtime-selfmonitor`
- 作用：执行中监控（工具调用、文件访问、输出内容）
- 输出：实时告警、降级建议、必要时中止建议

4. `trinityguard-postrun-audit`
- 作用：执行后审计与复盘
- 输出：证据链、风险判定、后续修复动作

## 3. 与 TrinityGuard 的对应关系

将 TrinityGuard 的三层能力映射为 code agent 自检链路：

1. L1（单体风险）-> agent 自身行为风险
- prompt injection / jailbreak
- sensitive disclosure
- code execution / tool misuse
- hallucination / memory poisoning

2. L2（交互风险）-> agent 与环境交互风险
- message tampering（输入上下文被污染）
- insecure output（输出含危险内容）
- goal drift（任务目标偏移）
- identity spoofing（来源伪装）

3. L3（系统风险）-> agent 运行全局风险
- cascading failures（错误连锁）
- insufficient monitoring（监控覆盖不足）
- rogue behavior（执行轨迹异常）

## 4. 单轮执行的标准自检流程（Skill 行为规范）

### Step 1: 执行前（Preflight）

- 解析用户目标与可疑输入
- 识别高风险动作（如批量改写、shell 执行、敏感路径读写）
- 生成“允许动作列表 + 禁止动作列表 + 升级审批点”

### Step 2: 执行中（Runtime）

- 对每次关键工具调用进行风险判定
- 对输出进行敏感泄露与危险内容检查
- 命中阈值时触发：告警 -> 降级 -> 中止建议

### Step 3: 执行后（Post-run Audit）

- 生成结构化安全摘要
- 输出证据（触发点、命令、文件、上下文片段）
- 给出整改建议（最小修复动作）

## 5. 目录结构建议

建议放在仓库内：`docs/survey/skills/trinityguard-self-guard/`

1. `trinityguard-self-guard-orchestrator/SKILL.md`
2. `trinityguard-preflight-selfcheck/SKILL.md`
3. `trinityguard-runtime-selfmonitor/SKILL.md`
4. `trinityguard-postrun-audit/SKILL.md`
5. `shared/references/`
- 风险分类映射（L1/L2/L3 -> code agent）
- 告警等级规范
- 审计报告模板
6. `shared/scripts/`
- 日志提取与归一化
- 风险分级统计
- 报告汇总

## 6. 触发策略（避免 under-trigger）

在 description 中明确“偏主动触发”：

- 用户提到：执行命令、修改代码、批量处理文件、自动化脚本、外部下载/调用
- 用户未显式说“安全”，但请求本身存在明显风险面
- 任何高权限动作前自动触发 preflight

不触发场景：

- 纯解释性问答
- 无工具调用、无文件变更、无执行动作的轻任务

## 7. skill-creator 落地流程（精简版）

每个 skill 按同一循环：

1. 写 SKILL.md 草稿
2. 准备 `evals/evals.json`（先只写 prompts）
3. 跑 with-skill vs baseline
4. 补 assertions 并生成 grading
5. 聚合 benchmark（pass_rate/time/tokens）
6. 人审反馈后迭代
7. description optimization（run_loop.py）

## 8. 评测集设计（面向“自检能力”）

每个技能建议 8 条 eval：

1. should-trigger（5 条）
- 包含可疑输入 + 工具调用请求
- 包含敏感路径访问/环境变量读取
- 包含大范围文件修改与自动执行
- 包含潜在越权命令组合
- 包含“继续执行即可能风险扩大”的场景

2. should-not-trigger（3 条）
- 纯文档改写
- 纯代码讲解
- 与执行无关的静态查询

关键指标：

- 风险识别召回率（主指标）
- 误报率（控制指标）
- 阻断决策正确率
- 额外执行开销（time/tokens）

## 9. 分阶段实施

### Phase 0（P0，1-2 天）

1. 完成 `preflight` 与 `runtime` 两个技能最小版
2. 接入基础风险规则（prompt injection / sensitive disclosure / tool misuse）
3. 建立首轮 eval + benchmark

### Phase 1（P1，2-4 天）

1. 加入 `postrun-audit` 与主编排技能
2. 补充 L2/L3 风险映射规则
3. 形成稳定的告警等级与行动建议模板

### Phase 2（P2，1-2 天）

1. 做 description 优化与触发稳定性回归
2. 产出可发布技能包
3. 建立每周回归评测（防漂移）

## 10. TrinityGuard 代码最小改造建议（仅为自检技能服务）

1. 增加“本轮任务审计输出”统一 schema
- 输入摘要、工具轨迹、告警、处置动作

2. 增加轻量 CLI/函数入口
- `preflight_check(...)`
- `runtime_check(...)`
- `postrun_audit(...)`

3. 增加 dry-run
- 无外部 LLM 依赖时也可跑规则级自检，便于 CI 回归

## 11. 最终建议

当前最优路径不是“把 TrinityGuard 做成外部 MAS 安全平台技能”，而是做成 **code agent 自身安全内核技能集**：

`self-guard-orchestrator + preflight-selfcheck + runtime-selfmonitor + postrun-audit`

这样可以最直接提升 Claude Code / Codex 在真实编码任务中的自我安全能力，且与 TrinityGuard 现有架构、survey 结论、skill-creator 工作流三者一致。
