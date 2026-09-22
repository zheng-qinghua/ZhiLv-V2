"""参数工具:抽取白名单 + 参数取值解析 + 确认门槛判断。

被 chat.py(confirm 路径)、agents/supervisor.py(抽取)、agents/chitchat.py(追问)
共用,所以独立成模块,不放进任何一个 Agent——否则会互相 import。
"""
from __future__ import annotations

import re
from datetime import date

# 参数白名单:抽取只认这些键,保证透给前端与后续生成的都是契约内的干净字段
PARAM_FIELDS = (
    "departure",
    "destination",
    "start_date",
    "end_date",
    "total_days",
    "travelers",
    "budget",
    "budget_unit",  # total(总额) | per_person(人均)
    "preferences",
    "pace",
    "hotel_level",
    "dietary_preferences",
    "special_notes",
)


def to_float(v) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"\d+(?:\.\d+)?", str(v))
    return float(m.group()) if m else None


def to_int(v, default: int) -> int:
    f = to_float(v)
    return int(f) if f is not None else default


def to_date(v) -> date | None:
    try:
        return date.fromisoformat(str(v))
    except Exception:
        return None


def missing_params(params: dict) -> list[str]:
    """确认门槛:出发地 + 目的地 + 时间(具体日期或大概天数)三样齐了才算可确认。"""
    missing = []
    if not str(params.get("departure") or "").strip():
        missing.append("出发地")
    if not str(params.get("destination") or "").strip():
        missing.append("目的地")
    if not (params.get("start_date") and params.get("end_date")) and not params.get("total_days"):
        missing.append("出行时间(日期或大概天数)")
    return missing


def is_ready(params: dict) -> bool:
    return not missing_params(params)


def resolved_days(params: dict) -> int | None:
    start = to_date(params.get("start_date"))
    end = to_date(params.get("end_date"))
    if start and end and end >= start:
        return (end - start).days + 1
    td = to_int(params.get("total_days"), 0)
    return td if td >= 1 else None


def resolved_travelers(params: dict) -> int:
    return max(1, to_int(params.get("travelers"), 3))  # 与生成默认对齐


def budget_total_of(params: dict) -> float | None:
    """把用户给的预算统一折算成总额(人均口径 × 人数);没给或非正返回 None。"""
    raw = to_float(params.get("budget"))
    if raw is None or raw <= 0:
        return None
    if str(params.get("budget_unit") or "").strip() == "per_person":
        return raw * resolved_travelers(params)
    return raw


def route_sig(dep: str, dest: str, day_count: int, travelers: int) -> str:
    """一条路线的签名(出发地+目的地+天数+人数),用于缓存与"已接受按最省"的判定。"""
    return f"{dep}->{dest}|{day_count}天|{travelers}人"
