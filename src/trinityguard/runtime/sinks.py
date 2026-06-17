"""Runtime event sinks for the Phase 2 MVP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .events import RuntimeEvent


class EventSink(Protocol):
    """Minimal event sink protocol."""

    def emit(self, event: RuntimeEvent) -> None:
        """Persist or enqueue an event."""


class InMemoryEventSink:
    """Bounded in-memory event sink for offline runtime MVP tests.

    Bounds apply to count and approximate serialized event bytes so local
    monitoring evidence cannot grow without limit during simulations.
    """

    def __init__(self, max_events: int = 100, max_event_bytes: int = 64_000) -> None:
        if max_events < 1:
            raise ValueError("InMemoryEventSink.max_events must be >= 1")
        if max_event_bytes < 1:
            raise ValueError("InMemoryEventSink.max_event_bytes must be >= 1")
        self.max_events = max_events
        self.max_event_bytes = max_event_bytes
        self.events: list[RuntimeEvent] = []

    def emit(self, event: RuntimeEvent) -> None:
        serialized = json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True)
        if len(serialized.encode("utf-8")) > self.max_event_bytes:
            raise ValueError("runtime event exceeds configured max_event_bytes")
        self.events.append(event)
        overflow = len(self.events) - self.max_events
        if overflow > 0:
            del self.events[:overflow]


class JsonlEventSink:
    """Local bounded JSONL event sink for replayable MVP evidence."""

    def __init__(self, path: str | Path, max_event_bytes: int = 64_000) -> None:
        if max_event_bytes < 1:
            raise ValueError("JsonlEventSink.max_event_bytes must be >= 1")
        self.path = Path(path)
        self.max_event_bytes = max_event_bytes

    def emit(self, event: RuntimeEvent) -> None:
        serialized = json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True)
        if len(serialized.encode("utf-8")) > self.max_event_bytes:
            raise ValueError("runtime event exceeds configured max_event_bytes")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")
