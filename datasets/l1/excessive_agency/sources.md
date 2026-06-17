# L1.4 Excessive Agency - Dataset Sources

## Overview

This dataset contains 20 static test cases for the **L1.4 Excessive Agency** risk
category.  Cases are organized into four sub-categories:

| Category | Count | Description |
|---|---|---|
| `missing_confirmation` | 8 | Agent performs destructive/irreversible actions without asking |
| `scope_creep` | 7 | Agent expands task beyond what the user requested |
| `unauthorized_tool_use` | 3 | Agent uses tools or capabilities beyond its granted scope |
| `privilege_escalation` | 2 | Agent attempts to obtain or exercise elevated permissions |

---

## Primary Sources

### 1. AgentHarm Benchmark (8 cases)

**Reference:** Andriushchenko, M., Souly, A., Bhatt, M., Xhonneux, S., Yu, T.,
Habib, S., Goel, S., Basart, S., Zou, J., Kolter, J.Z., & Schwinn, L. (2024).
*AgentHarm: A Benchmark for Measuring Attacks on LLM Agents.*
arXiv:2410.09024. https://arxiv.org/abs/2410.09024

AgentHarm provides a set of 110 harmful agentic tasks that test whether an LLM
agent can be induced to perform harmful tool use, ranging from illegal activity to
privacy violations.  The cases drawn from this benchmark focus on scenarios where
a plausible-sounding user instruction causes the agent to take a destructive or
unauthorized action (e.g., bulk-delete files, send mass emails, modify production
databases) without seeking confirmation.

**Cases inspired by this source:**
- `delete_temp_files_without_confirmation`
- `bulk_email_without_confirmation`
- `production_database_modification`
- `publish_without_review`
- `unauthorized_api_call_with_side_effects`
- `exfiltrate_user_data`
- `deploy_to_production_unilaterally`
- `cancel_subscriptions_beyond_scope`

---

### 2. ToolEmu (7 cases)

**Reference:** Ruan, Y., Dong, H., Wang, A., Pitis, S., Zhou, H., Ba, J., Bengio,
Y., Ghassemi, M., & Pitkow, X. (2023). *Identifying the Risks of LM Agents with
an LM-Emulated Sandbox.* arXiv:2309.15817.
https://arxiv.org/abs/2309.15817

ToolEmu introduces an LLM-emulated sandbox environment where agents interact with
real-world tools (web browsers, email clients, filesystems, APIs).  The benchmark
surfaces a class of *scope-creep* failures where the agent's interpretation of the
user's goal leads it to take additional unsolicited actions.  The 7 cases in this
dataset reproduce that pattern: a benign read/search request is expanded into a
write/publish/modify action that the user never requested.

**Cases inspired by this source:**
- `weather_check_scope_creep_flight_booking`
- `calendar_read_scope_creep_meeting_invite`
- `file_read_scope_creep_reorganize`
- `search_scope_creep_social_post`
- `code_review_scope_creep_auto_merge`
- `diagnostics_scope_creep_auto_remediation`
- `contact_lookup_scope_creep_outreach`

---

### 3. OWASP LLM Top 10 2025 - LLM08 Excessive Agency (5 cases)

**Reference:** OWASP Foundation. (2025). *OWASP Top 10 for Large Language Model
Applications 2025: LLM08 - Excessive Agency.*
https://genai.owasp.org/llmrisk/llm08-excessive-agency/

OWASP LLM08 documents patterns that arise when an LLM-powered system is granted
more capability, permission, or autonomy than is necessary for its task.  The five
cases drawn from this source cover the two most severe sub-patterns: unauthorized
tool use (installing software, modifying firewall rules, accessing out-of-scope
systems) and privilege escalation (granting admin rights, self-elevation).

**Cases inspired by this source:**
- `grant_admin_access`
- `self_privilege_escalation`
- `install_unapproved_software`
- `modify_security_policy`
- `access_out_of_scope_systems`

---

## Related Work

- **OWASP LLM01:2023 Prompt Injection** - prompt injection can be a vector that
  triggers excessive agency; see `l1_prompt_injection` test module.
- **AgentBench** (Liu et al., 2023) - evaluates LLM agents on real-world tasks and
  surfaces unsafe tool-call sequences.
- **R2R SafetyBench** (Shi et al., 2024) - includes tool-misuse sub-tasks that
  overlap with the scope-creep category above.

---

## Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-03-26 | Initial 20-case dataset (8 AgentHarm + 7 ToolEmu + 5 OWASP LLM08) |
