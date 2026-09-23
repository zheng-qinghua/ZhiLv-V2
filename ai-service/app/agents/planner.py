"""行程规划专家:把已确定的参数变成一份完整 TripPlan。

和别的专家不一样 —— 它不聊天、不见模型的脸:输入是结构化参数,输出是结构化 TripPlan,
中间那次 LLM 调用在哪都在 `llm.generate_trip_plan` 里,这里只负责"能不能生成"和"生成结果往哪放"。

两处入口共用同一个节点:
  1. 对话里说「帮我生成行程」→ supervisor 判 plan → 走图到 planner_node;
  2. 前端点「确认行程」按钮 → chat.handle_turn 直接调 planner_node(没有新消息可给
     supervisor 分类,绕开它比让它在空消息上瞎猜更稳)。
两条路的门槛、话术、返回字段因此天然一致。

生成结果写进 state["plan"],这是 Step 7/8 的前提:行程第一次进入会话状态,
critic 才有东西可审、reviser 才有东西可改。

按 CLAUDE.md,默认值规则(人数 3、节奏适中、住宿舒适型、预算兜底)与生成逻辑一起
从 chat.py 搬过来 —— 那时它叫 _generate_from_params,是 chat 的私有实现;
现在 planner 是它的第二个消费者,按本项目"第二个消费者出现才上移"的惯例提到 agents/。
"""
from __future__ import annotations

from datetime import date, timedelta

from app.agents import base
from app.agents.budget import block_state
from app.graph.params import is_ready, missing_params, to_date, to_float, to_int
from app.graph.state import ChatState
from app.llm import generate_trip_plan
from app.models import TripRequest
from app.rag.retrieve import format_for_prompt, format_guide_by_city, retrieve
from app.tools.weather_tool import fetch_forecast, format_forecast

# 高德 weatherInfo?extensions=all 只回 4 天(今天 + 未来 3 天)。行程起始日超出这个窗口时,
# 预报一天都盖不到行程上,硬塞进去只会让模型拿"这周的雨"去安排"下个月的行程"。
_WEATHER_HORIZON_DAYS = 3


def _gen_rag_context(dest: str) -> str:
    """生成注入:优先整篇城市指南,取不到退回语义召回,再不行空串(不带知识库也能生成)。"""
    try:
        guide = format_guide_by_city(dest)
        if guide:
            return guide
        return format_for_prompt(retrieve(f"{dest} 旅游攻略"))
    except Exception:
        return ""


def _gen_weather_note(req: TripRequest) -> str:
    """行程起始日在预报窗口内才给预报;否则空串(那份预报管不到那几天)。

    这里是**确定性调用**,不走模型、不依赖 state["weather"](那个字段一直留空),
    取不到就返回空串 —— 没有天气照样能生成行程。
    """
    start = to_date(req.start_date)
    if start is None:
        return ""
    ahead = (start - date.today()).days
    if not (0 <= ahead <= _WEATHER_HORIZON_DAYS):
        return ""
    try:
        return format_forecast(fetch_forecast(req.destination) or {}, limit=6)
    except Exception:
        return ""


def generate_plan(req: TripRequest, feedback: str | None = None):
    """带上下文(攻略 + 天气)生成一份行程。planner 和 reviser 共用这一个入口,
    免得两边各拼一遍 context —— 拼漏了就会"初版看天气、改版不看",很难查。"""
    return generate_trip_plan(
        req,
        rag_context=_gen_rag_context(req.destination),
        weather_note=_gen_weather_note(req),
        feedback=feedback,
    )


