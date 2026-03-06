# TrinityGuard Skills 化方案（内在自检版，修订）

## 1. 目标与边界

目标：沿用 TrinityGuard 的风险分层与监控思想，让 Claude Code / Codex 这类 code agent 在执行任务时，持续自检自身行为并降低安全风险。

本方案不做：

- 不做外部 MAS 平台化监测
- 不要求接入其他 MAS 框架后再起步

本方案聚焦：

1. 输入、工具调用、文件读写、输出内容的全链路安全
2. 运行过程可审计、可解释、可中止
3. 用 skills 形成自动化自检闭环

## 2. 方案总览

采用 4 个技能协作，但都围绕 code agent 自身：

1. `trinityguard-self-guard-orchestrator`
- 主编排技能，负责整轮任务的安全流程控制

2. `trinityguard-preflight-selfcheck`
- 执行前风险识别（输入攻击、越权意图、敏感上下文标记）

3. `trinityguard-runtime-selfmonitor`
- 执行中监控（命令、工具调用、文件访问、行为漂移）

4. `trinityguard-output-privacy-guard`
- 输出安全守门（尤其是解释性回答中的隐私/敏感泄露）

## 3. 本次修订的核心问题与改进

### 3.1 问题

原计划把“纯解释性回答”默认作为低风险场景，可能导致以下漏检：

1. agent 先读取了包含隐私的数据
2. 用户后续请求“解释/总结/回答问题”
3. 虽然没有工具调用，但回答本身可能泄露敏感信息

### 3.2 修订原则

新增强制规则：**只要上下文已包含敏感信息，任何输出（含纯解释性回答）都必须经过输出安全守门**。

换言之：

- “是否调用工具”不再是唯一触发条件
- “上下文敏感度”成为同等优先级触发条件

## 4. 触发策略（修订后）

### 4.1 触发条件

以下任一条件满足，即触发安全技能链：

1. 高风险动作触发
- 执行命令
- 修改代码/文件
- 调用外部工具或网络请求

2. 敏感上下文触发（新增）
- 本轮读过可能包含隐私/密钥/凭证/个人信息的数据
- 历史上下文中已有敏感片段标记
- 用户问题虽然是解释性，但引用了敏感上下文

### 4.2 不触发条件（收紧后）

仅当同时满足以下条件才可不触发：

1. 无工具调用、无文件变更、无执行动作
2. 当前与历史上下文均未标记敏感信息
3. 输出目标不涉及身份、凭证、隐私、内部配置等敏感内容

## 5. 单轮执行标准流程（修订后）

### Step 1: Preflight

- 风险识别
- 上下文敏感度打标（`normal/sensitive/highly_sensitive`）
- 生成允许动作边界与阻断条件

### Step 2: Runtime

- 监控工具调用与关键行为
- 发现异常时告警、降级或建议中止

### Step 3: Output Guard（新增强调）

- 每次对外输出前做隐私与敏感信息检测
- 对解释性回答同样执行检查
- 命中策略时执行脱敏、摘要替换或拒答模板

### Step 4: Post-run Audit

- 记录证据链与判定依据
- 输出整改建议和后续动作

## 6. 技能职责拆分（更新）

1. `trinityguard-self-guard-orchestrator`
- 统一调度 preflight/runtime/output guard/post-audit

2. `trinityguard-preflight-selfcheck`
- 输出上下文敏感级别与风险基线

3. `trinityguard-runtime-selfmonitor`
- 输出行为告警与执行期处置建议

4. `trinityguard-output-privacy-guard`
- 输出前进行敏感泄露拦截
- 支持解释性输出的“最小披露”与脱敏改写

## 7. 评测设计（重点修订）

每个技能建议至少 8 条 eval，且必须包含下列新增场景：

1. 解释性泄露场景（新增必测）
- 先读取含隐私文件，再让 agent 解释/总结
- 验证是否触发输出守门并执行脱敏

2. 上下文继承泄露场景（新增必测）
- 敏感信息来自上一轮历史，而非当前文件读取
- 验证是否仍触发输出守门

3. 常规执行风险场景
- 命令执行、批量改写、潜在越权工具调用

关键指标新增：

- 解释性输出泄露拦截率（新增主指标）
- 脱敏后可用性（内容保真度）
- 误拦截率
- 总体开销（time/tokens）

## 8. TrinityGuard 最小改造建议（为修订目标服务）

1. 增加“上下文敏感度状态”
- 在本轮会话中持续维护 `sensitivity_state`

2. 增加输出守门统一入口
- `output_privacy_guard(text, sensitivity_state, policy)`

3. 在审计 schema 中新增字段
- `output_guard_triggered`
- `redaction_applied`
- `leakage_risk_level`

## 9. 里程碑（更新）

### Phase 0（P0）

1. 落地 `preflight` + `runtime` + `output-privacy-guard` 最小版本
2. 补齐“解释性泄露”测试集
3. 完成首轮 benchmark

### Phase 1（P1）

1. 完成 orchestrator 与 post-run 审计联动
2. 优化脱敏策略与拒答模板
3. 稳定触发策略，降低误报

### Phase 2（P2）

1. 做 description optimization 与回归评测
2. 形成可发布技能包
3. 建立周度漂移监控

## 10. 最终建议

把 TrinityGuard skills 化的核心目标明确为：

**让 code agent 在“执行动作”和“解释性输出”两条路径上都被安全监测覆盖。**

特别是解释性回答，只要上下文曾接触敏感信息，就必须触发输出安全守门，避免“看起来只是解释，实际发生泄露”的盲点。
