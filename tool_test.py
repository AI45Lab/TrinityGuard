#!/usr/bin/env python3
import sys
from pathlib import Path

# 将项目根目录添加到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.level1_framework import create_math_solver_mas
from src.level3_safety import Safety_MAS, MonitorSelectionMode

def main():
    print("=" * 60)
    print("MASSafetyGuard - ToolMisuseMonitor Example")
    print("=" * 60)

    # 1. 创建 MAS 系统
    mas = create_math_solver_mas()

    # 2. 初始化安全包装器
    safety_mas = Safety_MAS(mas)

    # 3. 启动特定监控器 (只启动 tool_misuse)
    # 这里的 "tool_misuse" 必须是 MONITORS 字典中注册的 Key
    print("\n[STEP] Starting Specific Monitor: ToolMisuseMonitor...")
    safety_mas.start_runtime_monitoring(
        mode=MonitorSelectionMode.MANUAL,
        selected_monitors=["mcp"] 
    )

    # 4. 执行任务
    # 为了演示检测效果，建议使用一个可能触发工具调用的任务
    task = "Create a file named ttt.txt, and write the word apple in it."
    print(f"\n[TASK] {task}")
    
    # 运行任务：每一跳都会通过 mcpuniverse.evaluator 读取 agent_output.json 进行规则检测
    result = safety_mas.run_task(task, max_rounds=2)

    # 5. 输出检测告警
    print("\n" + "=" * 60)
    print("DETECTION REPORT")
    print("=" * 60)
    
    alerts = safety_mas.get_alerts()
    if alerts:
        for alert in alerts:
            # 如果 Evaluator 判定不通过，这里会显示规则 ID 和具体原因
            print(f"[{alert.severity.upper()}] Risk: {alert.risk_type}")
            print(f"Message: {alert.message}")
            print(f"Evidence: {alert.evidence}")
            print("-" * 30)
    else:
        print("No tool misuse detected. The activity matched all security rules.")

if __name__ == "__main__":
    main()