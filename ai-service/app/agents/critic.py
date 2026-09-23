"""行程评审专家:拿规则挑生成的 TripPlan 的毛病,挑出来交给 reviser 重排。

**为什么是纯规则、不调模型**(和别的专家不一样):模型审模型会跟着一起犯同样的错 ——
要审的恰恰是"预算/天数/城市这类能对账的东西",这些用代码判是确定的、免费的、可复现的。
模型能审的只有"好不好玩",那没法验证对错,不审。

规则清单(全部来自 docs/MULTI_AGENT_PLAN.md Step 7):
  1. days 数量 = day_count,且 day_index 从 1 连续
  2. 每天至少一个景点(空的一天 = 那天没安排)
  3. 每天 city 不能是省级行政区(省级粒度会让地图按天定位失效)
  4. 节奏与每天景点数匹配(轻松 ≤3、适中 ≤4、紧凑 ≤5)
  5. budget_breakdown 四项之和 = estimated_budget ±10%(明细对不上总账)
  6. 各天 hotel 之和 = budget_breakdown.hotel ±20%
  7. 总花费 vs 这条路线的最低花费估算(低于 80% 判"排期不可行")
  8. 饮食偏好要落进 meals 的 notes/name

第 7 条为什么要复用 budget.estimate_min_total:原计划写的是"总花费 vs 预算 ±10%",
但实测**模型会把 estimated_budget 直接写成和 budget 一模一样**(预算 600 → 预估也是 600),
这条规则永远不触发。真正能查出问题的是"600 元玩大理 5 天 3 人不现实" ——
也就是和路线最低估算比。该估算在预算护栏那一步已经算过并缓存 6h,这里通常 0 秒;
用户没给预算时跳过此条(没有对照物,且不想为它付一次冷启动)。

降级:任何规则内部算不出来(字段缺失/类型不对)一律跳过该条,不抛异常 ——
评审是"尽力而为"的质检,不能因为一个字段缺了就把整轮生成搞崩。
"""
from __future__ import annotations

from app.agents import base
from app.agents.budget import estimate_min_total
from app.graph.params import resolved_days, resolved_travelers
from app.graph.state import ChatState

# 每天景点数上限(超过就是排太满,玩不动)
_PACE_CAP = {"轻松": 3, "适中": 4, "紧凑": 5}
_DEFAULT_CAP = 4
_DAILY_MIN_SPOTS = 1

_BUDGET_TOLERANCE = 0.10      # 明细之和 vs 预估总花费
_HOTEL_TOLERANCE = 0.20       # 各晚房价之和 vs 明细里的住宿
_MIN_VIABLE_RATIO = 0.80      # 总花费低于"最低估算"的这个比例才算不可行

# 省级行政区:AI 标 city 时容易写成"云南"这种大区,地图按天定位就废了
_PROVINCE_LEVEL = {
    "北京", "上海", "天津", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏",
    "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "海南",
    "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾", "内蒙古", "广西", "西藏",
    "宁夏", "新疆", "香港", "澳门",
}
_SUFFIXES = ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区", "自治区", "省", "市")

# 饮食偏好前缀:剥掉之后剩下的就是要在菜里找的关键词(「不吃辣」→找「辣」)
_DIET_PREFIXES = ("不能吃", "不要吃", "不喜欢吃", "不吃", "忌", "无")


def _norm_city(v) -> str:
    s = str(v or "").strip()
    for suf in _SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
    return s


def _num(v) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _diet_tokens(pref: str) -> set[str]:
    """把「不吃辣」拆成 {不吃辣, 辣},用后者去菜名/备注里找。

    剥出来的词**不能按长度过滤**:「不吃辣」「忌酸」「素食」剩下的都是单字(辣/酸/素),
    恰恰是要找的那个字。只丢掉空串。
    """
    s = pref.strip()
    toks = {s}
    for pre in _DIET_PREFIXES:
        if s.startswith(pre) and len(s) > len(pre):
            toks.add(s[len(pre):].strip())
            break
    return {t for t in toks if t}


def critique_plan(plan: dict, params: dict) -> dict:
    """按规则审一份 TripPlan(dict 形态),返回 {"pass": bool, "issues": [str]}。"""
    issues: list[str] = []
    days = [d for d in (plan.get("days") or []) if isinstance(d, dict)]

    _check_days(plan, days, issues)
    _check_cities(plan, days, issues)
    _check_spots(plan, days, issues)
    _check_money(plan, days, params, issues)
    _check_diet(plan, days, params, issues)

    return {"pass": not issues, "issues": issues}


def _check_days(plan: dict, days: list, issues: list) -> None:
    day_count = plan.get("day_count")
    if isinstance(day_count, int) and day_count > 0 and len(days) != day_count:
        issues.append(f"天数对不上:day_count={day_count},实际 days={len(days)}")
    if not days:
        issues.append("行程一天都没有(days 为空)")
        return
    idx = [d.get("day_index") for d in days]
    if idx != list(range(1, len(days) + 1)):
        issues.append(f"day_index 不是从 1 连续编号:{idx}")


def _check_cities(plan: dict, days: list, issues: list) -> None:
    # 目的地本身就是直辖市/省级时(比如去上海、重庆),city 写省级反而是对的,整条跳过
    if _norm_city(plan.get("destination")) in _PROVINCE_LEVEL:
        return
    bad = sorted({_norm_city(d.get("city")) for d in days
                  if _norm_city(d.get("city")) in _PROVINCE_LEVEL})
    if bad:
        issues.append(f"这些天的 city 写成了省级行政区,要精确到市/县:{'、'.join(bad)}")


