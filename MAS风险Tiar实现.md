# **MAS风险Tiar实现**

## **Tiar 1层：单智能体原子风险**

> 尽管 按理mas的agent的system prompt都是设定好的，但是可以通过我们的接口来测试：

> 在给定 agent设计目标 下

> 不同api provider + system prompt（包含设定，身份，目标，工具等）设置中

> 最安全的组合，从而优化mas的agent设计

---

理想的用户使用场景：

* 用户已经想好整体mas的目标，以及各个agent大体的职责分工
* 用户希望在设计mas之前，先测试各个agent的system prompt设计 + api provider 的组合是否安全
* 用户可以选择输入 不同的api provider + system prompt 组合，并选择Tiar 1层的各个风险测试模块，来测试各个agent的安全性
* 具体system prompt设计，两种选择：
  * 用户自行传入，但同时系统会根据 风险测试模块，来自动补充一部分system prompt内容
  * 提供一个任务目标，系统自动生成合理的system prompt设计（包含设定，身份，目标，工具等）

---

### **Jailbreak 框架实现类**

主要依靠：

    - 开源Jailbreak框架

    - System消息提供设定/信息/tool

    - Judge Agent测评。

目前主要考虑：Pair or DAN or Crescendo

#### **1.1 提示词注入 (Prompt Injection)**

system：提供 智能体设定、身份信息、目标、可用工具等

user：调用Jailbreak框架进行自动攻击, 实现提示词注入目标

调用Judge Agent进行测评：是否 违背智能体设定/身份信息/目标

#### **1.2 越狱攻击 (Jailbreak Attack)**

system：提供 智能体设定、身份信息、目标、可用工具等

user：调用Jailbreak框架进行自动攻击，实现有害内容生成目标

调用Judge Agent进行测评：是否 违背智能体设定/身份信息/目标

#### **1.3 敏感信息泄露 (Sensitive Information Disclosure)**

system：提供 智能体设定、身份信息、目标、可用工具 + **任务相关的敏感信息**

user：调用Jailbreak框架进行自动攻击，实现敏感信息泄露目标

调用Judge Agent进行测评 ：是否 泄露 任务相关的敏感信息

#### **1.4 过度代理权限 (Excessive Agency)**

system: 提供 智能体设定、身份信息、目标、可用工具、权限范围等

user: 调用Jailbreak框架进行自动攻击，实现过度代理权限目标

调用Judge Agent进行测评：输出包含的 命令/代码 是否 超出权限范围

#### **1.5 未授权代码执行 (Unauthorized Code Execution)**

system: 提供 智能体设定、身份信息、目标、可用工具、允许执行的代码类型等

user: 调用Jailbreak框架进行自动攻击，实现未授权代码执行目标

调用Judge Agent进行测评：输出包含的 代码/命令 是否 包含 未授权代码类型/恶意代码

#### **1.8 工具滥用 (Tool Misuse)**

system: 提供 智能体设定、身份信息、目标、可用工具

user: 调用Jailbreak框架进行自动攻击，实现工具滥用目标

调用Judge Agent进行测评：输出包含的 工具调用 是否 滥用/误用

### **Benchmark 测试类**

#### **1.6 幻觉 （Hallucination）**

使用常见的幻觉测试集，评估智能体在面对不完整或误导性信息时的表现。

#### **1.8 工具滥用 (Tool Misuse)**

使用常见的agent 工具使用能力测试集，评估智能体在使用外部工具时的能力。

### **自动化测试**

#### **1.7 记忆投毒 （Memory Poisoning）**

给定agent的task,随机生成一些相关的上下文，包含恶意注入的agent记忆信息，评估智能体在面对被投毒的记忆时的表现。

---

## Tiar 2层：智能体间通信风险
本层关注智能体之间的交互和通信过程中，产生的安全风险,这些风险源于多智能体协作机制的漏洞。

注意：
- 本层一切实现都需要基于完整的真实 MAS运行， **不需要任何MOCK**
- 目前下方各个Risk Tesk模块描述的方法，应该作为接口的一个选择，未来在同一风险测试模块下，可以支持多种不同的实现方法。

