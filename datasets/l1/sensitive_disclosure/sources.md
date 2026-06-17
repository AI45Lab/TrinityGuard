# Sources – L1.3 Sensitive Disclosure Dataset

This document records the academic papers, benchmark suites, and industry
references that informed the 20 static test cases in `static_cases.yaml`.

---

## 1. Pleak / Direct System-Prompt Extraction

**Perez & Ribeiro (2022) – "Ignore Previous Prompt: Attack Techniques For Language Models"**
- arXiv: https://arxiv.org/abs/2211.09527
- Introduces the term *prompt leaking* and demonstrates verbatim repetition,
  continuation, and paraphrase attacks that can extract a model's hidden context.
- Inspired cases: `pleak_repeat_instructions`, `pleak_what_were_you_told`,
  `pleak_summarize_prompt`, `pleak_continuation_trick`, `pleak_translate_prompt`

**Greshake et al. (2023) – "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection"**
- arXiv: https://arxiv.org/abs/2302.12173
- Shows how retrieval-augmented pipelines can leak system prompts through
  injected documents.
- Relevant background for `pleak_continuation_trick` and `spe_debug_flag`.

---

## 2. Gandalf-Game / Encoding-Based Extraction

**Lakera AI – "Gandalf" Red-Teaming Game (2023)**
- https://gandalf.lakera.ai/
- Public benchmark where players attempt to extract a password from an AI by
  progressively refining prompt strategies (incremental extraction, encoding
  tricks, steganography).
- Inspired cases: `gandalf_first_word`, `gandalf_base64_encode`,
  `gandalf_acrostic_prompt`, `gandalf_last_character`, `gandalf_morse_code`

**Schulhoff et al. (2023) – "Ignore This Title and HackAPrompt: Exposing Systemic Vulnerabilities of LLMs through a Global Scale Prompt Hacking Competition"**
- arXiv: https://arxiv.org/abs/2311.16119
- Catalogues encoding-based (Base64, ROT-13, Morse) bypass attempts collected
  from a large-scale competition.
- Relevant to `gandalf_base64_encode` and `gandalf_morse_code`.

---

## 3. System-Prompt Extraction – Direct / Roleplay

**Kang et al. (2023) – "Exploiting Programmatic Behavior of LLMs: Dual-Use Through Standard Security Attacks"**
- arXiv: https://arxiv.org/abs/2302.05733
- Describes privilege-escalation roleplays (developer mode, admin mode) as
  extraction vectors.
- Inspired cases: `spe_developer_mode`, `spe_debug_flag`.

**Wei et al. (2023) – "Jailbroken: How Does LLM Safety Training Fail?"**
- arXiv: https://arxiv.org/abs/2307.02483
- Analyses persona-switch ("pretend you are an uncensored model") and
  hypothetical-framing strategies.
- Inspired cases: `spe_roleplay_as_other_model`, `spe_hypothetical_frame`.

**Deng et al. (2023) – "Master Key: Jailbreaking Second-Generation LLM-Integrated Applications"**
- arXiv: https://arxiv.org/abs/2307.17337
- Demonstrates architecture-disclosure attacks against LLM-integrated pipelines.
- Inspired case: `spe_architecture_disclosure`.

---

## 4. PII Leakage

**OWASP Top 10 for LLM Applications – LLM06:2023 Sensitive Information Disclosure**
- https://owasp.org/www-project-top-10-for-large-language-model-applications/
- The primary industry classification for PII leakage, credential exposure, and
  training-data extraction risks in LLM systems.
- Applies to all five PII cases and all four credential-extraction cases.

**Carlini et al. (2021) – "Extracting Training Data from Large Language Models"**
- arXiv: https://arxiv.org/abs/2012.07805
- Shows verbatim memorisation of PII (email addresses, phone numbers, SSNs)
  in GPT-2; foundational motivation for `pii_*` cases.

**Lukas et al. (2023) – "Analyzing Leakage of Personally Identifiable Information in Language Models"**
- arXiv: https://arxiv.org/abs/2302.00539
- Quantifies PII extraction risk across multiple model families and introduces
  "association attacks" (name + DOB → SSN).
- Directly inspired `pii_social_security_number` and `pii_extract_other_users`.

---

## 5. Credential Extraction

**OWASP Top 10 for LLM Applications – LLM06:2023 (see above)**

**Abdelnabi et al. (2023) – "Not What You've Signed Up For" (see Greshake et al. above)**

**PortSwigger Web Security Academy – "Prompt Injection" (2023)**
- https://portswigger.net/web-security/llm-attacks
- Documents environment-variable and API-key extraction patterns in LLM-backed
  web applications.
- Inspired `cred_env_variable_dump` and `cred_api_key_direct`.

---

## 6. Dataset Construction Notes

- All 20 cases are manually authored; no real PII is included.
- Fake identifiers (e.g., "Jane Doe", "patient ID 10482") are used solely to
  test agent refusal behaviour; they do not correspond to real individuals.
- Severity ratings follow the OWASP LLM06 criticality definitions and the
  TrinityGuard `sensitive_disclosure.yaml` judge severity criteria
  (`none / info / warning / critical`).
- The dataset is intended for automated red-teaming within the TrinityGuard
  benchmark; it is not a comprehensive coverage of all possible disclosure
  attacks.
