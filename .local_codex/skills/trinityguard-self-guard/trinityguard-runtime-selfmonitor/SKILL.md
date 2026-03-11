---
name: trinityguard-runtime-selfmonitor
description: 在执行过程中监控高风险动作与行为漂移。任务进入命令执行、工具调用、文件写入、批量修改时应触发本技能，持续产出事件日志、告警和处置建议。
---

# TrinityGuard Runtime Selfmonitor

## 作用

对执行中的行为进行在线风险监控，重点看“发生了什么”，而不是只看结果。

## 输入

1. preflight 结果
2. 实时动作流（命令、工具调用、文件写入）
3. 当前告警状态

## 输出

1. `runtime_events`
2. `alerts`
3. `suggested_actions`
4. `trust_annotations`
5. `runtime_decision`（continue|downgrade|stop）

## 监控重点

1. 高危命令与写操作
2. 连续失败或异常重试
3. 目标漂移（执行内容偏离用户任务）
4. 工具结果采信路径是否合规

## 规则

1. 关键动作必须记录事件与来源。
2. 命中 `critical` 告警时建议 `stop`。
3. 仅单工具来源的信息必须打低可信标签。
4. 运行期发现敏感泄露风险时立即切换到 output guard 严格模式。

## 输出模板

```markdown
## Runtime Monitor Result
- runtime_decision: <continue|downgrade|stop>
- runtime_events:
  - <event>
- alerts:
  - <severity>: <message>
- trust_annotations:
  - source: <internal_verified|internal_unverified|tool_single_source|multi_source_verified>
    confidence: <low|medium|high>
- suggested_actions:
  - <action>
```

## 推荐脚本调用

1. 使用 `../shared/scripts/verify_multi_source_template.py` 对运行期结论做来源一致性判断。
2. 将脚本输出映射到 `trust_annotations` 和 `runtime_decision`。
