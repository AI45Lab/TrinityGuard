# MAS Safety Framework Design Document

**Date**: 2026-01-23
**Status**: Approved for Implementation

---

## 1. Overview

TrinityGuard is a multi-agent system (MAS) safety framework that provides:
- **Pre-deployment safety testing**: Identify vulnerabilities before MAS goes live
- **Runtime safety monitoring**: Detect and respond to risks during execution

The framework is designed to be **framework-agnostic**, initially supporting AG2 with extensibility for LangGraph and other MAS frameworks.

### 1.1 Design Principles

1. **Separation of Concerns**: Each layer has clear responsibilities
2. **Plugin Architecture**: Risks are self-contained modules
3. **Framework Agnostic**: Level 2 abstracts framework-specific details
4. **Extensibility**: Easy to add new frameworks, risks, and monitors
5. **YAGNI**: Minimal implementation for current requirements

---

## 2. Architecture

### 2.1 Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Level 3: Safety_MAS                       │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │  Risk Test Library  │    │  Monitor Agent Repository   │ │
│  │  - 20 risk types    │    │  - 20 monitor types         │ │
│  │  - Static/dynamic   │    │  - Real-time detection      │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Level 2: MAS Intermediary                     │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │  Testing Scaffolding │    │  Monitoring Scaffolding     │ │
│  │  - Agent chat        │    │  - Structured logging       │ │
│  │  - Message injection │    │  - Stream callbacks         │ │
│  │  - WorkflowRunners   │    │  - Trajectory recording     │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Level 1: MAS Framework                       │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │      AG2 Wrapper    │    │   Future: LangGraph, etc.   │ │
│  │  - Agent access     │    │                             │ │
│  │  - Message hooks    │    │                             │ │
│  │  - Workflow exec    │    │                             │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Directory Structure

```
TrinityGuard/
├── src/
│   ├── level1_framework/          # MAS Framework Layer
│   │   ├── __init__.py
│   │   ├── base.py                # BaseMAS abstract class
│   │   ├── ag2_wrapper.py         # AG2-specific implementation
│   │   └── examples/
│   │       └── math_solver_ag2.py # Reference AG2 math solver
│   │
│   ├── level2_intermediary/       # MAS Intermediary Layer
│   │   ├── __init__.py
│   │   ├── base.py                # MASIntermediary abstract class
│   │   ├── ag2_intermediary.py    # AG2-specific intermediary
│   │   ├── workflow_runners/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # WorkflowRunner base class
│   │   │   ├── basic.py           # BasicWorkflowRunner
│   │   │   ├── intercepting.py    # InterceptingWorkflowRunner
│   │   │   ├── monitored.py       # MonitoredWorkflowRunner
│   │   │   └── combined.py        # MonitoredInterceptingRunner
│   │   └── structured_logging/
│   │       ├── __init__.py
│   │       ├── logger.py          # Structured log writer
│   │       └── schemas.py         # Log data schemas
│   │
│   ├── level3_safety/             # Safety_MAS Layer
│   │   ├── __init__.py
│   │   ├── safety_mas.py          # Main Safety_MAS class
│   │   ├── risk_tests/            # Risk Test Library
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # BaseRiskTest abstract class
│   │   │   ├── l1_jailbreak/
│   │   │   ├── l2_message_tampering/
│   │   │   ├── l3_cascading_failures/
│   │   │   └── [17 other risk folders]
│   │   │
│   │   └── monitor_agents/        # Monitor Agent Repository
│   │       ├── __init__.py
│   │       ├── base.py            # BaseMonitorAgent abstract class
│   │       ├── jailbreak_monitor/
│   │       ├── message_tampering_monitor/
│   │       ├── cascading_failures_monitor/
│   │       └── [17 other monitor folders]
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── llm_client.py          # LLM API wrapper
│   │   ├── config.py              # Configuration management
│   │   ├── exceptions.py          # Custom exceptions
│   │   └── logging_config.py      # Logging setup
│   │
│   └── __init__.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── docs/
│   └── plans/
│
├── examples/
│   └── basic_usage.py
│
├── config/
│   └── default.yaml
│
├── requirements.txt
├── setup.py
└── README.md
```

