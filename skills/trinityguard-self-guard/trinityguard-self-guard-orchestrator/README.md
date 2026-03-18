# trinityguard-self-guard-orchestrator

Single-turn orchestrator for preflight + runtime + output guard.

## Purpose

- run all stages in order
- merge reason codes and matched rules
- compute final decision and write auditable records

## Core outputs

- `final_action`
- `decision_chain`
- `trace_id`
- `output_guard.safe_response`
