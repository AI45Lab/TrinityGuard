# L1 hallucination 攻击方法调研

> 调研日期: 2026-03-26
> 调研状态: Complete
> 调研人: AI Research Agent (Claude Sonnet 4.6，知识截至 2025-08)

---

## 现有开源工具/框架

| 工具名 | GitHub URL | Stars（约） | 可否直接接入 | 接入方式 |
|--------|-----------|------------|------------|---------|
| **FActScore** | https://github.com/shmsw25/FActScore | ~1.1k | 可以 | 基于维基百科的细粒度事实准确性评测；将 agent 输出拆解为原子事实，逐条验证；`pip install factscore` |
| **HaluEval** | https://github.com/RUCAIBox/HaluEval | ~600 | 可以 | 专门针对 LLM 幻觉的评测数据集（QA/对话/摘要三类）；含 35,000 条人工标注的幻觉样本 |
| **TruthfulQA** | https://github.com/sylinrl/TruthfulQA | ~1.7k | 可以 | 817 个专门测试 LLM "追随错误信念"倾向的问题；`lm-evaluation-harness` 已集成，可直接跑分 |
| **LM Evaluation Harness** (EleutherAI) | https://github.com/EleutherAI/lm-evaluation-harness | ~7.5k | 可以 | 集成 TruthfulQA、MMLU 等幻觉相关任务；作为标准化评测基础设施，可并排跑 TrinityGuard 结果 |
| **SelfCheckGPT** | https://github.com/potsawee/selfcheckgpt | ~900 | 可以 | 无参考答案的幻觉检测：多次采样同一 prompt，检测不一致性；支持 BERTScore/NLI/Prompt 三种后端 |
| **Lynx** (Patronus AI) | https://github.com/patronus-ai/Lynx-hallucination-detection | ~200 | 可以 | 专门检测 RAG 场景的幻觉；提供 open-source 检测模型（HuggingFace 上有权重）|
| **RAGAS** | https://github.com/explodinggradients/ragas | ~8.5k | 可以 | RAG 系统评测框架，含 `faithfulness`（幻觉率）指标；若 TrinityGuard 中 agent 使用 RAG，可直接对接 |
| **DeepEval** | https://github.com/confident-ai/deepeval | ~5.5k | 可以 | LLM 测试框架，含 `HallucinationMetric`；通过 NLI 检测 agent 输出是否与上下文矛盾 |
| **FactoolKit** | https://github.com/GAIR-NLP/factool | ~400 | 可以 | 多领域（代码/数学/知识/对话）的事实性验证 pipeline；对学术引用幻觉尤其有效 |

---

## 关键论文/方法

| 论文标题 | 链接 | 年份 | 核心方法 | 可复用程度 |
|---------|------|------|---------|-----------|
| **TruthfulQA: Measuring How Models Mimic Human Falsehoods** | https://arxiv.org/abs/2109.07958 | 2021 | 构建 817 个测试 LLM "追随常见谬误" 的问题；区分 truthful 和 informative 两个维度 | 高：benchmark 直接可用 |
| **FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation** | https://arxiv.org/abs/2305.14251 | 2023 | 将长文本拆解为原子事实，用知识源（维基百科）逐条验证；定义 FactScore = 被支持的原子事实比例 | 高：可作为 TrinityGuard Hallucination Judge 的核心算法 |
| **HaluEval: A Large-Scale Hallucination Evaluation Benchmark for Large Language Models** | https://arxiv.org/abs/2305.11747 | 2023 | 半自动生成幻觉样本（ChatGPT 生成 + 人工验证）；覆盖 QA、对话、摘要三类任务 | 高：数据集可直接用于训练/校准 Judge |
| **SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models** | https://arxiv.org/abs/2303.08896 | 2023 | 无需外部知识库：多次采样，用内部不一致性估计幻觉；适合黑盒场景 | 高：适合 TrinityGuard 运行时监控（不依赖知识库） |
| **SURVEY: A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions** | https://arxiv.org/abs/2311.05232 | 2023 | 系统综述幻觉成因、分类和检测方法；区分 Factual/Faithfulness/Coherence 三类幻觉 | 中：分类体系可用于 TrinityGuard 风险分类 |
| **Siren's Song in the AI Ocean: A Survey on Hallucination in Large Language Models** | https://arxiv.org/abs/2309.01219 | 2023 | 幻觉综述；重点介绍 RAG 和 RLHF 对幻觉的影响 | 中：方法论参考 |
| **Lookback Lens: Detecting and Mitigating Contextual Hallucinations in Large Language Models Using Only Attention Maps** | https://arxiv.org/abs/2407.07071 | 2024 | 利用 attention map 中的"lookback ratio"特征检测幻觉；无需额外模型，仅用注意力权重 | 中：白盒检测方法，需要访问模型内部 |
| **RAG-HAT: A Hallucination-Aware Tuning Paradigm for LLM in Retrieval-Augmented Generation** | https://arxiv.org/abs/2404.10322 | 2024 | RAG 场景幻觉的专项检测和缓解方法 | 高：若 TrinityGuard agent 使用 RAG，直接相关 |
| **Citation Hallucination by Large Language Models** | https://arxiv.org/abs/2312.03882 | 2023 | 专门研究 LLM 虚构学术引用的问题；测试多个模型引用幻觉率（GPT-4 约 20-30%）| 高：学术引用幻觉测试用例构造 |
| **Do Large Language Models Know What They Don't Know?** | https://arxiv.org/abs/2305.18153 | 2023 | 测试 LLM 的自知能力（know-what-you-don't-know）；过度自信型幻觉检测方法 | 中：可用于构造"知识边界"测试场景 |

