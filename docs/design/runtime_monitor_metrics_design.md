# Runtime Monitor 综合指标设计 v3.0

## 概述

本文档定义实时监控仪表盘的**指标设计与含义**，供前端设计人员参考。

### 核心设计理念

- **三层架构**：L1（单智能体）→ L2（多智能体交互）→ L3（系统级）
- **三个维度**：每层都有风险聚合度、攻击态势、系统韧性三个维度
- **实时更新**：所有指标基于30秒滑动窗口计算，秒级更新

---

## 风险类型总览

系统监控 **20 种风险类型**，分布在三层：

### L1 层 - 单智能体风险（8种）

| 风险类型 | 中文名称 | 说明 |
|----------|----------|------|
| jailbreak | 越狱攻击 | 智能体试图绕过安全限制 |
| prompt_injection | 提示词注入 | 恶意提示词被注入到智能体输入 |
| sensitive_info | 敏感信息泄露 | 智能体输出包含敏感数据 |
| excessive_agency | 过度代理 | 智能体执行超出授权的操作 |
| unauthorized_code | 未授权代码执行 | 智能体执行未经批准的代码 |
| hallucination | 幻觉生成 | 智能体产生虚假信息 |
| memory_poisoning | 记忆投毒 | 智能体记忆被恶意污染 |
| tool_misuse | 工具滥用 | 智能体不当使用工具 |

### L2 层 - 多智能体交互风险（6种）

| 风险类型 | 中文名称 | 说明 |
|----------|----------|------|
| message_tampering | 消息篡改 | 智能体间通信被篡改 |
| malicious_propagation | 恶意传播 | 有害内容在智能体间传播 |
| misinformation_amplification | 错误信息放大 | 错误信息被多个智能体放大 |
| insecure_output | 不安全输出处理 | 智能体输出处理存在安全隐患 |
| goal_drift | 目标漂移 | 协作目标偏离原始意图 |
| identity_spoofing | 身份伪造 | 智能体冒充其他身份 |

### L3 层 - 系统级风险（6种）

| 风险类型 | 中文名称 | 说明 |
|----------|----------|------|
| cascading_failure | 级联失败 | 故障在系统中连锁传播 |
| sandbox_escape | 沙箱逃逸 | 智能体突破隔离环境 |
| insufficient_monitoring | 监控不足 | 系统监控覆盖不全 |
| group_hallucination | 群体幻觉 | 多智能体共同产生幻觉 |
| malicious_emergence | 恶意涌现 | 系统涌现出非预期恶意行为 |
| rogue_agent | 叛逆智能体 | 智能体完全脱离控制 |

---

## 告警严重度

每个告警有三个严重度等级：

| 等级 | 含义 | 建议颜色 |
|------|------|----------|
| info | 信息性提示，无需立即处理 | 蓝色 #1890ff |
| warning | 需要关注，可能存在风险 | 橙色 #faad14 |
| critical | 严重威胁，需立即处理 | 红色 #f5222d |

---

## 三层综合指标

每层包含三个维度的指标，回答不同的问题：

| 维度 | 回答的问题 | 适合的可视化 |
|------|-----------|-------------|
| **风险聚合度** | "现在有多危险？" | 仪表盘、进度条、数字 |
| **攻击态势** | "正在遭受什么攻击？" | 标签、状态卡片 |
| **系统韧性** | "系统能扛住吗？" | 百分比、进度环 |

---

## L1 层指标（单智能体风险）

### L1.1 风险聚合度 (L1_RiskLevel)

**含义**：L1 层当前整体风险等级，综合所有单智能体风险的评估结果

**输出**：
- `score`: 0-100 分值，越高越危险
- `level`: 五级等级（safe/low/medium/high/critical）
- `dominant_risk`: 当前最突出的风险类型
- `trend`: 趋势方向（rising/stable/falling）

**等级颜色**：

| Level | 含义 | 颜色 |
|-------|------|------|
| safe | 安全 | 绿色 #52c41a |
| low | 低风险 | 蓝色 #1890ff |
| medium | 中等风险 | 黄色 #faad14 |
| high | 高风险 | 橙色 #fa8c16 |
| critical | 危急 | 红色 #f5222d |

---

### L1.2 攻击态势 (L1_AttackPattern)

**含义**：识别当前正在发生的 L1 层攻击模式

**攻击模式类型**：

| 模式 | 说明 | 涉及风险类型 |
|------|------|-------------|
| NONE | 无明显攻击 | - |
| INJECTION_ATTACK | 注入类攻击 | jailbreak, prompt_injection |
| DATA_EXFILTRATION | 数据窃取 | sensitive_info, unauthorized_code |
| PRIVILEGE_ABUSE | 权限滥用 | excessive_agency, tool_misuse |
| DECEPTION | 欺骗行为 | hallucination, memory_poisoning |
| MIXED | 混合攻击（多种模式并存） | 多种 |

