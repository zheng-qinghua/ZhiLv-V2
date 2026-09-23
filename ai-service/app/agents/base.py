"""回复型专家共用的零件。

什么时候该往这里加东西:出现了第二个消费者,而且逻辑真的相同。
现在消费者是 chitchat / retriever / budget / weather,这里放它们确实重复的这几件事:
历史消息还原、参数现状描述、确认门槛状态、agent_trace 追加、function calling 工具循环。
某个专家专属的 prompt 内容留在它自己的模块里,不要往上抽。
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.graph.params import PARAM_FIELDS, is_ready, missing_params
from app.graph.state import ChatState

HISTORY_LIMIT = 20  # 只喂最近这些条,防对话过长拖慢速度、抬高成本
MAX_TOOL_ROUNDS = 2  # 允许"查 → 觉得不够再查"一轮,再多就是模型在打转


def trace(state: ChatState, name: str) -> list[str]:
    """本轮走过的专家,追加一个。"""
    return list(state.get("agent_trace") or []) + [name]


def param_status_text(params: dict) -> str:
    """告诉模型"哪些参数定了、哪些还没定",它据此决定要不要追问。"""
    line = "、".join(f"{k}={params[k]}" for k in PARAM_FIELDS if params.get(k) is not None) or "尚无"
    missing = missing_params(params)
    return f"\n\n已确定:{line}\n未确定:{'、'.join(missing) if missing else '无'}"


def ready_status(params: dict) -> tuple[bool, str]:
    """确认门槛:出发地+目的地+时间齐了才让点「确认行程」。"""
    ready = is_ready(params)
    return ready, ("await_confirm" if ready else "collecting")


def history_messages(state: ChatState) -> list:
    """把对话气泡还原成 LangChain 消息(只取最近 HISTORY_LIMIT 条)。"""
    out = []
    for m in (state.get("messages") or [])[-HISTORY_LIMIT:]:
        content = m.get("content", "")
        out.append(HumanMessage(content=content) if m.get("role") == "user"
                   else AIMessage(content=content))
    return out


def with_reply(state: ChatState, reply: str) -> list[dict]:
    """把助手回复追加进对话历史 —— 少这一步,下一轮的 supervisor 就看不到这轮说了什么。"""
    return list(state.get("messages") or []) + [{"role": "assistant", "content": reply}]


def tool_loop(llm, messages: list, tools, max_rounds: int = MAX_TOOL_ROUNDS) -> str:
    """给模型绑上工具跑循环:它要工具就给结果,直到它给出正文;只返回正文。

    为什么要自己写循环而不是用 ToolNode:ToolNode 需要一个带 messages 的子图,
    而本项目的图是扁平 dict 状态。循环很短,自己写更好读。

    降级都在这一个函数里:渠道不支持 function calling → 卸掉工具直接答;
    工具名不存在/工具自己抛错 → 返回一句可读文本让模型换个方式,不往上抛;
    轮次用尽还在要工具 → 卸掉工具,逼它基于已有资料作答。
    """
    try:
        tool_llm = llm.bind_tools(list(tools))
    except Exception:
        return _plain(llm, messages)
    by_name = {t.name: t for t in tools}
    convo = list(messages)
    for _ in range(max_rounds):
        ai = tool_llm.invoke(convo)
        calls = list(getattr(ai, "tool_calls", None) or [])
        if not calls:
            return str(getattr(ai, "content", "") or "").strip()
        convo.append(ai)
        for call in calls:
            convo.append(ToolMessage(content=_run_tool(call, by_name),
                                     tool_call_id=str(call.get("id") or "")))
    convo.append(HumanMessage(content="请基于上面查到的资料直接给出回答,不要再调用工具。"))
    return _plain(llm, convo)


def _run_tool(call: dict, by_name: dict) -> str:
    """执行模型请求的一次工具调用,任何失败都转成可读文本而不是异常。"""
    name = str(call.get("name") or "")
    tool = by_name.get(name)
    if tool is None:
        return f"（没有名为 {name} 的工具）"
    try:
        return str(tool.invoke(call.get("args") or {}))
    except Exception as exc:
        return f"（工具 {name} 调用失败:{type(exc).__name__}）"


def _plain(llm, messages: list) -> str:
    return str(getattr(llm.invoke(messages), "content", "") or "").strip()
