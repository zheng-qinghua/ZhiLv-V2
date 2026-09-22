"""Agent 可调用的工具(function calling)。

约定:
  - 用 langchain_core.tools 的 @tool 装饰,docstring 就是给模型看的工具说明,
    所以 docstring 必须写清"什么时候该用它",不能只写它做了什么。
  - 工具自己吞异常,返回一句可读的"没查到"而不是抛错 —— 模型据此换个方式再试,
    整条链路不该因为一个检索失败就断掉。
"""
