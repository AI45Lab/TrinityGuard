# Level1 EvoAgentX Adapter - 待完善功能清单

**创建日期**: 2026-01-28
**当前版本**: v1.0 (基础版本)
**状态**: 基础功能已实现，扩展功能待开发

---

## 已实现功能 ✅

- [x] 解析 workflow.json 的 original_nodes
- [x] 将 nodes 转换为 AG2 ConversableAgent
- [x] 构建顺序转移关系 (A → B → C)
- [x] 创建 AG2MAS 实例
- [x] 集成现有 MASLLMConfig
- [x] 改进 AG2MAS.get_topology() 支持自定义转移
- [x] 基础测试套件 (3/3 通过)
- [x] 使用示例和文档

---

## 待完善功能 📋

### 优先级 1: 核心功能扩展 🔴

#### 1.1 DocAgent 支持

**描述**: 支持 workflow.json 中的高级 agent (DocAgent)

**当前状态**:
- 已解析 `is_advanced_agent` 和 `advanced_agent_config` 字段
- 但所有节点都转换为普通 ConversableAgent

**需要实现**:
```python
# 在 WorkflowToAG2Converter._create_agents_from_nodes() 中
def _create_agents_from_nodes(self, nodes: List[WorkflowNode]):
    agents = []
    for node in nodes:
        for agent_config in node.agents:
            if self._should_use_doc_agent(node, agent_config):
                agent = self._create_doc_agent(node, agent_config)
            else:
                agent = ConversableAgent(...)
            agents.append(agent)
    return agents

def _should_use_doc_agent(self, node, agent_config):
    # 检查 node.is_advanced_agent 或 advanced_agent_config
    pass

def _create_doc_agent(self, node, agent_config):
    # 从 autogen.agentchat.contrib 导入 DocAgent
    # 解析 advanced_agent_config 中的配置
    # 创建 DocAgent 实例
    pass
```

**涉及文件**:
- `src/level1_framework/evoagentx_adapter.py`

**预计工作量**: 4-6 小时

**依赖**:
- 需要了解 AG2 中 DocAgent 的 API
- 需要处理 collection_name, parsed_docs_path 等配置

---

#### 1.2 uploaded_files 处理

**描述**: 将 workflow.json 中的 uploaded_files 传递给需要的 agents

**当前状态**:
- 已解析 uploaded_files 字段存储在 ParsedWorkflow 中
- 但没有传递给任何 agent

**需要实现**:
```python
# 在创建 agent 时，将文件路径作为上下文传递
def _create_agents_from_nodes(self, nodes, uploaded_files):
    for node in nodes:
        # 检查节点是否需要文件
        if self._node_requires_files(node):
            # 将文件列表注入到 agent 的 system_message 或配置中
            file_context = self._build_file_context(uploaded_files)
            agent.system_message += f"\n\nAvailable files: {file_context}"
```

**涉及文件**:
- `src/level1_framework/evoagentx_adapter.py`

**预计工作量**: 2-3 小时

---

#### 1.3 复杂转移条件支持

**描述**: 支持基于条件的 agent 转移，而不仅是顺序执行

**当前状态**:
- 只支持固定顺序: A → B → C
- workflow.json 中的 `condition: "always"` 没有被充分利用

**需要实现**:
```python
# 支持更复杂的转移规则
# 例如: 基于输出内容决定下一个 agent
class ConditionalTransitionBuilder:
    def build_transitions(self, edges, nodes):
        # 解析 edges 中的 condition 字段
        # 如果 condition != "always", 创建自定义 speaker_selection_method
        pass
```

**可能的实现方式**:
1. 使用 AG2 的 `speaker_selection_method` 参数
2. 实现自定义的选择函数
3. 支持条件表达式解析

**涉及文件**:
- `src/level1_framework/evoagentx_adapter.py`

**预计工作量**: 6-8 小时

**优先级**: 中 (当前顺序执行已够用)

---

### 优先级 2: 配置和兼容性 🟡

#### 2.1 execution_context 完整支持

**描述**: 处理 execution_context 中的其他配置项

**当前状态**:
- 只使用了 `goal` 字段
- 忽略了 `zh`, `parser_config`, `enable_advanced_agents` 等

