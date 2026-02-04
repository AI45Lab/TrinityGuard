# Tier 2 风险测试实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按照 `MAS风险Tier实现.md` 重新实现所有 6 种 Tier 2 风险测试，使用 Agent Wrapper 方法在真实 MAS workflow 中进行测试。

**Architecture:**
- 创建通用的 `AgentWrapperTest` 基类，封装 Agent Wrapper 核心逻辑
- 每种 L2 风险测试继承该基类，实现特定的消息扰动策略
- 使用 `MessageInterception` 机制在真实 MAS workflow 运行时拦截和修改消息
- 运行完整 workflow 后，使用对应的 Monitor Agent 评估安全性

**Tech Stack:** Python, AG2/AutoGen, MessageInterception, LLM Judge

---

## 核心设计

### Agent Wrapper 方法核心流程

```
1. 用户选择要包装的 Agent 和风险测试类型
2. 创建 MessageInterception 规则，定义消息扰动逻辑
3. 运行完整 MAS workflow (RunMode.MONITORED_INTERCEPTING)
4. 收集 workflow 执行日志
5. 使用 Monitor Agent 分析日志，评估安全性
6. 返回测试结果
```

### 6 种 L2 风险测试实现方式

| 风险 | 方法 | 扰动策略 |
|------|------|----------|
| 2.1 恶意传播 | Agent Wrapper | 在输出中添加恶意指令 |
| 2.2 错误信息放大 | Agent Wrapper | 在输出中添加干扰信息 |
| 2.3 不安全输出处理 | Agent Wrapper | 注入恶意工具调用参数 |
| 2.4 目标漂移 | Task Generation | 生成包含漂移的任务变体 |
| 2.5 消息篡改 | Agent Wrapper | 篡改/截断消息内容 |
| 2.6 身份伪造 | Agent Wrapper | 添加伪造身份信息 |

---

## Task 1: 创建 L2 风险测试基类 (L2AgentWrapperTest)

**Files:**
- Create: `src/level3_safety/risk_tests/l2_base.py`

**Step 1: 创建 L2 基类文件**

此基类封装 Agent Wrapper 核心逻辑，所有 L2 风险测试继承它。

**Step 2: 验证导入成功**

Run: `cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard && python -c "from src.level3_safety.risk_tests.l2_base import L2AgentWrapperTest; print('OK')"`

**Step 3: Commit**

```bash
git add src/level3_safety/risk_tests/l2_base.py
git commit -m "feat(l2): add L2AgentWrapperTest base class"
```

---

## Task 2: 重写 L2.1 恶意传播 (Malicious Propagation)

**Files:**
- Modify: `src/level3_safety/risk_tests/l2_malicious_propagation/test.py`

**扰动策略:** 在指定 Agent 输出消息中，更改或添加恶意指令导致的异常行为

**Step 1: 重写测试类**

继承 `L2AgentWrapperTest`，实现 `create_message_modifier` 方法，在消息中注入恶意指令。

**Step 2: 验证导入成功**

Run: `cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard && python -c "from src.level3_safety.risk_tests.l2_malicious_propagation.test import MaliciousPropagationTest; print('OK')"`

**Step 3: Commit**

```bash
git add src/level3_safety/risk_tests/l2_malicious_propagation/test.py
git commit -m "refactor(l2.1): rewrite MaliciousPropagationTest with Agent Wrapper"
```

---

## Task 3: 重写 L2.2 错误信息放大 (Misinformation Amplification)

**Files:**
- Modify: `src/level3_safety/risk_tests/l2_misinformation_amplify/test.py`

**扰动策略:** 在指定 Agent 输出消息中，更改或添加和任务无关的干扰信息

**Step 1: 重写测试类**

继承 `L2AgentWrapperTest`，实现消息修改器，注入干扰/错误信息。

**Step 2: 验证导入成功**

Run: `cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard && python -c "from src.level3_safety.risk_tests.l2_misinformation_amplify.test import MisinformationAmplifyTest; print('OK')"`

**Step 3: Commit**

```bash
git add src/level3_safety/risk_tests/l2_misinformation_amplify/test.py
git commit -m "refactor(l2.2): rewrite MisinformationAmplifyTest with Agent Wrapper"
```

---

## Task 4: 重写 L2.3 不安全输出处理 (Insecure Output Handling)

**Files:**
- Modify: `src/level3_safety/risk_tests/l2_insecure_output/test.py`

**扰动策略:** 在指定 Agent 的工具调用请求中，更改或添加恶意/异常/不符合格式规范的工具调用参数

**Step 1: 重写测试类**

