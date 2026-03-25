# Progressive Runtime Monitoring & Documentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在运行时增加全局监控协调器（LLM 元评估 + 窗口化摘要）以动态开关各子监控，并产出清晰的运行时监督与事前攻击测试说明文档。

**Architecture:** 在 `Safety_MAS` 中新增全局监控协调器组件，消费结构化事件流并按窗口触发 LLM 决策，动态更新激活的子监控列表；并输出决策日志与报告。文档从数据流、触发频率与判定逻辑角度解释现有实现与新增机制。

**Tech Stack:** Python, pytest, 现有 LLM 客户端与监控框架（`LLMJudge` / `get_monitor_llm_client`）

---

### Task 1: 全局监控窗口与决策测试

**Files:**
- Create: `tests/level3_safety/test_global_monitor.py`
- Create: `src/level3_safety/monitoring/global_monitor.py`
- Create: `src/level3_safety/monitoring/__init__.py`

**Step 1: Write the failing test**

```python
def test_global_monitor_triggers_decision_on_window_size():
    agent = GlobalMonitorAgent(
        available_monitors=["jailbreak", "prompt_injection"],
        config={"window_size": 2},
        decision_provider=lambda summary, active, available: {
            "enable": ["jailbreak"],
            "disable": [],
            "reason": "test"
        }
    )
    assert agent.ingest(_log("a")) is None
    decision = agent.ingest(_log("b"))
    assert decision["enable"] == ["jailbreak"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/level3_safety/test_global_monitor.py -v`  
Expected: FAIL with "GlobalMonitorAgent not found" or similar import error

**Step 3: Write minimal implementation**

```python
class GlobalMonitorAgent:
    def ingest(self, log_entry):
        # accumulate events, trigger decision at window threshold
        ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/level3_safety/test_global_monitor.py -v`  
Expected: PASS

**Step 5: Commit (可选，需用户确认)**

```bash
git add tests/level3_safety/test_global_monitor.py src/level3_safety/monitoring/global_monitor.py src/level3_safety/monitoring/__init__.py
git commit -m "feat: add global monitor windowing and tests"
```

---

### Task 2: 监控激活控制与 Safety_MAS 集成

**Files:**
- Create: `src/level3_safety/monitoring/activation.py`
- Modify: `src/level3_safety/safety_mas.py`
- Modify: `src/utils/logging_config.py` (新增结构化事件类型可选)

**Step 1: Write the failing test**

```python
def test_apply_monitor_decision_enables_and_disables():
    active, info = apply_monitor_decision(
        available={"a": Dummy(), "b": Dummy()},
        active_names=set(["a"]),
        decision={"enable": ["b"], "disable": ["a"]}
    )
    assert active == set(["b"])
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/level3_safety/test_global_monitor.py -v`  
Expected: FAIL with "apply_monitor_decision not found"

**Step 3: Write minimal implementation**

```python
def apply_monitor_decision(available, active_names, decision):
    # compute new active set and reset newly enabled monitors
    ...
```

**Step 4: Integrate into `Safety_MAS`**

```python
def start_runtime_monitoring(..., progressive_config: Optional[Dict] = None):
    # init GlobalMonitorAgent and baseline active set
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/level3_safety/test_global_monitor.py -v`  
Expected: PASS

**Step 6: Commit (可选，需用户确认)**

```bash
git add src/level3_safety/monitoring/activation.py src/level3_safety/safety_mas.py src/utils/logging_config.py
git commit -m "feat: enable progressive monitoring with global decisioning"
```

---

### Task 3: 运行时监督与事前攻击测试说明文档

**Files:**
- Create: `docs/runtime_monitoring_and_pretest.md`

**Step 1: Write the documentation**

```markdown
## Runtime 监督数据流
- 日志来源、结构化字段、频率
- 子监控联动与输出
## 事前攻击测试判定
- 测试执行流程
- 攻击成功/失败的判定规则
- 关键代码入口
```

**Step 2: Review doc accuracy with code references**

Manual check: `src/level3_safety/safety_mas.py`, `src/level2_intermediary/workflow_runners/monitored.py`, `src/level3_safety/risk_tests/*/test.py`

**Step 3: Commit (可选，需用户确认)**

```bash
git add docs/runtime_monitoring_and_pretest.md
git commit -m "docs: explain runtime monitoring and pre-attack tests"
```