**需要实现**:
```python
class WorkflowParser:
    def parse(self, json_path):
        exec_context = data.get("execution_context", {})

        # 处理中文模式
        zh_mode = exec_context.get("zh", False)

        # 处理 parser 配置
        parser_config = exec_context.get("parser_config", {})

        # 处理 capabilities_dir
        capabilities_dir = exec_context.get("capabilities_dir")

        # 存储到 ParsedWorkflow
        workflow.execution_context = exec_context
```

**涉及文件**:
- `src/level1_framework/evoagentx_adapter.py`

**预计工作量**: 2-3 小时

---

#### 2.2 LLM 配置灵活性

**描述**: 允许从 workflow.json 或 execution_context 中读取 LLM 配置

**当前状态**:
- 使用全局的 mas_llm_config.yaml
- 无法针对特定 workflow 定制 LLM 配置

**需要实现**:
```python
def create_ag2_mas_from_evoagentx(
    workflow_path: str,
    llm_config: Optional[Dict] = None,
    use_workflow_llm_config: bool = False  # 新参数
):
    if use_workflow_llm_config:
        # 从 workflow.json 的 metadata 或 execution_context 读取
        llm_config = extract_llm_config_from_workflow(workflow)
```

**涉及文件**:
- `src/level1_framework/evoagentx_adapter.py`

**预计工作量**: 1-2 小时

---

### 优先级 3: 健壮性和测试 🟢

#### 3.1 错误处理增强

**描述**: 添加更完善的错误处理和验证

**需要实现**:
- 验证 workflow.json 格式是否正确
- 检查必需字段是否存在
- 处理边界情况 (空 nodes, 循环依赖等)
- 提供清晰的错误消息

**示例**:
```python
class WorkflowValidator:
    def validate(self, workflow: ParsedWorkflow):
        if not workflow.nodes:
            raise ValueError("Workflow must contain at least one node")

        if self._has_circular_dependency(workflow):
            raise ValueError("Circular dependency detected in workflow")

        # 更多验证...
```

**涉及文件**:
- `src/level1_framework/evoagentx_adapter.py`
- 新增: `src/level1_framework/evoagentx_validator.py`

**预计工作量**: 3-4 小时

---

#### 3.2 扩展测试覆盖

**描述**: 添加更多测试用例

**需要添加的测试**:
- [ ] 空 workflow 处理
- [ ] 只有一个 node 的 workflow
- [ ] nodes 中 agents 列表为空
- [ ] 中文字符处理
- [ ] 超大 workflow (>10 nodes)
- [ ] 缺失必需字段的处理
- [ ] 不同 LLM config 的测试

**涉及文件**:
- `test_evoagentx_adapter.py`
- 新增: `tests/level1_framework/test_evoagentx_edge_cases.py`

**预计工作量**: 4-5 小时

---

#### 3.3 日志和调试支持

**描述**: 增强日志记录，方便调试

**需要添加**:
```python
# 更详细的转换日志
self.logger.debug(f"Converting node '{node.name}' with {len(node.agents)} agents")
self.logger.debug(f"Agent '{agent.name}' system_message length: {len(prompt)}")

# 转换过程的可视化
def visualize_workflow(workflow: ParsedWorkflow):
    """生成 workflow 的可视化表示"""
    # 使用 graphviz 或纯文本 ASCII art
    pass
```

**涉及文件**:
- `src/level1_framework/evoagentx_adapter.py`

**预计工作量**: 2-3 小时

---

### 优先级 4: 高级特性 ⚪

#### 4.1 动态依赖图推断

**描述**: 根据 nodes 的 inputs/outputs 自动推断执行依赖关系

**当前状态**:
- 固定顺序执行 (按数组顺序)
- 不考虑 inputs/outputs 依赖

**需要实现**:
```python
class DependencyGraphBuilder:
    def build_from_io(self, nodes: List[WorkflowNode]):
        """
        分析每个 node 的 inputs 和 outputs
        构建依赖关系图
        返回拓扑排序后的执行顺序
        """
        dependency_graph = {}
        for node in nodes:
            dependencies = self._find_dependencies(node, nodes)
            dependency_graph[node.name] = dependencies

        # 拓扑排序
        execution_order = self._topological_sort(dependency_graph)
        return execution_order
```

