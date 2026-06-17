"""A3S Code framework wrapper implementation.

The adapter is intentionally import-light: importing TrinityGuard must not
import ``a3s_code`` because that package may fetch a native wheel on first
import.  Use :meth:`A3SCodeMAS.from_acl` when constructing from a real A3S
configuration file.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ...runtime.adapter_contract import MessageHookResult
from ...utils.logging_config import get_logger
from ..base import AgentInfo, BaseMAS, WorkflowResult


@dataclass(frozen=True)
class A3SCodeAgentSpec:
    """TrinityGuard-visible agent in an A3S Code session."""

    name: str
    role: str = "coding_agent"
    prompt: str | None = None
    tools: list[str] = field(default_factory=list)


class A3SCodeMAS(BaseMAS):
    """Wrap an A3S Code agent/session as a TrinityGuard MAS.

    A3S Code is a coding-agent runtime, so this adapter models the root session
    plus optional delegated worker specs as a MAS topology.  Workflow execution
    uses ``session.tasks(...)`` when multiple worker specs are configured and
    the session exposes that API; otherwise it falls back to ``session.send``.
    """

    def __init__(
        self,
        agent: Any | None = None,
        *,
        workspace: str,
        session: Any | None = None,
        session_options: Any | None = None,
        agents: list[A3SCodeAgentSpec | dict[str, Any]] | None = None,
        root_agent_name: str = "a3s_root",
    ) -> None:
        super().__init__()
        if agent is None and session is None:
            raise ValueError("A3SCodeMAS requires either an agent or a pre-created session")
        self.logger = get_logger("A3SCodeMAS")
        self.agent = agent
        self.workspace = workspace
        self.session_options = session_options
        self._session = session
        self.root_agent_name = root_agent_name
        self._message_history: list[dict[str, Any]] = []
        self._memory: dict[str, list[dict[str, Any]]] = {}
        self._agent_specs = self._normalize_agent_specs(agents, root_agent_name)

    @classmethod
    def from_acl(
        cls,
        acl_path: str,
        *,
        workspace: str,
        session_options: Any | None = None,
        agents: list[A3SCodeAgentSpec | dict[str, Any]] | None = None,
        root_agent_name: str = "a3s_root",
    ) -> A3SCodeMAS:
        """Create an adapter from a real A3S Code ACL file."""

        try:
            from a3s_code import Agent
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise ImportError(
                "a3s-code is not installed. Install with: pip install a3s-code"
            ) from exc
        return cls(
            Agent.create(acl_path),
            workspace=workspace,
            session_options=session_options,
            agents=agents,
            root_agent_name=root_agent_name,
        )

    def get_agents(self) -> list[AgentInfo]:
        """Return TrinityGuard-visible A3S worker specs."""

        return [
            AgentInfo(
                name=spec.name,
                role=spec.role,
                system_prompt=spec.prompt,
                tools=list(spec.tools),
            )
            for spec in self._agent_specs
        ]

    def get_agent(self, name: str) -> A3SCodeAgentSpec:
        """Return an A3S worker spec by name."""

        for spec in self._agent_specs:
            if spec.name == name:
                return spec
        available = [spec.name for spec in self._agent_specs]
        raise ValueError(f"Agent '{name}' not found. Available agents: {available}")

    def get_topology(self) -> dict[str, list[str]]:
        """Return root-to-worker topology for delegated A3S Code workflows."""

        workers = [spec.name for spec in self._agent_specs if spec.name != self.root_agent_name]
        topology = {self.root_agent_name: workers}
        for worker in workers:
            topology[worker] = [self.root_agent_name]
        return topology

    def run_workflow(self, task: str, **kwargs: Any) -> WorkflowResult:
        """Execute an A3S Code workflow and expose a TrinityGuard trace."""

        self.logger.log_workflow_start(task, "a3s_code")
        self._message_history.clear()
        started = time.time()

        root_input = self._deliver(
            from_agent="user",
            to_agent=self.root_agent_name,
            content=task,
            metadata={"transition": "user_to_a3s_root", "route_complete": True},
        )
        if root_input.action == "deny":
            return self._denied_result(root_input, started)

        session = self._ensure_session()
        prompt = root_input.message.get("content", "")

        try:
            if self._should_use_delegation(session, kwargs):
                output = self._run_delegated_workflow(session, prompt, **kwargs)
            else:
                output = self._run_single_session_workflow(session, prompt, **kwargs)
        except Exception as exc:
            self.logger.error(f"A3S workflow execution failed: {exc}", exc_info=True)
            return WorkflowResult(
                success=False,
                output=None,
                messages=list(self._message_history),
                metadata=self._metadata(started, mode="a3s_code", error=str(exc)),
                error=str(exc),
            )

        root_output = self._deliver(
            from_agent=self.root_agent_name,
            to_agent="user",
            content=output,
            metadata={"transition": "a3s_root_to_user", "route_complete": True},
        )
        if root_output.action == "deny":
            return self._denied_result(root_output, started)

        self.logger.log_workflow_end(success=True, duration=time.time() - started)
        return WorkflowResult(
            success=True,
            output=root_output.message.get("content"),
            messages=list(self._message_history),
            metadata=self._metadata(started, mode="a3s_code"),
        )

    def direct_prompt(self, agent_name: str, message: str, history: list | None = None) -> str:
        """Run a direct prompt against the A3S session for L1 attack tests."""

        self.get_agent(agent_name)
        result = self.run_workflow(message, target_agent=agent_name, history=history)
        if not result.success:
            raise RuntimeError(result.error or "A3S direct prompt failed")
        return "" if result.output is None else str(result.output)

    def run_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        """Run an A3S direct tool when the session exposes ``tool``."""

        session = self._ensure_session()
        if not hasattr(session, "tool"):
            raise NotImplementedError("A3S session does not expose tool(...)")
        return session.tool(tool_name, params)

    def add_memory(self, agent_name: str, memory_content: str, memory_type: str) -> bool:
        """Store adapter-local memory and forward to session memory APIs if present."""

        self.get_agent(agent_name)
        row = {"type": memory_type, "content": memory_content}
        self._memory.setdefault(agent_name, []).append(row)
        session = self._ensure_session()
        for method_name in ("add_memory", "remember"):
            method = getattr(session, method_name, None)
            if callable(method):
                method(agent_name, row)
                break
        return True

    def _run_single_session_workflow(self, session: Any, prompt: str, **kwargs: Any) -> str:
        history = kwargs.get("history")
        request = kwargs.get("request")
        if isinstance(request, dict):
            request = dict(request)
            request["prompt"] = prompt
            if history is not None:
                request["history"] = history
            result = session.send(request)
            return self._result_text(result)

        target_agent = kwargs.get("target_agent")
        if target_agent:
            prompt = f"[target_agent={target_agent}]\n{prompt}"
        try:
            result = session.send(prompt, history=history)
        except TypeError:
            result = session.send(prompt)
        return self._result_text(result)

    def _run_delegated_workflow(self, session: Any, prompt: str, **kwargs: Any) -> str:
        workers = [spec for spec in self._agent_specs if spec.name != self.root_agent_name]
        task_specs: list[dict[str, Any]] = []
        for worker in workers:
            worker_prompt = self._worker_prompt(worker, prompt)
            handoff = self._deliver(
                from_agent=self.root_agent_name,
                to_agent=worker.name,
                content=worker_prompt,
                metadata={
                    "transition": "a3s_root_to_worker",
                    "route_complete": True,
                    "worker_role": worker.role,
                },
            )
            if handoff.action == "deny":
                raise RuntimeError(f"A3S worker handoff denied: {handoff.reason}")
            task_specs.append(
                {
                    "agent": worker.name,
                    "description": worker.role,
                    "prompt": handoff.message.get("content", ""),
                }
            )

        outcomes = session.tasks(task_specs)
        output = self._outcomes_text(outcomes)
        self._deliver(
            from_agent=",".join(worker.name for worker in workers),
            to_agent=self.root_agent_name,
            content=output,
            metadata={"transition": "a3s_workers_to_root", "route_complete": True},
        )
        return output

    def _deliver(
        self,
        *,
        from_agent: str,
        to_agent: str,
        content: Any,
        metadata: dict[str, Any],
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> MessageHookResult:
        message: dict[str, Any] = {
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "metadata": metadata,
        }
        if tool_calls:
            message["tool_calls"] = tool_calls

        hook_result = self._apply_message_hooks_with_result(message)
        delivered = dict(hook_result.message)
        if hook_result.action == "deny":
            delivered = hook_result.to_dict().get("message", delivered)
            delivered["delivery_denied"] = True
        self._message_history.append(delivered)
        return hook_result

    def _denied_result(self, hook_result: MessageHookResult, started: float) -> WorkflowResult:
        denial = hook_result.to_dict()
        return WorkflowResult(
            success=False,
            output=None,
            messages=list(self._message_history),
            metadata={**self._metadata(started, mode="a3s_code"), "delivery_denied": denial},
            error=hook_result.reason or "message delivery denied",
        )

    def _ensure_session(self) -> Any:
        if self._session is not None:
            return self._session
        if self.agent is None or not hasattr(self.agent, "session"):
            raise RuntimeError("A3S agent does not expose session(...)")
        if self.session_options is None:
            self._session = self.agent.session(self.workspace)
        else:
            self._session = self.agent.session(self.workspace, self.session_options)
        return self._session

    def _metadata(self, started: float, *, mode: str, error: str | None = None) -> dict[str, Any]:
        session = self._session
        runs = None
        if session is not None and hasattr(session, "runs"):
            try:
                runs = session.runs()
            except Exception:
                runs = None
        data: dict[str, Any] = {
            "adapter": "a3s_code",
            "mode": mode,
            "workspace": self.workspace,
            "duration": time.time() - started,
            "topology": self.get_topology(),
        }
        if runs is not None:
            data["runs"] = runs
        if error:
            data["error"] = error
        return data

    def _should_use_delegation(self, session: Any, kwargs: dict[str, Any]) -> bool:
        if kwargs.get("use_delegation") is False:
            return False
        if kwargs.get("target_agent"):
            return False
        workers = [spec for spec in self._agent_specs if spec.name != self.root_agent_name]
        return bool(workers) and hasattr(session, "tasks")

    def _normalize_agent_specs(
        self,
        agents: list[A3SCodeAgentSpec | dict[str, Any]] | None,
        root_agent_name: str,
    ) -> list[A3SCodeAgentSpec]:
        specs: list[A3SCodeAgentSpec] = []
        if agents:
            for item in agents:
                if isinstance(item, A3SCodeAgentSpec):
                    specs.append(item)
                else:
                    specs.append(
                        A3SCodeAgentSpec(
                            name=str(item["name"]),
                            role=str(item.get("role", "coding_agent")),
                            prompt=item.get("prompt"),
                            tools=list(item.get("tools", [])),
                        )
                    )
        if not any(spec.name == root_agent_name for spec in specs):
            specs.insert(
                0,
                A3SCodeAgentSpec(
                    name=root_agent_name,
                    role="root_coding_agent",
                    prompt="Root A3S Code session",
                ),
            )
        return specs

    @staticmethod
    def _worker_prompt(worker: A3SCodeAgentSpec, prompt: str) -> str:
        if worker.prompt:
            return f"{worker.prompt}\n\nTask: {prompt}"
        return prompt

    @staticmethod
    def _result_text(result: Any) -> str:
        if hasattr(result, "text"):
            return "" if result.text is None else str(result.text)
        if isinstance(result, dict):
            for key in ("text", "output", "content"):
                if key in result:
                    return "" if result[key] is None else str(result[key])
        return "" if result is None else str(result)

    def _outcomes_text(self, outcomes: Any) -> str:
        if isinstance(outcomes, dict) and "outcomes" in outcomes:
            outcomes = outcomes["outcomes"]
        if isinstance(outcomes, list):
            parts = []
            for item in outcomes:
                if isinstance(item, dict):
                    agent = item.get("agent") or item.get("name") or "worker"
                    text = self._result_text(item.get("result", item.get("text", item)))
                    parts.append(f"{agent}: {text}")
                else:
                    parts.append(self._result_text(item))
            return "\n".join(parts)
        return self._result_text(outcomes)
