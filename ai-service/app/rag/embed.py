"""向量化(SiliconFlow BAAI/bge-m3,OpenAI 兼容 /embeddings)。无 key/离线时抛 EmbedError,
上层 RAG 统一降级为"不用检索",绝不让知识库问题拖垮对话。"""
from __future__ import annotations

import time

import httpx

from app.config import EMBEDDING_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL


class EmbedError(Exception):
    pass


def _url() -> str:
    return (EMBEDDING_BASE_URL or "https://api.siliconflow.cn/v1").rstrip("/") + "/embeddings"


def embed_texts(texts: list[str], max_retries: int = 2) -> list[list[float]]:
    if not EMBEDDING_API_KEY:
        raise EmbedError("未配置 EMBEDDING_API_KEY")
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]
        last_err: str | None = None
        for attempt in range(max_retries + 1):
            try:
                resp = httpx.post(
                    _url(),
                    headers={"Authorization": f"Bearer {EMBEDDING_API_KEY}"},
                    json={"model": EMBEDDING_MODEL, "input": batch},
                    timeout=60,
                )
                if resp.status_code == 200:
                    items = sorted(resp.json().get("data", []), key=lambda x: x.get("index", 0))
                    vecs = [it["embedding"] for it in items if "embedding" in it]
                    if len(vecs) == len(batch):
                        out.extend(vecs)
                        break
                    last_err = f"返回 {len(vecs)}/{len(batch)} 条向量"
                else:
                    last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as exc:  # 网络/超时
                last_err = str(exc)
            time.sleep(1)
        else:
            raise EmbedError(f"embedding 请求失败: {last_err}")
    return out


def embed_one(text: str) -> list[float] | None:
    try:
        vecs = embed_texts([text])
        return vecs[0] if vecs else None
    except EmbedError:
        return None
