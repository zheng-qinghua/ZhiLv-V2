"""攻略检索工具:给 retriever 专家(function calling)用。

两个工具而不是一个,因为两条检索路径适用场景不同、且能互相兜底:
  search_guide    语义检索(Milvus 向量库)—— 适合具体问题(某道菜哪家好、某景点怎么去)
  get_city_guide  整篇城市指南(MySQL)  —— 适合宽泛问题(这城市怎么玩、几天合适)
Milvus 没起时 search_guide 返回空,模型会转而调 get_city_guide,不至于答不出来。
"""
from __future__ import annotations

from langchain_core.tools import tool

from app.rag.retrieve import format_for_prompt, format_guide_by_city, retrieve

_EMPTY = "（没有检索到相关资料）"


@tool
def search_guide(query: str) -> str:
    """在攻略资料库里做语义检索,返回与问题最相关的攻略片段。

    适合查具体问题:某道菜哪家好、某个景点怎么去、某个玩法值不值得。
    query 用中文,写清「目的地 + 关注点」,例如「大理 酸辣鱼 推荐」。
    如果需要某个城市的整体介绍,用 get_city_guide 更合适。
    """
    try:
        return format_for_prompt(retrieve(query)) or _EMPTY
    except Exception:
        return _EMPTY


@tool
def get_city_guide(city: str) -> str:
    """取出某个城市的整篇攻略指南(景点 / 美食 / 交通 / 玩法)。

    适合宽泛问题:这个城市怎么玩、有哪些必去的地方、待几天合适。
    city 只写城市名,例如「大理」;不要带"省""去"等多余字样。
    """
    try:
        return format_guide_by_city(city) or _EMPTY
    except Exception:
        return _EMPTY


RAG_TOOLS = (search_guide, get_city_guide)
