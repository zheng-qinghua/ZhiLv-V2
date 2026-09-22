"""对话式规划(M3):LangGraph 状态图 + Redis 原生 JSON 持久化 + 简单 RAG。

每轮(thread 粒度,backend 用会话 id 当 thread):
  抽取参数(DeepSeek,只认用户明说过的)→ 按"目的地/时间是否齐"和 RAG 参考生成中文回复。
图本身不挂 checkpointer:状态由 handle_turn 从 Redis 载入、跑完再写回(native JSON,
Windows Redis 无 RediSearch,不用 langgraph-checkpoint-redis)。
降级:Redis 挂了退进程内内存态;RAG(Milvus/嵌入)挂了退纯对话,均不让对话断掉。
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta

import redis as redis_lib
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.config import REDIS_HOST, REDIS_PORT
from app.graph.params import (
    PARAM_FIELDS,
    budget_total_of,
    is_ready,
    missing_params,
    resolved_days,
    resolved_travelers,
    route_sig,
    to_date,
    to_float,
    to_int,
)
from app.graph.state import ChatState
from app.llm import _extract_json_object, build_chat_llm, generate_trip_plan
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


def _extract_node(state: ChatState) -> dict:
    params = dict(state.get("params") or {})
    llm = build_chat_llm()
    if llm is None:
        return {"params": params}
    convo = "\n".join(
        f"{'用户' if m.get('role') == 'user' else '助手'}: {m.get('content', '')}"
        for m in state["messages"]
    )
    sys = (
        "你是行程参数抽取器。读完整段对话,只挑【用户明确说过】的字段输出 JSON,"
        "不要猜测、不要补默认值、不要解析尚未说清的信息。"
    )
    human = f"""当前已确定参数:{json.dumps(params, ensure_ascii=False)}
对话全文:
{convo}

只输出一个 JSON 对象,字段取值下面这套(未提到/不确定/无变化的都填 null,绝不编造):
- departure: 出发城市名(如 "北京");用户说"从X出发/从X去/家住X"才算,否则 null
- destination: 目的地城市名(如 "大理")
- start_date / end_date: "YYYY-MM-DD",仅用户给出具体日期才填
- total_days: 整数,仅用户说"玩N天/N日"才填;已给具体起止日期就别填
- travelers: 出行人数整数
- budget: 金额数字——用户是总额口径就写总额;明确是"人均/每人"就写那个单价
- budget_unit: "total" 或 "per_person"(与 budget 对应;没说金额则 null)
- preferences: 字符串数组(如 ["慢节奏"]);无则 null
- pace: 节奏(轻松/适中/紧凑)
- hotel_level: 住宿档次(经济型/舒适型/高档型)
- dietary_preferences: 饮食偏好数组(如 ["少辣"]);无则 null
- special_notes: 其它特殊要求(如 "想看日出")字符串
- insist_low_budget: 布尔。当且仅当用户本轮明确接受"预算不够也按最省/尽量压缩排期"继续(如"就按最省的安排吧""预算就这么点你看着办""越省越好"),才填 true;只是陈述自己预算低、或没表态,填 false

