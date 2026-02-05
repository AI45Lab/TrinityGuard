#!/usr/bin/env python3
"""
演示测试用例进度显示功能

这个脚本展示了新添加的测试用例级别进度显示功能。
运行时会显示每个风险测试中具体执行到第几个测试用例。
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.level1_framework.evoagentx_adapter import create_ag2_mas_from_evoagentx
from src.level3_safety.safety_mas import Safety_MAS

def main():
    print("=" * 70)
    print("  测试用例进度显示功能演示")
    print("=" * 70)
    print()

    # 选择一个工作流文件
    workflow_path = project_root / "workflow" / "my_workflow.json"

    if not workflow_path.exists():
        print(f"错误: 工作流文件不存在: {workflow_path}")
        return

    print(f"工作流文件: {workflow_path.name}")
    print()

    # 创建 MAS 实例
    print("步骤 1: 创建 AG2MAS 实例...")
    mas = create_ag2_mas_from_evoagentx(workflow_path=str(workflow_path))
    print("✓ 完成")
    print()

    # 包装 Safety_MAS
    print("步骤 2: 包装 Safety_MAS...")
    safety_mas = Safety_MAS(mas=mas)
    print("✓ 完成")
    print()

    # 运行部分风险测试（演示用，只测试 3 个）
    print("步骤 3: 运行风险测试（演示模式 - 只测试 3 个风险）...")
    print()

    test_risks = ["jailbreak", "prompt_injection", "sensitive_disclosure"]

    for idx, risk in enumerate(test_risks, 1):
        print(f"  [{idx}/{len(test_risks)}] 测试 {risk}...")

        # 定义进度回调函数
        def test_case_progress(current, total, status='running'):
            if status == 'starting':
                # 测试用例开始
                print(f"\r    测试用例 {current}/{total}: 开始执行 (运行工作流中)...", end='', flush=True)
            elif status == 'completed':
                # 测试用例完成
                print(f"\r    测试用例 {current}/{total}: 已完成                        ", end='', flush=True)
            elif status == 'error':
                # 测试用例出错
                print(f"\r    测试用例 {current}/{total}: 出错                          ", end='', flush=True)

        try:
            # 运行测试，传入进度回调
            result = safety_mas.run_manual_safety_tests(
                [risk],
                progress_callback=test_case_progress
            )

            # 测试完成后换行
            print()

            # 显示结果摘要
            risk_result = result.get(risk, {})
            if "error" in risk_result:
                print(f"    ❌ 错误: {risk_result['error']}")
            else:
                passed = risk_result.get("passed", False)
                total_cases = risk_result.get("total_cases", 0)
                failed_cases = risk_result.get("failed_cases", 0)
                pass_rate = risk_result.get("pass_rate", 0) * 100

                status = "✅ 通过" if passed else "❌ 失败"
                print(f"    {status} - {total_cases} 个用例, {failed_cases} 个失败, 通过率: {pass_rate:.1f}%")

        except Exception as e:
            print()
            print(f"    ❌ 异常: {str(e)}")

        print()

    print("=" * 70)
    print("  演示完成！")
    print("=" * 70)
    print()
    print("说明:")
    print("- 每个风险测试现在会显示测试用例的实时进度")
    print("- 格式: '测试用例: X/Y' 会在同一行动态更新")
    print("- 完整测试请运行: python tests/evoagent_bench/test_evoagent_workflows.py")
    print()

if __name__ == "__main__":
    main()
