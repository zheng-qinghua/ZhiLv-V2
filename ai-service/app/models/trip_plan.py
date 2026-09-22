"""TripPlan 契约模型。

字段/结构与 D11 契约一致,三个端对同一份契约:
  ai-service  Python Pydantic  (本文件)
  backend     Java  com.zhilv.dto.TripPlan
  frontend    TS   src/types/trip.ts
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Location(BaseModel):
    lat: float
    lng: float


class Spot(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[Location] = None
    duration: Optional[str] = None      # 如 "2小时"
    image_url: Optional[str] = None
    estimated_cost: Optional[float] = None   # 门票估算(元,免费景点为 0)


class Meal(BaseModel):
    name: str
    notes: Optional[str] = None
    estimated_cost: Optional[float] = None   # 一餐/人均估算(元)


class Transport(BaseModel):
    mode: str                           # 步行 / 地铁 / 公交 / 打车 / 骑行
    note: Optional[str] = None
    estimated_cost: Optional[float] = None   # 当天交通估算(元)


class Hotel(BaseModel):
    """当晚住宿:酒店名 + 档次 + 房价估算。"""
    name: str
    level: Optional[str] = None         # 舒适型 / 高档型 / 经济型
    estimated_cost: Optional[float] = None   # 当晚房价估算(元)


class BudgetBreakdown(BaseModel):
    """整体预算拆到四类(元),与源项目 Result 页的预算明细一一对应。"""
    tickets: float = 0.0                # 景点门票
    hotel: float = 0.0                  # 酒店住宿
    meals: float = 0.0                  # 餐饮费用
    transport: float = 0.0              # 交通费用


class Day(BaseModel):
    day_index: int
    date: str                           # yyyy-MM-dd
    theme: Optional[str] = None
    city: Optional[str] = None          # 当天主要活动所在城市(模块7 地图按天定位用,AI 生成时标注)
    spots: list[Spot] = Field(default_factory=list)
    meals: list[Meal] = Field(default_factory=list)
    hotel: Optional[Hotel] = None       # 当晚住宿
    transport: Optional[Transport] = None
    note: Optional[str] = None


class TripPlan(BaseModel):
    id: Optional[int] = None
    title: str
    destination: str
    departure: Optional[str] = None      # 出发城市(每单必填,与 destination 平行)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    day_count: int = 0
    travelers: int = 0
    budget: Optional[float] = None
    budget_breakdown: Optional[BudgetBreakdown] = None   # 预算明细(四类)
    estimated_budget: Optional[float] = None             # 预估总花费(≈预算)
    preferences: list[str] = Field(default_factory=list)
    pace: Optional[str] = None
    special_notes: Optional[str] = None
    summary: Optional[str] = None
    tips: list[str] = Field(default_factory=list)
    days: list[Day] = Field(default_factory=list)
    source: Optional[str] = None
    created_at: Optional[str] = None
