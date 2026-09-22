"""对话式规划(M3):LangGraph 状态图 + Redis 原生 JSON 持久化 + 简单 RAG。

每轮(thread 粒度,backend 用会话 id 当 thread):
  抽取参数(DeepSeek,只认用户明说过的)→ 按"目的地/时间是否齐"和 RAG 参考生成中文回复。
图本身不挂 checkpointer:状态由 handle_turn 从 Redis 载入、跑完再写回(native JSON,
Windows Redis 无 RediSearch,不用 langgraph-checkpoint-redis)。
降级:Redis 挂了退进程内内存态;RAG(Milvus/嵌入)挂了退纯对话,均不让对话断掉。
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import redis as redis_lib
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.agents.budget import low_block
from app.agents.supervisor import supervisor_node
from app.config import REDIS_HOST, REDIS_PORT
from app.graph.params import (
    PARAM_FIELDS,
    is_ready,
    missing_params,
    to_date,
    to_float,
    to_int,
)
from app.graph.state import ChatState
from app.llm import build_chat_llm, generate_trip_plan
from app.models import TripRequest
from app.rag.retrieve import format_for_prompt, format_guide_by_city, retrieve

_REDIS_PREFIX = "zhilv:chat:"
_MEM: dict[str, dict] = {}  # Redis 不可用时的进程内兜底


# ---------------- Redis 状态存取 ----------------


def _load_state(thread_id: str) -> dict:
    r = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True,
                        socket_connect_timeout=2)
    try:
        raw = r.get(_REDIS_PREFIX + thread_id)
        if raw:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
    except Exception:
        return _MEM.get(thread_id) or {"messages": [], "params": {}}
    return _MEM.get(thread_id) or {"messages": [], "params": {}}


def _save_state(thread_id: str, state: dict) -> None:
    try:
        r = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True,
                            socket_connect_timeout=2)
        r.set(_REDIS_PREFIX + thread_id, json.dumps(state, ensure_ascii=False))
        return
    except Exception:
        pass
    _MEM[thread_id] = state


# ---------------- LangGraph 节点 ----------------
# 参数抽取(= supervisor 的一半职责)已迁到 app/agents/supervisor.py。


def _respond_node(state: ChatState) -> dict:
    llm = build_chat_llm()
    params = state.get("params") or {}
    ready = is_ready(params)
    if llm is None:
        return {"reply": "当前未配置 LLM_API_KEY,无法回答。请在 ai-service/.env 填好密钥后再试。",
                "status": "failed", "ready": ready}

    dest = params.get("destination")
    ctx = ""
    if dest:
        try:
            ctx = format_for_prompt(retrieve(state.get("new_message") or f"{dest} 旅游攻略"))
        except Exception:
            ctx = ""

    missing = missing_params(params)

    # 预算不足拦截:信息齐且给过预算时,按路线最低花费判断要不要提醒并按住确认
    block = low_block(params, str(state.get("insisted_sig") or "")) if ready else None
    low_budget = bool(block)
    min_budget = round(block["min_total"]) if block else None

    param_line = "、".join(f"{k}={params[k]}" for k in PARAM_FIELDS if params.get(k) is not None) or "尚无"
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
    need = f"\n\n已确定:{param_line}\n未确定:{'、'.join(missing) if missing else '无'}"
    if ctx:
        sys = role + (
            "下面是该目的地指南片段,可作推荐依据,只挑相关的说,别逐条罗列,别谎称来源。"
        ) + need + f"\n〔参考指南〕\n{ctx}"
    else:
        sys = role + "没有可用指南,凭常识作答,别谎称来源。" + need
    history = [SystemMessage(content=sys)]
    for m in (state["messages"])[-20:]:  # 只喂最近 20 条,防对话过长
        c = m.get("content", "")
        if m.get("role") == "user":
            history.append(HumanMessage(content=c))
        else:
            history.append(AIMessage(content=c))
    try:
        resp = llm.invoke(history)
        reply = str(getattr(resp, "content", "")).strip()
    except Exception as exc:
        status = "failed"
        reply = "回复生成超时/失败,请换个更短的说法再试。" if "Timeout" in type(exc).__name__ else \
            f"回复生成失败:{type(exc).__name__}:{exc}"
        return {"reply": reply, "status": status, "ready": ready}

    messages = list(state["messages"])
    messages.append({"role": "assistant", "content": reply})
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
        }
    return {
        "reply": reply,
        "status": "await_confirm" if ready else "collecting",
        "ready": ready,
        "messages": messages,
    }


def _build_graph():
    # Step 2a:只把参数抽取换成 supervisor(合并了意图路由),图结构与路由都不变 ——
    # 先单独验证分类准不准,确认没有回归后再由 graph/builder.py 接管路由(Step 2b)。
    g = StateGraph(ChatState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("respond", _respond_node)
    g.add_edge(START, "supervisor")
    g.add_edge("supervisor", "respond")
    g.add_edge("respond", END)
    return g.compile()


_GRAPH = _build_graph()


# ---------------- M4:确认生成 ----------------
# 默认值规则(M4):人数 3、节奏适中、住宿舒适型、偏好/备注留空;
# 预算用户给过就用他的(人均→×人数换算总额),没给才按 200×人数×天数估算;
# 只说"N天"没给具体起止日 → 出发日取今天。


def _gen_rag_context(dest: str) -> str:
    """生成注入:优先整篇城市指南,取不到退回语义召回,再不行空串(不带知识库也能生成)。"""
    try:
        guide = format_guide_by_city(dest)
        if guide:
            return guide
        return format_for_prompt(retrieve(f"{dest} 旅游攻略"))
    except Exception:
        return ""


def _generate_from_params(p: dict):
    """把确认时的已确定参数解析成 TripRequest 并生成 TripPlan;缺关键项抛 RuntimeError。"""
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

    req = TripRequest(
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
    return generate_trip_plan(req, rag_context=_gen_rag_context(dest))


# ---------------- 对外入口 ----------------


def handle_turn(thread_id: str, message: str = "", action: str = "chat") -> dict:
    state = _load_state(thread_id)
    state.setdefault("messages", [])
    state.setdefault("params", {})

    confirm = bool(action and action.strip().lower() == "confirm")
    text = (message or "").strip()
    if confirm or not text:
        ready = is_ready(state["params"])
        if not ready:
            missing = missing_params(state["params"])
            return {
                "reply": "还缺关键信息:请先告诉我「从哪个城市出发 + 去哪里 + 什么时候去"
                        "(具体日期或打算玩几天)」,这样我才能生成完整行程。"
                        f"{('还差:' + '、'.join(missing) + '。') if missing else ''}",
                "status": "collecting",
                "ready": False,
                "params": state["params"] or None,
                "intent": "plan",
            }
        # 预算过低且没接受"按最省":确认也拦下,把提醒写回对话(下次生成时模型知道劝过)
        block = low_block(state["params"], str(state.get("insisted_sig") or ""))
        if block:
            mb = round(block["min_total"])
            bt = round(block["budget_total"])
            reply = (
                f"你的预算(约 {bt} 元)低于这趟路线的预估最低花费(约 {mb} 元,含往返大交通、"
                f"按最省方式估),按这预算生成会把排期压到没法玩。建议把预算加到 {mb} 元以上再确认;"
                f"实在只有这些,回复我「就按最省的吧」,我会按最省方式压缩排期。"
            )
            msgs = list(state["messages"]) + [{"role": "assistant", "content": reply}]
            _save_state(thread_id, {"messages": msgs, "params": state["params"],
                                    "insisted_sig": state.get("insisted_sig") or ""})
            return {
                "reply": reply,
                "status": "budget_low",
                "ready": False,
                "params": state["params"] or None,
                "low_budget": True,
                "min_budget": mb,
                "intent": "plan",
            }
        try:
            plan = _generate_from_params(state["params"])
        except RuntimeError as exc:
            return {
                "reply": f"行程生成失败:{exc}",
                "status": "generation_failed",
                "ready": True,
                "params": state["params"] or None,
                "intent": "plan",
            }
        return {
            "reply": "行程已按对话整理生成,正在为你打开。",
            "status": "generated",
            "ready": True,
            "params": state["params"] or None,
            "plan": plan.model_dump(),
            "intent": "plan",
        }

    state["messages"] = list(state["messages"])
    state["messages"].append({"role": "user", "content": text})
    state["new_message"] = text
    out = _GRAPH.invoke(state)

    final_messages = out.get("messages") or state["messages"]
    final_params = out.get("params") or state["params"] or {}
    _save_state(thread_id, {"messages": final_messages, "params": final_params,
                            "insisted_sig": out.get("insisted_sig") or (state.get("insisted_sig") or "")})

    reply = out.get("reply") or "我没听清,换个说法再问我一次吧。"
    result = {
        "reply": reply,
        "status": out.get("status", "collecting"),
        "ready": out.get("ready", False),
        "params": final_params or None,
        # 本轮 supervisor 判出的意图。Step 2 阶段只观察不路由;Java 侧按名取字段,多余字段无影响
        "intent": out.get("intent"),
    }
    if out.get("low_budget"):
        result["low_budget"] = True
        result["min_budget"] = out.get("min_budget")
    return result
