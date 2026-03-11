# Code Agent 安全监控与自监控 Skills 相关工作调研

## 背景与目标

本文整理可用于 code agent（如 Claude Code、Codex）安全能力建设的相关工作，覆盖两类需求：

- 对外安全监控：识别输入攻击、输出泄露、工具调用风险、代码安全风险。
- 对内自监控：agent 对自身行为进行策略校验、权限约束、审计追踪与异常中止。

## 相关工作清单

### 1. OpenAI Guardrails (Python)

- 能力：输入/输出校验、PII 检测、越狱检测、主题限制等。
- 用途：作为通用 guardrail 层，拦截不安全请求与不合规输出。
- 链接：https://github.com/openai/openai-guardrails-python

### 2. Anthropic Claude Code Security

- 能力：权限门控、命令拦截、提示注入防护。
- 用途：可作为 code agent 自身安全监控的基线设计参考。
- 链接：https://docs.claude.com/en/docs/claude-code/security

### 3. Claude Security Guidance 插件

- 能力：在工具执行前扫描高危模式（如命令注入、XSS、危险 eval 等）。
- 用途：作为 pre-tool hook 对代码与命令进行实时安全检查。
- 链接：https://claude.com/plugins/security-guidance

### 4. NVIDIA NeMo Guardrails

- 能力：self-check input、self-check output、fact-check 等 rail。
- 用途：实现 agent 自检闭环，在关键节点执行自我校验。
- 链接：https://docs.nvidia.com/nemo/guardrails/latest/configure-rails/guardrail-catalog.html

### 5. LangChain Guardrails

- 能力：在 model/tool 调用前后挂接中间件进行策略拦截与审计。
- 用途：适合多工具链 agent 的统一安全治理。
- 链接：https://docs.langchain.com/oss/python/langchain/guardrails

### 6. Lakera Guard

- 能力：检测 prompt attack、数据泄露风险等。
- 用途：作为外部安全检测服务，为 agent 提供二次判定。
- 链接：https://docs.lakera.ai/guard

### 7. OWASP Top 10 for LLM Applications v1.1

- 能力：提供 LLM 应用常见风险分类（如数据泄露、过度代理等）。
- 用途：用于技能设计时的威胁建模与检查清单。
- 链接：https://owasp.org/www-project-top-10-for-large-language-model-applications/

### 8. NIST AI RMF + GenAI Profile

- 能力：提供组织级 AI 风险管理框架与治理方法。
- 用途：定义持续监控指标、流程与审计要求。
- 链接：https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence

### 9. Google SAIF Top Risks

- 能力：提供面向生成式 AI 的关键风险视角与防护建议。
- 用途：可映射为 agent 的控制项（输出净化、权限控制、可观测性）。
- 链接：https://saif.google/secure-ai-framework/risks

### 10. MCP Security / Authorization 规范

- 能力：定义 agent 与工具边界的授权与安全要求。
- 用途：在 MCP 工具生态中构建最小权限与可信调用路径。
- 链接：
  - https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization
  - https://modelcontextprotocol.info/specification/draft/

## 现成 Safety Skills 调研补充（2026-03-06）

以下为“可直接拿来用”或“已有公开实现”的 safety skills 方向，优先列出可核验的一手仓库条目。

### A. OpenAI 官方 curated skills（可直接安装思路参考）

1. `security-best-practices`
- 能力：对生成代码执行安全最佳实践检查，并结合 Semgrep 等规则做漏洞扫描。
- 适配场景：代码生成后自动安全审查、PR 前置安全门禁。
- 链接：https://github.com/openai/skills/tree/main/skills/.curated/security-best-practices

2. `security-ownership-map`
- 能力：将代码区域映射到 owner、风险分层与安全热点。
- 适配场景：安全事件分派、风险代码归口治理、自监控告警路由。
- 链接：https://github.com/openai/skills/tree/main/skills/.curated/security-ownership-map

3. `security-threat-model`
- 能力：基于架构与数据流生成轻量威胁模型（含 STRIDE/LINDDUN 视角）。
- 适配场景：需求评审前 threat modeling、agent 执行前风险预估。
- 链接：https://github.com/openai/skills/tree/main/skills/.curated/security-threat-model

### B. 社区可见的现成安全技能目录（建议二次审计后再接入）

1. `security-threat-model`（社区镜像条目）
- 说明：目录中标注来源为 `lyndonkl/claude-code-language-skills`，定位为威胁建模能力。
- 链接：https://agent-skills.com/skills/security-threat-model

2. `threat-model`（社区镜像条目）
- 说明：目录中标注来源为 `cosmix/claude-loom`，同样聚焦威胁建模。
- 链接：https://agent-skills.com/skills/threat-model

3. `performing-security-audits` / `performing-penetration-testing`（社区技能目录）
- 说明：偏“安全审计与渗透测试流程化”技能，可作为外层审计 skill 的模板来源。
- 链接：
  - https://claude-plugins.dev/skills/performing-security-audits/
  - https://claude-plugins.dev/skills/performing-penetration-testing/

### C. 接入建议

- 对官方 curated skills：可优先纳入 P0，作为“代码安全扫描 + 威胁建模 + 风险归属”三件套。
- 对社区技能：先做供应链与内容审计（来源、更新频率、提示词安全性、外部依赖）再接入。
- 对自监控目标：建议把 `security-threat-model` 放在任务开始前，把 `security-best-practices` 放在代码产出后，形成前后双闸门。

## 面向 Skills 的落地映射建议

可将上述相关工作拆分为以下技能方向：

- `input-guard-skill`：提示注入检测、敏感词与越狱语义识别。
- `output-guard-skill`：PII/机密信息泄露检测、危险内容降级输出。
- `tool-policy-skill`：命令白名单、参数约束、执行前审批与阻断。
- `code-security-skill`：静态规则扫描（注入、XSS、反序列化、危险 API）。
- `self-audit-skill`：自检链路、策略命中日志、风险评分与自动中止。
- `governance-skill`：映射 OWASP/NIST/SAIF 控制项，输出合规报告。

## 备注

- 本文为“相关工作”汇总，优先列出官方文档、官方仓库与标准组织资料。
- 若后续需要，可进一步扩展为“技能优先级路线图”（P0/P1/P2）与“最小可用安全基线”。
