"""修订专家:把 critic 挑出来的问题灌回模型,让它重排一版。

和 planner 共用同一条生成链路(`llm.generate_trip_plan`)+ 同一份请求构建
(`planner.build_request`),区别只有一个:多传一个 `feedback`,内容是 critic 的 issues。
`generate_trip_plan` 里本来就有"上次未通过校验"的 prompt 段落(原本用于解析失败重试),
直接复用它,不另写一套 prompt —— 不重复造轮子,也保证修订版的字段口径和初版完全一致。

**为什么必须从 params 重建请求,而不是改手里这份 plan**:hotel_level 和
dietary_preferences 不在 TripPlan 契约里(见 app/models/trip_plan.py),从 plan 反推会丢,
而这两项正好是 critic 要审的东西 —— 丢了就永远修不好。

修订失败不算致命:保留原 plan、照常把行程返回给用户,只是这版没修。
宁可给一份"有毛病但能用"的行程,也不要让用户拿到空白页。
"""
from __future__ import annotations

from app.agents import base
from app.agents.planner import _gen_rag_context, build_request
from app.graph.state import ChatState
from app.llm import generate_trip_plan

MAX_REVISION_ROUNDS = 1  # 只修一轮:模型改不动的毛病,再喂一遍也是改不动,只是多烧一次时间


def _feedback_text(issues: list[str]) -> str:
    return "质检发现这份行程有这些问题,请逐条改正后重新输出完整行程:\n" + \
        "\n".join(f"- {i}" for i in issues)


def should_revise(state: ChatState) -> str:
    """critic 之后走哪:过关/已修满/压根没行程 → 收尾;还有问题 → 去 reviser。"""
    critique = state.get("critique") or {}
    if critique.get("pass", True):
        return "done"
    if int(state.get("revision_round") or 0) >= MAX_REVISION_ROUNDS:
        return "done"
    return "revise"


def reviser_node(state: ChatState) -> dict:
    trace = base.trace(state, "reviser")
    issues = list((state.get("critique") or {}).get("issues") or [])
    params = state.get("params") or {}
    round_ = int(state.get("revision_round") or 0)

    if not issues or round_ >= MAX_REVISION_ROUNDS:
        # 条件边已经挡过,这里只是不让节点在异常路径下做无谓的 LLM 调用
        return {"agent_trace": trace}

    try:
        req = build_request(params)
        plan = generate_trip_plan(req, rag_context=_gen_rag_context(req.destination),
                                  feedback=_feedback_text(issues))
    except Exception as exc:
        # 修订失败:原 plan 原样留着,记一轮计数避免卡住,回复降级成"原版可用"
        return {"revision_round": round_ + 1,
                "reply": f"行程已生成,但自动调整没过(原因:{type(exc).__name__}),"
                         f"当前这版仍可直接使用。",
                "agent_trace": trace}

    return {
        "plan": plan.model_dump(),
        "revision_round": round_ + 1,
        "reply": "行程已生成,我按质检意见调整了一版,正在为你打开。",
        "agent_trace": trace,
    }
