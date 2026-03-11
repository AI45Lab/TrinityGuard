# TrinityGuard Self Guard Skills

独立的 skills 集合，不依赖修改 TrinityGuard 主体源码。

## Skills
1. `trinityguard-self-guard-orchestrator`
2. `trinityguard-preflight-selfcheck`
3. `trinityguard-runtime-selfmonitor`
4. `trinityguard-output-privacy-guard`

## Design principles
1. 解释型回答与执行动作同等纳入安全监测。
2. 工具来源信息默认降级，需多源校验后再提升可信度。
3. 先边界、再执行、后输出，全程可审计。

## Quick install

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target codex
```

```bash
python skills/trinityguard-self-guard/install/install_skill_local.py --target claude
```

## Verification

```bash
python skills/trinityguard-self-guard/install/verify_install.py --target codex --policy-profile balanced
```

## Primary log contract

- Main output is JSONL events: `safety-guard-log/events/self_guard_events.jsonl`
- Optional summary JSON can be generated with `--out`
- Session state remains in `safety-guard-log/.self_guard_state/`
