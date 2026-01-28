# EvoAgentX Adapter Design

**Date**: 2026-01-28
**Author**: MASSafetyGuard Team
**Status**: Approved for Implementation

## Overview

This design adds support for EvoAgentX workflow.json files to MASSafetyGuard's level1_framework layer, allowing workflows from EvoAgentX to be converted and executed through the existing AG2MAS infrastructure.

## Goals

1. Enable MASSafetyGuard to consume EvoAgentX workflow.json files
2. Convert EvoAgentX workflows to AG2MAS instances (BaseMAS interface)
3. Maintain clean separation of concerns with testable components
4. Provide easy extension points for future features (DocAgent, complex transitions)

## Design Strategy

**Approach**: Layered conversion (Parser → Intermediate Representation → AG2MAS)

This provides:
- Clear separation of parsing and conversion logic
- Easy unit testing of each component
- Simple extension path for DocAgent support later
- Reuse of existing AG2MAS infrastructure

## Architecture

### File Structure

```
src/level1_framework/
├── base.py                          # Existing
├── ag2_wrapper.py                   # Existing
├── evoagentx_adapter.py            # NEW: EvoAgentX adapter
└── examples/
    └── evoagentx_workflow.py       # NEW: Usage example
```

### Component Overview

```
workflow.json
  → WorkflowParser.parse()
  → ParsedWorkflow (intermediate representation)
  → WorkflowToAG2Converter.convert()
  → AG2MAS (BaseMAS interface)
  → Safety_MAS (existing integration)
```

## Data Structures

### AgentConfig

Represents a single agent from original_nodes:

```python
@dataclass
class AgentConfig:
    """Agent definition from original_nodes"""
    name: str
    description: str
    inputs: List[Dict]      # Parameter objects
    outputs: List[Dict]     # Parameter objects
    prompt: str             # System prompt for the agent
```

### WorkflowNode

Represents a workflow node from original_nodes:

```python
@dataclass
class WorkflowNode:
    """Workflow node from original_nodes"""
    name: str
    description: str
    inputs: List[Dict]
    outputs: List[Dict]
    reason: str
    agents: List[AgentConfig]  # Each node may contain multiple agents
    status: str = "pending"
```

### ParsedWorkflow

Complete parsed workflow representation:

```python
@dataclass
class ParsedWorkflow:
    """Complete workflow parsing result"""
    goal: str
    nodes: List[WorkflowNode]        # From original_nodes
    uploaded_files: Dict[str, str]
    metadata: Dict
```

## Core Components

### 1. WorkflowParser

**Responsibility**: Read and validate workflow.json files

```python
class WorkflowParser:
    """Parse and validate workflow.json"""

    def parse(self, json_path: str) -> ParsedWorkflow:
        """Main entry: read file and parse to intermediate representation"""
        # Read JSON
        # Extract workflow, execution_context
        # Parse original_nodes
        # Return ParsedWorkflow

    def _parse_original_nodes(self, nodes_data: List[Dict]) -> List[WorkflowNode]:
        """Parse original_nodes section"""
        # Iterate through nodes
        # Extract agents from each node
        # Build WorkflowNode objects
```

**Design Notes**:
- Uses `.get()` with defaults for fault tolerance
- Explicitly uses utf-8 encoding for Chinese support
- Only parses original_nodes (not simplified nodes)

### 2. WorkflowToAG2Converter

**Responsibility**: Convert ParsedWorkflow to AG2MAS

