"""简单 RAG(M3):文本块存 MySQL rag_chunk,向量存 Milvus,查询经 bge-m3 嵌入后召回。
知识源:data/rag/*.md(大理/成都/西安指南),由 app/rag/ingest.py 一次性入库。
"""
