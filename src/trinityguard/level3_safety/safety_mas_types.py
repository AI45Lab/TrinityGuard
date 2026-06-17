"""Small shared types for the Safety_MAS compatibility façade."""

from __future__ import annotations

from enum import Enum


class MonitorSelectionMode(Enum):
    """How to select which monitors to activate."""

    MANUAL = "manual"
    AUTO_LLM = "auto_llm"
    PROGRESSIVE = "progressive"
