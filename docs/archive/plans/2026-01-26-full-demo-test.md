# 全流程演示测试实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 创建一个完整的演示测试，验证TrinityGuard框架从Level 1到Level 3的所有功能

**架构:** 创建一个带工具调用的AG2 MAS（研究助手系统），然后逐层封装为Level 1、Level 2、Level 3，测试各层接口和功能

**技术栈:** AG2/AutoGen, Python, TrinityGuard框架

---

## 任务概览

1. **Task 1**: 创建AG2原生MAS - 研究助手系统（带工具调用）
2. **Task 2**: Level 1封装 - 使用AG2MAS包装
3. **Task 3**: Level 2封装 - 测试脚手架接口
4. **Task 4**: Level 3封装 - 安全测试与监控
5. **Task 5**: 创建主测试脚本

---

## Task 1: 创建工具函数和AG2原生MAS

**目标:** 创建研究助手系统的工具函数和AG2 MAS实现

**文件:**
- Create: `examples/full_demo/__init__.py`
- Create: `examples/full_demo/tools.py`
- Create: `examples/full_demo/step1_native_ag2.py`

### Step 1.1: 创建__init__.py

```bash
touch examples/full_demo/__init__.py
```

### Step 1.2: 创建工具函数模块

创建 `examples/full_demo/tools.py`

### Step 1.3: 创建AG2原生MAS

创建 `examples/full_demo/step1_native_ag2.py`，实现研究助手MAS

### Step 1.4: 测试原生AG2 MAS

```bash
python examples/full_demo/step1_native_ag2.py
```

---

## Task 2: Level 1封装

**目标:** 使用AG2MAS类封装原生MAS

**文件:**
- Create: `examples/full_demo/step2_level1_wrapper.py`

### Step 2.1: 创建Level 1封装脚本

创建 `examples/full_demo/step2_level1_wrapper.py`

### Step 2.2: 测试Level 1封装

```bash
python examples/full_demo/step2_level1_wrapper.py
```

---

## Task 3: Level 2封装

**目标:** 使用AG2Intermediary测试脚手架接口

**文件:**
- Create: `examples/full_demo/step3_level2_intermediary.py`

### Step 3.1: 创建Level 2测试脚本

创建 `examples/full_demo/step3_level2_intermediary.py`

### Step 3.2: 测试Level 2接口

```bash
python examples/full_demo/step3_level2_intermediary.py
```

---

## Task 4: Level 3封装

**目标:** 使用Safety_MAS进行安全测试和监控

**文件:**
- Create: `examples/full_demo/step4_level3_safety.py`

### Step 4.1: 创建Level 3测试脚本

创建 `examples/full_demo/step4_level3_safety.py`

### Step 4.2: 测试Level 3功能

```bash
python examples/full_demo/step4_level3_safety.py
```

---

## Task 5: 创建完整演示脚本

**目标:** 创建一个完整的演示脚本，按顺序执行所有步骤

**文件:**
- Create: `examples/full_demo/run_full_demo.py`

### Step 5.1: 创建主演示脚本

创建 `examples/full_demo/run_full_demo.py`

### Step 5.2: 运行完整演示

```bash
python examples/full_demo/run_full_demo.py
```

---

## 实现细节

### 研究助手MAS设计

**Agents:**
1. **Coordinator** - 协调整个研究流程
2. **Searcher** - 搜索学术论文
3. **Analyzer** - 分析论文内容
4. **Summarizer** - 总结研究结果

**Tools:**
1. `search_papers(query, max_results)` - 搜索论文
2. `read_paper(paper_id)` - 读取论文内容
3. `extract_keywords(text)` - 提取关键词
4. `save_summary(content, filename)` - 保存摘要

**Workflow:**
用户提问 → Coordinator分析 → Searcher搜索 → Analyzer分析 → Summarizer总结 → 返回结果

---

## 测试用例

**Seed Task:** "研究多智能体系统的安全风险，找出最新的3篇相关论文并总结主要发现"

**预期行为:**
1. Coordinator接收任务并分解
2. Searcher调用search_papers工具
3. Analyzer调用read_paper和extract_keywords工具
4. Summarizer生成最终摘要
5. 返回结构化的研究报告

---

## 验证清单

- [ ] AG2原生MAS可以正常运行
- [ ] 工具调用功能正常工作
- [ ] Level 1封装后接口可用
- [ ] Level 2脚手架接口全部测试通过
- [ ] Level 3安全测试可以执行
- [ ] Level 3运行时监控可以工作
- [ ] 日志输出清晰明了
- [ ] 所有接口输出都有清晰打印
