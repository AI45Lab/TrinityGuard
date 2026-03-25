# 统一日志管理系统

## 概述

为了防止日志文件散落在不同目录，我们实现了统一的日志会话管理系统。每次运行都会在 `logs/log/` 下创建一个带时间戳的文件夹，所有输出文件（txt、json）都保存在该文件夹中。

## 目录结构

```
logs/log/
├── 20260202_143022/              # 第一次运行的会话文件夹
│   ├── session_20260202_143025.json
│   ├── comprehensive_report.json
│   └── level3_safety_research.txt
├── 20260202_145633/              # 第二次运行的会话文件夹
│   ├── session_20260202_145640.json
│   ├── comprehensive_report.json
│   └── level3_safety_research.txt
└── 20260202_151200_my_test/      # 带自定义名称的会话文件夹
    ├── session_20260202_151205.json
    ├── comprehensive_report.json
    └── level3_safety_research.txt
```

## 核心组件

### 1. LogSessionManager

**文件**: `src/utils/log_session_manager.py`

提供统一的日志会话管理：

```python
from src.utils.log_session_manager import start_log_session, get_current_session

# 启动日志会话（创建时间戳文件夹）
session = start_log_session(session_name="my_test")  # 可选的自定义名称

# 获取文件路径
file_path = session.get_file_path("report.json")

# 保存 JSON 文件
session.save_json_file("data.json", {"key": "value"})

# 保存文本文件
session.save_text_file("log.txt", "content here")

# 获取会话信息
info = session.get_session_info()
print(f"Session dir: {info['session_dir']}")
print(f"Created files: {info['created_files']}")
```

### 2. 集成到 Level3ConsoleLogger

**文件**: `src/level3_safety/console_logger.py`

控制台日志器已集成会话管理：

```python
from src.level3_safety import Level3ConsoleLogger
from src.utils.log_session_manager import start_log_session

# 创建会话
session = start_log_session(session_name="safety_test")

# 传递给日志器
logger = Level3ConsoleLogger(
    use_colors=True,
    verbose=False,
    session_manager=session  # 使用会话管理器
)

# 所有日志输出自动保存到会话目录
logger.start_session("My task")
# ... 执行任务 ...
logger.end_session()  # session_*.json 自动保存到会话目录
```

## 使用方式

### 运行 Level 3 Demo

```bash
# 基本运行（自动创建时间戳文件夹）
uv run python examples/full_demo/step4_level3_safety.py

# 带自定义会话名称
uv run python examples/full_demo/step4_level3_safety.py --session-name my_experiment

# 指定输出基础目录
uv run python examples/full_demo/step4_level3_safety.py --output-dir ./my_logs

# 完整示例
uv run python examples/full_demo/step4_level3_safety.py \
    --session-name safety_test_v1 \
    --output-dir ./logs/log \
    --verbose
```

### 文件保存位置

运行后，所有文件自动保存到会话目录：

1. **Session 日志** (`session_*.json`) - 由 `console_logger.end_session()` 自动保存
2. **综合报告** (`comprehensive_report.json`) - 由 module3 保存
3. **Agent 输出文件** (`level3_safety_research.txt`) - Agent 执行任务时创建，**任务完成后自动收集到 session 目录**

**关键修改**：
- `console_logger.py:249-265` - `_save_session_json()` 使用 session_manager
- `step4_level3_safety.py:223-236` - 任务中指定会话目录作为文件保存路径
- `step4_level3_safety.py:396-435` - **任务执行后自动收集生成的文件到 session 目录**
- `step4_level3_safety.py:569-580` - 综合报告保存到会话目录

## 实现细节

### 会话生命周期

```python
# 1. 启动会话（在 main() 开始时）
session = start_log_session(session_name=args.session_name, base_dir=args.output_dir)
# 创建目录: logs/log/20260202_143022/ 或 logs/log/20260202_143022_my_test/

# 2. 创建日志器并传递会话
logger = Level3ConsoleLogger(session_manager=session)

# 3. 执行任务（所有文件自动保存到会话目录）
logger.start_session(task)
# ... 执行 ...
logger.end_session()  # 保存 session_*.json

# 4. 保存综合报告
session.save_json_file("comprehensive_report.json", report_data)

# 5. 会话结束（可选）
from src.utils.log_session_manager import end_log_session
session_info = end_log_session()
print(f"Created {session_info['total_files']} files")
```

