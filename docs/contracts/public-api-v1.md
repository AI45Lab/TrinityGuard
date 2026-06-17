# TrinityGuard Public API Contract v1

Status: research-prototype API contract for the v2 refactor closeout path.

This contract defines canonical imports for TrinityGuard-Dev after Phase 4 refactor consolidation. It is **not production deployment**, **not CI/release**, and **not Garak/OpenRT comparison**.

## Canonical façade imports

Use the top-level package for the research façade and base execution contracts:

```python
from trinityguard import Safety_MAS, MonitorSelectionMode
from trinityguard import BaseMAS, AgentInfo, WorkflowResult
from trinityguard import RuntimeProtector, RuntimeProtectionSettings
```

`Safety_MAS` is a research compatibility façade. It is not a production rollout adapter.

## Canonical Level 1 imports

Use `trinityguard.level1_framework.base` for framework-independent contracts:

```python
from trinityguard.level1_framework.base import BaseMAS, WorkflowResult
```

Use the canonical AG2 adapter path for AG2-specific integrations:

```python
from trinityguard.level1_framework.ag2.adapter import AG2MAS, create_ag2_mas_from_config
```

The package-level `trinityguard.level1_framework` also lazily exposes AG2 names for compatibility discovery, but internal code should import concrete adapters from their canonical modules.

## Canonical runtime adapter imports

The runtime hook protocol is canonical in `trinityguard.runtime.adapter_contract`:

```python
from trinityguard.runtime.adapter_contract import MessageHookResult
from trinityguard.runtime.adapter_contract import MessageDeliveryDeniedError
from trinityguard.runtime.adapter_contract import normalize_message_hook_result
```

Legacy Level 1 re-exports remain compatibility only.

## Canonical Level 3 imports

Use `trinityguard.level3_safety` for the safety façade and base Level 3 types:

```python
from trinityguard.level3_safety import Safety_MAS, MonitorSelectionMode
from trinityguard.level3_safety import BaseAttack, AttackCase, AttackRunResult
from trinityguard.level3_safety import BaseMonitorAgent, Alert
```

Implementation details such as `test_orchestration`, `monitor_orchestration`, and `safety_reports` are owner modules for internal refactor boundaries, not recommended public extension points.

## Deprecated compatibility imports

The following modules are deprecated compatibility exports for older code and documents:

- `trinityguard.level1_framework.ag2_wrapper`
- `trinityguard.utils.ag2_io_filter`

They must not be used by new internal code. Existing guardrail tests keep internal imports on canonical paths.

## Non-goals

- not production deployment;
- not production telemetry or audit storage;
- not CI/release;
- not Garak/OpenRT comparison;
- not a stable semantic-versioned production SDK promise.
