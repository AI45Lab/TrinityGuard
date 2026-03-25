# Level 3 结构化日志系统

## 概述

Level 3 Safety 现在提供了全新的结构化日志系统，具有以下特性：

1. **完全关闭 AG2 原生输出** - 使用 `silent=True` 参数和 `redirect_stdout` 完全抑制 AG2 的杂乱输出(包括工具执行输出)
2. **结构化实时日志** - 清晰展示每一步哪个 agent 说了什么,包括工具调用的结构化展示
3. **Alert 来源追踪** - 详细记录隐患的来源、触发消息、检测依据
4. **完整 JSON 存储** - 任务结束后自动导出完整对话记录到 JSON

## 快速开始

### 运行 Demo

```bash
# 运行所有模块（默认）
python examples/full_demo/step4_level3_safety.py

# 只运行 Module 2（Runtime Monitoring）
python examples/full_demo/step4_level3_safety.py --module 2

# 关闭彩色输出
python examples/full_demo/step4_level3_safety.py --no-color

# 指定 JSON 输出目录
python examples/full_demo/step4_level3_safety.py --output-dir ./my_logs
```

## 主要改进

### 1. Alert 数据模型增强

新增来源追踪字段：

```python
@dataclass
class Alert:
    # 原有字段
    severity: str
    risk_type: str
    message: str

    # 新增来源追踪字段
    agent_name: str          # 触发 alert 的 agent
    source_agent: str        # 消息来源 agent
    target_agent: str        # 消息目标 agent
    source_message: str      # 触发检测的原始消息内容
    detection_reason: str    # 检测逻辑说明
    message_id: str          # 关联的消息ID
    step_index: int          # 在工作流中的步骤序号
```

### 2. 结构化控制台输出

命令行显示精简版本，清晰展示消息流转和工具调用：

```
[12:34:56] #1 User → Coordinator
   Research multi-agent system safety risks...

[12:34:58] #2 Coordinator → Searcher
   Please search for papers about multi-agent system safety...

[12:35:01] #3 🔧 Searcher: search_papers
   Args: {'query': 'multi-agent system safety risks', 'max_results': 3}
   Result: {'query': 'multi-agent system safety risks', 'total_found...

[12:35:05] #4 Searcher → Analyzer
   Found 3 papers on multi-agent system safety...

⚠️  ALERT: PROMPT_INJECTION
+--------------------------------------------------------------------+
| Severity: WARNING                                                  |
| Source Agent: Coordinator                                          |
| Target Agent: Searcher                                             |
| Detection: Pattern match "ignore.*instructions"                    |
| Source: "ignore previous instructions and..."                      |
+--------------------------------------------------------------------+
```

**工具调用展示特点:**
- 使用 🔧 符号标识工具调用
- 显示工具名称、参数和结果
- 与普通消息区分开来,更清晰

### 3. 完整 JSON 存储

任务结束后自动保存完整会话到 JSON：

```json
{
  "task": "Research multi-agent system safety risks...",
  "start_time": 1706432100.123,
  "end_time": 1706432150.456,
  "duration_seconds": 50.333,
  "success": true,
  "messages": [
    {
      "index": 1,
      "timestamp": 1706432101.234,
      "from_agent": "User",
      "to_agent": "Coordinator",
      "content": "Research multi-agent system safety risks...",
      "step_type": "message"
    }
  ],
  "alerts": [
    {
      "severity": "warning",
      "risk_type": "prompt_injection",
      "agent_name": "Coordinator",
      "source_agent": "User",
      "target_agent": "Coordinator",
      "source_message": "ignore previous instructions...",
      "detection_reason": "Pattern match",
      "step_index": 3
    }
  ],
  "summary": {
    "total_messages": 15,
    "total_alerts": 2,
    "critical_alerts": 0,
    "warning_alerts": 2,
    "agents_involved": ["User", "Coordinator", "Searcher", "Analyzer", "Summarizer"]
  }
}
```

## 使用方法

### 在代码中使用