def build_request(p: dict) -> TripRequest:
    """把已确定参数解析成 TripRequest;缺关键项抛 RuntimeError。

    默认值规则(CLAUDE.md/M4):人数 3、节奏适中、住宿舒适型、偏好/备注留空;
    预算用户给过就用他的(人均→×人数换算总额),没给才按 200×人数×天数估算;
    只说"N天"没给具体起止日 → 出发日取今天。

    公开出来是因为 reviser 也要用:重排必须拿**同一份**请求(尤其 hotel_level 和
    dietary_preferences —— 它们不在 TripPlan 里,从 plan 反推会丢,而丢的正好是
    critic 要审的那几项)。
    """
    dep = str(p.get("departure") or "").strip()
    if not dep:
        raise RuntimeError("出发地还没确定,先在对话里告诉我从哪个城市出发")
    dest = str(p.get("destination") or "").strip()
    if not dest:
        raise RuntimeError("目的地还没确定,先在对话里告诉我去哪")

    start = to_date(p.get("start_date"))
    end = to_date(p.get("end_date"))
    total_days = to_int(p.get("total_days"), 0)
    if start and end and end >= start:
        start_d, end_d = start, end
    elif start:
        # 常见说法是「10月1号出发,玩5天」——只有出发日、天数在 total_days 里。
        # 这一支必须排在 total_days 前面,否则用户给的出发日会被换成今天(实测踩到过:
        # 10月1号的行程排成了今天出发,顺带让天气注入的日期判断全部落在"今天")。
        start_d = start
        end_d = start + timedelta(days=total_days - 1) if total_days >= 1 else start
    elif total_days >= 1:
        start_d, end_d = date.today(), date.today() + timedelta(days=total_days - 1)
    else:
        raise RuntimeError("出行时间还没确定,告诉我具体日期或打算玩几天")

    day_count = (end_d - start_d).days + 1
    travelers = max(1, to_int(p.get("travelers"), 3))

    budget_total = None
    raw_budget = to_float(p.get("budget"))
    if raw_budget is not None:
        budget_total = raw_budget * travelers if str(p.get("budget_unit") or "").strip() == "per_person" else raw_budget
    if budget_total is None or budget_total <= 0:
        # 没给预算时的粗略帽:每人每天 200 当地花费 + 800 往返大交通兜底(不判距离)
        budget_total = float((200 * day_count + 800) * travelers)

    return TripRequest(
        departure=dep,
        destination=dest,
        start_date=start_d.isoformat(),
        end_date=end_d.isoformat(),
        travelers=travelers,
        budget=round(budget_total, 2),
        preferences=[str(x).strip() for x in (p.get("preferences") or []) if str(x).strip()],
        pace=str(p.get("pace") or "").strip() or "适中",
        hotel_level=str(p.get("hotel_level") or "").strip() or "舒适型",
        dietary_preferences=[str(x).strip() for x in (p.get("dietary_preferences") or []) if str(x).strip()] or None,
        special_notes=str(p.get("special_notes") or "").strip() or None,
    )


def _generate_from_params(p: dict):
    """解析参数并生成 TripPlan(planner 节点用)。"""
    return generate_plan(build_request(p))


def _collecting_reply(params: dict) -> str:
    missing = missing_params(params)
    return ("还缺关键信息:请先告诉我「从哪个城市出发 + 去哪里 + 什么时候去"
            "(具体日期或打算玩几天)」,这样我才能生成完整行程。"
            f"{('还差:' + '、'.join(missing) + '。') if missing else ''}")


def planner_node(state: ChatState) -> dict:
    trace = base.trace(state, "planner")
    params = state.get("params") or {}

    # 三条"没生成"的出口都要把 plan 显式清空:否则上一轮的旧行程会留给 critic 去审
    # (用户这轮只是补参数,却可能触发一次莫名其妙的"重排")。旧行程在 Redis 里仍在,
    # chat 写回时用的是 out["plan"] or state["plan"],不会丢。
    if not is_ready(params):
        reply = _collecting_reply(params)
        return {"reply": reply, "status": "collecting", "ready": False,
                "messages": base.with_reply(state, reply), "plan": None, "agent_trace": trace}

    # 预算过低且没接受"按最省":连"帮我生成行程"也按住,把提醒写回对话(下次生成时模型知道劝过)
    st = block_state(params, str(state.get("insisted_sig") or ""))
    if st:
        reply = (
            f"你的预算(约 {st['budget_total']} 元)低于这趟路线的预估最低花费(约 {st['min_total']} 元,"
            f"含往返大交通、按最省方式估),按这预算生成会把排期压到没法玩。"
            f"建议把预算加到 {st['min_budget']} 元以上再确认;实在只有这些,"
            f"回复我「就按最省的吧」,我会按最省方式压缩排期。"
        )
        return {"reply": reply, "status": st["status"], "ready": st["ready"],
                "messages": base.with_reply(state, reply), "params": params, "plan": None,
                "low_budget": True, "min_budget": st["min_budget"], "agent_trace": trace}

    try:
        plan = _generate_from_params(params)
    except RuntimeError as exc:
        return {"reply": f"行程生成失败:{exc}", "status": "generation_failed",
                "ready": True, "params": params, "plan": None, "agent_trace": trace}
    except Exception as exc:  # LLM 超时/输出解析失败等:降级成一句可读回复,不让对话 500
        return {"reply": f"行程生成失败:{type(exc).__name__}。稍后再让我试一次?",
                "status": "generation_failed", "ready": True, "params": params,
                "plan": None, "agent_trace": trace}

    reply = "行程已按对话整理生成,正在为你打开。"
    return {"reply": reply, "status": "generated", "ready": True,
            "messages": base.with_reply(state, reply), "params": params,
            "plan": plan.model_dump(), "agent_trace": trace}
