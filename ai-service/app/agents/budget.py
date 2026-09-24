"""预算专家:估"这条路线最省也现实可行要多少钱",并据此做预算护栏。

被三处使用:
  1. supervisor 路由到 budget 时,budget_node 回答"我这预算够吗";
  2. 信息齐但预算过低时,把「确认」按住(状态 budget_low)—— 由 block_state() 统一口径;
  3. 确认生成前的最后一道护栏(chat.py confirm 分支),和 2 用同一个 low_block。

提成独立模块是为了断开循环依赖:chitchat 节点要用预算护栏,
而 chitchat 由图引用,不能再反过来 import 入口 chat.py。
"""
from __future__ import annotations

import json
import time

from langchain_core.messages import SystemMessage

from app.agents import base
from app.graph.params import budget_total_of, resolved_days, resolved_travelers, route_sig
from app.graph.state import ChatState
from app.llm import _extract_json_object, build_chat_llm
from app.redis_client import get_client

_MIN_TTL_SECONDS = 6 * 3600  # 最低花费按路线缓存 6h,跨会话复用
_MIN_REDIS_PREFIX = "zhilv:mincost:"
_MIN_CACHE: dict[str, tuple[float, float]] = {}  # sig -> (存入时间, 最低总花费)


def _cached_min_total(sig: str) -> float | None:
    """取缓存:先进程内(免费),再 Redis(跨重启/多进程),都没有返回 None。

    为什么要落 Redis:这条估算冷启动要 26~48s(模型先吐一大段看不见的推理)。
    只缓在进程内的话,每次重启/发版,凡是用户新问到的路线都要再等一次 ——
    估算结果只取决于路线,是完全可以跨进程复用的。
    """
    item = _MIN_CACHE.get(sig)
    if item and time.time() - item[0] < _MIN_TTL_SECONDS:
        return item[1]
    try:
        raw = get_client().get(_MIN_REDIS_PREFIX + sig)
        data = json.loads(raw) if raw else None
    except Exception:
        return None  # Redis 挂了只损失"跨重启复用",本次问答照常
    if not isinstance(data, dict):
        return None
    try:
        saved, v = float(data["t"]), float(data["v"])
    except (KeyError, TypeError, ValueError):
        return None
    if 0 < v < 10_000_000 and time.time() - saved < _MIN_TTL_SECONDS:
        _MIN_CACHE[sig] = (saved, v)  # 回填进程内,同进程后续不再走 Redis
        return v
    return None


def _store_min_total(sig: str, v: float) -> None:
    now = time.time()
    _MIN_CACHE[sig] = (now, v)
    try:
        # TTL 交给 Redis;同时存写入时间,回填进程内后两边的过期口径才一致
        get_client().setex(_MIN_REDIS_PREFIX + sig, _MIN_TTL_SECONDS,
                           json.dumps({"t": now, "v": v}))
    except Exception:
        pass  # 写不进去只是下次还得重估,不影响本次结果


def estimate_min_total(dep: str, dest: str, day_count: int, travelers: int) -> float | None:
    """DeepSeek 估"最省也现实可行"的总花费(含往返大交通);失败返回 None = 不拦截。"""
    sig = route_sig(dep, dest, day_count, travelers)
    hit = _cached_min_total(sig)
    if hit is not None:
        return hit
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
        frag = _extract_json_object(str(getattr(resp, "content", "") or ""))
        if frag:
            v = float(json.loads(frag).get("min_total"))
            if 0 < v < 10_000_000:
                _store_min_total(sig, v)
                return v
    except Exception:
        pass  # 估算失败不缓存、不拦截,避免打断对话
    return None


def low_block(params: dict, insisted_sig: str = "") -> dict | None:
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
    min_total = estimate_min_total(dep, dest, day_count, travelers)
    if min_total is None or budget_total >= min_total:
        return None
    sig = route_sig(dep, dest, day_count, travelers)
    if insisted_sig == sig:
        return None
    return {"budget_total": budget_total, "min_total": min_total, "sig": sig}


