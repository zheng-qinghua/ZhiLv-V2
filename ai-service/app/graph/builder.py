"""图的组装。两个入口各一张图,共用同一批节点函数:

  GRAPH            START → supervisor →(条件边)专家 → END      —— 对话入口
  GENERATE_GRAPH   START → planner → critic →(不过关)reviser   —— 生成入口(点「确认行程」)

为什么要两张图(而不是让 confirm 也进 GRAPH):点按钮时没有新消息,supervisor 拿到空
消息会把它判成 collect、把 status 打回 collecting,confirm 就废了。绕开 supervisor 的代价
是会绕开 critic —— 同一个请求,点按钮和打字生成出来的质量不一样。所以 confirm 走
GENERATE_GRAPH:**复用 planner/critic/reviser 三个节点和 should_revise 这一个判断**,
只是不经过 supervisor。重复的只有 4 行接线,没有重复的逻辑。

路由表 ROUTES 是改对话路由的唯一地方:intent → 节点名,加一个专家就加一行映射。
没接的 intent 一律回落到 chitchat,保证对话永不落空。
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.budget import budget_node
from app.agents.chitchat import chitchat_node
from app.agents.critic import critic_node
from app.agents.planner import planner_node
from app.agents.retriever import retriever_node
from app.agents.reviser import reviser_node, should_revise
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
    "plan": "planner",      # 生成行程 → planner → critic(不过关再 reviser)
    "revise": "reviser",    # 用户主动改行程(supervisor 已保证此时 state["plan"] 非空)
}


def route(state: ChatState) -> str:
    """条件边:按 supervisor 判出的 intent 选下一个节点。"""
    return ROUTES.get(str(state.get("intent") or ""), FALLBACK)


def _add_writers(g: StateGraph) -> None:
    """把"写行程"这一串节点挂到图上(两张图共用)。"""
    g.add_node("planner", planner_node)
    g.add_node("critic", critic_node)
    g.add_node("reviser", reviser_node)


def _wire_review(g: StateGraph) -> None:
    """planner → critic →(不过关)reviser → critic 的接线(两张图共用)。

    revision_round 由 reviser 自己 +1、should_revise 校验上限,所以 reviser→critic
    这圈最多转一次,不会无限循环。
    """
    g.add_edge("planner", "critic")
    g.add_conditional_edges("critic", should_revise, {"done": END, "revise": "reviser"})
    g.add_edge("reviser", "critic")


def build_graph():
    g = StateGraph(ChatState)

    g.add_node("supervisor", supervisor_node)
    g.add_node("chitchat", chitchat_node)
    g.add_node("retriever", retriever_node)
    g.add_node("budget", budget_node)
    g.add_node("weather", weather_node)
    _add_writers(g)

    g.add_edge(START, "supervisor")
    # path_map 显式列出所有可能的目标节点(值=节点名),route 返回表外的值会直接报错而不是静默走错
    g.add_conditional_edges("supervisor", route, {n: n for n in set(ROUTES.values())})

    g.add_edge("chitchat", END)
    g.add_edge("retriever", END)
    g.add_edge("budget", END)
    g.add_edge("weather", END)
    _wire_review(g)
    return g.compile()


def build_generate_graph():
    """生成专用图:不起 supervisor,直接从 planner 进,但质检和修订一个不少。"""
    g = StateGraph(ChatState)
    _add_writers(g)
    g.add_edge(START, "planner")
    _wire_review(g)
    return g.compile()


GRAPH = build_graph()
GENERATE_GRAPH = build_generate_graph()
