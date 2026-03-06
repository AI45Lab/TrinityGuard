# TrinityGuard Skills 化方案（独立 Skills 版，任务清单）

## 1. 目标与边界

目标：基于 TrinityGuard 的风险分层思想，构建一套**独立于 TrinityGuard 代码库**的 skills，让 Claude Code / Codex 等 code agent 在自身运行过程中进行安全自检。

边界：

- 不修改 TrinityGuard 源码
- 不要求 TrinityGuard 作为运行时依赖
- 仅借鉴 TrinityGuard 的风险模型、流程设计与评测思路

## 2. 需要构建的技能

1. `trinityguard-self-guard-orchestrator`
- 主编排技能，负责整轮任务安全流程

2. `trinityguard-preflight-selfcheck`
- 执行前风险识别（输入攻击、越权意图、敏感上下文标记）

3. `trinityguard-runtime-selfmonitor`
- 执行中监控（命令、工具调用、文件访问、行为漂移）

4. `trinityguard-output-privacy-guard`
- 输出安全守门（尤其是解释性回答中的隐私/敏感泄露）

## 3. 风险覆盖要求（映射 TrinityGuard 思想）

1. L1（单体风险）
- prompt injection / jailbreak
- sensitive disclosure
- code execution / tool misuse
- hallucination / memory poisoning

2. L2（交互风险）
- message tampering（输入上下文污染）
- insecure output（输出含危险信息）
- goal drift（目标偏移）
- identity spoofing（来源伪装）

3. L3（系统风险）
- cascading failures（错误连锁）
- insufficient monitoring（监控覆盖不足）
- rogue behavior（执行轨迹异常）

## 4. 关键规则（必须实现）

1. 只要上下文含敏感信息，任何输出（含解释性回答）都必须经过输出守门。
2. “是否执行工具”与“上下文是否敏感”是同级触发条件。
3. 解释性回答不能作为默认低风险直通路径。

## 5. 触发策略

### 5.1 触发条件

任一满足即触发技能链：

1. 高风险动作
- 执行命令
- 修改文件/代码
- 外部工具或网络调用

2. 敏感上下文
- 本轮读取过隐私/密钥/凭证/个人信息
- 历史上下文已有敏感标记
- 用户问题虽是解释性，但引用了敏感上下文

### 5.2 不触发条件

同时满足才可不触发：

1. 无执行动作
2. 上下文无敏感标记
3. 输出目标不涉及隐私/凭证/内部配置

## 6. 单轮流程（技能行为规范）

1. Preflight
- 风险识别
- 上下文敏感度打标（`normal/sensitive/highly_sensitive`）
- 生成允许动作边界与阻断条件

2. Runtime
- 监控关键工具调用与行为轨迹
- 异常时告警、降级或建议中止

3. Output Guard
- 每次输出前做隐私与敏感信息检测
- 解释性回答同样执行
- 命中策略时脱敏、摘要替换或拒答

4. Post-run Audit
- 记录证据链与判定依据
- 输出整改建议

## 7. 目录结构

建议使用独立目录：`skills/trinityguard-self-guard/`

1. `trinityguard-self-guard-orchestrator/SKILL.md`
2. `trinityguard-preflight-selfcheck/SKILL.md`
3. `trinityguard-runtime-selfmonitor/SKILL.md`
4. `trinityguard-output-privacy-guard/SKILL.md`
5. `shared/references/`
- 风险分类映射
- 告警等级规范
- 审计模板
6. `shared/scripts/`
- 日志归一化
- 风险分级统计
- 报告汇总

## 8. 实施任务清单（仅列要做什么）

1. 编写四个技能的 SKILL.md 初稿。
2. 为四个技能建立统一术语和共享参考文档（L1/L2/L3 风险映射、告警等级、处置模板）。
3. 为输出守门技能定义最小披露策略（脱敏、摘要替换、拒答条件）。
4. 设计并实现上下文敏感度标记机制（会话级状态）。
5. 设计技能间编排协议（orchestrator 如何调用 preflight/runtime/output guard）。
6. 编写每个技能的 `evals/evals.json`（先 prompts，后 assertions）。
7. 补齐“解释性泄露场景”与“上下文继承泄露场景”测试集。
8. 跑 with-skill 与 baseline，对比触发正确率与泄露拦截效果。
9. 补充 grading 与 benchmark 汇总（pass_rate/time/tokens/误报率）。
10. 依据评审反馈迭代技能描述与规则。
11. 进行 description optimization，减少 under-trigger 与误触发。
12. 打包独立 skills 并输出安装/使用说明。
13. 建立回归评测清单，确保后续修改不回退解释性泄露防护能力。

## 9. 评测指标

1. 解释性输出泄露拦截率（主指标）
2. 风险识别召回率
3. 误报率
4. 脱敏后可用性
5. 额外开销（time/tokens）

## 10. 最终建议

本计划是“独立 skills 计划”，不是 TrinityGuard 改造计划。

目标是把 TrinityGuard 的安全方法沉淀为可复用技能，覆盖两条路径：

1. 执行动作路径（命令/工具/文件变更）
2. 解释性输出路径（重点防隐私泄露）

确保 code agent 在不改 TrinityGuard 源码的前提下，也能获得内在安全自检能力。