**涉及文件**:
- 新增: `src/level1_framework/evoagentx_dependency.py`
- `src/level1_framework/evoagentx_adapter.py`

**预计工作量**: 6-8 小时

**优先级**: 低 (YAGNI - 当前顺序执行已满足需求)

---

#### 4.2 workflow.json 版本兼容

**描述**: 支持不同版本的 EvoAgentX workflow.json 格式

**需要实现**:
```python
class WorkflowParser:
    def parse(self, json_path):
        data = json.load(f)
        version = data.get("metadata", {}).get("enhanced_version", "v3.0")

        if version == "v3.1":
            return self._parse_v3_1(data)
        elif version == "v3.0":
            return self._parse_v3_0(data)
        else:
            raise ValueError(f"Unsupported workflow version: {version}")
```

**涉及文件**:
- `src/level1_framework/evoagentx_adapter.py`

**预计工作量**: 3-4 小时

**优先级**: 低 (目前只有 v3.1)

---

#### 4.3 简化 nodes 支持

**描述**: 支持解析 workflow.json 中的简化 nodes (非 original_nodes)

**当前状态**:
- 只解析 original_nodes
- 忽略了简化后的 nodes 和 edges

**可能用途**:
- 简化 nodes 通常包含 DocAgent 等高级配置
- 可以作为 DocAgent 支持的一部分

**涉及文件**:
- `src/level1_framework/evoagentx_adapter.py`

**预计工作量**: 4-5 小时

**依赖**: 需要先实现 DocAgent 支持

---

## 性能优化 ⚡

### 5.1 缓存和复用

**描述**: 缓存解析结果，避免重复解析同一文件

```python
# 全局缓存
_workflow_cache: Dict[str, ParsedWorkflow] = {}

def create_ag2_mas_from_evoagentx(workflow_path: str, use_cache: bool = True):
    if use_cache and workflow_path in _workflow_cache:
        workflow = _workflow_cache[workflow_path]
    else:
        parser = WorkflowParser()
        workflow = parser.parse(workflow_path)
        if use_cache:
            _workflow_cache[workflow_path] = workflow
```

**预计工作量**: 1-2 小时

---

### 5.2 大型 workflow 优化

**描述**: 优化处理超大 workflow 的性能

**可能的优化**:
- 懒加载 agents
- 并行创建 agents
- 流式解析 JSON

**预计工作量**: 3-4 小时

**优先级**: 低 (目前 workflow 都不大)

---

## 文档和示例 📚

### 6.1 完整使用指南

**需要添加**:
- [ ] 详细的 API 文档
- [ ] 更多使用场景示例
- [ ] 常见问题 FAQ
- [ ] 故障排查指南

**涉及文件**:
- 新增: `docs/guides/evoagentx_adapter_guide.md`
- 更新: `README.md`

**预计工作量**: 3-4 小时

---

### 6.2 集成示例

**需要添加**:
- [ ] 与 Safety_MAS 完整集成示例
- [ ] 运行实际 workflow 的端到端示例
- [ ] 自定义 LLM 配置示例
- [ ] 错误处理最佳实践

**涉及文件**:
- 新增: `examples/evoagentx_integration/`

**预计工作量**: 2-3 小时

---

## 总结

### 近期优先事项 (1-2周)
1. ✅ 基础实现 (已完成)
2. 🔴 DocAgent 支持 (高优先级)
3. 🔴 uploaded_files 处理 (高优先级)
4. 🟡 错误处理增强 (中优先级)
5. 🟡 扩展测试覆盖 (中优先级)

### 中期目标 (1个月)
- 复杂转移条件支持
- execution_context 完整支持
- 完整文档和示例

### 长期目标 (2-3个月)
- 动态依赖图推断
- 版本兼容支持
- 性能优化

---

## 注意事项

⚠️ **破坏性变更风险**
- DocAgent 支持可能需要修改现有接口
- 建议使用可选参数保持向后兼容

⚠️ **测试要求**
- 每个新功能都必须有对应的单元测试
- 保持测试覆盖率 > 80%

⚠️ **文档同步**
- 新功能必须更新设计文档
- 示例代码需要保持可运行状态

---

**最后更新**: 2026-01-28
**维护者**: TrinityGuard Team
