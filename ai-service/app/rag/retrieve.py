"""召回:query 嵌入 → Milvus 取 chunk_id → MySQL 取原文。任一端不可用都静默降级为空列表,
对话照常走(不带知识库),不让 RAG 故障打断主流程。

熔断:Milvus 挂掉时 pymilvus 每次都要重试约 10 秒才抛异常。若不做处理,每轮对话都白等
这 10 秒(连嵌入的 1 秒也白花)。所以检测到连续失败后,在 RAG_BREAKER_TTL_SECONDS 内
直接返回空,不再发起请求;TTL 过期后再真试一次,通了就恢复。"""
from __future__ import annotations

import time

from app.config import RAG_BREAKER_TTL_SECONDS, RAG_TOP_K
from app.rag.embed import embed_texts
from app.rag.store import (
    fetch_chunks_by_ids,
    fetch_distinct_cities,
    fetch_guide_by_city,
    search_vectors,
)

# Milvus 熔断状态:记录"到什么时候为止认为它不可用"。用 dict 而非 global 变量,少一处 global 声明
_BREAKER: dict[str, float] = {"milvus_ok_after": 0.0}


def _milvus_is_down() -> bool:
    return time.time() < _BREAKER["milvus_ok_after"]


def retrieve(query_text: str, top_k: int | None = None) -> list[dict]:
    if _milvus_is_down():
        return []  # 已知不可用:直接降级,不浪费嵌入和 10 秒重试
    top_k = top_k or RAG_TOP_K
    try:
        vecs = embed_texts([query_text])
        if not vecs:
            return []
    except Exception:
        return []
    try:
        hits = search_vectors(vecs[0], top_k)
        _BREAKER["milvus_ok_after"] = 0.0  # 这次通了,恢复正常
    except Exception:
        _BREAKER["milvus_ok_after"] = time.time() + RAG_BREAKER_TTL_SECONDS
        return []
    meta = fetch_chunks_by_ids([h["chunk_id"] for h in hits])
    results = []
    for h in hits:
        m = meta.get(h["chunk_id"])
        if m:
            results.append({"score": round(h["score"], 4), **m})
    return results


def format_for_prompt(results: list[dict]) -> str:
    """拼成给大模型的参考资料段;空就返回空串,调用方据此省略知识库部分。"""
    if not results:
        return ""
    parts = []
    for i, r in enumerate(results, 1):
        src = r.get("source") or "未知来源"
        parts.append(f"[{i}] ({src}·{r.get('title') or ''})\n{r.get('text') or ''}")
    return "\n\n".join(parts)


def format_guide_by_city(dest: str, limit: int = 8) -> str:
    """按目的地城市整篇取指南(生成行程的可靠参考);名字带省市前缀也能对上,匹配不到返回空串。"""
    dest = (dest or "").strip()
    if not dest:
        return ""
    try:
        cities = fetch_distinct_cities()
    except Exception:
        return ""
    city = next((c for c in cities if c and (c in dest or dest in c)), None)
    if not city:
        return ""
    try:
        rows = fetch_guide_by_city(city, limit)
    except Exception:
        return ""
    if not rows:
        return ""
    parts = []
    for i, r in enumerate(rows, 1):
        name = r.get("title") or ""
        parts.append(f"[{i}] ({city}指南·{name})\n{r.get('text') or ''}")
    return "\n\n".join(parts)
