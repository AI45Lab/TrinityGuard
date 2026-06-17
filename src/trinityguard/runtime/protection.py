"""Synchronous runtime protection façade for Phase 2 MVP."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any

from .adapter_contract import MessageHookResult
from .config import PolicyConfig
from .events import RuntimeDecision, RuntimeEvent, RuntimeRequest, payload_hash
from .policy import decide_from_judge_results
from .sinks import EventSink, InMemoryEventSink


class RuntimeProtector:
    """Thin runtime façade over L1 messages, L2 evidence, and L3 judges.

    The protector intentionally depends on small contracts: judges expose
    ``analyze(content, context)`` and optional ``risk_type`` metadata; L1 hook
    integration is a plain dict-to-dict callable. This avoids coupling the MVP
    to the legacy ``Safety_MAS`` orchestrator while still reusing the validated
    Level 3 judge spine.
    """

    def __init__(
        self,
        *,
        judges: Iterable[Any],
        policy: PolicyConfig | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self.judges = list(judges)
        self.policy = policy or PolicyConfig()
        self.event_sink = (
            event_sink if event_sink is not None else InMemoryEventSink(self.policy.max_events)
        )
        self._consecutive_failures = 0
        self._circuit_open = False

    def evaluate(self, request: RuntimeRequest, *, output: Any = None) -> RuntimeDecision:
        """Evaluate a runtime request and emit redacted evidence."""

        results: list[Any] = []
        failures: list[BaseException | str] = []

        if self._circuit_open:
            failures.append("runtime circuit breaker is open")
        else:
            failures.extend(self._run_judges(request, results))

        self._update_circuit_state(failures, results)

        decision = decide_from_judge_results(
            request_id=request.request_id,
            policy=self.policy,
            judge_results=results,
            failures=failures,
        )
        event = RuntimeEvent.from_decision(request=request, decision=decision, output=output)
        try:
            self.event_sink.emit(event)
        except Exception as exc:  # noqa: BLE001 - sink failures are policy-controlled.
            if self.policy.fail_closed_on_sink_error:
                return decision.blocked_by_sink_error(exc)
            return decision.with_sink_error(exc)
        return decision

    def _run_judges(self, request: RuntimeRequest, results: list[Any]) -> list[BaseException | str]:
        failures: list[BaseException | str] = []
        for judge in self.judges:
            risk_type = getattr(judge, "risk_type", None)
            if self.policy.enabled_checks and risk_type not in self.policy.enabled_checks:
                continue
            try:
                result = self._analyze_judge(judge, request)
            except Exception as exc:  # noqa: BLE001 - runtime protection must capture judge failures.
                failures.append(exc)
                continue
            if result is None:
                failures.append(f"judge {risk_type or judge.__class__.__name__} returned no result")
                continue
            results.append(result)
        return failures

    def _analyze_judge(self, judge: Any, request: RuntimeRequest) -> Any:
        if self.policy.judge_timeout_seconds is None:
            return judge.analyze(request.message, context=self._judge_context(request))

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(judge.analyze, request.message, self._judge_context(request))
        try:
            result = future.result(timeout=self.policy.judge_timeout_seconds)
        except TimeoutError as exc:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            raise TimeoutError(
                f"judge {getattr(judge, 'risk_type', judge.__class__.__name__)} timed out"
            ) from exc
        except Exception:
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        executor.shutdown(wait=True)
        return result

    def _update_circuit_state(
        self, failures: list[BaseException | str], results: list[Any]
    ) -> None:
        if self.policy.circuit_breaker_failure_threshold is None:
            return
        if failures and not results:
            self._consecutive_failures += 1
        else:
            self._consecutive_failures = 0
            self._circuit_open = False
        if self._consecutive_failures >= self.policy.circuit_breaker_failure_threshold:
            self._circuit_open = True

    def as_message_hook(
        self, *, refusal_message: str | None = None
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        """Return a L1-compatible message hook using refusal replacement semantics."""

        structured_hook = self.as_message_hook_result(
            refusal_message=refusal_message,
            block_mode="replace",
        )

        def hook(message: dict[str, Any]) -> dict[str, Any]:
            return structured_hook(message).message

        return hook

    def as_message_hook_result(
        self,
        *,
        refusal_message: str | None = None,
        block_mode: str = "replace",
    ) -> Callable[[dict[str, Any]], MessageHookResult]:
        """Return a structured L1 hook that can replace or deny blocked messages."""

        if block_mode not in {"replace", "deny"}:
            raise ValueError("RuntimeProtector block_mode must be 'replace' or 'deny'")
        refusal = refusal_message or "[BLOCKED by TrinityGuard runtime policy]"

        def hook(message: dict[str, Any]) -> MessageHookResult:
            original_content = str(message.get("content", ""))
            request = RuntimeRequest(
                request_id=str(message.get("request_id") or uuid.uuid4()),
                agent_id=str(message.get("from") or message.get("agent_id") or "unknown"),
                action="message_hook",
                message=original_content,
                context={
                    "from": str(message.get("from", "")),
                    "to": str(message.get("to", "")),
                    "role": str(message.get("role", "")),
                },
                metadata=dict(message.get("metadata") or {}),
            )
            decision = self.evaluate(request)
            protected = dict(message)
            delivery_action = "allow"
            if decision.decision == "block":
                delivery_action = "deny" if block_mode == "deny" else "replace"
            protected["runtime_protection"] = {
                "decision": decision.decision,
                "permitted": decision.permitted,
                "reason": decision.reason,
                "request_id": decision.request_id,
                "policy": {"name": self.policy.name, "version": self.policy.version},
                "original_payload_ref": f"sha256:{payload_hash(original_content)}",
                "delivery_action": delivery_action,
            }
            if decision.decision == "block":
                if block_mode == "deny":
                    return MessageHookResult.deny(
                        protected,
                        reason=decision.reason,
                        metadata=protected["runtime_protection"],
                    )
                protected["content"] = refusal
                return MessageHookResult.replace(
                    protected,
                    reason=decision.reason,
                    metadata=protected["runtime_protection"],
                )
            return MessageHookResult.allow(
                protected,
                reason=decision.reason,
                metadata=protected["runtime_protection"],
            )

        return hook

    @staticmethod
    def _judge_context(request: RuntimeRequest) -> dict[str, Any]:
        return {
            "request_id": request.request_id,
            "agent_id": request.agent_id,
            "action": request.action,
            **request.context,
            "metadata": request.metadata,
        }
