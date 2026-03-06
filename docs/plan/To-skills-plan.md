# TrinityGuard Skills 化方案（To-skills-plan）

## 1. 目标与约束

目标：将 TrinityGuard 从“框架代码”沉淀为可复用的 skills，使 code agent（Codex/Claude Code）在实际开发任务中具备：

1. 事前安全评估（pre-deployment）
2. 运行时安全监控（runtime）
3. agent 自监控与告警闭环（self-audit）

约束（结合现状）：

- TrinityGuard 已有三层能力（L1/L2/L3）与 20 风险实现，不需要重造算法。
- 需遵循 skill-creator 的迭代方法：草稿 -> evals -> with/without 基线 -> 评审 -> 迭代。
- survey 结论显示：应优先采用“前后双闸门 + 最小权限 + 可观测性”组合策略。

## 2. 方案选择

推荐采用 **“1 个主技能 + 3 个子技能”** 的多技能方案，而不是单一大技能。

原因：

1. 与 TrinityGuard 架构天然对齐（测试 / 监控 / 治理分层）
2. 触发更准确，减少 under-trigger 或误触发
3. 便于按团队成熟度分阶段上线（先 P0，再 P1/P2）

### 2.1 技能拆分

1. `trinityguard-pretest`
- 职责：事前风险测试编排（L1/L2/L3）
- 输入：任务描述、待测 MAS 配置、目标风险集合
- 输出：测试执行计划 + 风险报告摘要 + 建议监控项

2. `trinityguard-runtime-monitor`
- 职责：运行时监控启动与模式选择（MANUAL/AUTO_LLM/PROGRESSIVE）
- 输入：任务上下文、监控预算、风险偏好
- 输出：监控激活策略、告警解释、阻断建议

3. `trinityguard-self-audit`
- 职责：对 agent 自身行为进行安全自检（工具调用、敏感输出、策略偏离）
- 输入：agent 执行轨迹/日志
- 输出：自监控结论、证据链、整改建议

4. `trinityguard-orchestrator`（主技能）
- 职责：在复杂请求中自动调度上述 3 个子技能
- 输入：用户高层目标（如“给这个多智能体工作流做上线前安全把关”）
- 输出：端到端执行路线（先测后监控，必要时触发自审计）

## 3. 对应 survey 的能力映射

### 3.1 前后双闸门（P0）

- 前闸门：`trinityguard-pretest`（威胁建模 + 风险测试）
- 后闸门：`trinityguard-runtime-monitor`（上线后持续监控）

对应 survey 中的：
- security-threat-model
- security-best-practices
- Guardrails / Monitor / MCP authorization 的组合思路

### 3.2 自监控闭环（P1）

- 使用 `trinityguard-self-audit` 对以下事件做复盘：
  - 高危工具调用
  - 敏感信息外发
  - 异常策略切换
- 形成“告警 -> 证据 -> 行动建议”闭环

### 3.3 治理与合规映射（P2）

- 将 OWASP LLM Top10 / NIST RMF / SAIF 映射到 TrinityGuard 报告字段
- 主技能输出“控制项覆盖摘要”

## 4. 技能目录结构建议

建议放在仓库内（便于版本化）：`docs/survey/skills/trinityguard/`

1. `trinityguard-orchestrator/SKILL.md`
2. `trinityguard-pretest/SKILL.md`
3. `trinityguard-runtime-monitor/SKILL.md`
4. `trinityguard-self-audit/SKILL.md`
5. `shared/references/`（公共参考：风险映射、报告模板、命令模板）
6. `shared/scripts/`（可复用脚本：报告聚合、日志解析、基线比较）

## 5. skill-creator 驱动的落地流程

按 skill-creator 的标准循环执行，每个技能都走以下步骤：

1. 先写 SKILL 草稿（description 要“偏主动触发”）
2. 建立 `evals/evals.json`（先写 prompt，不急着写 assertions）
3. 同轮跑 with-skill 与 baseline
4. 补 assertions 并打分（grading.json）
5. 聚合 benchmark（pass_rate/time/tokens）
6. 用 viewer 人审反馈后迭代
7. 最后做 description optimization（run_loop.py）

## 6. 评测设计（最小可用）

每个技能至少 6 条 eval：

1. should-trigger（4 条）
- 明确提到 MAS 安全测试/监控
- 提到 L1/L2/L3 或风险类型
- 提到上线前把关、监控告警
- 提到“agent 自检/自监控”

2. should-not-trigger（2 条）
- 普通代码重构/格式化请求
- 与安全无关的文案任务

关键指标：

- Trigger 准确率（主指标）
- 任务通过率（assertion pass_rate）
- 额外成本（time/tokens 相对 baseline 增量）

## 7. 里程碑与优先级

### Phase 0（1-2 天）

1. 产出 4 个 SKILL.md 初稿
2. 每个技能构建首批 evals
3. 跑首轮 benchmark，拿到基线

### Phase 1（2-4 天）

1. 迭代 description 与执行步骤
2. 固化 `shared/references` 与 `shared/scripts`
3. 主技能完成对子技能的调度策略

### Phase 2（1-2 天）

1. 输出治理映射（OWASP/NIST/SAIF）
2. 打包技能并形成发布说明
3. 建立后续回归评测计划

## 8. 风险与控制

1. 风险：技能描述过窄导致 under-trigger
- 控制：用 skill-creator 的 trigger eval + description optimization

2. 风险：技能过大导致执行冗长
- 控制：分成主技能 + 子技能，主技能只做编排

3. 风险：监控建议不可执行
- 控制：统一输出“可执行动作模板”（启动模式、监控清单、告警处理）

## 9. 对 TrinityGuard 代码的最小改造建议

为支持技能化，建议后续做 3 个轻量改造：

1. 增加稳定 CLI 入口（例如 pretest / monitor / report）
2. 统一报告 schema（测试结果、告警、证据链）
3. 提供无 API key 的 dry-run 模式（便于 skill benchmark）

## 10. 最终建议

优先落地多技能方案：`orchestrator + pretest + runtime-monitor + self-audit`。

这是当前 TrinityGuard 与 survey 结论之间最一致、最可执行、且可通过 skill-creator 标准流程持续优化的路径。
