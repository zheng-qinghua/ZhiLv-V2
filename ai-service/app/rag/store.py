"""持久化两端:文本块 → MySQL rag_chunk;向量 → Milvus rag_chunk_vec。
Milvus 只存 chunk_id(pk)+embedding,原文一律回 MySQL 取。连接按需懒建、轻量缓存。"""
from __future__ import annotations

import pymysql
from pymilvus import MilvusClient

from app.config import (
    EMBEDDING_DIM,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
    RAG_MILVUS_URI,
)

COLLECTION = "rag_chunk_vec"
CHUNK_TABLE = "rag_chunk"

# ---------- MySQL ----------


def mysql_conn() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def ensure_chunk_table() -> None:
    ddl = f"""CREATE TABLE IF NOT EXISTS {CHUNK_TABLE} (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        chunk_id VARCHAR(64) NOT NULL,
        source VARCHAR(64) NOT NULL,
        city VARCHAR(32) NULL,
        title VARCHAR(255) NOT NULL,
        chunk_text MEDIUMTEXT NOT NULL,
        chunk_index INT NOT NULL DEFAULT 0,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_chunk_id (chunk_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
    with mysql_conn() as conn:
        cur = conn.cursor()
        cur.execute(ddl)
        conn.commit()


def upsert_chunk_records(records: list[dict]) -> None:
    if not records:
        return
    sql = (
        f"INSERT INTO {CHUNK_TABLE} (chunk_id, source, city, title, chunk_index, chunk_text) "
        "VALUES (%s, %s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE source=VALUES(source), city=VALUES(city), "
        "title=VALUES(title), chunk_index=VALUES(chunk_index), chunk_text=VALUES(chunk_text)"
    )
    rows = [
        (r["chunk_id"], r["source"], r["city"], r["title"], r["chunk_index"], r["text"])
        for r in records
    ]
    with mysql_conn() as conn:
        cur = conn.cursor()
        cur.executemany(sql, rows)
        conn.commit()


def fetch_distinct_cities() -> list[str]:
    """有指南的城市名(如 ["大理","成都","西安"]);表没建/库挂了由调用方兜底。"""
    with mysql_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT DISTINCT city FROM {CHUNK_TABLE} WHERE city IS NOT NULL AND city <> ''")
        return [r["city"] for r in cur.fetchall()]


def fetch_guide_by_city(city: str, limit: int = 8) -> list[dict]:
    """取某城市指南前 limit 块(整篇注入用,按原文顺序),用于生成时的可靠参考。"""
    sql = (
        f"SELECT source, city, title, chunk_text FROM {CHUNK_TABLE} "
        "WHERE city=%s ORDER BY chunk_index ASC, id ASC LIMIT %s"
    )
    with mysql_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (city, limit))
        return [
            {"source": r["source"], "city": r["city"], "title": r["title"], "text": r["chunk_text"]}
            for r in cur.fetchall()
        ]


def fetch_chunks_by_ids(ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    placeholders = ",".join(["%s"] * len(ids))
    sql = (
        f"SELECT chunk_id, source, city, title, chunk_text "
        f"FROM {CHUNK_TABLE} WHERE chunk_id IN ({placeholders})"
    )
    out: dict[str, dict] = {}
    with mysql_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, list(ids))
        for row in cur.fetchall():
            out[row["chunk_id"]] = {
                "source": row["source"],
                "city": row["city"],
                "title": row["title"],
                "text": row["chunk_text"],
            }
    return out


# ---------- Milvus ----------

_milvus: MilvusClient | None = None


def milvus_client() -> MilvusClient:
    global _milvus
    if _milvus is None:
        _milvus = MilvusClient(uri=RAG_MILVUS_URI)
    return _milvus


def ensure_collection() -> None:
    from pymilvus import CollectionSchema, DataType, FieldSchema

    client = milvus_client()
    if not client.has_collection(COLLECTION):
        schema = CollectionSchema(
            fields=[
                FieldSchema("chunk_id", DataType.VARCHAR, is_primary=True, max_length=64),
                FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            ],
            description="RAG 指南文本块向量:正文存 MySQL rag_chunk",
        )
        client.create_collection(collection_name=COLLECTION, schema=schema)
    # 幂等保证有向量索引(create_collection 不会自动建 HNSW 索引)
    index = client.prepare_index_params(
        field_name="embedding", index_type="HNSW", metric_type="COSINE",
        index_name="vec_hnsw_idx", M=16, efConstruction=200,
    )
    try:
        client.create_index(COLLECTION, index)
    except Exception:
        pass  # 索引已存在等情况,忽略
    try:
        client.load_collection(COLLECTION)
    except Exception:
        pass


def upsert_vectors(rows: list[dict]) -> None:
    """rows: [{'chunk_id': str, 'embedding': [float]}]"""
    if not rows:
        return
    client = milvus_client()
    ensure_collection()
    client.insert(COLLECTION, rows)
    client.flush(COLLECTION)


def search_vectors(query_embedding: list[float], top_k: int) -> list[dict]:
    client = milvus_client()
    ensure_collection()
    res = client.search(
        COLLECTION,
        data=[query_embedding],
        limit=top_k,
        output_fields=["chunk_id"],
        search_params={"metric_type": "COSINE", "params": {}},
    )
    hits: list[dict] = []
    for h in (res[0] if res else []):
        cid = (h.get("entity") or {}).get("chunk_id")
        if cid:
            hits.append({"chunk_id": cid, "score": float(h.get("distance", 0.0))})
    return hits
