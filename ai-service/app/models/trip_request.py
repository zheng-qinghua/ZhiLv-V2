"""生成请求入参模型(字段与 Java com.zhilv.dto.TripRequest 对齐,全部 snake_case)。"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class TripRequest(BaseModel):
    title: Optional[str] = None
    destination: str
    departure: Optional[str] = None     # 出发城市(每单必填;旧请求无则 None)
    start_date: str                     # yyyy-MM-dd,与 Java LocalDate.parse 同格式
    end_date: str                       # yyyy-MM-dd
    travelers: int = Field(default=2, ge=1)
    budget: float = Field(gt=0)
    preferences: list[str] = Field(default_factory=list)
    pace: Optional[str] = None          # 轻松 / 适中 / 紧凑
    hotel_level: Optional[str] = None   # 舒适型 / 高档型 / 经济型
    dietary_preferences: Optional[list[str]] = None   # 如 ["少辣"]
    special_notes: Optional[str] = None

    @field_validator("start_date", "end_date")
    @classmethod
    def _validate_date_format(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("日期格式须为 yyyy-MM-dd,如 2026-09-01")
        return v

    @model_validator(mode="after")
    def _end_not_before_start(self) -> "TripRequest":
        if date.fromisoformat(self.end_date) < date.fromisoformat(self.start_date):
            raise ValueError("结束日期不能早于开始日期")
        return self
