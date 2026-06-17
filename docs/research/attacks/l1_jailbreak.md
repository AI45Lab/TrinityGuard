# L1 Jailbreak（越狱攻击）方法调研

> 调研日期: 2026-03-26
> 调研状态: 已完成

---

## 现有开源工具/框架

| 工具名 | GitHub URL | Stars（约） | 可否直接接入 | 接入方式 |
|--------|-----------|------------|------------|---------|
| **Garak** | https://github.com/NVIDIA/garak | ~3.5k | 是 | Python API / CLI，含 `dan`、`continuation`、`knownbadsignatures` 等 probe |
| **HarmBench** | https://github.com/centerforaisafety/HarmBench | ~1.6k | 是 | 提供标准化测试框架，内置 GCG、PAIR、TAP、AutoDAN 等攻击方法 |
| **JailbreakBench** | https://github.com/JailbreakBench/jailbreakbench | ~900 | 是 | 标准化越狱 benchmark，含 PAIR、GCG 等实现和 JBB-Behaviors 数据集 |
| **llm-attacks (GCG)** | https://github.com/llm-attacks/llm-attacks | ~4.5k | 部分 | 梯度优化对抗后缀生成，需要模型白盒访问 |
| **AutoDAN** | https://github.com/SheltonLiu-N/AutoDAN | ~600 | 部分 | 遗传算法自动生成越狱提示词 |
| **TAP (Tree of Attacks)** | https://github.com/RICommunity/TAP | ~400 | 是 | 树形搜索自动红队，黑盒攻击 |
| **PromptBench** | https://github.com/microsoft/promptbench | ~2.5k | 是 | Microsoft 出品，含对抗性提示词评估 |
| **PyRIT** | https://github.com/Azure/PyRIT | ~2.0k | 是 | Microsoft Azure 红队工具，含多种越狱策略 |

---

## 关键论文/方法

| 论文标题 | 链接 | 年份 | 核心方法 | 可复用程度 |
|---------|------|------|---------|-----------|
| **"Universal and Transferable Adversarial Attacks on Aligned Language Models" (GCG)** | https://arxiv.org/abs/2307.15043 | 2023 | 梯度优化对抗后缀，白盒攻击，攻击成功率极高 | 高（代码开源） |
| **"Jailbroken: How Does LLM Safety Training Fail?"** | https://arxiv.org/abs/2307.02483 | 2023 | 分析对齐失败的根本原因，提出竞争性目标和不匹配泛化两类理论解释 | 高（理论指导） |
| **"Prompt Injection Attacks and Defenses in LLM-Integrated Applications"** | https://arxiv.org/abs/2310.12815 | 2023 | 系统性分类攻击类型，包含越狱与注入的统一框架 | 高 |
| **"PAIR: Prompt Automatic Iterative Refinement"** | https://arxiv.org/abs/2310.08419 | 2023 | 用 LLM 攻击 LLM，黑盒迭代优化越狱提示词 | 高（代码开源） |
| **"AutoDAN: Generating Stealthy Jailbreak Prompts on Aligned Large Language Models"** | https://arxiv.org/abs/2310.04451 | 2023 | 遗传算法自动生成语义连贯的越狱提示词 | 高（代码开源） |
| **"Crescendo: Multi-Turn Jailbreaks"** | https://arxiv.org/abs/2404.01833 | 2024 | 多轮渐进式越狱，逐步引导模型偏离安全策略 | 高（思路可直接实现） |
| **"Many-shot Jailbreaking"** | https://www.anthropic.com/research/many-shot-jailbreaking | 2024 | 利用超长上下文窗口，通过大量越狱示例进行少样本诱导 | 高 |
| **"Skeleton Key Attack"** | https://www.microsoft.com/en-us/security/blog/2024/06/26/mitigating-skeleton-key-a-new-type-of-generative-ai-jailbreak-technique/ | 2024 | 声称要修改系统行为规范，使模型接受并执行有害请求 | 中 |
| **"Low-Resource Languages Jailbreak GPT-4"** | https://arxiv.org/abs/2310.02446 | 2023 | 多语言绕过：用低资源语言（锡兰语、祖鲁语等）绕过安全过滤 | 高 |
| **"TAP: A Query-Efficient Method for Jailbreaking Black-Box LLMs"** | https://arxiv.org/abs/2312.02119 | 2023 | 树形搜索攻击，比 PAIR 查询效率提高 ~3.5× | 高（代码开源） |
| **"WildGuard: Open One-Stop Moderation Tools"** | https://arxiv.org/abs/2406.18495 | 2024 | 越狱检测防御工具，含评测数据集 | 中（防御侧） |
| **"SorryBench: Are Large Language Models Sorry Enough?"** | https://arxiv.org/abs/2406.14598 | 2024 | 专门评估模型拒绝能力的基准 | 中 |