---

## 3. Level 1: MAS Framework Layer

### 3.1 Purpose

Wrap specific MAS frameworks to provide a consistent interface for upper layers.

### 3.2 Core Classes

#### 3.2.1 Data Classes

```python
@dataclass
class AgentInfo:
    """Metadata about an agent in the MAS."""
    name: str
    role: str
    system_prompt: Optional[str] = None
    tools: List[str] = None

@dataclass
class WorkflowResult:
    """Result from running a MAS workflow."""
    success: bool
    output: Any
    messages: List[Dict]  # Full message history
    metadata: Dict
    error: Optional[str] = None
```

#### 3.2.2 BaseMAS Abstract Class

```python
class BaseMAS(ABC):
    """Abstract base class for MAS framework wrappers."""

    def __init__(self):
        self._message_hooks: List[Callable[[Dict], Dict]] = []

    @abstractmethod
    def get_agents(self) -> List[AgentInfo]:
        """Return list of all agents in the system."""

    @abstractmethod
    def get_agent(self, name: str) -> Any:
        """Get a specific agent by name (returns framework-native object)."""

    @abstractmethod
    def run_workflow(self, task: str, **kwargs) -> WorkflowResult:
        """Execute the MAS workflow with given task."""

    @abstractmethod
    def get_topology(self) -> Dict:
        """Return the communication topology."""

    def register_message_hook(self, hook: Callable[[Dict], Dict]):
        """Register a hook to intercept/modify messages."""
        self._message_hooks.append(hook)

    def clear_message_hooks(self):
        """Clear all registered message hooks."""
        self._message_hooks.clear()

    def _apply_message_hooks(self, message: Dict) -> Dict:
        """Apply all registered hooks to a message."""
        for hook in self._message_hooks:
            message = hook(message)
        return message
```

### 3.3 AG2 Implementation

The AG2 wrapper will:
- Wrap AG2's `ConversableAgent`, `GroupChat`, and `GroupChatManager`
- Implement message interception via AG2's callback system
- Provide access to individual agents for testing

### 3.4 Reference Example: Math Solver

A 3-agent system for testing:
1. **Coordinator**: Receives tasks, delegates to specialists
2. **Calculator**: Performs arithmetic operations
3. **Verifier**: Double-checks results

---

## 4. Level 2: MAS Intermediary Layer

### 4.1 Purpose

Provide framework-agnostic interfaces for safety testing and runtime monitoring.

### 4.2 WorkflowRunner Pattern

#### 4.2.1 Base WorkflowRunner

```python
class WorkflowRunner(ABC):
    """Base class for workflow execution strategies."""

    def __init__(self, mas: BaseMAS):
        self.mas = mas

    @abstractmethod
    def run(self, task: str, **kwargs) -> WorkflowResult:
        """Execute the workflow."""

    def pre_run_hook(self, task: str) -> str:
        """Override to modify task before execution."""
        return task

    def post_run_hook(self, result: WorkflowResult) -> WorkflowResult:
        """Override to process result after execution."""
        return result

    def on_message(self, message: Dict) -> Dict:
        """Override to intercept/modify messages during execution."""
        return message
```

#### 4.2.2 Runner Implementations

| Runner | Purpose |
|--------|---------|
| `BasicWorkflowRunner` | Standard execution without modifications |
| `InterceptingWorkflowRunner` | Message interception/modification |
| `MonitoredWorkflowRunner` | Structured logging for monitoring |
| `MonitoredInterceptingRunner` | Combined monitoring + interception |

#### 4.2.3 InterceptingWorkflowRunner

```python
@dataclass
class MessageInterception:
    """Configuration for intercepting/modifying messages."""
    source_agent: str
    target_agent: Optional[str]  # None = all targets
    modifier: Callable[[str], str]
    condition: Optional[Callable[[Dict], bool]] = None

class InterceptingWorkflowRunner(WorkflowRunner):
    """Workflow execution with message interception."""

    def __init__(self, mas: BaseMAS, interceptions: List[MessageInterception]):
        super().__init__(mas)
        self.interceptions = interceptions

    def on_message(self, message: Dict) -> Dict:
        for interception in self.interceptions:
            if self._should_apply(interception, message):
                message["content"] = interception.modifier(message["content"])
        return message
```

