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

# ---- Java 后端(weather Agent 回调用;/internal/** 用共享密钥校验)----
# AI_SERVICE_KEY 不给默认值:本文件会进公开仓库,写死等于把共享密钥公开。
# 必须由 ai-service/.env(或环境变量)提供,且与后端 app.ai.service-key 完全一致。
# 两边都没配时,后端 /internal/weather 会回 500「内部接口未配置共享密钥:后端缺 AI_SERVICE_KEY。」
JAVA_BASE_URL = os.getenv("JAVA_BASE_URL", "http://localhost:8080")
AI_SERVICE_KEY = os.getenv("AI_SERVICE_KEY", "")

# ---- Redis(对话状态持久化,native JSON,本机 6379 无密码)----
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
# Redis 不可达时,单次读写最多等这么久就放弃、改走进程内兜底。
# 别名 localhost 会先试 IPv6(::1)再试 IPv4,两次各等满这个超时,所以:
#   每轮对话多等 ≈ 这个值 × 4(load 2 次 + save 2 次)。别调大。
REDIS_SOCKET_TIMEOUT_SECONDS = float(os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS", "0.5"))

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
# Milvus 不可用时每次召回要等 pymilvus 重试约 10 秒才降级;连续失败后短路这么久再试一次
RAG_BREAKER_TTL_SECONDS = float(os.getenv("RAG_BREAKER_TTL_SECONDS", "60"))