### 自动文件收集机制

为了确保 Agent 执行任务时创建的中间文件（txt、md 等）也能被收集到 session 目录，系统实现了自动文件收集：

**工作原理** (`step4_level3_safety.py:396-435`):

1. **任务执行完成后** - 在 Module 2 的 step 2.5/3 自动触发
2. **扫描目录** - 检查当前工作目录和 `examples/full_demo/` 目录
3. **识别新文件** - 查找最近 5 分钟内创建的 `.txt` 和 `.md` 文件
4. **过滤文件** - 跳过系统文件（`.` 开头）和 session 文件
5. **移动文件** - 将识别的文件移动到 session 目录
6. **更新追踪** - 将文件路径添加到 session 的文件列表

**示例输出**:
```
🔄 Step 2.5/3: Collecting generated files...
✓ Moved 2 generated file(s) to session directory
  - level3_safety_research.txt
  - research_notes.md
```

**支持的文件类型**:
- `.txt` - 文本文件
- `.md` - Markdown 文件
- 可根据需要扩展更多类型

这样确保了 Agent 无论在哪里创建文件，最终都会被收集到对应的 session 文件夹中。

### 兼容性

系统向后兼容：

- 如果没有传递 `session_manager`，会回退到旧的 `output_dir` 方式
- 旧代码无需修改即可运行
- 新代码建议使用 `session_manager`

```python
# 旧方式（仍然有效）
logger = Level3ConsoleLogger(output_dir="./logs/level3")

# 新方式（推荐）
session = start_log_session()
logger = Level3ConsoleLogger(session_manager=session)
```

## 优势

### 1. 文件组织清晰

每次运行的所有文件都在同一个文件夹中，不会散落：

```
logs/log/20260202_143022/
├── session_20260202_143025.json       # 会话日志
├── comprehensive_report.json          # 综合报告
└── level3_safety_research.txt         # Agent 输出
```

### 2. 易于追溯

通过时间戳文件夹名称快速定位运行记录：

```bash
# 查看最近的运行
ls -lt logs/log/

# 查看特定运行的所有文件
ls logs/log/20260202_143022/
```

### 3. 便于清理

删除整个会话文件夹即可清除该次运行的所有文件：

```bash
# 删除特定会话
rm -rf logs/log/20260202_143022/

# 清理旧会话（保留最近 10 个）
ls -t logs/log/ | tail -n +11 | xargs -I {} rm -rf logs/log/{}
```

### 4. 支持自定义命名

可以为重要的运行添加描述性名称：

```bash
# 实验性测试
python step4_level3_safety.py --session-name experimental_feature_v1

# 性能测试
python step4_level3_safety.py --session-name performance_benchmark

# 生成的文件夹名称
logs/log/20260202_143022_experimental_feature_v1/
logs/log/20260202_145633_performance_benchmark/
```

## 示例输出

运行 `step4_level3_safety.py` 后：

```
Level 3 Safety - Structured Monitoring Demo
============================================

>>> Creating MAS
✓ MAS created with 4 agents

>>> Creating Safety_MAS Wrapper
✓ Safety_MAS created successfully
  Available risk tests: 20
  Available monitors: 20

[1/3] Pre-deployment Safety Testing
------------------------------------------------------------

... 执行测试 ...

[2/3] Runtime Safety Monitoring
------------------------------------------------------------

... 执行监控 ...

✓ Session saved to: /path/to/logs/log/20260202_143022/session_20260202_143025.json

[3/3] Test-Monitor Integration
------------------------------------------------------------

... 生成报告 ...

✓ Report saved to: /path/to/logs/log/20260202_143022/comprehensive_report.json

Demo Complete
=============

Results:
  Module 1: 4/4 tests passed
  Module 2: 0 alerts detected
  Module 3: Comprehensive report generated

Log files saved to: ./logs/log
```

## 配置选项

### 命令行参数

```bash
python step4_level3_safety.py --help

Options:
  --session-name TEXT      Custom session name (default: timestamp)
  --output-dir TEXT        Directory for log sessions (default: ./logs/log)
  --verbose               Show verbose output
  --no-color              Disable colored output
  --module [1|2|3]        Run specific module only
  --all                   Run all modules (default)
```

### 代码配置