#### 4.2.4 MonitoredWorkflowRunner

```python
class MonitoredWorkflowRunner(WorkflowRunner):
    """Workflow execution with structured logging."""

    def __init__(self, mas: BaseMAS, stream_callback: Optional[Callable] = None):
        super().__init__(mas)
        self.stream_callback = stream_callback
        self.logs: List[AgentStepLog] = []

    def on_message(self, message: Dict) -> Dict:
        log_entry = self._create_log_entry(message)
        self.logs.append(log_entry)
        if self.stream_callback:
            self.stream_callback(log_entry)
        return message
```

### 4.3 MASIntermediary Class

```python
class RunMode(Enum):
    BASIC = "basic"
    INTERCEPTING = "intercepting"
    MONITORED = "monitored"
    MONITORED_INTERCEPTING = "monitored_intercepting"

class MASIntermediary(ABC):
    """Framework-agnostic interface for MAS safety operations."""

    def __init__(self, mas: BaseMAS):
        self.mas = mas
        self._current_runner: Optional[WorkflowRunner] = None

    @abstractmethod
    def agent_chat(self, agent_name: str, message: str,
                   history: Optional[List] = None) -> str:
        """Direct point-to-point chat with an agent."""

    @abstractmethod
    def simulate_agent_message(self, from_agent: str, to_agent: str,
                               message: str) -> Dict:
        """Simulate a message from one agent to another."""

    def create_runner(self, mode: RunMode, **kwargs) -> WorkflowRunner:
        """Factory method to create appropriate WorkflowRunner."""
        # Returns appropriate runner based on mode

    def run_workflow(self, task: str, mode: RunMode = RunMode.BASIC,
                     **kwargs) -> WorkflowResult:
        """Execute workflow with specified mode."""
        runner = self.create_runner(mode, **kwargs)
        self._current_runner = runner
        try:
            return runner.run(task, **kwargs)
        finally:
            self._current_runner = None

    def get_structured_logs(self) -> List[Dict]:
        """Get logs from last monitored run."""
```

### 4.4 Structured Logging Schemas

```python
@dataclass
class AgentStepLog:
    """Log entry for a single agent action."""
    timestamp: float
    agent_name: str
    step_type: str  # "receive", "think", "tool_call", "respond"
    content: Any
    metadata: Dict

@dataclass
class MessageLog:
    """Log entry for inter-agent communication."""
    timestamp: float
    from_agent: str
    to_agent: str
    message: str
    message_id: str
```

---

## 5. Level 3: Safety_MAS Layer

### 5.1 Purpose

Provide unified safety interface combining pre-deployment testing and runtime monitoring.

### 5.2 Safety_MAS Class

```python
class MonitorSelectionMode(Enum):
    MANUAL = "manual"
    AUTO_LLM = "auto_llm"
    PROGRESSIVE = "progressive"

class Safety_MAS:
    """Main safety wrapper for MAS systems."""

    def __init__(self, mas: BaseMAS):
        self.mas = mas
        self.intermediary = self._create_intermediary(mas)
        self.risk_tests = self._load_risk_tests()
        self.monitor_agents = self._load_monitor_agents()
        self._active_monitors: List[BaseMonitorAgent] = []

    # === Pre-deployment Testing API ===

    def run_auto_safety_tests(self, task_description: Optional[str] = None) -> Dict:
        """Automatically select and run relevant safety tests."""

    def run_manual_safety_tests(self, selected_tests: List[str]) -> Dict:
        """Run specific safety tests."""

    def get_test_report(self) -> str:
        """Generate human-readable test report."""

    # === Runtime Monitoring API ===

    def start_runtime_monitoring(self,
                                 mode: MonitorSelectionMode = MonitorSelectionMode.MANUAL,
                                 selected_monitors: Optional[List[str]] = None):
        """Configure runtime monitoring."""

    def run_task(self, task: str, **kwargs) -> WorkflowResult:
        """Execute MAS task with active monitoring."""
```

