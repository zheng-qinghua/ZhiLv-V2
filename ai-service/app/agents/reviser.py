"""修订专家:在已有行程上再改一版。两种触发走的是**同一个模型调用**。

  1. **critic 挑出毛病**(Step 7,自动):把 issues 灌进 feedback,让模型按质检意见重排。
  2. **用户主动要求改**(Step 8,手动):把「当前行程 + 用户那句话」灌进 feedback,
     让模型只动用户点到的地方,其余保持原样。

两者都用 `llm.generate_trip_plan` + `planner.build_request`,区别只在 feedback 的正文,
所以字段口径、默认值、缓存口径天然和首轮生成一致 —— 不另写一套 prompt。

**为什么两种走同一个节点而不是各写一个**:supervisor 判 `revise` 时图是从 supervisor
直接进 reviser 的,critic 那一跳会被跳过;而 critic 触发时是从 critic 进来的。
节点靠 `intent` 区分自己是被谁叫来的(见 `_feedback_for`)。

本节点还负责"说改行程但手上没有行程"的守卫(回「我得先有一份行程才能改」)——
放在这里而不是 supervisor,因为 supervisor 是路由、不产出话术。

**为什么必须从 params 重建请求,而不是改手里这份 plan**:hotel_level 和
dietary_preferences 不在 TripPlan 契约里(见 app/models/trip_plan.py),从 plan 反推会丢,
而这两项正好是 critic 要审的东西 —— 丢了就永远修不好。

修订失败不算致命:保留原 plan、照常把行程返回给用户,只是这版没改成。
宁可给一份"有毛病但能用"的行程,也不要让用户拿到空白页。
"""
from __future__ import annotations

import json

from app.agents import base
from app.agents.planner import _gen_rag_context, build_request
from app.graph.state import ChatState
from app.llm import generate_trip_plan

MAX_REVISION_ROUNDS = 1  # 只修一轮:模型改不动的毛病,再喂一遍也是改不动,只是多烧一次时间

# 用户改行程时喂给模型的当前行程,太长会挤掉别的上下文;实在放不下就只给摘要
_PLAN_INLINE_LIMIT = 12000


def _issues_feedback(issues: list[str]) -> str:
    return "质检发现这份行程有这些问题,请逐条改正后重新输出完整行程:\n" + \
        "\n".join(f"- {i}" for i in issues)


def _user_feedback(plan: dict, instruction: str) -> str:
    """用户主动改:把当前行程原样给它,要求只动用户点到的地方。

    不给当前行程的话,模型会推倒重来 —— 用户说"第 2 天换室内的",结果 5 天全变样,
    他前面认可的安排全没了。放不下就退化成只用文字描述,总比不给强。
    """
    try:
        inline = json.dumps(plan, ensure_ascii=False)
    except Exception:
        inline = ""
    head = ("这是当前已经生成好的行程。请**在它的基础上做最小改动**,"
            "没被要求改的部分(日期、天数、预算口径、其他天的安排)一律保持原样。\n")
    if inline and len(inline) <= _PLAN_INLINE_LIMIT:
        body = f"当前行程(JSON):\n{inline}\n\n"
    else:
        body = (f"当前行程:去{plan.get('destination') or '目的地'},"
                f"共 {plan.get('day_count') or len(plan.get('days') or [])} 天,"
                f"标题「{plan.get('title') or ''}」。\n\n")
    return head + body + f"用户这次的要求:{instruction}"


def should_revise(state: ChatState) -> str:
    """critic 之后走哪:过关/已修满/压根没行程 → 收尾;还有问题 → 去 reviser。"""
    critique = state.get("critique") or {}
    if critique.get("pass", True):
        return "done"
    if int(state.get("revision_round") or 0) >= MAX_REVISION_ROUNDS:
        return "done"
    return "revise"


def _feedback_for(state: ChatState) -> tuple[str, str] | None:
    """按"谁把我叫来的"决定 feedback 正文和回复话术;无从下手时返回 None。

    intent == "revise" 说明是 supervisor 判出来的用户主动改;否则是 critic 下游那一条。
    """
    plan = state.get("plan") or {}
    if str(state.get("intent") or "") == "revise":
        instruction = str(state.get("new_message") or "").strip()
        if not instruction:
            return None
        return _user_feedback(plan, instruction), "行程已按你的要求改好,正在为你打开。"
    issues = list((state.get("critique") or {}).get("issues") or [])
    if not issues:
        return None
    return _issues_feedback(issues), "行程已生成,我按质检意见调整了一版,正在为你打开。"


def reviser_node(state: ChatState) -> dict:
    trace = base.trace(state, "reviser")
    params = state.get("params") or {}
    user_asked = str(state.get("intent") or "") == "revise"
    round_ = int(state.get("revision_round") or 0)

    # 轮次上限只约束 critic 那圈自动重排;用户主动要求改是他自己的决定,不该被计数挡住
    if not user_asked and round_ >= MAX_REVISION_ROUNDS:
        return {"agent_trace": trace}

    if user_asked and not (state.get("plan") or {}).get("days"):
        # 说要改行程但手上还没有行程。守卫放这里而不是 supervisor:supervisor 只会把它
        # 降级成 chitchat,而 chitchat 会顺着用户的话答("好的,第2天全安排室内"),
        # 像是答应了改一份不存在的行程 —— 实测踩到过。
        reply = ("我得先有一份行程才能改。你先告诉我「从哪出发、去哪里、什么时候去、玩几天」,"
                 "我生成一版出来,你再告诉我要改哪儿。")
        return {"reply": reply, "status": "collecting", "ready": False,
                "messages": base.with_reply(state, reply), "agent_trace": trace}

    picked = _feedback_for(state)
    if picked is None:
        # 条件边应该已经挡过,这里是异常路径的兜底:不要让节点白调一次 LLM
        return {"agent_trace": trace}
    feedback, reply = picked

    try:
        req = build_request(params)
        plan = generate_trip_plan(req, rag_context=_gen_rag_context(req.destination),
                                  feedback=feedback)
    except Exception as exc:
        # 改失败了但手上那版行程还在:状态仍算可用,别让前端把用户的行程页关掉
        return {"revision_round": round_ + 1, "status": "generated", "ready": True,
                "reply": (f"这次改动没做成(原因:{type(exc).__name__}),"
                          f"当前这版行程仍可直接使用,过会儿再让我改一次?"),
                "messages": base.with_reply(state,
                    f"这次改动没做成(原因:{type(exc).__name__}),当前这版行程仍可直接使用。"),
                "agent_trace": trace}

    return {
        "plan": plan.model_dump(),
        # status/ready 必须自己给:critic 那条路上游的 planner 已经写过 generated,
        # 但用户主动改这条是从 supervisor 直接进 reviser 的,没人写 —— 不给就会一路
        # 兜底成 collecting,前端不打开行程页(实测踩到过)。
        "status": "generated",
        "ready": True,
        "revision_round": round_ + 1,
        "reply": reply,
        "messages": base.with_reply(state, reply),
        "agent_trace": trace,
    }