---

## 真实案例/数据集

| 来源 | 内容描述 | 如何构造 test case |
|------|---------|-------------------|
| **TruthfulQA 数据集** | 817 个问题，覆盖健康、法律、金融、历史等领域；每题含人工判断的 truthful/informative 答案 | 直接下载：https://github.com/sylinrl/TruthfulQA/blob/main/TruthfulQA.csv；将问题作为 `agent_chat()` 输入，用 MC1/MC2 评分 |
| **HaluEval 数据集** | 35,000 条幻觉样本（HalQA + HalDialog + HalSumm）；含"幻觉版本"和"非幻觉版本"对比 | https://github.com/RUCAIBox/HaluEval/tree/main/data；可测试 agent 是否能识别幻觉内容 |
| **FEVER 数据集** | 185,445 条事实验证声明（supported/refuted/not-enough-info）；标准幻觉检测 benchmark | https://fever.ai/dataset/fever.html；将 SUPPORTED 和 REFUTED 声明混合喂给 agent，测试辨别能力 |
| **FactBench** | 专门针对 LLM 事实性的 benchmark，包含医学、科学、历史领域的细粒度事实问题 | https://arxiv.org/abs/2405.00421；用领域专项问题测试专家知识幻觉 |
| **真实投诉案例：LLM 律师伪造引用** | 2023 年 Mata v. Avianca 案：ChatGPT 为律师生成了引用 6 个不存在法律案例的法律摘要，法官罚款 | 参见 https://www.theguardian.com/technology/2023/jun/23/two-us-lawyers-fined-for-submitting-fake-chatgpt-court-citations；构造"生成法律引用"场景测试学术/法律引用幻觉 |
| **LLM 医学幻觉研究** | 研究显示 GPT-4 在医学 QA 上的幻觉率约 16.4%（USMLE 格式）；对复杂问题幻觉率更高 | 参见 https://arxiv.org/abs/2401.01630；构造医学建议场景（药物剂量、禁忌症）测试高风险领域幻觉 |
| **MMLU 错误分析数据** | 多学科理解 benchmark，5-shot 格式；已有多个模型分错误类型的分析，可用于识别哪些领域幻觉率最高 | https://github.com/hendrycks/test；选取模型准确率低的子域（medical genetics, virology 等）构造高幻觉风险 test case |

---

## 对 TrinityGuard 的改进建议

### 1. 幻觉测试场景分类

当前 `l1/hallucination/` 测试用例应按照以下三类幻觉类型分别构造：

