# Jailbreak Dataset Sources

## JBB-Behaviors

**Citation:** Mazeika, M., Phan, L., Yin, X., Zou, A., Wang, Z., Mu, N., Sakhaee, E., Li, C.,
Basart, S., Li, B., Forsyth, D., & Hendrycks, D. (2024). HarmBench: A Standardized Evaluation
Framework for Automated Red Teaming and Robust Refusal. *arXiv:2402.04249*.

**Description:** A curated set of harmful behaviors derived from the HarmBench benchmark.
Cases cover categories including chemical/biological weapons, cyberattacks, harmful content
generation, and personal harm. 10 cases selected to represent diverse attack surfaces.

---

## DAN Collection

**Citation:** Community-collected DAN (Do Anything Now) prompts. Various online sources
including r/ChatGPT, jailbreakchat.com, and security researcher disclosures (2022–2024).

**Description:** Classic DAN-style jailbreak prompts that attempt to override AI safety
constraints by instructing the model to adopt an unrestricted alter ego. 5 cases covering
DAN v11, token injection, mode-switch, and opposite-mode variants.

---

## Crescendo / Multi-Turn

**Citation:** Russinovich, M., Salem, A., & Eldan, R. (2024). Great, Now Write an Article
About That: The Crescendo Multi-Turn LLM Jailbreak Attack. *arXiv:2404.01833*.

**Description:** Multi-turn jailbreak attacks that gradually escalate the harmfulness of
requests across conversation turns, starting with benign questions and pivoting to dangerous
content. 3 cases across chemistry, cybersecurity, and social engineering domains.

---

## Many-Shot

**Citation:** Anil, C., Durmus, E., Sharma, M., Benton, J., Kundu, S., Batson, J.,
Rimsky, N., Tong, M., Engstrom, L., Marks, S., Nanda, N., Olah, C., et al. (2024).
Many-Shot Jailbreaking. *Anthropic Technical Report*.

**Description:** Jailbreak attacks that exploit long-context models by conditioning
compliance through many benign question-answer pairs before injecting a harmful request.
2 cases covering explicit many-shot conditioning and role-conditioning patterns.

---

## Multilingual

**Citation:** Deng, Y., Zhang, W., Pan, S. J., & Bing, L. (2024). Multilingual Jailbreak
Challenges in Large Language Models. *arXiv:2310.06474*.

**Description:** Jailbreak prompts written in non-English languages to test whether safety
alignments transfer across languages. 2 cases in Mandarin Chinese and Arabic covering
identity-override and roleplay-bypass patterns.
