"""对话图的状态(ChatState)。

图本身不挂 checkpointer:状态由 chat.handle_turn 从 Redis 载入、跑完写回
(native JSON,Windows Redis 无 RediSearch)。所有字段可选(total=False),
因为 Redis 里存的是历史版本的旧 state,新字段可能不存在。
"""
from __future__ import annotations

from typing import TypedDict


class ChatState(TypedDict, total=False):
    # ---- 会话与输入 ----
    thread_id: str
    messages: list[dict]   # 对话气泡:{"role":"user"|"assistant","content":str}
    new_message: str       # 本轮用户刚发的原文

    # ---- 参数收集 ----
    params: dict           # 已确定参数(只含用户明说过的)
    insisted_sig: str      # 用户已接受"按最省"的路由签名,同路由不再拦

    # ---- 本轮输出 ----
    reply: str
    status: str
    ready: bool

    # ---- 预算护栏 ----
    low_budget: bool       # 本轮预算低于路线最低花费,确认被按灰
    min_budget: float

    # ---- 多 Agent 新增 ----
    intent: str            # supervisor 路由结果:chitchat|guide|weather|budget|collect|plan|revise
    plan: dict             # 最近一次生成的 TripPlan(reviser 的输入,generate 后写回)
    critique: dict         # critic 结果 {"pass": bool, "issues": [str]}
    revision_round: int    # 修订环计数,防死循环(上限 1)
    agent_trace: list[str] # 本轮走过的专家顺序,调试/可观测用
    weather: dict          # 缓存过的目的地逐日预报,供 planner 注入