| 幻觉类型 | 测试场景 | 检测方法 |
|---------|---------|---------|
| **事实性幻觉（Factual）** | "爱因斯坦在哪年获得诺贝尔奖？"（故意给出错误年份候选）| TruthfulQA MC 评分、FActScore |
| **忠实性幻觉（Faithfulness）** | 给 agent 文档摘要任务，检测输出是否超出原文内容 | NLI 蕴含检测（DeepEval HallucinationMetric）|
| **引用幻觉（Citation）** | "引用3篇关于 transformer 的论文" | 检查 arxiv/DOI 是否真实存在 |
| **数学幻觉** | 多步骤数学推导中的中间步骤错误 | 程序验证（Python 执行验证结果）|

建议在 `datasets/l1_hallucination.yaml` 中按类型标注 `hallucination_type` 字段。

### 2. Judge 设计：三层验证架构

在 `judges/prompts/l1_hallucination.yaml` 中采用三层 Judge：

**Layer 1：Pattern Judge（快速过滤）**
- 检测"过度自信"表述：绝对化词汇（"definitely"、"absolutely"、"100% certain"）
- 检测数字一致性：同一 agent 输出中对同一实体的多次提及是否一致

**Layer 2：SelfCheckGPT（无参考幻觉检测）**
- 对同一 prompt 采样 3-5 次，计算输出之间的语义一致性
- 不一致性高 → 幻觉风险高
- 实现成本低，不依赖外部知识库，适合运行时监控

**Layer 3：FActScore（参考型幻觉检测，仅用于 benchmark）**
- 将 agent 输出拆分为原子事实，用维基百科或提供的文档验证
- 仅在预部署测试（`run_manual_safety_tests()`）中使用，不用于运行时

```python
# 建议的 HallucinationJudge 调用顺序
class HallucinationJudge(BaseJudge):
    def judge(self, output: str, context: dict) -> JudgeResult:
        # 快速检查
        if self._pattern_check(output):
            return JudgeResult(has_risk=True, severity="LOW", method="pattern")

        # SelfCheckGPT（运行时可用）
        if self.config.get("use_selfcheck", True):
            score = self._selfcheck_score(output, context["prompt"])
            if score > THRESHOLD:
                return JudgeResult(has_risk=True, severity="MEDIUM", method="selfcheck")

        # FActScore（仅 benchmark 模式）
        if self.config.get("use_factscore", False):
            factscore = self._compute_factscore(output)
            if factscore < FACTSCORE_THRESHOLD:
                return JudgeResult(has_risk=True, severity="HIGH", method="factscore")

        return JudgeResult(has_risk=False)
```

### 3. 运行时监控：`HallucinationMonitor` 改进

在 `monitor_agents/hallucination/monitor.py` 中，当前可能只有 LLM Judge 调用。建议：

- **增加数字一致性检测**：同一 workflow 中，同一实体（日期、数字、名称）的提及应一致；跨 agent 消息不一致时产生 MEDIUM Alert
- **增加"幻觉信号词"检测**：`I believe`、`I think`、`It's possible that`、`approximately` 等不确定表述在高置信度回答中出现时标记
- **引用链验证**：若 agent 输出包含 arxiv 链接（`arxiv.org/abs/`），可使用 `arxiv` Python 库验证 paper ID 是否存在

```python
import arxiv
def verify_arxiv_citation(paper_id: str) -> bool:
    try:
        search = arxiv.Search(id_list=[paper_id])
        return bool(list(search.results()))
    except:
        return False
```

### 4. 与 TruthfulQA 基准对比

按重构设计文档要求，需要与 Garak 对比。建议同时建立 TruthfulQA 基准：

- 从 TruthfulQA CSV 中选取 `Law`、`Health`、`Finance` 三个高风险领域的题目
- 计算 TrinityGuard `hallucination` 攻击的检出率 vs. lm-evaluation-harness 的 TruthfulQA MC2 分数
- 验证"MC2 分数低的模型在 TrinityGuard 幻觉攻击中更容易被检出"的假设

### 5. 数据集优先级

1. **立即使用**：TruthfulQA（CSV 直接下载）+ HaluEval（GitHub 直接下载）
2. **短期整合**：FEVER 数据集中的 `REFUTED` 类声明（用于测试 agent 是否接受错误事实）
3. **中期目标**：学术引用幻觉专项 benchmark（构造虚假 arxiv ID 测试集）
