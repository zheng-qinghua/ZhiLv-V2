"""天气专家:回答"大理明天天气怎么样""去那边要带伞吗"。

数据不在 Python 侧:模型调 get_weather 工具 —— 工具再回调 Java 的 /internal/weather
(高德 key 在 backend),这里只负责组织回复。
为什么用工具而不是直接拿 params.destination 查:supervisor 对天气问句的目的地抽取不稳
(实测 1/4 抽不到),由模型读对话定城市更稳。

降级:渠道不支持 function calling → 卸掉工具答(此时没数据,回复会明说查不到);
查不到就明说查不到并建议看天气 App,绝不拿常识编预报 —— 天气是"查得到才算数"的信息,
编一个"大理明天多云 25 度"比说不知道更糟。
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage

from app.agents import base
from app.graph.state import ChatState
from app.llm import build_chat_llm
from app.tools.weather_tool import WEATHER_TOOLS

_SYS = (
    "你是旅行天气助手。先用 get_weather 工具查用户问的那个城市的预报,再依据查到的结果回答。"
    "只报预报里有的信息,预报里没有的不要补;工具说没查到就直说暂时查不到、建议看天气 App,"
    "绝不凭常识编天气或温度。"
    "用户问的是哪一天(今天/明天/后天/具体日期)要对照查到的日期算清楚,别答错日子 —— "
    "标了「(今天)」的那条就是今天。"
    "城市以用户这次问的为准(可能不是本次行程的目的地);实在没提到任何城市时才问一句。"
    "回复简洁(通常不超过 120 字),可以顺带给一两句穿衣/带伞建议。"
)


def weather_node(state: ChatState) -> dict:
    trace = base.trace(state, "weather")
    params = state.get("params") or {}
    ready, status = base.ready_status(params)

    llm = build_chat_llm()
    if llm is None:
        return {"reply": "当前未配置 LLM_API_KEY,无法回答。请在 ai-service/.env 填好密钥后再试。",
                "status": "failed", "ready": ready, "agent_trace": trace}

    messages = [SystemMessage(content=_SYS + base.param_status_text(params))]
    messages += base.history_messages(state)

    try:
        reply = base.tool_loop(llm, messages, WEATHER_TOOLS)
    except Exception as exc:
        reply = "回复生成超时/失败,请换个更短的说法再试。" if "Timeout" in type(exc).__name__ else \
            f"回复生成失败:{type(exc).__name__}:{exc}"
        return {"reply": reply, "status": "failed", "ready": ready, "agent_trace": trace}

    if not reply:
        reply = "抱歉,天气我这边暂时查不到,建议用天气 App 确认一下。"
    return {
        "reply": reply,
        "status": status,
        "ready": ready,
        "messages": base.with_reply(state, reply),
        "agent_trace": trace,
    }