```python
class WorkflowToAG2Converter:
    """Convert ParsedWorkflow to AG2MAS"""

    def __init__(self, llm_config: Optional[Dict] = None):
        """Initialize with LLM config"""
        self.llm_config = llm_config or self._get_default_llm_config()
        self.logger = get_logger("EvoAgentXConverter")

    def convert(self, workflow: ParsedWorkflow) -> AG2MAS:
        """Main conversion method"""
        # 1. Create agents from nodes
        # 2. Build sequential transitions
        # 3. Create GroupChat with transitions
        # 4. Create GroupChatManager
        # 5. Return AG2MAS

    def _create_agents_from_nodes(self, nodes: List[WorkflowNode]) -> List[ConversableAgent]:
        """Extract and create all agents from nodes"""
        # Iterate through nodes
        # For each agent in node.agents:
        #   Create ConversableAgent with agent.prompt as system_message

    def _build_sequential_transitions(
        self,
        agents: List[ConversableAgent]
    ) -> Dict[ConversableAgent, List[ConversableAgent]]:
        """Build sequential transitions: A → B → C → ..."""
        # agents[0] → [agents[1]]
        # agents[1] → [agents[2]]
        # ...
        # agents[-1] → []
```

**Design Notes**:
- Sequential execution: agents execute in array order
- Integrates with existing logging infrastructure
- Reuses MASLLMConfig for LLM configuration
- Extension point: `_create_agents_from_nodes()` can be enhanced to support DocAgent

### 3. Convenience Function

```python
def create_ag2_mas_from_evoagentx(
    workflow_path: str,
    llm_config: Optional[Dict] = None
) -> AG2MAS:
    """
    Create AG2MAS instance from EvoAgentX workflow.json

    Args:
        workflow_path: Path to workflow.json file
        llm_config: Optional LLM config, defaults to MASLLMConfig

    Returns:
        AG2MAS instance ready for use with Safety_MAS

    Example:
        >>> mas = create_ag2_mas_from_evoagentx("workflow/my_workflow.json")
        >>> safety_mas = Safety_MAS(mas=mas)
        >>> result = safety_mas.run_task("Analyze document")
    """
    parser = WorkflowParser()
    workflow = parser.parse(workflow_path)

    converter = WorkflowToAG2Converter(llm_config)
    return converter.convert(workflow)
```

## Workflow Execution Model

### Input: EvoAgentX workflow.json

From the example workflow:

```json
{
  "workflow": {
    "original_nodes": [
      {
        "name": "pdf_text_extraction",
        "agents": [{"name": "pdf_text_extraction_agent", "prompt": "..."}]
      },
      {
        "name": "content_analysis",
        "agents": [{"name": "content_analysis_agent", "prompt": "..."}]
      },
      {
        "name": "summary_generation",
        "agents": [{"name": "summary_generation_agent", "prompt": "..."}]
      }
    ]
  }
}
```

### Output: AG2 Sequential Workflow

Converted to AG2 speaker_transitions:

```python
{
  pdf_text_extraction_agent: [content_analysis_agent],
  content_analysis_agent: [summary_generation_agent],
  summary_generation_agent: []
}
```

Execution flow: `pdf_text_extraction_agent → content_analysis_agent → summary_generation_agent`

## Integration with MASSafetyGuard

### Module Exports

Add to `level1_framework/__init__.py`:

```python
from .evoagentx_adapter import (
    create_ag2_mas_from_evoagentx,
    WorkflowParser,
    WorkflowToAG2Converter,
    ParsedWorkflow,
    WorkflowNode,
    AgentConfig
)

__all__ = [
    # Existing exports
    "BaseMAS", "AgentInfo", "WorkflowResult",
    "AG2MAS", "create_ag2_mas_from_config",
    # New exports
    "create_ag2_mas_from_evoagentx",
    "WorkflowParser",
    "WorkflowToAG2Converter",
]
```

### Usage Example

```python
from src.level1_framework import create_ag2_mas_from_evoagentx
from src.level3_safety import Safety_MAS

# 1. Create MAS from workflow.json
mas = create_ag2_mas_from_evoagentx("workflow/my_workflow.json")

# 2. Inspect created agents
agents = mas.get_agents()
print(f"Created {len(agents)} agents")

# 3. Run workflow
result = mas.run_workflow("分析 daily_paper_digest.pdf 并生成总结")
print(f"Success: {result.success}")

# 4. Optional: Integrate with Safety_MAS for security testing
safety_mas = Safety_MAS(mas=mas)
safety_mas.register_risk_test("jailbreak", JailbreakTest())
safety_mas.run_manual_safety_tests(["jailbreak"])
```