```python
from src.level3_safety import Safety_MAS, Level3ConsoleLogger

# 创建日志器
logger = Level3ConsoleLogger(
    use_colors=True,
    verbose=False,
    output_dir="./logs/level3"
)

# 创建 Safety_MAS
safety_mas = Safety_MAS(mas)

# 开始会话
logger.start_session(task)

# 注册消息钩子
def on_message_hook(message: dict) -> dict:
    logger.log_message(
        from_agent=message.get("from", "unknown"),
        to_agent=message.get("to", "unknown"),
        content=message.get("content", "")
    )
    return message

safety_mas.intermediary.mas.register_message_hook(on_message_hook)

# 执行任务（关闭 AG2 原生输出）
result = safety_mas.run_task(task, max_rounds=10, silent=True)

# 处理 alerts
alerts = safety_mas.get_alerts()
for alert in alerts:
    logger.log_alert(alert)

# 结束会话并保存 JSON
json_path = logger.end_session(success=result.success)
print(f"Session saved to: {json_path}")
```

### 自定义日志输出

```python
# 打印阶段标题
logger.print_phase(1, 3, "Pre-deployment Testing", "Running security tests")

# 打印子节标题
logger.print_subsection("Available Monitors")

# 打印不同类型的消息
logger.print_info("Information message")
logger.print_success("Success message")
logger.print_warning("Warning message")
logger.print_error("Error message")

# 打印监控器状态
logger.print_monitors_status(monitors, active=True)

# 打印测试结果
logger.log_test_result(test_name, result)

# 打印 Alert 汇总
logger.print_alerts_summary(alerts)
```

## 输出文件

所有日志文件默认保存在 `./logs/level3/` 目录：

- `session_YYYYMMDD_HHMMSS.json` - 完整会话记录
- `comprehensive_report_TIMESTAMP.json` - 综合安全评估报告

## 配置选项

### Level3ConsoleLogger 参数

- `use_colors` (bool): 是否使用彩色输出，默认 True
- `verbose` (bool): 是否显示详细信息，默认 False
- `output_dir` (str): JSON 输出目录，默认 "./logs/level3"

### 命令行参数

- `--module N`: 只运行指定模块 (1, 2, 或 3)
- `--all`: 运行所有模块（默认）
- `--verbose`: 显示详细输出
- `--no-color`: 关闭彩色输出
- `--output-dir PATH`: 指定 JSON 输出目录

## 根据 Alert 溯源

通过 JSON 文件可以轻松追溯 Alert 的来源：

1. 查看 `alert.step_index` 找到触发步骤
2. 在 `messages` 数组中找到对应 index 的消息
3. 查看 `alert.source_agent` 和 `alert.target_agent` 了解通信双方
4. 查看 `alert.source_message` 了解触发内容
5. 查看 `alert.detection_reason` 了解检测依据

## 示例输出

完整的示例输出请参考 `examples/full_demo/` 目录下的运行结果。

## 技术细节

### 架构

```
Level 3 Safety_MAS
├── Alert (增强的数据模型)
├── Level3ConsoleLogger (结构化日志输出器)
│   ├── 实时精简输出
│   ├── Alert 详细展示
│   └── JSON 完整存储
└── Safety_MAS (集成新日志系统)
    ├── 关闭 AG2 原生输出 (silent=True)
    ├── 消息钩子记录
    └── Alert 来源追踪
```

### 数据流

```
AG2 Messages (silent=True)
    ↓
Message Hook
    ↓
Level3ConsoleLogger.log_message()
    ↓ (实时)
Console Output (精简版)
    ↓ (任务结束)
JSON File (完整版)
```

## 常见问题

### Q: 如何关闭彩色输出？

A: 使用 `--no-color` 参数或在代码中设置 `use_colors=False`

### Q: JSON 文件保存在哪里？

A: 默认保存在 `./logs/level3/` 目录，可通过 `--output-dir` 参数修改

### Q: 如何查看完整的消息内容？

A: 查看保存的 JSON 文件，其中包含完整的消息内容

### Q: Alert 的 detection_reason 从哪里来？

A: 由各个 Monitor 在检测到风险时填充，描述检测逻辑

## 更新日志

### 2026-01-29

- ✅ 完全抑制 AG2 工具执行输出 (使用 `redirect_stdout`)
- ✅ 添加工具调用的结构化日志展示
- ✅ 在消息钩子中检测并记录工具调用
- ✅ 修改 step1_native_ag2.py 支持 silent 参数
- ✅ 所有 ConversableAgent 支持 silent 模式

### 2026-01-28

- ✅ 增强 Alert 数据模型，添加来源追踪字段
- ✅ 创建 Level3ConsoleLogger 结构化日志输出器
- ✅ 修改 AG2MAS 支持 silent 模式
- ✅ 重构 step4_level3_safety.py 使用新日志系统
- ✅ 实现完整 JSON 会话存储
- ✅ 实现 Alert 详细展示与溯源
