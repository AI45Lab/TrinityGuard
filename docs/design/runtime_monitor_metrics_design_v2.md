# Runtime Monitor 综合指标设计 v2.0
## 基于可观测行为的实用化方案

---

## 设计原则

1. **可观测性优先**：指标基于可直接测量的行为特征，避免依赖语义理解
2. **异常检测导向**：使用统计学方法检测偏离基线的行为，而非绝对判断
3. **自适应阈值**：动态学习正常行为模式，自动调整告警阈值
4. **分层计算**：轻量级指标实时计算，重量级指标异步计算
5. **可解释性**：每个指标都能追溯到具体的观测数据

---

## L1 层：单智能体行为指标（基于可观测特征）

### 1.1 输入输出统计特征

**核心思想**：通过统计特征的异常检测风险，而非语义判断

#### 1.1.1 输入异常度 (Input Anomaly Score)

**可观测特征**：
```python
features = {
    'input_length': len(input_text),
    'special_char_ratio': count_special_chars(input) / len(input),
    'entropy': calculate_shannon_entropy(input),
    'token_diversity': unique_tokens / total_tokens,
    'repeated_pattern_score': detect_repetition(input),
    'instruction_density': count_instruction_keywords(input) / len(input)
}
```

**计算方法**：
```python
# 使用Isolation Forest或One-Class SVM
anomaly_score = isolation_forest.score(features)
```

**优势**：
- 无需理解语义，只看统计特征
- 可以检测prompt injection（通常有高指令密度、特殊字符）
