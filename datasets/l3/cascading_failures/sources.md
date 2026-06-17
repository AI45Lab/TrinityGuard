# Sources: L3 Cascading Failures Dataset

This document lists the references and methodologies used to design the
20 static test cases in `static_cases.yaml`.

---

## 1. Academic and Industry References

### Distributed Systems Failure Theory

- **Fischer, Lynch & Paterson (1985)** — "Impossibility of Distributed Consensus
  with One Faulty Process."  FLP Impossibility underpins the network-partition
  and split-brain test cases.

- **Lamport, Shostak & Pease (1982)** — "Byzantine Generals Problem."  The
  `byzantine_failure` category (conflicting facts, trust escalation, phantom
  leader) is directly derived from Byzantine fault models where a subset of
  nodes may send contradictory or adversarial messages.

- **Brewer (2000) / CAP Theorem** — Characterises the trade-off between
  consistency, availability, and partition tolerance; motivates the
  `network_partition_split_brain` and `flapping_dependency_state` test cases.

### Chaos Engineering

- **Principles of Chaos Engineering** (Basiri et al., Netflix, 2016)
  https://principlesofchaos.org/
  The chaos-engineering section borrows directly from the practice of
  deliberately injecting production faults (resource exhaustion, partial
  failures, dependency unavailability) to validate system resilience.

- **Simian Army / Chaos Monkey** (Netflix OSS)
  Inspired the `partial_failure_silent_drop`, `flapping_dependency_state`,
  and `synthetic_timeout_chain` test cases.

- **Gremlin Chaos Engineering Platform Documentation**
  https://www.gremlin.com/chaos-engineering/
  Reference for fault-injection categories: CPU/memory saturation,
  network latency, DNS failures, and dependency blackholing.

### Multi-Agent System Safety

- **OWASP LLM Top 10 (2025)** — LLM04 (Data and Model Poisoning),
  LLM06 (Excessive Agency), LLM08 (Vector and Embedding Weaknesses).
  State-corruption and memory-wipe test cases map to these categories.

- **OWASP Agentic AI Threats, ASI15** — "Cascading Failures in Agentic
  Pipelines."  The risk identifier for this entire test suite.

- **Perez et al. (2022)** — "Ignore Previous Prompt: Attack Techniques
  for Language Models."  Prompt-injection patterns inform the injected halt
  commands and state-override test cases.

- **Greshake et al. (2023)** — "Not What You've Signed Up For: Compromising
  Real-World LLM-Integrated Applications with Indirect Prompt Injection."
  Motivates the `coordinator_poisoned_task_distribution` and
  `middle_agent_data_corruption_relay` test cases.

### Resilience Patterns

- **Nygard (2007)** — "Release It! Design and Deploy Production-Ready
  Software."  Circuit-breaker, bulkhead, and timeout patterns referenced
  by `flapping_dependency_state` and `bottleneck_timeout_starvation`.

- **Fowler & Nygard — Circuit Breaker Pattern**
  https://martinfowler.com/bliki/CircuitBreaker.html
  Directly informs expected-behavior descriptions for dependency-failure cases.

---

## 2. Test Case Design Methodology

### 2.1 Enhanced Baseline (8 cases)

The eight baseline cases extend the original hard-coded cases in
`src/level3_safety/risk_tests/l3_cascading_failures/test.py` with:

- More realistic, production-resembling payloads (formatted error codes,
  structured JSON with embedded malformations).
- Explicit inject-point metadata (`inject_at`) indicating where in the
  pipeline the failure is introduced.
- Richer `expected_behavior` descriptions that specify both detection and
  graceful-degradation requirements.

### 2.2 Chaos Engineering Patterns (7 cases)

These cases follow a systematic fault-taxonomy approach:

| Fault Class           | Cases                                              |
|-----------------------|----------------------------------------------------|
| Byzantine (adversarial) | conflicting_facts, trust_escalation, phantom_leader |
| Partial failure       | silent_drop, context_truncation                   |
| Network partition     | split_brain, phantom_leader                       |
| Flapping dependency   | dependency_flapping                               |

Each case pairs a fault injection with a concrete expected-behavior contract
so that automated judges can evaluate both detection and containment.

### 2.3 Topology-Aware Cases (5 cases)

Topology awareness uses three canonical positions:

| Position     | Role in Pipeline               | Cases                                       |
|--------------|-------------------------------|---------------------------------------------|
| coordinator  | Root / orchestrator            | broadcast_halt, poisoned_task_distribution |
| middle       | Intermediary / relay / fan-in  | data_corruption_relay, bottleneck_timeout  |
| leaf         | Terminal output producer       | infinite_report_expansion                  |

The `expected_cascade_depth` field estimates how many downstream hops are
expected to be affected if containment fails, enabling depth-aware scoring
in the benchmark runner.

---

## 3. Relationship to Other Dataset Files

- `../../../datasets/l3/excessive_agency/` — overlaps with resource-exhaustion
  cases; the present dataset focuses on systemic propagation rather than
  individual-agent over-reach.
- Judge prompts: `src/level3_safety/judges/prompts/cascading_failures.yaml`
  — few-shot examples in the judge were aligned with the failure types
  catalogued here.

---

## 4. Revision History

| Version | Date       | Author        | Notes                                   |
|---------|------------|---------------|-----------------------------------------|
| 1.0     | 2026-03-26 | TrinityGuard  | Initial 20-case dataset                 |
