# TrinityGuard-Dev Introduction

本目录是 TrinityGuard 的使用入口文档。它面向希望快速理解、安装、运行真实 API smoke、调用 public API、接入 AG2 demo、阅读架构说明的用户。

## 推荐阅读顺序

1. [根目录 README](../../README.md)：功能概览、安装、快速示例、架构。
2. [Usage Guide](usage.md)：安装、真实 API smoke、AG2 demo、runtime protection、API 调用方式。
3. [Public API Contract](../contracts/public-api-v1.md)：当前推荐导入路径与兼容边界。
4. [Runtime Adapter Contract](../contracts/runtime-adapter-contract-v1.md)：message hook / deny-replace contract。

## 当前最重要的边界

TrinityGuard 当前是真实 API 优先的 MAS 安全评估框架：

- 可以运行真实 API bounded smoke；2026-05-11 修复闭环已覆盖 20 个已实现风险的一样本真实 API smoke；
- 可以运行 AG2 precheck/runtime 真实 API demo；provider content filter 目标阻断会记录为 conclusive safe/refusal evidence，而不是 judge-backed verdict；
- 可以运行 OpenRT API smoke；
- 可以用确定性示例快速验证 trace、judge、monitor、runtime proof；
- 可以用 runtime protection MVP 演示 allow/replace/deny 语义；
- 当前真实 API 示例是 bounded smoke，不等同于生产认证或论文规模复现实验。

## 常用命令速查

```bash
# 安装开发环境
pip install -e ".[dev]"

# 完整 regression 测试
PYTHONPATH=src pytest -q tests/unit tests/integration

# 真实 API bounded smoke 示例
PYTHONPATH=src python examples/minset_real_api.py \
  --sample 1 \
  --risk jailbreak \
  --risk prompt_injection \
  --output-dir /tmp/trinityguard-real-api-smoke

# AG2 precheck/runtime 真实 API demo
PYTHONPATH=src python demos/ag2_real_api/run_demo.py \
  --scenarios precheck,runtime \
  --max-round 2 \
  --output-root /tmp/trinityguard-ag2-real-api-recheck
```

更多细节见 [Usage Guide](usage.md)。
