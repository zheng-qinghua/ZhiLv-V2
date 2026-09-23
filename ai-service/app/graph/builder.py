"""图的组装:START → supervisor →(条件边)专家节点 → END。

路由表 ROUTES 是唯一改图的地方:intent → 节点名,加一个专家就加一行映射。
没接的 intent 一律回落到 chitchat,保证对话永不落空。

当前进度(见 docs/MULTI_AGENT_PLAN.md):
  已接:chitchat / retriever / budget / weather;plan/revise 待 Step 6~8。
在那些分支接上之前,supervisor 判出的 intent 只用于观察(probe 脚本),不影响走向。
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.budget import budget_node
from app.agents.chitchat import chitchat_node
from app.agents.retriever import retriever_node
from app.agents.supervisor import supervisor_node
from app.agents.weather import weather_node
from app.graph.state import ChatState

FALLBACK = "chitchat"

# intent → 节点名(值必须是下面 add_node 注册过的节点)
ROUTES: dict[str, str] = {
    "chitchat": "chitchat",
    "collect": "chitchat",  # 信息不全 → 由 chitchat 追问
    "guide": "retriever",   # 攻略/景点/美食/交通 → RAG 工具
    "budget": "budget",     # 预算够不够 → 路线最低花费估算 + 预算护栏
    "weather": "weather",   # 天气 → 回调 Java /internal/weather(高德 key 在 Java)
    # "plan": "planner",        # Step 6(planner → critic → …)
    # "revise": "reviser",      # Step 8
}


def route(state: ChatState) -> str:
    """条件边:按 supervisor 判出的 intent 选下一个节点。"""
    return ROUTES.get(str(state.get("intent") or ""), FALLBACK)


def build_graph():
    g = StateGraph(ChatState)

    g.add_node("supervisor", supervisor_node)
    g.add_node("chitchat", chitchat_node)
    g.add_node("retriever", retriever_node)
    g.add_node("budget", budget_node)
    g.add_node("weather", weather_node)

    g.add_edge(START, "supervisor")
    # path_map 显式列出所有可能的目标节点(值=节点名),route 返回表外的值会直接报错而不是静默走错
    g.add_conditional_edges("supervisor", route, {n: n for n in set(ROUTES.values())})

    g.add_edge("chitchat", END)
    g.add_edge("retriever", END)
    g.add_edge("budget", END)
    g.add_edge("weather", END)
    return g.compile()


GRAPH = build_graph()