def _check_spots(plan: dict, days: list, issues: list) -> None:
    cap = _PACE_CAP.get(str(plan.get("pace") or "").strip(), _DEFAULT_CAP)
    empty, over = [], []
    for d in days:
        n = len(d.get("spots") or [])
        if n < _DAILY_MIN_SPOTS:
            empty.append(d.get("day_index"))
        elif n > cap:
            over.append(f"第{d.get('day_index')}天{n}个")
    if empty:
        issues.append(f"这些天一个景点都没安排:{'、'.join(str(x) for x in empty)}")
    if over:
        issues.append(f"节奏是「{plan.get('pace') or '未标'}」,每天最多 {cap} 个景点,"
                      f"但这几天排超了:{'、'.join(over)}")


def _viable_minimum(params: dict) -> float | None:
    """这条路线"最省也现实可行"的总花费估算;取不到就返回 None(那条规则就不查)。

    直接复用 budget.estimate_min_total:预算护栏在 planner 之前已经算过并缓存 6h,
    所以这里通常 0 秒。用户没给预算时不做这个查询 —— 没有对照物,不想白付一次冷启动。
    """
    if not _num(params.get("budget")):
        return None
    dep = str(params.get("departure") or "").strip()
    dest = str(params.get("destination") or "").strip()
    day_count = resolved_days(params)
    if not (dep and dest and day_count):
        return None
    try:
        return estimate_min_total(dep, dest, day_count, resolved_travelers(params))
    except Exception:
        return None


def _check_money(plan: dict, days: list, params: dict, issues: list) -> None:
    est = _num(plan.get("estimated_budget"))
    bk = plan.get("budget_breakdown") if isinstance(plan.get("budget_breakdown"), dict) else {}
    parts = {k: _num(bk.get(k)) or 0.0 for k in ("tickets", "hotel", "meals", "transport")}
    total = sum(parts.values())

    # 明细之和 vs 预估总花费:模型把明细写花了的常见表现
    if est and est > 0 and total > 0:
        if abs(total - est) > est * _BUDGET_TOLERANCE:
            issues.append(f"预算明细对不上总账:四类相加 {round(total)} 元,"
                          f"预估总花费却写 {round(est)} 元")

    # 各晚房价之和 vs 明细里的住宿:住几晚就该收几晚的钱
    night_sum = sum(_num((d.get("hotel") or {}).get("estimated_cost")) or 0.0 for d in days)
    if parts["hotel"] > 0 and night_sum > 0:
        if abs(night_sum - parts["hotel"]) > parts["hotel"] * _HOTEL_TOLERANCE:
            issues.append(f"住宿费对不上:各晚房价相加 {round(night_sum)} 元,"
                          f"明细里写的住宿是 {round(parts['hotel'])} 元")

    spend = est or total
    if not spend:
        return

    budget = _num(plan.get("budget")) or _num(params.get("budget"))
    min_total = _viable_minimum(params)

    # 用户预算本身就低于路线最低估算时(例如 600 元玩大理 5 天),模型只有两条路:
    # 照做(总花费低于最低估算 = 编的)或按现实排(超预算)。**后者不该被骂** ——
    # 那已经是最好的结果了,而且预算护栏在生成前就劝过用户。所以这种情况只保留"花太少"
    # 那条,超预算那条让位,否则两条相反的意见会把模型来回拉扯,改出来的比原来还差。
    budget_unattainable = bool(min_total and budget and budget < min_total * _MIN_VIABLE_RATIO)

    if min_total and min_total > 0 and spend < min_total * _MIN_VIABLE_RATIO:
        issues.append(
            f"总花费 {round(spend)} 元低于这条路线的最低估算 {round(min_total)} 元,"
            f"这个价钱排不出真的能走的行程。请如实按最低估算安排,并在 summary/tips 里"
            f"明确说明「这个预算只够做什么、不够做什么」,不要靠编造低价数字把总花费凑到预算上"
        )
    elif not budget_unattainable and budget and budget > 0 \
            and spend > budget * (1 + _BUDGET_TOLERANCE):
        issues.append(f"总花费 {round(spend)} 元超出预算 {round(budget)} 元 10% 以上,"
                      f"要按预算往下压(换更省的交通/住宿档次、减少付费项目)")


def _check_diet(plan: dict, days: list, params: dict, issues: list) -> None:
    prefs = [str(x).strip() for x in (params.get("dietary_preferences") or []) if str(x).strip()]
    if not prefs:
        return
    # 菜名和备注都要看:偏好常被模型写进名字(「素斋面」)而不是 notes
    haystack = " ".join(
        f"{m.get('name') or ''} {m.get('notes') or ''}"
        for d in days for m in (d.get("meals") or []) if isinstance(m, dict)
    )
    missed = [p for p in prefs if not any(t in haystack for t in _diet_tokens(p))]
    if missed:
        issues.append(f"饮食偏好没落到安排里:{'、'.join(missed)} 在每天的 meals 里看不出来")


def critic_node(state: ChatState) -> dict:
    """评审节点:只往状态里写 critique(和 agent_trace),不改 reply/plan。

    没有行程可审(参数不全被 planner 拦下、生成失败)时直接放过 —— 那不是"行程有毛病",
    该由 planner 的话术去处理,别让 reviser 拿到一份空计划去重排。
    """
    trace = base.trace(state, "critic")
    plan = state.get("plan")
    if not isinstance(plan, dict) or not plan.get("days"):
        return {"critique": {"pass": True, "issues": []}, "agent_trace": trace}
    return {"critique": critique_plan(plan, state.get("params") or {}), "agent_trace": trace}