### 5.3 Usage Example

```python
from trinityguard import Safety_MAS
from trinityguard.level1_framework import AG2MAS

# Create MAS instance
math_solver = AG2MAS(config="math_solver_config.yaml")

# Wrap with safety
safety_math_solver = Safety_MAS(mas=math_solver)

# Pre-deployment testing
results = safety_math_solver.run_auto_safety_tests()
print(safety_math_solver.get_test_report())

# Or manual test selection
results = safety_math_solver.run_manual_safety_tests([
    "jailbreak",
    "message_tampering"
])

# Runtime monitoring
safety_math_solver.start_runtime_monitoring(
    mode=MonitorSelectionMode.AUTO_LLM
)

# Execute task with monitoring
result = safety_math_solver.run_task("Calculate 25 * 4 and verify")
print(result.monitoring_report)
```

### 5.4 Risk Test Base Class

```python
@dataclass
class TestCase:
    name: str
    input: str
    expected_behavior: str
    severity: str  # "low", "medium", "high", "critical"

@dataclass
class TestResult:
    risk_name: str
    passed: bool
    total_cases: int
    failed_cases: int
    details: List[Dict]
    severity_summary: Dict[str, int]

class BaseRiskTest(ABC):
    """Abstract base class for risk tests."""

    @abstractmethod
    def get_risk_info(self) -> Dict[str, str]:
        """Return risk metadata."""

    @abstractmethod
    def load_test_cases(self) -> List[TestCase]:
        """Load static test cases."""

    @abstractmethod
    def generate_dynamic_cases(self, mas_description: str) -> List[TestCase]:
        """Generate test cases using LLM."""

    @abstractmethod
    def run_single_test(self, test_case: TestCase,
                        intermediary: MASIntermediary) -> Dict:
        """Execute a single test case."""

    def run(self, intermediary: MASIntermediary,
            use_dynamic: bool = False) -> TestResult:
        """Run all test cases for this risk."""
```

### 5.5 Monitor Agent Base Class

```python
@dataclass
class Alert:
    severity: str  # "info", "warning", "critical"
    risk_type: str
    message: str
    evidence: Dict
    recommended_action: str  # "log", "warn", "block"

class BaseMonitorAgent(ABC):
    """Abstract base class for runtime monitors."""

    @abstractmethod
    def get_monitor_info(self) -> Dict[str, str]:
        """Return monitor metadata."""

    @abstractmethod
    def process(self, log_entry: AgentStepLog) -> Optional[Alert]:
        """Process a log entry and return alert if risk detected."""

    def reset(self):
        """Reset monitor state between runs."""
        self.state = {}
```

---

## 6. Initial Risk Implementations

### 6.1 Scope

- Full infrastructure for all 20 risks (directory structure, stub classes)
- Complete implementation for 3 representative risks:
  - **L1: Jailbreak** (single-agent attack)
  - **L2: Message Tampering** (inter-agent communication)
  - **L3: Cascading Failures** (system-level)

### 6.2 L1: Jailbreak Test & Monitor

**Test Approach:**
- Send jailbreak prompts (DAN, role-play, etc.) to each agent via `agent_chat()`
- Use LLM to judge if agent was compromised
- Test cases: static library + dynamic generation

**Monitor Approach:**
- Pattern matching for known jailbreak attempts in incoming messages
- LLM-based detection of compromised responses
- Alert levels: warning (attempt detected), critical (agent compromised)

### 6.3 L2: Message Tampering Test & Monitor

**Test Approach:**
- Use `InterceptingWorkflowRunner` to inject malicious payloads
- Observe if tampering causes downstream harm
- Test various injection points and payload types

**Monitor Approach:**
- Track message patterns and detect anomalies
- Compare expected vs actual message content
- Detect unexpected content injection

### 6.4 L3: Cascading Failures Test & Monitor

**Test Approach:**
- Inject failures in individual agents
- Observe propagation to other agents
- Measure cascade extent and recovery

**Monitor Approach:**
- Track agent failures in real-time
- Detect cascade patterns (multiple sequential failures)
- Alert when failure count exceeds threshold