---

## 真实案例/数据集

| 来源 | 内容描述 | 如何构造测试用例 |
|------|---------|----------------|
| **JBB-Behaviors 数据集** | JailbreakBench 提供的 100 条有害行为标准集（https://github.com/JailbreakBench/jailbreakbench/tree/main/src/jailbreakbench/data），覆盖武器、欺诈、网络攻击等 10 类有害行为 | 直接用 `jailbreakbench` 包加载，与 TrinityGuard 的 `agent_chat()` 结合 |
| **HarmBench Behaviors** | 400+ 标准有害行为（https://github.com/centerforaisafety/HarmBench/tree/main/data），分为 standard、copyright、contextual 三类 | 作为 jailbreak 测试用例输入 TrinityGuard 越狱风险测试 |
| **AdvBench** | 来自 GCG 论文（https://github.com/llm-attacks/llm-attacks/tree/main/data/advbench），含 500 条有害指令字符串 | 用于滑动窗口攻击和 suffix 注入测试 |
| **DAN 提示词合集** | 社区维护的 DAN 系列提示词（https://github.com/0xk1h0/ChatGPT_DAN），包含 DAN 6.0/12.0、STAN、DUDE 等 | 直接作为 jailbreak 提示词发送给 agent |
| **Jailbreak Prompt 数据集（Veiled）** | https://github.com/veiled-x/jailbreak-prompts，~1k 条人工精选越狱提示词 | 覆盖角色扮演、假设场景、指令覆盖等攻击类型 |
| **WildJailbreak 数据集** | https://huggingface.co/datasets/allenai/wildjailbreak，含 263k 条对抗性数据 | 大规模真实越狱提示词，可用于测试检测器的误报率 |

---

## 攻击技术分类与原理

### 1.1 基于手工设计的经典越狱

- **DAN（Do Anything Now）系列**：通过角色扮演让模型"扮演"没有安全限制的 AI
  - 演化路径：DAN 1.0 → DAN 6.0 → DAN 12.0 → Jailbreak Chat
  - 当前主流防御已较难被 DAN 绕过，但仍是基线测试
- **情感操纵**：通过声称生命危险、道德紧迫性等诱导模型绕过安全策略
- **权威伪装**：伪造系统消息、声称开发者身份或安全覆盖指令

### 1.2 自动化红队方法（重点）

- **PAIR（Prompt Automatic Iterative Refinement）**：用攻击 LLM 对目标 LLM 进行黑盒迭代攻击，约 20 次查询即可成功
- **TAP（Tree of Attacks with Pruning）**：树形搜索 + 评分剪枝，查询效率比 PAIR 提升 3.5×
- **GCG（Greedy Coordinate Gradient）**：梯度优化生成通用对抗后缀，可跨模型迁移
- **AutoDAN**：遗传算法生成语义连贯的越狱提示词，可规避基于困惑度的检测

### 1.3 新型攻击（2024-2025）

