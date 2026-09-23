"""DeepSeek 单轮生成逻辑(D17 加固版)。

对齐源项目 trip_planner_agent.py 的 ChatOpenAI 用法。产出必须 100% 贴合 TripPlan 契约:
  1. 解析失败 / 天数不足 / 字段缺失 → 自动把原因回灌给模型重试(最多 LLM_MAX_RETRIES+1 次);
  2. 天数超过请求时截断,少于请求时判失败重试(不伪造天数);
  3. 每天 date/day_index 由请求日期序列强制生成,忽略模型给的日期;
  4. transport 缺失时补步行默认,spots 缺失判失败(不编造景点)。
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import date, timedelta

from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_CACHE_TTL_SECONDS,
    LLM_MAX_RETRIES,
    LLM_MODEL,
    LLM_TIMEOUT_SECONDS,
)
from app.models import TripPlan, TripRequest


class PlanError(Exception):
    """模型输出校验不过,reason 会被当作纠正信息喂回模型。"""


def _to_cost(v) -> float | None:
    """把模型给的金额清洗成 float 元;识别不了就返回 None(调用方决定兜底)。"""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip().lower()
    if not s or s in {"免费", "free", "-", "无", "无价"}:
        return 0.0
    m = re.search(r"\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


# 进程内 TTL 缓存:key = 入参哈希,value = (存入时间戳, TripPlan)
_LLM_CACHE: dict[str, tuple[float, TripPlan]] = {}


def _cache_key(req: TripRequest, rag_context: str = "", feedback: str = "",
               weather_note: str = "") -> str:
    raw = json.dumps(req.model_dump(), sort_keys=True, ensure_ascii=False)
    if rag_context:
        raw += "\nRAG:" + rag_context
    # feedback 必须进 key:否则「按质检意见重排」会命中原始那版缓存,原样返回没改过的行程
    if feedback:
        raw += "\nFB:" + feedback
    # 天气同理,而且更隐蔽:预报每天在变,不进 key 的话明天同一请求会拿回昨天那份排期
    if weather_note:
        raw += "\nWX:" + weather_note
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> TripPlan | None:
    item = _LLM_CACHE.get(key)
    if item is None:
        return None
    ts, plan = item
    if time.time() - ts > LLM_CACHE_TTL_SECONDS:
        _LLM_CACHE.pop(key, None)
        return None
    # 返回副本,防止调用方改动污染缓存
    return TripPlan(**plan.model_dump())


def _cache_set(key: str, plan: TripPlan) -> None:
    _LLM_CACHE[key] = (time.time(), TripPlan(**plan.model_dump()))


def build_chat_llm():
    """创建 ChatOpenAI 实例;没配 API key 就返回 None。"""
    if not LLM_API_KEY:
        return None
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=0.3,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL or None,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )


def _extract_json_object(raw_text: str) -> str | None:
    """从模型输出里抠出第一个最外层大括号平衡的 JSON 片段(容忍 markdown 围栏/前后文字)。"""
    start = raw_text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(raw_text)):
        if raw_text[i] == "{":
            depth += 1
        elif raw_text[i] == "}":
            depth -= 1
            if depth == 0:
                return raw_text[start:i + 1]
    return None


def _build_prompt(req: TripRequest, day_count: int, correction: str | None = None,
                  rag_context: str | None = None,
                  weather_note: str | None = None) -> tuple[str, str]:
    system_prompt = (
        "你是一名旅行规划助手。请用中文生成一份结构化的每日旅行计划。"
        "必须遵守用户给出的出发地、目的地、日期、预算、人数、节奏与偏好。"
        "只输出一个 JSON 对象,不要输出 Markdown,不要输出解释文字,不要输出代码块。"
        "若额外备注里有明确诉求(例如看日落、不想早起、少辣、拍照等),"
        "必须把诉求落实到具体某一天的主要安排里,不能只写成泛泛提示。"
    )
    departure = (req.departure or "").strip()
    dep_line = departure or req.destination  # 没给出发地按当地游处理(往返大交通≈0)
    human_prompt = f"""出发地:{dep_line}
目的地:{req.destination}
出发日期:{req.start_date}
结束日期:{req.end_date}
天数:{day_count}
人数:{req.travelers}
预算:{req.budget}
偏好:{'、'.join(req.preferences) if req.preferences else '无特别偏好'}
节奏:{req.pace or '适中'}
住宿档次:{req.hotel_level or '舒适型'}
饮食偏好:{'、'.join(req.dietary_preferences) if req.dietary_preferences else '无'}
额外备注:{req.special_notes or '无'}

