# MAS Safety Framework Implementation Plan

**Date**: 2026-01-23
**Based on**: 2026-01-23-mas-safety-framework-design.md

---

## Implementation Tasks

### Phase 1: Project Setup & Core Infrastructure

#### Task 1.1: Project Structure Setup
- [ ] Create directory structure
- [ ] Create requirements.txt
- [ ] Create setup.py
- [ ] Create config/default.yaml

#### Task 1.2: Utils Module
- [ ] src/utils/__init__.py
- [ ] src/utils/exceptions.py - Custom exception hierarchy
- [ ] src/utils/config.py - Configuration management
- [ ] src/utils/llm_client.py - LLM API wrapper
- [ ] src/utils/logging_config.py - Structured logging

#### Task 1.3: Level 1 - MAS Framework Layer
- [ ] src/level1_framework/__init__.py
- [ ] src/level1_framework/base.py - BaseMAS, AgentInfo, WorkflowResult
- [ ] src/level1_framework/ag2_wrapper.py - AG2MAS implementation
- [ ] src/level1_framework/examples/math_solver_ag2.py - Reference example

#### Task 1.4: Level 2 - Intermediary Layer
- [ ] src/level2_intermediary/__init__.py
- [ ] src/level2_intermediary/structured_logging/schemas.py - Log schemas
- [ ] src/level2_intermediary/structured_logging/logger.py - Log writer
- [ ] src/level2_intermediary/workflow_runners/base.py - WorkflowRunner base
- [ ] src/level2_intermediary/workflow_runners/basic.py
- [ ] src/level2_intermediary/workflow_runners/intercepting.py
- [ ] src/level2_intermediary/workflow_runners/monitored.py
- [ ] src/level2_intermediary/workflow_runners/combined.py
- [ ] src/level2_intermediary/base.py - MASIntermediary base
- [ ] src/level2_intermediary/ag2_intermediary.py - AG2 implementation

#### Task 1.5: Level 3 - Safety Layer Base
- [ ] src/level3_safety/__init__.py
- [ ] src/level3_safety/risk_tests/base.py - BaseRiskTest
- [ ] src/level3_safety/monitor_agents/base.py - BaseMonitorAgent
- [ ] src/level3_safety/safety_mas.py - Safety_MAS class

### Phase 2: Risk Implementations

#### Task 2.1: Jailbreak (L1)
- [ ] src/level3_safety/risk_tests/l1_jailbreak/__init__.py
- [ ] src/level3_safety/risk_tests/l1_jailbreak/test.py
- [ ] src/level3_safety/risk_tests/l1_jailbreak/test_cases.json
- [ ] src/level3_safety/risk_tests/l1_jailbreak/config.yaml
- [ ] src/level3_safety/monitor_agents/jailbreak_monitor/__init__.py
- [ ] src/level3_safety/monitor_agents/jailbreak_monitor/monitor.py
- [ ] src/level3_safety/monitor_agents/jailbreak_monitor/patterns.json
- [ ] src/level3_safety/monitor_agents/jailbreak_monitor/config.yaml

#### Task 2.2: Message Tampering (L2)
- [ ] src/level3_safety/risk_tests/l2_message_tampering/__init__.py
- [ ] src/level3_safety/risk_tests/l2_message_tampering/test.py
- [ ] src/level3_safety/risk_tests/l2_message_tampering/test_cases.json
- [ ] src/level3_safety/risk_tests/l2_message_tampering/config.yaml
- [ ] src/level3_safety/monitor_agents/message_tampering_monitor/__init__.py
- [ ] src/level3_safety/monitor_agents/message_tampering_monitor/monitor.py
- [ ] src/level3_safety/monitor_agents/message_tampering_monitor/config.yaml

#### Task 2.3: Cascading Failures (L3)
- [ ] src/level3_safety/risk_tests/l3_cascading_failures/__init__.py
- [ ] src/level3_safety/risk_tests/l3_cascading_failures/test.py
- [ ] src/level3_safety/risk_tests/l3_cascading_failures/test_cases.json
- [ ] src/level3_safety/risk_tests/l3_cascading_failures/config.yaml
- [ ] src/level3_safety/monitor_agents/cascading_failures_monitor/__init__.py
- [ ] src/level3_safety/monitor_agents/cascading_failures_monitor/monitor.py
- [ ] src/level3_safety/monitor_agents/cascading_failures_monitor/config.yaml

#### Task 2.4: Stub Classes for Remaining 17 Risks
- [ ] Create stub directories and base files for all remaining risks

### Phase 3: Integration & Examples

#### Task 3.1: Main Package Init
- [ ] src/__init__.py - Package exports

#### Task 3.2: Examples
- [ ] examples/basic_usage.py

#### Task 3.3: Tests
- [ ] tests/conftest.py
- [ ] tests/unit/test_level1.py
- [ ] tests/unit/test_level2.py
- [ ] tests/unit/test_level3.py
- [ ] tests/integration/test_safety_mas.py

---

## Execution Order

The tasks should be executed in this order due to dependencies:

1. **Task 1.1** - Project structure (no dependencies)
2. **Task 1.2** - Utils (depends on 1.1)
3. **Task 1.3** - Level 1 (depends on 1.2)
4. **Task 1.4** - Level 2 (depends on 1.3)
5. **Task 1.5** - Level 3 base (depends on 1.4)
6. **Tasks 2.1-2.4** - Risk implementations (depend on 1.5, can run in parallel)
7. **Tasks 3.1-3.3** - Integration (depend on Phase 2)

---

## Notes

- Each task produces working, testable code
- Tasks within the same phase can often be parallelized
- All code follows the design document specifications
