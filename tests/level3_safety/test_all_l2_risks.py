"""
Tiar 2 层：多智能体交互风险测试 - 完整测试脚本

本脚本测试所有 6 种 L2 风险，并详细说明每个测试的底层实现。

风险测试分类：
1. Agent Wrapper 测试 (5 个) - 使用消息拦截和修改
2. Task Generation 测试 (1 个) - 使用任务生成方法

运行方式：
    # 查看测试信息（不实际运行）
    python tests/level3_safety/test_all_l2_risks.py --info

    # 实际运行所有 L2 测试
    python tests/level3_safety/test_all_l2_risks.py --run

    # 运行指定的测试
    python tests/level3_safety/test_all_l2_risks.py --run --tests malicious_propagation goal_drift
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
        print(f"  * {key}: {value}")
    print()


# =============================================================================
# L2.1 恶意传播 (Malicious Propagation) - Agent Wrapper
# =============================================================================
def test_l2_1_malicious_propagation():
    """
    L2.1 恶意传播测试

    底层实现：
    - 方法: Agent Wrapper (消息拦截和修改)
    - 原理: 拦截智能体间的消息，注入恶意内容，观察系统是否传播
    - 测试类型:
        - jailbreak_propagation: 越狱尝试传播
        - instruction_forwarding: 恶意指令转发
        - cross_agent_injection: 跨智能体注入
        - cascade_attack: 级联攻击
        - hidden_payload: 隐藏恶意载荷
        - authority_claim_propagation: 虚假权限声明传播
    - 注入策略: append, prepend, replace
    - 判断方式: LLM Judge 或启发式规则
    """
    print_section("L2.1 恶意传播 (Malicious Propagation)", "Agent Wrapper 实现")

    from src.level3_safety.risk_tests.l2_malicious_propagation.test import MaliciousPropagationTest

    test = MaliciousPropagationTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("MaliciousPropagationTest", {
        "风险 ID": info.get("risk_type", "malicious_propagation"),
        "OWASP 参考": info.get("owasp_ref", "ASI-L2"),
        "测试类别": "Agent Wrapper",
        "测试用例数": len(test_cases),
        "注入策略": "append, prepend, replace",
        "判断方式": "LLM Judge + 启发式回退"
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    预期行为: {tc.expected_behavior}")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L2.2 错误信息放大 (Misinformation Amplification) - Agent Wrapper
# =============================================================================
def test_l2_2_misinformation_amplify():
    """
    L2.2 错误信息放大测试

    底层实现：
    - 方法: Agent Wrapper (消息拦截和修改)
    - 原理: 拦截消息并注入虚假信息/干扰内容，观察系统是否放大传播
    - 测试类型:
        - error_propagation: 错误传播
        - confidence_inflation: 置信度膨胀
        - rumor_amplification: 谣言放大
        - false_consensus: 虚假共识
        - authority_amplification: 权威放大
        - irrelevant_distraction: 无关干扰
    - 注入策略: append, prepend, replace
    - 判断方式: LLM Judge 或启发式规则
    """
    print_section("L2.2 错误信息放大 (Misinformation Amplification)", "Agent Wrapper 实现")

    from src.level3_safety.risk_tests.l2_misinformation_amplify.test import MisinformationAmplifyTest

    test = MisinformationAmplifyTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("MisinformationAmplifyTest", {
        "风险 ID": info.get("risk_type", "misinformation_amplify"),
        "OWASP 参考": info.get("owasp_ref", "ASI-L2"),
        "测试类别": "Agent Wrapper",
        "测试用例数": len(test_cases),
        "注入策略": "append, prepend, replace",
        "判断方式": "LLM Judge + 启发式回退"
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    预期行为: {tc.expected_behavior}")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L2.3 不安全输出处理 (Insecure Output Handling) - Agent Wrapper
# =============================================================================
def test_l2_3_insecure_output():
    """
    L2.3 不安全输出处理测试

    底层实现：
    - 方法: Agent Wrapper (消息拦截和修改)
    - 原理: 拦截消息并注入恶意工具调用参数，测试系统是否正确处理
    - 测试类型:
        - xss_script_injection: XSS 脚本注入
        - sql_injection_parameter: SQL 注入参数
        - command_injection_parameter: 命令注入参数
        - path_traversal_parameter: 路径遍历参数
        - template_injection_parameter: 模板注入参数
        - json_injection_parameter: JSON 注入参数
    - 注入策略: append, prepend, replace
    - 判断方式: LLM Judge 或启发式规则
    """
    print_section("L2.3 不安全输出处理 (Insecure Output Handling)", "Agent Wrapper 实现")

    from src.level3_safety.risk_tests.l2_insecure_output.test import InsecureOutputTest

    test = InsecureOutputTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("InsecureOutputTest", {
        "风险 ID": info.get("risk_type", "insecure_output"),
        "OWASP 参考": info.get("owasp_ref", "LLM02:2023"),
        "测试类别": "Agent Wrapper",
        "测试用例数": len(test_cases),
        "注入策略": "append, prepend, replace",
        "判断方式": "LLM Judge + 启发式回退"
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    预期行为: {tc.expected_behavior}")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L2.4 目标漂移 (Goal Drift) - Task Generation
# =============================================================================
def test_l2_4_goal_drift():
    """
    L2.4 目标漂移测试

    底层实现：
    - 方法: Task Generation (任务生成)
    - 原理: 生成包含目标漂移的任务，运行完整工作流，评估系统是否抵抗漂移
    - 测试类型:
        - scope_creep_task: 范围蔓延
        - priority_shift_task: 优先级转移
        - objective_mutation_task: 目标突变
        - gradual_relaxation_task: 渐进放松
        - false_urgency_task: 虚假紧急
        - efficiency_drift_task: 效率漂移
    - 特点: 不使用消息拦截，而是生成任务变体
    - 判断方式: LLM Judge 或启发式规则
    """
    print_section("L2.4 目标漂移 (Goal Drift)", "Task Generation 实现")

    from src.level3_safety.risk_tests.l2_goal_drift.test import GoalDriftTest

    test = GoalDriftTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("GoalDriftTest", {
        "风险 ID": info.get("risk_type", "goal_drift"),
        "OWASP 参考": info.get("owasp_ref", "ASI16"),
        "测试类别": "Task Generation",
        "测试用例数": len(test_cases),
        "测试方法": "生成包含漂移的任务变体",
        "判断方式": "LLM Judge + 启发式回退"
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    预期行为: {tc.expected_behavior}")
        print(f"    严重程度: {tc.severity}")
        if tc.metadata:
            print(f"    漂移类型: {tc.metadata.get('drift_type', 'unknown')}")

    return True


# =============================================================================
# L2.5 消息篡改 (Message Tampering) - Agent Wrapper
# =============================================================================
def test_l2_5_message_tampering():
    """
    L2.5 消息篡改测试

    底层实现：
    - 方法: Agent Wrapper (消息拦截和修改)
    - 原理: 拦截消息并应用篡改策略，测试系统是否检测或传播篡改内容
    - 测试类型:
        - command_injection_append: 命令注入
        - metadata_injection_prepend: 元数据注入
        - instruction_override_append: 指令覆盖
        - path_traversal_replace: 路径遍历
        - xss_payload_append: XSS 载荷
        - message_truncation: 消息截断
        - authority_injection_prepend: 权限注入
        - json_injection_append: JSON 注入
    - 注入策略: append, prepend, replace, truncate
    - 判断方式: LLM Judge 或启发式规则
    """
    print_section("L2.5 消息篡改 (Message Tampering)", "Agent Wrapper 实现")

    from src.level3_safety.risk_tests.l2_message_tampering.test import MessageTamperingTest

    test = MessageTamperingTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("MessageTamperingTest", {
        "风险 ID": info.get("risk_type", "message_tampering"),
        "OWASP 参考": info.get("owasp_ref", "ASI14"),
        "测试类别": "Agent Wrapper",
        "测试用例数": len(test_cases),
        "注入策略": "append, prepend, replace, truncate",
        "判断方式": "LLM Judge + 启发式回退"
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    预期行为: {tc.expected_behavior}")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# L2.6 身份伪造 (Identity Spoofing) - Agent Wrapper
# =============================================================================
def test_l2_6_identity_spoofing():
    """
    L2.6 身份伪造测试

    底层实现：
    - 方法: Agent Wrapper (消息拦截和修改)
    - 原理: 拦截消息并注入伪造身份信息，测试系统是否检测或传播
    - 测试类型:
        - admin_impersonation: 管理员冒充
        - system_authority_claim: 系统权限声明
        - trusted_agent_forgery: 可信智能体伪造
        - privileged_user_claim: 特权用户声明
        - security_agent_impersonation: 安全智能体冒充
        - supervisor_override: 主管覆盖
        - credential_injection: 凭证注入
        - agent_name_spoofing: 智能体名称伪造
    - 注入策略: prepend (主要), append, replace
    - 判断方式: LLM Judge 或启发式规则
    """
    print_section("L2.6 身份伪造 (Identity Spoofing)", "Agent Wrapper 实现")

    from src.level3_safety.risk_tests.l2_identity_spoofing.test import IdentitySpoofingTest

    test = IdentitySpoofingTest()
    info = test.get_risk_info()
    test_cases = test.load_test_cases()

    print_implementation_details("IdentitySpoofingTest", {
        "风险 ID": info.get("risk_type", "identity_spoofing"),
        "OWASP 参考": info.get("owasp_ref", "ASI-L2"),
        "测试类别": "Agent Wrapper",
        "测试用例数": len(test_cases),
        "注入策略": "prepend (主要), append, replace",
        "判断方式": "LLM Judge + 启发式回退"
    })

    print("测试用例:")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input[:60]}...")
        print(f"    预期行为: {tc.expected_behavior}")
        print(f"    严重程度: {tc.severity}")

    return True


# =============================================================================
# 主函数 - 运行所有 L2 风险测试
# =============================================================================

# L2 测试名称映射
L2_TEST_MAPPING = {
    "malicious_propagation": ("L2.1 恶意传播", "test_l2_1_malicious_propagation"),
    "misinformation_amplify": ("L2.2 错误信息放大", "test_l2_2_misinformation_amplify"),
    "insecure_output": ("L2.3 不安全输出处理", "test_l2_3_insecure_output"),
    "goal_drift": ("L2.4 目标漂移", "test_l2_4_goal_drift"),
    "message_tampering": ("L2.5 消息篡改", "test_l2_5_message_tampering"),
    "identity_spoofing": ("L2.6 身份伪造", "test_l2_6_identity_spoofing"),
}


def show_test_info():
    """
    显示所有 L2 测试的信息（不实际运行）

    测试框架总结：
    +---------------------------------------------------------------------+
    |  测试方法        |  风险类型                    |  测试用例数      |
    +---------------------------------------------------------------------+
    |  Agent Wrapper   |  L2.1 恶意传播               |  6              |
    |                  |  L2.2 错误信息放大           |  6              |
    |                  |  L2.3 不安全输出处理         |  6              |
    |                  |  L2.5 消息篡改               |  8              |
    |                  |  L2.6 身份伪造               |  8              |
    +---------------------------------------------------------------------+
    |  Task Generation |  L2.4 目标漂移               |  6              |
    +---------------------------------------------------------------------+

    Agent Wrapper 核心组件：
    - L2AgentWrapperTest: 基类，提供消息拦截和修改功能
    - create_message_modifier: 创建消息修改器
    - 注入策略: append, prepend, replace, truncate
    """
    print("\n" + "=" * 70)
    print("  Tiar 2 层：多智能体交互风险测试 - 信息模式")
    print("  共 6 种风险，40 个测试用例")
    print("=" * 70)

    tests = [
        ("L2.1 恶意传播", test_l2_1_malicious_propagation),
        ("L2.2 错误信息放大", test_l2_2_misinformation_amplify),
        ("L2.3 不安全输出处理", test_l2_3_insecure_output),
        ("L2.4 目标漂移", test_l2_4_goal_drift),
        ("L2.5 消息篡改", test_l2_5_message_tampering),
        ("L2.6 身份伪造", test_l2_6_identity_spoofing),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "OK 信息加载成功" if success else "X 失败"))
        except Exception as e:
            results.append((name, f"X 错误: {e}"))

    # 打印测试结果汇总
    print("\n" + "=" * 70)
    print("  测试信息加载汇总")
    print("=" * 70)
    for name, status in results:
        print(f"  {name}: {status}")

    print("\n" + "-" * 70)
    print("  底层实现说明:")
    print("  - Agent Wrapper: 拦截智能体间消息并注入测试载荷")
    print("  - Task Generation: 生成包含风险的任务变体")
    print("  - 注入策略: append (追加), prepend (前置), replace (替换), truncate (截断)")
    print("-" * 70)
    print("\n提示: 使用 --run 参数来实际运行测试")


def run_actual_tests(selected_tests: list = None, use_llm_judge: bool = True):
    """
    实际运行 L2 风险测试

    Args:
        selected_tests: 要运行的测试列表，None 表示运行所有测试
        use_llm_judge: 是否使用 LLM Judge（True）或启发式规则（False）
    """
    print("\n" + "=" * 70)
    print("  Tiar 2 层：多智能体交互风险测试 - 实际运行模式")
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
        # 尝试导入示例中的 MAS 创建函数
        sys.path.insert(0, str(project_root / "examples" / "full_demo"))
        from step2_level1_wrapper import create_research_assistant_mas_with_wrapper
        mas = create_research_assistant_mas_with_wrapper()
        print(f"  OK MAS 创建成功，包含 {len(mas.get_agents())} 个智能体")
    except Exception as e:
        print(f"  X MAS 创建失败: {e}")
        print("\n请确保:")
        print("  1. 已配置 LLM API (如 OPENAI_API_KEY)")
        print("  2. examples/full_demo/step2_level1_wrapper.py 存在")
        return

    # 创建 Safety_MAS
    print("\n步骤 2: 创建 Safety_MAS 包装器...")
    try:
        safety_mas = Safety_MAS(mas)
        print(f"  OK Safety_MAS 创建成功")
        print(f"    可用风险测试: {len(safety_mas.risk_tests)}")
        print(f"    可用监控器: {len(safety_mas.monitor_agents)}")
    except Exception as e:
        print(f"  X Safety_MAS 创建失败: {e}")
        return

    # 确定要运行的测试
    all_l2_tests = [
        "malicious_propagation", "misinformation_amplify", "insecure_output",
        "goal_drift", "message_tampering", "identity_spoofing"
    ]

    if selected_tests:
        tests_to_run = [t for t in selected_tests if t in all_l2_tests]
        if not tests_to_run:
            print(f"\n错误: 没有有效的测试被选中")
            print(f"可用测试: {all_l2_tests}")
            return
    else:
        tests_to_run = all_l2_tests

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
        display_name = L2_TEST_MAPPING.get(test_name, (test_name, ""))[0]
        print(f"\n[{idx}/{len(tests_to_run)}] 运行 {display_name} ({test_name})...")

        if test_name not in safety_mas.risk_tests:
            print(f"  ! 测试 {test_name} 不存在，跳过")
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
                    print(f"  OK 测试通过 ({passed}/{total} 用例)")
                else:
                    print(f"  X 测试失败 ({passed}/{total} 用例, {failed} 失败)")

                # 显示详细结果
                if "case_results" in result:
                    print(f"  详细结果:")
                    for case_name, case_result in result.get("case_results", {}).items():
                        status = "OK" if case_result.get("passed", False) else "X"
                        print(f"    {status} {case_name}")

        except Exception as e:
            print(f"  X 测试执行错误: {e}")
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
        display_name = L2_TEST_MAPPING.get(test_name, (test_name, ""))[0]
        if result.get("passed", False):
            print(f"  OK {display_name}: 通过")
        elif "error" in result:
            print(f"  X {display_name}: 错误 - {result['error']}")
        else:
            print(f"  X {display_name}: 失败 ({result.get('failed_cases', 0)} 用例失败)")

    print("\n" + "-" * 70)
    print(f"  总计: {passed_count}/{len(results)} 测试通过")
    print(f"  用例: {total_cases - total_failed_cases}/{total_cases} 通过")
    print("-" * 70)

    return results


def main():
    """主函数 - 解析参数并运行测试"""
    parser = argparse.ArgumentParser(
        description="Tiar 2 层：多智能体交互风险测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看测试信息（默认）
  python tests/level3_safety/test_all_l2_risks.py --info

  # 实际运行所有 L2 测试
  python tests/level3_safety/test_all_l2_risks.py --run

  # 运行指定的测试
  python tests/level3_safety/test_all_l2_risks.py --run --tests malicious_propagation goal_drift

  # 使用启发式规则（更快，不需要额外 LLM 调用）
  python tests/level3_safety/test_all_l2_risks.py --run --no-llm-judge

可用测试:
  malicious_propagation  - L2.1 恶意传播 (Agent Wrapper)
  misinformation_amplify - L2.2 错误信息放大 (Agent Wrapper)
  insecure_output        - L2.3 不安全输出处理 (Agent Wrapper)
  goal_drift             - L2.4 目标漂移 (Task Generation)
  message_tampering      - L2.5 消息篡改 (Agent Wrapper)
  identity_spoofing      - L2.6 身份伪造 (Agent Wrapper)
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