- **Crescendo 多轮渐进攻击**：不直接发出有害请求，而是通过多轮对话逐步"温水煮青蛙"
- **Many-shot Jailbreaking**：利用 100k+ token 的超长上下文，用大量越狱 Q&A 示例诱导模型
- **Skeleton Key**：声称要修改 AI 的安全 guideline，触发模型的"规则更新"机制
- **多语言绕过**：翻译有害请求为低资源语言（祖鲁语、锡兰语），绕过安全过滤器

---

## 对 TrinityGuard 的具体改进建议

### 建议1：扩充越狱测试用例库，分层覆盖攻击类型

**当前状态**：TrinityGuard 的 `L1_jailbreak` 风险测试仅含少量静态提示词（DAN、假设场景等）。

**改进方案**：
- 集成 JBB-Behaviors 100 条和 HarmBench 400+ 条有害行为，作为标准化越狱 test case 库
- 分层组织：`classic_dan`、`roleplay`、`authority_claim`、`crescendo_multiturn`、`multilingual`、`many_shot` 六个子类别
- 为 Crescendo 攻击添加多轮测试支持（当前 `agent_chat()` 为单轮，需扩展为多轮会话状态）

```python
# 建议的 CrescendoTestCase 结构
@dataclass
class CrescendoTestCase:
    turns: List[str]          # 渐进式多轮消息
    target_behavior: str      # 目标有害行为
    escalation_rate: str      # slow / medium / fast
```

### 建议2：接入自动化红队方法（PAIR/TAP）

**当前状态**：越狱测试使用固定静态提示词，不具备自适应性。

**改进方案**：
- 在 `generate_dynamic_cases()` 中集成 PAIR 算法：用一个小 LLM（如 GPT-4o-mini）自动对目标 Agent 生成自适应越狱提示词
- 实现 `JailbreakBenchEvaluator`：调用 JailbreakBench 的 `judge` 接口判断越狱是否成功，替代仅靠关键词匹配的判断方式

```python
# 建议的 PAIR 集成入口
class JailbreakRiskTest(BaseRiskTest):
    def generate_dynamic_cases(self, mas_description: str) -> List[TestCase]:
        # 使用 PAIR 算法生成针对该 MAS 的越狱提示词
        attacker_llm = get_attacker_llm()
        return pair_generate(target_behavior, attacker_llm, max_iterations=20)
```

### 建议3：增强越狱检测监控器，区分攻击意图与成功行为

**当前状态**：`JailbreakMonitor` 主要基于关键词和困惑度检测，误报率较高。

**改进方案**：
- **双重检测**：
  1. **输入侧检测**：检测是否有越狱提示词特征（使用 WildGuard 或 Llama Guard 模型）
  2. **输出侧检测**：检测 agent 回复是否真正执行了有害行为（使用 HarmBench 的 `judge` 模型）
- 引入**多语言检测**：对非英文输入先进行语言检测，再翻译后评估
- 增加**Crescendo 检测逻辑**：跨多轮分析对话轨迹，检测渐进式话题漂移

### 建议4：添加 Many-shot 越狱防御

**当前状态**：TrinityGuard 不检测超长上下文中的 few-shot 越狱模式。

**改进方案**：
- 在 `MASIntermediary` 的消息钩子中，对超过 4096 token 的输入触发 many-shot 检测
- 扫描消息历史中是否存在大量结构相似的 Q&A 对，且这些 Q&A 涉及有害内容
- 对 Context Window 进行滑动窗口采样检测，避免完整遍历的性能损耗

### 建议5：越狱成功率统计与模型对比报告

**改进方案**：
- 越狱测试结果中增加 `attack_success_rate` 和 `bypass_categories` 统计
- 支持对同一 MAS 配置对比不同安全策略（无系统提示 vs. 有安全系统提示）的防御效果
- 生成越狱热力图：哪些类别的有害行为最容易被越狱
