"""一次性/可重跑 RAG 入库:切块 → 文本进 MySQL、向量进 Milvus。幂等(chunk_id 稳定 upsert)。
用法: cd ai-service && ./.venv/Scripts/python -m app.rag.ingest
"""
from __future__ import annotations

from app.config import EMBEDDING_DIM, RAG_DATA_DIR
from app.rag.chunker import load_all_chunks
from app.rag.embed import embed_texts
from app.rag.store import ensure_chunk_table, ensure_collection, upsert_chunk_records, upsert_vectors


def run() -> dict:
    records = load_all_chunks(RAG_DATA_DIR)
    if not records:
        raise SystemExit(f"{RAG_DATA_DIR} 下没有 .md 指南可切块")
    texts = [r["text"] for r in records]
    vecs = embed_texts(texts)
    if len(vecs) != len(texts):
        raise RuntimeError(f"向量数 {len(vecs)} != 块数 {len(texts)}")

    ensure_chunk_table()
    upsert_chunk_records(records)
    ensure_collection()
    upsert_vectors(
        [
            {"chunk_id": r["chunk_id"], "embedding": v}
            for r, v in zip(records, vecs)
        ]
    )
    bad_dim = sum(1 for v in vecs if len(v) != EMBEDDING_DIM)
    return {
        "files": len(list(RAG_DATA_DIR.glob("*.md"))),
        "chunks": len(records),
        "dim": len(vecs[0]) if vecs else 0,
        "bad_dim": bad_dim,
    }


if __name__ == "__main__":
    info = run()
    print("ingest OK:", info)