要求:
1. 输出一个整体 summary 和 tips。
2. 输出 {day_count} 天,day_index 从 1 到 {day_count},一天都不能少,不要加返程日(首日即抵达日、末日即返程日,都算在 {day_count} 天内)。
3. 每天给 theme;spots 至少 1 个主要景点(可再配 1-2 个顺路景点),每个景点含 name、description、duration、estimated_cost(门票估算,整数元,免费景点写 0)。
4. 每天给 meals(1-3 家,每家含 name、notes、estimated_cost 一餐估算整数元)和 transport(mode + note + estimated_cost 当天交通估算整数元)。
5. 每天给 hotel:对象含 name(当晚入住的当地具体酒店名)、level(住宿档次)、estimated_cost(当晚房价整数元)。
6. 排期密度匹配节奏:轻松别太满,紧凑可以多排。
7. 文本一律中文;当地交通 transport.mode 用:步行/地铁/公交/打车/骑行;首日与末日的跨城段(从出发地到目的地往返)可用 高铁/飞机/大巴。
8. 饮食偏好要落实到每天的餐饮:meals 的 notes 写清如何满足(如"菜可做少辣""避开香菜葱"),若为"无"则正常推荐当地美食。
9. 住宿档次为 {req.hotel_level or '舒适型'} 决定每晚 hotel 的 level 与 estimated_cost 量级:高档约 300-900 元/晚、舒适约 150-500 元/晚、经济约 80-250 元/晚(再按出行人数与城市行情微调),并在每天 note 里提一句当晚住宿安排。
10. 首日交通:第 1 天从出发地「{dep_line}」前往目的地,按到达时间安排当天:若需早起赶早班/当天上午能到可排半天行程,下午到就午后开玩,晚上到则只排晚餐+入住(入住酒店仍在当晚 city 内)。末日通常是返程日,当天安排要轻量、留足返程时间。若出发地「{dep_line}」与目的地首城是同一城市(或用户没说出发地),按本地游处理:首日/末日不排长途大交通。
11. 预算口径:预算 {req.budget} 是【含往返大交通】的总预算。整体 budget_breakdown 四类 tickets/hotel/meals/transport 相加约等于预算;其中 transport 类 = 「往返大交通(按出发地→目的地距离估算:高铁按二等座、长途按折扣机票或大巴)×人数」+「各天当地交通之和」;往返大交通金额请写进第 1 天(或末日)的 transport.note 里说明(如"高铁 北京→大理 约 620/人"),该天 transport.estimated_cost 只计当天当地交通,别重复累计大交通;各天 hotel.estimated_cost 之和尽量接近 budget_breakdown.hotel,各天门票/餐饮/当地交通的 estimated_cost 合计也尽量贴合 budget_breakdown 对应类;estimated_budget 给预估总花费。出发地==目的地首城时往返大交通≈0,transport 基本就是当地交通。
12. 所有 estimated_cost 一律整数元、可写 0;只返回 JSON,不要 ```json 围栏。
13. 每一天的 day 对象都必须给 city 字段:值为当天游玩/住宿所在的具体城市名(如 青岛、威海、济南)。多城市行程按停留顺序逐天标对,一个城市待几天就连续几天写同一城市;单城市行程每天都写同一城市。city 只写城市名(可带"市"),不要把 destination 整串或省份当 city。

JSON 结构示例:
{{
  "title": "行程标题",
  "destination": "{req.destination}",
  "departure": "{dep_line}",
  "budget_breakdown": {{"tickets": 800, "hotel": 1200, "meals": 700, "transport": 500}},
  "estimated_budget": 3200,
  "summary": "整体概述",
  "tips": ["提示1", "提示2"],
  "days": [
    {{
      "day_index": 1,
      "date": "{req.start_date}",
      "theme": "当天主题",
      "city": "杭州",
      "spots": [{{"name": "景点名", "description": "推荐理由", "duration": "2小时", "estimated_cost": 80}}],
      "meals": [{{"name": "餐厅或特色菜", "notes": "说明", "estimated_cost": 60}}],
      "transport": {{"mode": "地铁", "note": "如何到达", "estimated_cost": 20}},
      "hotel": {{"name": "当地具体酒店名", "level": "{req.hotel_level or '舒适型'}", "estimated_cost": 300}},
      "note": "当天备注"
    }}
  ]
}}
"""
    if rag_context and rag_context.strip():
        human_prompt += (
            "\n\n=== 目的地参考指南(真实资料) ===\n" + rag_context.strip() +
            "\n请参考其中真实的景点、美食与交通来安排具体行程,但必须严格遵守上面给定的日期、天数、"
            "人数与预算口径;不要编造指南之外的细节名目与价格。"
        )
    if weather_note and weather_note.strip():
        human_prompt += (
            "\n\n=== 目的地天气预报(真实数据) ===\n" + weather_note.strip() +
            "\n排期时把这个预报算进去:预报有雨的那天优先安排室内(博物馆/展馆/商街/古镇室内段),"
            "把洱海骑行、登山、观景这类户外项挪到不下雨的那天;高温天避开正午暴晒时段。"
            "**只对预报里明确列出的日期做调整**,预报没覆盖到的日子照常安排,"
            "不要编造预报里没有的天气,也不要在 summary/tips 里复述整份预报(挑影响安排的说)。"
        )
    if correction:
        # 标题写成中性的是因为这段有四个来源:解析失败重试、critic 的 issues、
        # 用户主动要求改行程、以及"轮次用尽仍不合格"的兜底。写死"未通过校验"对
        # 后两种来源语义不对,模型会以为自己在修 bug 而不是在执行用户指令。
        human_prompt += (
            f"\n\n=== 这次必须落实的调整要求 ===\n{correction}\n"
            f"请据此调整,重新输出一份完整 JSON。必须是正好 {day_count} 天,"
            f"每 天都要有 spots,不要省略任何一天,不要加任何解释文字。"
        )
    return system_prompt, human_prompt


def _normalize_plan(data: dict, req: TripRequest, day_count: int) -> dict:
    """把模型原始 JSON 规范化成可转 TripPlan 的干净 dict;不合格抛 PlanError。"""
    start = date.fromisoformat(req.start_date)

    # 请求级字段:模型漏了就回填请求值
    data.setdefault("title", req.title or f"{req.destination}旅行")
    data.setdefault("destination", req.destination)
    data.setdefault("departure", (req.departure or "").strip() or None)  # 模型漏了就以请求为准
    data.setdefault("start_date", req.start_date)
    data.setdefault("end_date", req.end_date)
    data.setdefault("travelers", req.travelers)
    data.setdefault("budget", req.budget)
    data.setdefault("preferences", list(req.preferences))

    # 预算明细:模型没给或给得不完整就按住宿档次对应的比例兜底,保证新行程必有
    budget = data.get("budget") or req.budget or 0
    bb = data.get("budget_breakdown")
    keys = ("tickets", "hotel", "meals", "transport")
    if not isinstance(bb, dict) or not all(isinstance(bb.get(k), (int, float)) for k in keys):
        if req.hotel_level == "高档型":
            w = {"tickets": 0.25, "hotel": 0.55, "meals": 0.12, "transport": 0.08}
        elif req.hotel_level == "经济型":
            w = {"tickets": 0.35, "hotel": 0.25, "meals": 0.25, "transport": 0.15}
        else:  # 舒适型 / 未指定
            w = {"tickets": 0.3, "hotel": 0.4, "meals": 0.2, "transport": 0.1}
        bb = {k: round(budget * v) for k, v in w.items()}
    data["budget_breakdown"] = bb
    data.setdefault("estimated_budget", budget)
    data.setdefault("pace", req.pace)
    data.setdefault("special_notes", req.special_notes)

    raw_days = data.get("days")
    if not isinstance(raw_days, list) or not raw_days:
        raise PlanError("输出缺少 days 数组")
    if len(raw_days) < day_count:
        raise PlanError(f"只输出了 {len(raw_days)} 天,需要 {day_count} 天")
    raw_days = raw_days[:day_count]  # 多出来的(如返程日)直接截掉

    days = []
    # 每晚住宿兜底价:预算明细 hotel 总量按天均摊(模型个别天漏给房价时用)
    nightly_est = int(round((bb.get("hotel") or 0) / day_count)) if day_count else 0
    for i, d in enumerate(raw_days):
        if not isinstance(d, dict):
            raise PlanError(f"第 {i + 1} 天不是对象")
        spots = d.get("spots")
        if not isinstance(spots, list) or not spots:
            raise PlanError(f"第 {i + 1} 天缺少 spots")

        clean_spots = []
        for sp in spots:
            if not isinstance(sp, dict) or not sp.get("name"):
                raise PlanError(f"第 {i + 1} 天存在缺少 name 的景点")
            clean_spots.append({
                "name": sp["name"],
                "description": sp.get("description"),
                "location": sp.get("location") if isinstance(sp.get("location"), dict) else None,
                "duration": sp.get("duration"),
                "image_url": sp.get("image_url"),
                "estimated_cost": _to_cost(sp.get("estimated_cost")),
            })

        raw_meals = d.get("meals")
        clean_meals = []
        for m in raw_meals if isinstance(raw_meals, list) else []:
            if isinstance(m, dict) and m.get("name"):
                clean_meals.append({
                    "name": m["name"],
                    "notes": m.get("notes"),
                    "estimated_cost": _to_cost(m.get("estimated_cost")),
                })

        td = d.get("transport")
        td = td if isinstance(td, dict) else {}
        transport = {
            "mode": td.get("mode") or "步行",
            "note": td.get("note"),
            "estimated_cost": _to_cost(td.get("estimated_cost")),
        }

        hotel = d.get("hotel")
        if isinstance(hotel, dict) and hotel.get("name"):
            hcost = _to_cost(hotel.get("estimated_cost"))
            clean_hotel = {
                "name": str(hotel["name"]).strip(),
                "level": str(hotel.get("level") or "").strip() or (req.hotel_level or "") or None,
                "estimated_cost": hcost if hcost is not None else nightly_est,
            }
        else:
            # 模型没给当晚酒店:兜底"目的地+档次"通用酒店,保证按天花费里住宿行存在
            clean_hotel = {
                "name": f"{req.destination}当地{req.hotel_level or '舒适型'}酒店",
                "level": req.hotel_level or None,
                "estimated_cost": nightly_est,
            }

        # 每天必须带 city(模块7 地图按天定位用):跨城市行程缺了它,通用景点名会
        # 在全国范围搜到异地同名 POI(如"栈桥"被定位到东北)。
        city = str(d.get("city") or "").strip()
        if not city:
            raise PlanError(f"第 {i + 1} 天缺少 city(当天所在城市名,如 青岛/济南)")
        if "省" in city and "市" not in city:
            raise PlanError(f"第 {i + 1} 天 city={city} 是省级区域,要填具体城市(如 青岛/济南)")

        days.append({
            "day_index": i + 1,
            "date": (start + timedelta(days=i)).isoformat(),  # 日期以请求为准
            "theme": d.get("theme"),
            "city": city,
            "spots": clean_spots,
            "meals": clean_meals,
            "hotel": clean_hotel,
            "transport": transport,
            "note": d.get("note"),
        })
    data["days"] = days
    data["day_count"] = day_count
    return data


def generate_trip_plan(req: TripRequest, max_attempts: int | None = None,
                       rag_context: str | None = None, feedback: str | None = None,
                       weather_note: str | None = None) -> TripPlan:
    """调 DeepSeek 生成 TripPlan;重试后仍失败抛 RuntimeError(携带最近失败原因)。

    feedback 是给 reviser 用的:把 critic 挑出来的问题 / 用户的要求灌进"必须落实的
    调整要求"那段。weather_note 是目的地未来几天的真实预报(行程起始日不在预报窗口
    内时由调用方传空)。两者都进缓存 key,所以修过的版本、不同天气下的版本不会互相命中。
    """
    llm = build_chat_llm()
    if llm is None:
        raise RuntimeError("未配置 LLM_API_KEY,无法调用 DeepSeek")

    key = _cache_key(req, rag_context or "", feedback or "", weather_note or "")
    cached = _cache_get(key)
    if cached is not None:
        return cached

    attempts = max_attempts or (LLM_MAX_RETRIES + 1)
    day_count = (date.fromisoformat(req.end_date) - date.fromisoformat(req.start_date)).days + 1
    correction: str | None = feedback or None

    for attempt in range(1, attempts + 1):
        system_prompt, human_prompt = _build_prompt(req, day_count, correction, rag_context,
                                                    weather_note)
        try:
            response = llm.invoke([("system", system_prompt), ("human", human_prompt)])
        except Exception as exc:
            # 超时是大行程(天数多/跨多城市)的常见失败:一次生成不完,重试只会再烧一轮
            # 时间,直接报错让用户放宽条件或重试,避免两次超时叠加等十几分钟
            if "Timeout" in type(exc).__name__:
                raise RuntimeError(
                    f"DeepSeek 请求超时(超过 {LLM_TIMEOUT_SECONDS} 秒未返回),"
                    f"内容过大(天数多/跨多城市)时生成很久,可稍后重试或拆分行程") from exc
            correction = f"模型调用异常({type(exc).__name__}:{exc})"
            continue

        raw_text = getattr(response, "content", "")
        json_text = _extract_json_object(str(raw_text))
        if json_text is None:
            correction = f"模型返回里没找到 JSON(预览:{str(raw_text)[:200]})"
            continue
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as exc:
            correction = f"JSON 解析失败:{exc}"
            continue
        try:
            data = _normalize_plan(data, req, day_count)
            plan = TripPlan(**data)
            _cache_set(key, plan)
            return plan
        except PlanError as exc:
            correction = str(exc)
            continue
        except Exception as exc:  # pydantic ValidationError:spot 缺 name、类型错等
            correction = f"输出与 TripPlan 契约不符:{type(exc).__name__}:{exc}"
            continue

    raise RuntimeError(f"尝试 {attempts} 次仍未生成合格行程,最近原因:{correction}")