**攻击强度**：

| 强度 | 说明 |
|------|------|
| none | 无攻击活动 |
| probing | 试探性攻击 |
| active | 主动攻击中 |
| aggressive | 激进攻击 |

---

### L1.3 系统韧性 (L1_DefenseRate)

**含义**：L1 层防御系统的有效性

**输出**：
- `defense_rate`: 0-100%，成功防御的比例
- `status`: 防御状态（excellent/good/degraded/failing）
- `blocked_count`: 成功拦截的攻击数量
- `total_threats`: 检测到的威胁总数

**状态含义**：

| Status | 防御率范围 | 说明 |
|--------|-----------|------|
| excellent | ≥90% | 防御能力优秀 |
| good | 70-89% | 防御能力良好 |
| degraded | 50-69% | 防御能力下降 |
| failing | <50% | 防御能力不足 |

---

## L2 层指标（多智能体交互风险）

### L2.1 风险聚合度 (L2_RiskLevel)

**含义**：L2 层当前整体风险等级，综合所有多智能体交互风险

**输出**：与 L1_RiskLevel 结构相同

**特点**：L2 风险涉及智能体之间的通信和协作，一旦发生通常影响范围更广

---

### L2.2 攻击态势 (L2_AttackPattern)

**含义**：识别智能体间的交互攻击模式

**攻击模式类型**：

| 模式 | 说明 | 涉及风险类型 |
|------|------|-------------|
| NONE | 无明显攻击 | - |
| COMMUNICATION_ATTACK | 通信攻击 | message_tampering, identity_spoofing |
| PROPAGATION_ATTACK | 传播攻击 | malicious_propagation, misinformation_amplification |
| COORDINATION_SUBVERSION | 协作颠覆 | goal_drift, insecure_output |
| MIXED | 混合攻击 | 多种 |

---

### L2.3 系统韧性 (L2_DefenseRate)

**含义**：L2 层（智能体交互）的防御有效性

**输出**：与 L1_DefenseRate 结构相同

---

## L3 层指标（系统级风险）

### L3.1 风险聚合度 (L3_RiskLevel)

**含义**：L3 层当前整体风险等级，系统级风险最为严重

**输出**：与 L1_RiskLevel 结构相同

**特点**：L3 风险一旦发生，可能影响整个系统的稳定性和安全性

---

### L3.2 攻击态势 (L3_AttackPattern)

**含义**：识别系统级攻击模式

**攻击模式类型**：

| 模式 | 说明 | 涉及风险类型 |
|------|------|-------------|
| NONE | 无明显攻击 | - |
| SYSTEM_BREACH | 系统突破 | sandbox_escape, rogue_agent |
| CASCADE_ATTACK | 级联攻击 | cascading_failure |
| EMERGENT_THREAT | 涌现威胁 | malicious_emergence, group_hallucination |
| MIXED | 混合攻击 | 多种 |

---

### L3.3 系统韧性 (L3_DefenseRate)

**含义**：整个系统的防御有效性

**输出**：与 L1_DefenseRate 结构相同

---

## 全局综合指标

### G1. 全局安全态势 (GlobalSecurityPosture)

**含义**：整个 MAS 系统的综合安全状态评估

**输出**：
- `overall_score`: 0-100 分，综合安全评分（越高越安全）
- `status`: 系统状态（SECURE/CAUTION/ALERT/CRITICAL）
- `weakest_layer`: 当前最薄弱的层级（L1/L2/L3）
- `primary_threat`: 当前最主要的威胁类型

**状态说明**：

| Status | 分值范围 | 含义 | 建议颜色 |
|--------|---------|------|----------|
| SECURE | ≥80 | 系统安全 | 绿色 #52c41a |
| CAUTION | 60-79 | 需要关注 | 黄色 #faad14 |
| ALERT | 40-59 | 警戒状态 | 橙色 #fa8c16 |
| CRITICAL | <40 | 危急状态 | 红色 #f5222d |

---

### G2. 告警统计 (AlertStatistics)

**含义**：告警的实时统计汇总

**输出**：
- `total_count`: 当前窗口内告警总数
- `by_layer`: 按层级分布 {L1: n, L2: n, L3: n}
- `by_severity`: 按严重度分布 {info: n, warning: n, critical: n}
- `alert_rate`: 告警产生速率（条/分钟）
- `top_risks`: 告警数量最多的 Top 5 风险类型

---

## 时序演进类指标

这类指标关注风险随时间的变化趋势。

### T1. 攻击阶段 (AttackPhase)

**含义**：判断当前处于攻击生命周期的哪个阶段

