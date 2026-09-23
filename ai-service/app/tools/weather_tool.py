"""天气工具:给 weather 专家(function calling)用,数据来自 Java 后端的 /internal/weather
(高德 key 在 Java 侧,Python 只消费)。

为什么是工具而不是直接拿 params.destination 查:实测 supervisor 对天气问句的**目的地抽取不稳**
(「大理明天天气怎么样」4 次里 1 次抽不到),一旦抽不到就没法确定查哪个城市。
交给模型读对话去定城市更稳,也顺带处理"用户这次问的城市不是行程目的地"。

降级:任何失败(Java 没起、key 不对、高德没配 key、超时)一律返回一句可读的"没查到",
由模型转述,天气故障不该打断对话。
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from langchain_core.tools import tool

from app.config import AI_SERVICE_KEY, JAVA_BASE_URL

TIMEOUT_SECONDS = 8  # 内部调用,本地回环;给足高德那一段(实测 0.5s)但别让对话卡住

_EMPTY = "（没有查到天气数据）"

_WEEK = {"1": "周一", "2": "周二", "3": "周三", "4": "周四", "5": "周五", "6": "周六", "7": "周日"}


def fetch_forecast(city: str) -> dict | None:
    """取某城市预报,返回 Java 响应里的 data 段(city/province/reportTime/days);失败返回 None。"""
    city = (city or "").strip()
    if not city:
        return None
    url = f"{JAVA_BASE_URL.rstrip('/')}/internal/weather?" + urllib.parse.urlencode({"city": city})
    try:
        req = urllib.request.Request(url, headers={"X-AI-Service-Key": AI_SERVICE_KEY})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None  # 含 401/400/502:Bearer 头不对、Java 没起、高德没配 key 都走这里
    data = body.get("data") if isinstance(body, dict) else None
    return data if isinstance(data, dict) else None


def format_forecast(data: dict, limit: int = 4) -> str:
    """拼成给模型看的预报文本;没有可用数据返回空串,调用方据此说"查不到"。"""
    days = [d for d in (data.get("days") or []) if isinstance(d, dict)][:limit]
    if not days:
        return ""
    today = str(data.get("reportTime") or "")[:10]
    where = " ".join(x for x in (str(data.get("city") or ""), str(data.get("province") or "")) if x)
    lines = [f"{where} 天气预报(发布时间 {data.get('reportTime') or '未知'})"]
    for d in days:
        date = str(d.get("date") or "")
        mark = "(今天)" if date and date == today else ""
        week = _WEEK.get(str(d.get("week") or ""), "")
        lines.append(
            f"- {date}{mark} {week}: 白天{_t(d.get('dayWeather'))} / 夜间{_t(d.get('nightWeather'))}, "
            f"{_t(d.get('nightTemp'))}~{_t(d.get('dayTemp'))}℃, {_t(d.get('dayWind'))}风"
        )
    return "\n".join(lines)


def _t(v) -> str:
    """高德字段缺了会是 None;给模型看的文本里不要出现 None。"""
    s = str(v or "").strip()
    return s if s else "未知"


@tool
def get_weather(city: str) -> str:
    """查某个城市未来几天的天气预报(日期 / 白天夜间天气 / 温度 / 风向)。

    适合回答「XX 明天天气怎么样」「后天会下雨吗」「去那边要不要带伞」这类问题。
    city 只写城市名,例如「大理」;不要带"市""省""去"等多余字样。
    用户在对话里提到的城市和行程目的地不一致时,以他这次问的城市为准。
    """
    try:
        return format_forecast(fetch_forecast(city) or {}) or _EMPTY
    except Exception:
        return _EMPTY


WEATHER_TOOLS = (get_weather,)
