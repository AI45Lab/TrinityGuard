## src分析TODO
- logger回头分析
- run_direct后续优化或者完善 
- 拓扑结构获取的函数：加入可视化
- mock全删了
- inject_tool_call 是真实调用工具，但是并没有被用到
- interceptingWorkflowRunner 它给所有的agent都注册了 hook,但实际上底层因为是包装send,只需要对source agent注册hook就行了

# 周四Todo
- 完善项目文档，面向展示我们已完成的项目功能
- 测试接入EvoagentX2AG2的系统，看能否跑通
- 选择一到两个具体风险，接入已实现的外部评估/攻击方法



# 长期计划
- 渐进式披露：一个总的global monitor agent，知道各个monitor agent的功能和使用方法
    - 预期应将 初始化各个monitor agent 作为一个 mcp tool, 由 global monitor agent 调用
    - global monitor agent会实时浏览总的日志 与 目前已启用的各个monitor agent的监控结果， 来决定是否增加新的monitor agent
- 其余风险的，继续接入外部方法
- 最好是针对evoagentx2ag2的上游框架,完整的测试 
- 开源主页



