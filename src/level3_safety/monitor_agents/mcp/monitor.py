import json
import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, List
import logging
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
from mcpuniverse.evaluator.evaluator import Evaluator, EvaluationResult
from mcpuniverse.common.context import Context
from mcpuniverse.tracer.types import TraceRecord
from ..base import BaseMonitorAgent, Alert
from ....level2_intermediary.structured_logging import AgentStepLog

logger = logging.getLogger(__name__)

class ToolMonitor(BaseMonitorAgent):
    """
    L1 Tool Misuse Monitor - 生产级 mcpuniverse 集成版。
    使用 mcpuniverse 官方 Evaluator 引擎进行逐步轨迹检测。
    """

    def __init__(self, rules_json_path: str = "security_eval_rules.json", output_json_path: str = "agent_output.json"):
        super().__init__()
        monitor_dir = Path(__file__).resolve().parent

        self.rules_path = monitor_dir / rules_json_path
        self.output_path = monitor_dir / output_json_path

        self.ts = 0
        self.eval_context = Context()
        self._init_output_file()

    def _init_output_file(self):
        """初始化 agent_output.json，确保格式符合 trace_records 规范"""
        initial_data = {"trace_records": [{"records": []}]}
        self.output_path.write_text(json.dumps(initial_data, indent=2, ensure_ascii=False))

    def get_monitor_info(self) -> Dict[str, str]:
        return {
            "name": "ToolMisuseMonitor",
            "risk_type": "tool_misuse",
            "description": "基于 mcpuniverse 评估引擎的实时安全检测"
        }

    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """
        同步处理入口：每一步都更新 JSON 并触发 mcpuniverse 评估逻辑。
        """
        # 1. 加载持久化的轨迹文件
        try:
            content = self.output_path.read_text()
            agent_output = json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            self._init_output_file()
            agent_output = {"trace_records": [{"records": []}]}

        # 获取当前 Session 的 records
        current_records = agent_output["trace_records"][-1]["records"]

        # 2. 逐步追加记录 (严格对齐你提供的转换逻辑)
        updated = False
        print("9999999", log_entry)
        if log_entry.step_type == "tool_call":
            record = {
                "timestamp": self.ts,
                "data": {
                    "type": "tool",
                    "tool_name": log_entry.metadata.get("tool_name", ""),
                    "arguments": log_entry.metadata.get("params", {})
                }
            }
            current_records.append(record)
            self.ts += 1
            updated = True
        elif log_entry.step_type == "tool_response":
            if current_records:
                # 回填 Response，以便 Evaluator 进行结果审计
                current_records[-1]["data"]["response"] = log_entry.content
                updated = True

        # 3. 只有数据变化时才持久化，确保外部工具读取的是最新状态
        if updated:
            self.output_path.write_text(json.dumps(agent_output, indent=2, ensure_ascii=False))

        # 4. 执行 mcpuniverse 安全评估
        # 因为 process 是同步方法，使用 asyncio.run 运行异步评估器
        try:
            return asyncio.run(self._run_mcp_evaluation(agent_output, log_entry))
        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            return None

    async def _run_mcp_evaluation(self, agent_output: Dict, log_entry: AgentStepLog) -> Optional[Alert]:

        if not self.rules_path.exists():
            return None

        rules = json.loads(self.rules_path.read_text())

        # === 关键：dict → TraceRecord 对象 ===
        trace_records = []
        for tr in agent_output.get("trace_records", []):
            trace = TraceRecord()
            for r in tr.get("records", []):
                trace.records.append(r)
            trace_records.append(trace)

        evaluator_input = {
            "trace_records": trace_records
        }

        for rule in rules:
            evaluator = Evaluator(rule, context=self.eval_context)
            result: EvaluationResult = await evaluator.evaluate(evaluator_input)

            if not result.passed:
                alert = Alert(
                    severity="critical",
                    risk_type="tool_misuse",
                    message=f"[MCP-SECURITY] {result.config.desc}",
                    evidence={
                        "reason": result.reason,
                        "error": result.error,
                        "tool": log_entry.metadata.get("tool_name", ""),
                        "detected_by": "mcpuniverse_evaluator",
                    },
                    recommended_action="block",
                    timestamp=log_entry.timestamp,
                )
                self._record_alert(alert)
                return alert

        return None

    def reset(self):
        """完全重置，包括 mcpuniverse 的 Context 和轨迹文件"""
        super().reset()
        self.ts = 0
        self.eval_context = Context()
        self._init_output_file()