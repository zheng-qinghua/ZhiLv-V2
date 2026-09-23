"""Supervisor:一轮对话只调一次 LLM,同时产出「意图路由」和「参数抽取」。

为什么要合并成一次调用:参数抽取本来每轮就要调一次模型,路由再单独调一次
等于每轮翻倍延迟和成本。两个任务共用同一份对话上下文,写进同一个 JSON 契约,
一次调用出两个结果。

intent 枚举(架构见 docs/MULTI_AGENT_PLAN.md):
  chitchat  闲聊、打招呼、与行程无关的话
  guide     问攻略/美食/景点/交通等知识性问题
  weather   问天气
  budget    问预算够不够、大概花多少
  collect   补充或修正行程参数(出发地/目的地/时间/人数/预算/偏好)
  plan      信息齐了,明确要求生成行程
  revise    已有行程,要求改动其中某天/某项

降级:模型没配 / 调用失败 / JSON 解析失败 → intent 回落 collect(继续追问),
参数沿用旧值,绝不让对话断掉。

守卫:模型说 plan 但关键信息(出发地/目的地/时间)还没齐时,强制降级为 collect。
这个判断用代码做,不信模型。
"""
from __future__ import annotations

import json

from app.graph.params import PARAM_FIELDS, missing_params, resolved_days, resolved_travelers, route_sig
from app.graph.state import ChatState
from app.llm import _extract_json_object, build_chat_llm

INTENTS = ("chitchat", "guide", "weather", "budget", "collect", "plan", "revise")

_SYS = (
    "你是行程对话的调度器。读完整段对话,做两件事:"
    "①判断用户【这一轮】最想干什么,给出 intent;"
    "②抽取用户明确说过的行程参数。"
    "参数部分只挑用户明确说过的,不要猜测、不要补默认值、不要解析尚未说清的信息。"
    "只输出一个 JSON 对象,不要 markdown,不要解释。"
)

_HUMAN_TMPL = """当前已确定参数:{params}
对话全文:
{convo}

只输出一个 JSON 对象,字段取值下面这套(未提到/不确定/无变化的都填 null,绝不编造):

- intent: 字符串,本轮用户意图,只能取下面 7 个值之一:
  "chitchat" 闲聊/打招呼/与行程无关的话
  "guide"    问攻略、美食、景点、交通这类知识性问题(如"大理有什么好吃的""洱海怎么玩")
  "weather"  问天气(如"大理明天天气怎么样""这几天会下雨吗")
  "budget"   问预算够不够、大概要花多少钱(如"3000 块够吗""大概花多少钱")
  "collect"  补充或修正行程参数(说出发地/目的地/时间/人数/预算/偏好等)
  "plan"     关键信息(出发地+目的地+时间)已经齐了,且用户明确要求生成/开始做行程
  "revise"   已经有生成的行程,用户要求改动其中某天或某项安排
  拿不准一律填 "chitchat"。

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

注意:金额没说单位一律按总额 total;日期只认用户原话,别拿今天当默认;
地点变了但用户没重说时间/人数等,就保留上文已确定的。直接给 JSON,不要 markdown,不要解释。"""


def _build_prompt(params: dict, messages: list[dict]) -> str:
    convo = "\n".join(
        f"{'用户' if m.get('role') == 'user' else '助手'}: {m.get('content', '')}"
        for m in messages
    )
    return _HUMAN_TMPL.format(params=json.dumps(params, ensure_ascii=False), convo=convo)


def _merge_params(params: dict, obj: dict) -> dict:
    """把模型输出里白名单内的字段并进已确定参数(空值/空串跳过,不覆盖已有值)。"""
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
    return params


def _apply_guards(intent: str, params: dict, state: ChatState) -> str:
    """代码侧守卫,不依赖模型自觉。"""
    if intent not in INTENTS:
        return "collect"
    # 说要生成,但出发地/目的地/时间还没齐 → 先回去追问,别硬生成
    if intent == "plan" and missing_params(params):
        return "collect"
    # 注意:"说改行程但手上没有行程"这条守卫**不在这里**,在 reviser_node 里。
    # 放在这里只能降级成 chitchat,而 chitchat 会顺着用户的话往下答("好的,第2天全
    # 安排室内"),像是答应了要改一份并不存在的行程。由 reviser 自己回一句
    # 「我得先有一份行程才能改」才对,而 supervisor 是路由、不产出话术。
    return intent


def supervisor_node(state: ChatState) -> dict:
    params = dict(state.get("params") or {})
    trace = list(state.get("agent_trace") or []) + ["supervisor"]
    out: dict = {"params": params, "intent": "collect", "agent_trace": trace}

    llm = build_chat_llm()
    if llm is None:
        return out

    try:
        resp = llm.invoke([
            ("system", _SYS),
            ("human", _build_prompt(params, state.get("messages") or [])),
        ])
        frag = _extract_json_object(str(getattr(resp, "content", "")))
        if not frag:
            return out
        obj = json.loads(frag)
    except Exception:
        return out  # 路由/抽取失败不打断对话:沿用旧参数,按 collect 继续追问

    params = _merge_params(params, obj)
    intent = _apply_guards(str(obj.get("intent") or "").strip().lower(), params, state)
    out = {"params": params, "intent": intent, "agent_trace": trace}

    # 用户接受"预算低也按最省"→ 记住当前路由签名,同路由不再拦截(路由变了要重新拦)
    insist = obj.get("insist_low_budget")
    if insist is True or str(insist).strip().lower() in ("true", "yes", "1", "是", "对"):
        dep = str(params.get("departure") or "").strip()
        dest = str(params.get("destination") or "").strip()
        dc = resolved_days(params)
        if dep and dest and dc:
            out["insisted_sig"] = route_sig(dep, dest, dc, resolved_travelers(params))
    return out
