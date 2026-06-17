# TrinityGuard + AG2 真实 API Demo

这个 demo 用一个中文 AG2 多智能体小组来体验 TrinityGuard 的核心路径：

1. **原生 AG2 GroupChat**：不经过 TrinityGuard，保存 AG2 对话历史。
2. **AG2MAS 包装后正常运行**：通过 Level 1 `AG2MAS` 适配器运行同一个中文 MAS。
3. **事前测试 / pre-deployment check**：用 TrinityGuard 的攻击 API 跑一条中文 prompt-injection 探针，并用真实 LLM judge 评估。
4. **运行时检测与拦截**：把 `RuntimeProtector` 接到 AG2 消息 hook，保存 JSONL 事件和 runtime report。

所有输出默认只写到：

```text
demos/ag2_real_api/runs/<run-id>/
```

`runs/` 已在本目录 `.gitignore` 中忽略，避免日志、JSONL、报告到处散落。

## 准备 API key

任选一种方式：

```bash
export OPENAI_API_KEY="sk-..."
# 可选：分别指定被测 MAS 和 judge 的模型
export MAS_LLM_MODEL="gpt-4o-mini"
export JUDGE_LLM_MODEL="gpt-4o-mini"
```

或使用分离的 key：

```bash
export MAS_LLM_API_KEY="sk-..."
export JUDGE_LLM_API_KEY="sk-..."
export MAS_LLM_BASE_URL="https://api.openai.com/v1"      # 可选
export JUDGE_LLM_BASE_URL="https://api.openai.com/v1"    # 可选
```

也可以在仓库根目录 `.env` 或 `demos/ag2_real_api/.env` 中放同名变量（不要提交）。

## 代理兼容说明

AG2 当前导入链会加载 `ollama/httpx`。如果你的 shell 里有 `socks://127.0.0.1:7897/` 这类代理，`httpx` 会报 `Unknown scheme for proxy URL`。本 demo 会在进程内把 `socks://` 自动规范化为 Python/httpx 可解析的代理 URL，并把调整记录到 `run_manifest.json` 的 `proxy_env_adjustments`。如果你的代理端口不支持 HTTP mixed-port，请手动设置 `HTTP_PROXY`/`HTTPS_PROXY` 为可用的 `http://...`，或安装支持 SOCKS 的 `socksio` 后使用 SOCKS5。

## 先检查目录与脚本（不调用 API）

```bash
PYTHONPATH=src python demos/ag2_real_api/run_demo.py --dry-run
```

成功后会打印：

```text
trinityguard_ag2_real_api_demo=dry_run_ok
```

## 运行完整真实 API demo

```bash
PYTHONPATH=src python demos/ag2_real_api/run_demo.py
```

如果想减少 API 调用，可以只跑部分场景：

```bash
PYTHONPATH=src python demos/ag2_real_api/run_demo.py --scenarios native,wrapped
PYTHONPATH=src python demos/ag2_real_api/run_demo.py --scenarios precheck,runtime
```

## 主要证据文件

每次运行会生成一个独立 run 目录，里面包含：

```text
run_manifest.json                         # 本次运行配置（已脱敏）
llm_settings.redacted.json                 # 模型/endpoint 配置（不含 key）
01_native_ag2/chat_history.json            # 原生 AG2 对话证据
02_wrapped_ag2/workflow_result.json        # AG2MAS 包装后的消息/拓扑证据
03_predeployment_check/predeployment_evaluation.json
04_runtime_detection/runtime_events.jsonl  # RuntimeProtector 逐消息 JSONL 证据
04_runtime_detection/runtime_report.json   # 可验证 runtime report artifact
04_runtime_detection/runtime_run_result.json
summary.md
```

这些文件能让你从“黑盒”角度看到：AG2 原始消息、TrinityGuard 包装后的消息历史、事前攻击评估、运行时 judge 决策、payload hash、拦截动作和报告校验结果。
