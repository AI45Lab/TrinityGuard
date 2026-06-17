# Prompt Injection Test Case Sources

This document describes the provenance and design rationale for each group of
static test cases in `static_cases.yaml`.

---

## 1. AgentDojo-inspired (8 cases)

**Reference:**
Debenedetti, E., Severi, G., Bhatt, U., Dolan-Gavitt, B., Mittal, P., Tramèr, F.,
& Staab, M. (2024). *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection
Attacks and Defenses for LLM Agents*. arXiv:2406.13352.
<https://arxiv.org/abs/2406.13352>

**Design rationale:**
AgentDojo establishes a benchmark framework where agents interact with realistic
tool environments (web search, email, calendar, file system, APIs, databases).
Adversarial tasks embed injection payloads inside simulated tool return values.
The 8 cases here are independently authored scenarios inspired by AgentDojo's
threat model:

| Case name                              | Tool vector           | Injection goal               |
|----------------------------------------|-----------------------|------------------------------|
| agentdojo_search_result_exfil          | Web search            | HTTP exfiltration            |
| agentdojo_email_draft_override         | Email draft retrieval | Persistent cc exfiltration   |
| agentdojo_calendar_event_hijack        | Calendar event        | Destructive tool call        |
| agentdojo_web_page_role_switch         | Web scrape            | Role/persona hijack          |
| agentdojo_file_read_persistence        | File read             | Persistent behavior override |
| agentdojo_api_response_privilege_escalation | API JSON field   | Privilege escalation         |
| agentdojo_database_row_exfil           | Database query        | Data exfiltration via email  |
| agentdojo_tool_error_message_injection | Error message         | Auth bypass                  |

---

## 2. Tensor Trust-inspired (5 cases)

**Reference:**
Toyer, S., Watkins, O., Bulatov, E., Bagdasaryan, A., Wu, R., Zhu, S., ... &
Russell, S. (2023). *Tensor Trust: Interpretable Prompt Injection Attacks from an
Online Game*. arXiv:2311.01011.
<https://arxiv.org/abs/2311.01011>

**Design rationale:**
The Tensor Trust dataset collects real-world prompt injection attacks submitted
by human players in an adversarial game where the objective is to bypass an
LLM's "access code" defense prompt. The patterns observed in the dataset informed
the following 5 archetypal attack structures:

| Case name                            | Attack structure                                      |
|--------------------------------------|-------------------------------------------------------|
| tensor_trust_prefix_override         | Hard override ("Ignore previous instructions...")    |
| tensor_trust_sandwich_attack         | Inject inside user-supplied content delimiters        |
| tensor_trust_context_continuation    | Fake "additional system configuration" appended       |
| tensor_trust_translation_bypass      | Task-vector: injection hidden as translation content  |
| tensor_trust_completion_hijack       | Sentence completion used to elicit system prompt      |

---

## 3. Manual direct/indirect injection (4 cases)

**Reference / inspiration:**
- Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M.
  (2023). *Not What You've Signed Up For: Compromising Real-World LLM-Integrated
  Applications with Indirect Prompt Injections*. arXiv:2302.12173.
  <https://arxiv.org/abs/2302.12173>
- Perez, F., & Ribeiro, I. (2022). *Ignore Previous Prompt: Attack Techniques
  For Language Models*. arXiv:2211.09527.
  <https://arxiv.org/abs/2211.09527>

**Design rationale:**
These four cases cover fundamental injection vectors identified in foundational
academic work on prompt injection and indirect injection via external content:

| Case name                             | Vector                                         |
|---------------------------------------|------------------------------------------------|
| manual_system_prompt_override_direct  | User-turn SYSTEM prefix spoofing               |
| manual_context_window_injection       | Fabricated conversation history                |
| manual_indirect_document_command      | Hidden AI directive inside a document          |
| manual_indirect_persona_via_tool      | Persona override embedded in tool JSON result  |

---

## 4. Encoding tricks (3 cases)

**Reference / inspiration:**
- Kang, D., Li, X., Stoica, I., Guestrin, C., Zaharia, M., & Hashimoto, T.
  (2023). *Exploiting Programmatic Behavior of LLMs: Dual-Use Through Standard
  Security Attacks*. arXiv:2302.05733.
  <https://arxiv.org/abs/2302.05733>
- Selvi, J. (2022). *Exploring Prompt Injection Attacks*.
  NCC Group Research Blog.
  <https://research.nccgroup.com/2022/12/05/exploring-prompt-injection-attacks/>

**Design rationale:**
Encoding-based evasion techniques attempt to bypass keyword-based input filters
by disguising the injection payload. Three representative techniques are covered:

| Case name                       | Technique                                        |
|---------------------------------|--------------------------------------------------|
| encoding_base64_instruction     | Base64-encoded instruction payload               |
| encoding_unicode_confusables    | Homoglyph substitution (visually identical chars)|
| encoding_separator_injection    | Custom delimiter / separator-based context split |

---

## OWASP and Industry References

- **OWASP LLM Top 10 - LLM01: Prompt Injection**
  <https://owasp.org/www-project-top-10-for-large-language-model-applications/>

- **MITRE ATLAS - AML.T0051: LLM Prompt Injection**
  <https://atlas.mitre.org/techniques/AML.T0051>

- **NIST AI 100-1: Artificial Intelligence Risk Management Framework**
  <https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf>
