"""ai-service 全局配置:所有可调参数从 .env 读,默认值写在代码里。

D15 只需要端口;LLM 相关是给 D16(DeepSeek 接入)预留的。
D16 前把 .env 填好:LLM_API_KEY 必填,LLM_BASE_URL 按你的渠道填。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---- 服务 ----
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8100"))

# ---- Redis(对话状态持久化,native JSON,本机 6379 无密码)----
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# ---- 大模型(OpenAI 兼容接口,DeepSeek / 中转渠道都用这套)----
# 你指定的模型,key / base_url 由你填进 ai-service/.env
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
# 相同入参的行程结果缓存秒数:重复请求直接秒回,不再调 DeepSeek
LLM_CACHE_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL_SECONDS", "300"))

# ---- 向量化(SiliconFlow BAAI/bge-m3,OpenAI 兼容 /embeddings),键复用 Agent Param ----
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))

# ---- MySQL:rag_chunk(文本块原文)与 zhilv 业务库同一实例,供 RAG 召回取块 ----
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "zhilv")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

# ---- Milvus:只存向量 + chunk_id(pk),召回后按 chunk_id 回 MySQL 取原文 ----
# 注意:不能叫 MILVUS_URI,pymilvus 保留该环境变量(期望 http(s)://... 形式),避免撞名
RAG_MILVUS_URI = os.getenv("RAG_MILVUS_URI", "http://localhost:19530")

# ---- RAG 指南数据(切块源 .md,已拷贝到 ai-service 内,不依赖 Agent Param 目录)----
RAG_DATA_DIR = Path(os.getenv("RAG_DATA_DIR", "data/rag"))
if not RAG_DATA_DIR.is_absolute():
    RAG_DATA_DIR = BASE_DIR / RAG_DATA_DIR
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))  # bge-m3 固定 1024
