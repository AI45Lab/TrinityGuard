# MAS风险Tiar实现

## Tiar 1层：单智能体原子风险
>尽管 按理mas的agent的system prompt都是设定好的，但是可以通过我们的接口来测试：
>- 在给定 agent设计目标 下
>- 不同api provider + system prompt（包含设定，身份，目标，工具等）设置中
>- 最安全的组合，从而优化mas的agent设计
---
理想的用户使用场景：
- 用户已经想好整体mas的目标，以及各个agent大体的职责分工
- 用户希望在设计mas之前，先测试各个agent的system prompt设计 + api provider 的组合是否安全
- 用户可以选择输入 不同的api provider + system prompt 组合，并选择Tiar 1层的各个风险测试模块，来测试各个agent的安全性
- 具体system prompt设计，两种选择：
    - 用户自行传入，但同时系统会根据 风险测试模块，来自动补充一部分system prompt内容
    - 提供一个任务目标，系统自动生成合理的system prompt设计（包含设定，身份，目标，工具等）

---

### Jailbreak 框架实现类
主要依靠：
    - 开源Jailbreak框架
    - System消息提供设定/信息/tool 
    - Judge Agent测评。
目前主要考虑：Pair or DAN or Crescendo

#### 1.1 提示词注入 (Prompt Injection)
system：提供 智能体设定、身份信息、目标、可用工具等
user：调用Jailbreak框架进行自动攻击
调用Judge Agent进行测评：是否 违背智能体设定/身份信息/目标

#### 1.2 越狱攻击 (Jailbreak Attack)
system：提供 智能体设定、身份信息、目标、可用工具等
user：调用Jailbreak框架进行自动攻击
调用Judge Agent进行测评：是否 违背智能体设定/身份信息/目标

#### 1.3 敏感信息泄露 (Sensitive Information Disclosure)
system：提供 智能体设定、身份信息、目标、可用工具 + **任务相关的敏感信息**
user：调用Jailbreak框架进行自动攻击
调用Judge Agent进行测评 ：是否 泄露 任务相关的敏感信息

#### 1.4 过度代理权限 (Excessive Agency)
system: 提供 智能体设定、身份信息、目标、可用工具、权限范围等
user: 调用Jailbreak框架进行自动攻击
调用Judge Agent进行测评：输出包含的 命令/代码 是否 超出权限范围

#### 1.5 未授权代码执行 (Unauthorized Code Execution)
system: 提供 智能体设定、身份信息、目标、可用工具、允许执行的代码类型等
user: 调用Jailbreak框架进行自动攻击
调用Judge Agent进行测评：输出包含的 代码/命令 是否 包含 未授权代码类型/恶意代码

### 1.8 工具滥用 (Tool Misuse)
system: 提供 智能体设定、身份信息、目标、可用工具
user: 调用Jailbreak框架进行自动攻击
调用Judge Agent进行测评：输出包含的 工具调用 是否 滥用/误用

### Benchmark 测试类

#### 1.6 幻觉 （Hallucination）
使用常见的幻觉测试集，评估智能体在面对不完整或误导性信息时的表现。

#### 1.8 工具滥用 (Tool Misuse)
使用常见的agent 工具使用能力测试集，评估智能体在使用外部工具时的能力。

### 自动化测试

#### 1.7 记忆投毒 （Memory Poisoning）
给定agent的task,随机生成一些相关的上下文，包含恶意注入的agent记忆信息，评估智能体在面对被投毒的记忆时的表现。

---

## Tiar 2层：智能体间通信风险

>本层的主要通过包装指定Agent，具体来说就是通过