```python
# 自定义基础目录
session = start_log_session(
    session_name="my_test",
    base_dir="./custom_logs"
)
# 创建: ./custom_logs/20260202_143022_my_test/

# 创建子目录
file_path = session.get_file_path("report.json", subdir="reports")
# 创建: ./logs/log/20260202_143022/reports/report.json

# 保存到子目录
session.save_json_file("data.json", {...}, subdir="data")
# 保存到: ./logs/log/20260202_143022/data/data.json
```

## API 文档

### LogSessionManager 类

#### 初始化

```python
LogSessionManager(session_name: Optional[str] = None, base_dir: str = "logs/log")
```

**参数**：
- `session_name`: 可选的自定义会话名称（默认：时间戳）
- `base_dir`: 所有日志的基础目录（默认：logs/log）

#### 方法

**get_session_dir() -> Path**
- 返回当前会话目录的路径

**get_file_path(filename: str, subdir: Optional[str] = None) -> Path**
- 获取会话目录中的文件路径
- `subdir`: 可选的子目录名称

**save_text_file(filename: str, content: str, subdir: Optional[str] = None) -> Path**
- 保存文本文件到会话目录
- 返回保存的文件路径

**save_json_file(filename: str, data: dict, subdir: Optional[str] = None) -> Path**
- 保存 JSON 文件到会话目录
- 返回保存的文件路径

**get_created_files() -> list**
- 返回该会话创建的所有文件列表

**get_session_info() -> dict**
- 返回会话信息（名称、目录、时间戳、文件列表）

### 全局函数

**start_log_session(session_name: Optional[str] = None, base_dir: str = "logs/log") -> LogSessionManager**
- 启动新的日志会话（如果已存在则返回现有会话）
- 返回 LogSessionManager 实例

**get_current_session() -> Optional[LogSessionManager]**
- 获取当前活动的日志会话
- 如果没有活动会话则返回 None

**end_log_session() -> Optional[dict]**
- 结束当前会话并返回会话信息
- 返回会话信息字典，如果没有活动会话则返回 None

**get_session_file_path(filename: str, subdir: Optional[str] = None) -> Path**
- 获取当前会话中的文件路径
- 如果没有活动会话则自动创建一个

**save_session_text_file(filename: str, content: str, subdir: Optional[str] = None) -> Path**
- 保存文本文件到当前会话目录
- 如果没有活动会话则自动创建一个

**save_session_json_file(filename: str, data: dict, subdir: Optional[str] = None) -> Path**
- 保存 JSON 文件到当前会话目录
- 如果没有活动会话则自动创建一个

## 与现有系统集成

### chat_manager 解析

统一日志管理系统与 chat_manager 接收方解析完全兼容：

```python
# 会话管理自动应用 chat_manager 解析
session = start_log_session()
logger = Level3ConsoleLogger(session_manager=session)

logger.start_session(task)
# ... 执行任务（消息会被记录）...
logger.end_session()  # 自动应用 resolve_chat_manager_recipients()

# session_*.json 中的消息已解析为真实接收方
```

解析在以下位置自动应用：
1. `console_logger.py:73-76` - WorkflowSession.to_dict() 应用解析
2. `safety_mas.py` - get_comprehensive_report() 应用嵌套解析

## 故障排查

### 问题：文件没有保存到会话目录

**检查**：
1. 确认代码中使用了 `session_manager`：
   ```python
   session = start_log_session()
   logger = Level3ConsoleLogger(session_manager=session)
   ```

2. 确认文件保存时使用了 session 方法：
   ```python
   session.save_json_file("report.json", data)
   # 而不是直接写文件
   ```

### 问题：会话目录名称不正确

**检查**：
- 确认 `session_name` 参数正确传递
- 检查系统时间是否正确（时间戳来自系统时间）

### 问题：无法找到会话目录

**检查**：
```python
session = get_current_session()
if session:
    print(f"Session dir: {session.get_session_dir()}")
else:
    print("No active session!")
```

## 总结

统一日志管理系统提供了：

✅ 所有文件集中在同一个文件夹中
✅ 带时间戳的文件夹名称便于追溯
✅ 支持自定义会话名称
✅ 向后兼容旧代码
✅ 与 chat_manager 解析无缝集成
✅ 简单易用的 API

**现在，每次运行都会创建一个新的会话文件夹，所有文件都保存在里面，再也不用担心文件到处跑！** 🎉
