"""回复型专家共用的零件。

什么时候该往这里加东西:出现了第二个消费者,而且逻辑真的相同。
现在消费者是 chitchat 和 retriever,所以这里只放它们确实重复的四件事:
历史消息还原、参数现状描述、确认门槛状态、agent_trace 追加。
某个专家专属的 prompt 内容留在它自己的模块里,不要往上抽。
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from app.graph.params import PARAM_FIELDS, is_ready, missing_params
from app.graph.state import ChatState

HISTORY_LIMIT = 20  # 只喂最近这些条,防对话过长拖慢速度、抬高成本


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
