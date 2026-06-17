# Phase 3 Runtime Adapter Contract v1

> Status: Phase 3 production-boundary contract; **not production-ready**.  
> Scope: adapter semantics for future production deployment planning.  
> Non-goals: production deployment, production telemetry, formal Garak/OpenRT comparison.

## Purpose

Phase 3 hardens the runtime adapter boundary created in Phase 2. The contract defines how adapters represent local runtime decisions without claiming that TrinityGuard-Dev is production-ready.

## Contract

The canonical Python contract lives in
`trinityguard.runtime.adapter_contract`. Legacy imports from
`trinityguard.level1_framework.base` remain compatibility re-exports and must
refer to the same classes/functions.

Adapters must preserve the structured `MessageHookResult` actions:

- `allow`: deliver the original or already-safe message.
- `replace`: deliver a policy-refusal replacement while retaining redacted evidence.
- `deny`: do not call the framework-native send/delivery method and return redacted denial metadata.

## Evidence rules

Adapters must record payload refs or hashes, policy name/version, request id, decision, delivery action, and redacted reason. Raw payload persistence is forbidden by default.

## Failure semantics

Adapters must expose fail-open and fail-closed behavior as policy-controlled outcomes. Adapter errors must be represented as evidence and must not silently downgrade `deny` into `replace`.

## Production boundary

This contract is a Phase 3 readiness artifact for later production deployment work. It does not implement production deployment, production telemetry, Garak/OpenRT comparison.
