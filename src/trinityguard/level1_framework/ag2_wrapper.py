"""Deprecated compatibility exports for the migrated AG2 framework adapter."""

from __future__ import annotations

from .ag2.adapter import AG2MAS, create_ag2_mas_from_config

__all__ = ["AG2MAS", "create_ag2_mas_from_config"]