def block_state(params: dict, insisted_sig: str = "") -> dict | None:
    """预算被按住时该写回状态的那几个字段(含给 prompt 用的两个数字);不用按住则 None。

    抽出来是因为 chitchat 和 budget 两个节点都要做同一件事:同一句话走不同路由,
    按钮状态和 min_budget 必须一模一样。数字只在一处 round,免得两边差一块钱。
    """
    block = low_block(params, insisted_sig)
    if not block:
        return None
    return {
        "status": "budget_low",
        "ready": False,
        "low_budget": True,
        "min_budget": round(block["min_total"]),
        "budget_total": round(block["budget_total"]),
        "min_total": round(block["min_total"]),
    }


_SYS = (
    "你是旅行预算评估专家,回答「这个行程钱够不够、大概要花多少」这类问题。"
    "依据是下面给的「路线最低花费估算」(含往返大交通,按最省但现实可行的方式估)和用户给的预算。"
    "先给明确结论(够 / 不够 / 差多少),再一句话说清钱主要花在哪、想省能怎么省。"
    "别编造具体票价、酒店价格、餐厅人均;缺关键信息就先问清楚,别硬给数字。"
    "语气自然友好,回复简洁(通常不超过 150 字),别用长清单。"
)


def _facts_text(params: dict, budget_total: float | None, min_total: float | None) -> str:
    """把估算结果拼成模型可读的参考数据;拿不准的项直接标"无法估算",别让它猜。"""
    dep = str(params.get("departure") or "").strip() or "未定"
    dest = str(params.get("destination") or "").strip() or "未定"
    days = resolved_days(params) or "未定"
    lines = [
        f"出发地:{dep};目的地:{dest};天数:{days};人数:{resolved_travelers(params)}",
        f"用户给的预算:{'未给' if budget_total is None else str(round(budget_total)) + ' 元'}",
        f"路线最低花费估算:{'无法估算(信息不足)' if min_total is None else str(round(min_total)) + ' 元'}",
    ]
    if min_total is None:
        lines.append("注意:这次没估出最低花费,只能给粗略区间并说明是粗略估计。")
    elif budget_total is not None and budget_total < min_total:
        lines.append(f"结论:用户预算不够,差约 {round(min_total - budget_total)} 元。")
    return "\n".join(lines)


def budget_node(state: ChatState) -> dict:
    trace = base.trace(state, "budget")
    params = state.get("params") or {}
    ready, status = base.ready_status(params)

    llm = build_chat_llm()
    if llm is None:
        return {"reply": "当前未配置 LLM_API_KEY,无法回答。请在 ai-service/.env 填好密钥后再试。",
                "status": "failed", "ready": ready, "agent_trace": trace}

    dep = str(params.get("departure") or "").strip()
    dest = str(params.get("destination") or "").strip()
    day_count = resolved_days(params)
    budget_total = budget_total_of(params)
    # dep/dest/天数缺一个就无法估路线成本;estimate_min_total 按路线缓存 6h,重复问不重复花 LLM
    min_total = estimate_min_total(dep, dest, day_count, resolved_travelers(params)) \
        if (dep and dest and day_count) else None

    st = block_state(params, str(state.get("insisted_sig") or "")) if ready else None

    hint = ""
    if not (dep and dest and day_count):
        hint = "\n关键信息还没齐,先用一两句自然地问清楚(别列清单),别给数字结论。"
    elif st:
        hint = (f"\n用户想省:点明按这预算正常排期走不下来,建议加到 {st['min_budget']} 元以上;"
                f"若他实在只有这些,告诉他可以说「就按最省的吧」,你会按最省方式压缩排期。")

    sys = (_SYS + base.param_status_text(params)
           + "\n\n〔参考数据〕\n" + _facts_text(params, budget_total, min_total) + hint)
    messages = [SystemMessage(content=sys)] + base.history_messages(state)

    try:
        reply = str(getattr(llm.invoke(messages), "content", "") or "").strip()
    except Exception as exc:
        reply = "回复生成超时/失败,请换个更短的说法再试。" if "Timeout" in type(exc).__name__ else \
            f"回复生成失败:{type(exc).__name__}:{exc}"
        return {"reply": reply, "status": "failed", "ready": ready, "agent_trace": trace}

    if not reply:
        reply = "我这次没估准这条线的最低花费,你把出发地、目的地和天数告诉我,我再算一次?"
    result = {
        "reply": reply,
        "status": st["status"] if st else status,
        "ready": st["ready"] if st else ready,
        "messages": base.with_reply(state, reply),
        "agent_trace": trace,
    }
    if st:
        result.update({"params": params, "low_budget": True, "min_budget": st["min_budget"]})
    return result