## Current Scope (v1)

**Included**:
- ✅ Parse original_nodes from workflow.json
- ✅ Convert to ConversableAgent instances
- ✅ Build sequential speaker_transitions
- ✅ Create AG2MAS with GroupChat
- ✅ Integrate with existing logging and LLM config
- ✅ Simple convenience function interface

**Excluded (Future Extensions)**:
- ❌ DocAgent support (requires advanced_agent_config parsing)
- ❌ Complex condition-based transitions (only "always" supported)
- ❌ uploaded_files integration (parsed but not passed to agents)
- ❌ Dynamic transition graph from inputs/outputs dependencies

## Extension Points

### Future: DocAgent Support

To add DocAgent support later:

1. Modify `_create_agents_from_nodes()`:
```python
def _create_agents_from_nodes(self, nodes: List[WorkflowNode]) -> List[ConversableAgent]:
    agents = []
    for node in nodes:
        for agent_config in node.agents:
            # Check if this should be a DocAgent
            if self._is_doc_agent(agent_config):
                agent = self._create_doc_agent(agent_config)
            else:
                agent = ConversableAgent(...)
            agents.append(agent)
    return agents
```

2. Add helper methods:
```python
def _is_doc_agent(self, agent_config: AgentConfig) -> bool:
    # Check agent_config metadata or name patterns

def _create_doc_agent(self, agent_config: AgentConfig) -> DocAgent:
    # Import and create DocAgent with proper config
```

### Future: Complex Transitions

To support conditional transitions:

1. Add `condition` field to WorkflowEdge
2. Parse `edges` from workflow.json (not just original_nodes order)
3. Implement custom `speaker_selection_method` for AG2

## Design Benefits

1. **Separation of Concerns**: Parser and converter are independent, testable units
2. **Minimal Code**: ~250 lines total, reuses existing AG2MAS infrastructure
3. **Easy Extension**: Clear extension points for DocAgent and complex transitions
4. **Consistent Style**: Matches existing MASSafetyGuard architecture patterns
5. **Type Safety**: Dataclasses provide clear contracts and IDE support

## Testing Strategy

### Unit Tests
- `test_workflow_parser.py`: Test JSON parsing with various inputs
- `test_workflow_converter.py`: Test AG2MAS conversion logic

### Integration Tests
- `test_evoagentx_integration.py`: Test full workflow.json → AG2MAS → run_workflow
- Use actual workflow/my_workflow.json for realistic testing

### Example Usage
- `examples/evoagentx_workflow.py`: Demonstrates complete usage

## Dependencies

**New Dependencies**: None (uses existing MASSafetyGuard dependencies)

**Existing Dependencies**:
- `autogen` / `pyautogen`: For ConversableAgent, GroupChat, GroupChatManager
- `src.utils.llm_config`: For MASLLMConfig
- `src.utils.logging_config`: For get_logger
- `src.level1_framework.ag2_wrapper`: For AG2MAS

## Implementation Checklist

- [ ] Implement `evoagentx_adapter.py` with all dataclasses and classes
- [ ] Update `level1_framework/__init__.py` exports
- [ ] Create `examples/evoagentx_workflow.py` usage example
- [ ] Test with actual `workflow/my_workflow.json`
- [ ] Verify integration with Safety_MAS
- [ ] Add inline documentation and type hints

## Success Criteria

1. ✅ Can successfully parse workflow/my_workflow.json
2. ✅ Creates correct number of AG2 agents (3 for the example workflow)
3. ✅ Builds correct sequential transitions
4. ✅ run_workflow() executes agents in correct order
5. ✅ Returns WorkflowResult with expected output
6. ✅ Integrates seamlessly with existing Safety_MAS

## Conclusion

This design provides a clean, maintainable way to integrate EvoAgentX workflows into MASSafetyGuard. By using a layered conversion approach and reusing existing AG2MAS infrastructure, we achieve the goal with minimal code while maintaining extensibility for future enhancements like DocAgent support.