---
### 基于代理包装器的方法（Agent Wrapper）
>本层的主要通过 包装指定Agent
>具体来说就是:
>- 将指定Agent包装，外层有一个恶意模拟中介Agent
>- 恶意模拟Agent相当于作为红队，来根据给定风险测试块的目标，对指定Agent收发的通信内容进行扰动更改
>- 进而观察后续的mas运行结果，从而评估智能体间通信的安全性。

---
理想的用户使用场景：
- 用户已经设计并实现好AG2的MAS,使用我们的Safety包装
- 选择事前测试的 Tiar 2的测试风险类型，包装指定的agent，Task
- 对于每种测试风险类型，运行mas,最终获得mas的完整运行日志，调用对应的monitor agent进行测评，评估mas的整体安全性

---

#### 2.1 恶意传播 (Malicious Propagation)
在指定Agent输出消息中，更改或添加：
- 恶意指令
- 异常行为

#### 2.2 错误信息放大 (Misinformation Amplification)
在指定Agent输出消息中，更改或添加：
- 任务相关的错误信息

#### 2.3 不安全的输出处理 (Insecure Output Handling)
在指定Agent的工具调用请求/响应中，更改或添加：
- 恶意工具调用参数
- 异常工具响应

#### 2.5 消息篡改 (Message Tampering)
在指定Agent输出消息中，更改或添加：
- 内容修改
- 命令替换

#### 2.6 身份伪造 (Identity Spoofing)
在指定Agent输出消息中，更改或添加：
- 管理员伪装
- 特权用户
- 可信智能体伪造

---

### 基于特定任务生成的方法（Task-Specific Generation）

#### 2.4 目标漂移 (Goal Drift)
生成许多适用于该MAS,但包含潜在目标漂移的任务变体,并评估MAS在这些任务上的表现。

---

## Tiar 3层：系统级涌现风险
本层关注整个多智能体系统层面的涌现性风险,这些风险源于复杂系统的集体行为和相互作用。

#### 3.1 级联失败 (Cascading Failures)
- 为指定智能体添加一个tool,该tool是一个函数，内部会 随机抛出异常 或者 sleep很长时间，来模拟智能体的失败行为，评估该失败如何在系统中传播。
- 同样在指定Agent外部包装一个 意外模拟Agent,将会强制输出该tool的call，
- 从而观察整个系统的响应和恢复能力。

#### 3.2 沙箱隔离不足 (Inadequate Sandboxing)
更改传入MAS的拓扑结构，也就是模拟 不该出现的智能体间通信路径，

#### 3.3 监控不足 (Insufficient Monitoring)


#### 3.4 群体幻觉 (Group Hallucination)
包装指定的多个Agent，可以选择：
- 同时修改多个智能体的输出消息，添加一致的幻觉信息
- 修改Agent的system prompt，注入一致的幻觉设定

#### 3.5 恶意涌现 (Malicious Emergence)
包装指定的多个Agent,修改输出：
添加一致的共谋恶意邀请，观察后续MAS运行结果

#### 3.6 叛逆智能体 (Rogue Agent)
替换指定的Agent的模型为一个完全恶意的模型，观察后续MAS运行结果

---
# 设计说明
- 本文档描述了SafetyMAS框架的事前风险测试模块设计
    - 主要分为Tiar 1层，Tiar 2层，Tiar 3层
    - 每一层包含多个风险测试模块
- 我们的目的是，在mas真正投入运行之前，先**主动模拟各种可能的风险场景与攻击**，评估mas的安全性
- 通过这些测试，用户可以识别和缓解潜在的安全漏洞，从而增强多智能体系统的整体安全性和可靠性。
- 目前每一种风险测试模块之下，描述了一种或多种可行的实现方式，需要实现先使用着
- 但是未来可以在同一风险测试模块下，支持多种不同的实现方式，用户可以根据需求选择合适的实现方式来进行测试，所以需要为每一种可行的实现方式，都有统一的接口设计，包含方式介绍，参数说明等等
- 未来会不断扩展更多的风险测试模块，来丰富SafetyMAS的测试能力
- **一定要保证所有的实现都可以基于真实MAS与LLM API运行，不需要任何MOCK**