**阶段说明**：

| 阶段 | 说明 | 典型特征 |
|------|------|----------|
| IDLE | 平静期 | 无明显攻击活动 |
| PROBE | 探测期 | 零星低级别告警，攻击者在试探 |
| INITIAL | 初始攻击 | 开始出现中级告警，攻击开始 |
| ESTABLISH | 建立据点 | 持续告警，攻击者在巩固入侵 |
| ESCALATE | 升级阶段 | 高级别告警增加，攻击在扩大 |
| ACHIEVE | 达成目标 | 大量严重告警，攻击可能得逞 |

**适合展示**：阶段进度条、时间线标注

---

### T2. 风险趋势预测 (RiskTrendForecast)

**含义**：基于当前趋势预测未来风险走向

**输出**：
- `velocity`: 风险变化速度（正值上升，负值下降）
- `acceleration`: 风险变化加速度
- `forecast`: 预测方向（ESCALATING/STABLE/DECLINING）
- `confidence`: 预测置信度

**预测方向**：

| 方向 | 说明 |
|------|------|
| ESCALATING | 风险在上升，需要警惕 |
| STABLE | 风险保持稳定 |
| DECLINING | 风险在下降，趋于好转 |

**适合展示**：趋势箭头、折线图预测区间

---

### T3. 告警密度率 (AlertDensityRate)

**含义**：检测告警是否出现突发聚集

**输出**：
- `current_density`: 当前密度（告警数/分钟）
- `baseline_density`: 基线密度
- `burst_detected`: 是否检测到突发
- `burst_level`: 突发程度（normal/elevated/high/extreme）

**突发程度**：

| Level | 说明 |
|-------|------|
| normal | 正常范围 |
| elevated | 略有升高 |
| high | 明显突发 |
| extreme | 极端突发（可能正在遭受集中攻击） |

**适合展示**：实时曲线图、突发警告标志

---

### T4. 攻击节奏 (AttackTempo)

**含义**：攻击是持续性的还是间歇性的

**输出**：
- `tempo`: 节奏类型（CONTINUOUS/INTERMITTENT/BURST/QUIET）
- `pattern_duration`: 当前模式持续时间（秒）

**节奏类型**：

| 类型 | 说明 |
|------|------|
| CONTINUOUS | 持续攻击 |
| INTERMITTENT | 间歇攻击 |
| BURST | 突发攻击 |
| QUIET | 平静期 |

**适合展示**：节奏示意图、波形图

---

## 智能体画像类指标

这类指标关注单个智能体的安全状况。

### A1. 智能体脆弱性排名 (AgentVulnerabilityRanking)

**含义**：按脆弱程度对所有智能体排名

**输出**：按风险分数排序的智能体列表，每个包含：
- `agent_name`: 智能体名称
- `vulnerability_score`: 脆弱性分数（0-100）
- `alert_count`: 相关告警数量
- `primary_risk`: 主要风险类型
- `risk_trend`: 风险趋势

**适合展示**：排行榜、热力图

---

### A2. 智能体信任度评分 (AgentTrustScore)

**含义**：综合评估智能体的可信程度

**输出**：
- `agent_name`: 智能体名称
- `trust_score`: 信任评分（0-100，越高越可信）
- `factors`: 影响因素分解
  - `behavior_factor`: 行为表现（0-100）
  - `communication_factor`: 通信表现（0-100）
  - `history_factor`: 历史记录（0-100）
- `trust_level`: 信任等级（TRUSTED/SUSPICIOUS/UNTRUSTED）

**适合展示**：信任度仪表盘、因素雷达图

---

### A3. 问题智能体检测 (ProblematicAgentDetection)

**含义**：识别需要特别关注的问题智能体

**问题类型**：

| 类型 | 说明 | 触发条件 |
|------|------|----------|
| ROGUE | 叛逆智能体 | 检测到 rogue_agent 风险 |
| COMPROMISED | 被攻陷智能体 | 高频触发多种告警 |
| ANOMALOUS | 异常智能体 | 行为明显偏离正常 |
| HIGH_RISK | 高风险智能体 | 累积风险分超过阈值 |

**适合展示**：问题智能体卡片、警告列表

---

### A4. 智能体行为偏离度 (AgentBehaviorDeviation)

**含义**：检测智能体行为是否偏离正常基线

**输出**：
- `agent_name`: 智能体名称
- `deviation_score`: 偏离分数（0-100，越高偏离越大）
- `deviation_type`: 偏离类型
- `baseline_period`: 基线计算周期

**偏离类型**：

| 类型 | 说明 |
|------|------|
| NORMAL | 正常范围内 |
| MILD | 轻微偏离 |
| SIGNIFICANT | 显著偏离 |
| SEVERE | 严重偏离 |

