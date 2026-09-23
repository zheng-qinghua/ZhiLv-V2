"""攻略检索专家:回答景点/美食/交通/玩法这类知识性问题。

走 function calling:把攻略检索包成工具交给模型,由它自己决定
  查什么(把"大理有什么好吃的"改写成"大理 美食 推荐"这种检索式)、
  用哪个工具(宽泛问题取整篇城市指南,具体问题做语义检索)、
  查几次(不够可以再查一轮)。
循环本身在 agents/base.tool_loop —— weather 是第二个消费者,所以放公共处。

降级:渠道不支持 function calling → 卸掉工具直接答;工具报错 → 返回一句"没查到"
让模型换个方式;LLM 挂 → 回复一句可读的失败原因,不抛异常。
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage

from app.agents import base
from app.graph.state import ChatState
from app.llm import build_chat_llm
from app.tools.rag_tool import RAG_TOOLS

_SYS = (
    "你是旅行攻略专家,回答景点、美食、交通、玩法这类问题。"
    "回答前先用工具查真实资料:问某个城市整体怎么玩用 get_city_guide,"
    "问具体的事(某道菜、某个景点、某段路)用 search_guide。"
    "只依据查到的资料回答,绝不编造店名、价格、营业时间、门票;资料里没有的就直说没有。"
    "语气自然友好,回复简洁(通常不超过 150 字),别逐条罗列资料原文。"
)


def retriever_node(state: ChatState) -> dict:
    trace = base.trace(state, "retriever")
    params = state.get("params") or {}
    ready, status = base.ready_status(params)

    llm = build_chat_llm()
    if llm is None:
        return {"reply": "当前未配置 LLM_API_KEY,无法回答。请在 ai-service/.env 填好密钥后再试。",
                "status": "failed", "ready": ready, "agent_trace": trace}

    messages = [SystemMessage(content=_SYS + base.param_status_text(params))]
    messages += base.history_messages(state)

    try:
        reply = base.tool_loop(llm, messages, RAG_TOOLS)
    except Exception as exc:
        reply = "回复生成超时/失败,请换个更短的说法再试。" if "Timeout" in type(exc).__name__ else \
            f"回复生成失败:{type(exc).__name__}:{exc}"
        return {"reply": reply, "status": "failed", "ready": ready, "agent_trace": trace}

    if not reply:
        reply = "这方面我暂时没查到可靠资料,换个说法再问一次试试?"
    return {
        "reply": reply,
        "status": status,
        "ready": ready,
        "messages": base.with_reply(state, reply),
        "agent_trace": trace,
    }