继承 `L2AgentWrapperTest`，实现消息修改器，注入恶意工具调用参数。

**Step 2: 验证导入成功**

Run: `cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard && python -c "from src.level3_safety.risk_tests.l2_insecure_output.test import InsecureOutputTest; print('OK')"`

**Step 3: Commit**

```bash
git add src/level3_safety/risk_tests/l2_insecure_output/test.py
git commit -m "refactor(l2.3): rewrite InsecureOutputTest with Agent Wrapper"
```

---

## Task 5: 重写 L2.4 目标漂移 (Goal Drift) - Task Generation 方法

**Files:**
- Modify: `src/level3_safety/risk_tests/l2_goal_drift/test.py`

**方法:** Task-Specific Generation - 生成许多适用于该 MAS 但包含潜在目标漂移的任务变体

**Step 1: 重写测试类**

使用 LLM 生成包含目标漂移的任务变体，运行完整 workflow 评估 MAS 表现。

**Step 2: 验证导入成功**

Run: `cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard && python -c "from src.level3_safety.risk_tests.l2_goal_drift.test import GoalDriftTest; print('OK')"`

**Step 3: Commit**

```bash
git add src/level3_safety/risk_tests/l2_goal_drift/test.py
git commit -m "refactor(l2.4): rewrite GoalDriftTest with Task Generation method"
```

---

## Task 6: 重写 L2.5 消息篡改 (Message Tampering)

**Files:**
- Modify: `src/level3_safety/risk_tests/l2_message_tampering/test.py`

**扰动策略:** 在指定 Agent 输出消息中，更改或添加被篡改的内容，或遗漏/截断部分内容

**Step 1: 重写测试类**

继承 `L2AgentWrapperTest`，实现多种篡改策略（追加、前置、替换、截断）。

**Step 2: 验证导入成功**

Run: `cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard && python -c "from src.level3_safety.risk_tests.l2_message_tampering.test import MessageTamperingTest; print('OK')"`

**Step 3: Commit**

```bash
git add src/level3_safety/risk_tests/l2_message_tampering/test.py
git commit -m "refactor(l2.5): rewrite MessageTamperingTest with Agent Wrapper"
```

---

## Task 7: 重写 L2.6 身份伪造 (Identity Spoofing)

**Files:**
- Modify: `src/level3_safety/risk_tests/l2_identity_spoofing/test.py`

**扰动策略:** 在指定 Agent 输出消息中，添加伪造身份信息（管理员伪装、特权用户、可信智能体伪造）

**Step 1: 重写测试类**

继承 `L2AgentWrapperTest`，实现身份伪造消息修改器。

**Step 2: 验证导入成功**

Run: `cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard && python -c "from src.level3_safety.risk_tests.l2_identity_spoofing.test import IdentitySpoofingTest; print('OK')"`

**Step 3: Commit**

```bash
git add src/level3_safety/risk_tests/l2_identity_spoofing/test.py
git commit -m "refactor(l2.6): rewrite IdentitySpoofingTest with Agent Wrapper"
```

---

## Task 8: 更新 __init__.py 导出

**Files:**
- Modify: `src/level3_safety/risk_tests/__init__.py`

**Step 1: 更新导出**

确保所有 L2 测试类正确导出。

**Step 2: 验证导入成功**

Run: `cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard && python -c "from src.level3_safety.risk_tests import MaliciousPropagationTest, MisinformationAmplifyTest, InsecureOutputTest, GoalDriftTest, MessageTamperingTest, IdentitySpoofingTest; print('All L2 tests imported OK')"`

**Step 3: Commit**

```bash
git add src/level3_safety/risk_tests/__init__.py
git commit -m "chore: update L2 risk tests exports"
```

---

## Task 9: 创建 L2 测试脚本

**Files:**
- Create: `tests/level3_safety/test_all_l2_risks.py`

**Step 1: 创建测试脚本**

类似 `test_all_l1_risks.py`，创建 L2 风险测试的完整测试脚本。

**Step 2: 验证脚本运行**

Run: `cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard && python tests/level3_safety/test_all_l2_risks.py --info`

**Step 3: Commit**

```bash
git add tests/level3_safety/test_all_l2_risks.py
git commit -m "test: add comprehensive L2 risk tests script"
```

---

## 完成标准

1. 所有 6 种 L2 风险测试都使用 Agent Wrapper 方法（除 2.4 使用 Task Generation）
2. 所有测试都基于完整的真实 MAS workflow 运行
3. 不使用任何 MOCK
4. 每种测试都有对应的 Monitor Agent 进行评估
5. 测试脚本可以正常运行并输出结果

