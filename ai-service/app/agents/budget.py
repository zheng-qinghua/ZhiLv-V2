"""预算专家:估"这条路线最省也现实可行要多少钱",并据此做预算护栏。

被两处使用:
  1. 对话里 supervisor 路由到 budget 时,回答"我这预算够吗";
  2. 确认生成前,预算远低于最低花费就把确认按住(状态 budget_low)。

提成独立模块是为了断开循环依赖:chitchat 节点要用 low_block,
而 chitchat 由图引用,不能再反过来 import 入口 chat.py。
"""
from __future__ import annotations

import json
import time

from app.graph.params import budget_total_of, resolved_days, resolved_travelers, route_sig
from app.llm import _extract_json_object, build_chat_llm

_MIN_TTL_SECONDS = 6 * 3600  # 最低花费按路线缓存 6h,跨会话复用
_MIN_CACHE: dict[str, tuple[float, float]] = {}  # sig -> (存入时间, 最低总花费)


def estimate_min_total(dep: str, dest: str, day_count: int, travelers: int) -> float | None:
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