注意:金额没说单位一律按总额 total;日期只认用户原话,别拿今天当默认;地点变了但用户没重说时间/人数等,就保留上文已确定的。直接给 JSON,不要 markdown,不要解释。"""
    try:
        resp = llm.invoke([("system", sys), ("human", human)])
        frag = _extract_json_object(str(getattr(resp, "content", "")))
        if frag:
            obj = json.loads(frag)
            for k in PARAM_FIELDS:
                v = obj.get(k)
                if v is None:
                    continue
                if isinstance(v, (list, tuple)):
                    v = [str(x).strip() for x in v if str(x).strip()]
                    if not v:
                        continue
                elif isinstance(v, str):
                    v = v.strip()
                    if not v:
                        continue
                params[k] = v
            # 用户接受"预算低也按最省"→ 记住当前路由签名,同路由不再拦截(路由变了要重新拦)
            insist = obj.get("insist_low_budget")
            if insist is True or str(insist).strip().lower() in ("true", "yes", "1", "是", "对"):
                dep = str(params.get("departure") or "").strip()
                dest = str(params.get("destination") or "").strip()
                dc = resolved_days(params)
                if dep and dest and dc:
                    return {"params": params,
                            "insisted_sig": route_sig(dep, dest, dc, resolved_travelers(params))}
    except Exception:
        pass  # 抽取失败不打断对话:沿用旧参数继续
    return {"params": params}


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
    block = _low_block(params, str(state.get("insisted_sig") or "")) if ready else None
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
    g = StateGraph(ChatState)
    g.add_node("extract", _extract_node)
    g.add_node("respond", _respond_node)
    g.add_edge(START, "extract")
    g.add_edge("extract", "respond")
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


# ---------------- 预算不足检测(只拦对话式) ----------------


_MIN_TTL_SECONDS = 6 * 3600  # 最低花费按路线缓存 6h,跨会话复用
_MIN_CACHE: dict[str, tuple[float, float]] = {}  # sig -> (存入时间, 最低总花费)


def _estimate_min_total(dep: str, dest: str, day_count: int, travelers: int) -> float | None:
    """DeepSeek 估"最省也现实可行"的总花费(含往返大交通);失败返回 None = 不拦截。"""
    sig = route_sig(dep, dest, day_count, travelers)
    item = _MIN_CACHE.get(sig)
    if item and time.time() - item[0] < _MIN_TTL_SECONDS:
        return item[1]
    llm = build_chat_llm()
    if llm is None:
        return None
    prompt = (
        f"请估算:从{dep}出发到{dest}旅行 {day_count} 天、共 {travelers} 人,"
        f"按最省但现实可行(往返选最便宜的长途交通,住宿经济型/合住,吃饭从简,"
        f"市内公共交通,只去标志性景点)安排,全程含往返大交通的总花费大约最低要多少元。"
        f"只输出一个 JSON 对象:{chr(123)}min_total:整数{chr(125)}。"
    )
    try:
        resp = llm.invoke([("system", "你是旅行成本估算器,只回答数字,不解释。"), ("human", prompt)])
        frag = _extract_json_object(str(getattr(resp, "content", "")))
        if frag:
            v = float(json.loads(frag).get("min_total"))
            if 0 < v < 10_000_000:
                _MIN_CACHE[sig] = (time.time(), v)
                return v
    except Exception:
        pass  # 估算失败不缓存、不拦截,避免打断对话
    return None


def _low_block(params: dict, insisted_sig: str = "") -> dict | None:
    """预算远低于路线最低花费且用户尚未接受压缩时,返回 {budget_total, min_total, sig};否则 None。"""
    dep = str(params.get("departure") or "").strip()
    dest = str(params.get("destination") or "").strip()
    day_count = resolved_days(params)
    if not dep or not dest or not day_count:
        return None
    travelers = resolved_travelers(params)
    budget_total = budget_total_of(params)
    if budget_total is None:
        return None
    min_total = _estimate_min_total(dep, dest, day_count, travelers)
    if min_total is None or budget_total >= min_total:
        return None
    sig = route_sig(dep, dest, day_count, travelers)
    if insisted_sig == sig:
        return None
    return {"budget_total": budget_total, "min_total": min_total, "sig": sig}


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
            }
        # 预算过低且没接受"按最省":确认也拦下,把提醒写回对话(下次生成时模型知道劝过)
        block = _low_block(state["params"], str(state.get("insisted_sig") or ""))
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
            }
        try:
            plan = _generate_from_params(state["params"])
        except RuntimeError as exc:
            return {
                "reply": f"行程生成失败:{exc}",
                "status": "generation_failed",
                "ready": True,
                "params": state["params"] or None,
            }
        return {
            "reply": "行程已按对话整理生成,正在为你打开。",
            "status": "generated",
            "ready": True,
            "params": state["params"] or None,
            "plan": plan.model_dump(),
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
    }
    if out.get("low_budget"):
        result["low_budget"] = True
        result["min_budget"] = out.get("min_budget")
    return result
