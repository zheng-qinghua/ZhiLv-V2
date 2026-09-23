"""对话式规划的对外入口:Redis 状态存取 + handle_turn + 确认生成。

每轮(thread 粒度,backend 用会话 id 当 thread):
  载入状态 → 跑 LangGraph 图(见 app/graph/builder.py,supervisor 先判意图再分发专家)
  → 写回状态。
图本身不挂 checkpointer:状态由 handle_turn 从 Redis 载入、跑完再写回(native JSON,
Windows Redis 无 RediSearch,不用 langgraph-checkpoint-redis)。
降级:Redis 挂了退进程内内存态;RAG(Milvus/嵌入)挂了退纯对话,均不让对话断掉。

confirm 路径(前端「确认行程」按钮)不进图:它没有新消息可给 supervisor 分类,所以直接叫
planner 专家 —— 与「帮我生成行程」走的是同一个 planner_node。生成的 plan 会存回 state,
Step 7/8 的 critic/reviser 才有东西可审、可改。
"""
from __future__ import annotations

import copy
import json

import redis as redis_lib

from app.config import REDIS_HOST, REDIS_PORT, REDIS_SOCKET_TIMEOUT_SECONDS
from app.graph.builder import GENERATE_GRAPH, GRAPH

_REDIS_PREFIX = "zhilv:chat:"


# ---------------- Redis 状态存取 ----------------
# 三个坑,都在这里处理:
#   1) 每次新建连接没必要 —— 复用一个 client。
#   2) redis-py 8.x 默认带重试退避:只设 socket_connect_timeout 时 Redis 停机单次 get 要等
#      27 秒(实测),每轮 load+save 就是 ~50 秒。retry=None + 短超时后降到每次 ~1 秒。
#   3) 历史只在 Redis 里的话,Redis 一挂**当轮就把对话清空**(读不到 → 当成新会话)。
#      所以本地要留镜像 _STATE:读 Redis 失败时兜底用,对话不会断。
# _DIRTY 记"本地比 Redis 新"的 thread(那次写没成功),读的时候优先本地,
# 免得 Redis 恢复后拿旧值把刚聊的内容盖掉;写成功就清标记,并自然完成回同步。
_CLIENT: dict[str, redis_lib.Redis] = {}
_STATE: dict[str, dict] = {}
_DIRTY: set[str] = set()
_STATE_MAX = 500  # 本地镜像条数上限(每条约几 KB),防长跑进程累积
_DEFAULT_STATE = {"messages": [], "params": {}}


def _client() -> redis_lib.Redis:
    r = _CLIENT.get("r")
    if r is None:
        r = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True,
                            socket_connect_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
                            socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
                            retry=None)
        _CLIENT["r"] = r
    return r


def _remember(thread_id: str, state: dict) -> None:
    """记本地镜像。满了就丢最老的"已同步"条目;脏条目(还没写进 Redis)一个都不丢。"""
    _STATE[thread_id] = state
    while len(_STATE) > _STATE_MAX:
        victim = next((k for k in _STATE if k not in _DIRTY), None)
        if victim is None:
            break
        _STATE.pop(victim, None)


def _load_state(thread_id: str) -> dict:
    if thread_id in _DIRTY:
        return copy.deepcopy(_STATE[thread_id])  # 本地比 Redis 新,别被 Redis 里的旧值盖掉
    try:
        raw = _client().get(_REDIS_PREFIX + thread_id)
        data = json.loads(raw) if raw else None
        if isinstance(data, dict):
            _remember(thread_id, data)
            return data
    except Exception:
        return copy.deepcopy(_STATE.get(thread_id) or _DEFAULT_STATE)
    return copy.deepcopy(_STATE.get(thread_id) or _DEFAULT_STATE)


def _save_state(thread_id: str, state: dict) -> None:
    _remember(thread_id, state)  # 先记本地:写 Redis 失败也不丢这一轮
    try:
        _client().set(_REDIS_PREFIX + thread_id, json.dumps(state, ensure_ascii=False))
    except Exception:
        _DIRTY.add(thread_id)  # 下次读优先本地,下一轮继续试着写回来
        return
    _DIRTY.discard(thread_id)


# ---------------- 对外入口 ----------------


def handle_turn(thread_id: str, message: str = "", action: str = "chat") -> dict:
    state = _load_state(thread_id)
    state.setdefault("messages", [])
    state.setdefault("params", {})

    confirm = bool(action and action.strip().lower() == "confirm")
    text = (message or "").strip()
    if confirm or not text:
        # 点「确认行程」时没有新消息可以给 supervisor 分类,所以不进 GRAPH、走 GENERATE_GRAPH
        # (planner → critic → reviser,复用同一批节点)。和「帮我生成行程」的质量门槛一致:
        # 前者只是少了 supervisor 那一跳。
        out = GENERATE_GRAPH.invoke(state)
        result = {
            "reply": out.get("reply") or "行程暂时生成不出来,稍后再让我试一次?",
            "status": out.get("status", "collecting"),
            "ready": out.get("ready", False),
            "params": state["params"] or None,
            "intent": "plan",
            "agent_trace": out.get("agent_trace"),
        }
        if out.get("low_budget"):
            result["low_budget"] = True
            result["min_budget"] = out.get("min_budget")
        if out.get("plan"):
            result["plan"] = out["plan"]
        # 只有 planner 动过历史才写回;生成失败/护栏拦下时它也会写(要留痕),没动就保持原样
        if out.get("messages") is not None:
            _save_state(thread_id, {"messages": out["messages"], "params": state["params"],
                                    "plan": out.get("plan") or state.get("plan"),
                                    "insisted_sig": state.get("insisted_sig") or ""})
        return result

    state["messages"] = list(state["messages"])
    state["messages"].append({"role": "user", "content": text})
    state["new_message"] = text
    out = GRAPH.invoke(state)

    final_messages = out.get("messages") or state["messages"]
    final_params = out.get("params") or state["params"] or {}
    _save_state(thread_id, {"messages": final_messages, "params": final_params,
                            "plan": out.get("plan") or state.get("plan"),
                            "insisted_sig": out.get("insisted_sig") or (state.get("insisted_sig") or "")})

    reply = out.get("reply") or "我没听清,换个说法再问我一次吧。"
    result = {
        "reply": reply,
        "status": out.get("status", "collecting"),
        "ready": out.get("ready", False),
        "params": final_params or None,
        # 本轮 supervisor 判出的意图 + 走过的专家。前端暂未使用,给 probe 脚本与排查用;
        # Java 按名取字段,多余的字段不影响解析
        "intent": out.get("intent"),
        "agent_trace": out.get("agent_trace"),
    }
    if out.get("low_budget"):
        result["low_budget"] = True
        result["min_budget"] = out.get("min_budget")
    if out.get("plan"):
        result["plan"] = out["plan"]  # planner 生成的新行程:前端据此打开结果页
    return result
