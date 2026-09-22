"""闲聊 / 追问专家:信息没齐时自然追问,信息齐了提示可以确认生成。

这是改造前 _respond_node 的完整逻辑,原样迁过来:
  - 带目的地时注入 RAG 参考片段;
  - 信息齐且预算过低时,回复里点明并说明"按最省"的口子;
  - 历史只喂最近若干条,防对话过长。

共用的零件(历史还原、参数现状、确认门槛、trace、追加回复)在 agents/base.py,
本模块只留 chitchat 专属的 prompt 和预算拦截分支。
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage

from app.agents import base
from app.agents.budget import low_block
from app.graph.state import ChatState
from app.llm import build_chat_llm
from app.rag.retrieve import format_for_prompt, retrieve


def chitchat_node(state: ChatState) -> dict:
    trace = base.trace(state, "chitchat")
    params = state.get("params") or {}
    ready, status = base.ready_status(params)

    llm = build_chat_llm()
    if llm is None:
        return {"reply": "当前未配置 LLM_API_KEY,无法回答。请在 ai-service/.env 填好密钥后再试。",
                "status": "failed", "ready": ready, "agent_trace": trace}

    dest = params.get("destination")
    ctx = ""
    if dest:
        try:
            ctx = format_for_prompt(retrieve(state.get("new_message") or f"{dest} 旅游攻略"))
        except Exception:
            ctx = ""

    # 预算不足拦截:信息齐且给过预算时,按路线最低花费判断要不要提醒并按住确认
    block = low_block(params, str(state.get("insisted_sig") or "")) if ready else None
    min_budget = round(block["min_total"]) if block else None

    role = (
        "你是一名贴心的中国旅行规划助手,正在和用户聊天收集行程需求。语气自然友好,回复简洁"
        "(通常不超过 120 字)。若还有关键信息(出发地/目的地/时间)没问全,结尾自然问一句,别用列表盘问。"
    )
    if block:
        role += (
            "注意:用户给出的预算(总额约 {} 元)明显低于这条路线的预估最低花费(约 {} 元,"
            "含往返大交通、按最省方式估)。请在回复里自然点明:按这预算正常排期走不下来,"
            "建议把预算至少加到 {} 元以上再生成;若预算实在有限,可以让他说「就按最省的吧」,"
            "你会按最省方式压缩排期。一两句带过即可,别列清单。".format(
                round(block["budget_total"]), min_budget, min_budget
            )
        )
    need = base.param_status_text(params)
    if ctx:
        sys = role + (
            "下面是该目的地指南片段,可作推荐依据,只挑相关的说,别逐条罗列,别谎称来源。"
        ) + need + f"\n〔参考指南〕\n{ctx}"
    else:
        sys = role + "没有可用指南,凭常识作答,别谎称来源。" + need
    history = [SystemMessage(content=sys)] + base.history_messages(state)

    try:
        resp = llm.invoke(history)
        reply = str(getattr(resp, "content", "")).strip()
    except Exception as exc:
        reply = "回复生成超时/失败,请换个更短的说法再试。" if "Timeout" in type(exc).__name__ else \
            f"回复生成失败:{type(exc).__name__}:{exc}"
        return {"reply": reply, "status": "failed", "ready": ready, "agent_trace": trace}

    messages = base.with_reply(state, reply)
    if block:
        # 信息其实齐了,但预算过低:确认按钮按灰(ready=false),回复里已提示加预算/接受压缩
        return {
            "reply": reply,
            "status": "budget_low",
            "ready": False,
            "messages": messages,
            "params": params,
            "low_budget": True,
            "min_budget": min_budget,
            "agent_trace": trace,
        }
    return {
        "reply": reply,
        "status": status,
        "ready": ready,
        "messages": messages,
        "agent_trace": trace,
    }
