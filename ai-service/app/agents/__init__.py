"""专家 Agent 层:每个模块负责一类任务,由图(supervisor 的条件边)决定调用谁。

约定:
  - 每个 Agent 暴露一个 `<name>_node(state) -> dict`,返回值是"要写回 state 的部分字段",
    不直接改 state(和 LangGraph 节点约定一致)。
  - 单个 Agent 失败一律降级(返回兜底内容),不抛异常打断对话。
  - Agent 之间不互相调用;共用逻辑放 base.py,参数工具放 graph/params.py。

架构见 docs/MULTI_AGENT_PLAN.md。
"""
