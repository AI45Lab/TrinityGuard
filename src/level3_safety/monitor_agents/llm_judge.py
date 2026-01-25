"""Compatibility shim for LLM Judge.

This module re-exports from the judges module for backward compatibility.
Direct imports from here are deprecated - use `from ..judges import LLMJudge, JudgeResult` instead.
"""

# Re-export from judges module
from ..judges import LLMJudge, JudgeResult

__all__ = ["LLMJudge", "JudgeResult"]
