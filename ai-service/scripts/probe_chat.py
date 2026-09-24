"""路由探针:往本地 ai-service 发对话,打印每轮 supervisor 判出的 intent 与参数。

多 Agent 改造的验证工具。supervisor 分类准不准,靠这个脚本用固定话术集回归,
不用每次手点前端。

用法(在 ai-service 目录下,服务需已启动):
    .venv/Scripts/python scripts/probe_chat.py "你好呀"
    .venv/Scripts/python scripts/probe_chat.py "从北京去大理玩5天" "3000块够吗"
    .venv/Scripts/python scripts/probe_chat.py --suite            # 跑内置话术集(每条独立会话)
    .venv/Scripts/python scripts/probe_chat.py --url http://127.0.0.1:8100 "你好"

输出格式: `[intent] status=... ready=... | 用户话 → 回复摘要`
--suite 模式会在末尾给出分类命中率统计,便于判断 prompt 是否需要调。

**--suite 每轮都用新的 run 标记**(默认取时间戳,可用 `--tag` 指定),跑完清掉自己造的会话。
原因:`probe-suite-{i}` 这种固定会话 id 会跨轮次复用 Redis 里的历史 —— 第二轮的对话里
已经躺着第一轮的问答,量出来的分歧就成了"历史不同"而不是"分类抖动",数字没法当回归基线。
(实测踩过:同代码三轮 15→14→13→12,看起来像抖动,其实是会话在攒历史。)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8100"

# 内置话术集:(话术, 期望 intent)。期望值用于 --suite 的命中率统计。
SUITE: list[tuple[str, str]] = [
    ("你好呀", "chitchat"),
    ("你能干什么", "chitchat"),
    ("谢谢,你真好", "chitchat"),
    ("大理有什么好吃的", "guide"),
    ("洱海怎么玩比较合适", "guide"),
    ("成都必去的景点有哪些", "guide"),
    ("大理明天天气怎么样", "weather"),
    ("这几天会下雨吗", "weather"),
    ("我一个人去大理 5 天,3000 块够吗", "budget"),
    ("大概要花多少钱", "budget"),
    ("我们从北京出发", "collect"),
    ("想去大理", "collect"),
    ("玩 5 天", "collect"),
    ("就按最省的安排吧", "collect"),
    # 信息不齐时说"生成" → 守卫应把它压回 collect
    ("帮我生成行程吧", "collect"),
]


def turn(url: str, thread: str, message: str, action: str = "chat") -> dict:
    body = json.dumps({"thread_id": thread, "message": message, "action": action}).encode("utf-8")
    req = urllib.request.Request(url + "/chat", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.load(resp)
    except urllib.error.URLError as exc:
        sys.exit(f"连不上 ai-service({url}):{exc}\n先在 ai-service 目录跑 "
                 f".venv/Scripts/python -m uvicorn app.main:app --port 8100")


def _fmt_params(params: dict | None) -> str:
    """参数压缩成一行,只显示已确定的键(按值排序,便于肉眼比对)。"""
    if not params:
        return "-"
    return ",".join(f"{k}={params[k]}" for k in sorted(params) if params[k] is not None)


def line(user_msg: str, out: dict, expect: str | None = None) -> bool:
    got = out.get("intent")
    ok = expect is None or got == expect
    flag = "" if expect is None else ("  OK " if ok else f"  期望 {expect} ✗")
    reply = (out.get("reply") or "").replace("\n", " ")
    trace = out.get("agent_trace") or []
    print(f"[{got or '?':8}] status={out.get('status'):14} ready={str(out.get('ready')):5} "
          f"| {user_msg} → {reply[:38]}{flag}")
    print(f"           trace: {'→'.join(trace) or '-'}")
    print(f"           params: {_fmt_params(out.get('params'))}")
    return ok


def main() -> None:
    # Windows 控制台默认 GBK,模型回复里的 emoji 会直接抛 UnicodeEncodeError 打断回归
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("messages", nargs="*", help="要说的话,可多条(同一会话连续说)")
    ap.add_argument("--suite", action="store_true", help="跑内置话术集(每条独立会话)")
    ap.add_argument("--thread", default="probe", help="会话 id,同一 id 连续对话")
    ap.add_argument("--tag", default="", help="suite 的 run 标记(默认时间戳),用来隔开各轮会话")
    ap.add_argument("--keep", action="store_true", help="suite 跑完不清理会话(默认清理)")
    ap.add_argument("--url", default=DEFAULT_URL)
    args = ap.parse_args()

    if args.suite:
        tag = args.tag or time.strftime("%m%d-%H%M%S")
        threads = [f"probe-{tag}-{i}" for i in range(len(SUITE))]
        hit = 0
        try:
            for thread, (msg, expect) in zip(threads, SUITE):
                out = turn(args.url, thread, msg)
                hit += line(msg, out, expect)
            print(f"\n分类命中 {hit}/{len(SUITE)}   (run={tag})")
        finally:
            if not args.keep:
                _drop(args.url, threads)
        return

    if not args.messages:
        ap.error("给一句话,或加 --suite")

    for msg in args.messages:
        line(msg, turn(args.url, args.thread, msg))


def _drop(url: str, threads: list[str]) -> None:
    """清掉本次 suite 造的会话。探针跑得勤,不清的话 Redis 里会攒一堆没人看的会话状态。

    清不掉不算失败(Redis 没起时对话本来也走内存态),所以这里只提示不抛。
    """
    try:
        from app.redis_client import get_client
    except Exception as exc:  # 不在 ai-service 目录下跑时不致命
        print(f"(跳过清理:{type(exc).__name__})")
        return
    try:
        client = get_client()
        keys = ["zhilv:chat:" + t for t in threads]
        client.delete(*keys)
    except Exception as exc:
        print(f"(跳过清理:{type(exc).__name__})")


if __name__ == "__main__":
    main()
