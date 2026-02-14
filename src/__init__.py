"""TrinityGuard - Multi-Agent System Safety Framework.

This package provides pre-deployment safety testing and runtime monitoring
for multi-agent systems.
"""

__version__ = "0.1.0"

# Level 1: MAS Framework Layer
from .level1_framework import (
    BaseMAS,
    AgentInfo,
    WorkflowResult,
    AG2MAS,
    create_ag2_mas_from_config,
)

# Level 2: MAS Intermediary Layer
from .level2_intermediary import (
    MASIntermediary,
    RunMode,
    AG2Intermediary,
    WorkflowRunner,
    MessageInterception,
    AgentStepLog,
    MessageLog,
    WorkflowTrace,
)

# Level 3: Safety_MAS Layer
from .level3_safety import (
    Safety_MAS,
    MonitorSelectionMode,
    BaseRiskTest,
    TestCase,
    TestResult,
    BaseMonitorAgent,
    Alert,
)

# Utils
from .utils import (
    TrinitySafetyConfig,
    get_config,
    set_config,
    load_config,
    get_llm_client,
    get_logger,
)

__all__ = [
    # Version
    "__version__",
    # Level 1
    "BaseMAS",
    "AgentInfo",
    "WorkflowResult",
    "AG2MAS",
    "create_ag2_mas_from_config",
    # Level 2
    "MASIntermediary",
    "RunMode",
    "AG2Intermediary",
    "WorkflowRunner",
    "MessageInterception",
    "AgentStepLog",
    "MessageLog",
    "WorkflowTrace",
    # Level 3
    "Safety_MAS",
    "MonitorSelectionMode",
    "BaseRiskTest",
    "TestCase",
    "TestResult",
    "BaseMonitorAgent",
    "Alert",
    # Utils
    "TrinitySafetyConfig",
    "get_config",
    "set_config",
    "load_config",
    "get_llm_client",
    "get_logger",
]
