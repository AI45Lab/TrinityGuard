# test_all_l1_risks.py 功能改进说明

## 改进概述

对 `tests/level3_safety/test_all_l1_risks.py` 进行了功能增强，使其能够实际运行 L1 风险测试，而不仅仅是显示测试信息。

## 改进内容

### 1. 增强 `run_test()` 函数

**改进前**:
- 只显示测试信息
- 显示警告消息："实际运行需要创建 MAS 实例"
- 无法实际执行测试

**改进后**:
- 添加 `safety_mas` 参数（可选）
- 当 `safety_mas=None` 时，保持原有行为（仅显示信息）
- 当提供 `safety_mas` 实例时，实际调用 `safety_mas.run_manual_safety_tests()` 执行测试
- 显示详细的测试结果（通过/失败的用例数）

```python
def run_test(test_name: str, test_fn, use_llm_judge: bool = True, safety_mas=None):
    """运行单个测试

    Args:
        test_name: 测试名称
        test_fn: 测试函数
        use_llm_judge: 是否使用 LLM Judge
        safety_mas: Safety_MAS 实例（如果为 None，则只显示测试信息）
    """
    # ... 实现代码
```

### 2. 增强 `main()` 函数

**改进前**:
- 直接调用 `run_test()` 而不创建 MAS 实例
- 无法实际运行测试

**改进后**:
- 当使用 `--run` 参数时，自动创建 MAS 和 Safety_MAS 实例
- 分步骤显示创建过程：
  - 步骤 1: 创建测试用 MAS
  - 步骤 2: 创建 Safety_MAS 包装器
  - 步骤 3: 运行测试
- 提供详细的错误处理和提示信息
- 如果创建失败，给出明确的解决建议

### 3. 更新 README 文档

在 `tests/level3_safety/README.md` 中添加了使用说明：

```markdown
**注意**: 实际运行测试（`--run`）需要:
1. 配置 LLM API (如 OPENAI_API_KEY)
2. 确保 `examples/full_demo/step2_level1_wrapper.py` 存在
3. 脚本会自动创建 MAS 实例并运行测试
```

## 使用示例

### 查看测试信息（不实际运行）

```bash
# 查看所有 L1 测试的信息
python tests/level3_safety/test_all_l1_risks.py --info

# 查看指定测试的信息
python tests/level3_safety/test_all_l1_risks.py --info --tests jailbreak prompt_injection
```

### 实际运行测试

```bash
# 运行所有 L1 测试（使用 LLM Judge）
python tests/level3_safety/test_all_l1_risks.py --run

# 运行指定的测试
python tests/level3_safety/test_all_l1_risks.py --run --tests jailbreak prompt_injection

# 使用启发式规则（更快，不需要额外 LLM 调用）
python tests/level3_safety/test_all_l1_risks.py --run --no-llm-judge

# 运行指定测试并使用启发式规则
python tests/level3_safety/test_all_l1_risks.py --run --tests tool_misuse --no-llm-judge
```

## 运行流程

### 使用 `--info` 参数（默认）

1. 加载测试类
2. 显示测试实现细节
3. 列出测试用例
4. 不创建 MAS，不实际运行

### 使用 `--run` 参数

1. **步骤 1**: 创建测试用 MAS
   - 导入 `AG2MAS` 和 `Safety_MAS`
   - 导入 `create_research_assistant_mas_with_wrapper()`
   - 创建 MAS 实例
   - 显示智能体数量

2. **步骤 2**: 创建 Safety_MAS 包装器
   - 用 MAS 实例创建 `Safety_MAS`
   - 显示可用的风险测试和监控器数量

3. **步骤 3**: 运行测试
   - 配置 LLM Judge 选项
   - 对每个测试调用 `safety_mas.run_manual_safety_tests()`
   - 显示测试结果（通过/失败）
   - 生成测试总结

## 错误处理

### MAS 创建失败

如果 MAS 创建失败，脚本会：
1. 显示错误信息
2. 提供解决建议：
   - 检查 LLM API 配置（如 OPENAI_API_KEY）
   - 确认 `examples/full_demo/step2_level1_wrapper.py` 存在
3. 提示可以使用 `--info` 参数查看测试信息

### Safety_MAS 创建失败

如果 Safety_MAS 创建失败，脚本会：
1. 显示错误信息
2. 打印完整的堆栈跟踪
3. 退出程序

## 技术实现

### 参考实现

改进参考了以下文件的实现：
- `examples/full_demo/step4_level3_safety.py` - MAS 创建和测试运行流程
- `tests/level3_safety/test_all_l2_risks.py` - L2 测试的实际运行实现

### 关键代码

```python
# 创建 MAS
from src.level1_framework.ag2_wrapper import AG2MAS
from src.level3_safety import Safety_MAS
sys.path.insert(0, str(project_root / "examples" / "full_demo"))
from step2_level1_wrapper import create_research_assistant_mas_with_wrapper

mas = create_research_assistant_mas_with_wrapper()
safety_mas = Safety_MAS(mas)

# 运行测试
test_results = safety_mas.run_manual_safety_tests([test_name])
```

## 兼容性

- 保持向后兼容：`--info` 参数行为不变
- 新增功能：`--run` 参数现在可以实际运行测试
- 所有原有参数（`--tests`, `--no-llm-judge`）继续工作

## 测试验证

已验证以下功能：
- ✓ `--info` 参数正常工作
- ✓ `--info --tests <test_name>` 正常工作
- ✓ `--run` 参数能够创建 MAS 并运行测试（需要 API 配置）
- ✓ 错误处理和提示信息正确显示

## 总结

通过这次改进，`test_all_l1_risks.py` 现在是一个完整的测试工具：
- 可以查看测试信息（`--info`）
- 可以实际运行测试（`--run`）
- 提供清晰的步骤和错误提示
- 与 `test_all_l2_risks.py` 保持一致的使用体验
