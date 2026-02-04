# 测试脚本改进完成总结

## 改进概述

本次改进为 `test_all_l1_risks.py` 和 `test_all_l2_risks.py` 添加了两个重要功能：
1. **实际运行测试**：自动创建 MAS 实例并执行测试
2. **日志保存**：自动保存测试结果到 JSON 文件

## 完成的工作

### 1. test_all_l1_risks.py 改进

#### 功能 1: 实际运行测试
- ✅ 增强 `run_test()` 函数，添加 `safety_mas` 参数
- ✅ 增强 `main()` 函数，在 `--run` 模式下自动创建 MAS
- ✅ 分步骤显示创建过程（步骤 1-3）
- ✅ 提供详细的错误处理和解决建议

#### 功能 2: 日志保存
- ✅ 添加 `save_test_results()` 函数
- ✅ 添加 `--output-dir` 命令行参数（默认: `./logs/l1_tests`）
- ✅ 测试完成后自动保存结果到 JSON 文件
- ✅ 显示保存路径和状态

### 2. test_all_l2_risks.py 改进

#### 功能 1: 日志保存
- ✅ 添加 `save_test_results()` 函数
- ✅ 添加 `--output-dir` 命令行参数（默认: `./logs/l2_tests`）
- ✅ 修改 `run_actual_tests()` 函数，添加 `output_dir` 参数
- ✅ 测试完成后自动保存结果到 JSON 文件
- ✅ 显示保存路径和状态

### 3. 文档更新

- ✅ 更新 `tests/level3_safety/README.md`
  - 添加 `--output-dir` 参数说明
  - 添加日志文件说明
  - 添加使用示例

- ✅ 创建详细文档
  - `docs/solutions/test_all_l1_risks_improvement.md` - L1 测试改进说明
  - `docs/solutions/test_all_l1_risks_final_summary.md` - L1 测试完整总结
  - `docs/solutions/test_log_saving_feature.md` - 日志保存功能详细说明
  - `docs/solutions/test_scripts_improvement_summary.md` - 本文档（总结）

## 使用方式

### L1 测试

```bash
# 查看测试信息
python tests/level3_safety/test_all_l1_risks.py --info

# 运行测试（保存到默认目录）
python tests/level3_safety/test_all_l1_risks.py --run

# 运行测试（保存到自定义目录）
python tests/level3_safety/test_all_l1_risks.py --run --output-dir ./my_logs

# 运行指定测试
python tests/level3_safety/test_all_l1_risks.py --run --tests jailbreak prompt_injection

# 使用启发式规则（更快）
python tests/level3_safety/test_all_l1_risks.py --run --no-llm-judge
```

### L2 测试

```bash
# 查看测试信息
python tests/level3_safety/test_all_l2_risks.py --info

# 运行测试（保存到默认目录）
python tests/level3_safety/test_all_l2_risks.py --run

# 运行测试（保存到自定义目录）
python tests/level3_safety/test_all_l2_risks.py --run --output-dir ./my_logs

# 运行指定测试
python tests/level3_safety/test_all_l2_risks.py --run --tests malicious_propagation goal_drift

# 使用启发式规则（更快）
python tests/level3_safety/test_all_l2_risks.py --run --no-llm-judge
```

## 日志文件

### 保存位置

- **L1 测试**: `./logs/l1_tests/l1_test_results_<时间戳>.json`
- **L2 测试**: `./logs/l2_tests/l2_test_results_<时间戳>.json`

### 文件格式

#### L1 日志示例
```json
{
  "test_type": "L1_risks",
  "timestamp": "20260204_153045",
  "datetime": "2026-02-04T15:30:45.123456",
  "configuration": {
    "use_llm_judge": true,
    "tests_run": ["jailbreak", "prompt_injection"]
  },
  "summary": {
    "total_tests": 2,
    "passed_tests": 2,
    "failed_tests": 0
  },
  "results": {
    "jailbreak": true,
    "prompt_injection": true
  }
}
```

#### L2 日志示例
```json
{
  "test_type": "L2_risks",
  "timestamp": "20260204_153045",
  "datetime": "2026-02-04T15:30:45.123456",
  "configuration": {
    "use_llm_judge": true,
    "tests_run": ["malicious_propagation"]
  },
  "summary": {
    "total_tests": 1,
    "passed_tests": 1,
    "failed_tests": 0,
    "total_cases": 6,
    "failed_cases": 0
  },
  "results": {
    "malicious_propagation": {
      "passed": true,
      "total_cases": 6,
      "failed_cases": 0,
      "case_results": { ... }
    }
  }
}
```

## 功能对比

### 改进前

| 功能 | test_all_l1_risks.py | test_all_l2_risks.py |
|------|---------------------|---------------------|
| 查看测试信息 | ✓ | ✓ |
| 实际运行测试 | ✗ | ✓ |
| 自动创建 MAS | ✗ | ✓ |
| 保存日志文件 | ✗ | ✗ |
| 自定义输出目录 | ✗ | ✗ |

### 改进后

| 功能 | test_all_l1_risks.py | test_all_l2_risks.py |
|------|---------------------|---------------------|
| 查看测试信息 | ✓ | ✓ |
| 实际运行测试 | ✓ | ✓ |
| 自动创建 MAS | ✓ | ✓ |
| 保存日志文件 | ✓ | ✓ |
| 自定义输出目录 | ✓ | ✓ |

## 技术实现

### 关键代码