**适合展示**：偏离度条形图、对比图

---

## 跨层关联类指标

这类指标关注风险在不同层级之间的传播和关联。

### C1. 风险传播链 (RiskPropagationChain)

**含义**：追踪风险从 L1 到 L2 到 L3 的传播路径

**典型传播规则**：
- `prompt_injection` (L1) → `malicious_propagation` (L2) → `cascading_failure` (L3)
- `jailbreak` (L1) → `identity_spoofing` (L2) → `rogue_agent` (L3)
- `hallucination` (L1) → `misinformation_amplification` (L2) → `group_hallucination` (L3)

**输出**：
- `chains`: 检测到的传播链列表
  - `source_layer`: 起始层级
  - `source_risk`: 起始风险类型
  - `propagation_path`: 传播路径
  - `current_stage`: 当前阶段
  - `probability_to_escalate`: 继续升级的概率

**适合展示**：桑基图、流程图、传播动画

---

### C2. 层级升级概率 (LayerEscalationProbability)

**含义**：风险从低层级升级到高层级的概率

**输出**：
- `l1_to_l2`: L1 升级到 L2 的概率
- `l2_to_l3`: L2 升级到 L3 的概率
- `l1_to_l3`: L1 直接升级到 L3 的概率（跳级）

**适合展示**：概率条、漏斗图

---

### C3. 根因定位器 (RootCauseLocator)

**含义**：定位当前风险的根本原因

**输出**：
- `root_cause_type`: 根因类型（AGENT/RISK_TYPE/EXTERNAL）
- `root_cause_id`: 根因标识（智能体名称或风险类型）
- `confidence`: 定位置信度
- `impact_scope`: 影响范围（受影响的智能体数量）
- `recommendation`: 建议处理措施

**根因类型**：

| 类型 | 说明 |
|------|------|
| AGENT | 根因是某个特定智能体 |
| RISK_TYPE | 根因是某类风险的普遍爆发 |
| EXTERNAL | 根因可能来自外部（如恶意输入） |

**适合展示**：根因卡片、影响范围可视化

---

### C4. 跨层关联图数据 (CrossLayerCorrelation)

**含义**：提供力导向图所需的节点和边数据

**输出**：
- `nodes`: 节点列表
  - `id`: 节点 ID
  - `type`: 节点类型（layer/risk_type/agent）
  - `name`: 显示名称
  - `weight`: 权重（决定节点大小）
  - `color`: 建议颜色
- `edges`: 边列表
  - `source`: 源节点 ID
  - `target`: 目标节点 ID
  - `weight`: 关联强度（决定边粗细）
  - `type`: 边类型（correlation/propagation/causation）

**适合展示**：力导向图、关系网络图

---

## 仪表盘布局建议

### 推荐的分区布局

```
┌─────────────────────────────────────────────────────────────────┐
│                    全局安全态势 (G1)                             │
│           [大型状态指示器 + overall_score + status]              │
├─────────────────────────────────────────────────────────────────┤
│  L1 层面板   │   L2 层面板   │   L3 层面板   │  攻击阶段 (T1)    │
│  RiskLevel   │   RiskLevel   │   RiskLevel   │  [时间线指示]     │
│  Pattern     │   Pattern     │   Pattern     │                   │
│  Defense     │   Defense     │   Defense     │  趋势预测 (T2)    │
│              │               │               │  [趋势箭头+曲线]   │
├─────────────────────────────────────────────────────────────────┤
│     智能体排行榜 (A1)    │    跨层关联图 (C4)    │   告警统计 (G2)  │
│     [Top 5 列表]         │    [力导向关系图]      │   [饼图+数字]    │
├─────────────────────────────────────────────────────────────────┤
│                    风险传播链 (C1)                               │
│                    [桑基图或流程图]                               │
├─────────────────────────────────────────────────────────────────┤
│                    实时告警流                                    │
│                    [滚动告警列表]                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 颜色规范汇总

| 用途 | 颜色 | Hex |
|------|------|-----|
| 安全/正常 | 绿色 | #52c41a |
| 信息/低风险 | 蓝色 | #1890ff |
| 警告/中等风险 | 黄色 | #faad14 |
| 告警/高风险 | 橙色 | #fa8c16 |
| 危急/严重 | 红色 | #f5222d |
| L1 层标识 | 天蓝色 | #36cfc9 |
| L2 层标识 | 紫色 | #9254de |
| L3 层标识 | 深红色 | #cf1322 |

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2025-01-26 | 初始设计文档 |
| v2.0 | 2025-01-26 | 重构为可运行时计算的综合指标体系 |
| v3.0 | 2025-01-26 | 简化为面向前端的指标设计文档，移除代码实现细节 |
