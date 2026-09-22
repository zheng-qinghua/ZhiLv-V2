"""DeepSeek 接入 + 单轮生成 + 对话式(/chat)。

  GET  /health              健康检查
  POST /generate            收 TripRequest → 调 DeepSeek → 返回 TripPlan JSON
  POST /chat                收 {thread_id,message,action} → 对话式一轮(状态在 Redis,见 app/chat)
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.chat import handle_turn
from app.config import LLM_MODEL
from app.llm import generate_trip_plan
from app.models import TripRequest
from app.models.chat import ChatTurnInput

app = FastAPI(title="智旅云图 ai-service", version="0.3.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-service", "model": LLM_MODEL}


@app.post("/generate")
def generate(req: TripRequest):
    try:
        plan = generate_trip_plan(req)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 生成失败:{type(exc).__name__}:{exc}")
    return plan.model_dump()


@app.post("/chat")
def chat(req: ChatTurnInput):
    try:
        return handle_turn(req.thread_id, req.message, req.action)
    except Exception as exc:
        # 对话内部失败不裸抛:回 failed 让前端在气泡里展示,可重试
        return {
            "reply": f"处理失败:{type(exc).__name__}:{exc}",
            "status": "failed",
            "ready": False,
            "params": None,
        }