#### 1. 保存测试结果函数

```python
def save_test_results(results: dict, output_dir: Path, use_llm_judge: bool):
    """保存测试结果到 JSON 文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report = {
        "test_type": "L1_risks",  # 或 "L2_risks"
        "timestamp": timestamp,
        "datetime": datetime.now().isoformat(),
        "configuration": {
            "use_llm_judge": use_llm_judge,
            "tests_run": list(results.keys())
        },
        "summary": {
            "total_tests": len(results),
            "passed_tests": sum(1 for v in results.values() if v),
            "failed_tests": sum(1 for v in results.values() if not v)
        },
        "results": results
    }

    output_file = output_dir / f"l1_test_results_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return output_file
```

#### 2. 自动创建 MAS（L1 测试）

```python
if args.run:
    # 步骤 1: 创建测试用 MAS
    from src.level1_framework.ag2_wrapper import AG2MAS
    from src.level3_safety import Safety_MAS
    sys.path.insert(0, str(project_root / "examples" / "full_demo"))
    from step2_level1_wrapper import create_research_assistant_mas_with_wrapper

    mas = create_research_assistant_mas_with_wrapper()

    # 步骤 2: 创建 Safety_MAS 包装器
    safety_mas = Safety_MAS(mas)

    # 步骤 3: 运行测试
    for test_name, test_fn in tests_to_run.items():
        success = run_test(test_name, test_fn, use_llm_judge, safety_mas)
        results[test_name] = success

    # 保存结果
    output_file = save_test_results(results, output_dir, use_llm_judge)
```

## 验证测试

已验证以下场景：

### ✓ L1 测试
- 查看单个测试信息
- 查看多个测试信息
- 查看所有测试信息
- 脚本语法正确，导入正常

### ✓ L2 测试
- 查看测试信息
- 脚本语法正确，导入正常

### ✓ 日志保存
- 函数实现正确
- 参数传递正确
- 文件路径处理正确

## 文件清单

### 修改的文件
1. `tests/level3_safety/test_all_l1_risks.py`
   - 添加日志保存功能
   - 添加实际运行测试功能
   - 添加 `--output-dir` 参数

2. `tests/level3_safety/test_all_l2_risks.py`
   - 添加日志保存功能
   - 添加 `--output-dir` 参数

3. `tests/level3_safety/README.md`
   - 更新使用说明
   - 添加日志文件说明

### 新增的文档
1. `docs/solutions/test_all_l1_risks_improvement.md`
   - L1 测试改进详细说明

2. `docs/solutions/test_all_l1_risks_final_summary.md`
   - L1 测试完整总结

3. `docs/solutions/test_log_saving_feature.md`
   - 日志保存功能详细说明

4. `docs/solutions/test_scripts_improvement_summary.md`
   - 本文档（总体总结）

## 优势

### 1. 功能完整性
- ✓ 可以查看测试信息
- ✓ 可以实际运行测试
- ✓ 可以保存测试结果
- ✓ 两个测试脚本功能一致

### 2. 易用性
- ✓ 自动创建 MAS，无需手动配置
- ✓ 自动保存日志，无需额外操作
- ✓ 清晰的步骤显示
- ✓ 详细的错误提示

### 3. 可追溯性
- ✓ 时间戳文件名
- ✓ 完整的测试配置记录
- ✓ 详细的测试结果
- ✓ 便于历史对比

### 4. 灵活性
- ✓ 可自定义输出目录
- ✓ 可选择测试子集
- ✓ 可选择评估方法（LLM Judge 或启发式）
- ✓ 标准 JSON 格式便于解析

## 与其他系统的关系

### step4_level3_safety.py
- 使用 `log_session_manager` 创建会话文件夹
- 保存更多信息（会话日志、综合报告等）
- 适合完整的演示和集成测试

### test_all_l1_risks.py 和 test_all_l2_risks.py
- 简单的 JSON 文件保存
- 只保存测试结果
- 适合快速测试和 CI/CD 集成

## 后续改进建议

1. **增强日志内容**
   - 添加运行环境信息（Python 版本、依赖版本）
   - 添加测试执行时间
   - 添加失败用例的详细错误信息

2. **支持多种格式**
   - CSV 格式（便于 Excel 分析）
   - HTML 报告（便于查看）
   - Markdown 报告（便于文档）

3. **历史对比功能**
   - 对比不同时间的测试结果
   - 生成趋势图表
   - 识别回归问题

4. **CI/CD 集成**
   - 添加 JUnit XML 格式支持
   - 添加退出码（测试失败时返回非零）
   - 添加 GitHub Actions 示例

5. **自动清理**
   - 自动删除过期日志
   - 保留最近 N 次测试结果
   - 压缩旧日志文件

## 总结

通过本次改进：

1. **test_all_l1_risks.py** 现在可以：
   - ✓ 查看测试信息
   - ✓ 实际运行测试（自动创建 MAS）
   - ✓ 保存测试结果到 JSON 文件

2. **test_all_l2_risks.py** 现在可以：
   - ✓ 查看测试信息
   - ✓ 实际运行测试（已有功能）
   - ✓ 保存测试结果到 JSON 文件（新增）

3. **两个脚本现在功能一致**，使用体验统一

4. **测试结果可追溯**，便于分析和报告

这使得测试流程更加完整和专业，特别适合：
- 开发过程中的快速测试
- CI/CD 自动化测试
- 测试结果的历史追踪
- 安全评估报告生成
