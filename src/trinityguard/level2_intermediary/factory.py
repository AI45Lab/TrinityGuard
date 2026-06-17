"""Level 2 intermediary factory for Level 1 MAS implementations."""

from __future__ import annotations

from ..level1_framework.a3s.adapter import A3SCodeMAS
from ..level1_framework.base import BaseMAS
from .a3s_intermediary import A3SIntermediary
from .base import MASIntermediary
from .local_intermediary import LocalMASIntermediary

try:  # Keep non-AG2 adapters usable when the optional AG2 package is absent.
    from ..level1_framework.ag2.adapter import AG2MAS
    from .ag2_intermediary import AG2Intermediary
except ImportError:  # pragma: no cover - depends on optional dependency environment
    AG2MAS = None
    AG2Intermediary = None


def create_intermediary(mas: BaseMAS) -> MASIntermediary:
    """Create the appropriate Level 2 intermediary for a Level 1 MAS instance."""

    if AG2MAS is not None and isinstance(mas, AG2MAS):
        assert AG2Intermediary is not None
        return AG2Intermediary(mas)
    if isinstance(mas, A3SCodeMAS):
        return A3SIntermediary(mas)
    return LocalMASIntermediary(mas)
