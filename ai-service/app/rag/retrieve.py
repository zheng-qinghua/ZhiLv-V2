"""召回:query 嵌入 → Milvus 取 chunk_id → MySQL 取原文。任一端不可用都静默降级为空列表,
对话照常走(不带知识库),不让 RAG 故障打断主流程。"""
from __future__ import annotations

from app.config import RAG_TOP_K
from app.rag.embed import embed_texts
from app.rag.store import (
    fetch_chunks_by_ids,
    fetch_distinct_cities,
    fetch_guide_by_city,
    search_vectors,
)


def retrieve(query_text: str, top_k: int | None = None) -> list[dict]:
    top_k = top_k or RAG_TOP_K
    try:
        vecs = embed_texts([query_text])
        if not vecs:
            return []
    except Exception:
        return []
    try:
        hits = search_vectors(vecs[0], top_k)
    except Exception:
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