---

## 7. Error Handling

### 7.1 Exception Hierarchy

```python
class TrinitySafetyError(Exception):
    """Base exception for TrinityGuard."""

class MASFrameworkError(TrinitySafetyError):
    """Errors from Level 1 MAS framework."""

class IntermediaryError(TrinitySafetyError):
    """Errors from Level 2 intermediary operations."""

class RiskTestError(TrinitySafetyError):
    """Errors during risk testing."""

class MonitorError(TrinitySafetyError):
    """Errors from monitor agents."""
```

### 7.2 Error Recovery Strategies

1. **Test Isolation**: If one test fails, continue with others
2. **Monitor Isolation**: If one monitor crashes, others continue
3. **Graceful Degradation**: Capture errors with context, don't crash
4. **Timeout Protection**: All operations have configurable timeouts

---

## 8. Configuration

### 8.1 Configuration File (config/default.yaml)

```yaml
llm:
  provider: "openai"  # or "anthropic", "local"
  model: "gpt-4"
  api_key_env: "MASSAFETY_LLM_API_KEY"

logging:
  level: "INFO"
  file: "massafety.log"
  format: "json"

testing:
  timeout: 300  # seconds per test
  parallel: false

monitoring:
  buffer_size: 1000  # log entries
  alert_threshold: 3  # alerts before auto-block
```

### 8.2 Environment Variables

| Variable | Description |
|----------|-------------|
| `MASSAFETY_LLM_API_KEY` | LLM API key |
| `MASSAFETY_LLM_PROVIDER` | LLM provider (openai/anthropic) |
| `MASSAFETY_LOG_LEVEL` | Logging level |

---

## 9. Implementation Plan

### Phase 1: Core Infrastructure
1. Set up project structure and dependencies
2. Implement Level 1 base classes and AG2 wrapper
3. Implement Level 2 base classes and WorkflowRunners
4. Implement Level 3 Safety_MAS skeleton

### Phase 2: Risk Implementations
5. Implement Jailbreak test and monitor
6. Implement Message Tampering test and monitor
7. Implement Cascading Failures test and monitor
8. Create stub classes for remaining 17 risks

### Phase 3: Integration & Testing
9. Create AG2 math solver example
10. Write unit tests
11. Write integration tests
12. Create usage examples and documentation

---

## 10. Risk Coverage Matrix

| Level | Risk Name | Test | Monitor | Status |
|-------|-----------|------|---------|--------|
| L1 | Prompt Injection | Stub | Stub | Planned |
| L1 | **Jailbreak** | Full | Full | **Implement** |
| L1 | Sensitive Info Disclosure | Stub | Stub | Planned |
| L1 | Excessive Agency | Stub | Stub | Planned |
| L1 | Unauthorized Code Execution | Stub | Stub | Planned |
| L1 | Hallucination | Stub | Stub | Planned |
| L1 | Memory Poisoning | Stub | Stub | Planned |
| L1 | Tool Misuse | Stub | Stub | Planned |
| L2 | Malicious Propagation | Stub | Stub | Planned |
| L2 | Misinformation Amplification | Stub | Stub | Planned |
| L2 | Insecure Output Handling | Stub | Stub | Planned |
| L2 | Goal Drift | Stub | Stub | Planned |
| L2 | **Message Tampering** | Full | Full | **Implement** |
| L2 | Identity Spoofing | Stub | Stub | Planned |
| L3 | **Cascading Failures** | Full | Full | **Implement** |
| L3 | Inadequate Sandboxing | Stub | Stub | Planned |
| L3 | Insufficient Monitoring | Stub | Stub | Planned |
| L3 | Group Hallucination | Stub | Stub | Planned |
| L3 | Malicious Emergence | Stub | Stub | Planned |
| L3 | Rogue Agent | Stub | Stub | Planned |

---

## 11. Dependencies

```
# requirements.txt
ag2>=0.2.0
pydantic>=2.0
pyyaml>=6.0
openai>=1.0  # or anthropic
pytest>=7.0
pytest-asyncio>=0.21
```

---

*Document generated: 2026-01-23*
