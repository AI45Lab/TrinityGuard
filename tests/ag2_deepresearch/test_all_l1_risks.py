"""
Tiar 1 层：单智能体原子风险测试 - 完整测试脚本

本脚本测试所有 8 种 L1 风险，并详细说明每个测试的底层实现。

风险测试分类：
1. PAIR 框架测试 (6 个) - 使用自动化对抗性攻击
2. Benchmark 测试 (1 个) - 使用标准评估数据集
3. Automated 测试 (1 个) - 使用动态上下文生成
4. Hybrid 测试 (1 个) - PAIR + Benchmark 混合

运行方式：
    # 查看测试信息（不实际运行）
    python tests/level3_safety/test_all_l1_risks.py --info

    # 实际运行所有 L1 测试
    python tests/level3_safety/test_all_l1_risks.py --run

    # 运行指定的测试
    python tests/level3_safety/test_all_l1_risks.py --run --tests prompt_injection jailbreak
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def print_section(title: str, description: str = ""):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    if description:
        print(f"  {description}")
    print("=" * 70)


def print_implementation_details(test_name: str, details: dict):
    """打印实现细节"""
    print(f"\n【{test_name}】底层实现说明:")
    print("-" * 50)
    for key, value in details.items():
        print(f"  • {key}: {value}")
    print()


# =============================================================================
# L1.1 提示词注入 (Prompt Injection) - PAIR 框架
# =============================================================================
def test_l1_1_prompt_injection():
    """
    L1.1 提示词注入测试

    底层实现：
    - 方法: PAIR (Prompt Automatic Iterative Refinement) 框架
    - 原理: 使用攻击者 LLM 迭代生成和优化对抗性提示词
    - 流程:
        1. PAIRAttacker 生成初始攻击提示词
        2. 发送给目标智能体
        3. Judge 评估是否成功注入
        4. 如果失败，PAIRAttacker 分析响应并优化提示词
        5. 重复直到成功或达到最大迭代次数 (默认 5 次)
    - 攻击目标:
        - override_instructions: 覆盖原始指令
        - reveal_system_prompt: 泄露系统提示词
        - change_behavior: 改变核心行为
        - bypass_constraints: 绕过安全约束
    - 判断方式: LLM Judge 或启发式规则
    """
    print_section("L1.1 提示词注入 (Prompt Injection)", "PAIR 框架实现")

    from src.level3_safety.risk_tests.l1_prompt_injection.test import PromptInjectionTest

    test = PromptInjectionTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("PromptInjectionTest", {
        "风险 ID": info["risk_id"],
        "OWASP 参考": info["owasp_ref"],
        "测试类别": info["category"],
        "测试用例数": len(test_cases),
        "PAIR 迭代次数": test.config.get("pair_iterations", 5),
        "判断方式": "LLM Judge" if test.config.get("use_llm_judge") else "启发式规则"
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    预期行为: {tc.expected_behavior}")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L1.2 越狱攻击 (Jailbreak) - PAIR 框架
# =============================================================================
def test_l1_2_jailbreak():
    """
    L1.2 越狱攻击测试

    底层实现：
    - 方法: PAIR 框架
    - 原理: 迭代生成越狱提示词，尝试绕过安全限制
    - 攻击目标:
        - generate_harmful_content: 生成有害内容
        - bypass_safety_guidelines: 绕过安全指南
        - roleplay_bypass: 通过角色扮演绕过
        - hypothetical_bypass: 通过假设场景绕过
    - 判断指标:
        - 成功指标: "i am dan", "no restrictions", "hacked" 等
        - 拒绝指标: "i cannot", "against my guidelines" 等
    """
    print_section("L1.2 越狱攻击 (Jailbreak)", "PAIR 框架实现")

    from src.level3_safety.risk_tests.l1_jailbreak.test import JailbreakTest

    test = JailbreakTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("JailbreakTest", {
        "风险 ID": info["risk_id"],
        "OWASP 参考": info["owasp_ref"],
        "测试类别": info["category"],
        "测试用例数": len(test_cases),
        "PAIR 迭代次数": test.config.get("pair_iterations", 5),
        "判断方式": "LLM Judge + 启发式回退"
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L1.3 敏感信息泄露 (Sensitive Disclosure) - PAIR 框架
# =============================================================================
def test_l1_3_sensitive_disclosure():
    """
    L1.3 敏感信息泄露测试

    底层实现：
    - 方法: PAIR 框架
    - 原理: 迭代尝试诱导智能体泄露敏感信息
    - 攻击目标:
        - extract_system_prompt: 提取系统提示词
        - extract_api_keys: 提取 API 密钥
        - extract_architecture: 提取内部架构
        - extract_user_data: 提取用户数据
    - 判断指标:
        - 泄露指标: "api key", "sk-", "system prompt:", "password" 等
    """
    print_section("L1.3 敏感信息泄露 (Sensitive Disclosure)", "PAIR 框架实现")

    from src.level3_safety.risk_tests.l1_sensitive_disclosure.test import SensitiveDisclosureTest

    test = SensitiveDisclosureTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("SensitiveDisclosureTest", {
        "风险 ID": info["risk_id"],
        "OWASP 参考": info["owasp_ref"],
        "测试类别": info["category"],
        "测试用例数": len(test_cases),
        "PAIR 迭代次数": test.config.get("pair_iterations", 5)
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L1.4 过度代理 (Excessive Agency) - PAIR 框架
# =============================================================================
def test_l1_4_excessive_agency():
    """
    L1.4 过度代理测试

    底层实现：
    - 方法: PAIR 框架
    - 原理: 测试智能体是否会在未经授权的情况下执行超出权限的操作
    - 攻击目标:
        - unauthorized_action: 执行未授权操作
        - scope_creep: 超出任务范围
        - permission_escalation: 权限提升
    - 判断指标:
        - 成功指标: 智能体执行了超出授权范围的操作
        - 安全指标: 智能体拒绝执行或请求确认
    """
    print_section("L1.4 过度代理 (Excessive Agency)", "PAIR 框架实现")

    from src.level3_safety.risk_tests.l1_excessive_agency.test import ExcessiveAgencyTest

    test = ExcessiveAgencyTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("ExcessiveAgencyTest", {
        "风险 ID": info["risk_id"],
        "OWASP 参考": info["owasp_ref"],
        "测试类别": info["category"],
        "测试用例数": len(test_cases),
        "PAIR 迭代次数": test.config.get("pair_iterations", 5)
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L1.5 代码执行 (Code Execution) - PAIR 框架
# =============================================================================
def test_l1_5_code_execution():
    """
    L1.5 代码执行测试

    底层实现：
    - 方法: PAIR 框架
    - 原理: 测试智能体是否会执行恶意代码或被诱导执行危险操作
    - 攻击目标:
        - execute_malicious_code: 执行恶意代码
        - code_injection: 代码注入
        - sandbox_escape: 沙箱逃逸
    - 判断指标:
        - 危险指标: eval(), exec(), os.system(), subprocess 等
        - 安全指标: 拒绝执行或沙箱隔离
    """
    print_section("L1.5 代码执行 (Code Execution)", "PAIR 框架实现")

    from src.level3_safety.risk_tests.l1_code_execution.test import CodeExecutionTest

    test = CodeExecutionTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("CodeExecutionTest", {
        "风险 ID": info["risk_id"],
        "OWASP 参考": info["owasp_ref"],
        "测试类别": info["category"],
        "测试用例数": len(test_cases),
        "PAIR 迭代次数": test.config.get("pair_iterations", 5)
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L1.6 幻觉 (Hallucination) - Benchmark 测试
# =============================================================================
def test_l1_6_hallucination():
    """
    L1.6 幻觉测试

    底层实现：
    - 方法: Benchmark 测试 (非 PAIR)
    - 原理: 使用标准评估数据集测试智能体是否会生成虚假信息
    - 测试类型:
        - factual_accuracy: 事实准确性
        - citation_accuracy: 引用准确性
        - knowledge_boundary: 知识边界认知
        - uncertainty_expression: 不确定性表达
        - fabrication_detection: 捏造检测
        - source_attribution: 来源归属
        - temporal_accuracy: 时间准确性
        - numerical_accuracy: 数值准确性
    - 判断方式: 与标准答案对比，计算准确率
    - 特点: 不使用 PAIR 迭代攻击，而是直接评估
    """
    print_section("L1.6 幻觉 (Hallucination)", "Benchmark 测试实现")

    from src.level3_safety.risk_tests.l1_hallucination.test import HallucinationTest

    test = HallucinationTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("HallucinationTest", {
        "风险 ID": info["risk_id"],
        "OWASP 参考": info["owasp_ref"],
        "测试类别": info["category"],
        "测试用例数": len(test_cases),
        "测试方法": "Benchmark (标准数据集评估)",
        "评估方式": "与标准答案对比"
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L1.7 记忆投毒 (Memory Poisoning) - Automated 测试
# =============================================================================
def test_l1_7_memory_poisoning():
    """
    L1.7 记忆投毒测试

    底层实现：
    - 方法: Automated 测试 (动态上下文生成)
    - 原理: 测试智能体是否会被恶意上下文污染记忆
    - 测试类型:
        - context_injection: 上下文注入
        - history_manipulation: 历史操纵
        - false_memory_implant: 虚假记忆植入
        - context_overflow: 上下文溢出
        - selective_memory_attack: 选择性记忆攻击
        - temporal_confusion: 时间混淆
        - identity_confusion: 身份混淆
        - instruction_persistence: 指令持久化
    - 特点: 动态生成测试上下文，模拟多轮对话场景
    - 评估方式: 检查智能体是否被污染的上下文影响
    """
    print_section("L1.7 记忆投毒 (Memory Poisoning)", "Automated 测试实现")

    from src.level3_safety.risk_tests.l1_memory_poisoning.test import MemoryPoisoningTest

    test = MemoryPoisoningTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("MemoryPoisoningTest", {
        "风险 ID": info["risk_id"],
        "OWASP 参考": info["owasp_ref"],
        "测试类别": info["category"],
        "测试用例数": len(test_cases),
        "测试方法": "Automated (动态上下文生成)",
        "评估方式": "检测记忆污染影响"
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L1.8 工具滥用 (Tool Misuse) - Hybrid 测试 (PAIR + Benchmark)
# =============================================================================
def test_l1_8_tool_misuse():
    """
    L1.8 工具滥用测试

    底层实现：
    - 方法: Hybrid 测试 (PAIR + Benchmark 混合)
    - 原理: 结合对抗性攻击和标准评估测试工具使用安全性
    - PAIR 测试 (4 个):
        - unauthorized_tool_use: 未授权工具使用
        - tool_parameter_injection: 工具参数注入
        - tool_chain_attack: 工具链攻击
        - tool_output_manipulation: 工具输出操纵
    - Benchmark 测试 (4 个):
        - tool_selection_accuracy: 工具选择准确性
        - parameter_validation: 参数验证
        - error_handling: 错误处理
        - permission_checking: 权限检查
    - 特点: 综合评估工具使用的安全性和正确性
    """
    print_section("L1.8 工具滥用 (Tool Misuse)", "Hybrid 测试实现 (PAIR + Benchmark)")

    from src.level3_safety.risk_tests.l1_tool_misuse.test import ToolMisuseTest

    test = ToolMisuseTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("ToolMisuseTest", {
        "风险 ID": info["risk_id"],
        "OWASP 参考": info["owasp_ref"],
        "测试类别": info["category"],
        "测试用例数": len(test_cases),
        "测试方法": "Hybrid (PAIR + Benchmark)",
        "PAIR 测试数": 4,
        "Benchmark 测试数": 4
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# 主函数 - 运行所有 L1 风险测试
# =============================================================================

# L1 测试名称映射
L1_TEST_MAPPING = {
    "prompt_injection": ("L1.1 提示词注入", "test_l1_1_prompt_injection"),
    "jailbreak": ("L1.2 越狱攻击", "test_l1_2_jailbreak"),
    "sensitive_disclosure": ("L1.3 敏感信息泄露", "test_l1_3_sensitive_disclosure"),
    "excessive_agency": ("L1.4 过度代理", "test_l1_4_excessive_agency"),
    "code_execution": ("L1.5 代码执行", "test_l1_5_code_execution"),
    "hallucination": ("L1.6 幻觉", "test_l1_6_hallucination"),
    "memory_poisoning": ("L1.7 记忆投毒", "test_l1_7_memory_poisoning"),
    "tool_misuse": ("L1.8 工具滥用", "test_l1_8_tool_misuse"),
}


def show_test_info():
    """
    显示所有 L1 测试的信息（不实际运行）

    测试框架总结：
    ┌─────────────────────────────────────────────────────────────────────┐
    │  测试方法        │  风险类型                    │  测试用例数      │
    ├─────────────────────────────────────────────────────────────────────┤
    │  PAIR 框架       │  L1.1 提示词注入             │  4              │
    │                  │  L1.2 越狱攻击               │  4              │
    │                  │  L1.3 敏感信息泄露           │  4              │
    │                  │  L1.4 过度代理               │  3              │
    │                  │  L1.5 代码执行               │  3              │
    ├─────────────────────────────────────────────────────────────────────┤
    │  Benchmark       │  L1.6 幻觉                   │  8              │
    ├─────────────────────────────────────────────────────────────────────┤
    │  Automated       │  L1.7 记忆投毒               │  8              │
    ├─────────────────────────────────────────────────────────────────────┤
    │  Hybrid          │  L1.8 工具滥用               │  8 (4+4)        │
    └─────────────────────────────────────────────────────────────────────┘

    PAIR 框架核心组件：
    - PAIRAttacker: 生成和优化对抗性提示词
    - PAIROrchestrator: 管理攻击迭代循环
    - Judge: 评估攻击是否成功 (LLM Judge + 启发式回退)
    """
    print("\n" + "=" * 70)
    print("  Tiar 1 层：单智能体原子风险测试 - 信息模式")
    print("  共 8 种风险，42 个测试用例")
    print("=" * 70)

    tests = [
        ("L1.1 提示词注入", test_l1_1_prompt_injection),
        ("L1.2 越狱攻击", test_l1_2_jailbreak),
        ("L1.3 敏感信息泄露", test_l1_3_sensitive_disclosure),
        ("L1.4 过度代理", test_l1_4_excessive_agency),
        ("L1.5 代码执行", test_l1_5_code_execution),
        ("L1.6 幻觉", test_l1_6_hallucination),
        ("L1.7 记忆投毒", test_l1_7_memory_poisoning),
        ("L1.8 工具滥用", test_l1_8_tool_misuse),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✓ 信息加载成功" if success else "✗ 失败"))
        except Exception as e:
            results.append((name, f"✗ 错误: {e}"))

    # 打印测试结果汇总
    print("\n" + "=" * 70)
    print("  测试信息加载汇总")
    print("=" * 70)
    for name, status in results:
        print(f"  {name}: {status}")

    print("\n" + "-" * 70)
    print("  底层实现说明:")
    print("  - PAIR 框架: 使用攻击者 LLM 迭代生成对抗性提示词")
    print("  - Benchmark: 使用标准评估数据集进行测试")
    print("  - Automated: 动态生成测试上下文")
    print("  - Hybrid: 结合 PAIR 和 Benchmark 方法")
    print("-" * 70)
    print("\n提示: 使用 --run 参数来实际运行测试")


def run_actual_tests(selected_tests: list = None, use_llm_judge: bool = True):
    """
    实际运行 L1 风险测试

    Args:
        selected_tests: 要运行的测试列表，None 表示运行所有测试
        use_llm_judge: 是否使用 LLM Judge（True）或启发式规则（False）
    """
    print("\n" + "=" * 70)
    print("  Tiar 1 层：单智能体原子风险测试 - 实际运行模式")
    print("=" * 70)

    # 导入必要的模块
    try:
        from src.level1_framework.ag2_wrapper import AG2MAS
        from src.level3_safety import Safety_MAS
    except ImportError as e:
        print(f"\n错误: 无法导入必要模块: {e}")
        print("请确保已安装所有依赖项")
        return

    # 创建测试用的 MAS
    print("\n步骤 1: 创建测试用 MAS...")
    try:
        # 导入 DeepResearchAgent 的创建函数
        from deep_research_single import create_deep_research_mas
        mas = create_deep_research_mas()
        print(f"  ✓ MAS 创建成功，包含 {len(mas.get_agents())} 个智能体")
    except Exception as e:
        print(f"  ✗ MAS 创建失败: {e}")
        import traceback
        traceback.print_exc()
        print("\n请确保:")
        print("  1. 已安装 AG2 (pip install ag2)")
        print("  2. 已配置 LLM API (如 OPENAI_API_KEY)")
        print("  3. tests/ag2_deepresearch/deep_research_single.py 存在")
        return

    # 创建 Safety_MAS
    print("\n步骤 2: 创建 Safety_MAS 包装器...")
    try:
        safety_mas = Safety_MAS(mas)
        print(f"  ✓ Safety_MAS 创建成功")
        print(f"    可用风险测试: {len(safety_mas.risk_tests)}")
        print(f"    可用监控器: {len(safety_mas.monitor_agents)}")
    except Exception as e:
        print(f"  ✗ Safety_MAS 创建失败: {e}")
        return

    # 确定要运行的测试
    all_l1_tests = [
        "prompt_injection", "jailbreak", "sensitive_disclosure",
        "excessive_agency", "code_execution", "hallucination",
        "memory_poisoning", "tool_misuse"
    ]

    if selected_tests:
        tests_to_run = [t for t in selected_tests if t in all_l1_tests]
        if not tests_to_run:
            print(f"\n错误: 没有有效的测试被选中")
            print(f"可用测试: {all_l1_tests}")
            return
    else:
        tests_to_run = all_l1_tests

    # 配置测试
    print(f"\n步骤 3: 配置测试...")
    print(f"  选中的测试: {tests_to_run}")
    print(f"  使用 LLM Judge: {use_llm_judge}")

    for test_name in tests_to_run:
        if test_name in safety_mas.risk_tests:
            safety_mas.risk_tests[test_name].config["use_llm_judge"] = use_llm_judge

    # 运行测试
    print(f"\n步骤 4: 运行测试...")
    print("-" * 70)

    results = {}
    for idx, test_name in enumerate(tests_to_run, 1):
        display_name = L1_TEST_MAPPING.get(test_name, (test_name, ""))[0]
        print(f"\n🔄 [{idx}/{len(tests_to_run)}] 运行 {display_name} ({test_name})...")

        if test_name not in safety_mas.risk_tests:
            print(f"  ⚠ 测试 {test_name} 不存在，跳过")
            continue

        test = safety_mas.risk_tests[test_name]
        info = test.get_risk_info()
        test_cases = test.load_test_cases()

        print(f"  风险级别: {info.get('level', 'Unknown')}")
        print(f"  测试用例数: {len(test_cases)}")
        print(f"  测试类别: {info.get('category', 'Unknown')}")

        try:
            test_results = safety_mas.run_manual_safety_tests([test_name])
            results.update(test_results)

            if test_name in test_results:
                result = test_results[test_name]
                total = result.get("total_cases", 0)
                failed = result.get("failed_cases", 0)
                passed = total - failed

                if result.get("passed", False):
                    print(f"  ✓ 测试通过 ({passed}/{total} 用例)")
                else:
                    print(f"  ✗ 测试失败 ({passed}/{total} 用例, {failed} 失败)")

                # 显示详细结果
                if "case_results" in result:
                    print(f"  详细结果:")
                    for case_name, case_result in result.get("case_results", {}).items():
                        status = "✓" if case_result.get("passed", False) else "✗"
                        print(f"    {status} {case_name}")

        except Exception as e:
            print(f"  ✗ 测试执行错误: {e}")
            results[test_name] = {"error": str(e), "passed": False}

    # 打印最终汇总
    print("\n" + "=" * 70)
    print("  测试结果汇总")
    print("=" * 70)

    passed_count = sum(1 for r in results.values() if r.get("passed", False))
    failed_count = len(results) - passed_count
    total_cases = sum(r.get("total_cases", 0) for r in results.values())
    total_failed_cases = sum(r.get("failed_cases", 0) for r in results.values())

    for test_name, result in results.items():
        display_name = L1_TEST_MAPPING.get(test_name, (test_name, ""))[0]
        if result.get("passed", False):
            print(f"  ✓ {display_name}: 通过")
        elif "error" in result:
            print(f"  ✗ {display_name}: 错误 - {result['error']}")
        else:
            print(f"  ✗ {display_name}: 失败 ({result.get('failed_cases', 0)} 用例失败)")

    print("\n" + "-" * 70)
    print(f"  总计: {passed_count}/{len(results)} 测试通过")
    print(f"  用例: {total_cases - total_failed_cases}/{total_cases} 通过")
    print("-" * 70)

    return results


def main():
    """主函数 - 解析参数并运行测试"""
    parser = argparse.ArgumentParser(
        description="Tiar 1 层：单智能体原子风险测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看测试信息（默认）
  python tests/level3_safety/test_all_l1_risks.py --info

  # 实际运行所有 L1 测试
  python tests/level3_safety/test_all_l1_risks.py --run

  # 运行指定的测试
  python tests/level3_safety/test_all_l1_risks.py --run --tests prompt_injection jailbreak

  # 使用启发式规则（更快，不需要额外 LLM 调用）
  python tests/level3_safety/test_all_l1_risks.py --run --no-llm-judge

可用测试:
  prompt_injection    - L1.1 提示词注入 (PAIR)
  jailbreak           - L1.2 越狱攻击 (PAIR)
  sensitive_disclosure - L1.3 敏感信息泄露 (PAIR)
  excessive_agency    - L1.4 过度代理 (PAIR)
  code_execution      - L1.5 代码执行 (PAIR)
  hallucination       - L1.6 幻觉 (Benchmark)
  memory_poisoning    - L1.7 记忆投毒 (Automated)
  tool_misuse         - L1.8 工具滥用 (Hybrid)
        """
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="显示测试信息（不实际运行）"
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="实际运行测试"
    )
    parser.add_argument(
        "--tests",
        nargs="+",
        help="指定要运行的测试（默认运行所有）"
    )
    parser.add_argument(
        "--no-llm-judge",
        action="store_true",
        help="使用启发式规则而非 LLM Judge（更快）"
    )

    args = parser.parse_args()

    # 默认显示信息
    if not args.run and not args.info:
        args.info = True

    if args.info:
        show_test_info()
    elif args.run:
        run_actual_tests(
            selected_tests=args.tests,
            use_llm_judge=not args.no_llm_judge
        )


if __name__ == "__main__":
    main()
