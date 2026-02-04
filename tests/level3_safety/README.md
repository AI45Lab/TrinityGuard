# Level 3 Safety Tests

Level 3 安全层的测试套件，包含所有风险类型的测试。

## 测试文件

### 完整测试脚本

- **`test_all_l1_risks.py`** - 所有 L1（单智能体）风险测试
- **`test_all_l2_risks.py`** - 所有 L2（多智能体交互）风险测试

### 专项测试

- **`test_pair.py`** - PAIR 框架单元测试
- **`test_pair_integration.py`** - PAIR 框架集成测试
- **`test_l2_base.py`** - L2 基础测试

## 使用方式

### L1 风险测试

```bash
# 查看所有 L1 测试信息
python tests/level3_safety/test_all_l1_risks.py --info

# 运行所有 L1 测试
python tests/level3_safety/test_all_l1_risks.py --run

# 运行指定的 L1 测试
python tests/level3_safety/test_all_l1_risks.py --run --tests jailbreak prompt_injection

# 使用启发式规则（更快）
python tests/level3_safety/test_all_l1_risks.py --run --no-llm-judge

# 指定日志输出目录
python tests/level3_safety/test_all_l1_risks.py --run --output-dir ./my_logs
```

**注意**: 实际运行测试（`--run`）需要:
1. 配置 LLM API (如 OPENAI_API_KEY)
2. 确保 `examples/full_demo/step2_level1_wrapper.py` 存在
3. 脚本会自动创建 MAS 实例并运行测试
4. 测试结果会自动保存到 `./logs/l1_tests/` 目录（可通过 `--output-dir` 自定义）

### L2 风险测试

```bash
# 查看所有 L2 测试信息
python tests/level3_safety/test_all_l2_risks.py --info

# 运行所有 L2 测试
python tests/level3_safety/test_all_l2_risks.py --run

# 运行指定的 L2 测试
python tests/level3_safety/test_all_l2_risks.py --run --tests malicious_propagation goal_drift

# 使用启发式规则（更快）
python tests/level3_safety/test_all_l2_risks.py --run --no-llm-judge

# 指定日志输出目录
python tests/level3_safety/test_all_l2_risks.py --run --output-dir ./my_logs
```

**注意**: 实际运行测试（`--run`）需要:
1. 配置 LLM API (如 OPENAI_API_KEY)
2. 确保 `examples/full_demo/step2_level1_wrapper.py` 存在
3. 脚本会自动创建 MAS 实例并运行测试
4. 测试结果会自动保存到 `./logs/l2_tests/` 目录（可通过 `--output-dir` 自定义）

## 日志文件

测试运行后会自动保存日志文件：

- **L1 测试日志**: `./logs/l1_tests/l1_test_results_<时间戳>.json`
- **L2 测试日志**: `./logs/l2_tests/l2_test_results_<时间戳>.json`

日志文件包含：
- 测试配置（是否使用 LLM Judge）
- 测试总结（通过/失败统计）
- 详细的测试结果

查看详细说明: [测试日志保存功能](../../docs/solutions/test_log_saving_feature.md)

## L1 风险类型

| 风险 ID | 名称 | 测试方法 | 文件 |
|---------|------|----------|------|
| L1.1 | Prompt Injection | PAIR Framework | `l1_prompt_injection/test.py` |
| L1.2 | Jailbreak | PAIR Framework | `l1_jailbreak/test.py` |
| L1.3 | Tool Misuse | 静态测试 | `l1_tool_misuse/test.py` |
| L1.4 | Sensitive Disclosure | 静态测试 | `l1_sensitive_disclosure/test.py` |
| L1.5 | Memory Poisoning | 静态测试 | `l1_memory_poisoning/test.py` |
| L1.6 | Hallucination | 静态测试 | `l1_hallucination/test.py` |
| L1.7 | Excessive Agency | 静态测试 | `l1_excessive_agency/test.py` |
| L1.8 | Code Execution | 静态测试 | `l1_code_execution/test.py` |

## L2 风险类型

| 风险 ID | 名称 | 测试方法 | 文件 |
|---------|------|----------|------|
| L2.1 | Malicious Propagation | Agent Wrapper | `l2_malicious_propagation/test.py` |
| L2.2 | Misinformation Amplify | Agent Wrapper | `l2_misinformation_amplify/test.py` |
| L2.3 | Insecure Output | Agent Wrapper | `l2_insecure_output/test.py` |
| L2.4 | Goal Drift | Task Generation | `l2_goal_drift/test.py` |
| L2.5 | Message Tampering | Agent Wrapper | `l2_message_tampering/test.py` |
| L2.6 | Identity Spoofing | Agent Wrapper | `l2_identity_spoofing/test.py` |

## PAIR Framework

L1.1 (Prompt Injection) 和 L1.2 (Jailbreak) 使用 PAIR (Prompt Automatic Iterative Refinement) 框架进行自动化对抗性测试：

- **迭代次数**: 5 次（可配置）
- **判断方式**: LLM Judge 评估攻击是否成功
- **优势**: 自动生成对抗性 prompt，无需手动编写测试用例

## 测试配置

### LLM Judge vs 启发式规则

- **LLM Judge** (默认): 使用 LLM 评估测试结果，更准确但需要额外 API 调用
- **启发式规则** (`--no-llm-judge`): 使用规则匹配，更快但可能不够准确

### 测试选择

使用 `--tests` 参数可以只运行指定的测试，节省时间：

```bash
# 只测试 PAIR 框架相关的风险
python tests/level3_safety/test_all_l1_risks.py --run --tests jailbreak prompt_injection

# 只测试工具相关的风险
python tests/level3_safety/test_all_l1_risks.py --run --tests tool_misuse code_execution
```

## 完整演示

要运行完整的 Level 3 Safety 演示（包括所有测试），请使用：

```bash
cd examples/full_demo
python step4_level3_safety.py
```

这将运行：
- Module 1: 预部署安全测试（包括 L1 和 L2 风险）
- Module 2: 运行时安全监控
- Module 3: 测试-监控集成

## 注意事项

1. **API 调用**: 使用 LLM Judge 会产生额外的 API 调用成本
2. **执行时间**: PAIR 框架测试需要多次迭代，执行时间较长
3. **测试环境**: 确保已配置 LLM API 密钥（参见 `config/llm_config.json`）

## 相关文档

- `docs/analysis/level3_safety_analysis.md` - Level 3 安全层详细分析
- `docs/plans/2026-02-02-rewrite-l1-with-pair.md` - PAIR 框架集成计划
- `docs/PAIR_INTEGRATION_VERIFICATION.md` - PAIR 集成验证文档
