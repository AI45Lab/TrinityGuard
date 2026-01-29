"""Level 3 结构化控制台日志输出器。

提供:
1. 命令行精简实时输出
2. 完整 JSON 存储
3. Alert 详细展示与溯源
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from .monitor_agents.base import Alert


@dataclass
class ConversationMessage:
    """对话消息记录。"""
    index: int                    # 消息序号
    timestamp: float              # 时间戳
    from_agent: str               # 发送者
    to_agent: str                 # 接收者
    content: Optional[str]        # 消息内容（可能为 None）
    message_id: str = ""          # 消息ID
    step_type: str = "message"    # 步骤类型: message, tool_call, tool_result
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WorkflowSession:
    """完整工作流会话记录。"""
    task: str                                           # 任务描述
    start_time: float                                   # 开始时间
    end_time: Optional[float] = None                    # 结束时间
    success: bool = True                                # 是否成功
    error: Optional[str] = None                         # 错误信息
    messages: List[ConversationMessage] = field(default_factory=list)  # 所有消息
    alerts: List[Dict] = field(default_factory=list)    # 所有 alerts
    test_results: Dict = field(default_factory=dict)    # 测试结果
    metadata: Dict = field(default_factory=dict)        # 元数据

    def to_dict(self) -> Dict:
        return {
            "task": self.task,
            "start_time": self.start_time,
            "start_time_formatted": datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time,
            "end_time_formatted": datetime.fromtimestamp(self.end_time).strftime("%Y-%m-%d %H:%M:%S") if self.end_time else None,
            "duration_seconds": self.end_time - self.start_time if self.end_time else None,
            "success": self.success,
            "error": self.error,
            "messages": [m.to_dict() for m in self.messages],
            "alerts": self.alerts,
            "test_results": self.test_results,
            "metadata": self.metadata,
            "summary": {
                "total_messages": len(self.messages),
                "total_alerts": len(self.alerts),
                "critical_alerts": sum(1 for a in self.alerts if a.get("severity") == "critical"),
                "warning_alerts": sum(1 for a in self.alerts if a.get("severity") == "warning"),
                "agents_involved": list(set(m.from_agent for m in self.messages) | set(m.to_agent for m in self.messages))
            }
        }


class Level3ConsoleLogger:
    """Level 3 结构化控制台日志输出器。"""

    # ANSI 颜色代码
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bg_red": "\033[41m",
        "bg_yellow": "\033[43m",
        "bg_green": "\033[42m",
    }

    # Agent 颜色映射
    AGENT_COLORS = {
        "User": "cyan",
        "Coordinator": "blue",
        "Searcher": "magenta",
        "Analyzer": "yellow",
        "Summarizer": "green",
    }

    def __init__(self,
                 use_colors: bool = True,
                 verbose: bool = False,
                 output_dir: Optional[str] = None):
        """初始化日志输出器。

        Args:
            use_colors: 是否使用彩色输出
            verbose: 是否显示详细信息
            output_dir: JSON 输出目录
        """
        self.use_colors = use_colors
        self.verbose = verbose
        self.output_dir = Path(output_dir) if output_dir else Path("./logs/level3")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.current_session: Optional[WorkflowSession] = None
        self.message_counter = 0

    def _color(self, text: str, color: str) -> str:
        """给文本添加颜色。"""
        if not self.use_colors:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def _agent_color(self, agent_name: str) -> str:
        """获取 agent 对应的颜色。"""
        return self.AGENT_COLORS.get(agent_name, "white")

    def _format_time(self, timestamp: float) -> str:
        """格式化时间戳。"""
        return datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

    def _truncate(self, text: str, max_len: int = 80) -> str:
        """截断文本。"""
        if len(text) <= max_len:
            return text
        return text[:max_len-3] + "..."

    # ==================== 阶段分隔符 ====================

    def print_header(self, title: str, width: int = 80):
        """打印主标题。"""
        print()
        print(self._color("=" * width, "bold"))
        print(self._color(f"  {title}", "bold"))
        print(self._color("=" * width, "bold"))
        print()

    def print_phase(self, phase_num: int, total_phases: int, title: str, description: str = ""):
        """打印阶段标题。"""
        print()
        phase_text = f"[{phase_num}/{total_phases}] {title}"
        print(self._color(phase_text, "cyan"))
        print(self._color("-" * 60, "dim"))
        if description:
            print(self._color(f"  {description}", "dim"))
        print()

    def print_subsection(self, title: str):
        """打印子节标题。"""
        print()
        print(self._color(f">>> {title}", "blue"))
        print()

    # ==================== 会话管理 ====================

    def start_session(self, task: str):
        """开始新的工作流会话。"""
        self.current_session = WorkflowSession(
            task=task,
            start_time=time.time()
        )
        self.message_counter = 0

        self.print_header("Level 3 Safety - Runtime Monitoring")
        print(f"  Task: {self._truncate(task, 70)}")
        print(f"  Time: {self._format_time(self.current_session.start_time)}")
        print()

    def end_session(self, success: bool = True, error: Optional[str] = None) -> Optional[str]:
        """结束当前会话并保存 JSON。

        Returns:
            JSON 文件路径
        """
        if not self.current_session:
            return None

        self.current_session.end_time = time.time()
        self.current_session.success = success
        self.current_session.error = error

        # 保存 JSON
        json_path = self._save_session_json()

        # 打印会话摘要
        self._print_session_summary()

        session = self.current_session
        self.current_session = None

        return json_path

    def _save_session_json(self) -> str:
        """保存会话到 JSON 文件。"""
        if not self.current_session:
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.current_session.to_dict(), f, ensure_ascii=False, indent=2)

        return str(filepath)

    def _print_session_summary(self):
        """打印会话摘要。"""
        if not self.current_session:
            return

        session = self.current_session
        duration = session.end_time - session.start_time if session.end_time else 0

        self.print_header("Session Summary")

        status = self._color("SUCCESS", "green") if session.success else self._color("FAILED", "red")
        print(f"  Status: {status}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Messages: {len(session.messages)}")
        print(f"  Alerts: {len(session.alerts)}")
        print()

    # ==================== 消息日志 ====================

    def log_message(self,
                    from_agent: str,
                    to_agent: str,
                    content: Optional[str],
                    message_id: str = "",
                    step_type: str = "message",
                    metadata: Optional[Dict] = None):
        """记录并打印消息。"""
        self.message_counter += 1
        timestamp = time.time()

        # 确保 content 不是 None
        content = content if content is not None else ""

        msg = ConversationMessage(
            index=self.message_counter,
            timestamp=timestamp,
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_id=message_id,
            step_type=step_type,
            metadata=metadata or {}
        )

        if self.current_session:
            self.current_session.messages.append(msg)

        # 打印精简版本
        self._print_message_compact(msg)

    def _print_message_compact(self, msg: ConversationMessage):
        """打印精简版消息。"""
        time_str = self._format_time(msg.timestamp)
        from_color = self._agent_color(msg.from_agent)
        to_color = self._agent_color(msg.to_agent)

        # 检查是否是工具调用
        if msg.step_type == "tool_call":
            self._print_tool_call_compact(msg)
            return

        # 格式: [12:34:56] #1 Coordinator → Searcher
        header = (
            f"{self._color(f'[{time_str}]', 'dim')} "
            f"{self._color(f'#{msg.index}', 'dim')} "
            f"{self._color(msg.from_agent, from_color)} "
            f"{self._color('→', 'dim')} "
            f"{self._color(msg.to_agent, to_color)}"
        )
        print(header)

        # 消息内容预览
        content_str = str(msg.content) if msg.content is not None else ""
        preview = self._truncate(content_str.replace('\n', ' '), 70)
        print(f"   {self._color(preview, 'dim')}")
        print()

    def _print_tool_call_compact(self, msg: ConversationMessage):
        """打印精简版工具调用。"""
        time_str = self._format_time(msg.timestamp)
        from_color = self._agent_color(msg.from_agent)

        # 从 metadata 中提取工具信息
        tool_name = msg.metadata.get("tool_name", "unknown")
        tool_args = msg.metadata.get("tool_args", {})
        tool_result = msg.metadata.get("tool_result", None)

        # 格式: [12:34:56] #1 🔧 Searcher: search_papers
        header = (
            f"{self._color(f'[{time_str}]', 'dim')} "
            f"{self._color(f'#{msg.index}', 'dim')} "
            f"{self._color('🔧', 'yellow')} "
            f"{self._color(msg.from_agent, from_color)}: "
            f"{self._color(tool_name, 'yellow')}"
        )
        print(header)

        # 工具参数预览
        if tool_args:
            args_str = str(tool_args)
            args_preview = self._truncate(args_str, 60)
            print(f"   {self._color('Args:', 'dim')} {self._color(args_preview, 'dim')}")

        # 工具结果预览(如果有)
        if tool_result is not None:
            result_str = str(tool_result)
            result_preview = self._truncate(result_str, 60)
            print(f"   {self._color('Result:', 'dim')} {self._color(result_preview, 'dim')}")

        print()

    # ==================== Alert 日志 ====================

    def log_alert(self, alert: Alert):
        """记录并打印 Alert。"""
        alert_dict = alert.to_dict()
        if self.current_session:
            self.current_session.alerts.append(alert_dict)

        # 立即打印 Alert
        self._print_alert_detail(alert)

    def _print_alert_detail(self, alert: Alert):
        """打印详细的 Alert 信息。"""
        severity = alert.severity.upper()

        # 根据严重程度选择颜色和符号
        if severity == "CRITICAL":
            color = "red"
            symbol = "!!!"
            bg = "bg_red"
        elif severity == "WARNING":
            color = "yellow"
            symbol = " ! "
            bg = "bg_yellow"
        else:
            color = "cyan"
            symbol = " i "
            bg = None

        # Alert 框
        print()
        print(self._color("+" + "-" * 68 + "+", color))

        # 标题行
        title = f"| {symbol} ALERT: {alert.risk_type.upper()}"
        title = title.ljust(69) + "|"
        print(self._color(title, color))

        print(self._color("+" + "-" * 68 + "+", color))

        # 详细信息
        details = [
            ("Severity", severity),
            ("Message", self._truncate(alert.message, 50)),
            ("Source Agent", alert.source_agent or alert.agent_name or "N/A"),
            ("Target Agent", alert.target_agent or "N/A"),
            ("Detection", alert.detection_reason or "Pattern match"),
            ("Action", alert.recommended_action),
        ]

        for label, value in details:
            line = f"| {label}: {value}"
            line = line.ljust(69) + "|"
            print(self._color(line, color))

        # 消息来源预览
        if alert.source_message:
            print(self._color("|" + "-" * 68 + "|", color))
            preview = self._truncate(alert.source_message.replace('\n', ' '), 60)
            line = f"| Source: \"{preview}\""
            line = line.ljust(69) + "|"
            print(self._color(line, color))

        print(self._color("+" + "-" * 68 + "+", color))
        print()

    def print_alerts_summary(self, alerts: List[Alert]):
        """打印 Alerts 汇总。"""
        if not alerts:
            print(self._color("  No alerts detected during execution.", "green"))
            return

        critical = [a for a in alerts if a.severity == "critical"]
        warnings = [a for a in alerts if a.severity == "warning"]
        infos = [a for a in alerts if a.severity == "info"]

        print(f"  Total alerts: {len(alerts)}")
        if critical:
            print(self._color(f"    Critical: {len(critical)}", "red"))
        if warnings:
            print(self._color(f"    Warning:  {len(warnings)}", "yellow"))
        if infos:
            print(self._color(f"    Info:     {len(infos)}", "cyan"))
        print()

        # 按严重程度打印详情
        for alert in critical + warnings:
            self._print_alert_detail(alert)

    # ==================== 测试结果日志 ====================

    def log_test_result(self, test_name: str, result: Dict):
        """记录测试结果。"""
        if self.current_session:
            self.current_session.test_results[test_name] = result

        # 打印测试结果
        self._print_test_result(test_name, result)

    def _print_test_result(self, test_name: str, result: Dict):
        """打印测试结果。"""
        if "error" in result:
            status = self._color("ERROR", "red")
            print(f"  {test_name}: {status} - {result['error']}")
            return

        passed = result.get("passed", False)
        pass_rate = result.get("pass_rate", 0) * 100

        if passed:
            status = self._color("PASSED", "green")
        else:
            status = self._color("FAILED", "red")

        print(f"  {test_name}: {status} ({pass_rate:.1f}%)")

    # ==================== 监控器状态 ====================

    def print_monitors_status(self, monitors: List, active: bool = True):
        """打印监控器状态。"""
        status_text = self._color("ACTIVE", "green") if active else self._color("INACTIVE", "dim")

        for monitor in monitors:
            info = monitor.get_monitor_info()
            name = info.get("name", "unknown")
            print(f"    [{status_text}] {name}")

    # ==================== 工具方法 ====================

    def print_info(self, message: str):
        """打印信息。"""
        print(self._color(f"  {message}", "dim"))

    def print_success(self, message: str):
        """打印成功消息。"""
        print(self._color(f"  {message}", "green"))

    def print_warning(self, message: str):
        """打印警告消息。"""
        print(self._color(f"  ! {message}", "yellow"))

    def print_error(self, message: str):
        """打印错误消息。"""
        print(self._color(f"  X {message}", "red"))


# 全局实例
_console_logger: Optional[Level3ConsoleLogger] = None


def get_console_logger(**kwargs) -> Level3ConsoleLogger:
    """获取全局控制台日志实例。"""
    global _console_logger
    if _console_logger is None:
        _console_logger = Level3ConsoleLogger(**kwargs)
    return _console_logger
